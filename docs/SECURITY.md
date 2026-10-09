# Security Architecture & Threat Defense (`docs/SECURITY.md`)

## 1. Non-Negotiable Security Guarantees
1. **100% Local Execution (`OFFLINE_MODE=True`)**:
   - No external cloud APIs, external telemetry, or remote vector databases are ever contacted.
   - All embeddings (`intfloat/multilingual-e5-small`), OCR (`RapidOCR` / `Tesseract`), vector storage (`ChromaDB`), relational metadata (`SQLite`), and LLM inference (`Ollama` / local extractive fallback) run strictly on the local machine.
2. **Deny by Default**:
   - Normal employees (`role = "employee"`) have zero access to any document, collection, vector chunk, database table, or artifact unless explicitly granted by policy.
3. **File Storage Isolation**:
   - Uploaded documents reside in `./data/uploads` outside the frontend static asset tree (`frontend/dist` and `frontend/public`).
   - Direct requests to `/uploads/*`, `/secure_uploads/*`, or `/data/*` are explicitly rejected with `403 Forbidden`.
   - File downloads are served exclusively through `GET /api/documents/{document_id}/content` (and `/file`) after passing both JWT authentication and `authorization_service.evaluate_document_access(db, user, doc, "read")`.
4. **Prompt Injection & Indirect Data Leakage Prevention**:
   - Authorization is enforced by deterministic backend Python logic **before** retrieval—never delegated to the LLM.
   - All retrieved document excerpts are wrapped inside `<document_excerpt>` passive data tags with explicit system instructions to ignore embedded commands.
   - When an employee asks about restricted topics (e.g., CEO salary), restricted documents are excluded before vector search and the assistant responds neutrally without confirming whether a restricted file exists.
5. **Internal Database Protection**:
   - `is_internal_system_database()` in [`backend/database/query_planner.py`](file:///c:/Users/devik/Desktop/rag/backend/database/query_planner.py) blocks any attempt to inspect, ingest, or query the application's own SQLite metadata/auth database (`app.db`).
   - All natural-language SQL queries are validated by `sql_validator.py` to enforce read-only `SELECT` statements.
