# ============================================================
# PDF Loader — Text-Based and Scanned PDFs
#
# PDFs come in two flavours:
#   1. Text-based PDFs: The text is stored as actual characters inside the
#      file. Tools like PyMuPDF can extract it directly. Fast and accurate.
#   2. Scanned PDFs: These are images of pages. There is no text layer.
#      PyMuPDF will return an empty string for each page. We detect this
#      and fall back to the vision LLM approach (same as the image loader).
#
# HOW PDF EXTRACTION WORKS (ANALOGY):
# Think of a PDF as a filing cabinet. Text-based PDFs store documents as
# Word files in the cabinet — you can open and read them directly.
# Scanned PDFs store photographs of the documents — you need to look at
# the picture and type out what you see (= OCR or vision LLM).
# ============================================================

import logging
from pathlib import Path

from src.ingestion.document import Document

logger = logging.getLogger(__name__)

# Minimum characters per page before we consider extraction "failed"
# and fall back to vision. Some pages have headers/footers but no real text.
MIN_TEXT_CHARS = 50


def load_pdf(file_path: Path) -> list[Document]:
    """
    Load a PDF file, returning one Document per page.

    For each page:
    - If text extraction succeeds (>= MIN_TEXT_CHARS), use the extracted text.
    - If extraction returns little or no text, the page is likely scanned.
      Falls back to vision LLM (via the image loader's vision call).

    Args:
        file_path: Path to the .pdf file.

    Returns:
        List of Documents, one per page with text content.
    """
    try:
        import fitz  # PyMuPDF — install: pip install pymupdf
    except ImportError:
        raise ImportError(
            "PyMuPDF is required for PDF loading. "
            "Install with: pip install pymupdf"
        )

    documents: list[Document] = []

    try:
        pdf = fitz.open(str(file_path))
        logger.info("Opened PDF %s (%d pages)", file_path.name, pdf.page_count)

        for page_num in range(pdf.page_count):
            page = pdf[page_num]
            text = page.get_text().strip()

            if len(text) >= MIN_TEXT_CHARS:
                # Text-based page — use extracted text directly
                doc = Document(
                    text=text,
                    metadata={
                        "source": file_path.name,
                        "source_path": str(file_path),
                        "type": "pdf",
                        "page": page_num + 1,       # 1-indexed for humans
                        "total_pages": pdf.page_count,
                        "extraction_method": "pymupdf",
                    },
                )
                documents.append(doc)
                logger.debug(
                    "  Page %d: extracted %d chars via text layer",
                    page_num + 1, len(text)
                )

            else:
                # Scanned page — fall back to vision LLM
                logger.warning(
                    "  Page %d of %s: text layer is empty/garbled (%d chars). "
                    "Falling back to vision LLM.",
                    page_num + 1, file_path.name, len(text)
                )
                vision_docs = _load_scanned_page_with_vision(
                    pdf, page_num, file_path
                )
                documents.extend(vision_docs)

        pdf.close()

    except Exception as exc:
        logger.error("Failed to load PDF %s: %s", file_path.name, exc)
        raise

    logger.info(
        "Loaded %d pages from %s", len(documents), file_path.name
    )
    return documents


def _load_scanned_page_with_vision(
    pdf,
    page_num: int,
    file_path: Path,
) -> list[Document]:
    """
    Render a PDF page to a PNG image and pass it to the vision LLM for OCR.

    This is the same technique as load_image_with_vision(), but applied to
    a rendered page rather than a standalone image file.

    Args:
        pdf:       Open PyMuPDF document object.
        page_num:  0-based page index.
        file_path: Original PDF path (for metadata).

    Returns:
        List of one Document with vision-extracted text (or empty if vision fails).
    """
    try:
        import tempfile
        import os
        from src.ingestion.loaders.image_loader import _describe_image_bytes

        page = pdf[page_num]
        # Render at 2x resolution (matrix scale=2) for better OCR quality
        mat = __import__("fitz").Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        image_bytes = pix.tobytes("png")

        extracted_text = _describe_image_bytes(image_bytes, "png")

        if not extracted_text:
            logger.warning(
                "Vision LLM returned no text for page %d of %s",
                page_num + 1, file_path.name
            )
            return []

        return [
            Document(
                text=extracted_text,
                metadata={
                    "source": file_path.name,
                    "source_path": str(file_path),
                    "type": "pdf",
                    "page": page_num + 1,
                    "extraction_method": "vision_llm",
                },
            )
        ]

    except Exception as exc:
        logger.error(
            "Vision fallback failed for page %d of %s: %s",
            page_num + 1, file_path.name, exc
        )
        return []
