"""Phoring backend entrypoint."""

import os
import sys

# Windows: force UTF-8 IO for readable logs and error messages.
if sys.platform == 'win32':
    # Ensure Python process uses UTF-8.
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
    # Reconfigure stdio streams for UTF-8 output where supported.
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add backend project directory to import path.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import Config


def main():
    """Validate config and start the Flask app."""
    # Validate required configuration before app boot.
    errors = Config.validate()
    if errors:
        print("Configuration error:")
        for err in errors:
            print(f" - {err}")
        print("\nPlease check your .env configuration.")
        sys.exit(1)
    
    # Create app instance.
    app = create_app()
    
    # Read runtime configuration.
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = Config.DEBUG
    
    # Start service.
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    main()

