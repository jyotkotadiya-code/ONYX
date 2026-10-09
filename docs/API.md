# API Documentation — ONYX Local Multimodal RAG

Base URL (Local Backend): `http://127.0.0.1:8000`  
Interactive Swagger UI: `http://127.0.0.1:8000/docs`

---

## 1. Authentication & Users

### `POST /api/auth/login`
Authenticate a user and receive a signed JWT bearer token.

**Request Body:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response (`200 OK`):**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "username": "admin",
    "role": "ADMIN",
    "workspace": "ONYX",
    "allowed_collections": ["*"],
    "can_upload": true
  }
}
```

### `GET /api/auth/me`
Return the currently authenticated user profile and permissions.

### `GET /api/users` *(Admin Only)*
List all users in the workspace.

### `POST /api/users` *(Admin Only)*
Create a new team user with Argon2id password hashing and collection permissions.

---

## 2. Health, Models & System Status

### `GET /api/health`
Lightweight health check endpoint.

### `GET /api/models`
Returns discovered local LLM runtime (`ollama` / `lm_studio`), selected model (`hf.co/bartowski/Llama-3.1-8B-Lexi-Uncensored-V2-GGUF:Q4_K_M`), local embedding model status (`intfloat/multilingual-e5-small`), OCR status, and Whisper audio status.

### `GET /api/system/status`
Comprehensive system status and storage statistics:
```json
{
  "llm": "online",
  "embedding_model": "online",
  "vector_database": "online",
  "sqlite": "online",
  "ocr": "available",
  "audio": "disabled",
  "offline_mode": true,
  "verified_private": true
}
```

---

## 3. Documents & Multimodal Ingestion

### `POST /api/documents/upload`
Multipart file upload supporting `.pdf`, Scanned `.pdf`, `.docx`, `.doc`, `.txt`, `.xml`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.db`/`.sqlite`, `.mp3`, `.wav`.
- Automatically computes `SHA256(file)` for duplicate detection.
- Increments document `version` if filename exists with a modified hash.

### `GET /api/documents`
List all documents in collections the user has permission to access.

### `GET /api/documents/{id}`
Retrieve document metadata, version history, and all indexed chunks.

### `GET /api/documents/{id}/file`
Download or preview the raw uploaded file.

### `DELETE /api/documents/{id}` *(Admin Only)*
Delete a document from SQLite, remove its raw file, and delete all associated vectors from ChromaDB.

### `POST /api/documents/{id}/reindex` *(Admin Only)*
Re-run the extraction, chunking, embedding, and vector indexing pipeline on an existing document.

---

## 4. Database Ingestion

### `POST /api/database/inspect`
Inspect tables, columns, primary keys, and row counts of a local SQLite, PostgreSQL, or MySQL database.

### `POST /api/database/ingest`
Selectively serialize and index rows from specified database tables with full `database`, `table`, and `row_id` metadata.

---

## 5. Collections

### `GET /api/collections`
List permitted collections and document counts.

### `POST /api/collections`
Create a new collection inside the workspace.

### `DELETE /api/collections/{id}` *(Admin Only)*
Delete a collection and its vectors.

---

## 6. Direct Search & RAG Chat

### `POST /api/search`
Search chunks directly before asking the LLM. Supports `"mode": "rag"` (Hybrid Semantic + BM25) and `"mode": "exact"` (Exact keyword/ID matching).

### `POST /api/chat`
Run the full RAG pipeline (`Question -> Embedding -> Hybrid Vector Search -> Grounding Guard -> Prompt-Injection-Safe Context Assembly -> Local Llama -> Cited Answer`).
Supports both JSON responses (`"stream": false`) and Server-Sent Events token streaming (`"stream": true`).
