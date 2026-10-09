import os
from pathlib import Path
from typing import Any, Optional
from PIL import Image
from backend.core.config import settings
from backend.core.logging_config import error_logger, ingestion_logger


class LocalOCREngine:
    """
    100% Local CPU-friendly OCR Engine.
    Supports RapidOCR (ONNX Runtime CPU, zero external system binary required)
    and Tesseract OCR (`pytesseract`) when installed on Windows.
    Never sends images or pages to any cloud OCR API.
    """

    def __init__(self) -> None:
        self._rapid_ocr = None
        self._tesseract_available: Optional[bool] = None

    def is_tesseract_available(self) -> bool:
        if self._tesseract_available is not None:
            return self._tesseract_available
        try:
            import pytesseract

            if os.path.exists(settings.TESSERACT_CMD):
                pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
            _ = pytesseract.get_tesseract_version()
            self._tesseract_available = True
        except Exception:
            self._tesseract_available = False
        return self._tesseract_available

    def _get_rapid_ocr(self):
        if self._rapid_ocr is None:
            from rapidocr_onnxruntime import RapidOCR

            self._rapid_ocr = RapidOCR()
        return self._rapid_ocr

    def get_status(self) -> dict[str, Any]:
        if not settings.OCR_ENABLED:
            return {"status": "disabled", "engine": "none"}
        tess_ok = self.is_tesseract_available()
        rapid_ok = False
        try:
            import rapidocr_onnxruntime  # noqa: F401

            rapid_ok = True
        except Exception:
            rapid_ok = False

        if tess_ok or rapid_ok:
            engines = []
            if rapid_ok:
                engines.append("RapidOCR (ONNX CPU)")
            if tess_ok:
                engines.append("Tesseract OCR")
            return {
                "status": "available",
                "engine": " + ".join(engines),
                "tesseract_installed": tess_ok,
                "rapidocr_installed": rapid_ok,
            }
        return {
            "status": "unavailable",
            "engine": "none",
            "suggested_action": "Install RapidOCR (pip install rapidocr-onnxruntime) or Tesseract OCR at C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
        }

    def extract_text_from_image(
        self,
        image_input: Path | Image.Image | bytes,
        page_number: int = 1,
    ) -> dict[str, Any]:
        """
        Run local OCR on an image file, PIL Image, or PNG bytes.
        Returns extracted text, average confidence, bounding boxes, and engine used.
        """
        if not settings.OCR_ENABLED:
            raise RuntimeError(
                "OCR is disabled in configuration (OCR_ENABLED=false). Enable OCR to process scanned pages or images."
            )

        # 1. Try RapidOCR (ONNX CPU) first for fast, zero-external-binary OCR with bounding boxes & confidence
        try:
            ocr = self._get_rapid_ocr()
            if isinstance(image_input, Path):
                target = str(image_input)
            else:
                target = image_input

            result, _elapse = ocr(target)
            if result:
                lines = []
                confidences = []
                boxes = []
                for item in result:
                    # item format: [bbox, text, score]
                    bbox, text, score = item[0], str(item[1]).strip(), float(item[2])
                    if text:
                        lines.append(text)
                        confidences.append(score)
                        boxes.append({"bbox": bbox, "text": text, "confidence": round(score, 4)})
                avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else 0.0
                full_text = "\n".join(lines)
                ingestion_logger.info(
                    f"RapidOCR extracted {len(lines)} lines from page {page_number} (avg_conf={avg_conf})"
                )
                return {
                    "text": full_text,
                    "confidence": avg_conf,
                    "boxes": boxes,
                    "page_number": page_number,
                    "engine": "RapidOCR-ONNX",
                }
        except Exception as e:
            error_logger.error(f"RapidOCR error on page {page_number}: {e}")

        # 2. Fallback to Tesseract OCR if installed
        if self.is_tesseract_available():
            try:
                import pytesseract

                if isinstance(image_input, Path):
                    img = Image.open(image_input)
                elif isinstance(image_input, bytes):
                    import io

                    img = Image.open(io.BytesIO(image_input))
                else:
                    img = image_input

                text = pytesseract.image_to_string(img, lang=settings.OCR_LANGUAGES)
                return {
                    "text": text.strip(),
                    "confidence": 0.85,
                    "boxes": [],
                    "page_number": page_number,
                    "engine": "Tesseract",
                }
            except Exception as e:
                error_logger.error(f"Tesseract OCR error on page {page_number}: {e}")

        return {
            "text": "",
            "confidence": 0.0,
            "boxes": [],
            "page_number": page_number,
            "engine": "none",
        }


ocr_engine = LocalOCREngine()
