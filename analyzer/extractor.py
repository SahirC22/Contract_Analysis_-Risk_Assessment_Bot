"""
extractor.py

Robust text extraction from PDF, DOCX and TXT files.
Keeps a small amount of layout (paragraph breaks) to help clause segmentation.
"""

from __future__ import annotations
from typing import Union
import io
import logging

import pdfplumber
from docx import Document
import os
import re

logger = logging.getLogger(__name__)


def _extract_from_pdf(file_obj: Union[str, io.BytesIO]) -> str:
    # Ensure pdfplumber receives a seekable file-like object
    if isinstance(file_obj, (bytes, bytearray)):
        file_obj = io.BytesIO(file_obj)

    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    text_parts = []
    with pdfplumber.open(file_obj) as pdf:
        for i, page in enumerate(pdf.pages):
            try:
                page_text = page.extract_text() or ""
            except Exception as e:
                logger.warning("Failed to extract text from page %s: %s", i, e)
                page_text = ""
            text_parts.append(page_text)
    raw = "\n\n".join(part.strip() for part in text_parts if part)
    cleaned = re.sub(r"\n{3,}", "\n\n", raw).strip()
    return cleaned


def _extract_from_docx(file_obj: Union[str, io.BytesIO]) -> str:
    # python-docx needs a file-like object or path
    if isinstance(file_obj, io.BytesIO):
        file_obj.seek(0)
    doc = Document(file_obj)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    raw = "\n\n".join(paras)
    cleaned = re.sub(r"\n{3,}", "\n\n", raw).strip()
    return cleaned


def _extract_from_txt(file_obj: Union[str, io.BytesIO]) -> str:
    if isinstance(file_obj, str):
        with open(file_obj, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    # file-like
    file_obj.seek(0)
    raw = file_obj.read().decode("utf-8", errors="ignore")
    cleaned = re.sub(r"\n{3,}", "\n\n", raw).strip()
    return cleaned


def extract_text(file_obj: Union[str, io.BytesIO], file_mime: str | None = None) -> str:
    """
    Unified entry point.

    Parameters
    ----------
    file_obj : path or BytesIO
    file_mime: optional MIME type from upload (e.g. 'application/pdf')

    Returns
    -------
    str : extracted text
    """
    # Normalize extension safely
    ext = ""
    if isinstance(file_obj, str):
        ext = os.path.splitext(file_obj)[1].lower()
    elif hasattr(file_obj, "name"):
        ext = os.path.splitext(file_obj.name)[1].lower()

    # Detect file format by extension or MIME
    if file_mime == "application/pdf" or ext == ".pdf":
        return _extract_from_pdf(file_obj)

    if file_mime in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
    } or ext in (".docx", ".doc"):
        return _extract_from_docx(file_obj)

    # Default to TXT extraction when type unknown
    try:
        return _extract_from_txt(file_obj)
    except Exception:
        logger.error("Unknown or unsupported file format — cannot extract text.")
        return ""