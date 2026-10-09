# Authorization & Security Audit (`docs/AUTHORIZATION_AUDIT.md`)

**Date:** 2026-10-08  
**System:** ONYX — Local Multimodal RAG Knowledge System  
**Scope:** End-to-End Authentication, RBAC, ABAC (Department/Group/User), Document-Level Access Control, Vector Retrieval Filtering, Database Query Authorization, Artifact/Workspace Protection, and Audit Logging.

---

## 1. Current State Inspection Summary

### 1.1 Current Authentication System
- **Location:** `backend/auth/auth_handler.py`
- **Mechanism:** Argon2id password hashing (`argon2-cffi`) + HS256 JWT tokens (`create_access_token`, `decode_access_token`).
- **Gaps Identified:**
  1. Stateless JWTs cannot be immediately invalidated on logout, password reset, role change, or user disablement/suspension (`User.status` does not exist yet).
  2. No server-side `UserSession` table or `token_version` check to revoke active sessions when an employee is suspended or disabled.
  3. No login rate limiting or failed-login security alerting.

### 1.2 Current User Model (`backend/database/sqlite_db.py`)
- **Current Fields:** `id`, `username`, `password_hash`, `role` (`"ADMIN"` / `"MEMBER"`), `workspace_id`, `allowed_collections_json`, `can_upload`, `created_at`.
- **Gaps Identified:**
  1. Missing `name`, `email`, `job_title`, `department_id`, `status` (`ACTIVE`, `SUSPENDED`, `DISABLED`), `permissions_json`, `token_version`, `updated_at`, `last_login`.
  2. Uses legacy `"MEMBER"` role instead of normalized `"admin"` / `"employee"` roles (must support both seamlessly for backward compatibility while standardizing on `"admin"` and `"employee"`).
  3. No `Department`, `Group`, or `UserGroup` membership models.

### 1.3 Current Document & Collection Models (`backend/database/sqlite_db.py`)
- **Current Document Fields:** `id`, `filename`, `original_filename`, `file_type`, `modality`, `file_path`, `file_size`, `content_hash`, `version`, `collection_id`, `collection_name`, `workspace_id`, `owner`, `status`, `chunk_count`, `page_count`, `metadata_json`, `created_at`, `updated_at`.
- **Gaps Identified:**
  1. No document-level access policy (`access_level`: `ADMIN_ONLY`, `EMPLOYEE_SHARED`, `DEPARTMENT_ONLY`, `GROUP_ONLY`, `USER_SPECIFIC`, `PRIVATE_UPLOAD`).
  2. No `department_id`, `approval_status` (`APPROVED`, `PENDING_REVIEW`), or `document_access` policy rules table (`DocumentAccess`).
  3. No `collection_access` policy rules table (`CollectionAccess`). Currently authorization only checks coarse `user.allowed_collections`.
  4. If an employee has access to the `General` collection, they can currently read **every** document in `General`, even if a specific document in `General` is restricted to `ADMIN_ONLY` or a specific department/group/user.

### 1.4 Current Vector Metadata (`backend/database/vector_store.py` & `backend/ingestion/chunker.py`)
- **Current Metadata on ChromaDB Chunks:** `document_id`, `chunk_id`, `modality`, `filename`, `collection`, `page_number`, `section_title`, `owner`, `version`.
- **Gaps Identified:**
  1. `vector_store.query_similar()` only filters by `collection`, **not** by authorized `document_id` list or document-level access policy!
  2. If a collection contains both employee-accessible and admin-only documents, `vector_store.query_similar()` can retrieve chunks from restricted documents during top-K candidate generation.
  3. Vector chunks lack `access_level`, `department_id`, and `collection_id` metadata fields, and `query_similar` does not enforce pre-retrieval `{"document_id": {"$in": authorized_doc_ids}}` filtering.

### 1.5 Current File Storage (`backend/core/config.py` & `backend/api/routes.py`)
- **Current Path:** `./data/uploads` (outside `frontend/dist` and `frontend/public`, which is good, and `data/secure_uploads` will also be supported/migrated seamlessly).
- **Gaps Identified:**
  1. `GET /api/documents/{document_id}/file` only checks `user_can_access_collection(current_user, doc.collection_name)` instead of full document-level authorization + `document.read` permission + audit logging.
  2. Missing `GET /api/documents/{document_id}/content` canonical secure download/stream route.

---

## 2. Route-by-Route Authorization Audit Matrix

| Current Route | Current Authentication | Current Authorization | Potential Vulnerability | Required Change |
| :--- | :--- | :--- | :--- | :--- |
| `GET /api/health` | Public (`None`) | Public | Leaks `app`, `version`, `offline_mode` metadata | Keep `/api/health` minimal (`{"status": "ok"}`) or non-sensitive; keep detailed diagnostics on `/api/system/status`. |
| `GET /api/models` | **None (Public!)** | **None!** | Unauthenticated caller can inspect local LLM/OCR/Embedding models | Require `get_current_user` authentication. |
| `GET /api/system/status` | **None (Public!)** | **None!** | Exposes document counts, chunk counts, vector counts, and hardware info to unauthenticated users or restricted employees | Allow minimal pre-auth boot check (service online/offline booleans only), and scope document/chunk/vector counts to the authenticated user's authorized scope (or admin). |
| `POST /api/auth/login` | Public | Verifies password | Does not check `user.status` (`SUSPENDED`/`DISABLED`), does not create a revocable `UserSession`, does not log `ADMIN_LOGIN` / `EMPLOYEE_LOGIN` / `LOGIN_FAILED` in `audit_logs`, no rate limiting | Enforce `user.status == "ACTIVE"`, issue session-bound JWT, record audit log & failed login attempts, enforce rate limit. |
| `POST /api/auth/logout` | Missing | Missing | Cannot invalidate active token on server | Add `POST /api/auth/logout` to revoke current session & log `LOGOUT`. |
| `GET /api/auth/me` | `get_current_user` | Self | Does not return `job_title`, `department`, `groups`, `permissions`, `status` | Return complete RBAC profile & effective permissions. |
| `GET /api/users` | `require_admin` | Admin role check | Does not check `user.read` permission via central policy engine | Route through central `authorization_service.require_permission(user, "user.read")`. |
| `POST /api/users` | `require_admin` | Admin role check | Does not support `name`, `email`, `job_title`, `department_id`, `groups`, `status`, `permissions` or audit logging | Upgrade user creation with full RBAC fields + `USER_CREATED` audit log. |
| `GET /api/collections` | `get_current_user` | `user_can_access_collection` | Leaks total `document_count` in collection including `ADMIN_ONLY` documents inside that collection! | Filter collections via `authorization.can_access_collection` AND count only documents the user is authorized to read. |
| `POST /api/collections` | `get_current_user` | **Any logged-in user!** | An employee without `collection.create` permission can create collections | Enforce `authorization.require_permission(user, "collection.create")` and record audit log. |
| `DELETE /api/collections/{id}` | `require_admin` | Admin role check | No audit log entry | Enforce `collection.delete` permission and record `COLLECTION_DELETED` audit log. |
| `POST /api/documents/upload` | `get_current_user` | `can_upload` + collection check | Employee-uploaded documents immediately become visible to all collection members instead of defaulting to private/uploader or specified policy; no `document.upload` permission check | Enforce `document.upload` permission; default employee uploads to `USER_SPECIFIC` (private to uploader + admin) unless admin sets policy; store `DocumentAccess` policy and vector metadata; log `DOCUMENT_UPLOAD`. |
| `POST /api/database/inspect` | `get_current_user` | **Any logged-in user!** | Employee can pass arbitrary local SQLite path (e.g., `./data/metadata/app.db`!) and inspect internal application tables including `users`! | **CRITICAL FIX:** Block inspection of internal app DB (`app.db`), require `database.read` / admin permission for external DB ingestion, and log `DATABASE_QUERY`. |
| `POST /api/database/ingest` | `get_current_user` | Collection check only | Employee could ingest arbitrary local SQLite file | Restrict external DB ingestion to admins (or explicit `database.ingest` permission) and block internal `app.db`. |
| `GET /api/documents` | `get_current_user` | Collection check only | **HIGH VULNERABILITY:** Lists all documents in an allowed collection, ignoring document-level access policies (`ADMIN_ONLY`, `DEPARTMENT_ONLY`, `GROUP_ONLY`, `USER_SPECIFIC`) | Filter every document through `authorization.filter_authorized_documents(db, current_user)` before returning. |
| `GET /api/documents/{id}` | `get_current_user` | Collection check only | **HIGH VULNERABILITY:** Employee can view chunks/metadata of an `ADMIN_ONLY` document if it sits in an allowed collection | Enforce `authorization.can_access_document(db, current_user, doc, "read")`; log `DOCUMENT_VIEW` (or `UNAUTHORIZED_ACCESS_ATTEMPT` on 403). |
| `GET /api/documents/{id}/file` & `/content` | `get_current_user` | Collection check only | **HIGH VULNERABILITY:** Employee can download raw file of an `ADMIN_ONLY` document in an allowed collection | Enforce `authorization.can_access_document(db, current_user, doc, "read")` on both `/file` and `/content`; stream securely; log `DOCUMENT_DOWNLOAD`. |
| `DELETE /api/documents/{id}` | `require_admin` | Admin check | No `document.delete` permission check or audit log | Enforce `document.delete` permission and log `DOCUMENT_DELETE`. |
| `POST /api/search` | `get_current_user` | Collection filter only | **CRITICAL VULNERABILITY:** Searches all chunks in allowed collections without filtering by authorized `document_id` set! | Compute `authorized_doc_ids` **before** retrieval; pass `authorized_doc_ids` into `retriever.retrieve()` and `vector_store.query_similar()`. |
| `POST /api/chat` | `get_current_user` | Collection filter only | **CRITICAL VULNERABILITY:** Vector retrieval and SQL `plan_and_execute_database_query` only filter by collection, allowing unauthorized document chunks or database tables to reach the LLM and structured response generator! | Compute `authorized_doc_ids` before retrieval and SQL planning; filter both ChromaDB (`document_id in authorized_doc_ids`) and SQLite chunks/DB sources prior to LLM execution; persist artifacts with `source_document_ids` and owner authorization; log `RAG_QUERY`. |
| `POST /api/workspace/mutate` | `get_current_user` | Authenticated only | Does not verify user is authorized for the underlying `sources` of the workspace/artifact being mutated | Verify source document access before mutating or viewing saved workspaces/artifacts. |

---

## 3. Proposed RBAC + ABAC + Document-Level Architecture

1. **Central Policy & Authorization Engine (`backend/auth/`):**
   - `permissions.py`: Defines granular permissions (`document.read`, `document.upload`, `document.delete`, `document.update`, `document.share`, `document.manage_access`, `collection.read`, `collection.create`, `collection.delete`, `user.read`, `user.create`, `user.update`, `user.disable`, `audit.read`, `database.read`, `rag.search`, `rag.ask`), role defaults (`admin` -> `["*"]`, `employee` -> configurable default subset).
   - `policies.py`: Deterministic policy evaluation (`ADMIN_ONLY`, `EMPLOYEE_SHARED`, `DEPARTMENT_ONLY`, `GROUP_ONLY`, `USER_SPECIFIC`, `PRIVATE_UPLOAD`) with explicit deny-by-default resolution.
   - `authorization.py`: Central `AuthorizationService` (`can_access_document`, `can_access_collection`, `get_authorized_document_ids`, `has_permission`, `simulate_user_access`, `check_document_access_test`).
   - `audit.py`: Structured security audit logger writing to `audit_logs` table without ever logging plaintext passwords or confidential document contents.

2. **Pre-Retrieval RAG & Vector Security:**
   - Before any call to `vector_store.query_similar()` or BM25 chunk scoring or SQL `plan_and_execute_database_query()`, the backend resolves the exact set of `authorized_document_ids` for `current_user`.
   - If `authorized_document_ids` is empty for an employee, retrieval immediately returns 0 chunks and the neutral message: `"I couldn't find enough information in the knowledge base available to your account."`
   - ChromaDB receives `where={"document_id": {"$in": list(authorized_document_ids)}}` so unauthorized vectors are **never** scored or returned.
   - When an admin updates a document's access policy, both the SQLite `Document` / `DocumentAccess` tables and the ChromaDB chunk metadata are updated immediately.
