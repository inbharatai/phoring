"""
Project model and manager.
Handles project lifecycle, file storage, and metadata persistence.
"""

import os
import re
import json
import uuid
import shutil
import tempfile
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field, asdict
from..config import Config


class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    CREATED = "created"
    ONTOLOGY_GENERATED = "ontology_generated"
    GRAPH_BUILDING = "graph_building"
    GRAPH_COMPLETED = "graph_completed"
    FAILED = "failed"


@dataclass
class Project:
    """Project data model."""
    project_id: str
    name: str
    status: ProjectStatus
    created_at: str
    updated_at: str

    # Uploaded file info
    files: List[Dict[str, str]] = field(default_factory=list)  # [{filename, path, size}]
    total_text_length: int = 0

    # Ontology (generated in step 1)
    ontology: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None

    # Graph info (populated after step 2)
    graph_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None

    # Simulation configuration
    simulation_requirement: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Error details
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, ProjectStatus) else self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "files": self.files,
            "total_text_length": self.total_text_length,
            "ontology": self.ontology,
            "analysis_summary": self.analysis_summary,
            "graph_id": self.graph_id,
            "graph_build_task_id": self.graph_build_task_id,
            "simulation_requirement": self.simulation_requirement,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "error": self.error
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        """Create a Project instance from a dictionary."""
        status = data.get('status', 'created')
        if isinstance(status, str):
            status = ProjectStatus(status)

        return cls(
            project_id=data['project_id'],
            name=data.get('name', 'Unnamed Project'),
            status=status,
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', ''),
            files=data.get('files', []),
            total_text_length=data.get('total_text_length', 0),
            ontology=data.get('ontology'),
            analysis_summary=data.get('analysis_summary'),
            graph_id=data.get('graph_id'),
            graph_build_task_id=data.get('graph_build_task_id'),
            simulation_requirement=data.get('simulation_requirement'),
            chunk_size=data.get('chunk_size', 500),
            chunk_overlap=data.get('chunk_overlap', 50),
            error=data.get('error')
        )


class ProjectManager:
    """Project manager with file-based persistence."""

    PROJECTS_DIR = os.path.join(Config.UPLOAD_FOLDER, 'projects')

    # Per-project locks to prevent concurrent read/write corruption
    _locks: Dict[str, threading.Lock] = {}
    _locks_lock = threading.Lock()

    @classmethod
    def _get_lock(cls, project_id: str) -> threading.Lock:
        """Get or create a lock for a specific project."""
        with cls._locks_lock:
            if project_id not in cls._locks:
                cls._locks[project_id] = threading.Lock()
            return cls._locks[project_id]

    @classmethod
    def _ensure_projects_dir(cls):
        """Ensure the projects directory exists."""
        os.makedirs(cls.PROJECTS_DIR, exist_ok=True)

    @classmethod
    def _get_project_dir(cls, project_id: str) -> str:
        """Get the directory path for a project."""
        if not re.match(r'^[a-zA-Z0-9_-]+$', project_id):
            raise ValueError(f"Invalid project_id: {project_id!r}")
        return os.path.join(cls.PROJECTS_DIR, project_id)

    @classmethod
    def _get_project_meta_path(cls, project_id: str) -> str:
        """Get the metadata JSON file path for a project."""
        return os.path.join(cls._get_project_dir(project_id), 'project.json')

    @classmethod
    def _get_project_files_dir(cls, project_id: str) -> str:
        """Get the uploaded files directory for a project."""
        return os.path.join(cls._get_project_dir(project_id), 'files')

    @classmethod
    def _get_project_text_path(cls, project_id: str) -> str:
        """Get the extracted text file path for a project."""
        return os.path.join(cls._get_project_dir(project_id), 'extracted_text.txt')

    @classmethod
    def create_project(cls, name: str = "Unnamed Project") -> Project:
        """Create a new project.

        Args:
            name: Project display name.

        Returns:
            The newly created Project object.
        """
        cls._ensure_projects_dir()

        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        project = Project(
            project_id=project_id,
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now
        )

        # Create project directory structure
        project_dir = cls._get_project_dir(project_id)
        files_dir = cls._get_project_files_dir(project_id)
        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(files_dir, exist_ok=True)

        # Save project metadata
        cls.save_project(project)

        return project

    @classmethod
    def save_project(cls, project: Project) -> None:
        """Atomically save project metadata (write-to-temp then rename)."""
        lock = cls._get_lock(project.project_id)
        with lock:
            project.updated_at = datetime.now().isoformat()
            meta_path = cls._get_project_meta_path(project.project_id)

            dir_path = os.path.dirname(meta_path)
            fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=dir_path)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(project.to_dict(), f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, meta_path)
            except BaseException:
                # Clean up temp file on any failure
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise

    @classmethod
    def get_project(cls, project_id: str) -> Optional[Project]:
        """Get a project by ID.

        Args:
            project_id: Project ID.

        Returns:
            Project object, or None if not found.
        """
        meta_path = cls._get_project_meta_path(project_id)

        if not os.path.exists(meta_path):
            return None

        with open(meta_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return Project.from_dict(data)

    @classmethod
    def list_projects(cls, limit: int = 50) -> List[Project]:
        """List all projects, sorted by creation time (newest first).

        Args:
            limit: Maximum number of projects to return.

        Returns:
            List of Project objects.
        """
        cls._ensure_projects_dir()

        projects = []
        for project_id in os.listdir(cls.PROJECTS_DIR):
            project = cls.get_project(project_id)
            if project:
                projects.append(project)

        projects.sort(key=lambda p: p.created_at, reverse=True)

        return projects[:limit]

    @classmethod
    def find_project_by_graph_id(cls, graph_id: str) -> Optional[Project]:
        """Find the project that owns a given Zep graph_id.

        Scans all project directories (no limit cap).

        Args:
            graph_id: Zep graph UUID.

        Returns:
            Project object, or None if no project owns this graph_id.
        """
        cls._ensure_projects_dir()
        for project_id in os.listdir(cls.PROJECTS_DIR):
            project = cls.get_project(project_id)
            if project and project.graph_id == graph_id:
                return project
        return None

    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        """Delete a project and all its files.

        Args:
            project_id: Project ID.

        Returns:
            True if deleted, False if not found.
        """
        lock = cls._get_lock(project_id)
        with lock:
            project_dir = cls._get_project_dir(project_id)

            if not os.path.exists(project_dir):
                return False

            shutil.rmtree(project_dir)

        # Remove the per-project lock to avoid memory leaks
        with cls._locks_lock:
            cls._locks.pop(project_id, None)

        return True

    @classmethod
    def save_file_to_project(cls, project_id: str, file_storage, original_filename: str) -> Dict[str, str]:
        """Save an uploaded file to the project directory.

        Args:
            project_id: Project ID.
            file_storage: Flask FileStorage object.
            original_filename: Original filename from the upload.

        Returns:
            File info dict with keys: original_filename, saved_filename, path, size.
        """
        files_dir = cls._get_project_files_dir(project_id)
        os.makedirs(files_dir, exist_ok=True)

        # Generate a safe filename
        ext = os.path.splitext(original_filename)[1].lower()
        safe_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(files_dir, safe_filename)

        file_storage.save(file_path)

        file_size = os.path.getsize(file_path)

        return {
            "original_filename": original_filename,
            "saved_filename": safe_filename,
            "path": file_path,
            "size": file_size
        }

    @classmethod
    def save_extracted_text(cls, project_id: str, text: str) -> None:
        """Atomically save extracted text."""
        text_path = cls._get_project_text_path(project_id)
        dir_path = os.path.dirname(text_path)
        fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=dir_path)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(text)
            os.replace(tmp_path, text_path)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    @classmethod
    def get_extracted_text(cls, project_id: str) -> Optional[str]:
        """Get the extracted text for a project."""
        text_path = cls._get_project_text_path(project_id)

        if not os.path.exists(text_path):
            return None

        with open(text_path, 'r', encoding='utf-8') as f:
            return f.read()

    @classmethod
    def get_project_files(cls, project_id: str) -> List[str]:
        """Get all file paths for a project."""
        files_dir = cls._get_project_files_dir(project_id)

        if not os.path.exists(files_dir):
            return []

        return [
            os.path.join(files_dir, f)
            for f in os.listdir(files_dir)
            if os.path.isfile(os.path.join(files_dir, f))
        ]
