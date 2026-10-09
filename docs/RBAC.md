# Role-Based & Attribute-Based Access Control (`docs/RBAC.md`)

## 1. Primary Roles
The system implements two primary organizational roles while storing descriptive job titles separately:

1. **Administrator (`role = "admin"`)**
   - Examples of `job_title`: `HR Manager`, `Head of Department`, `System Administrator`, `Authorized Management`.
   - Effective Permissions: `["*"]`
   - Scope: Full organizational access to documents, collections, user management, department/group management, access policy configuration, access simulation, and security audit logs.

2. **Employee / Visitor (`role = "employee"`)**
   - Examples of `job_title`: `Software Developer`, `Financial Analyst`, `Designer`, `Sales Representative`, `Intern`.
   - Default Effective Permissions (configurable by Admin via `PUT /api/admin/permissions/employee-defaults` or per-user):
     - `document.read`
     - `document.upload`
     - `collection.read`
     - `database.read`
     - `rag.search`
     - `rag.ask`
   - Scope: **Deny by Default**. Can only view, search, or ask questions over documents explicitly authorized via `EMPLOYEE_SHARED`, their primary `Department`, their assigned `Groups`, or `USER_SPECIFIC` grants.

## 2. Departments & Groups
- **Departments (`departments` table)**: Default departments include `Engineering`, `HR`, `Finance`, `Marketing`, `Sales`, `Operations`, and `Management`. Each user can be assigned a primary `department_id`.
- **Groups (`groups` & `user_groups` tables)**: Default groups include `Managers`, `HR Team`, `Engineering Team`, `Finance Team`, `Project Alpha`, `Project Beta`, and `Leadership`. Users can belong to multiple groups simultaneously.
