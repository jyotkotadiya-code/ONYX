from pathlib import Path
from typing import Any
from PIL import Image, ExifTags
from backend.core.logging_config import ingestion_logger
from backend.core.models import ParsedBlock
from backend.core.security import compute_sha256_file
from backend.ingestion.ocr import ocr_engine


def parse_image(file_path: Path, progress_callback=None) -> tuple[list[ParsedBlock], dict[str, Any]]:
    """
    Ingest PNG, JPG, JPEG, WEBP, BMP, TIFF images.
    Extracts dimensions, format, EXIF metadata, and runs local OCR to extract embedded text.
    """
    if progress_callback:
        progress_callback("OCR", 40)

    img_hash = compute_sha256_file(file_path)
    with Image.open(file_path) as img:
        width, height = img.size
        img_format = img.format or file_path.suffix.lstrip(".").upper()
        mode = img.mode

        exif_info = {}
        try:
            raw_exif = img.getexif()
            if raw_exif:
                for k, v in raw_exif.items():
                    tag_name = ExifTags.TAGS.get(k, str(k))
                    if isinstance(v, (str, int, float)):
                        exif_info[str(tag_name)] = v
        except Exception:
            pass

    ocr_result = ocr_engine.extract_text_from_image(file_path, page_number=1)
    ocr_text = ocr_result.get("text", "").strip()
    confidence = ocr_result.get("confidence", 0.0)

    # Build a rich searchable text representation combining OCR text and visual metadata
    lines = [
        f"Image File: {file_path.name}",
        f"Resolution: {width}x{height} ({img_format}, {mode})",
    ]
    if ocr_text:
        lines.append(f"\nExtracted Text (OCR):\n{ocr_text}")
    else:
        lines.append("\n[Visual image without detected embedded text]")

    content_text = "\n".join(lines).strip()

    image_metadata = {
        "filename": file_path.name,
        "width": width,
        "height": height,
        "format": img_format,
        "mode": mode,
        "ocr_text": ocr_text,
        "ocr_confidence": confidence,
        "ocr_engine": ocr_result.get("engine", "local"),
        "path": str(file_path),
        "hash": img_hash,
        "page_count": 1,
    }

    block = ParsedBlock(
        text=content_text,
        modality="image",
        page_number=1,
        section_title=f"Image: {file_path.name} ({width}x{height})",
        confidence=confidence,
        extra_metadata={
            "width": width,
            "height": height,
            "ocr_engine": ocr_result.get("engine", "local"),
            "has_ocr_text": bool(ocr_text),
        },
    )
    ingestion_logger.info(
        f"Parsed Image '{file_path.name}' ({width}x{height}), OCR chars={len(ocr_text)}, conf={confidence}"
    )
    return [block], image_metadata
