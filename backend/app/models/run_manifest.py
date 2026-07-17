"""Versioned, immutable run metadata for reproducible Phoring execution."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class SourceFingerprint:
    """Stable identity for one input document or frozen evidence snapshot."""

    source_id: str
    sha256: str
    size_bytes: int
    source_type: str = "document"
    filename: Optional[str] = None

    @classmethod
    def from_file(
        cls,
        path: str | os.PathLike[str],
        source_id: str,
        source_type: str = "document",
    ) -> "SourceFingerprint":
        file_path = Path(path)
        digest = hashlib.sha256()
        size = 0
        with file_path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
        return cls(
            source_id=source_id,
            sha256=digest.hexdigest(),
            size_bytes=size,
            source_type=source_type,
            filename=file_path.name,
        )


@dataclass(frozen=True)
class RunManifest:
    """Frozen description of the inputs and software choices for one run."""

    run_id: str
    project_id: str
    simulation_id: str
    graph_id: str
    base_seed: int
    manifest_version: str
    prompt_version: str
    git_sha: str = "unknown"
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    models: Dict[str, str] = field(default_factory=dict)
    settings: Dict[str, Any] = field(default_factory=dict)
    sources: List[SourceFingerprint] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def canonical_json(self) -> str:
        """Return stable JSON suitable for hashing, comparison and audit."""
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @property
    def manifest_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def save_atomic(self, path: str | os.PathLike[str]) -> None:
        """Persist the manifest without exposing a partially written file."""
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                payload = self.to_dict()
                payload["manifest_hash"] = self.manifest_hash
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, target)
        except BaseException:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise


def fingerprint_files(
    paths: Iterable[str | os.PathLike[str]],
    source_type: str = "document",
) -> List[SourceFingerprint]:
    """Fingerprint files in input order using deterministic source IDs."""
    fingerprints: List[SourceFingerprint] = []
    for index, path in enumerate(paths, start=1):
        fingerprints.append(
            SourceFingerprint.from_file(
                path,
                source_id=f"source_{index:04d}",
                source_type=source_type,
            )
        )
    return fingerprints
