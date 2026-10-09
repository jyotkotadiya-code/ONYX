import json
from typing import Any, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.auth.permissions import get_effective_permissions, user_has_permission
from backend.auth.policies import PolicyDecision
from backend.database.sqlite_db import (
    Collection,
    CollectionAccess,
    Department,
    Document,
    DocumentAccess,
    Group,
    SavedArtifact,
    User,
    UserGroup,
)


class AuthorizationService:
    """
    Central deterministic Workplace Isolation + RBAC + ABAC + Document-Level Policy Engine.
    Guarantees:
    - ZERO cross-workplace data access (even for admins of another workplace)
    - DENY BY DEFAULT for all non-admin users
    - Pre-retrieval filtering of archived and unauthorized documents

    Policy Evaluation Priority:
    0. Workplace Isolation check (`resource.workspace_id != user.workspace_id` -> immediate DENY)
    1. Account status check (SUSPENDED / DISABLED / INVITED -> immediate DENY)
    2. Archive check (`document.is_archived` -> DENY for employees unless `include_archived=True` for admin)
    3. Admin role check (Active Admin in same workplace -> ALLOWED across workplace resources)
    4. Explicit DENY rule (`EXPLICIT_DENY` / `DENY_USER` on document or collection -> DENY)
    5. Pending approval check (`PENDING_REVIEW` / `REJECTED` -> only owner or admin allowed)
    6. Collection access gate (User must have access to the parent collection OR explicit document grant)
    7. Document access policy resolution (`ADMIN_ONLY`, `EMPLOYEE_SHARED`, `DEPARTMENT_ONLY`, `GROUP_ONLY`, `USER_SPECIFIC`)
    8. Default -> DENY
    """

    def get_user_group_ids(self, db: Session, user_id: str) -> set[str]:
        rows = db.query(UserGroup.group_id).filter(UserGroup.user_id == user_id).all()
        return {r[0] for r in rows if r[0]}

    def require_permission(self, user: User, permission: str) -> None:
        if (user.status or "ACTIVE").upper() != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active.",
            )
        if not user_has_permission(user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to access this resource.",
            )

    def evaluate_collection_access(
        self,
        db: Session,
        user: User,
        collection: Collection,
    ) -> PolicyDecision:
        # 0. Strict Workplace Isolation
        if collection.workspace_id and user.workspace_id and collection.workspace_id != user.workspace_id:
            return PolicyDecision(False, "Collection belongs to a different workplace", "cross_workplace_deny")

        if (user.status or "ACTIVE").upper() != "ACTIVE":
            return PolicyDecision(False, "User account is suspended or disabled", "account_inactive")

        if user.is_admin:
            return PolicyDecision(True, "Administrator full workplace access", "admin_role")

        if not user_has_permission(user, "collection.read"):
            return PolicyDecision(False, "Missing collection.read permission", "missing_permission")

        rules = (
            db.query(CollectionAccess)
            .filter(CollectionAccess.collection_id == collection.id)
            .all()
        )
        user_groups = self.get_user_group_ids(db, user.id)

        # 1. Explicit DENY on collection
        for r in rules:
            if r.access_type == "DENY_USER" and r.user_id == user.id:
                return PolicyDecision(False, "Explicitly denied collection access", "collection_explicit_deny")

        # 2. Check collection access_level
        col_level = (collection.access_level or "EMPLOYEE_SHARED").upper()
        if col_level == "ADMIN_ONLY":
            for r in rules:
                if r.access_type == "USER" and r.user_id == user.id:
                    return PolicyDecision(True, "Explicit user grant on collection", "collection_user_grant")
                if r.access_type == "GROUP" and r.group_id in user_groups:
                    return PolicyDecision(True, "Group grant on collection", "collection_group_grant")
                if r.access_type == "DEPARTMENT" and user.department_id and r.department_id == user.department_id:
                    return PolicyDecision(True, "Department grant on collection", "collection_department_grant")
            return PolicyDecision(False, f"Collection '{collection.name}' is restricted to Administrators", "collection_admin_only")

        if col_level == "DEPARTMENT_ONLY":
            if user.department_id and collection.department_id == user.department_id:
                return PolicyDecision(True, "Primary department matches collection department", "collection_department_match")
            for r in rules:
                if r.access_type == "DEPARTMENT" and user.department_id and r.department_id == user.department_id:
                    return PolicyDecision(True, "Department rule matches collection", "collection_department_rule")
                if r.access_type == "GROUP" and r.group_id in user_groups:
                    return PolicyDecision(True, "Group rule matches collection", "collection_group_rule")
                if r.access_type == "USER" and r.user_id == user.id:
                    return PolicyDecision(True, "User rule matches collection", "collection_user_rule")
            return PolicyDecision(False, f"Collection '{collection.name}' is restricted to specific departments", "collection_department_mismatch")

        if col_level == "GROUP_ONLY":
            for r in rules:
                if r.access_type == "GROUP" and r.group_id in user_groups:
                    return PolicyDecision(True, "Group membership matches collection policy", "collection_group_match")
                if r.access_type == "USER" and r.user_id == user.id:
                    return PolicyDecision(True, "Explicit user grant on collection", "collection_user_grant")
            return PolicyDecision(False, f"Collection '{collection.name}' is restricted to specific groups", "collection_group_mismatch")

        # For EMPLOYEE_SHARED or legacy collections: check user.allowed_collections + rules
        for r in rules:
            if r.access_type == "USER" and r.user_id == user.id:
                return PolicyDecision(True, "Explicit user grant on collection", "collection_user_grant")
            if r.access_type == "GROUP" and r.group_id in user_groups:
                return PolicyDecision(True, "Group grant on collection", "collection_group_grant")
            if r.access_type == "DEPARTMENT" and user.department_id and r.department_id == user.department_id:
                return PolicyDecision(True, "Department grant on collection", "collection_department_grant")

        allowed_cols = user.allowed_collections
        if "*" in allowed_cols or collection.name in allowed_cols:
            if collection.is_private and collection.name not in allowed_cols and "*" not in allowed_cols:
                return PolicyDecision(False, "Private collection not in user allowed list", "collection_private_deny")
            return PolicyDecision(True, f"Collection '{collection.name}' is accessible to employee", "collection_employee_shared")

        return PolicyDecision(False, f"User is not authorized for collection '{collection.name}'", "collection_default_deny")

    def can_access_collection_by_name(
        self,
        db: Session,
        user: User,
        collection_name: str,
    ) -> bool:
        if (user.status or "ACTIVE").upper() != "ACTIVE":
            return False
        if user.is_admin:
            return True
        col = (
            db.query(Collection)
            .filter(
                Collection.name == collection_name,
                Collection.workspace_id == user.workspace_id,
            )
            .first()
        )
        if not col:
            allowed_cols = user.allowed_collections
            return "*" in allowed_cols or collection_name in allowed_cols
        return self.evaluate_collection_access(db, user, col).allowed

    def evaluate_document_access(
        self,
        db: Session,
        user: User,
        document: Document,
        action: str = "read",
        include_archived: bool = False,
    ) -> PolicyDecision:
        """
        Deterministic workplace-scoped document-level policy evaluation.
        """
        # 0. Strict Workplace Isolation (never allow cross-workplace access even for admins)
        if document.workspace_id and user.workspace_id and document.workspace_id != user.workspace_id:
            return PolicyDecision(False, "Document belongs to a different workplace", "cross_workplace_deny")

        if (user.status or "ACTIVE").upper() != "ACTIVE":
            return PolicyDecision(False, "User account is suspended or disabled", "account_inactive")

        # Archive check: Employees can never access archived documents; admins can access when include_archived=True or managing
        is_archived = bool(getattr(document, "is_archived", False)) or (document.status or "").upper() == "ARCHIVED"
        if is_archived and not user.is_admin:
            return PolicyDecision(False, "Document is archived and inactive", "document_archived")

        # 1. Admin always has full workplace access
        if user.is_admin:
            return PolicyDecision(True, "Administrator full workplace access", "admin_role")

        # 2. Action permission check
        perm_map = {
            "read": "document.read",
            "upload": "document.upload",
            "delete": "document.delete",
            "update": "document.update",
            "share": "document.share",
            "manage_access": "document.manage_access",
        }
        required_perm = perm_map.get(action, f"document.{action}")
        if not user_has_permission(user, required_perm):
            return PolicyDecision(False, f"Missing '{required_perm}' permission", "missing_permission")

        # 3. Fetch explicit DocumentAccess rules
        rules = (
            db.query(DocumentAccess)
            .filter(DocumentAccess.document_id == document.id)
            .all()
        )
        user_groups = self.get_user_group_ids(db, user.id)

        # 4. Explicit DENY rule takes highest priority
        for r in rules:
            if r.access_type == "EXPLICIT_DENY":
                if r.user_id == user.id:
                    return PolicyDecision(False, "Explicit user deny rule on document", "explicit_user_deny")
                if r.group_id and r.group_id in user_groups:
                    return PolicyDecision(False, "Explicit group deny rule on document", "explicit_group_deny")
                if r.department_id and user.department_id and r.department_id == user.department_id:
                    return PolicyDecision(False, "Explicit department deny rule on document", "explicit_department_deny")

        # 5. Unapproved / Pending Review document check
        approval = (document.approval_status or "APPROVED").upper()
        if approval != "APPROVED":
            if document.owner_id == user.id or document.owner == user.username:
                return PolicyDecision(True, "Uploader accessing own pending document", "owner_pending_access")
            return PolicyDecision(False, "Document is pending administrator review", "pending_admin_review")

        doc_level = (document.access_level or "EMPLOYEE_SHARED").upper()

        # 6. ADMIN_ONLY policy strictly blocks non-admin users
        if doc_level == "ADMIN_ONLY":
            return PolicyDecision(False, "Admin-only document policy", "document_admin_only")

        # 7. Check explicit user, group, or department rules in DocumentAccess
        has_dept_rules = False

        for r in rules:
            rtype = (r.access_type or "").upper()
            if rtype == "USER_SPECIFIC":
                if r.user_id == user.id:
                    return PolicyDecision(True, f"Explicit user access granted to '{user.username}'", "explicit_user_access")
            elif rtype == "GROUP_ONLY":
                if r.group_id and r.group_id in user_groups:
                    grp = db.query(Group).filter(Group.id == r.group_id).first()
                    grp_name = grp.name if grp else r.group_id
                    return PolicyDecision(True, f"Group access via '{grp_name}'", "group_access")
            elif rtype == "DEPARTMENT_ONLY":
                has_dept_rules = True
                if r.department_id and user.department_id and r.department_id == user.department_id:
                    dept = db.query(Department).filter(Department.id == r.department_id).first()
                    dept_name = dept.name if dept else r.department_id
                    return PolicyDecision(True, f"{dept_name} department access", "department_access")
            elif rtype == "EMPLOYEE_SHARED":
                if self.can_access_collection_by_name(db, user, document.collection_name):
                    return PolicyDecision(True, "Employee-shared document access", "employee_shared_rule")

        # 8. Evaluate primary document.access_level
        if doc_level == "USER_SPECIFIC":
            if document.owner_id == user.id or document.owner == user.username:
                return PolicyDecision(True, "Document owner access", "document_owner")
            return PolicyDecision(False, "Document is restricted to specific assigned users", "user_specific_deny")

        if doc_level == "GROUP_ONLY":
            return PolicyDecision(False, "Document is restricted to specific assigned groups", "group_only_deny")

        if doc_level == "DEPARTMENT_ONLY":
            if document.department_id and user.department_id and document.department_id == user.department_id:
                dept = db.query(Department).filter(Department.id == document.department_id).first()
                dept_name = dept.name if dept else document.department_id
                return PolicyDecision(True, f"{dept_name} department access", "department_access")
            if has_dept_rules:
                return PolicyDecision(False, "User department does not match document department policy", "department_mismatch")
            return PolicyDecision(False, "Document is restricted to a specific department", "department_only_deny")

        if doc_level == "EMPLOYEE_SHARED":
            if self.can_access_collection_by_name(db, user, document.collection_name):
                return PolicyDecision(True, "Shared with all employees in accessible collection", "employee_shared")
            return PolicyDecision(False, f"Collection '{document.collection_name}' is not accessible to user", "collection_restricted")

        # 9. Default DENY
        return PolicyDecision(False, "Denied by default security policy", "default_deny")

    def can_access(
        self,
        db: Session,
        user: User,
        resource: Any,
        action: str = "read",
    ) -> bool:
        if isinstance(resource, Document):
            return self.evaluate_document_access(db, user, resource, action=action).allowed
        if isinstance(resource, Collection):
            return self.evaluate_collection_access(db, user, resource).allowed
        if isinstance(resource, SavedArtifact):
            return self.can_access_artifact(db, user, resource, action=action)
        return False

    def filter_authorized_documents(
        self,
        db: Session,
        user: User,
        collection_filter: Optional[str] = None,
        only_ready: bool = False,
        include_archived: bool = False,
    ) -> list[Document]:
        """
        Return the exact list of Document objects in `user.workspace_id` that `user` is authorized to read.
        """
        if (user.status or "ACTIVE").upper() != "ACTIVE":
            return []

        q = db.query(Document).filter(Document.workspace_id == user.workspace_id)
        if not include_archived:
            q = q.filter((Document.is_archived == False) | (Document.is_archived == None))
            q = q.filter(Document.status != "Archived")
        if only_ready:
            q = q.filter(Document.status == "Ready")
        if collection_filter and collection_filter.upper() != "ALL":
            q = q.filter(Document.collection_name == collection_filter)

        all_docs = q.order_by(Document.updated_at.desc()).all()
        if user.is_admin:
            return all_docs

        authorized: list[Document] = []
        for doc in all_docs:
            decision = self.evaluate_document_access(
                db, user, doc, action="read", include_archived=include_archived
            )
            if decision.allowed:
                authorized.append(doc)
        return authorized

    def get_authorized_document_ids(
        self,
        db: Session,
        user: User,
        collection_filter: Optional[str] = None,
        include_archived: bool = False,
    ) -> list[str]:
        """
        Compute the exact list of `document_id` strings in `user.workspace_id` that `user` is permitted
        to retrieve from the vector store and relational chunk store BEFORE any RAG or search query executes.
        """
        docs = self.filter_authorized_documents(
            db=db,
            user=user,
            collection_filter=collection_filter,
            only_ready=True,
            include_archived=include_archived if user.is_admin else False,
        )
        return [d.id for d in docs]

    def can_access_artifact(
        self,
        db: Session,
        user: User,
        artifact: SavedArtifact,
        action: str = "read",
    ) -> bool:
        """
        Verify workplace isolation, artifact ownership/visibility, AND authorization for every underlying source document.
        """
        if artifact.workspace_id and user.workspace_id and artifact.workspace_id != user.workspace_id:
            return False
        if (user.status or "ACTIVE").upper() != "ACTIVE":
            return False
        if user.is_admin:
            return True
        if action in {"update", "delete"} and artifact.owner_id != user.id:
            return False
        if artifact.visibility == "ADMIN_ONLY":
            return False
        if artifact.visibility == "PRIVATE" and artifact.owner_id != user.id:
            return False

        source_ids = artifact.source_document_ids
        if source_ids:
            for sid in source_ids:
                if not sid:
                    continue
                doc = db.query(Document).filter(Document.id == sid).first()
                if doc and not self.evaluate_document_access(db, user, doc, action="read").allowed:
                    return False
        return True

    def preview_user_access(self, db: Session, target_user: User) -> dict[str, Any]:
        """
        Read-only simulation for admins ("Preview access as user").
        Computes accessible documents, collections, and effective permissions within the user's workplace.
        """
        dept = (
            db.query(Department).filter(Department.id == target_user.department_id).first()
            if target_user.department_id
            else None
        )
        group_ids = self.get_user_group_ids(db, target_user.id)
        groups = db.query(Group).filter(Group.id.in_(group_ids)).all() if group_ids else []

        all_cols = (
            db.query(Collection)
            .filter(Collection.workspace_id == target_user.workspace_id)
            .order_by(Collection.name)
            .all()
        )
        accessible_collections = []
        for c in all_cols:
            dec = self.evaluate_collection_access(db, target_user, c)
            if dec.allowed:
                accessible_collections.append(
                    {
                        "id": c.id,
                        "name": c.name,
                        "access_level": c.access_level,
                        "reason": dec.reason,
                    }
                )

        all_docs = (
            db.query(Document)
            .filter(Document.workspace_id == target_user.workspace_id)
            .order_by(Document.filename)
            .all()
        )
        accessible_docs = []
        denied_docs_count = 0
        for d in all_docs:
            dec = self.evaluate_document_access(db, target_user, d, action="read")
            if dec.allowed:
                accessible_docs.append(
                    {
                        "id": d.id,
                        "filename": d.filename,
                        "collection": d.collection_name,
                        "access_level": d.access_level,
                        "is_archived": bool(getattr(d, "is_archived", False)),
                        "reason": dec.reason,
                        "matched_rule": dec.matched_rule,
                    }
                )
            else:
                denied_docs_count += 1

        return {
            "user": {
                "id": target_user.id,
                "username": target_user.username,
                "name": target_user.name or target_user.username,
                "email": target_user.email or "",
                "role": target_user.normalized_role,
                "job_title": target_user.job_title or "Employee",
                "status": target_user.status or "ACTIVE",
                "workplace_id": target_user.workspace_id,
                "department": dept.name if dept else None,
                "groups": [g.name for g in groups],
            },
            "effective_permissions": get_effective_permissions(target_user),
            "accessible_collections": accessible_collections,
            "accessible_documents": accessible_docs,
            "summary": {
                "accessible_collections_count": len(accessible_collections),
                "accessible_documents_count": len(accessible_docs),
                "restricted_documents_hidden": denied_docs_count,
            },
        }


authorization_service = AuthorizationService()
