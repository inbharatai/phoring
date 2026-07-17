import hashlib
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


file_parser = _load_module(
    "phoring_test_file_parser", "app/utils/file_parser.py"
)
ExtractedPage = file_parser.ExtractedPage
FileParser = file_parser.FileParser
split_text_into_chunks = file_parser.split_text_into_chunks
split_text_into_chunks_with_metadata = (
    file_parser.split_text_into_chunks_with_metadata
)


def test_metadata_chunks_match_legacy_text_output():
    text = "Alpha sentence. Beta sentence. Gamma sentence. Delta sentence."
    legacy = split_text_into_chunks(text, chunk_size=28, overlap=6)
    metadata = split_text_into_chunks_with_metadata(
        text, chunk_size=28, overlap=6, source_id="doc_a"
    )

    assert legacy == [chunk.text for chunk in metadata]
    assert all(chunk.source_id == "doc_a" for chunk in metadata)
    assert all(text[chunk.start_offset:chunk.end_offset] == chunk.text for chunk in metadata)
    assert all(
        chunk.content_sha256
        == hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
        for chunk in metadata
    )
    assert len({chunk.chunk_id for chunk in metadata}) == len(metadata)


def test_chunker_guarantees_forward_progress_with_large_overlap():
    text = "One. Two. Three. Four. Five. Six. Seven. Eight. Nine. Ten."
    chunks = split_text_into_chunks_with_metadata(
        text, chunk_size=20, overlap=9
    )

    assert chunks
    assert len(chunks) < len(text)
    assert all(
        current.start_offset < following.start_offset
        for current, following in zip(chunks, chunks[1:])
    )


def test_chunk_settings_are_rejected_early():
    with pytest.raises(ValueError, match="chunk_size"):
        split_text_into_chunks("text", chunk_size=0)
    with pytest.raises(ValueError, match="overlap"):
        split_text_into_chunks("text", chunk_size=10, overlap=10)
    with pytest.raises(ValueError, match="overlap"):
        split_text_into_chunks("text", chunk_size=10, overlap=-1)


def test_plain_text_extract_pages_preserves_source_text(tmp_path):
    source = tmp_path / "evidence.txt"
    source.write_text("Evidence with café and Assamese context.", encoding="utf-8")

    pages = FileParser.extract_pages(str(source))
    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert pages[0].extraction_method == "text_decode"
    assert pages[0].text == source.read_text(encoding="utf-8")
    assert pages[0].confidence == 1.0


def test_extracted_page_validation_prevents_invalid_metadata():
    with pytest.raises(ValueError, match="page_number"):
        ExtractedPage(0, "text", "native", 1.0)
    with pytest.raises(ValueError, match="confidence"):
        ExtractedPage(1, "text", "native", 1.2)
