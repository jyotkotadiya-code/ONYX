import json
from typing import Optional
from backend.database.sqlite_db import User

ALL_PERMISSIONS: dict[str, str] = {
    "document.read": "View and read authorized documents",
    "document.upload": "Upload new documents to the workspace",
    "document.delete": "Delete documents and vectors",
    "document.update": "Modify document metadata or re-index",
    "document.share": "Share documents with users or groups",
    "document.manage_access": "Configure document-level access policies",
    "collection.read": "View authorized collections",
    "collection.create": "Create new knowledge collections",
    "collection.delete": "Delete collections",
    "user.read": "View organizational users, departments, and groups",
    "user.create": "Create new user accounts",
    "user.update": "Edit user roles, departments, groups, and permissions",
    "user.disable": "Suspend or disable user accounts",
    "audit.read": "View security audit logs and alerts",
    "database.read": "Query authorized structured database sources",
    "rag.search": "Search across authorized knowledge base",
    "rag.ask": "Ask AI questions over authorized knowledge",
}

DEFAULT_ADMIN_PERMISSIONS: list[str] = ["*"]

DEFAULT_EMPLOYEE_PERMISSIONS: list[str] = [
    "document.read",
    "document.upload",
    "collection.read",
    "database.read",
    "rag.search",
    "rag.ask",
]

# Runtime configurable default permissions for the employee role
_employee_role_default_permissions: set[str] = set(DEFAULT_EMPLOYEE_PERMISSIONS)


def get_default_employee_permissions() -> list[str]:
    return sorted(_employee_role_default_permissions)


def set_default_employee_permissions(perms: list[str]) -> list[str]:
    global _employee_role_default_permissions
    valid = {p for p in perms if p in ALL_PERMISSIONS}
    _employee_role_default_permissions = valid
    return sorted(_employee_role_default_permissions)


def get_effective_permissions(user: User) -> list[str]:
    """
    Calculate effective permissions for a user.
    - Active admins receive ["*"] (all permissions).
    - Employees receive their explicit custom_permissions if non-empty, or the configurable employee default permissions,
      adjusted by user.can_upload.
    """
    if (user.status or "ACTIVE").upper() != "ACTIVE":
        return []
    if user.is_admin:
        return ["*"]

    custom = user.custom_permissions
    if custom:
        perms = {p for p in custom if p in ALL_PERMISSIONS}
    else:
        perms = set(_employee_role_default_permissions)

    if not user.can_upload:
        perms.discard("document.upload")
    elif user.can_upload and not custom:
        perms.add("document.upload")

    return sorted(perms)


def user_has_permission(user: Optional[User], permission: str) -> bool:
    if not user:
        return False
    if (user.status or "ACTIVE").upper() != "ACTIVE":
        return False
    if user.is_admin:
        return True
    effective = get_effective_permissions(user)
    if "*" in effective:
        return True
    return permission in effective
