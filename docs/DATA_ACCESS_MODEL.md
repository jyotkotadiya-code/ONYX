# Data Access & Pre-Retrieval RAG Security Model (`docs/DATA_ACCESS_MODEL.md`)

## 1. Document Access Levels
Every document in the system carries an explicit `access_level` and optional granular `DocumentAccess` rules:

| Access Level | Who Can Access | Example Use Case |
| :--- | :--- | :--- |
| `ADMIN_ONLY` | Administrators only (`role = "admin"`) | `Salary_Report_2026.pdf`, Executive board decks |
| `EMPLOYEE_SHARED` | All active employees with collection access | `Employee_Handbook.pdf`, Leave policy |
| `DEPARTMENT_ONLY` | Admins + members of the specified Department(s) | `Engineering_Guidelines.pdf` → `Engineering` |
| `GROUP_ONLY` | Admins + members of the specified Group(s) | `Project_Alpha_Spec.pdf` → `Project Alpha` |
| `USER_SPECIFIC` | Admins + document owner + explicitly selected Users | Individual performance review or private draft |

## 2. Pre-Retrieval RAG Filtering
To guarantee that **unauthorized chunks never reach the local Llama model or leak via citations**:
1. On every `POST /api/search` and `POST /api/chat` request, the backend first calls `authorization_service.get_authorized_document_ids(db, current_user, collection_filter)`.
2. This list of `authorized_document_ids` is passed into:
   - `vector_store.query_similar(..., authorized_document_ids=authorized_doc_ids)` which applies a strict ChromaDB metadata filter `{"document_id": {"$in": authorized_doc_ids}}` **during** vector search.
   - `retriever.retrieve(..., authorized_document_ids=authorized_doc_ids)` which restricts SQLite `ChunkRecord` queries for BM25 and exact matching to `ChunkRecord.document_id.in_(authorized_doc_ids)`.
   - `plan_and_execute_database_query(..., authorized_document_ids=authorized_doc_ids)` which restricts natural-language SQL queries strictly to authorized database documents.
3. When an admin modifies a document's access policy (`PUT /api/documents/{id}/access`), `vector_store.update_document_access_metadata()` updates the ChromaDB metadata in-place immediately without requiring re-embedding.
