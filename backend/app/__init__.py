"""
Phoring Backend - Flask Application Factory
"""

import os
import uuid
import time

import warnings

# Suppress multiprocessing resource_tracker warnings
warnings.filterwarnings("ignore", message=".*resource_tracker.*")

from flask import Flask, request, jsonify, g
from flask_cors import CORS

from.config import Config
from.utils.logger import setup_logger, get_logger
from.utils.validators import ValidationError


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # JSON encoding: allow non-ASCII characters
    if hasattr(app, 'json') and hasattr(app.json, 'ensure_ascii'):
        app.json.ensure_ascii = False
    
    # Setup logging
    logger = setup_logger('phoring')
    
    # Only log startup in main process (avoid duplicate in debug reloader)
    is_reloader_process = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    debug_mode = app.config.get('DEBUG', False)
    should_log_startup = not debug_mode or is_reloader_process
    
    if should_log_startup:
        logger.info("=" * 50)
        logger.info("Phoring Backend starting...")
        logger.info("=" * 50)
    
    # CORS
    cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
    CORS(app, resources={r"/api/*": {"origins": cors_origins}})
    
    # Simulation process cleanup
    from.services.simulation_runner import SimulationRunner
    SimulationRunner.register_cleanup()

    # Register atexit handler to mark in-flight tasks as failed on shutdown
    import atexit
    def _cleanup_inflight_tasks():
        try:
            from.models.task import TaskManager, TaskStatus
            tm = TaskManager()
            with tm._task_lock:
                for task in tm._tasks.values():
                    if task.status in (TaskStatus.PENDING, TaskStatus.PROCESSING):
                        task.status = TaskStatus.FAILED
                        task.error = "Server shutdown while task was in progress"
        except Exception:
            pass
    atexit.register(_cleanup_inflight_tasks)

    if should_log_startup:
        logger.info("Simulation process cleanup function registered")
    
    # --- Request lifecycle: ID tracing + timing ---
    
    @app.before_request
    def before_request_handler():
        g.request_id = request.headers.get('X-Request-ID', uuid.uuid4().hex[:16])
        g.request_start = time.monotonic()
        req_logger = get_logger('phoring.request')
        req_logger.debug(f"[{g.request_id}] {request.method} {request.path}")
    
    @app.after_request
    def after_request_handler(response):
        # Attach request ID to response for client-side correlation
        response.headers['X-Request-ID'] = getattr(g, 'request_id', 'unknown')
        elapsed = time.monotonic() - getattr(g, 'request_start', time.monotonic())
        req_logger = get_logger('phoring.request')
        req_logger.debug(
            f"[{getattr(g, 'request_id', '?')}] "
            f"{response.status_code} ({elapsed:.3f}s)"
        )
        return response
    
    # --- Global error handlers (prevent traceback leaks) ---
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """Return 400 for input validation failures."""
        return jsonify({
            "success": False,
            "error": str(e),
            "error_type": "validation_error",
            "request_id": getattr(g, 'request_id', None)
        }), 400
    
    @app.errorhandler(400)
    def handle_bad_request(e):
        return jsonify({
            "success": False,
            "error": "Bad request. Check your input and try again.",
            "request_id": getattr(g, 'request_id', None)
        }), 400

    from werkzeug.exceptions import BadRequest

    @app.errorhandler(BadRequest)
    def handle_bad_request_exception(e):
        return jsonify({
            "success": False,
            "error": "Bad request. Check your input and try again.",
            "request_id": getattr(g, 'request_id', None)
        }), 400

    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({
            "success": False,
            "error": "Resource not found",
            "request_id": getattr(g, 'request_id', None)
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(e):
        """Log full traceback server-side but never expose it to the client."""
        err_logger = get_logger('phoring.error')
        err_logger.error(
            f"[{getattr(g, 'request_id', '?')}] "
            f"Internal error on {request.method} {request.path}: {e}",
            exc_info=True
        )
        return jsonify({
            "success": False,
            "error": "Internal server error. Check server logs for details.",
            "request_id": getattr(g, 'request_id', None)
        }), 500
    
    # --- Register blueprints ---
    
    from.api import graph_bp, simulation_bp, report_bp
    app.register_blueprint(graph_bp, url_prefix='/api/graph')
    app.register_blueprint(simulation_bp, url_prefix='/api/simulation')
    app.register_blueprint(report_bp, url_prefix='/api/report')
    
    # --- Health check with dependency status ---
    
    @app.route('/health')
    def health():
        """Health check with dependency readiness."""
        status = {
            'status': 'ok',
            'service': 'Phoring Backend',
            'checks': {
                'llm_configured': bool(Config.LLM_API_KEY),
                'zep_configured': bool(Config.ZEP_API_KEY),
                'llm_model': Config.LLM_MODEL_NAME,
                'llm_base_url': Config.LLM_BASE_URL,
                'validator_2_configured': bool(Config.LLM_VALIDATOR_2_API_KEY),
                'validator_3_configured': bool(Config.LLM_VALIDATOR_3_API_KEY),
                'speed_mode': Config.SIMULATION_SPEED_MODE,
                'geopolitical_events': Config.ENABLE_GEOPOLITICAL_EVENTS,
                'upload_dir_exists': os.path.isdir(Config.UPLOAD_FOLDER),
            }
        }
        config_errors = Config.validate()
        if config_errors:
            status['status'] = 'degraded'
            status['warnings'] = config_errors
        return jsonify(status)
    
    if should_log_startup:
        logger.info("Phoring Backend initialized successfully")
    
    return app

