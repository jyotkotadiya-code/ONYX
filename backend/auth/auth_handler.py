import json
import re
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from backend.auth.authorization import authorization_service
from backend.auth.permissions import DEFAULT_EMPLOYEE_PERMISSIONS
from backend.core.config import settings
from backend.core.logging_config import app_logger
from backend.database.sqlite_db import (
    Base,
    ChunkRecord,
    Collection,
    Department,
    Document,
    Group,
    SessionLocal,
    User,
    UserGroup,
    UserSession,
    Workspace,
    engine,
    get_db,
    run_safe_schema_migrations,
)

ph = PasswordHasher()
security_scheme = HTTPBearer(auto_error=False)

DEFAULT_DEPARTMENTS = [
    ("Engineering", "Software engineering, architecture, infrastructure, and AI"),
    ("HR", "Human resources, people operations, compensation, and policies"),
    ("Finance", "Accounting, financial statements, budgets, and payroll"),
    ("Marketing", "Brand, product marketing, and growth"),
    ("Sales", "Enterprise sales, revenue operations, and accounts"),
    ("Operations", "Business operations, compliance, and administration"),
    ("Management", "Executive leadership and department heads"),
]

DEFAULT_GROUPS = [
    ("Managers", "Department managers and team leads"),
    ("HR Team", "Human resources specialists and administrators"),
    ("Engineering Team", "Core software and platform engineers"),
    ("Finance Team", "Financial analysts and controllers"),
    ("Project Alpha", "Cross-functional Project Alpha team"),
    ("Project Beta", "Cross-functional Project Beta team"),
    ("Leadership", "Executive leadership group"),
]

DEFAULT_COLLECTIONS = [
    ("General", "Company-wide general knowledge and policies", "EMPLOYEE_SHARED", False),
    ("Company Policies", "Leave policy, handbook, and company-wide guidelines", "EMPLOYEE_SHARED", False),
    ("Projects", "Project plans, roadmaps, and engineering deliverables", "EMPLOYEE_SHARED", False),
    ("Finance", "Financial reports, invoices, budgets, and Q1-Q4 statements", "EMPLOYEE_SHARED", False),
    ("HR", "Human resources, onboarding, and confidential HR records", "EMPLOYEE_SHARED", False),
    ("Research", "Research papers, architecture specs, and benchmarks", "EMPLOYEE_SHARED", False),
    ("Product", "Product requirements and user documentation", "EMPLOYEE_SHARED", False),
    ("Engineering", "Technical architecture, schemas, and operations", "DEPARTMENT_ONLY", False),
    ("Management", "Executive leadership reports and strategic plans", "ADMIN_ONLY", True),
]

# In-memory sliding window login rate limiter (per username/IP)
_failed_login_timestamps: dict[str, list[float]] = defaultdict(list)
LOGIN_WINDOW_SECONDS = 300  # 5 minutes
MAX_FAILED_LOGINS = 10


def slugify_workplace_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (name or "workplace").strip().lower()).strip("-")
    return slug or "workplace"


def check_login_rate_limit(key: str) -> bool:
    """Return True if allowed, False if rate-limited due to excessive failed attempts."""
    now = time.time()
    recent = [t for t in _failed_login_timestamps[key] if now - t < LOGIN_WINDOW_SECONDS]
    _failed_login_timestamps[key] = recent
    return len(recent) < MAX_FAILED_LOGINS


def record_failed_login_attempt(key: str) -> int:
    now = time.time()
    recent = [t for t in _failed_login_timestamps[key] if now - t < LOGIN_WINDOW_SECONDS]
    recent.append(now)
    _failed_login_timestamps[key] = recent
    return len(recent)


def clear_failed_login_attempts(key: str) -> None:
    _failed_login_timestamps.pop(key, None)


def hash_password(password: str) -> str:
    """Hash a password using Argon2id (never store plaintext)."""
    return ph.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a password against its Argon2 hash."""
    try:
        return ph.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    db: Optional[Session] = None,
    user: Optional[User] = None,
    ip_address: Optional[str] = None,
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    jti = str(uuid.uuid4())
    to_encode.update(
        {
            "exp": expire,
            "jti": jti,
            "tv": user.token_version if user else 1,
            "wid": user.workspace_id if user else None,
        }
    )
    encoded = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    if db is not None and user is not None:
        sess = UserSession(
            user_id=user.id,
            token_jti=jti,
            ip_address=ip_address or "127.0.0.1",
            is_active=True,
            expires_at=expire,
        )
        db.add(sess)
        db.commit()
    return encoded


def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return None


def invalidate_user_sessions(db: Session, user: User) -> None:
    """Immediately invalidate all active sessions and increment token_version for a user."""
    user.token_version = (user.token_version or 1) + 1
    now = datetime.now(timezone.utc)
    active_sessions = (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.is_active == True)
        .all()
    )
    for s in active_sessions:
        s.is_active = False
        s.revoked_at = now
    db.commit()


def seed_workplace_structure(
    db: Session,
    workspace: Workspace,
    created_by: str = "admin",
) -> tuple[dict[str, Department], dict[str, Group]]:
    """
    Ensure a Workplace has its own isolated default Departments, Groups, and Collections.
    """
    dept_map: dict[str, Department] = {}
    for d_name, d_desc in DEFAULT_DEPARTMENTS:
        existing_dept = (
            db.query(Department)
            .filter(Department.name == d_name, Department.workspace_id == workspace.id)
            .first()
        )
        if not existing_dept:
            existing_dept = Department(
                name=d_name,
                description=d_desc,
                workspace_id=workspace.id,
                created_by=created_by,
            )
            db.add(existing_dept)
            db.commit()
            db.refresh(existing_dept)
        dept_map[d_name] = existing_dept

    group_map: dict[str, Group] = {}
    for g_name, g_desc in DEFAULT_GROUPS:
        existing_grp = (
            db.query(Group)
            .filter(Group.name == g_name, Group.workspace_id == workspace.id)
            .first()
        )
        if not existing_grp:
            existing_grp = Group(
                name=g_name,
                description=g_desc,
                workspace_id=workspace.id,
                created_by=created_by,
            )
            db.add(existing_grp)
            db.commit()
            db.refresh(existing_grp)
        group_map[g_name] = existing_grp

    for col_name, col_desc, col_access, is_priv in DEFAULT_COLLECTIONS:
        existing_col = (
            db.query(Collection)
            .filter(Collection.name == col_name, Collection.workspace_id == workspace.id)
            .first()
        )
        eng_dept_id = dept_map["Engineering"].id if col_name == "Engineering" and "Engineering" in dept_map else None
        if not existing_col:
            col = Collection(
                name=col_name,
                description=col_desc,
                workspace_id=workspace.id,
                is_private=is_priv,
                access_level=col_access,
                department_id=eng_dept_id,
                allowed_roles_json=json.dumps(["admin"] if is_priv else ["admin", "employee"]),
                created_by=created_by,
            )
            db.add(col)
        else:
            if not existing_col.access_level:
                existing_col.access_level = col_access
            if col_name == "Engineering" and not existing_col.department_id and eng_dept_id:
                existing_col.department_id = eng_dept_id
    db.commit()
    return dept_map, group_map


def init_db_and_defaults() -> None:
    """
    Run non-destructive schema migrations and seed default ONYX Studio workplace,
    departments, groups, collections, and initial accounts while preserving existing data.
    """
    run_safe_schema_migrations()
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).order_by(Workspace.created_at.asc()).first()
        if not workspace:
            workspace = Workspace(
                name="ONYX Studio",
                slug="onyx-studio",
                description="Creative technology and private AI organization",
                industry="Technology & AI",
                assistant_name="ONYX AI",
                welcome_message="Ask anything about your workplace knowledge.",
                default_doc_visibility="EMPLOYEE_SHARED",
                allow_employee_uploads=False,
                session_duration_minutes=1440,
                onboarding_completed=True,
                created_by="admin",
                status="ACTIVE",
            )
            db.add(workspace)
            db.commit()
            db.refresh(workspace)
            app_logger.info("Created default workplace 'ONYX Studio'")
        else:
            if not workspace.slug:
                workspace.slug = slugify_workplace_name(workspace.name)
            if not workspace.assistant_name:
                workspace.assistant_name = "ONYX AI"
            if not workspace.welcome_message:
                workspace.welcome_message = "Ask anything about your workplace knowledge."
            if not workspace.default_doc_visibility:
                workspace.default_doc_visibility = "EMPLOYEE_SHARED"
            if not workspace.status:
                workspace.status = "ACTIVE"
            db.commit()

        dept_map, group_map = seed_workplace_structure(db, workspace, created_by="system")

        # 4. Ensure default admin user ('admin')
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            admin_user = User(
                name="Jyot Admin",
                email="admin@onyx.local",
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
                job_title="Workplace Administrator",
                department_id=dept_map["Management"].id if "Management" in dept_map else None,
                status="ACTIVE",
                workspace_id=workspace.id,
                allowed_collections_json=json.dumps(["*"]),
                permissions_json=json.dumps(["*"]),
                can_upload=True,
                invite_status="ACCEPTED",
                token_version=1,
            )
            db.add(admin_user)
            app_logger.info("Seeded default admin user: 'admin'")
        else:
            if not admin_user.name:
                admin_user.name = "Jyot Admin"
            if not admin_user.job_title or admin_user.job_title == "Staff":
                admin_user.job_title = "Workplace Administrator"
            if not admin_user.status:
                admin_user.status = "ACTIVE"
            if not admin_user.department_id and "Management" in dept_map:
                admin_user.department_id = dept_map["Management"].id

        # 5. Ensure default employee user ('member')
        member_user = db.query(User).filter(User.username == "member").first()
        if not member_user:
            member_user = User(
                name="Rahul Patel",
                email="rahul@onyx.local",
                username="member",
                password_hash=hash_password("member123"),
                role="employee",
                job_title="Software Developer",
                department_id=dept_map["Engineering"].id if "Engineering" in dept_map else None,
                status="ACTIVE",
                workspace_id=workspace.id,
                allowed_collections_json=json.dumps(
                    ["General", "Company Policies", "Projects", "Research", "Product", "Engineering"]
                ),
                permissions_json=json.dumps(DEFAULT_EMPLOYEE_PERMISSIONS),
                can_upload=False,
                invite_status="ACCEPTED",
                token_version=1,
            )
            db.add(member_user)
            db.commit()
            db.refresh(member_user)
            app_logger.info("Seeded default employee user: 'member'")
        else:
            if not member_user.name:
                member_user.name = "Rahul Patel"
            if not member_user.job_title or member_user.job_title == "Staff":
                member_user.job_title = "Software Developer"
            if not member_user.status:
                member_user.status = "ACTIVE"
            if not member_user.department_id and "Engineering" in dept_map:
                member_user.department_id = dept_map["Engineering"].id
            db.commit()

        existing_ug = db.query(UserGroup).filter(UserGroup.user_id == member_user.id).count()
        if existing_ug == 0:
            for gname in ("Engineering Team", "Project Alpha"):
                if gname in group_map:
                    db.add(UserGroup(user_id=member_user.id, group_id=group_map[gname].id))
            db.commit()

        # 6. Backfill existing documents & chunks with workspace_id and access_level
        docs = db.query(Document).all()
        for doc in docs:
            if not doc.workspace_id:
                doc.workspace_id = workspace.id
            if not doc.access_level:
                if doc.collection_name in {"HR", "Finance", "Management"}:
                    doc.access_level = "ADMIN_ONLY"
                else:
                    doc.access_level = "EMPLOYEE_SHARED"
            if not doc.approval_status:
                doc.approval_status = "APPROVED"
            if doc.is_archived is None:
                doc.is_archived = False
            if not doc.owner_id and doc.owner:
                owner_u = db.query(User).filter(User.username == doc.owner).first()
                if owner_u:
                    doc.owner_id = owner_u.id
        db.commit()

        # Backfill ChunkRecord.workspace_id from parent document
        orphan_chunks = db.query(ChunkRecord).filter(ChunkRecord.workspace_id == None).all()
        if orphan_chunks:
            doc_ws_map = {d.id: d.workspace_id for d in docs}
            for ch in orphan_chunks:
                ch.workspace_id = doc_ws_map.get(ch.document_id, workspace.id)
            db.commit()
    finally:
        db.close()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        if payload and "sub" in payload:
            user = db.query(User).filter(User.username == payload["sub"]).first()
            if user:
                # 1. Immediately block SUSPENDED or DISABLED accounts
                if (user.status or "ACTIVE").upper() != "ACTIVE":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Account is {(user.status or 'DISABLED').lower()}. Access has been revoked.",
                    )
                # 2. Check token_version for immediate session invalidation after role/status/password changes
                token_tv = payload.get("tv")
                if token_tv is not None and int(token_tv) != int(user.token_version or 1):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Session has been invalidated. Please sign in again.",
                    )
                # 3. Check JTI session revocation if session row exists
                jti = payload.get("jti")
                if jti:
                    sess = db.query(UserSession).filter(UserSession.token_jti == jti).first()
                    if sess and not sess.is_active:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Session has been logged out or revoked. Please sign in again.",
                        )
                return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please log in.",
    )


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not credentials or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials=credentials, db=db)
    except HTTPException:
        return None


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required for this action.",
        )
    return current_user


def user_can_access_collection(user: User, collection_name: str, db: Optional[Session] = None) -> bool:
    if (user.status or "ACTIVE").upper() != "ACTIVE":
        return False
    if user.is_admin:
        return True
    if db is not None:
        return authorization_service.can_access_collection_by_name(db, user, collection_name)
    allowed = user.allowed_collections
    if "*" in allowed:
        return True
    return collection_name in allowed
