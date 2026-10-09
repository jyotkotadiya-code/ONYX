from pathlib import Path
from typing import Any
import fitz  # PyMuPDF
import pdfplumber
from backend.core.logging_config import error_logger, ingestion_logger
from backend.core.models import ParsedBlock
from backend.ingestion.ocr import ocr_engine

MIN_NATIVE_CHARS_PER_PAGE = 25


def _extract_spatially_aligned_text(page: fitz.Page) -> str:
    """
    Reconstruct horizontal reading lines from PDF word coordinates (Y, X).
    Prevents vertical column scrambling in complex statement-of-marks, invoices, and forms,
    while filtering out giant diagonal watermark words (height > 45pt).
    """
    words = page.get_text("words")
    if not words:
        return page.get_text("text").strip()

    filtered_words = []
    for w in words:
        x0, y0, x1, y1, txt = w[:5]
        height = y1 - y0
        # Filter out huge background watermark text (e.g. giant diagonal "Web Result")
        if height > 45.0 and len(words) > 20:
            continue
        filtered_words.append((x0, y0, x1, y1, str(txt).strip()))

    if not filtered_words:
        return page.get_text("text").strip()

    # Sort primarily by top Y coordinate, then X
    filtered_words.sort(key=lambda item: (item[1], item[0]))

    rows: list[dict[str, Any]] = []
    for x0, y0, x1, y1, txt in filtered_words:
        if not txt:
            continue
        # Group words that sit on the same horizontal line (within 5.5pt vertical tolerance)
        placed = False
        for r in reversed(rows[-4:]):
            if abs(r["y"] - y0) <= 5.5:
                r["items"].append((x0, x1, txt))
                placed = True
                break
        if not placed:
            rows.append({"y": y0, "items": [(x0, x1, txt)]})

    # Sort rows top-to-bottom and merge wrapped sub-lines (such as wrapped course titles)
    rows.sort(key=lambda r: r["y"])
    lines: list[str] = []
    for idx, r in enumerate(rows):
        sorted_items = sorted(r["items"], key=lambda it: it[0])
        # Group words into column cells when horizontal gap > 8pt
        cells: list[str] = []
        current_cell_words: list[str] = []
        last_x1: float | None = None
        for x0, x1, t in sorted_items:
            if last_x1 is not None and (x0 - last_x1) > 8.0:
                cells.append(" ".join(current_cell_words))
                current_cell_words = [t]
            else:
                current_cell_words.append(t)
            last_x1 = x1
        if current_cell_words:
            cells.append(" ".join(current_cell_words))

        line_str = " | ".join(cells) if len(cells) > 1 else (cells[0] if cells else "")

        # If a short 1-2 word continuation line sits immediately below a multi-column table row (delta_y <= 14pt),
        # merge it into the course title cell of the previous row.
        if (
            lines
            and len(cells) == 1
            and idx > 0
            and (r["y"] - rows[idx - 1]["y"]) <= 14.0
            and len(rows[idx - 1]["items"]) >= 6
        ):
            prev_parts = lines[-1].split(" | ")
            if len(prev_parts) >= 3:
                prev_parts[2] = f"{prev_parts[2]} {line_str}".strip()
                lines[-1] = " | ".join(prev_parts)
            else:
                lines[-1] = f"{lines[-1]} {line_str}"
        else:
            lines.append(line_str)

    return "\n".join(lines).strip()


def _format_table_as_markdown(table: list[list[Any]]) -> str:
    if not table:
        return ""
    cleaned_rows = []
    for row in table:
        if not row:
            continue
        cells = [str(c).strip().replace("\n", " ") if c is not None else "" for c in row]
        # Skip merged cells where pdfplumber collapsed 4+ multi-line rows into a single cell
        if any(str(c).count("\n") >= 4 for c in row if c is not None):
            continue
        if any(cells):
            cleaned_rows.append(cells)
    if len(cleaned_rows) < 2:
        return ""

    header = cleaned_rows[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * len(header)) + " |",
    ]
    for row in cleaned_rows[1:]:
        padded = row + [""] * max(0, len(header) - len(row))
        lines.append("| " + " | ".join(padded[: len(header)]) + " |")
    return "\n".join(lines)


def parse_pdf(file_path: Path, progress_callback=None) -> tuple[list[ParsedBlock], dict[str, Any]]:
    """
    Parse normal and scanned PDFs locally.
    1. Reconstructs spatially aligned horizontal rows via PyMuPDF word coordinates and extracts clean tables via pdfplumber.
    2. If a page has fewer than MIN_NATIVE_CHARS_PER_PAGE characters, renders the page to PNG bytes
       and runs local OCR automatically.
    """
    blocks: list[ParsedBlock] = []
    ocr_pages_triggered = 0
    total_tables = 0

    doc = fitz.open(str(file_path))
    page_count = len(doc)
    pdf_meta = doc.metadata or {}

    plumber_pdf = None
    try:
        plumber_pdf = pdfplumber.open(str(file_path))
    except Exception as e:
        error_logger.error(f"pdfplumber could not open {file_path.name}: {e}")

    try:
        for page_idx in range(page_count):
            page_num = page_idx + 1
            page = doc[page_idx]
            spatial_text = _extract_spatially_aligned_text(page)

            table_md_list: list[str] = []
            if plumber_pdf and page_idx < len(plumber_pdf.pages):
                try:
                    raw_tables = plumber_pdf.pages[page_idx].extract_tables() or []
                    for t in raw_tables:
                        md = _format_table_as_markdown(t)
                        if md:
                            table_md_list.append(md)
                            total_tables += 1
                except Exception:
                    pass

            section_heading = f"Page {page_num}"
            try:
                page_dict = page.get_text("dict")
                max_size = 0.0
                for b in page_dict.get("blocks", []):
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            txt = span.get("text", "").strip()
                            sz = float(span.get("size", 0.0))
                            if 3 < len(txt) < 100 and 13.0 <= sz <= 28.0 and sz > max_size:
                                max_size = sz
                                section_heading = txt
            except Exception:
                pass

            if len(spatial_text) >= MIN_NATIVE_CHARS_PER_PAGE:
                combined_text = spatial_text
                if table_md_list:
                    combined_text += "\n\n### Extracted Structured Tables\n" + "\n\n".join(table_md_list)
                blocks.append(
                    ParsedBlock(
                        text=combined_text,
                        modality="pdf",
                        page_number=page_num,
                        section_title=section_heading,
                        extra_metadata={"ocr_used": False},
                    )
                )
            else:
                if progress_callback:
                    progress_callback("OCR", int(30 + (page_num / max(1, page_count)) * 30))
                ocr_pages_triggered += 1
                pix = page.get_pixmap(dpi=200)
                png_bytes = pix.tobytes("png")
                ocr_res = ocr_engine.extract_text_from_image(png_bytes, page_number=page_num)
                ocr_text = ocr_res.get("text", "").strip()
                if table_md_list:
                    ocr_text += "\n\n### Extracted Structured Tables\n" + "\n\n".join(table_md_list)

                if ocr_text:
                    blocks.append(
                        ParsedBlock(
                            text=ocr_text,
                            modality="scanned_pdf",
                            page_number=page_num,
                            section_title=f"Scanned Page {page_num}",
                            confidence=ocr_res.get("confidence", 0.0),
                            extra_metadata={
                                "ocr_used": True,
                                "ocr_engine": ocr_res.get("engine", "local"),
                            },
                        )
                    )
                elif spatial_text:
                    blocks.append(
                        ParsedBlock(
                            text=spatial_text,
                            modality="pdf",
                            page_number=page_num,
                            section_title=section_heading,
                            extra_metadata={"ocr_used": True},
                        )
                    )
    finally:
        doc.close()
        if plumber_pdf:
            plumber_pdf.close()

    doc_metadata = {
        "page_count": page_count,
        "ocr_pages_triggered": ocr_pages_triggered,
        "is_scanned": ocr_pages_triggered > 0,
        "tables_extracted": total_tables,
        "title": pdf_meta.get("title") or file_path.stem,
        "author": pdf_meta.get("author") or "",
    }
    ingestion_logger.info(
        f"Parsed PDF '{file_path.name}': {page_count} pages ({ocr_pages_triggered} OCR pages, {total_tables} tables)"
    )
    return blocks, doc_metadata
