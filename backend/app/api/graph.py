"""
Graph API endpoints.
Handles projects, ontology generation, graph building, and task status.
"""

import os
import traceback
import threading
from flask import request, jsonify

from. import graph_bp
from..config import Config
from..services.ontology_generator import OntologyGenerator
from..services.graph_builder import GraphBuilderService
from..services.text_processor import TextProcessor
from..utils.file_parser import FileParser
from..utils.logger import get_logger
from..utils.validators import Validators, ValidationError
from..models.task import TaskManager, TaskStatus
from..models.project import ProjectManager, ProjectStatus

logger = get_logger('phoring.api')


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    if not filename or '.' not in filename:
        return False
    ext = os.path.splitext(filename)[1].lower().lstrip('.')
    return ext in Config.ALLOWED_EXTENSIONS


# ============== Project endpoints ==============

@graph_bp.route('/project/<project_id>', methods=['GET'])
def get_project(project_id: str):
    """Get project details."""
    Validators.validate_project_id(project_id)
    project = ProjectManager.get_project(project_id)

    if not project:
        return jsonify({
            "success": False,
            "error": f"Project not found: {project_id}"
        }), 404

    return jsonify({
        "success": True,
        "data": project.to_dict()
    })


@graph_bp.route('/project/list', methods=['GET'])
def list_projects():
    """List all projects."""
    limit = request.args.get('limit', 50, type=int)
    projects = ProjectManager.list_projects(limit=limit)

    return jsonify({
        "success": True,
        "data": [p.to_dict() for p in projects],
        "count": len(projects)
    })


@graph_bp.route('/project/<project_id>', methods=['DELETE'])
def delete_project(project_id: str):
    """Delete a project."""
    Validators.validate_project_id(project_id)
    success = ProjectManager.delete_project(project_id)

    if not success:
        return jsonify({
            "success": False,
            "error": f"Project not found or delete failed: {project_id}"
        }), 404

    return jsonify({
        "success": True,
        "message": f"Project deleted: {project_id}"
    })


@graph_bp.route('/project/<project_id>/reset', methods=['POST'])
def reset_project(project_id: str):
    """Reset project status to allow rebuilding the graph."""
    Validators.validate_project_id(project_id)
    project = ProjectManager.get_project(project_id)

    if not project:
        return jsonify({
            "success": False,
            "error": f"Project not found: {project_id}"
        }), 404

    # Reset to the most recent completed stage
    if project.ontology:
        project.status = ProjectStatus.ONTOLOGY_GENERATED
    else:
        project.status = ProjectStatus.CREATED

    project.graph_id = None
    project.graph_build_task_id = None
    project.error = None
    ProjectManager.save_project(project)

    return jsonify({
        "success": True,
        "message": f"Project reset: {project_id}",
        "data": project.to_dict()
    })


# ============== Step 1: Upload files and generate ontology ==============

@graph_bp.route('/ontology/generate', methods=['POST'])
def generate_ontology():
    """
    Upload documents and generate an ontology definition.

    Content-Type: multipart/form-data

    Parameters:
        files: Document files (PDF/MD/TXT), required
        simulation_requirement: Simulation requirement description, required
        project_name: Project name (optional)
        additional_context: Extra context (optional)

    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "ontology": {
                    "entity_types": [...],
                    "edge_types": [...],
                    "analysis_summary": "..."
                },
                "files": [...],
                "total_text_length": 12345
            }
        }
    """
    try:
        logger.info("=== Starting ontology generation ===")

        simulation_requirement = request.form.get('simulation_requirement', '')
        project_name = request.form.get('project_name', 'Unnamed Project')
        additional_context = request.form.get('additional_context', '')

        logger.debug(f"Project: {project_name}")
        logger.debug(f"Simulation requirement: {simulation_requirement[:100]}...")

        if not simulation_requirement:
            return jsonify({
                "success": False,
                "error": "Please provide simulation requirement description (simulation_requirement)"
            }), 400

        # Get uploaded files
        uploaded_files = request.files.getlist('files')
        if not uploaded_files or all(not f.filename for f in uploaded_files):
            return jsonify({
                "success": False,
                "error": "Please upload document file"
            }), 400

        # Create project
        project = ProjectManager.create_project(name=project_name)
        project.simulation_requirement = simulation_requirement
        logger.info(f"Created project: {project.project_id}")

        # Parse files and extract text
        document_texts = []
        all_text = ""

        for file in uploaded_files:
            if file and file.filename and allowed_file(file.filename):
                Validators.validate_filename(file.filename, Config.ALLOWED_EXTENSIONS)
                file_info = ProjectManager.save_file_to_project(
                    project.project_id,
                    file,
                    file.filename
                )
                project.files.append({
                    "filename": file_info["original_filename"],
                    "size": file_info["size"]
                })

                # Extract text content
                text = FileParser.extract_text(file_info["path"])
                text = TextProcessor.preprocess_text(text)
                document_texts.append(text)
                all_text += f"\n\n=== {file_info['original_filename']} ===\n{text}"

        if not document_texts:
            ProjectManager.delete_project(project.project_id)
            return jsonify({
                "success": False,
                "error": "Failed to process document, please check file format"
            }), 400

        # Save extracted text
        project.total_text_length = len(all_text)
        ProjectManager.save_extracted_text(project.project_id, all_text)
        logger.info(f"Text extraction complete: {len(all_text)} characters")

        # Generate ontology via LLM
        logger.info("Calling LLM to generate ontology definition...")
        generator = OntologyGenerator()
        ontology = generator.generate(
            document_texts=document_texts,
            simulation_requirement=simulation_requirement,
            additional_context=additional_context if additional_context else None
        )

        # Save ontology to project
        entity_count = len(ontology.get("entity_types", []))
        edge_count = len(ontology.get("edge_types", []))
        logger.info(f"Ontology generated: {entity_count} entity types, {edge_count} relation types")

        project.ontology = {
            "entity_types": ontology.get("entity_types", []),
            "edge_types": ontology.get("edge_types", [])
        }
        project.analysis_summary = ontology.get("analysis_summary", "")
        project.status = ProjectStatus.ONTOLOGY_GENERATED
        ProjectManager.save_project(project)
        logger.info(f"=== Ontology generation complete === project_id: {project.project_id}")

        return jsonify({
            "success": True,
            "data": {
                "project_id": project.project_id,
                "project_name": project.name,
                "ontology": project.ontology,
                "analysis_summary": project.analysis_summary,
                "files": project.files,
                "total_text_length": project.total_text_length
            }
        })

    except Exception as e:
        logger.error(f"Ontology generation failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Ontology generation failed. Check server logs for details."
        }), 500


# ============== Step 2: Build knowledge graph ==============

@graph_bp.route('/build', methods=['POST'])
def build_graph():
    """
    Build a knowledge graph from the project's extracted text and ontology.

    Request body (JSON):
        {
            "project_id": "proj_xxxx",     // required, from step 1
            "graph_name": "My Graph",       // optional
            "chunk_size": 500,              // optional, default 500
            "chunk_overlap": 50             // optional, default 50
        }

    Returns:
        {
            "success": true,
            "data": {
                "project_id": "proj_xxxx",
                "task_id": "task_xxxx",
                "message": "Graph build task started. Poll /task/{task_id} for progress."
            }
        }
    """
    try:
        logger.info("=== Starting graph build ===")

        # Validate config
        errors = []
        if not Config.ZEP_API_KEY:
            errors.append("ZEP_API_KEY not configured")
        if errors:
            logger.error(f"Configuration error: {errors}")
            return jsonify({
                "success": False,
                "error": "Configuration error: " + "; ".join(errors)
            }), 500

        # Parse request
        data = request.get_json(silent=True) or {}
        project_id = data.get('project_id')
        logger.debug(f"Request params: project_id={project_id}")

        if not project_id:
            return jsonify({
                "success": False,
                "error": "Please provide project_id"
            }), 400

        # Get project
        project = ProjectManager.get_project(project_id)
        if not project:
            return jsonify({
                "success": False,
                "error": f"Project not found: {project_id}"
            }), 404

        # Check project status
        force = data.get('force', False)

        if project.status == ProjectStatus.CREATED:
            return jsonify({
                "success": False,
                "error": "Project ontology not yet generated, please call /ontology/generate"
            }), 400

        if project.status == ProjectStatus.GRAPH_BUILDING and not force:
            return jsonify({
                "success": False,
                "error": "Graph is currently building, please wait or add force: true",
                "task_id": project.graph_build_task_id
            }), 400

        # If force rebuilding, reset status
        if force and project.status in [ProjectStatus.GRAPH_BUILDING, ProjectStatus.FAILED, ProjectStatus.GRAPH_COMPLETED]:
            project.status = ProjectStatus.ONTOLOGY_GENERATED
            project.graph_id = None
            project.graph_build_task_id = None
            project.error = None

        # Get build configuration
        graph_name = data.get('graph_name', project.name or 'Phoring Graph')
        chunk_size = data.get('chunk_size', project.chunk_size or Config.DEFAULT_CHUNK_SIZE)
        chunk_overlap = data.get('chunk_overlap', project.chunk_overlap or Config.DEFAULT_CHUNK_OVERLAP)

        project.chunk_size = chunk_size
        project.chunk_overlap = chunk_overlap

        # Get extracted text
        text = ProjectManager.get_extracted_text(project_id)
        if not text:
            return jsonify({
                "success": False,
                "error": "Text content not yet extracted"
            }), 400

        # Get ontology
        ontology = project.ontology
        if not ontology:
            return jsonify({
                "success": False,
                "error": "Ontology definition not yet generated"
            }), 400

        # Create async task
        task_manager = TaskManager()
        task_id = task_manager.create_task(f"Build graph: {graph_name}")
        logger.info(f"Created graph build task: task_id={task_id}, project_id={project_id}")

        # Update project status
        project.status = ProjectStatus.GRAPH_BUILDING
        project.graph_build_task_id = task_id
        ProjectManager.save_project(project)

        # Background build task
        def build_task():
            build_logger = get_logger('phoring.build')
            try:
                build_logger.info(f"[{task_id}] Starting graph build...")
                task_manager.update_task(
                    task_id,
                    status=TaskStatus.PROCESSING,
                    message="Initializing graph build service..."
                )

                builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)

                # Split text into chunks
                task_manager.update_task(
                    task_id,
                    message="Splitting text into chunks...",
                    progress=5
                )
                chunks = TextProcessor.split_text(
                    text,
                    chunk_size=chunk_size,
                    overlap=chunk_overlap
                )
                total_chunks = len(chunks)

                # Create graph
                task_manager.update_task(
                    task_id,
                    message="Creating Zep graph...",
                    progress=10
                )
                graph_id = builder.create_graph(name=graph_name)

                # Update project with graph_id
                project.graph_id = graph_id
                ProjectManager.save_project(project)

                # Set ontology definition
                task_manager.update_task(
                    task_id,
                    message="Setting ontology definition...",
                    progress=15
                )
                builder.set_ontology(graph_id, ontology)

                # Add text chunks with progress tracking
                def add_progress_callback(msg, progress_ratio):
                    progress = 15 + int(progress_ratio * 40)  # 15% - 55%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )

                task_manager.update_task(
                    task_id,
                    message=f"Adding {total_chunks} text chunks...",
                    progress=15
                )

                episode_uuids = builder.add_text_batches(
                    graph_id,
                    chunks,
                    batch_size=3,
                    progress_callback=add_progress_callback
                )

                # Wait for Zep to finish processing
                task_manager.update_task(
                    task_id,
                    message="Waiting for Zep to process data...",
                    progress=55
                )

                def wait_progress_callback(msg, progress_ratio):
                    progress = 55 + int(progress_ratio * 35)  # 55% - 90%
                    task_manager.update_task(
                        task_id,
                        message=msg,
                        progress=progress
                    )

                builder._wait_for_episodes(episode_uuids, wait_progress_callback)

                # Retrieve graph stats (lightweight — avoids loading full payloads)
                task_manager.update_task(
                    task_id,
                    message="Retrieving graph statistics...",
                    progress=95
                )
                graph_info = builder.get_graph_info(graph_id)

                # Update project status
                project.status = ProjectStatus.GRAPH_COMPLETED
                ProjectManager.save_project(project)

                node_count = graph_info.node_count
                edge_count = graph_info.edge_count
                build_logger.info(f"[{task_id}] Graph build complete: graph_id={graph_id}, nodes={node_count}, edges={edge_count}")

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    message="Graph build complete",
                    progress=100,
                    result={
                        "project_id": project_id,
                        "graph_id": graph_id,
                        "node_count": node_count,
                        "edge_count": edge_count,
                        "chunk_count": total_chunks
                    }
                )

            except Exception as e:
                build_logger.error(f"[{task_id}] Graph build failed: {e}")
                build_logger.debug(traceback.format_exc())

                project.status = ProjectStatus.FAILED
                project.error = str(e)
                project.graph_id = None
                project.graph_build_task_id = None
                ProjectManager.save_project(project)

                task_manager.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    message=f"Build failed: {e}",
                    error=str(e)
                )

        # Start background thread
        thread = threading.Thread(target=build_task, daemon=True)
        thread.start()

        return jsonify({
            "success": True,
            "data": {
                "project_id": project_id,
                "task_id": task_id,
                "message": f"Graph build task started. Poll /task/{task_id} for progress."
            }
        })

    except Exception as e:
        logger.error(f"Graph build request failed: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Graph build request failed. Check server logs for details."
        }), 500


# ============== Task query endpoints ==============

@graph_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id: str):
    """Query task status."""
    Validators.validate_task_id(task_id)
    task = TaskManager().get_task(task_id)

    if not task:
        return jsonify({
            "success": False,
            "error": f"Task not found: {task_id}"
        }), 404

    return jsonify({
        "success": True,
        "data": task.to_dict()
    })


@graph_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """List all tasks."""
    tasks = TaskManager().list_tasks()

    return jsonify({
        "success": True,
        "data": tasks,
        "count": len(tasks)
    })


# ============== Graph data endpoints ==============

@graph_bp.route('/data/<graph_id>', methods=['GET'])
def get_graph_data(graph_id: str):
    """Get graph data (nodes and edges)."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY not configured"
            }), 500

        # Guard: reject premature fetches while graph is building or failed
        owner = ProjectManager.find_project_by_graph_id(graph_id)
        if owner and owner.status == ProjectStatus.GRAPH_BUILDING:
            return jsonify({
                "success": False,
                "error": "Graph is still building. Poll the build task for progress.",
                "status": "building",
                "task_id": owner.graph_build_task_id
            }), 202
        if owner and owner.status == ProjectStatus.FAILED:
            return jsonify({
                "success": False,
                "error": "Graph build failed. Please rebuild the graph.",
                "status": "failed"
            }), 422

        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        graph_data = builder.get_graph_data(graph_id)

        return jsonify({
            "success": True,
            "data": graph_data
        })

    except Exception as e:
        from zep_cloud import NotFoundError, BadRequestError
        if isinstance(e, NotFoundError):
            logger.warning(f"Graph not found in Zep: {graph_id}")
            return jsonify({
                "success": False,
                "error": f"Graph not found: {graph_id}"
            }), 404
        if isinstance(e, BadRequestError):
            logger.warning(f"Bad graph request for {graph_id}: {e}")
            return jsonify({
                "success": False,
                "error": f"Invalid graph request: {str(e)[:200]}"
            }), 400
        logger.error(f"Failed to get graph data for {graph_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to get graph data: {type(e).__name__}"
        }), 500


@graph_bp.route('/data/<graph_id>/preview', methods=['GET'])
def get_graph_preview_data(graph_id: str):
    """Get a live graph preview while a graph is still being built."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY not configured"
            }), 500

        owner = ProjectManager.find_project_by_graph_id(graph_id)
        if owner and owner.status == ProjectStatus.FAILED:
            return jsonify({
                "success": False,
                "error": "Graph build failed. Please rebuild the graph.",
                "status": "failed"
            }), 422

        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)

        if owner and owner.status == ProjectStatus.GRAPH_COMPLETED:
            graph_data = builder.get_graph_data(graph_id)
        else:
            graph_data = builder.get_graph_preview(graph_id)
            if owner:
                graph_data["task_id"] = owner.graph_build_task_id

        return jsonify({
            "success": True,
            "data": graph_data
        })

    except Exception as e:
        from zep_cloud import NotFoundError, BadRequestError
        if isinstance(e, NotFoundError):
            logger.warning(f"Graph not found in Zep preview: {graph_id}")
            return jsonify({
                "success": False,
                "error": f"Graph not found: {graph_id}"
            }), 404
        if isinstance(e, BadRequestError):
            logger.warning(f"Bad graph preview request for {graph_id}: {e}")
            return jsonify({
                "success": False,
                "error": f"Invalid graph request: {str(e)[:200]}"
            }), 400
        logger.error(f"Failed to get graph preview for {graph_id}: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": f"Failed to get graph preview: {type(e).__name__}"
        }), 500


@graph_bp.route('/delete/<graph_id>', methods=['DELETE'])
def delete_graph(graph_id: str):
    """Delete a Zep graph."""
    try:
        if not Config.ZEP_API_KEY:
            return jsonify({
                "success": False,
                "error": "ZEP_API_KEY not configured"
            }), 500

        builder = GraphBuilderService(api_key=Config.ZEP_API_KEY)
        builder.delete_graph(graph_id)

        return jsonify({
            "success": True,
            "message": f"Graph deleted: {graph_id}"
        })

    except Exception as e:
        logger.error(f"Failed to delete graph: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to delete graph. Check server logs for details."
        }), 500
