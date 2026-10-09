# Security Audit Logging (`docs/AUDIT_LOGGING.md`)

## 1. Overview
All security-sensitive operations are recorded in the local SQLite `audit_logs` table via `record_audit_log()` in [`backend/auth/audit.py`](file:///c:/Users/devik/Desktop/rag/backend/auth/audit.py) and exposed exclusively to administrators via `GET /api/admin/audit-logs`.

## 2. Recorded Fields
- `id`: UUID primary key
- `timestamp`: UTC ISO-8601 timestamp
- `user_id`: Authenticated user UUID (if applicable)
- `username`: Username (`admin`, `member`, etc.)
- `user_role`: Normalized role (`admin`, `employee`, or `unauthenticated`)
- `action`: Standardized event code
- `resource_type`: Target entity type (`auth`, `user`, `department`, `group`, `collection`, `document`, `search`, `chat`, `database`, `permissions`)
- `resource_id`: Target entity UUID
- `success`: Boolean (`True` / `False`)
- `severity`: `INFO`, `WARNING`, or `ALERT`
- `ip_address`: Client IP address
- `details_json`: Sanitized metadata JSON

## 3. Audited Actions & Security Alerts
- **Authentication & Sessions**: `ADMIN_LOGIN`, `EMPLOYEE_LOGIN`, `LOGIN_FAILED`, `LOGIN_RATE_LIMITED` (`ALERT`), `LOGIN_BLOCKED_INACTIVE`, `LOGOUT`
- **User & Role Administration**: `USER_CREATED`, `ROLE_CHANGED` (`WARNING`), `USER_DISABLED` (`WARNING`), `USER_REACTIVATED`, `ROLE_ESCALATION_ATTEMPT` (`ALERT`), `UNAUTHORIZED_USER_MODIFICATION_ATTEMPT` (`ALERT`)
- **Departments, Groups & Permissions**: `DEPARTMENT_CREATED`, `DEPARTMENT_DELETED`, `GROUP_CREATED`, `GROUP_MEMBERS_UPDATED`, `GROUP_DELETED`, `EMPLOYEE_DEFAULT_PERMISSIONS_CHANGED`
- **Document & Collection Access Control**: `DOCUMENT_UPLOAD`, `DOCUMENT_VIEW`, `DOCUMENT_DOWNLOAD`, `DOCUMENT_DELETE`, `ACCESS_POLICY_CHANGED`, `UNAUTHORIZED_DOCUMENT_ACCESS_ATTEMPT` (`WARNING`), `UNAUTHORIZED_DOWNLOAD_ATTEMPT` (`WARNING`), `COLLECTION_CREATED`, `COLLECTION_ACCESS_CHANGED`, `COLLECTION_DELETED`
- **RAG & Database Queries**: `RAG_SEARCH`, `RAG_QUERY`, `DATABASE_QUERY`, `DATABASE_INGESTED`, `INTERNAL_DB_ACCESS_BLOCKED` (`ALERT`)

## 4. Data Sanitization Rule
`sanitize_audit_details()` automatically strips sensitive keys (`password`, `password_hash`, `secret`, `token`, `access_token`, `raw_content`, `content`) so neither user credentials nor confidential document text are ever written to audit logs.
