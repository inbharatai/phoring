"""
File parser utility.
Extracts text from PDF, Markdown, and TXT files.
"""

import os
from pathlib import Path
from typing import List, Optional


def _read_text_with_fallback(file_path: str) -> str:
    """Read a text file with automatic encoding detection.

    Fallback order:
    1. UTF-8
    2. charset_normalizer detection
    3. chardet detection
    4. UTF-8 with error replacement

    Args:
        file_path: Path to the file.

    Returns:
        Decoded text content.
    """
    data = Path(file_path).read_bytes()

    # Try UTF-8 first
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass

    # Try charset_normalizer for encoding detection
    encoding = None
    try:
        from charset_normalizer import from_bytes
        best = from_bytes(data).best()
        if best and best.encoding:
            encoding = best.encoding
    except Exception:
        pass

    # Fallback to chardet
    if not encoding:
        try:
            import chardet
            result = chardet.detect(data)
            encoding = result.get('encoding') if result else None
        except Exception:
            pass

    # Last resort: UTF-8 with replacement
    if not encoding:
        encoding = 'utf-8'

    return data.decode(encoding, errors='replace')


class FileParser:
    """File parser utility."""

    SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.markdown', '.txt'}

    @classmethod
    def extract_text(cls, file_path: str) -> str:
        """Extract text content from a file.

        Args:
            file_path: Path to the file.

        Returns:
            Extracted text content.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format: {suffix}")

        if suffix == '.pdf':
            return cls._extract_from_pdf(file_path)
        elif suffix in {'.md', '.markdown'}:
            return cls._extract_from_md(file_path)
        elif suffix == '.txt':
            return cls._extract_from_txt(file_path)

        raise ValueError(f"Cannot process file format: {suffix}")

    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """Extract text from a PDF file."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise ImportError("PyMuPDF is required: pip install PyMuPDF")

        text_parts = []
        with fitz.open(file_path) as doc:
            for page in doc:
                text = page.get_text()
                if text.strip():
                    text_parts.append(text)

        # If no text was extracted (scanned/image-based PDF), use OpenAI Vision OCR
        if not text_parts:
            text_parts = FileParser._ocr_pdf_with_vision(file_path)

        return "\n\n".join(text_parts)

    @staticmethod
    def _ocr_pdf_with_vision(file_path: str) -> list:
        """Extract text from a scanned (image-based) PDF using OpenAI Vision API.

        Each page is rendered as an image and sent to the vision model.
        """
        import fitz
        import base64
        from ..config import Config

        try:
            from openai import OpenAI
            client = OpenAI(api_key=Config.LLM_API_KEY, base_url=Config.LLM_BASE_URL)
        except Exception as e:
            raise RuntimeError(f"Cannot initialise OpenAI client for OCR: {e}")

        text_parts = []
        with fitz.open(file_path) as doc:
            for page_num, page in enumerate(doc):
                # Render page at 150 DPI as PNG
                mat = fitz.Matrix(150 / 72, 150 / 72)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                b64_img = base64.b64encode(img_bytes).decode("utf-8")

                try:
                    response = client.chat.completions.create(
                        model=Config.LLM_MODEL_NAME,
                        messages=[
                            {
                                "role": "user",
                                "content": [
                                    {
                                        "type": "text",
                                        "text": (
                                            "Please extract ALL text from this document page as accurately as possible. "
                                            "Preserve the original layout structure (headings, paragraphs, tables, lists). "
                                            "Output only the extracted text with no commentary."
                                        ),
                                    },
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/png;base64,{b64_img}",
                                            "detail": "high",
                                        },
                                    },
                                ],
                            }
                        ],
                        max_tokens=4096,
                    )
                    page_text = response.choices[0].message.content or ""
                    if page_text.strip():
                        text_parts.append(f"[Page {page_num + 1}]\n{page_text.strip()}")
                except Exception as e:
                    text_parts.append(f"[Page {page_num + 1}: OCR failed -- {e}]")

        return text_parts

    @staticmethod
    def _extract_from_md(file_path: str) -> str:
        """Extract text from a Markdown file with automatic encoding detection."""
        return _read_text_with_fallback(file_path)

    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """Extract text from a plain text file with automatic encoding detection."""
        return _read_text_with_fallback(file_path)

    @classmethod
    def extract_from_multiple(cls, file_paths: List[str]) -> str:
        """Extract and merge text from multiple files.

        Args:
            file_paths: List of file paths.

        Returns:
            Merged text content.
        """
        all_texts = []

        for i, file_path in enumerate(file_paths, 1):
            try:
                text = cls.extract_text(file_path)
                filename = Path(file_path).name
                all_texts.append(f"=== Document {i}: {filename} ===\n{text}")
            except Exception as e:
                all_texts.append(f"=== Document {i}: {file_path} (extraction failed: {str(e)}) ===")

        return "\n\n".join(all_texts)


def split_text_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 50
) -> List[str]:
    """Split text into overlapping chunks.

    Args:
        text: Input text.
        chunk_size: Maximum characters per chunk.
        overlap: Overlap characters between chunks.

    Returns:
        List of text chunks.
    """
    if chunk_size < 1:
        raise ValueError("chunk_size must be >= 1")
    if overlap < 0:
        raise ValueError("overlap must be >= 0")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size")

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < len(text):
            for sep in ['.', '!', '?', '.\n', '!\n', '?\n', '\n\n', '. ', '! ', '? ']:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size * 0.3:
                    end = start + last_sep + len(sep)
                    break

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = end - overlap if end < len(text) else len(text)

    return chunks
