"""Load input documents (PDFs and images) into a uniform list of pages.

Each page is a tuple `(bytes, mime_type)`. PDFs are split into one entry per
page; image files become one entry each. The mime type tells the extractor
which Anthropic content block to build (`document` for PDFs, `image` for
images — Claude handles both natively, including OCR on scanned pages).
"""
from __future__ import annotations

import io
import mimetypes
from pathlib import Path

from pypdf import PdfReader, PdfWriter


# Image formats Claude's vision API accepts directly.
NATIVE_IMAGE_MIME = {
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
}

SUPPORTED_EXTENSIONS = {".pdf", *NATIVE_IMAGE_MIME.keys()}


def split_pdf_to_pages(pdf_path: Path) -> list[bytes]:
    """Split a multi-page PDF into single-page PDFs (as bytes)."""
    reader = PdfReader(str(pdf_path))
    pages: list[bytes] = []
    for page in reader.pages:
        writer = PdfWriter()
        writer.add_page(page)
        buf = io.BytesIO()
        writer.write(buf)
        pages.append(buf.getvalue())
    return pages


def load_pages(paths: list[Path]) -> list[tuple[bytes, str]]:
    """Turn a mixed list of PDF/image paths into uniform `(bytes, mime_type)` pages.

    Skips unsupported file types silently — the caller should pre-filter or
    surface this in the UI. Raises FileNotFoundError if a path doesn't exist.
    """
    pages: list[tuple[bytes, str]] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(path)
        ext = path.suffix.lower()
        if ext == ".pdf":
            for page_bytes in split_pdf_to_pages(path):
                pages.append((page_bytes, "application/pdf"))
        elif ext in NATIVE_IMAGE_MIME:
            pages.append((path.read_bytes(), NATIVE_IMAGE_MIME[ext]))
        # else: silently skip — UI prevents this
    return pages
