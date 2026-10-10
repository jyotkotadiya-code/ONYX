import os
import re
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional
from PIL import Image
import vtracer
from backend.core.config import settings
from backend.core.logging_config import app_logger, error_logger


SUPPORTED_RASTER_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
MAX_IMAGE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class ImageVectorizationError(Exception):
    pass


class RasterToVectorConverter:
    """
    Genuine local raster-to-vector tracing engine powered by VTracer (Rust/WASM vectorizer).
    Converts PNG/JPG/JPEG raster bitmaps into valid SVG vector graphics containing real vector paths.
    Does NOT wrap raster images in an SVG tag or rename extensions.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or (settings.resolve_path(settings.PROCESSED_DIR) / "vector_svgs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def validate_image(self, file_path: Path) -> tuple[int, int, str]:
        if not file_path.exists():
            raise ImageVectorizationError(f"Input file not found: {file_path}")

        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_RASTER_EXTENSIONS:
            raise ImageVectorizationError(
                f"Unsupported image format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_RASTER_EXTENSIONS))}"
            )

        size_bytes = file_path.stat().st_size
        if size_bytes == 0:
            raise ImageVectorizationError("Uploaded image file is empty (0 bytes).")
        if size_bytes > MAX_IMAGE_SIZE_BYTES:
            raise ImageVectorizationError(
                f"Image file exceeds maximum allowed size of {MAX_IMAGE_SIZE_BYTES // (1024*1024)} MB."
            )

        try:
            with Image.open(file_path) as img:
                w, h = img.size
                img_format = img.format or "UNKNOWN"
                if w < 4 or h < 4:
                    raise ImageVectorizationError(f"Image dimensions too small ({w}x{h}). Minimum size is 4x4 px.")
                if w > 8192 or h > 8192:
                    raise ImageVectorizationError(f"Image dimensions too large ({w}x{h}). Maximum size is 8192x8192 px.")
                return w, h, img_format
        except Exception as e:
            if isinstance(e, ImageVectorizationError):
                raise
            raise ImageVectorizationError(f"Corrupted or invalid image file: {e}")

    def convert_to_svg(
        self,
        input_path: Path,
        colormode: str = "color",  # "color" or "binary"
        hierarchical: str = "stacked",  # "stacked" or "cutout"
        mode: str = "spline",  # "spline", "polygon", "none"
        filter_speckle: int = 4,
        color_precision: int = 6,
        layer_difference: int = 16,
        corner_threshold: int = 60,
        length_threshold: float = 4.0,
        max_iterations: int = 10,
        splice_threshold: int = 45,
        path_precision: int = 3,
    ) -> dict[str, Any]:
        """
        Execute genuine raster-to-vector tracing on input image and save output SVG.
        """
        t0 = time.perf_counter()
        w, h, orig_fmt = self.validate_image(input_path)

        out_id = str(uuid.uuid4())
        out_filename = f"{input_path.stem}_{out_id[:8]}.svg"
        out_svg_path = self.output_dir / out_filename

        # Normalize colormode and mode settings
        colormode = "binary" if str(colormode).lower() in ("binary", "bw", "black_white") else "color"
        mode = "polygon" if str(mode).lower() == "polygon" else "spline"

        # Pre-process image with PIL if required (e.g. handle palette/CMYK modes)
        temp_input_to_clean: Optional[Path] = None
        target_input = input_path
        try:
            with Image.open(input_path) as img:
                if img.mode not in ("RGB", "RGBA"):
                    temp_input_to_clean = self.output_dir / f"tmp_{out_id}.png"
                    img.convert("RGBA" if "A" in img.mode else "RGB").save(temp_input_to_clean)
                    target_input = temp_input_to_clean

            app_logger.info(
                f"Starting VTracer vectorization for '{input_path.name}' ({w}x{h}, mode={colormode})"
            )

            # Invoke VTracer Python binding
            vtracer.convert_image_to_svg_py(
                image_path=str(target_input),
                out_path=str(out_svg_path),
                colormode=colormode,
                hierarchical=hierarchical,
                mode=mode,
                filter_speckle=filter_speckle,
                color_precision=color_precision,
                layer_difference=layer_difference,
                corner_threshold=corner_threshold,
                length_threshold=length_threshold,
                max_iterations=max_iterations,
                splice_threshold=splice_threshold,
                path_precision=path_precision,
            )

        except Exception as e:
            error_logger.error(f"VTracer tracing failed on '{input_path.name}': {e}")
            raise ImageVectorizationError(f"Vector tracing failed: {e}")
        finally:
            if temp_input_to_clean and temp_input_to_clean.exists():
                try:
                    temp_input_to_clean.unlink()
                except Exception:
                    pass

        # Validate the generated SVG file
        if not out_svg_path.exists() or out_svg_path.stat().st_size == 0:
            raise ImageVectorizationError("Vectorization produced an empty or missing SVG file.")

        svg_content = out_svg_path.read_text(encoding="utf-8", errors="replace")
        validation_info = self.validate_svg_markup(svg_content)

        duration_ms = round((time.perf_counter() - t0) * 1000, 2)
        app_logger.info(
            f"Vectorization completed for '{input_path.name}': {validation_info['path_count']} vector paths in {duration_ms}ms"
        )

        return {
            "success": True,
            "filename": out_filename,
            "svg_path": str(out_svg_path),
            "svg_markup": svg_content,
            "file_size_bytes": out_svg_path.stat().st_size,
            "width": w,
            "height": h,
            "original_format": orig_fmt,
            "vector_mode": colormode,
            "path_count": validation_info["path_count"],
            "has_vector_geometry": validation_info["has_vector_geometry"],
            "duration_ms": duration_ms,
            "warning": (
                "Vector tracing converts bitmap shapes into scalable mathematical curves. "
                "It produces best results for logos, diagrams, illustrations, and line art; "
                "complex photographic textures may result in simplified polygonal representations."
            ),
        }

    @staticmethod
    def validate_svg_markup(svg_text: str) -> dict[str, Any]:
        """
        Verify that the output SVG is genuine vector XML containing actual path geometry
        and NOT an embedded raster image.
        """
        if "<svg" not in svg_text:
            raise ImageVectorizationError("Generated output does not contain valid SVG markup.")

        # Check for false vectorization (e.g. embedding raster <image href="data:image/png...")
        if "<image" in svg_text and "<path" not in svg_text:
            raise ImageVectorizationError("Output merely embeds a raster image and contains no genuine vector paths.")

        # Count genuine path elements
        path_matches = re.findall(r"<path[^>]*\sd=[\"']([^\"']+)[\"']", svg_text, re.IGNORECASE)
        polygon_matches = re.findall(r"<polygon[^>]*", svg_text, re.IGNORECASE)
        total_vectors = len(path_matches) + len(polygon_matches)

        if total_vectors == 0:
            raise ImageVectorizationError("SVG output contains 0 vector path elements.")

        return {
            "has_vector_geometry": True,
            "path_count": total_vectors,
        }


vector_converter = RasterToVectorConverter()
