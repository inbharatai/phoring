import json

from app.models.run_manifest import RunManifest, SourceFingerprint, fingerprint_files


def _manifest(sources=None):
    return RunManifest(
        run_id="run_001",
        project_id="proj_123456789abc",
        simulation_id="sim_123456789abc",
        graph_id="graph_001",
        base_seed=20260717,
        manifest_version="1",
        prompt_version="2026-07-17",
        git_sha="abc123",
        created_at="2026-07-17T12:00:00+00:00",
        models={"primary": "gemini-2.5-pro"},
        settings={"event_mode": "observed_only"},
        sources=sources or [],
    )


def test_manifest_hash_is_stable_for_same_content():
    first = _manifest()
    second = _manifest()
    assert first.canonical_json() == second.canonical_json()
    assert first.manifest_hash == second.manifest_hash


def test_manifest_hash_changes_when_material_input_changes():
    first = _manifest()
    second = RunManifest(**{**first.to_dict(), "base_seed": 99})
    assert first.manifest_hash != second.manifest_hash


def test_source_fingerprint_and_atomic_save(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("Phoring evidence", encoding="utf-8")

    fingerprints = fingerprint_files([source])
    assert len(fingerprints) == 1
    assert fingerprints[0].filename == "source.txt"
    assert fingerprints[0].size_bytes == len("Phoring evidence".encode("utf-8"))
    assert len(fingerprints[0].sha256) == 64

    manifest = _manifest(sources=fingerprints)
    output = tmp_path / "run_manifest.json"
    manifest.save_atomic(output)

    saved = json.loads(output.read_text(encoding="utf-8"))
    assert saved["run_id"] == manifest.run_id
    assert saved["sources"][0]["sha256"] == fingerprints[0].sha256
    assert saved["manifest_hash"] == manifest.manifest_hash
    assert not list(tmp_path.glob("*.tmp"))


def test_source_fingerprint_from_file(tmp_path):
    source = tmp_path / "sample.md"
    source.write_bytes(b"same bytes")
    first = SourceFingerprint.from_file(source, "source_a")
    second = SourceFingerprint.from_file(source, "source_a")
    assert first == second
