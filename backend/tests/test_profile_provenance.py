import importlib.util
import sys
from pathlib import Path

import pytest


def _load_module(name: str, relative_path: str):
    module_path = Path(__file__).parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(name, module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


provenance = _load_module(
    "phoring_test_profile_provenance", "app/models/profile_provenance.py"
)
ProfileProvenance = provenance.ProfileProvenance
ProvenanceField = provenance.ProvenanceField
ProvenanceStatus = provenance.ProvenanceStatus


def test_verified_fields_require_evidence():
    with pytest.raises(ValueError, match="evidence_id"):
        ProvenanceField(
            value="Assam",
            status=ProvenanceStatus.VERIFIED,
            confidence=0.99,
        )


def test_unknown_field_cannot_carry_a_fabricated_value():
    with pytest.raises(ValueError, match="value=None"):
        ProvenanceField(
            value="India",
            status=ProvenanceStatus.UNKNOWN,
            confidence=0.0,
        )


def test_confidence_is_bounded():
    with pytest.raises(ValueError, match="between 0.0 and 1.0"):
        ProvenanceField(
            value="cautious",
            status=ProvenanceStatus.INFERRED,
            confidence=1.1,
        )


def test_profile_serialization_separates_verified_and_assumed_values():
    profile = ProfileProvenance(
        source_entity_uuid="entity-1",
        source_entity_name="Example Institution",
        source_entity_type="Organization",
    )
    profile.set_field(
        "country",
        ProvenanceField(
            value="India",
            status=ProvenanceStatus.VERIFIED,
            evidence_ids=["doc_1_page_2"],
            confidence=0.98,
            method="document extraction",
        ),
    )
    profile.set_field(
        "posting_propensity",
        ProvenanceField(
            value=0.35,
            status=ProvenanceStatus.ASSUMED,
            confidence=0.2,
            method="simulation default",
        ),
    )
    profile.set_field("follower_count", ProvenanceField.unknown())

    output = profile.to_dict()
    assert profile.get_value("country") == "India"
    assert profile.get_value("follower_count", 0) == 0
    assert output["fields"]["country"]["status"] == "verified"
    assert output["fields"]["follower_count"]["value"] is None
    assert output["unsupported_assumptions"] == ["posting_propensity"]


def test_empty_field_name_is_rejected():
    profile = ProfileProvenance("entity-1", "Example", "Person")
    with pytest.raises(ValueError, match="cannot be empty"):
        profile.set_field("  ", ProvenanceField.unknown())
