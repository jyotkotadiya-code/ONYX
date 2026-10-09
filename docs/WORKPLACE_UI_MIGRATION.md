# Workplace-Based Private AI Platform — Architecture Audit & UI Migration Plan

## 1. Current Architecture Audit

### 1.1 Current Routes (`backend/api/routes.py`)
- **Authentication**: `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`
- **System Status**: `GET /api/system/status` (public readiness summary), `GET /api/health`
- **Admin RBAC & Security**:
  - `GET /api/admin/overview`, `GET /api/admin/permissions`, `PUT /api/admin/permissions`
  - `GET /api/admin/departments`, `POST /api/admin/departments`, `DELETE /api/admin/departments/{id}`
  - `GET /api/admin/groups`, `POST /api/admin/groups`, `DELETE /api/admin/groups/{id}`
  - `GET /api/admin/users`, `POST /api/admin/users`, `PUT /api/admin/users/{id}`, `POST /api/admin/users/{id}/revoke-sessions`
  - `PUT /api/admin/documents/{id}/access`
  - `POST /api/admin/access/simulate`, `POST /api/admin/access/test-document`
  - `GET /api/admin/audit-logs`
- **Collections & Knowledge**:
  - `GET /api/collections`, `POST /api/collections`, `PUT /api/collections/{id}/access`, `DELETE /api/collections/{id}`
  - `POST /api/documents/upload`, `GET /api/documents`, `GET /api/documents/{id}`, `GET /api/documents/{id}/content`, `GET /api/documents/{id}/file`, `DELETE /api/documents/{id}`, `POST /api/documents/{id}/reindex`
  - `POST /api/database/inspect`, `POST /api/database/ingest`
- **RAG & Chat**:
  - `POST /api/search` (direct chunk search)
  - `POST /api/query` (RAG chat + SSE streaming + structured response)
  - `POST /api/workspace/followup`
  - `GET /api/chat/sessions`, `GET /api/chat/sessions/{id}`, `DELETE /api/chat/sessions/{id}`
  - `GET /api/artifacts`, `POST /api/artifacts`, `GET /api/artifacts/{id}`, `DELETE /api/artifacts/{id}`

### 1.2 Current User Model (`User` in `backend/database/sqlite_db.py`)
- Fields: `id`, `name`, `email`, `username`, `password_hash`, `role` (`admin` / `employee`), `job_title`, `department_id`, `status` (`ACTIVE`, `SUSPENDED`, `DISABLED`), `workspace_id`, `allowed_collections_json`, `permissions_json`, `can_upload`, `token_version`, `created_at`, `updated_at`, `last_login`.
- Gap: `can_upload` defaulted to `True` for employees; needs to default to `False` per Section 65 (`Upload: NO` by default for employees, configurable by admin). Needs local employee invitation/activation support (`invite_code`, `invite_status`, `last_active_at`).

### 1.3 Current Workplace Model (`Workspace` in `backend/database/sqlite_db.py`)
- Currently named `Workspace` (`workspaces` table) with `id`, `name`, `description`, `created_at`.
- Needs full Workplace identity & branding fields:
  - `slug`, `logo`, `industry`, `created_by`, `status` (`ACTIVE`, `ARCHIVED`)
  - Branding & AI Configuration: `assistant_name` (e.g., `"ONYX AI"`), `welcome_message`, `default_doc_visibility` (`EMPLOYEE_SHARED` / `ADMIN_ONLY`), `allow_employee_uploads` (`False` by default), `session_duration_minutes`, `onboarding_completed`.

### 1.4 Current RBAC & Knowledge Model
- Central `AuthorizationService` in `backend/auth/authorization.py` with `ADMIN_ONLY`, `EMPLOYEE_SHARED`, `DEPARTMENT_ONLY`, `GROUP_ONLY`, and `USER_SPECIFIC` policies.
- Gap:
  1. `Document` needs `is_archived` (boolean) and `ARCHIVED` status support so admins can archive documents (`POST /api/admin/documents/{id}/archive`), excluding archived documents from employee RAG retrieval while allowing optional admin archive search.
  2. Strict workplace scoping (`workspace_id == current_user.workspace_id`) must be enforced across **every** query (`User`, `Department`, `Group`, `Collection`, `Document`, `ChunkRecord`, `ChatSession`, `SavedArtifact`, `AuditLog`) and inside ChromaDB vector metadata (`workplace_id` / `workspace_id`).

### 1.5 Current Frontend Navigation & Experience
- Currently `frontend/src/App.tsx` shares a single multi-tab sidebar (`AI Chat & Query`, `Multimodal Ingestion`, `Documents & Versions`, `Direct Search`, `Collections & Team`, `Admin & Access Policies`, `System Health`) between Admins and Employees (hiding only the Admin tab for employees).
- **Required Change**: Split into **two completely distinct product experiences**:
  1. **Admin Workplace Console (`/admin/*`)**:
     - Sidebar: `Overview`, `Employees`, `Knowledge`, `Collections`, `Access`, `Analytics`, `Settings` (+ `AI Workspace` & `System status` / `Profile` / `Logout`).
     - Supports Workplace creation/switching, Employee management + local invite/activation flow, Employee profile drawer with accessible knowledge debugger, unified Knowledge management (`Documents`, `Collections`, `Data Sources`, `Processing`, `+ Add Knowledge`, Archive/Re-index/Preview), Access policies, Workplace Analytics, and Workplace Branding/AI Settings.
  2. **Employee Private AI Assistant (`/chat`, `/profile`)**:
     - Distraction-free, chat-first private AI experience (`ONYX AI — Private workplace assistant`).
     - Minimal navigation: `New Chat`, `Recent Chats`, `Profile`, `Sign out`.
     - Zero exposure of `Documents`, `Collections`, `Users`, `Admin`, `Settings`, `Analytics`, `System Health`, `Vector Database`, `Chunks`, `Embedding Model`, or `OCR`.
     - Supports rich structured responses (Text, Tables, Charts, KPIs, Comparisons, Citations) strictly grounded in employee-authorized workplace knowledge.

---

## 2. Proposed Workplace Architecture & Migration Plan

### 2.1 Role-Based Routing (`frontend/src/App.tsx`)
```text
LOGIN
  ├── role == "admin"    ──► /admin (Overview, Employees, Knowledge, Collections, Access, Analytics, Settings, AI Workspace)
  └── role == "employee" ──► /chat  (Distraction-free Workplace AI Chat + /profile)
```
- If an employee navigates to `/admin` or any `/admin/*` path, the frontend immediately redirects to `/chat` and the backend rejects `/api/admin/*`, `/api/system/*`, `/api/users/*`, and management endpoints with HTTP `403`.
- Local Employee Invitation Flow (`/activate` or Login "Activate Invite" tab): Admin can invite an employee and generate a local invite code/token; the employee sets their password locally without requiring external cloud email servers.

### 2.2 Database Schema Additions (Non-Destructive via `run_safe_schema_migrations`)
- `workspaces` table (representing `Workplace`):
  - `slug` (`VARCHAR(100)`)
  - `logo` (`TEXT`)
  - `industry` (`VARCHAR(100)`)
  - `created_by` (`VARCHAR(100)`)
  - `status` (`VARCHAR(30) DEFAULT 'ACTIVE'`)
  - `assistant_name` (`VARCHAR(100) DEFAULT 'ONYX AI'`)
  - `welcome_message` (`TEXT DEFAULT 'Ask anything about your workplace knowledge.'`)
  - `default_doc_visibility` (`VARCHAR(40) DEFAULT 'EMPLOYEE_SHARED'`)
  - `allow_employee_uploads` (`BOOLEAN DEFAULT 0`)
  - `session_duration_minutes` (`INTEGER DEFAULT 1440`)
  - `onboarding_completed` (`BOOLEAN DEFAULT 1`)
- `users` table:
  - `invite_token` (`VARCHAR(100)`)
  - `invite_status` (`VARCHAR(30) DEFAULT 'ACCEPTED'`)
  - `last_active_at` (`DATETIME`)
- `documents` table:
  - `is_archived` (`BOOLEAN DEFAULT 0`)
- `chunks` table:
  - `workspace_id` (`VARCHAR(36)`)
- `audit_logs` table:
  - `workspace_id` (`VARCHAR(36)`)

### 2.3 Cross-Workplace Isolation & RAG Changes
- `AuthorizationService.filter_authorized_documents()` enforces `Document.workspace_id == user.workspace_id` and excludes `Document.is_archived == True` (unless `include_archived=True` is passed by an Admin).
- `VectorStore.upsert_chunks()` writes `workplace_id` and `workspace_id` to every vector's metadata.
- `HybridRetriever.retrieve()` scopes SQLite `ChunkRecord` and ChromaDB vector queries by `authorized_document_ids` (which are strictly bound to `user.workspace_id`).
- When an employee asks a question with no authorized matching evidence, the response returns the access-aware message:
  `"I couldn't find enough information in the knowledge available to your account."` (without disclosing whether restricted documents exist).

### 2.4 Migration Risks & Mitigations
- **Existing Tests Compatibility**: Existing tests in `tests/test_rag_system.py`, `tests/test_structured_workspace.py`, and `tests/test_rbac_and_document_security.py` must continue to pass. We preserve existing API contracts while adding workplace isolation, `/api/workplaces/*`, `/api/admin/analytics`, document archiving, and employee invitation endpoints.
