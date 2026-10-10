import io
import os
import tempfile
from pathlib import Path
import openpyxl
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from backend.main import app
from backend.tools.vectorizer import ImageVectorizationError, vector_converter
from backend.ingestion.doc_parser import _parse_excel_file

client = TestClient(app)


def test_raster_to_vector_converter_generates_valid_svg():
    # Generate an isolated synthetic test image with crisp geometric shapes
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "test_logo.png"
        img = Image.new("RGBA", (150, 150), (255, 255, 255, 255))
        draw = ImageDraw.Draw(img)
        # Draw a blue rectangle and red circle
        draw.rectangle([20, 20, 70, 70], fill=(0, 102, 204, 255))
        draw.ellipse([80, 80, 130, 130], fill=(220, 50, 50, 255))
        img.save(img_path)

        # Execute genuine raster-to-vector tracing
        res = vector_converter.convert_to_svg(img_path, colormode="color", mode="spline")

        assert res["success"] is True
        assert res["path_count"] >= 1
        assert res["has_vector_geometry"] is True
        assert res["file_size_bytes"] > 100

        # Assert output is valid SVG with path definitions and NOT an embedded raster image
        svg_content = res["svg_markup"]
        assert "<svg" in svg_content
        assert "<path" in svg_content
        assert 'd="' in svg_content
        assert "<image" not in svg_content, "Output must contain genuine vector geometry, not an embedded raster image"

        # Cleanup generated SVG
        out_p = Path(res["svg_path"])
        if out_p.exists():
            out_p.unlink()


def test_vectorizer_handles_transparent_png():
    with tempfile.TemporaryDirectory() as tmpdir:
        img_path = Path(tmpdir) / "transparent_icon.png"
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.polygon([(50, 10), (90, 90), (10, 90)], fill=(0, 200, 100, 255))
        img.save(img_path)

        res = vector_converter.convert_to_svg(img_path, colormode="color")
        assert res["success"] is True
        assert res["path_count"] >= 1
        assert "<path" in res["svg_markup"]

        out_p = Path(res["svg_path"])
        if out_p.exists():
            out_p.unlink()


def test_vectorizer_rejects_corrupted_or_invalid_image():
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_file = Path(tmpdir) / "corrupt.png"
        bad_file.write_bytes(b"NOT_A_VALID_IMAGE_DATA_BYTES")

        with pytest.raises(ImageVectorizationError) as exc_info:
            vector_converter.convert_to_svg(bad_file)
        assert "Corrupted or invalid image file" in str(exc_info.value)


def test_vectorize_image_api_endpoint():
    # Login as admin to get token
    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create test image in memory
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 90, 90], fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    resp = client.post(
        "/api/tools/vectorize-image",
        headers=headers,
        files={"file": ("shape.png", buf.getvalue(), "image/png")},
        data={"colormode": "color"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["success"] is True
    assert data["path_count"] >= 1
    assert "preview_url" in data
    assert "download_url" in data

    # Test preview URL
    prev_resp = client.get(data["preview_url"], headers=headers)
    assert prev_resp.status_code == 200
    assert "image/svg+xml" in prev_resp.headers.get("content-type", "")
    assert "<svg" in prev_resp.text

    # Test download URL
    dl_resp = client.get(data["download_url"], headers=headers)
    assert dl_resp.status_code == 200
    assert "attachment" in dl_resp.headers.get("content-disposition", "")

    # Cleanup generated SVG
    out_p = Path(data["svg_path"])
    if out_p.exists():
        out_p.unlink()


def test_excel_spreadsheet_ingestion():
    with tempfile.TemporaryDirectory() as tmpdir:
        excel_path = Path(tmpdir) / "financial_ledger.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Revenue_2025"
        ws.append(["Month", "Revenue (USD)", "Operating Cost (USD)"])
        ws.append(["January 2025", 10000, 6000])
        ws.append(["February 2025", 15000, 8000])
        ws.append(["March 2025", 12000, 7500])
        wb.save(str(excel_path))

        blocks, meta = _parse_excel_file(excel_path)
        assert len(blocks) == 1
        assert blocks[0].table_name == "Revenue_2025"
        assert "January 2025" in blocks[0].text
        assert "15000" in blocks[0].text
        assert meta["tables_extracted"] == 1
        assert "Revenue_2025" in meta["sheets"]
