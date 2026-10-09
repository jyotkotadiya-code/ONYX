# Testing & Evaluation Documentation

## 1. Automated Functional & Security Tests (`tests/test_rag_system.py`)

Run the full automated test suite with:

```powershell
python -m pytest tests/test_rag_system.py -v
```

### What Is Tested:
1. **`test_system_health_and_offline_mode`**: Verifies `/api/system/status`, `offline_mode=true`, `verified_private=true`, ChromaDB online, and SQLite online.
2. **`test_pdf_ingestion_and_duplicate_detection`**: Generates a multi-paragraph PDF, verifies extraction, chunking, embedding, and indexing, then uploads the exact same file a second time and verifies `SHA-256` duplicate detection skips re-indexing.
3. **`test_scanned_pdf_ocr_ingestion`**: Generates a rasterized image-only PDF with zero native text, verifies automatic fallback to local page rendering + RapidOCR/Tesseract OCR, and indexes the extracted text as `scanned_pdf`.
4. **`test_docx_ingestion`**: Generates a structured `.docx` with headings and paragraphs and verifies section-preserving chunking.
5. **`test_xml_ingestion`**: Uploads a hierarchical `.xml` document and verifies semantic key-value serialization (`Customer -> Name, Company, Subscription Tier`).
6. **`test_image_ocr_ingestion`**: Generates a `.jpg` invoice image with embedded text and verifies local OCR + image dimension metadata indexing.
7. **`test_sqlite_database_ingestion`**: Creates a `.db` SQLite database (`employees` table), indexes structured rows with primary keys, and verifies row-level chunk creation.
8. **`test_rag_positive_and_negative_questions`**:
   - Verifies single-document QA + accurate source citations.
   - Verifies multi-document synthesis across PDF + DOCX.
   - Verifies Exact Search mode (`EMP-184`).
   - Verifies **Anti-Hallucination Refusal** on unanswerable questions (`"I couldn't find enough information in the uploaded knowledge base to answer that."`).
9. **`test_security_malicious_filenames_and_prompt_injection`**: Tests path traversal sanitization, `.exe` rejection, and prompt injection detection.

---

## 2. Quantitative RAG Evaluation Suite (`tests/evaluate_rag.py`)

Run the RAG evaluation benchmark with:

```powershell
python tests/evaluate_rag.py
```

### Benchmark Dataset (`tests/evaluation/`)
Automatically generates sample PDF, DOCX, and XML documents in `tests/evaluation/` and runs 7 benchmark queries across 6 categories:
- `easy`
- `multi-document`
- `exact-match`
- `cross-document`
- `summarization`
- `negative` (unanswerable questions testing hallucination resistance)

### Latest Benchmark Results
- **Retrieval accuracy:** `100.0%`
- **Answer accuracy:** `100.0%`
- **Citation accuracy:** `100.0%`
- **Unsupported-answer (hallucination) rate:** `0.0%`
