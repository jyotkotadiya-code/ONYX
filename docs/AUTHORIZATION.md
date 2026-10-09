# Authorization Engine (`docs/AUTHORIZATION.md`)

## 1. Core Security Principle
**Authentication ≠ Authorization.** Every authenticated request is evaluated by the central `AuthorizationService` in [`backend/auth/authorization.py`](file:///c:/Users/devik/Desktop/rag/backend/auth/authorization.py) **before** any file, collection, database table, or vector chunk is accessed.

## 2. Policy Evaluation Pipeline
```text
Authentication (JWT + Active UserSession + Active Account Status)
      ↓
Identity (User ID, Role, Primary Department, Group Memberships)
      ↓
Permission Check (e.g., document.read, rag.ask, rag.search)
      ↓
Collection & Document Access Policy Evaluation
      ↓
Pre-Retrieval Authorized Document Scope (authorized_document_ids)
      ↓
Filtered ChromaDB Vector Search + Filtered BM25 + Filtered SQL Query
      ↓
Authorized Context Only -> Local Llama -> Grounded Structured Response
```

## 3. Deterministic Policy Priority
When evaluating `authorization_service.evaluate_document_access(db, user, document, action)`:
1. **Account Status Check**: If `user.status != "ACTIVE"`, immediately `DENY`.
2. **Admin Role**: If `user.is_admin`, `ALLOW` across organizational knowledge.
3. **Action Permission Check**: Verify user holds the required action permission (`document.read`, `document.upload`, `document.delete`, etc.).
4. **Explicit DENY Rules**: If any `DocumentAccess` row has `access_type == "EXPLICIT_DENY"` matching the user, their group, or their department, immediately `DENY`.
5. **Approval Status Check**: If `document.approval_status != "APPROVED"`, only the uploader or an administrator is allowed.
6. **Document Access Level Resolution**:
   - `ADMIN_ONLY`: Denied for all employees.
   - `USER_SPECIFIC`: Allowed only if `user.id` is the owner or explicitly listed in `DocumentAccess(USER_SPECIFIC)`.
   - `GROUP_ONLY`: Allowed only if the user is a member of a group listed in `DocumentAccess(GROUP_ONLY)`.
   - `DEPARTMENT_ONLY`: Allowed only if `user.department_id` matches `document.department_id` or a `DocumentAccess(DEPARTMENT_ONLY)` rule.
   - `EMPLOYEE_SHARED`: Allowed if the employee has access to the parent collection.
7. **Default Fallback**: `DENY`.
