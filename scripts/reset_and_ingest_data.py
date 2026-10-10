import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import sys
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.core.config import settings
from backend.core.security import compute_sha256_bytes, sanitize_filename, validate_file_extension
from backend.database.sqlite_db import (
    SessionLocal,
    User,
    Workspace,
    Collection,
    Document,
    DocumentVersion,
    ChunkRecord,
    IngestionJob,
    ChatSession,
    ChatMessage,
    SavedArtifact,
    AuditLog,
    UserSession,
    DocumentAccess,
    CollectionAccess,
    UserGroup,
    Group,
    Department,
)
from backend.auth.auth_handler import init_db_and_defaults
from backend.embeddings.embedding_service import embedding_service
from backend.ingestion.pipeline import process_document_ingestion
from backend.database.vector_store import vector_store

def run():
    print("=== Step 1: Pre-warming Local Embedding Model ===")
    embedding_service.load_model()
    print("[OK] Embedding model pre-warmed.")

    print("\n=== Step 2: Purging Old SQLite Data ===")
    db = SessionLocal()
    try:
        db.query(ChatMessage).delete()
        db.query(ChatSession).delete()
        db.query(SavedArtifact).delete()
        db.query(AuditLog).delete()
        db.query(UserSession).delete()
        db.query(DocumentAccess).delete()
        db.query(CollectionAccess).delete()
        db.query(UserGroup).delete()
        db.query(ChunkRecord).delete()
        db.query(DocumentVersion).delete()
        db.query(IngestionJob).delete()
        db.query(Document).delete()
        db.query(Collection).delete()
        db.query(Group).delete()
        db.query(Department).delete()
        db.query(User).delete()
        db.query(Workspace).delete()
        db.commit()
        print("[OK] SQLite tables purged successfully.")
    finally:
        db.close()

    print("\n=== Step 3: Purging ChromaDB Vectors ===")
    try:
        vector_store.reset()
        print(f"[OK] ChromaDB collection reset. Current vector count: {vector_store.count()}")
    except Exception as e:
        print(f"Collection reset warning: {e}")

    print("\n=== Step 4: Cleaning Old Files from Uploads Directory ===")
    upload_dir = settings.resolve_path(settings.UPLOAD_DIR)
    if upload_dir.exists():
        for item in upload_dir.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except Exception as e:
                    print(f"Could not remove {item.name}: {e}")
    else:
        upload_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Upload directory {upload_dir} cleaned.")

    print("\n=== Step 5: Initializing Clean 'ONYX Studio' Workspace and Defaults ===")
    init_db_and_defaults()
    
    db = SessionLocal()
    try:
        workspace = db.query(Workspace).filter(Workspace.name == "ONYX Studio").first()
        if not workspace:
            workspace = db.query(Workspace).first()
        admin_user = db.query(User).filter(User.username == "admin").first()
        workspace_id = workspace.id
        admin_username = admin_user.username
        admin_id = admin_user.id
        print(f"[OK] Primary Workspace: '{workspace.name}' (ID: {workspace_id})")
        print(f"[OK] Admin User: '{admin_username}' (Role: {admin_user.role})")

        collections = {c.name: c.id for c in db.query(Collection).filter(Collection.workspace_id == workspace_id).all()}
        print(f"[OK] Seeded Collections: {list(collections.keys())}")
    finally:
        db.close()

    print("\n=== Step 6: Ingesting Files from ONYX_Data ===")
    source_dir = Path(r"c:\Users\devik\Desktop\rag\ONYX_Data")
    if not source_dir.exists():
        raise FileNotFoundError(f"Source folder not found: {source_dir}")

    collection_mapping = {
        "CLIENT TERMS & POLICIES.txt": "Company Policies",
        "sample_organization_monthly_revenue_24_months.pdf": "Finance",
        "Revenue_Report_2020_to_2026.pdf": "Finance",
        "Revenue_Report.xlsx": "Finance",
        "Data_Entry.xlsx": "Finance",
        "Onyx Studio Employee Salary Report.png": "HR",
        "salary_report_sept2026.pdf": "HR",
        "AI RAG Workflow Infographic.png": "Projects",
    }

    files = sorted(source_dir.iterdir())
    ingested_records = []

    for file_path in files:
        if not file_path.is_file():
            continue

        raw_bytes = file_path.read_bytes()
        file_hash = compute_sha256_bytes(raw_bytes)
        safe_name = sanitize_filename(file_path.name)
        ext = validate_file_extension(safe_name)

        col_name = collection_mapping.get(file_path.name, "General")
        col_id = collections.get(col_name) or collections.get("General")

        stored_name = f"v1_{file_hash[:8]}_{safe_name}"
        target_file_path = upload_dir / stored_name
        target_file_path.write_bytes(raw_bytes)

        # Create record in SQLite
        db = SessionLocal()
        try:
            doc_record = Document(
                filename=safe_name,
                original_filename=file_path.name,
                file_type=ext,
                modality=ext.lstrip("."),
                file_path=str(target_file_path),
                file_size=len(raw_bytes),
                content_hash=file_hash,
                version=1,
                collection_id=col_id,
                collection_name=col_name,
                workspace_id=workspace_id,
                owner=admin_username,
                owner_id=admin_id,
                access_level="EMPLOYEE_SHARED",
                approval_status="APPROVED",
                status="Uploaded",
            )
            db.add(doc_record)
            db.commit()
            db.refresh(doc_record)
            doc_id = doc_record.id

            job = IngestionJob(
                document_id=doc_id,
                status="Uploaded",
                stage="Uploaded",
                progress_pct=10,
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
        finally:
            db.close()

        print(f"--> Ingesting '{safe_name}' [{ext}] into collection '{col_name}'...")
        res = process_document_ingestion(
            document_id=doc_id,
            job_id=job_id,
        )

        db = SessionLocal()
        try:
            doc_record = db.query(Document).filter(Document.id == doc_id).first()
            print(f"    Result: {doc_record.status} | Chunks: {doc_record.chunk_count} | Modality: {doc_record.modality} | Pages: {doc_record.page_count}")
            ingested_records.append({
                "filename": doc_record.filename,
                "collection": doc_record.collection_name,
                "status": doc_record.status,
                "chunks": doc_record.chunk_count,
                "modality": doc_record.modality,
            })
        finally:
            db.close()

    print("\n" + "=" * 60)
    print("INGESTION SUMMARY")
    print("=" * 60)
    for r in ingested_records:
        print(f" - {r['filename']:<50} | {r['collection']:<16} | Status: {r['status']} | Chunks: {r['chunks']}")
    
    total_vectors = vector_store.count()
    print("-" * 60)
    print(f"Total Vectors in ChromaDB: {total_vectors}")
    print(f"Total Documents: {len(ingested_records)}")
    print("=" * 60)

if __name__ == "__main__":
    run()
