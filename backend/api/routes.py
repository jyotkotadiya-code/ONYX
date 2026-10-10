import json
import os
import shutil
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import psutil
import torch
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.auth.audit import record_audit_log
from backend.auth.auth_handler import (
    check_login_rate_limit,
    clear_failed_login_attempts,
    create_access_token,
    decode_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    invalidate_user_sessions,
    record_failed_login_attempt,
    require_admin,
    security_scheme,
    seed_workplace_structure,
    slugify_workplace_name,
    user_can_access_collection,
    verify_password,
)
from backend.auth.authorization import authorization_service
from backend.auth.permissions import (
    ALL_PERMISSIONS,
    get_default_employee_permissions,
    get_effective_permissions,
    set_default_employee_permissions,
)
from backend.auth.policies import VALID_ACCESS_LEVELS, VALID_USER_STATUSES
from backend.core.config import settings
from backend.core.logging_config import app_logger
from backend.core.security import (
    compute_sha256_bytes,
    ensure_safe_path,
    sanitize_filename,
    validate_file_extension,
    validate_file_size,
)
from backend.database.query_planner import (
    is_internal_system_database,
    plan_and_execute_database_query,
)
from backend.database.router import route_user_query
from backend.database.sqlite_db import (
    AuditLog,
    ChatMessage,
    ChatSession,
    ChunkRecord,
    Collection,
    CollectionAccess,
    Department,
    Document,
    DocumentAccess,
    DocumentVersion,
    Group,
    IngestionJob,
    SavedArtifact,
    User,
    UserGroup,
    UserSession,
    Workspace,
    get_db,
)
from backend.database.vector_store import vector_store
from backend.embeddings.embedding_service import embedding_service
from backend.ingestion.database_parser import inspect_database_schema
from backend.ingestion.ocr import ocr_engine
from backend.ingestion.pipeline import process_document_ingestion
from backend.llm.llm_client import NOT_FOUND_RESPONSE, llm_client
from backend.response.financial_engine import financial_engine
from backend.response.planner import (
    apply_workspace_followup_command,
    build_grounded_structured_response,
)
from backend.retrieval.retriever import retriever
from backend.tools.vectorizer import ImageVectorizationError, vector_converter

router = APIRouter(prefix="/api")

EMPLOYEE_EMPTY_KNOWLEDGE_RESPONSE = (
    "I couldn't find enough reliable information in the uploaded data available to your account to answer that question."
)


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str


class CreateWorkplaceRequest(BaseModel):
    name: str
    description: str = ""
    industry: str = ""
    logo: str = ""
    assistant_name: str = ""
    welcome_message: str = "Ask anything about your workplace knowledge."
    switch_to_new: bool = False


class UpdateWorkplaceRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    logo: Optional[str] = None
    assistant_name: Optional[str] = None
    welcome_message: Optional[str] = None
    default_doc_visibility: Optional[str] = None
    allow_employee_uploads: Optional[bool] = None
    session_duration_minutes: Optional[int] = None
    onboarding_completed: Optional[bool] = None


class CreateUserRequest(BaseModel):
    username: str
    password: str = ""
    name: str = ""
    email: str = ""
    role: str = "employee"
    job_title: str = "Employee"
    department_id: Optional[str] = None
    group_ids: list[str] = []
    allowed_collections: list[str] = ["General", "Company Policies", "Projects"]
    permissions: list[str] = []
    can_upload: bool = False
    status: str = "ACTIVE"


class InviteEmployeeRequest(BaseModel):
    name: str
    email: str = ""
    username: Optional[str] = None
    job_title: str = "Employee"
    department_id: Optional[str] = None
    group_ids: list[str] = []
    allowed_collections: list[str] = ["General", "Company Policies", "Projects"]
    can_upload: bool = False


class ActivateInviteRequest(BaseModel):
    invite_token: str
    password: str


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    job_title: Optional[str] = None
    department_id: Optional[str] = None
    group_ids: Optional[list[str]] = None
    allowed_collections: Optional[list[str]] = None
    permissions: Optional[list[str]] = None
    can_upload: Optional[bool] = None
    status: Optional[str] = None
    password: Optional[str] = None


class DepartmentRequest(BaseModel):
    name: str
    description: str = ""


class GroupRequest(BaseModel):
    name: str
    description: str = ""
    member_ids: list[str] = []


class UpdateGroupMembersRequest(BaseModel):
    member_ids: list[str]


class CreateCollectionRequest(BaseModel):
    name: str
    description: str = ""
    is_private: bool = False
    access_level: str = "EMPLOYEE_SHARED"
    department_id: Optional[str] = None


class UpdateCollectionAccessRequest(BaseModel):
    access_level: str = "EMPLOYEE_SHARED"
    is_private: bool = False
    department_id: Optional[str] = None
    allowed_group_ids: list[str] = []
    allowed_user_ids: list[str] = []


class UpdateDocumentAccessRequest(BaseModel):
    access_level: str  # ADMIN_ONLY, EMPLOYEE_SHARED, DEPARTMENT_ONLY, GROUP_ONLY, USER_SPECIFIC
    department_id: Optional[str] = None
    allowed_department_ids: list[str] = []
    allowed_group_ids: list[str] = []
    allowed_user_ids: list[str] = []
    denied_user_ids: list[str] = []
    approval_status: Optional[str] = None


class ArchiveDocumentRequest(BaseModel):
    is_archived: bool = True


class MoveDocumentRequest(BaseModel):
    collection: str


class UpdateEmployeeDefaultPermissionsRequest(BaseModel):
    permissions: list[str]


class AccessTestRequest(BaseModel):
    user_id: str
    document_id: str


class SaveArtifactRequest(BaseModel):
    title: str
    session_id: Optional[str] = None
    visibility: str = "PRIVATE"  # PRIVATE, SHARED, ADMIN_ONLY
    source_document_ids: list[str] = []
    payload: dict[str, Any]


class SearchRequest(BaseModel):
    query: str
    collection: str = "ALL"
    mode: str = "rag"  # "rag" or "exact"
    top_k: int = 5
    include_archived: bool = False


class ChatRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    collection: str = "ALL"
    mode: str = "rag"
    top_k: int = 5
    stream: bool = False
    active_workspace: Optional[dict[str, Any]] = None
    include_archived: bool = False


class WorkspaceMutateRequest(BaseModel):
    command: str
    active_workspace: dict[str, Any]
    session_id: Optional[str] = None


class DatabaseInspectRequest(BaseModel):
    connection_url: str


class DatabaseIngestRequest(BaseModel):
    connection_url: str
    selected_tables: Optional[list[str]] = None
    collection: str = "General"
    access_level: str = "ADMIN_ONLY"


# ─── Serialization Helpers ────────────────────────────────────────────────────

def _serialize_workplace(db: Session, ws: Workspace, user: Optional[User] = None) -> dict[str, Any]:
    has_knowledge = True
    if user is not None:
        auth_ids = authorization_service.get_authorized_document_ids(db, user)
        has_knowledge = len(auth_ids) > 0
    return {
        "id": ws.id,
        "workplace_id": ws.id,
        "name": ws.name,
        "slug": ws.slug or slugify_workplace_name(ws.name),
        "logo": ws.logo or "",
        "description": ws.description or "",
        "industry": ws.industry or "",
        "assistant_name": ws.assistant_name or f"{ws.name} AI",
        "welcome_message": ws.welcome_message or "Ask anything about your workplace knowledge.",
        "default_doc_visibility": ws.default_doc_visibility or "EMPLOYEE_SHARED",
        "allow_employee_uploads": bool(ws.allow_employee_uploads),
        "session_duration_minutes": ws.session_duration_minutes or 1440,
        "onboarding_completed": bool(ws.onboarding_completed),
        "created_by": ws.created_by or "admin",
        "status": ws.status or "ACTIVE",
        "has_authorized_knowledge": has_knowledge,
        "created_at": ws.created_at.isoformat() if ws.created_at else None,
    }


def _serialize_user(db: Session, u: User) -> dict[str, Any]:
    dept = (
        db.query(Department).filter(Department.id == u.department_id).first()
        if u.department_id
        else None
    )
    ug_rows = db.query(UserGroup).filter(UserGroup.user_id == u.id).all()
    grp_ids = [r.group_id for r in ug_rows]
    groups = db.query(Group).filter(Group.id.in_(grp_ids)).all() if grp_ids else []
    workspace = db.query(Workspace).filter(Workspace.id == u.workspace_id).first()
    ws_name = workspace.name if workspace else "ONYX Studio"
    return {
        "id": u.id,
        "name": u.name or u.username,
        "email": u.email or "",
        "username": u.username,
        "role": u.normalized_role,
        "role_display": "Administrator" if u.is_admin else "Employee",
        "job_title": u.job_title or ("Administrator" if u.is_admin else "Employee"),
        "department_id": u.department_id,
        "department": dept.name if dept else None,
        "groups": [{"id": g.id, "name": g.name} for g in groups],
        "group_ids": grp_ids,
        "status": u.status or "ACTIVE",
        "invite_status": u.invite_status or "ACCEPTED",
        "invite_token": u.invite_token if u.invite_status == "PENDING" else None,
        "workspace": ws_name,
        "workspace_id": u.workspace_id,
        "workplace_id": u.workspace_id,
        "workplace_name": ws_name,
        "workplace_slug": workspace.slug if workspace else "onyx-studio",
        "assistant_name": (workspace.assistant_name if workspace and workspace.assistant_name else f"{ws_name} AI"),
        "welcome_message": (
            workspace.welcome_message
            if workspace and workspace.welcome_message
            else "Ask anything about your workplace knowledge."
        ),
        "allowed_collections": u.allowed_collections,
        "permissions": get_effective_permissions(u),
        "custom_permissions": u.custom_permissions,
        "can_upload": bool(u.can_upload),
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "last_active_at": (u.last_active_at or u.last_login).isoformat() if (u.last_active_at or u.last_login) else None,
    }


def _serialize_document(d: Document, db: Optional[Session] = None, include_access_rules: bool = False) -> dict[str, Any]:
    meta = {}
    try:
        meta = json.loads(d.metadata_json or "{}")
    except Exception:
        pass

    dept_name = None
    access_rules_list = []
    if db is not None:
        if d.department_id:
            dept = db.query(Department).filter(Department.id == d.department_id).first()
            dept_name = dept.name if dept else None
        if include_access_rules:
            rules = db.query(DocumentAccess).filter(DocumentAccess.document_id == d.id).all()
            for r in rules:
                access_rules_list.append(
                    {
                        "id": r.id,
                        "access_type": r.access_type,
                        "role": r.role,
                        "department_id": r.department_id,
                        "group_id": r.group_id,
                        "user_id": r.user_id,
                    }
                )

    is_arch = bool(getattr(d, "is_archived", False)) or (d.status or "").upper() == "ARCHIVED"
    payload = {
        "id": d.id,
        "workplace_id": d.workspace_id,
        "filename": d.filename,
        "file_type": d.file_type,
        "modality": d.modality,
        "file_size": d.file_size,
        "content_hash": d.content_hash,
        "version": d.version,
        "collection": d.collection_name,
        "owner": d.owner,
        "owner_id": d.owner_id,
        "access_level": d.access_level or "EMPLOYEE_SHARED",
        "department_id": d.department_id,
        "department": dept_name,
        "approval_status": d.approval_status or "APPROVED",
        "is_archived": is_arch,
        "status": "Archived" if is_arch else d.status,
        "chunk_count": d.chunk_count,
        "page_count": d.page_count,
        "error_message": d.error_message,
        "suggested_action": d.suggested_action,
        "metadata": meta,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "updated_at": d.updated_at.isoformat() if d.updated_at else None,
    }
    if include_access_rules:
        payload["access_rules"] = access_rules_list
    return payload



# ─── 1. Health & System Status ────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Minimal public health check that does not expose sensitive system or document counts."""
    return {
        "status": "ok",
        "offline_mode": settings.OFFLINE_MODE,
    }


@router.get("/models")
async def get_models(current_user: User = Depends(get_current_user)):
    llm_info = await llm_client.discover_models()
    emb_info = embedding_service.get_status()
    return {
        "generation_llm": llm_info,
        "embedding_model": emb_info,
        "ocr_engine": ocr_engine.get_status(),
        "database_engine": {"status": "online", "engine": "SQLite / Universal SQL"},
    }


@router.get("/system/status")
async def system_status(
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    llm_info = await llm_client.discover_models()
    emb_info = embedding_service.get_status()
    vec_info = vector_store.get_status()
    ocr_info = ocr_engine.get_status()

    # Scope statistics to the user's authorized documents so restricted document counts are never leaked
    if current_user is None:
        doc_count = 0
        ready_docs = 0
        failed_docs = 0
        chunk_count = 0
        col_count = 0
        total_bytes = 0
    elif current_user.is_admin:
        doc_count = db.query(Document).count()
        ready_docs = db.query(Document).filter(Document.status == "Ready").count()
        failed_docs = db.query(Document).filter(Document.status == "Failed").count()
        chunk_count = db.query(ChunkRecord).count()
        col_count = db.query(Collection).count()
        upload_dir = settings.resolve_path(settings.UPLOAD_DIR)
        vec_dir = settings.resolve_path(settings.VECTOR_DB_PATH)
        total_bytes = 0
        for folder in [upload_dir, vec_dir]:
            if folder.exists():
                for f in folder.rglob("*"):
                    if f.is_file():
                        total_bytes += f.stat().st_size
    else:
        auth_docs = authorization_service.filter_authorized_documents(db, current_user)
        auth_doc_ids = [d.id for d in auth_docs]
        doc_count = len(auth_docs)
        ready_docs = sum(1 for d in auth_docs if d.status == "Ready")
        failed_docs = sum(1 for d in auth_docs if d.status == "Failed")
        chunk_count = (
            db.query(ChunkRecord).filter(ChunkRecord.document_id.in_(auth_doc_ids)).count()
            if auth_doc_ids
            else 0
        )
        all_cols = db.query(Collection).all()
        col_count = sum(1 for c in all_cols if authorization_service.evaluate_collection_access(db, current_user, c).allowed)
        total_bytes = sum(d.file_size or 0 for d in auth_docs)

    mem = psutil.virtual_memory()
    is_strictly_local = (
        settings.OFFLINE_MODE
        and ("127.0.0.1" in settings.LLM_BASE_URL or "localhost" in settings.LLM_BASE_URL)
        and settings.VECTOR_DB == "chroma"
    )

    safe_llm_details = {
        "online": llm_info.get("online", False),
        "runtime": llm_info.get("runtime", "local"),
        "selected_model": (llm_info.get("selected_model") or "local-model").split("/")[-1].split("\\")[-1],
        "quantization": llm_info.get("quantization", "Q4_K_M"),
    }
    safe_vec_details = {
        "status": vec_info.get("status", "online"),
        "engine": vec_info.get("engine", "ChromaDB"),
        "collection": vec_info.get("collection", "knowledge_chunks"),
        "vector_count": chunk_count if (current_user and not current_user.is_admin) else vec_info.get("vector_count", 0),
    }
    safe_ocr_details = {
        "status": ocr_info.get("status", "online"),
        "engine": ocr_info.get("engine", "RapidOCR / Tesseract"),
    }

    return {
        "application": "ready",
        "llm": "online" if llm_info["online"] else "local_fallback_ready",
        "llm_details": safe_llm_details,
        "embedding": {
            "status": "online" if emb_info["loaded"] else emb_info["status"],
            "model": (emb_info.get("model") or "multilingual-e5-small").split("/")[-1],
        },
        "embedding_model": "online" if emb_info["loaded"] else emb_info["status"],
        "embedding_details": emb_info,
        "vector_database": vec_info["status"],
        "vector_details": safe_vec_details,
        "sqlite": "online",
        "ocr": ocr_info["status"],
        "ocr_details": safe_ocr_details,
        "services": {
            "application": {"status": "online", "label": "Application API"},
            "database": {"status": "online", "label": "Local Metadata DB (SQLite)"},
            "vector_database": {"status": vec_info["status"], "label": "Vector Database (ChromaDB)"},
            "embedding": {
                "status": "online" if emb_info["loaded"] else emb_info["status"],
                "label": "Embedding Model",
                "model": (emb_info.get("model") or "multilingual-e5-small").split("/")[-1],
            },
            "llm": {
                "status": "online" if llm_info["online"] else "local_fallback_ready",
                "label": "Local Llama Runtime",
                "model": safe_llm_details["selected_model"],
            },
            "ocr": {"status": ocr_info["status"], "label": "OCR Engine"},
        },
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": "NVIDIA GeForce RTX 3050 Laptop GPU (4096 MiB)",
        "cpu_Info": f"Intel Core i5-11400H ({psutil.cpu_count(logical=True)} logical cores)",
        "ram_total_gb": round(mem.total / (1024**3), 2),
        "ram_used_pct": mem.percent,
        "offline_mode": settings.OFFLINE_MODE,
        "verified_private": is_strictly_local,
        "stats": {
            "documents": doc_count,
            "ready_documents": ready_docs,
            "failed_documents": failed_docs,
            "chunks": chunk_count,
            "vectors": chunk_count if (current_user and not current_user.is_admin) else vec_info.get("vector_count", 0),
            "collections": col_count,
            "storage_mb": round(total_bytes / (1024 * 1024), 2),
        },
    }


# ─── 2. Authentication, Sessions & User Management ────────────────────────────

@router.post("/auth/login")
def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    uname = req.username.strip()
    client_ip = request.client.host if request.client else "127.0.0.1"
    rate_key = f"{client_ip}::{uname.lower()}"

    if not check_login_rate_limit(rate_key):
        record_audit_log(
            db=db,
            action="LOGIN_RATE_LIMITED",
            resource_type="auth",
            username=uname,
            success=False,
            severity="ALERT",
            ip_address=client_ip,
            details={"reason": "Too many failed login attempts"},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait a few minutes before trying again.",
        )

    user = db.query(User).filter(User.username == uname).first()
    if not user or not verify_password(req.password, user.password_hash):
        fail_count = record_failed_login_attempt(rate_key)
        sev = "ALERT" if fail_count >= 3 else "WARNING"
        record_audit_log(
            db=db,
            action="LOGIN_FAILED",
            resource_type="auth",
            username=uname,
            success=False,
            severity=sev,
            ip_address=client_ip,
            details={"failed_attempts": fail_count},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if (user.status or "ACTIVE").upper() != "ACTIVE":
        record_audit_log(
            db=db,
            action="LOGIN_BLOCKED_INACTIVE",
            resource_type="auth",
            user=user,
            success=False,
            severity="WARNING",
            ip_address=client_ip,
            details={"status": user.status},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account is {(user.status or 'DISABLED').lower()}. Please contact an administrator.",
        )

    clear_failed_login_attempts(rate_key)
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    workspace = db.query(Workspace).filter(Workspace.id == user.workspace_id).first()
    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.normalized_role,
            "workspace": workspace.name if workspace else "ONYX",
        },
        db=db,
        user=user,
        ip_address=client_ip,
    )

    login_action = "ADMIN_LOGIN" if user.is_admin else "EMPLOYEE_LOGIN"
    record_audit_log(
        db=db,
        action=login_action,
        resource_type="auth",
        user=user,
        resource_id=user.id,
        success=True,
        severity="INFO",
        ip_address=client_ip,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _serialize_user(db, user),
    }


@router.post("/auth/logout")
def logout(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    if credentials and credentials.credentials:
        payload = decode_access_token(credentials.credentials)
        jti = payload.get("jti") if payload else None
        if jti:
            sess = db.query(UserSession).filter(UserSession.token_jti == jti).first()
            if sess:
                sess.is_active = False
                sess.revoked_at = datetime.now(timezone.utc)
                db.commit()

    record_audit_log(
        db=db,
        action="LOGOUT",
        resource_type="auth",
        user=current_user,
        resource_id=current_user.id,
        success=True,
        ip_address=client_ip,
    )
    return {"status": "logged_out"}


@router.get("/auth/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.last_active_at = datetime.now(timezone.utc)
    db.commit()
    return _serialize_user(db, current_user)


# ─── 2B. Workplace Management, Creation, Branding & Switching ─────────────────

@router.get("/workplaces/current")
def get_current_workplace(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == current_user.workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workplace not found.")
    return _serialize_workplace(db, ws, user=current_user)


@router.get("/workplaces")
def list_workplaces(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    workplaces = db.query(Workspace).order_by(Workspace.created_at.asc()).all()
    return [
        {
            **_serialize_workplace(db, ws),
            "employee_count": db.query(User).filter(User.workspace_id == ws.id, User.role != "admin").count(),
            "document_count": db.query(Document).filter(Document.workspace_id == ws.id).count(),
            "is_current": ws.id == admin.workspace_id,
        }
        for ws in workplaces
    ]


@router.post("/workplaces")
def create_workplace(
    req: CreateWorkplaceRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = req.name.strip()
    if not name or len(name) < 2:
        raise HTTPException(status_code=400, detail="Workplace name must be at least 2 characters.")
    slug = slugify_workplace_name(name)
    if db.query(Workspace).filter(Workspace.name == name).first():
        raise HTTPException(status_code=400, detail=f"Workplace '{name}' already exists.")

    ws = Workspace(
        name=name,
        slug=slug,
        description=req.description.strip(),
        industry=req.industry.strip(),
        logo=req.logo.strip(),
        assistant_name=req.assistant_name.strip() or f"{name} AI",
        welcome_message=req.welcome_message.strip() or "Ask anything about your workplace knowledge.",
        default_doc_visibility="EMPLOYEE_SHARED",
        allow_employee_uploads=False,
        session_duration_minutes=1440,
        onboarding_completed=False,
        created_by=admin.username,
        status="ACTIVE",
    )
    db.add(ws)
    db.commit()
    db.refresh(ws)

    # Seed isolated default departments, groups, and collections for this new workplace
    seed_workplace_structure(db, ws, created_by=admin.username)

    if req.switch_to_new:
        admin.workspace_id = ws.id
        db.commit()
        db.refresh(admin)

    record_audit_log(
        db=db,
        action="WORKPLACE_CREATED",
        resource_type="workplace",
        user=admin,
        resource_id=ws.id,
        workspace_id=ws.id,
        details={"name": ws.name, "slug": ws.slug},
    )
    return _serialize_workplace(db, ws, user=admin)


@router.put("/workplaces/current")
def update_current_workplace(
    req: UpdateWorkplaceRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == admin.workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workplace not found.")

    if req.name is not None and req.name.strip():
        ws.name = req.name.strip()
        ws.slug = slugify_workplace_name(ws.name)
    if req.description is not None:
        ws.description = req.description.strip()
    if req.industry is not None:
        ws.industry = req.industry.strip()
    if req.logo is not None:
        ws.logo = req.logo.strip()
    if req.assistant_name is not None and req.assistant_name.strip():
        ws.assistant_name = req.assistant_name.strip()
    if req.welcome_message is not None and req.welcome_message.strip():
        ws.welcome_message = req.welcome_message.strip()
    if req.default_doc_visibility is not None and req.default_doc_visibility.upper() in VALID_ACCESS_LEVELS:
        ws.default_doc_visibility = req.default_doc_visibility.upper()
    if req.allow_employee_uploads is not None:
        ws.allow_employee_uploads = bool(req.allow_employee_uploads)
    if req.session_duration_minutes is not None and req.session_duration_minutes >= 15:
        ws.session_duration_minutes = int(req.session_duration_minutes)
    if req.onboarding_completed is not None:
        ws.onboarding_completed = bool(req.onboarding_completed)

    db.commit()
    db.refresh(ws)
    record_audit_log(
        db=db,
        action="WORKPLACE_UPDATED",
        resource_type="workplace",
        user=admin,
        resource_id=ws.id,
        details={"name": ws.name, "assistant_name": ws.assistant_name},
    )
    return _serialize_workplace(db, ws, user=admin)


@router.delete("/workplaces/{workplace_id}")
def delete_workplace(
    workplace_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == workplace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workplace not found.")

    total_workplaces = db.query(Workspace).count()
    if total_workplaces <= 1:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete the sole workplace in the system. Create another workplace first or use system data purge.",
        )

    # Delete all documents & vector chunks associated with this workplace
    docs = db.query(Document).filter(Document.workspace_id == workplace_id).all()
    for d in docs:
        try:
            vector_store.delete_document_chunks(d.id)
        except Exception:
            pass
        db.query(ChunkRecord).filter(ChunkRecord.document_id == d.id).delete(synchronize_session=False)
        db.query(DocumentVersion).filter(DocumentVersion.document_id == d.id).delete(synchronize_session=False)
        db.query(DocumentAccess).filter(DocumentAccess.document_id == d.id).delete(synchronize_session=False)
        db.query(Document).filter(Document.id == d.id).delete(synchronize_session=False)

    db.query(Collection).filter(Collection.workspace_id == workplace_id).delete(synchronize_session=False)
    db.query(Department).filter(Department.workspace_id == workplace_id).delete(synchronize_session=False)
    db.query(Group).filter(Group.workspace_id == workplace_id).delete(synchronize_session=False)
    db.query(ChatSession).filter(ChatSession.workspace_id == workplace_id).delete(synchronize_session=False)

    # Reassign any users whose active workspace was this workplace
    other_ws = db.query(Workspace).filter(Workspace.id != workplace_id).first()
    if other_ws:
        db.query(User).filter(User.workspace_id == workplace_id).update(
            {"workspace_id": other_ws.id}, synchronize_session=False
        )
        if admin.workspace_id == workplace_id:
            admin.workspace_id = other_ws.id

    db.query(Workspace).filter(Workspace.id == workplace_id).delete(synchronize_session=False)
    db.commit()

    record_audit_log(
        db=db,
        action="WORKPLACE_DELETED",
        resource_type="workplace",
        user=admin,
        resource_id=workplace_id,
        details={"name": ws.name},
    )
    return {"status": "success", "message": f"Workplace '{ws.name}' deleted successfully."}


@router.post("/admin/system/purge-all-data")
def purge_all_data(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Purge all documents, chunks, vector embeddings, chat sessions, collections,
    and extra non-default workplaces to reset the app to a clean state.
    """
    try:
        vector_store.reset()
    except Exception as e:
        app_logger.warning(f"Vector store reset warning: {e}")

    db.query(ChunkRecord).delete(synchronize_session=False)
    db.query(DocumentVersion).delete(synchronize_session=False)
    db.query(DocumentAccess).delete(synchronize_session=False)
    db.query(Document).delete(synchronize_session=False)
    db.query(CollectionAccess).delete(synchronize_session=False)
    db.query(Collection).delete(synchronize_session=False)
    db.query(ChatMessage).delete(synchronize_session=False)
    db.query(ChatSession).delete(synchronize_session=False)
    db.query(SavedArtifact).delete(synchronize_session=False)
    db.query(IngestionJob).delete(synchronize_session=False)

    for dir_setting in [settings.UPLOAD_DIR, settings.PROCESSED_DIR]:
        target_dir = settings.resolve_path(dir_setting)
        if target_dir.exists():
            for item in target_dir.iterdir():
                if item.is_file():
                    try:
                        item.unlink()
                    except Exception:
                        pass
                elif item.is_dir():
                    try:
                        shutil.rmtree(item)
                    except Exception:
                        pass

    primary_ws = db.query(Workspace).filter(Workspace.id == admin.workspace_id).first()
    if not primary_ws:
        primary_ws = db.query(Workspace).order_by(Workspace.created_at.asc()).first()

    if primary_ws:
        extra_workplaces = db.query(Workspace).filter(Workspace.id != primary_ws.id).all()
        for e_ws in extra_workplaces:
            db.query(User).filter(User.workspace_id == e_ws.id).update(
                {"workspace_id": primary_ws.id}, synchronize_session=False
            )
            db.query(Workspace).filter(Workspace.id == e_ws.id).delete(synchronize_session=False)

        seed_workplace_structure(db, primary_ws, created_by=admin.username)

    db.commit()

    record_audit_log(
        db=db,
        action="SYSTEM_PURGE_ALL_DATA",
        resource_type="system",
        user=admin,
        details={"message": "All data, documents, chunks, and extra workspaces purged."},
    )

    return {"status": "success", "message": "All database data and vector chunks successfully purged."}


@router.get("/workplaces/my-approved")
def list_my_approved_workplaces(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.is_admin:
        workplaces = db.query(Workspace).order_by(Workspace.created_at.asc()).all()
        return [
            {
                **_serialize_workplace(db, ws, user=current_user),
                "employee_count": db.query(User).filter(User.workspace_id == ws.id, User.role != "admin").count(),
                "document_count": db.query(Document).filter(Document.workspace_id == ws.id).count(),
                "is_current": ws.id == current_user.workspace_id,
                "is_approved": True,
                "department_name": "Management",
            }
            for ws in workplaces
        ]

    # For employees, find all workplaces where they have an active user record
    user_records = (
        db.query(User)
        .filter(
            (User.workspace_id == current_user.workspace_id)
            | (User.username == current_user.username)
            | (User.email == current_user.email if current_user.email else False)
        )
        .all()
    )

    ws_ids = list({u.workspace_id for u in user_records if u.workspace_id})
    if not ws_ids:
        ws_ids = [current_user.workspace_id]

    workplaces = db.query(Workspace).filter(Workspace.id.in_(ws_ids)).order_by(Workspace.name.asc()).all()

    results = []
    for ws in workplaces:
        u_rec = next((u for u in user_records if u.workspace_id == ws.id), current_user)
        dept = db.query(Department).filter(Department.id == u_rec.department_id).first() if u_rec.department_id else None
        
        results.append({
            **_serialize_workplace(db, ws, user=u_rec),
            "is_current": ws.id == current_user.workspace_id,
            "is_approved": (u_rec.status or "ACTIVE").upper() == "ACTIVE" and (u_rec.invite_status or "ACCEPTED").upper() == "ACCEPTED",
            "department_name": dept.name if dept else "General Team",
            "job_title": u_rec.job_title or "Employee",
            "allowed_collections": u_rec.allowed_collections,
            "can_upload": bool(u_rec.can_upload),
        })

    return results


@router.post("/workplaces/{workplace_id}/switch")
def switch_active_workplace(
    workplace_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ws = db.query(Workspace).filter(Workspace.id == workplace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workplace not found.")

    if not current_user.is_admin:
        matching_user = (
            db.query(User)
            .filter(User.username == current_user.username, User.workspace_id == ws.id)
            .first()
        )
        if not matching_user and current_user.email:
            matching_user = (
                db.query(User)
                .filter(User.email == current_user.email, User.workspace_id == ws.id)
                .first()
            )
        if not matching_user and current_user.workspace_id != ws.id:
            raise HTTPException(
                status_code=403,
                detail="You are not authorized to join this workplace. Please ask your administrator to approve your account."
            )

    current_user.workspace_id = ws.id
    if current_user.is_admin:
        mgmt = (
            db.query(Department)
            .filter(Department.workspace_id == ws.id, Department.name == "Management")
            .first()
        )
        if mgmt:
            current_user.department_id = mgmt.id

    db.commit()
    db.refresh(current_user)

    token = create_access_token(
        data={
            "sub": current_user.username,
            "role": current_user.normalized_role,
            "workspace": ws.name,
            "workspace_id": ws.id,
        },
        db=db,
        user=current_user,
    )
    record_audit_log(
        db=db,
        action="WORKPLACE_SWITCHED",
        resource_type="workplace",
        user=current_user,
        resource_id=ws.id,
        workspace_id=ws.id,
        details={"workplace": ws.name},
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "workplace": _serialize_workplace(db, ws, user=current_user),
        "user": _serialize_user(db, current_user),
    }



# ─── 3. Admin Users, Employees, Invitations, Departments & Groups ─────────────

@router.get("/users")
def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "user.read")
    users = (
        db.query(User)
        .filter(User.workspace_id == current_user.workspace_id)
        .order_by(User.created_at.asc())
        .all()
    )
    return [_serialize_user(db, u) for u in users]


@router.post("/users")
def create_user(
    req: CreateUserRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "user.create")
    uname = req.username.strip()
    if not uname or len(uname) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters.")
    if db.query(User).filter(User.username == uname).first():
        raise HTTPException(status_code=400, detail=f"User '{uname}' already exists.")
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    normalized_role = "admin" if req.role.strip().lower() == "admin" else "employee"
    if normalized_role == "admin" and not current_user.is_admin:
        record_audit_log(
            db=db,
            action="ROLE_ESCALATION_ATTEMPT",
            resource_type="user",
            user=current_user,
            success=False,
            severity="ALERT",
            details={"attempted_role": "admin"},
        )
        raise HTTPException(status_code=403, detail="Only an administrator can create an admin account.")

    user_status = req.status.upper() if req.status.upper() in VALID_USER_STATUSES else "ACTIVE"
    allowed_cols = ["*"] if normalized_role == "admin" else (req.allowed_collections or ["General", "Company Policies"])
    perms = ["*"] if normalized_role == "admin" else [p for p in req.permissions if p in ALL_PERMISSIONS]

    new_user = User(
        name=req.name.strip() or uname,
        email=req.email.strip(),
        username=uname,
        password_hash=hash_password(req.password),
        role=normalized_role,
        job_title=req.job_title.strip() or ("Administrator" if normalized_role == "admin" else "Employee"),
        department_id=req.department_id or None,
        status=user_status,
        invite_status="ACCEPTED",
        workspace_id=current_user.workspace_id,
        allowed_collections_json=json.dumps(allowed_cols),
        permissions_json=json.dumps(perms),
        can_upload=True if normalized_role == "admin" else bool(req.can_upload),
        token_version=1,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    for gid in set(req.group_ids or []):
        grp = (
            db.query(Group)
            .filter(Group.id == gid, Group.workspace_id == current_user.workspace_id)
            .first()
        )
        if grp:
            db.add(UserGroup(user_id=new_user.id, group_id=grp.id))
    db.commit()

    record_audit_log(
        db=db,
        action="USER_CREATED",
        resource_type="user",
        user=current_user,
        resource_id=new_user.id,
        success=True,
        ip_address=request.client.host if request.client else "127.0.0.1",
        details={
            "created_username": new_user.username,
            "role": new_user.normalized_role,
            "department_id": new_user.department_id,
        },
    )
    return _serialize_user(db, new_user)


@router.post("/users/invite")
@router.post("/admin/employees/invite")
def invite_employee(
    req: InviteEmployeeRequest,
    request: Request,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Local invitation flow for air-gapped / offline workplaces.
    Creates a pending employee record with a local activation code (`invite_token`)
    so the employee can set their own password and activate their account without external email servers.
    """
    base_uname = (req.username or req.email.split("@")[0] or req.name.lower().replace(" ", ".")).strip()
    base_uname = "".join(c for c in base_uname if c.isalnum() or c in {".", "_", "-"}).strip(".")
    if len(base_uname) < 2:
        base_uname = f"emp_{uuid.uuid4().hex[:6]}"
    uname = base_uname
    if db.query(User).filter(User.username == uname).first():
        uname = f"{base_uname}_{uuid.uuid4().hex[:4]}"

    invite_code = f"INV-{uuid.uuid4().hex[:4].upper()}-{uuid.uuid4().hex[:4].upper()}"
    temp_pass = uuid.uuid4().hex

    new_emp = User(
        name=req.name.strip() or uname,
        email=req.email.strip(),
        username=uname,
        password_hash=hash_password(temp_pass),
        role="employee",
        job_title=req.job_title.strip() or "Employee",
        department_id=req.department_id or None,
        status="ACTIVE",
        invite_token=invite_code,
        invite_status="PENDING",
        workspace_id=admin.workspace_id,
        allowed_collections_json=json.dumps(req.allowed_collections or ["General", "Company Policies", "Projects"]),
        permissions_json=json.dumps([]),
        can_upload=bool(req.can_upload),
        token_version=1,
    )
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)

    for gid in set(req.group_ids or []):
        grp = db.query(Group).filter(Group.id == gid, Group.workspace_id == admin.workspace_id).first()
        if grp:
            db.add(UserGroup(user_id=new_emp.id, group_id=grp.id))
    db.commit()

    record_audit_log(
        db=db,
        action="EMPLOYEE_INVITED",
        resource_type="user",
        user=admin,
        resource_id=new_emp.id,
        ip_address=request.client.host if request.client else "127.0.0.1",
        details={"username": new_emp.username, "name": new_emp.name, "department_id": new_emp.department_id},
    )
    return {
        "user": _serialize_user(db, new_emp),
        "invite_token": invite_code,
        "username": new_emp.username,
    }


@router.post("/auth/activate-invite")
def activate_employee_invite(
    req: ActivateInviteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    code = req.invite_token.strip()
    if not code:
        raise HTTPException(status_code=400, detail="Invitation code is required.")
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    user = db.query(User).filter(User.invite_token == code).first()
    if not user:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation code.")

    user.password_hash = hash_password(req.password)
    user.invite_status = "ACCEPTED"
    user.invite_token = None
    user.status = "ACTIVE"
    user.last_login = datetime.now(timezone.utc)
    user.last_active_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    workspace = db.query(Workspace).filter(Workspace.id == user.workspace_id).first()
    client_ip = request.client.host if request.client else "127.0.0.1"
    token = create_access_token(
        data={
            "sub": user.username,
            "role": user.normalized_role,
            "workspace": workspace.name if workspace else "ONYX Studio",
        },
        db=db,
        user=user,
        ip_address=client_ip,
    )

    record_audit_log(
        db=db,
        action="EMPLOYEE_INVITE_ACTIVATED",
        resource_type="user",
        user=user,
        resource_id=user.id,
        ip_address=client_ip,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": _serialize_user(db, user),
    }


@router.get("/admin/employees/{user_id}/profile")
def get_employee_profile_and_access(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = (
        db.query(User)
        .filter(User.id == user_id, User.workspace_id == admin.workspace_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Employee not found in this workplace.")
    preview = authorization_service.preview_user_access(db, target)
    serialized = _serialize_user(db, target)
    return {
        "profile": serialized,
        "employee": serialized,
        "access": preview,
        "accessible_collections": preview.get("accessible_collections", []),
        "accessible_documents": preview.get("accessible_documents", []),
        "restricted_documents": preview.get("restricted_documents", []),
    }


@router.put("/users/{user_id}")
def update_user(
    user_id: str,
    req: UpdateUserRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        record_audit_log(
            db=db,
            action="UNAUTHORIZED_USER_MODIFICATION_ATTEMPT",
            resource_type="user",
            user=current_user,
            resource_id=user_id,
            success=False,
            severity="ALERT",
        )
        raise HTTPException(status_code=403, detail="Administrator privileges required.")

    target = (
        db.query(User)
        .filter(User.id == user_id, User.workspace_id == current_user.workspace_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this workplace.")

    previous_role = target.normalized_role
    previous_status = target.status or "ACTIVE"
    session_invalidation_needed = False

    if req.name is not None:
        target.name = req.name.strip()
    if req.email is not None:
        target.email = req.email.strip()
    if req.job_title is not None:
        target.job_title = req.job_title.strip()
    if req.department_id is not None:
        target.department_id = req.department_id or None
    if req.can_upload is not None:
        target.can_upload = req.can_upload
    if req.allowed_collections is not None:
        target.allowed_collections_json = json.dumps(req.allowed_collections)
    if req.permissions is not None:
        valid_perms = ["*"] if "*" in req.permissions else [p for p in req.permissions if p in ALL_PERMISSIONS]
        target.permissions_json = json.dumps(valid_perms)

    if req.role is not None:
        new_role = "admin" if req.role.strip().lower() == "admin" else "employee"
        if target.username == "admin" and new_role != "admin":
            raise HTTPException(status_code=400, detail="Cannot demote the primary system administrator.")
        if new_role != previous_role:
            target.role = new_role
            session_invalidation_needed = True
            record_audit_log(
                db=db,
                action="ROLE_CHANGED",
                resource_type="user",
                user=current_user,
                resource_id=target.id,
                success=True,
                severity="WARNING",
                details={
                    "target_username": target.username,
                    "previous_role": previous_role,
                    "new_role": new_role,
                },
            )

    if req.status is not None:
        new_status = req.status.strip().upper()
        if new_status in VALID_USER_STATUSES and new_status != previous_status:
            if target.username == "admin" and new_status != "ACTIVE":
                raise HTTPException(status_code=400, detail="Cannot disable the primary system administrator.")
            target.status = new_status
            if new_status != "ACTIVE":
                session_invalidation_needed = True
            record_audit_log(
                db=db,
                action="USER_DISABLED" if new_status != "ACTIVE" else "USER_REACTIVATED",
                resource_type="user",
                user=current_user,
                resource_id=target.id,
                success=True,
                severity="WARNING",
                details={
                    "target_username": target.username,
                    "previous_status": previous_status,
                    "new_status": new_status,
                },
            )

    if req.password:
        target.password_hash = hash_password(req.password)
        target.invite_status = "ACCEPTED"
        target.invite_token = None
        session_invalidation_needed = True

    if req.group_ids is not None:
        db.query(UserGroup).filter(UserGroup.user_id == target.id).delete()
        for gid in set(req.group_ids):
            grp = (
                db.query(Group)
                .filter(Group.id == gid, Group.workspace_id == current_user.workspace_id)
                .first()
            )
            if grp:
                db.add(UserGroup(user_id=target.id, group_id=grp.id))

    db.commit()
    if session_invalidation_needed:
        invalidate_user_sessions(db, target)
    db.refresh(target)
    return _serialize_user(db, target)


@router.post("/users/{user_id}/disable")
def disable_user_endpoint(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = (
        db.query(User)
        .filter(User.id == user_id, User.workspace_id == admin.workspace_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot disable the primary system administrator.")

    target.status = "DISABLED"
    db.commit()
    invalidate_user_sessions(db, target)
    record_audit_log(
        db=db,
        action="USER_DISABLED",
        resource_type="user",
        user=admin,
        resource_id=target.id,
        success=True,
        severity="WARNING",
        details={"target_username": target.username, "preserved_documents": True},
    )
    return _serialize_user(db, target)


@router.delete("/users/{user_id}")
@router.delete("/admin/employees/{user_id}")
def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = (
        db.query(User)
        .filter(User.id == user_id, User.workspace_id == admin.workspace_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.username == "admin" or target.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete the primary system administrator account.")

    invalidate_user_sessions(db, target)
    db.query(UserGroup).filter(UserGroup.user_id == target.id).delete()
    db.delete(target)
    db.commit()

    record_audit_log(
        db=db,
        action="USER_DELETED",
        resource_type="user",
        user=admin,
        resource_id=user_id,
        severity="ALERT",
        details={"deleted_username": target.username, "deleted_name": target.name},
    )
    return {"status": "deleted", "user_id": user_id}



@router.post("/users/{user_id}/revoke-sessions")
def revoke_user_sessions_endpoint(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target = (
        db.query(User)
        .filter(User.id == user_id, User.workspace_id == admin.workspace_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    invalidate_user_sessions(db, target)
    record_audit_log(
        db=db,
        action="USER_SESSIONS_REVOKED",
        resource_type="user",
        user=admin,
        resource_id=target.id,
        details={"target_username": target.username},
    )
    return {"status": "revoked", "user_id": target.id}


# ─── 4. Departments & Groups Management (Workplace-Scoped) ────────────────────

@router.get("/departments")
def list_departments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    depts = (
        db.query(Department)
        .filter(Department.workspace_id == current_user.workspace_id)
        .order_by(Department.name.asc())
        .all()
    )
    result = []
    for d in depts:
        member_count = (
            db.query(User)
            .filter(User.department_id == d.id, User.workspace_id == current_user.workspace_id)
            .count()
        )
        doc_count = (
            db.query(Document)
            .filter(Document.department_id == d.id, Document.workspace_id == current_user.workspace_id)
            .count()
        )
        result.append(
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "member_count": member_count,
                "document_count": doc_count if current_user.is_admin else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
        )
    return result


@router.post("/departments")
def create_department(
    req: DepartmentRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Department name is required.")
    if (
        db.query(Department)
        .filter(Department.name == name, Department.workspace_id == admin.workspace_id)
        .first()
    ):
        raise HTTPException(status_code=400, detail=f"Department '{name}' already exists in this workplace.")

    dept = Department(
        name=name,
        description=req.description.strip(),
        workspace_id=admin.workspace_id,
        created_by=admin.username,
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)
    record_audit_log(
        db=db,
        action="DEPARTMENT_CREATED",
        resource_type="department",
        user=admin,
        resource_id=dept.id,
        details={"name": dept.name},
    )
    return {
        "id": dept.id,
        "name": dept.name,
        "description": dept.description,
        "member_count": 0,
    }


@router.delete("/departments/{department_id}")
def delete_department(
    department_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    dept = (
        db.query(Department)
        .filter(Department.id == department_id, Department.workspace_id == admin.workspace_id)
        .first()
    )
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    for u in db.query(User).filter(User.department_id == dept.id).all():
        u.department_id = None
    for d in db.query(Document).filter(Document.department_id == dept.id).all():
        d.department_id = None
        if d.access_level == "DEPARTMENT_ONLY":
            d.access_level = "ADMIN_ONLY"

    db.delete(dept)
    db.commit()
    record_audit_log(
        db=db,
        action="DEPARTMENT_DELETED",
        resource_type="department",
        user=admin,
        resource_id=department_id,
        details={"name": dept.name},
    )
    return {"status": "deleted", "department": dept.name}


@router.get("/groups")
def list_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    groups = (
        db.query(Group)
        .filter(Group.workspace_id == current_user.workspace_id)
        .order_by(Group.name.asc())
        .all()
    )
    result = []
    for g in groups:
        ug_rows = db.query(UserGroup).filter(UserGroup.group_id == g.id).all()
        m_ids = [r.user_id for r in ug_rows]
        members = (
            db.query(User)
            .filter(User.id.in_(m_ids), User.workspace_id == current_user.workspace_id)
            .all()
            if m_ids
            else []
        )
        result.append(
            {
                "id": g.id,
                "name": g.name,
                "description": g.description,
                "member_count": len(members),
                "members": [
                    {"id": m.id, "username": m.username, "name": m.name or m.username}
                    for m in members
                ]
                if current_user.is_admin
                else [],
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
        )
    return result


@router.post("/groups")
def create_group(
    req: GroupRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required.")
    if (
        db.query(Group)
        .filter(Group.name == name, Group.workspace_id == admin.workspace_id)
        .first()
    ):
        raise HTTPException(status_code=400, detail=f"Group '{name}' already exists in this workplace.")

    grp = Group(
        name=name,
        description=req.description.strip(),
        workspace_id=admin.workspace_id,
        created_by=admin.username,
    )
    db.add(grp)
    db.commit()
    db.refresh(grp)

    for uid in set(req.member_ids or []):
        u = db.query(User).filter(User.id == uid, User.workspace_id == admin.workspace_id).first()
        if u:
            db.add(UserGroup(user_id=u.id, group_id=grp.id))
    db.commit()

    record_audit_log(
        db=db,
        action="GROUP_CREATED",
        resource_type="group",
        user=admin,
        resource_id=grp.id,
        details={"name": grp.name, "member_count": len(req.member_ids)},
    )
    return {"id": grp.id, "name": grp.name, "description": grp.description}


@router.put("/groups/{group_id}/members")
def update_group_members(
    group_id: str,
    req: UpdateGroupMembersRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    grp = (
        db.query(Group)
        .filter(Group.id == group_id, Group.workspace_id == admin.workspace_id)
        .first()
    )
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found.")

    db.query(UserGroup).filter(UserGroup.group_id == grp.id).delete()
    for uid in set(req.member_ids):
        u = db.query(User).filter(User.id == uid, User.workspace_id == admin.workspace_id).first()
        if u:
            db.add(UserGroup(user_id=u.id, group_id=grp.id))
    db.commit()

    record_audit_log(
        db=db,
        action="GROUP_MEMBERS_UPDATED",
        resource_type="group",
        user=admin,
        resource_id=grp.id,
        details={"group": grp.name, "member_ids": req.member_ids},
    )
    return {"status": "updated", "group_id": grp.id, "member_count": len(req.member_ids)}


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    grp = (
        db.query(Group)
        .filter(Group.id == group_id, Group.workspace_id == admin.workspace_id)
        .first()
    )
    if not grp:
        raise HTTPException(status_code=404, detail="Group not found.")
    db.delete(grp)
    db.commit()
    record_audit_log(
        db=db,
        action="GROUP_DELETED",
        resource_type="group",
        user=admin,
        resource_id=group_id,
        details={"name": grp.name},
    )
    return {"status": "deleted", "group": grp.name}


# ─── 5. Permissions, Access Policy & Workplace Analytics ──────────────────────

@router.get("/admin/permissions")
def get_permissions_config(admin: User = Depends(require_admin)):
    return {
        "available_permissions": [
            {"key": k, "description": v} for k, v in ALL_PERMISSIONS.items()
        ],
        "default_employee_permissions": get_default_employee_permissions(),
        "admin_permissions": ["*"],
    }


@router.put("/admin/permissions/employee-defaults")
def update_employee_default_permissions(
    req: UpdateEmployeeDefaultPermissionsRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    updated = set_default_employee_permissions(req.permissions)
    record_audit_log(
        db=db,
        action="EMPLOYEE_DEFAULT_PERMISSIONS_CHANGED",
        resource_type="permissions",
        user=admin,
        details={"permissions": updated},
    )
    return {"default_employee_permissions": updated}


@router.get("/admin/access/preview/{user_id}")
def preview_user_access_endpoint(
    user_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Read-only simulation ('Preview access as user') for administrators."""
    target = (
        db.query(User)
        .filter(User.id == user_id, User.workspace_id == admin.workspace_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found in this workplace.")
    return authorization_service.preview_user_access(db, target)


@router.post("/admin/access/test")
def test_document_access_endpoint(
    req: AccessTestRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Test whether a specific user can access a specific document and return the exact policy reason."""
    target_user = (
        db.query(User)
        .filter(User.id == req.user_id, User.workspace_id == admin.workspace_id)
        .first()
    )
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")
    doc = db.query(Document).filter(Document.id == req.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    decision = authorization_service.evaluate_document_access(db, target_user, doc, action="read")
    return {
        "user": {"id": target_user.id, "username": target_user.username, "role": target_user.normalized_role},
        "document": {"id": doc.id, "filename": doc.filename, "access_level": doc.access_level},
        "status": "ALLOWED" if decision.allowed else "DENIED",
        "allowed": decision.allowed,
        "reason": decision.reason,
        "matched_rule": decision.matched_rule,
    }


@router.get("/admin/analytics")
def get_workplace_analytics(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Aggregate workplace analytics without exposing private employee conversation text.
    """
    wid = admin.workspace_id
    all_users = db.query(User).filter(User.workspace_id == wid).all()
    employees = [u for u in all_users if not u.is_admin]
    admins = [u for u in all_users if u.is_admin]
    active_users = [u for u in all_users if (u.status or "ACTIVE") == "ACTIVE"]

    all_docs = db.query(Document).filter(Document.workspace_id == wid).all()
    ready_docs = [d for d in all_docs if d.status == "Ready" and not getattr(d, "is_archived", False)]
    archived_docs = [d for d in all_docs if getattr(d, "is_archived", False) or d.status == "Archived"]
    total_chunks = sum(d.chunk_count or 0 for d in all_docs)

    sessions = db.query(ChatSession).filter(ChatSession.workspace_id == wid).all()
    session_ids = [s.id for s in sessions]
    questions_asked = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id.in_(session_ids), ChatMessage.role == "user")
        .count()
        if session_ids
        else 0
    )

    cols = db.query(Collection).filter(Collection.workspace_id == wid).all()
    popular_collections = []
    for c in cols:
        c_docs = sum(1 for d in all_docs if d.collection_name == c.name)
        c_queries = sum(1 for s in sessions if s.collection_filter == c.name)
        popular_collections.append(
            {
                "name": c.name,
                "access_level": c.access_level,
                "document_count": c_docs,
                "query_count": c_queries,
            }
        )
    popular_collections.sort(key=lambda x: (x["document_count"], x["query_count"]), reverse=True)

    modality_breakdown: dict[str, int] = {}
    policy_breakdown: dict[str, int] = {}
    for d in all_docs:
        mod = (d.modality or "text").lower()
        modality_breakdown[mod] = modality_breakdown.get(mod, 0) + 1
        pol = (d.access_level or "EMPLOYEE_SHARED").upper()
        policy_breakdown[pol] = policy_breakdown.get(pol, 0) + 1

    recent_logs = (
        db.query(AuditLog)
        .filter((AuditLog.workspace_id == wid) | (AuditLog.workspace_id == None))
        .order_by(AuditLog.timestamp.desc())
        .limit(15)
        .all()
    )

    return {
        "workplace_id": wid,
        "summary": {
            "total_users": len(all_users),
            "total_employees": len(employees),
            "active_employees": sum(1 for e in employees if (e.status or "ACTIVE") == "ACTIVE"),
            "disabled_employees": sum(1 for e in employees if (e.status or "ACTIVE") != "ACTIVE"),
            "total_admins": len(admins),
            "active_users": len(active_users),
            "total_documents": len(all_docs),
            "ready_documents": len(ready_docs),
            "archived_documents": len(archived_docs),
            "total_chunks": total_chunks,
            "questions_asked": questions_asked,
            "chat_sessions": len(sessions),
            "collections_count": len(cols),
        },
        "popular_collections": popular_collections,
        "modality_breakdown": [
            {"modality": k.upper(), "count": v} for k, v in modality_breakdown.items()
        ],
        "access_policy_breakdown": [
            {"policy": k, "count": v} for k, v in policy_breakdown.items()
        ],
        "recent_activity": [
            {
                "id": l.id,
                "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                "username": l.username,
                "user_role": l.user_role,
                "action": l.action,
                "resource_type": l.resource_type,
                "success": l.success,
                "severity": l.severity,
            }
            for l in recent_logs
        ],
    }


@router.get("/admin/audit-logs")
def list_audit_logs(
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(admin, "audit.read")
    q = db.query(AuditLog).filter(
        (AuditLog.workspace_id == admin.workspace_id) | (AuditLog.workspace_id == None)
    )
    if action:
        q = q.filter(AuditLog.action == action)
    if severity:
        q = q.filter(AuditLog.severity == severity.upper())
    logs = q.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": l.id,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            "user_id": l.user_id,
            "username": l.username,
            "user_role": l.user_role,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "success": l.success,
            "severity": l.severity,
            "ip_address": l.ip_address,
            "details": json.loads(l.details_json or "{}"),
        }
        for l in logs
    ]


# ─── 6. Collections Management (Workplace-Scoped) ─────────────────────────────

@router.get("/collections")
def list_collections(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cols = (
        db.query(Collection)
        .filter(Collection.workspace_id == current_user.workspace_id)
        .order_by(Collection.name)
        .all()
    )
    auth_docs = authorization_service.filter_authorized_documents(
        db, current_user, include_archived=current_user.is_admin
    )
    auth_doc_counts_by_col: dict[str, int] = {}
    for d in auth_docs:
        auth_doc_counts_by_col[d.collection_name] = auth_doc_counts_by_col.get(d.collection_name, 0) + 1

    visible = []
    for c in cols:
        if authorization_service.evaluate_collection_access(db, current_user, c).allowed:
            doc_cnt = (
                db.query(Document)
                .filter(
                    Document.collection_name == c.name,
                    Document.workspace_id == current_user.workspace_id,
                )
                .count()
                if current_user.is_admin
                else auth_doc_counts_by_col.get(c.name, 0)
            )
            visible.append(
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "is_private": c.is_private,
                    "access_level": c.access_level or "EMPLOYEE_SHARED",
                    "department_id": c.department_id,
                    "document_count": doc_cnt,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
            )
    return visible


@router.post("/collections")
def create_collection(
    req: CreateCollectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "collection.create")
    name = req.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Collection name is required.")
    existing = (
        db.query(Collection)
        .filter(
            Collection.name == name,
            Collection.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail=f"Collection '{name}' already exists in this workplace.")

    access_lvl = req.access_level.upper() if req.access_level.upper() in VALID_ACCESS_LEVELS else "EMPLOYEE_SHARED"
    col = Collection(
        name=name,
        description=req.description,
        workspace_id=current_user.workspace_id,
        is_private=req.is_private or (access_lvl == "ADMIN_ONLY"),
        access_level=access_lvl,
        department_id=req.department_id,
        created_by=current_user.username,
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    record_audit_log(
        db=db,
        action="COLLECTION_CREATED",
        resource_type="collection",
        user=current_user,
        resource_id=col.id,
        details={"name": col.name, "access_level": col.access_level},
    )
    return {
        "id": col.id,
        "name": col.name,
        "description": col.description,
        "is_private": col.is_private,
        "access_level": col.access_level,
        "document_count": 0,
    }


@router.put("/collections/{collection_id}/access")
def update_collection_access(
    collection_id: str,
    req: UpdateCollectionAccessRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    col = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.workspace_id == admin.workspace_id)
        .first()
    )
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found.")

    prev_level = col.access_level
    col.access_level = req.access_level.upper() if req.access_level.upper() in VALID_ACCESS_LEVELS else "EMPLOYEE_SHARED"
    col.is_private = req.is_private or (col.access_level == "ADMIN_ONLY")
    col.department_id = req.department_id or None

    db.query(CollectionAccess).filter(CollectionAccess.collection_id == col.id).delete()
    for gid in set(req.allowed_group_ids or []):
        db.add(
            CollectionAccess(
                collection_id=col.id,
                access_type="GROUP",
                group_id=gid,
                created_by=admin.username,
            )
        )
    for uid in set(req.allowed_user_ids or []):
        db.add(
            CollectionAccess(
                collection_id=col.id,
                access_type="USER",
                user_id=uid,
                created_by=admin.username,
            )
        )
    db.commit()

    record_audit_log(
        db=db,
        action="COLLECTION_ACCESS_CHANGED",
        resource_type="collection",
        user=admin,
        resource_id=col.id,
        details={
            "collection": col.name,
            "previous": prev_level,
            "new": col.access_level,
        },
    )
    return {
        "id": col.id,
        "name": col.name,
        "access_level": col.access_level,
        "is_private": col.is_private,
        "department_id": col.department_id,
    }


@router.delete("/collections/{collection_id}")
def delete_collection(
    collection_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(admin, "collection.delete")
    col = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.workspace_id == admin.workspace_id)
        .first()
    )
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found.")
    if col.name == "General":
        raise HTTPException(status_code=400, detail="The default 'General' collection cannot be deleted.")

    vector_store.delete_by_collection_name(col.name)
    db.delete(col)
    db.commit()
    record_audit_log(
        db=db,
        action="COLLECTION_DELETED",
        resource_type="collection",
        user=admin,
        resource_id=collection_id,
        details={"collection": col.name},
    )
    return {"status": "deleted", "collection": col.name}


# ─── 7. Document Upload, Access Policy Management & Secure File Delivery ──────

@router.post("/documents/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    collection: str = Form("General"),
    access_level: Optional[str] = Form(None),
    department_id: Optional[str] = Form(None),
    sync: bool = Form(True),
    selected_tables: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "document.upload")
    if not current_user.can_upload and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="You do not have permission to upload documents.")

    if not user_can_access_collection(current_user, collection, db=db):
        raise HTTPException(status_code=403, detail=f"No permission to access collection '{collection}'.")

    # 1. File validation & path traversal sanitization
    try:
        safe_name = sanitize_filename(file.filename or "uploaded_file")
        ext = validate_file_extension(safe_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    raw_bytes = await file.read()
    try:
        validate_file_size(len(raw_bytes))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Compute SHA-256 hash
    file_hash = compute_sha256_bytes(raw_bytes)

    # 3. Determine initial access policy
    # Security Rule: If an employee uploads a document without admin privileges, default to USER_SPECIFIC
    # (visible to the uploader and admins) unless admin explicitly shared it, preventing accidental org-wide leaks.
    if current_user.is_admin:
        resolved_access_level = (
            access_level.upper()
            if (access_level and access_level.upper() in VALID_ACCESS_LEVELS)
            else ("ADMIN_ONLY" if collection in {"HR", "Finance", "Management"} else "EMPLOYEE_SHARED")
        )
        approval_state = "APPROVED"
    else:
        resolved_access_level = (
            access_level.upper()
            if (access_level and access_level.upper() in {"USER_SPECIFIC", "DEPARTMENT_ONLY", "EMPLOYEE_SHARED"})
            else "USER_SPECIFIC"
        )
        approval_state = "APPROVED"

    # 4. Duplicate Detection: Check if exact hash already exists in this collection & workplace
    exact_match = (
        db.query(Document)
        .filter(
            Document.content_hash == file_hash,
            Document.collection_name == collection,
            Document.workspace_id == current_user.workspace_id,
            Document.status == "Ready",
        )
        .first()
    )
    if exact_match:
        if not authorization_service.evaluate_document_access(db, current_user, exact_match, action="read").allowed:
            raise HTTPException(status_code=403, detail="You do not have permission to overwrite or access this document.")
        return {
            "duplicate": True,
            "message": "Identical file hash already exists in the knowledge base. Skipped duplicate vector indexing.",
            "document": _serialize_document(exact_match, db=db),
        }

    # Ensure target collection exists in this workplace
    col_obj = (
        db.query(Collection)
        .filter(
            Collection.name == collection,
            Collection.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if not col_obj:
        if not current_user.is_admin:
            raise HTTPException(status_code=403, detail="Only administrators can create new collections during upload.")
        col_obj = Collection(
            name=collection,
            description=f"Collection {collection}",
            workspace_id=current_user.workspace_id,
            created_by=current_user.username,
        )
        db.add(col_obj)
        db.commit()
        db.refresh(col_obj)

    # 5. Document Versioning: Check if same filename exists with a different hash in this workplace
    existing_by_name = (
        db.query(Document)
        .filter(
            Document.filename == safe_name,
            Document.collection_name == collection,
            Document.workspace_id == current_user.workspace_id,
        )
        .first()
    )

    upload_dir = settings.resolve_path(settings.UPLOAD_DIR)
    if existing_by_name:
        if not current_user.is_admin and existing_by_name.owner != current_user.username:
            raise HTTPException(status_code=403, detail="You do not have permission to overwrite another user's document.")
        new_version = existing_by_name.version + 1
        stored_filename = f"v{new_version}_{file_hash[:8]}_{safe_name}"
        target_path = ensure_safe_path(upload_dir, upload_dir / stored_filename)
        target_path.write_bytes(raw_bytes)

        existing_by_name.version = new_version
        existing_by_name.content_hash = file_hash
        existing_by_name.file_path = str(target_path)
        existing_by_name.file_size = len(raw_bytes)
        existing_by_name.status = "Uploaded"
        existing_by_name.error_message = None
        existing_by_name.suggested_action = None
        if access_level and current_user.is_admin:
            existing_by_name.access_level = resolved_access_level
        doc_record = existing_by_name
        db.commit()
        db.refresh(doc_record)
    else:
        stored_filename = f"v1_{file_hash[:8]}_{safe_name}"
        target_path = ensure_safe_path(upload_dir, upload_dir / stored_filename)
        target_path.write_bytes(raw_bytes)

        doc_record = Document(
            filename=safe_name,
            original_filename=file.filename or safe_name,
            file_type=ext,
            modality=ext.lstrip("."),
            file_path=str(target_path),
            file_size=len(raw_bytes),
            content_hash=file_hash,
            version=1,
            collection_id=col_obj.id,
            collection_name=col_obj.name,
            workspace_id=current_user.workspace_id,
            owner=current_user.username,
            owner_id=current_user.id,
            access_level=resolved_access_level,
            department_id=department_id or current_user.department_id,
            approval_status=approval_state,
            status="Uploaded",
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        if resolved_access_level == "USER_SPECIFIC":
            db.add(
                DocumentAccess(
                    document_id=doc_record.id,
                    access_type="USER_SPECIFIC",
                    user_id=current_user.id,
                    created_by=current_user.username,
                )
            )
            db.commit()

    # Create IngestionJob
    job = IngestionJob(
        document_id=doc_record.id,
        status="Uploaded",
        stage="Uploaded",
        progress_pct=10,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    tables_list = None
    if selected_tables:
        try:
            tables_list = json.loads(selected_tables)
        except Exception:
            tables_list = [t.strip() for t in selected_tables.split(",") if t.strip()]

    if sync:
        process_document_ingestion(
            document_id=doc_record.id,
            job_id=job.id,
            selected_tables=tables_list,
        )
        db.refresh(doc_record)
    else:
        background_tasks.add_task(
            process_document_ingestion,
            document_id=doc_record.id,
            job_id=job.id,
            selected_tables=tables_list,
        )

    record_audit_log(
        db=db,
        action="DOCUMENT_UPLOAD",
        resource_type="document",
        user=current_user,
        resource_id=doc_record.id,
        details={
            "filename": doc_record.filename,
            "collection": doc_record.collection_name,
            "access_level": doc_record.access_level,
        },
    )

    return {
        "duplicate": False,
        "job_id": job.id,
        "document": _serialize_document(doc_record, db=db),
    }


@router.post("/database/inspect")
def inspect_db_endpoint(
    req: DatabaseInspectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "database.read")
    if is_internal_system_database(req.connection_url):
        record_audit_log(
            db=db,
            action="INTERNAL_DB_ACCESS_BLOCKED",
            resource_type="database",
            user=current_user,
            success=False,
            severity="ALERT",
            details={"attempted_connection": req.connection_url},
        )
        raise HTTPException(status_code=403, detail="Access to internal system database is strictly prohibited.")
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can inspect raw external database connections.")
    try:
        return inspect_database_schema(req.connection_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Database inspection failed: {e}")


@router.post("/database/ingest")
def ingest_external_db(
    req: DatabaseIngestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only administrators can ingest external databases.")
    if is_internal_system_database(req.connection_url):
        raise HTTPException(status_code=403, detail="Cannot ingest internal application metadata database.")

    col_obj = (
        db.query(Collection)
        .filter(
            Collection.name == req.collection,
            Collection.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if not col_obj:
        col_obj = Collection(
            name=req.collection,
            description=f"Collection {req.collection}",
            workspace_id=current_user.workspace_id,
            created_by=current_user.username,
        )
        db.add(col_obj)
        db.commit()
        db.refresh(col_obj)

    db_label = req.connection_url.split("/")[-1].split("\\")[-1] or "external_db"
    safe_label = sanitize_filename(db_label)
    hash_key = compute_sha256_bytes(
        f"{req.connection_url}::{json.dumps(req.selected_tables or [])}::{time.time()}".encode("utf-8")
    )
    access_lvl = req.access_level.upper() if req.access_level.upper() in VALID_ACCESS_LEVELS else "EMPLOYEE_SHARED"

    doc_record = Document(
        filename=safe_label,
        original_filename=safe_label,
        file_type=".db",
        modality="database",
        file_path=req.connection_url,
        file_size=0,
        content_hash=hash_key,
        version=1,
        collection_id=col_obj.id,
        collection_name=col_obj.name,
        workspace_id=current_user.workspace_id,
        owner=current_user.username,
        owner_id=current_user.id,
        access_level=access_lvl,
        status="Uploaded",
    )
    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    job = IngestionJob(
        document_id=doc_record.id,
        status="Uploaded",
        stage="Uploaded",
        progress_pct=10,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    process_document_ingestion(
        document_id=doc_record.id,
        job_id=job.id,
        selected_tables=req.selected_tables,
        connection_url=req.connection_url,
    )
    db.refresh(doc_record)
    record_audit_log(
        db=db,
        action="DATABASE_INGESTED",
        resource_type="database",
        user=current_user,
        resource_id=doc_record.id,
        details={"filename": doc_record.filename, "access_level": doc_record.access_level},
    )
    return {"document": _serialize_document(doc_record, db=db)}


@router.get("/documents")
def list_documents(
    collection: Optional[str] = Query(None),
    include_archived: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "document.read")
    authorized_docs = authorization_service.filter_authorized_documents(
        db=db,
        user=current_user,
        collection_filter=collection,
        only_ready=False,
        include_archived=bool(current_user.is_admin and include_archived),
    )
    return [
        _serialize_document(d, db=db, include_access_rules=current_user.is_admin)
        for d in authorized_docs
    ]


@router.get("/documents/{document_id}")
def get_document_details(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=403, detail="You don't have permission to access this resource.")

    decision = authorization_service.evaluate_document_access(db, current_user, doc, action="read")
    if not decision.allowed:
        record_audit_log(
            db=db,
            action="UNAUTHORIZED_DOCUMENT_ACCESS_ATTEMPT",
            resource_type="document",
            user=current_user,
            resource_id=document_id,
            success=False,
            severity="WARNING",
            details={"reason": decision.reason},
        )
        raise HTTPException(status_code=403, detail="You don't have permission to access this resource.")

    record_audit_log(
        db=db,
        action="DOCUMENT_VIEW",
        resource_type="document",
        user=current_user,
        resource_id=doc.id,
        details={"filename": doc.filename},
    )

    chunks = (
        db.query(ChunkRecord)
        .filter(ChunkRecord.document_id == doc.id)
        .order_by(ChunkRecord.chunk_index)
        .all()
    )
    versions = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version.desc())
        .all()
    )
    return {
        "document": _serialize_document(doc, db=db, include_access_rules=current_user.is_admin),
        "versions": [
            {
                "version": v.version,
                "content_hash": v.content_hash,
                "chunk_count": v.chunk_count,
                "status": v.status,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
        "chunks": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "content": c.content,
                "modality": c.modality,
                "page_number": c.page_number,
                "section_title": c.section_title,
                "metadata": json.loads(c.metadata_json or "{}"),
            }
            for c in chunks
        ],
    }


def _stream_authorized_document_file(
    document_id: str,
    current_user: User,
    db: Session,
) -> FileResponse:
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        # Return generic 403 so employees cannot probe which document IDs exist
        raise HTTPException(status_code=403, detail="You don't have permission to access this resource.")

    decision = authorization_service.evaluate_document_access(db, current_user, doc, action="read")
    if not decision.allowed:
        record_audit_log(
            db=db,
            action="UNAUTHORIZED_DOWNLOAD_ATTEMPT",
            resource_type="document",
            user=current_user,
            resource_id=document_id,
            success=False,
            severity="WARNING",
            details={"reason": decision.reason},
        )
        raise HTTPException(status_code=403, detail="You don't have permission to access this resource.")

    p = Path(doc.file_path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Raw file not available on disk.")

    record_audit_log(
        db=db,
        action="DOCUMENT_DOWNLOAD",
        resource_type="document",
        user=current_user,
        resource_id=doc.id,
        details={"filename": doc.filename},
    )
    return FileResponse(path=str(p), filename=doc.filename)


@router.get("/documents/{document_id}/content")
def serve_document_content(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Canonical secure authenticated & authorized document stream endpoint."""
    return _stream_authorized_document_file(document_id, current_user, db)


@router.get("/documents/{document_id}/file")
def serve_document_file(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Backward-compatible alias for secure authenticated & authorized document stream."""
    return _stream_authorized_document_file(document_id, current_user, db)


@router.put("/documents/{document_id}/access")
def update_document_access(
    document_id: str,
    req: UpdateDocumentAccessRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(admin, "document.manage_access")
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.workspace_id == admin.workspace_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    previous_level = doc.access_level
    new_level = req.access_level.upper()
    if new_level not in VALID_ACCESS_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid access_level '{req.access_level}'.")

    doc.access_level = new_level
    if req.department_id is not None:
        doc.department_id = req.department_id or None
    elif req.allowed_department_ids:
        doc.department_id = req.allowed_department_ids[0]

    if req.approval_status and req.approval_status.upper() in {"APPROVED", "PENDING_REVIEW", "REJECTED"}:
        doc.approval_status = req.approval_status.upper()

    # Replace explicit DocumentAccess rules for this document
    db.query(DocumentAccess).filter(DocumentAccess.document_id == doc.id).delete()

    dept_ids = set(req.allowed_department_ids or [])
    if req.department_id:
        dept_ids.add(req.department_id)
    for did in dept_ids:
        db.add(
            DocumentAccess(
                document_id=doc.id,
                access_type="DEPARTMENT_ONLY",
                department_id=did,
                created_by=admin.username,
            )
        )

    for gid in set(req.allowed_group_ids or []):
        db.add(
            DocumentAccess(
                document_id=doc.id,
                access_type="GROUP_ONLY",
                group_id=gid,
                created_by=admin.username,
            )
        )

    for uid in set(req.allowed_user_ids or []):
        db.add(
            DocumentAccess(
                document_id=doc.id,
                access_type="USER_SPECIFIC",
                user_id=uid,
                created_by=admin.username,
            )
        )

    for duid in set(req.denied_user_ids or []):
        db.add(
            DocumentAccess(
                document_id=doc.id,
                access_type="EXPLICIT_DENY",
                user_id=duid,
                created_by=admin.username,
            )
        )

    db.commit()
    db.refresh(doc)

    # Immediately update ChromaDB vector metadata without re-computing embeddings
    vector_store.update_document_access_metadata(
        document_id=doc.id,
        access_level=doc.access_level,
        department_id=doc.department_id,
        collection_name=doc.collection_name,
    )

    record_audit_log(
        db=db,
        action="ACCESS_POLICY_CHANGED",
        resource_type="document",
        user=admin,
        resource_id=doc.id,
        success=True,
        details={
            "filename": doc.filename,
            "previous": previous_level,
            "new": doc.access_level,
            "department_id": doc.department_id,
            "allowed_groups": req.allowed_group_ids,
            "allowed_users": req.allowed_user_ids,
        },
    )

    return _serialize_document(doc, db=db, include_access_rules=True)


@router.post("/documents/{document_id}/archive")
def archive_document(
    document_id: str,
    req: ArchiveDocumentRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.workspace_id == admin.workspace_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    doc.is_archived = bool(req.is_archived)
    if req.is_archived:
        doc.status = "Archived"
    elif doc.status == "Archived":
        doc.status = "Ready"
    db.commit()
    db.refresh(doc)

    record_audit_log(
        db=db,
        action="DOCUMENT_ARCHIVED" if req.is_archived else "DOCUMENT_UNARCHIVED",
        resource_type="document",
        user=admin,
        resource_id=doc.id,
        details={"filename": doc.filename, "is_archived": doc.is_archived},
    )
    return _serialize_document(doc, db=db, include_access_rules=True)


@router.put("/documents/{document_id}/move")
def move_document_to_collection(
    document_id: str,
    req: MoveDocumentRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.workspace_id == admin.workspace_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    target_name = req.collection.strip()
    if not target_name:
        raise HTTPException(status_code=400, detail="Target collection is required.")

    col = (
        db.query(Collection)
        .filter(Collection.name == target_name, Collection.workspace_id == admin.workspace_id)
        .first()
    )
    if not col:
        col = Collection(
            name=target_name,
            description=f"Collection {target_name}",
            workspace_id=admin.workspace_id,
            created_by=admin.username,
        )
        db.add(col)
        db.commit()
        db.refresh(col)

    prev_col = doc.collection_name
    doc.collection_id = col.id
    doc.collection_name = col.name
    db.commit()
    db.refresh(doc)

    vector_store.update_document_access_metadata(
        document_id=doc.id,
        access_level=doc.access_level,
        department_id=doc.department_id,
        collection_name=doc.collection_name,
    )

    record_audit_log(
        db=db,
        action="DOCUMENT_MOVED",
        resource_type="document",
        user=admin,
        resource_id=doc.id,
        details={"filename": doc.filename, "from": prev_col, "to": col.name},
    )
    return _serialize_document(doc, db=db, include_access_rules=True)


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "document.delete")
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.workspace_id == current_user.workspace_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    vector_store.delete_by_document_id(doc.id)

    try:
        p = Path(doc.file_path)
        upload_dir = settings.resolve_path(settings.UPLOAD_DIR)
        if p.exists() and p.is_file() and str(p.resolve()).startswith(str(upload_dir.resolve())):
            p.unlink(missing_ok=True)
    except Exception:
        pass

    fname = doc.filename
    db.delete(doc)
    db.commit()
    record_audit_log(
        db=db,
        action="DOCUMENT_DELETE",
        resource_type="document",
        user=current_user,
        resource_id=document_id,
        details={"filename": fname},
    )
    return {"status": "deleted", "document_id": document_id, "filename": fname}


@router.post("/documents/{document_id}/reindex")
def reindex_document(
    document_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.workspace_id == admin.workspace_id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    job = IngestionJob(
        document_id=doc.id,
        status="Uploaded",
        stage="Re-indexing",
        progress_pct=10,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    conn_url = doc.file_path if doc.modality == "database" and not Path(doc.file_path).exists() else None
    res = process_document_ingestion(
        document_id=doc.id,
        job_id=job.id,
        connection_url=conn_url,
    )
    db.refresh(doc)
    return {"result": res, "document": _serialize_document(doc, db=db)}


# ─── 7b. Raster-to-Vector Tracing Tool Endpoints (PNG/JPG -> SVG) ─────────────

@router.post("/tools/vectorize-image")
async def vectorize_image_upload(
    file: UploadFile = File(...),
    colormode: str = Form("color"),
    mode: str = Form("spline"),
    filter_speckle: int = Form(4),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "document.read")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Raster-to-vector tracing supports PNG, JPG, JPEG, WEBP, and BMP.",
        )

    upload_dir = settings.resolve_path(settings.UPLOAD_DIR) / "temp_vectorize"
    upload_dir.mkdir(parents=True, exist_ok=True)
    temp_img_path = upload_dir / f"vec_{uuid.uuid4().hex[:12]}_{sanitize_filename(file.filename or 'image.png')}"
    try:
        content = await file.read()
        temp_img_path.write_bytes(content)

        res = vector_converter.convert_to_svg(
            input_path=temp_img_path,
            colormode=colormode,
            mode=mode,
            filter_speckle=filter_speckle,
        )

        record_audit_log(
            db=db,
            action="IMAGE_VECTORIZATION",
            resource_type="tool",
            user=current_user,
            resource_id=res["filename"],
            details={"original_file": file.filename, "paths": res["path_count"]},
        )

        res["preview_url"] = f"/api/tools/vector-preview/{res['filename']}"
        res["download_url"] = f"/api/tools/vector-download/{res['filename']}"
        return res
    except ImageVectorizationError as ive:
        raise HTTPException(status_code=400, detail=str(ive))
    except Exception as e:
        error_logger.error(f"Image vectorization failed: {e}")
        raise HTTPException(status_code=500, detail=f"Image vectorization failed: {str(e)}")
    finally:
        if temp_img_path.exists():
            try:
                temp_img_path.unlink()
            except Exception:
                pass


@router.get("/tools/vector-preview/{filename}")
def preview_vector_svg(
    filename: str,
    current_user: User = Depends(get_optional_user),
):
    safe_name = sanitize_filename(filename)
    svg_dir = settings.resolve_path(settings.PROCESSED_DIR) / "vector_svgs"
    svg_path = svg_dir / safe_name
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail="Vector SVG file not found.")
    return FileResponse(
        path=str(svg_path),
        media_type="image/svg+xml",
        filename=safe_name,
    )


@router.get("/tools/vector-download/{filename}")
def download_vector_svg(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    safe_name = sanitize_filename(filename)
    svg_dir = settings.resolve_path(settings.PROCESSED_DIR) / "vector_svgs"
    svg_path = svg_dir / safe_name
    if not svg_path.exists():
        raise HTTPException(status_code=404, detail="Vector SVG file not found.")
    return FileResponse(
        path=str(svg_path),
        media_type="image/svg+xml",
        filename=safe_name,
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@router.post("/documents/{document_id}/vectorize")
def vectorize_document_image(
    document_id: str,
    colormode: str = Query("color"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "document.read")
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    decision = authorization_service.evaluate_document_access(db, current_user, doc, action="read")
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    if doc.modality != "image" and doc.file_type not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
        raise HTTPException(status_code=400, detail="Only image documents can be converted to vector SVG.")

    img_path = Path(doc.file_path)
    if not img_path.exists():
        raise HTTPException(status_code=404, detail="Source image file missing on disk.")

    try:
        res = vector_converter.convert_to_svg(input_path=img_path, colormode=colormode)
        res["preview_url"] = f"/api/tools/vector-preview/{res['filename']}"
        res["download_url"] = f"/api/tools/vector-download/{res['filename']}"
        return res
    except ImageVectorizationError as ive:
        raise HTTPException(status_code=400, detail=str(ive))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vectorization failed: {e}")


# ─── 8. Direct Document Search & RAG Chat Pipeline (Pre-Retrieval Filtered) ───

EMPLOYEE_EMPTY_KNOWLEDGE_RESPONSE = (
    "I couldn't find enough reliable information in the uploaded data available to your account to answer that question."
)


@router.post("/search")
def search_knowledge_base(
    req: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "rag.search")

    # Compute exact authorized document IDs BEFORE retrieval
    authorized_doc_ids = authorization_service.get_authorized_document_ids(
        db=db,
        user=current_user,
        collection_filter=req.collection,
        include_archived=bool(current_user.is_admin and req.include_archived),
    )
    allowed_cols = ["*"] if current_user.is_admin else current_user.allowed_collections

    ret = retriever.retrieve(
        db=db,
        query=req.query,
        top_k=req.top_k,
        mode=req.mode,
        allowed_collections=allowed_cols,
        selected_collection=req.collection,
        authorized_document_ids=authorized_doc_ids,
        workspace_id=current_user.workspace_id,
    )

    record_audit_log(
        db=db,
        action="RAG_SEARCH",
        resource_type="search",
        user=current_user,
        details={
            "mode": req.mode,
            "collection": req.collection,
            "authorized_docs_scope": len(authorized_doc_ids),
            "results_returned": len(ret["chunks"]),
        },
    )

    return {
        "query": req.query,
        "mode": req.mode,
        "collection": req.collection,
        "embedding_time_ms": ret["embedding_time_ms"],
        "retrieval_time_ms": ret["retrieval_time_ms"],
        "results": ret["chunks"],
        "citations": ret["citations"],
    }


@router.post("/chat")
async def chat_with_knowledge_base(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    authorization_service.require_permission(current_user, "rag.ask")
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Compute exact authorized document IDs BEFORE any vector, BM25, or SQL retrieval
    authorized_doc_ids = authorization_service.get_authorized_document_ids(
        db=db,
        user=current_user,
        collection_filter=req.collection,
    )
    allowed_cols = ["*"] if current_user.is_admin else current_user.allowed_collections

    # Manage user-isolated ChatSession in SQLite
    session_obj = None
    if req.session_id:
        session_obj = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == req.session_id,
                ChatSession.user_id == current_user.id,
                ChatSession.workspace_id == current_user.workspace_id,
            )
            .first()
        )
    if not session_obj:
        session_obj = ChatSession(
            title=question[:60],
            user_id=current_user.id,
            workspace_id=current_user.workspace_id,
            collection_filter=req.collection,
        )
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)

    prior_msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_obj.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    history = [{"role": m.role, "content": m.content} for m in prior_msgs[-6:]]

    active_ws = req.active_workspace
    if not active_ws and prior_msgs:
        for pm in reversed(prior_msgs):
            if pm.role == "assistant" and pm.observability_json:
                try:
                    pm_obs = json.loads(pm.observability_json)
                    if pm_obs.get("structured_response"):
                        active_ws = pm_obs["structured_response"]
                        break
                except Exception:
                    pass

    # Verify active_ws sources are authorized for current_user
    if active_ws and not current_user.is_admin:
        ws_sources = active_ws.get("sources", [])
        auth_set = set(authorized_doc_ids)
        for src in ws_sources:
            sid = src.get("document_id")
            if sid and sid not in auth_set:
                active_ws = None
                break

    user_msg = ChatMessage(
        session_id=session_obj.id,
        role="user",
        content=question,
    )
    db.add(user_msg)
    db.commit()

    # Step 0: Query Routing
    route = route_user_query(
        db=db,
        question=question,
        has_active_workspace=bool(active_ws),
    )

    if route == "workspace_followup" and active_ws:
        mutated_ws = apply_workspace_followup_command(active_ws, question)
        mutated_dict = mutated_ws.model_dump()
        summary_msg = (
            f"Updated workspace **{mutated_ws.title}** to `v{mutated_ws.version}` "
            f"({len(mutated_ws.components)} components: {', '.join(c.type for c in mutated_ws.components)})."
        )
        obs = {
            "query": question,
            "route": route,
            "embedding_time_ms": 0.0,
            "retrieval_time_ms": 0.0,
            "llm_time_ms": 0.0,
            "retrieved_chunks_count": 0,
            "structured_response": mutated_dict,
        }
        asst_msg = ChatMessage(
            session_id=session_obj.id,
            role="assistant",
            content=summary_msg,
            answer_found=True,
            citations_json=json.dumps([s.model_dump() for s in mutated_ws.sources]),
            observability_json=json.dumps(obs),
        )
        db.add(asst_msg)
        db.commit()

        if req.stream:
            async def followup_stream():
                yield f"data: {json.dumps({'type': 'metadata', 'session_id': session_obj.id, 'citations': [s.model_dump() for s in mutated_ws.sources], 'embedding_time_ms': 0.0, 'retrieval_time_ms': 0.0, 'retrieved_chunks': []})}\n\n"
                yield f"data: {json.dumps({'type': 'token', 'token': summary_msg})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'answer_found': True, 'citations': [s.model_dump() for s in mutated_ws.sources], 'observability': obs, 'structured_response': mutated_dict})}\n\n"

            return StreamingResponse(followup_stream(), media_type="text/event-stream")

        return {
            "session_id": session_obj.id,
            "question": question,
            "answer": summary_msg,
            "answer_found": True,
            "status_flag": "ANSWER FOUND",
            "citations": [s.model_dump() for s in mutated_ws.sources],
            "observability": obs,
            "structured_response": mutated_dict,
        }

    # Pre-authorized Read-Only Database Query Path
    db_query_result = None
    if route in {"database", "hybrid", "documents"} and authorized_doc_ids:
        db_query_result = plan_and_execute_database_query(
            db=db,
            question=question,
            allowed_collections=allowed_cols,
            selected_collection=req.collection,
            authorized_document_ids=authorized_doc_ids,
        )
        if db_query_result:
            record_audit_log(
                db=db,
                action="DATABASE_QUERY",
                resource_type="database",
                user=current_user,
                resource_id=db_query_result.get("document_id"),
                details={"table": db_query_result.get("table")},
            )

    # Pre-authorized Vector + Hybrid Retrieval
    ret = retriever.retrieve(
        db=db,
        query=question,
        top_k=req.top_k,
        mode=req.mode,
        allowed_collections=allowed_cols,
        selected_collection=req.collection,
        authorized_document_ids=authorized_doc_ids,
        workspace_id=current_user.workspace_id,
    )

    record_audit_log(
        db=db,
        action="RAG_QUERY",
        resource_type="chat",
        user=current_user,
        resource_id=session_obj.id,
        details={
            "collection": req.collection,
            "authorized_docs_scope": len(authorized_doc_ids),
            "retrieved_chunks": len(ret["chunks"]),
        },
    )

    if req.stream:
        async def event_generator():
            t_llm0 = time.perf_counter()
            collected_tokens: list[str] = []
            meta_payload = {
                "type": "metadata",
                "session_id": session_obj.id,
                "citations": ret["citations"],
                "embedding_time_ms": ret["embedding_time_ms"],
                "retrieval_time_ms": ret["retrieval_time_ms"],
                "retrieved_chunks": [
                    {
                        "chunk_id": c["chunk_id"],
                        "filename": c["citation"]["filename"],
                        "locator": c["citation"]["locator"],
                        "similarity": c["similarity"],
                        "content": c["content"],
                    }
                    for c in ret["chunks"]
                ],
            }
            yield f"data: {json.dumps(meta_payload)}\n\n"

            fin_calc_res = financial_engine.execute_financial_query(question, ret["chunks"])
            if fin_calc_res:
                token = fin_calc_res["answer"]
                collected_tokens.append(token)
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            else:
                async for token in llm_client.stream_answer(
                    question=question,
                    assembled_context=ret["assembled_context"],
                    retrieved_chunks=ret["chunks"],
                    chat_history=history,
                ):
                    collected_tokens.append(token)
                    yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

            llm_time_ms = round((time.perf_counter() - t_llm0) * 1000, 2)
            full_answer = "".join(collected_tokens).strip()
            ans_found = NOT_FOUND_RESPONSE.lower() not in full_answer.lower()
            if not ans_found and not current_user.is_admin:
                full_answer = EMPLOYEE_EMPTY_KNOWLEDGE_RESPONSE
            final_citations = ret["citations"] if ans_found else []

            structured_resp = build_grounded_structured_response(
                question=question,
                answer_text=full_answer,
                answer_found=ans_found,
                retrieved_chunks=ret["chunks"],
                citations=final_citations,
                route=route,
                db_query_result=db_query_result,
            )
            structured_dict = structured_resp.model_dump()

            obs = {
                "query": question,
                "route": route,
                "embedding_time_ms": ret["embedding_time_ms"],
                "retrieval_time_ms": ret["retrieval_time_ms"],
                "llm_time_ms": llm_time_ms,
                "retrieved_chunks_count": len(ret["chunks"]),
                "similarity_scores": [c["similarity"] for c in ret["chunks"]],
                "final_context": ret["assembled_context"] if current_user.is_admin else "",
                "structured_response": structured_dict,
            }

            db_inner = next(get_db())
            try:
                asst_msg = ChatMessage(
                    session_id=session_obj.id,
                    role="assistant",
                    content=full_answer,
                    answer_found=ans_found,
                    citations_json=json.dumps(final_citations),
                    observability_json=json.dumps(obs),
                )
                db_inner.add(asst_msg)
                db_inner.commit()
            finally:
                db_inner.close()

            yield f"data: {json.dumps({'type': 'done', 'answer_found': ans_found, 'citations': final_citations, 'observability': obs, 'structured_response': structured_dict})}\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Non-streaming response
    fin_calc_res = financial_engine.execute_financial_query(question, ret["chunks"])
    if fin_calc_res:
        ans_found = True
        final_answer_text = fin_calc_res["answer"]
        llm_time_ms = 0.0
        llm_res = {
            "answer": final_answer_text,
            "answer_found": True,
            "model_used": "Deterministic Financial Engine",
            "runtime": "deterministic_math",
        }
    else:
        t_llm0 = time.perf_counter()
        llm_res = await llm_client.generate_answer(
            question=question,
            assembled_context=ret["assembled_context"],
            retrieved_chunks=ret["chunks"],
            chat_history=history,
        )
        llm_time_ms = round((time.perf_counter() - t_llm0) * 1000, 2)
        ans_found = llm_res["answer_found"]
        final_answer_text = llm_res["answer"]
        if not ans_found and not current_user.is_admin:
            final_answer_text = EMPLOYEE_EMPTY_KNOWLEDGE_RESPONSE
    final_citations = ret["citations"] if ans_found else []

    structured_resp = build_grounded_structured_response(
        question=question,
        answer_text=final_answer_text,
        answer_found=ans_found,
        retrieved_chunks=ret["chunks"],
        citations=final_citations,
        route=route,
        db_query_result=db_query_result,
    )
    structured_dict = structured_resp.model_dump()

    observability = {
        "query": question,
        "route": route,
        "embedding_time_ms": ret["embedding_time_ms"],
        "retrieval_time_ms": ret["retrieval_time_ms"],
        "llm_time_ms": llm_time_ms,
        "model_used": llm_res["model_used"],
        "runtime": llm_res["runtime"],
        "retrieved_chunks": [
            {
                "chunk_id": c["chunk_id"],
                "document_id": c["document_id"],
                "filename": c["citation"]["filename"],
                "locator": c["citation"]["locator"],
                "similarity": c["similarity"],
                "vector_similarity": c["vector_similarity"],
                "keyword_score": c["keyword_score"],
                "content": c["content"],
            }
            for c in ret["chunks"]
        ],
        "final_context": ret["assembled_context"] if current_user.is_admin else "",
        "structured_response": structured_dict,
    }

    asst_msg = ChatMessage(
        session_id=session_obj.id,
        role="assistant",
        content=final_answer_text,
        answer_found=ans_found,
        citations_json=json.dumps(final_citations),
        observability_json=json.dumps(observability),
    )
    db.add(asst_msg)
    db.commit()

    # Automatically save/update workspace artifact record with source_document_ids for authorization
    source_doc_ids = list({c["document_id"] for c in ret["chunks"] if c.get("document_id")})
    if db_query_result and db_query_result.get("document_id"):
        if db_query_result["document_id"] not in source_doc_ids:
            source_doc_ids.append(db_query_result["document_id"])

    if ans_found and len(structured_resp.components) > 0:
        artifact = SavedArtifact(
            title=structured_resp.title or question[:60],
            owner_id=current_user.id,
            session_id=session_obj.id,
            workspace_id=current_user.workspace_id,
            visibility="PRIVATE",
            source_document_ids_json=json.dumps(source_doc_ids),
            payload_json=json.dumps(structured_dict),
        )
        db.add(artifact)
        db.commit()

    return {
        "session_id": session_obj.id,
        "question": question,
        "answer": final_answer_text,
        "answer_found": ans_found,
        "status_flag": "ANSWER FOUND" if ans_found else "ANSWER NOT FOUND",
        "citations": final_citations,
        "observability": observability,
        "structured_response": structured_dict,
    }


# ─── 9. Protected Workspaces, Artifacts & Chat History ────────────────────────

@router.post("/workspace/mutate")
def mutate_workspace(
    req: WorkspaceMutateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Apply a direct follow-up command or transformation to an existing StructuredResponse workspace
    after verifying the user is authorized to access its underlying source documents.
    """
    if not current_user.is_admin:
        sources = req.active_workspace.get("sources", [])
        for src in sources:
            doc_id = src.get("document_id")
            if doc_id:
                doc = db.query(Document).filter(Document.id == doc_id).first()
                if doc and not authorization_service.evaluate_document_access(db, current_user, doc, "read").allowed:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have permission to access the sources of this workspace.",
                    )

    mutated = apply_workspace_followup_command(req.active_workspace, req.command)
    return {
        "status": "ok",
        "command": req.command,
        "structured_response": mutated.model_dump(),
    }


@router.get("/artifacts")
def list_artifacts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = (
        db.query(SavedArtifact)
        .filter(SavedArtifact.workspace_id == current_user.workspace_id)
        .order_by(SavedArtifact.updated_at.desc())
    )
    if not current_user.is_admin:
        q = q.filter(SavedArtifact.owner_id == current_user.id)
    artifacts = q.limit(100).all()
    visible = []
    for a in artifacts:
        if authorization_service.can_access_artifact(db, current_user, a, action="read"):
            visible.append(
                {
                    "id": a.id,
                    "title": a.title,
                    "owner_id": a.owner_id,
                    "session_id": a.session_id,
                    "visibility": a.visibility,
                    "source_document_ids": a.source_document_ids,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
            )
    return visible


@router.post("/artifacts")
def create_artifact(
    req: SaveArtifactRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    for sid in req.source_document_ids:
        doc = db.query(Document).filter(Document.id == sid).first()
        if doc and not authorization_service.evaluate_document_access(db, current_user, doc, "read").allowed:
            raise HTTPException(status_code=403, detail="Unauthorized source document in artifact.")

    art = SavedArtifact(
        title=req.title.strip() or "Workspace Artifact",
        owner_id=current_user.id,
        session_id=req.session_id,
        workspace_id=current_user.workspace_id,
        visibility=req.visibility.upper() if req.visibility.upper() in {"PRIVATE", "SHARED", "ADMIN_ONLY"} else "PRIVATE",
        source_document_ids_json=json.dumps(req.source_document_ids),
        payload_json=json.dumps(req.payload),
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    return {
        "id": art.id,
        "title": art.title,
        "owner_id": art.owner_id,
        "visibility": art.visibility,
        "source_document_ids": art.source_document_ids,
        "payload": json.loads(art.payload_json or "{}"),
    }


@router.get("/artifacts/{artifact_id}")
def get_artifact(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    art = db.query(SavedArtifact).filter(SavedArtifact.id == artifact_id).first()
    if not art or not authorization_service.can_access_artifact(db, current_user, art, action="read"):
        raise HTTPException(status_code=403, detail="You don't have permission to access this resource.")
    return {
        "id": art.id,
        "title": art.title,
        "owner_id": art.owner_id,
        "session_id": art.session_id,
        "visibility": art.visibility,
        "source_document_ids": art.source_document_ids,
        "payload": json.loads(art.payload_json or "{}"),
        "created_at": art.created_at.isoformat() if art.created_at else None,
    }


@router.delete("/artifacts/{artifact_id}")
def delete_artifact(
    artifact_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    art = db.query(SavedArtifact).filter(SavedArtifact.id == artifact_id).first()
    if not art or not authorization_service.can_access_artifact(db, current_user, art, action="delete"):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this resource.")
    db.delete(art)
    db.commit()
    return {"status": "deleted", "artifact_id": artifact_id}


@router.get("/chat/sessions")
@router.get("/chats")
def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == current_user.id,
            ChatSession.workspace_id == current_user.workspace_id,
        )
        .order_by(ChatSession.updated_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "title": s.title,
            "collection_filter": s.collection_filter,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in sessions
    ]


@router.get("/chat/sessions/{session_id}")
def get_chat_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
            ChatSession.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if not s:
        raise HTTPException(status_code=403, detail="You don't have permission to access this conversation.")
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == s.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return {
        "session": {"id": s.id, "title": s.title, "collection_filter": s.collection_filter},
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "answer_found": m.answer_found,
                "citations": json.loads(m.citations_json or "[]"),
                "observability": json.loads(m.observability_json or "{}"),
                "structured_response": json.loads(m.observability_json or "{}").get("structured_response"),
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in msgs
        ],
    }


@router.delete("/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id,
            ChatSession.workspace_id == current_user.workspace_id,
        )
        .first()
    )
    if not s:
        raise HTTPException(status_code=403, detail="You don't have permission to delete this conversation.")
    db.delete(s)
    db.commit()
    return {"status": "deleted", "session_id": session_id}

