"""
Input validation utilities.
Provides reusable validators for API inputs, config values, and LLM outputs.
Prevents garbage-in-garbage-out issues throughout the pipeline.
"""

import re
import os
from typing import Any


class ValidationError(Exception):
    """Raised when input validation fails."""

    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"{field}: {message}")


class Validators:
    """Reusable input validators for the Phoring pipeline."""

    # --- ID validators ---

    ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')
    PROJECT_ID_PATTERN = re.compile(r'^proj_[a-f0-9]{12}$')
    SIMULATION_ID_PATTERN = re.compile(r'^sim_[a-f0-9]{12}$')
    REPORT_ID_PATTERN = re.compile(r'^report_[a-f0-9]{12}$')
    GRAPH_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{1,128}$')
    TASK_ID_PATTERN = re.compile(r'^task_[a-f0-9]{12}$')

    @classmethod
    def validate_id(cls, value: Any, field_name: str = "id") -> str:
        """Validate a generic ID string."""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(field_name, "must be a non-empty string")
        value = value.strip()
        if not cls.ID_PATTERN.match(value):
            raise ValidationError(field_name, "contains invalid characters (use alphanumeric, _, -)")
        return value

    @classmethod
    def validate_project_id(cls, value: Any) -> str:
        """Validate a project ID format."""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("project_id", "must be a non-empty string")
        value = value.strip()
        if not cls.PROJECT_ID_PATTERN.match(value):
            raise ValidationError("project_id", f"invalid format: {value!r} (expected proj_xxxxxxxxxxxx)")
        return value

    @classmethod
    def validate_simulation_id(cls, value: Any) -> str:
        """Validate a simulation ID format."""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("simulation_id", "must be a non-empty string")
        value = value.strip()
        if not cls.SIMULATION_ID_PATTERN.match(value):
            raise ValidationError("simulation_id", f"invalid format: {value!r} (expected sim_xxxxxxxxxxxx)")
        return value

    @classmethod
    def validate_report_id(cls, value: Any) -> str:
        """Validate a report ID format."""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("report_id", "must be a non-empty string")
        value = value.strip()
        if not cls.REPORT_ID_PATTERN.match(value):
            raise ValidationError("report_id", f"invalid format: {value!r} (expected report_xxxxxxxxxxxx)")
        return value

    @classmethod
    def validate_graph_id(cls, value: Any) -> str:
        """Validate a graph ID (alphanumeric, _, -)."""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("graph_id", "must be a non-empty string")
        value = value.strip()
        if not cls.GRAPH_ID_PATTERN.match(value):
            raise ValidationError("graph_id", "contains invalid characters")
        return value

    @classmethod
    def validate_task_id(cls, value: Any) -> str:
        """Validate a task ID format."""
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("task_id", "must be a non-empty string")
        value = value.strip()
        if not cls.TASK_ID_PATTERN.match(value):
            raise ValidationError("task_id", f"invalid format: {value!r} (expected task_xxxxxxxxxxxx)")
        return value

    # --- File validators ---

    @classmethod
    def validate_filename(cls, filename: str, allowed_extensions: set) -> str:
        """Validate an uploaded filename for safety."""
        if not filename or not isinstance(filename, str):
            raise ValidationError("filename", "must be a non-empty string")
        # Prevent directory traversal
        basename = os.path.basename(filename)
        if basename != filename or '..' in filename or '/' in filename or '\\' in filename:
            raise ValidationError("filename", "invalid filename (no path separators allowed)")
        ext = os.path.splitext(basename)[1].lower().lstrip('.')
        if ext not in allowed_extensions:
            raise ValidationError("filename", f"unsupported file type '.{ext}' (allowed: {allowed_extensions})")
        return basename

