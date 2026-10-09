import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session
from backend.core.config import settings


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


Base = declarative_base()


class Workspace(Base):
    """
    Represents a Workplace (organization / company / team) on the platform.
    Maps to the `workspaces` table for backward compatibility while providing
    both `id` and `workplace_id` aliases and full branding/configuration metadata.
    """
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(100), nullable=True, index=True)
    logo = Column(Text, default="")
    description = Column(Text, default="")
    industry = Column(String(100), default="")
    created_by = Column(String(100), default="admin")
    status = Column(String(30), nullable=False, default="ACTIVE")  # ACTIVE, ARCHIVED
    assistant_name = Column(String(100), nullable=False, default="ONYX AI")
    welcome_message = Column(Text, nullable=False, default="Ask anything about your workplace knowledge.")
    default_doc_visibility = Column(String(40), nullable=False, default="EMPLOYEE_SHARED")
    allow_employee_uploads = Column(Boolean, nullable=False, default=False)
    session_duration_minutes = Column(Integer, nullable=False, default=1440)
    onboarding_completed = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utc_now)

    users = relationship("User", back_populates="workspace", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="workspace", cascade="all, delete-orphan")

    @property
    def workplace_id(self) -> str:
        return self.id


# Alias for clarity in workplace-scoped modules
Workplace = Workspace


class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, default="")
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=utc_now)

    @property
    def workplace_id(self) -> str:
        return self.workspace_id


class Group(Base):
    __tablename__ = "groups"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, default="")
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=utc_now)

    @property
    def workplace_id(self) -> str:
        return self.workspace_id


class UserGroup(Base):
    __tablename__ = "user_groups"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=True, default="")
    email = Column(String(150), nullable=True, default="")
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    # Normalized role: "admin" or "employee" (accepts legacy "ADMIN" / "MEMBER" seamlessly)
    role = Column(String(30), nullable=False, default="employee")
    job_title = Column(String(120), nullable=True, default="Employee")
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True, index=True)
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, SUSPENDED, DISABLED, INVITED
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    allowed_collections_json = Column(Text, default='["General"]')
    permissions_json = Column(Text, default="[]")
    can_upload = Column(Boolean, default=False)
    invite_token = Column(String(100), nullable=True, index=True)
    invite_status = Column(String(30), nullable=False, default="ACCEPTED")  # PENDING, ACCEPTED
    token_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    last_login = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, nullable=True)

    workspace = relationship("Workspace", back_populates="users")

    @property
    def workplace_id(self) -> str:
        return self.workspace_id

    @property
    def is_admin(self) -> bool:
        return (self.role or "").strip().lower() == "admin"

    @property
    def normalized_role(self) -> str:
        return "admin" if self.is_admin else "employee"

    @property
    def allowed_collections(self) -> list[str]:
        if self.is_admin:
            return ["*"]
        try:
            return json.loads(self.allowed_collections_json or '["General"]')
        except Exception:
            return ["General"]

    @property
    def custom_permissions(self) -> list[str]:
        try:
            return json.loads(self.permissions_json or "[]")
        except Exception:
            return []


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti = Column(String(64), unique=True, nullable=False, index=True)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, default="")
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    is_private = Column(Boolean, default=False)
    access_level = Column(String(40), nullable=False, default="EMPLOYEE_SHARED")
    allowed_roles_json = Column(Text, default='["admin", "employee"]')
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=utc_now)

    workspace = relationship("Workspace", back_populates="collections")
    documents = relationship("Document", back_populates="collection_rel", cascade="all, delete-orphan")

    @property
    def workplace_id(self) -> str:
        return self.workspace_id


class CollectionAccess(Base):
    __tablename__ = "collection_access"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    collection_id = Column(String(36), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    access_type = Column(String(40), nullable=False, default="ROLE")  # ADMIN_ONLY, EMPLOYEE_SHARED, DEPARTMENT, GROUP, USER, DENY_USER
    role = Column(String(30), nullable=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    created_by = Column(String(100), default="admin")
    created_at = Column(DateTime, default=utc_now)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False, index=True)
    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    modality = Column(String(50), nullable=False, default="text")
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    content_hash = Column(String(64), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    collection_id = Column(String(36), ForeignKey("collections.id"), nullable=False)
    collection_name = Column(String(100), nullable=False, default="General", index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    owner = Column(String(100), nullable=False, default="admin")
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # Access Control Fields
    # Values: ADMIN_ONLY, EMPLOYEE_SHARED, DEPARTMENT_ONLY, GROUP_ONLY, USER_SPECIFIC
    access_level = Column(String(40), nullable=False, default="EMPLOYEE_SHARED", index=True)
    department_id = Column(String(36), ForeignKey("departments.id"), nullable=True, index=True)
    approval_status = Column(String(30), nullable=False, default="APPROVED")  # APPROVED, PENDING_REVIEW, REJECTED
    is_archived = Column(Boolean, nullable=False, default=False)

    # Processing Status: Uploaded, Extracting, OCR, Chunking, Embedding, Indexing, Ready, Failed, Archived
    status = Column(String(50), nullable=False, default="Uploaded")
    chunk_count = Column(Integer, nullable=False, default=0)
    page_count = Column(Integer, nullable=False, default=1)
    error_message = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    metadata_json = Column(Text, default="{}")

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    collection_rel = relationship("Collection", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("ChunkRecord", back_populates="document", cascade="all, delete-orphan")
    jobs = relationship("IngestionJob", back_populates="document", cascade="all, delete-orphan")
    access_rules = relationship("DocumentAccess", back_populates="document", cascade="all, delete-orphan")

    @property
    def workplace_id(self) -> str:
        return self.workspace_id


class DocumentAccess(Base):
    __tablename__ = "document_access"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    # access_type: ADMIN_ONLY, EMPLOYEE_SHARED, DEPARTMENT_ONLY, GROUP_ONLY, USER_SPECIFIC, EXPLICIT_DENY
    access_type = Column(String(40), nullable=False, index=True)
    role = Column(String(30), nullable=True)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=True, index=True)
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    created_by = Column(String(100), default="admin")
    created_at = Column(DateTime, default=utc_now)

    document = relationship("Document", back_populates="access_rules")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=False, default=0)
    chunk_count = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="Ready")
    created_at = Column(DateTime, default=utc_now)

    document = relationship("Document", back_populates="versions")


class ChunkRecord(Base):
    __tablename__ = "chunks"

    id = Column(String(64), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), nullable=True, index=True)
    version = Column(Integer, nullable=False, default=1)
    chunk_index = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=False)
    modality = Column(String(50), nullable=False, default="text")
    page_number = Column(Integer, nullable=True)
    section_title = Column(String(255), nullable=True)
    collection_name = Column(String(100), nullable=False, default="General", index=True)
    content_hash = Column(String(64), nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)

    document = relationship("Document", back_populates="chunks")

    @property
    def workplace_id(self) -> str:
        return self.workspace_id or ""


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="Uploaded")
    stage = Column(String(50), nullable=False, default="Uploaded")
    progress_pct = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    suggested_action = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    document = relationship("Document", back_populates="jobs")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False, default="New Knowledge Session")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    collection_filter = Column(String(100), default="ALL")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    @property
    def workplace_id(self) -> str:
        return self.workspace_id


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    answer_found = Column(Boolean, default=True)
    citations_json = Column(Text, default="[]")
    observability_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=utc_now)

    session = relationship("ChatSession", back_populates="messages")


class SavedArtifact(Base):
    __tablename__ = "saved_artifacts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(255), nullable=False)
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id"), nullable=False, index=True)
    visibility = Column(String(30), nullable=False, default="PRIVATE")  # PRIVATE, SHARED, ADMIN_ONLY
    source_document_ids_json = Column(Text, default="[]")
    payload_json = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    @property
    def workplace_id(self) -> str:
        return self.workspace_id

    @property
    def source_document_ids(self) -> list[str]:
        try:
            return json.loads(self.source_document_ids_json or "[]")
        except Exception:
            return []


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    workspace_id = Column(String(36), nullable=True, index=True)
    timestamp = Column(DateTime, default=utc_now, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    user_role = Column(String(30), nullable=True)
    action = Column(String(80), nullable=False, index=True)
    resource_type = Column(String(60), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    success = Column(Boolean, default=True, nullable=False)
    severity = Column(String(20), default="INFO", nullable=False)  # INFO, WARNING, ALERT
    ip_address = Column(String(64), nullable=True)
    details_json = Column(Text, default="{}")

    @property
    def workplace_id(self) -> str:
        return self.workspace_id or ""


sqlite_path = settings.resolve_path(settings.SQLITE_DB_PATH)
sqlite_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{sqlite_path}",
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def run_safe_schema_migrations() -> None:
    """
    Non-destructively add new Workplace, RBAC, and ABAC columns to existing SQLite tables.
    Preserves 100% of existing workplaces, users, documents, chunks, and sessions.
    """
    from sqlalchemy import inspect as sa_inspect, text

    Base.metadata.create_all(bind=engine)
    insp = sa_inspect(engine)
    existing_tables = set(insp.get_table_names())

    migrations: list[tuple[str, str, str]] = [
        ("workspaces", "slug", "VARCHAR(100)"),
        ("workspaces", "logo", "TEXT DEFAULT ''"),
        ("workspaces", "industry", "VARCHAR(100) DEFAULT ''"),
        ("workspaces", "created_by", "VARCHAR(100) DEFAULT 'admin'"),
        ("workspaces", "status", "VARCHAR(30) DEFAULT 'ACTIVE'"),
        ("workspaces", "assistant_name", "VARCHAR(100) DEFAULT 'ONYX AI'"),
        ("workspaces", "welcome_message", "TEXT DEFAULT 'Ask anything about your workplace knowledge.'"),
        ("workspaces", "default_doc_visibility", "VARCHAR(40) DEFAULT 'EMPLOYEE_SHARED'"),
        ("workspaces", "allow_employee_uploads", "BOOLEAN DEFAULT 0"),
        ("workspaces", "session_duration_minutes", "INTEGER DEFAULT 1440"),
        ("workspaces", "onboarding_completed", "BOOLEAN DEFAULT 1"),
        ("users", "name", "VARCHAR(150) DEFAULT ''"),
        ("users", "email", "VARCHAR(150) DEFAULT ''"),
        ("users", "job_title", "VARCHAR(120) DEFAULT 'Employee'"),
        ("users", "department_id", "VARCHAR(36)"),
        ("users", "status", "VARCHAR(20) DEFAULT 'ACTIVE'"),
        ("users", "permissions_json", "TEXT DEFAULT '[]'"),
        ("users", "invite_token", "VARCHAR(100)"),
        ("users", "invite_status", "VARCHAR(30) DEFAULT 'ACCEPTED'"),
        ("users", "token_version", "INTEGER DEFAULT 1"),
        ("users", "updated_at", "DATETIME"),
        ("users", "last_login", "DATETIME"),
        ("users", "last_active_at", "DATETIME"),
        ("collections", "access_level", "VARCHAR(40) DEFAULT 'EMPLOYEE_SHARED'"),
        ("collections", "department_id", "VARCHAR(36)"),
        ("documents", "owner_id", "VARCHAR(36)"),
        ("documents", "access_level", "VARCHAR(40) DEFAULT 'EMPLOYEE_SHARED'"),
        ("documents", "department_id", "VARCHAR(36)"),
        ("documents", "approval_status", "VARCHAR(30) DEFAULT 'APPROVED'"),
        ("documents", "is_archived", "BOOLEAN DEFAULT 0"),
        ("chunks", "workspace_id", "VARCHAR(36)"),
        ("audit_logs", "workspace_id", "VARCHAR(36)"),
    ]

    with engine.begin() as conn:
        for table_name, col_name, col_def in migrations:
            if table_name in existing_tables:
                cols = {c["name"] for c in insp.get_columns(table_name)}
                if col_name not in cols:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_def}"))

        # Drop legacy global unique index on departments.name and groups.name if present
        # so that multiple workplaces can independently create "Engineering", "HR", "Finance", etc.
        for tbl in ("departments", "groups"):
            if tbl in existing_tables:
                for idx in insp.get_indexes(tbl):
                    if idx.get("unique") and idx.get("column_names") == ["name"] and idx.get("name"):
                        try:
                            conn.execute(text(f"DROP INDEX IF EXISTS {idx['name']}"))
                        except Exception:
                            pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
