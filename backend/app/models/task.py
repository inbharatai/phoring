"""
Task status manager.
Tracks long-running asynchronous tasks (e.g. graph builds, report generation).
"""

import json
import os
import tempfile
import uuid
import threading
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


class TaskStatus(str, Enum):
    """Task lifecycle status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Data model for a single task."""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0  # 0-100 percentage
    message: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    progress_detail: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class TaskManager:
    """Thread-safe singleton task manager.

    Tracks task status across background threads.
    """

    _instance = None
    _lock = threading.Lock()

    # Persistent task storage directory
    TASKS_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/tasks'
    )

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    os.makedirs(cls.TASKS_DIR, exist_ok=True)
                    cls._instance._tasks: Dict[str, Task] = {}
                    cls._instance._task_lock = threading.Lock()
        return cls._instance

    def _task_file_path(self, task_id: str) -> str:
        """Return the JSON file path for a given task ID."""
        return os.path.join(self.TASKS_DIR, f"{task_id}.json")

    def _save_task_to_disk(self, task: Task):
        """Atomically persist a task to disk (write tmp then os.replace)."""
        state_file = self._task_file_path(task.task_id)
        fd, tmp_path = tempfile.mkstemp(suffix='.tmp', dir=self.TASKS_DIR)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(task.to_dict(), f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, state_file)
        except BaseException:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _load_task_from_disk(self, task_id: str) -> Optional[Task]:
        """Load a single task from its JSON file on disk, if it exists."""
        state_file = self._task_file_path(task_id)
        if not os.path.exists(state_file):
            return None
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            task = Task(
                task_id=data["task_id"],
                task_type=data["task_type"],
                status=TaskStatus(data["status"]),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                progress=data.get("progress", 0),
                message=data.get("message", ""),
                result=data.get("result"),
                error=data.get("error"),
                metadata=data.get("metadata", {}),
                progress_detail=data.get("progress_detail", {}),
            )
            self._tasks[task_id] = task
            return task
        except (json.JSONDecodeError, KeyError, ValueError):
            return None

    def create_task(self, task_type: str, metadata: Optional[Dict] = None) -> str:
        """Create a new task.

        Args:
            task_type: Type of the task (e.g. "graph_build", "report_generate").
            metadata: Additional metadata for the task.

        Returns:
            The generated task ID.
        """
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = datetime.now()

        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {}
        )

        with self._task_lock:
            self._tasks[task_id] = task
            self._save_task_to_disk(task)

        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID. Falls back to disk if not in memory."""
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is not None:
                return task
            return self._load_task_from_disk(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        progress_detail: Optional[Dict] = None
    ):
        """Update task fields.

        Args:
            task_id: Task ID.
            status: New status.
            progress: Progress percentage (0-100).
            message: Status message.
            result: Task result data.
            error: Error information.
            progress_detail: Detailed progress breakdown.
        """
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is None:
                task = self._load_task_from_disk(task_id)
            if task:
                task.updated_at = datetime.now()
                if status is not None:
                    task.status = status
                if progress is not None:
                    task.progress = progress
                if message is not None:
                    task.message = message
                if result is not None:
                    task.result = result
                if error is not None:
                    task.error = error
                if progress_detail is not None:
                    task.progress_detail = progress_detail
                self._save_task_to_disk(task)

    def complete_task(self, task_id: str, result: Dict):
        """Mark a task as completed."""
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="Task completed",
            result=result
        )

    def fail_task(self, task_id: str, error: str):
        """Mark a task as failed."""
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="Task failed",
            error=error
        )

    def list_tasks(self, task_type: Optional[str] = None) -> list:
        """List all tasks, optionally filtered by type."""
        with self._task_lock:
            # Load any on-disk tasks not yet in memory
            if os.path.exists(self.TASKS_DIR):
                for filename in os.listdir(self.TASKS_DIR):
                    if not filename.endswith('.json'):
                        continue
                    tid = filename[:-5]  # strip .json
                    if tid not in self._tasks:
                        self._load_task_from_disk(tid)

            tasks = list(self._tasks.values())
            if task_type:
                tasks = [t for t in tasks if t.task_type == task_type]
            return [t.to_dict() for t in sorted(tasks, key=lambda x: x.created_at, reverse=True)]

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove completed/failed tasks older than the specified age."""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(hours=max_age_hours)

        with self._task_lock:
            # Load any on-disk tasks not yet in memory so they can be cleaned up too
            if os.path.exists(self.TASKS_DIR):
                for filename in os.listdir(self.TASKS_DIR):
                    if not filename.endswith('.json'):
                        continue
                    tid = filename[:-5]
                    if tid not in self._tasks:
                        self._load_task_from_disk(tid)

            old_ids = [
                tid for tid, task in self._tasks.items()
                if task.created_at < cutoff and task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
            ]
            for tid in old_ids:
                del self._tasks[tid]
                state_file = self._task_file_path(tid)
                if os.path.exists(state_file):
                    os.unlink(state_file)
