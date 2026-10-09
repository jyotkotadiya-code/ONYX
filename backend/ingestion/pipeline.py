import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from sqlalchemy.orm import Session
from backend.core.config import settings
from backend.core.logging_config import error_logger, ingestion_logger
from backend.core.models import ParsedBlock
from backend.database.sqlite_db import (
    ChunkRecord,
    Document,
    DocumentVersion,
    IngestionJob,
    SessionLocal,
)
from backend.database.vector_store import vector_store
from backend.ingestion.chunker import chunk_parsed_blocks
from backend.ingestion.database_parser import parse_database
from backend.ingestion.doc_parser import parse_text_or_doc
from backend.ingestion.embedder import embed_document_chunks
from backend.ingestion.image_parser import parse_image
from backend.ingestion.pdf_parser import parse_pdf


def _update_status(
    db: Session,
    doc: Document,
    job: Optional[IngestionJob],
    status_name: str,
    progress_pct: int,
    error_msg: Optional[str] = None,
    suggested_action: Optional[str] = None,
) -> None:
    doc.status = status_name
    doc.error_message = error_msg
    doc.suggested_action = suggested_action
    doc.updated_at = datetime.now(timezone.utc)
    if job:
        job.status = status_name
        job.stage = status_name
        job.progress_pct = progress_pct
        job.error_message = error_msg
        job.suggested_action = suggested_action
        if status_name in {"Ready", "Failed"}:
            job.completed_at = datetime.now(timezone.utc)
    db.commit()


def _route_parser(
    file_path: Path,
    ext: str,
    selected_tables: Optional[list[str]] = None,
    progress_cb=None,
) -> tuple[list[ParsedBlock], dict[str, Any], str]:
    ext = ext.lower()
    if ext == ".pdf":
        blocks, meta = parse_pdf(file_path, progress_callback=progress_cb)
        modality = "scanned_pdf" if meta.get("is_scanned") else "pdf"
        return blocks, meta, modality
    if ext in {".docx", ".doc", ".txt", ".md", ".csv", ".json", ".xml"}:
        blocks, meta = parse_text_or_doc(file_path)
        modality = "docx" if ext == ".docx" else ("doc" if ext == ".doc" else "text")
        return blocks, meta, modality
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}:
        blocks, meta = parse_image(file_path, progress_callback=progress_cb)
        return blocks, meta, "image"
    if ext in {".db", ".sqlite", ".sqlite3"}:
        blocks, meta = parse_database(str(file_path), selected_tables=selected_tables)
        return blocks, meta, "database"
    raise ValueError(f"Unsupported file extension '{ext}'. Only PDF, OCR Images (PNG/JPG), Databases, and Text documents are supported.")


def process_document_ingestion(
    document_id: str,
    job_id: Optional[str] = None,
    selected_tables: Optional[list[str]] = None,
    connection_url: Optional[str] = None,
) -> dict[str, Any]:
    """
    Execute the full modular ingestion pipeline for a document:
    Extracting -> OCR -> Chunking -> Embedding -> Indexing -> Ready (or Failed).
    Can be invoked synchronously (e.g. in tests or small files) or via FastAPI BackgroundTasks.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found in metadata database.")

        job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first() if job_id else None

        def progress_cb(stage: str, pct: int):
            _update_status(db, doc, job, stage, pct)

        ingestion_logger.info(
            f"Starting ingestion for document '{doc.filename}' (id={doc.id}, v={doc.version}, type={doc.file_type})"
        )
        _update_status(db, doc, job, "Extracting", 20)

        if connection_url:
            blocks, doc_meta, modality = parse_database(
                connection_url, selected_tables=selected_tables
            )
            modality = "database"
        else:
            file_path = Path(doc.file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"Source file missing on disk: {file_path}")
            blocks, doc_meta, modality = _route_parser(
                file_path, doc.file_type, selected_tables=selected_tables, progress_cb=progress_cb
            )

        if not blocks:
            raise ValueError(
                f"No extractable text or structured records found in '{doc.filename}'."
            )

        doc.modality = modality
        doc.page_count = int(doc_meta.get("page_count", 1) or 1)
        doc.metadata_json = json.dumps(doc_meta)

        # Stage: Chunking
        _update_status(db, doc, job, "Chunking", 55)
        chunks = chunk_parsed_blocks(
            blocks=blocks,
            document_id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            collection=doc.collection_name,
            owner=doc.owner,
            content_hash=doc.content_hash,
            version=doc.version,
            access_level=doc.access_level or "EMPLOYEE_SHARED",
            department_id=doc.department_id or "",
            workplace_id=doc.workspace_id or "",
            collection_id=doc.collection_id or "",
        )
        if not chunks:
            raise ValueError(f"Chunking produced 0 chunks for '{doc.filename}'.")

        # Stage: Embedding
        _update_status(db, doc, job, "Embedding", 75)
        embed_document_chunks(chunks)

        # Stage: Indexing (Vector DB + Relational Metadata DB)
        _update_status(db, doc, job, "Indexing", 90)
        # Clear any old vectors for this document_id before indexing new version
        vector_store.delete_by_document_id(doc.id)
        vector_store.upsert_chunks(chunks)

        # Replace relational chunk records
        db.query(ChunkRecord).filter(ChunkRecord.document_id == doc.id).delete()
        for idx, ch in enumerate(chunks, start=1):
            db.add(
                ChunkRecord(
                    id=ch.id,
                    document_id=doc.id,
                    workspace_id=doc.workspace_id,
                    version=doc.version,
                    chunk_index=idx,
                    content=ch.content,
                    modality=ch.modality,
                    page_number=ch.metadata.get("page_number", 1),
                    section_title=ch.metadata.get("section_title", ""),
                    collection_name=doc.collection_name,
                    content_hash=doc.content_hash,
                    metadata_json=json.dumps(ch.to_chroma_metadata()),
                )
            )

        doc.chunk_count = len(chunks)

        # Save/update version history entry
        ver_record = (
            db.query(DocumentVersion)
            .filter(
                DocumentVersion.document_id == doc.id,
                DocumentVersion.version == doc.version,
            )
            .first()
        )
        if ver_record:
            ver_record.chunk_count = len(chunks)
            ver_record.status = "Ready"
        else:
            db.add(
                DocumentVersion(
                    document_id=doc.id,
                    version=doc.version,
                    content_hash=doc.content_hash,
                    file_path=doc.file_path,
                    file_size=doc.file_size,
                    chunk_count=len(chunks),
                    status="Ready",
                )
            )

        # Write processed artifact JSON for inspection
        processed_dir = settings.resolve_path(settings.PROCESSED_DIR)
        processed_file = processed_dir / f"{doc.id}_v{doc.version}.json"
        processed_file.write_text(
            json.dumps(
                {
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "version": doc.version,
                    "modality": doc.modality,
                    "chunk_count": len(chunks),
                    "metadata": doc_meta,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        _update_status(db, doc, job, "Ready", 100)
        ingestion_logger.info(
            f"Completed ingestion for '{doc.filename}' (v{doc.version}): {len(chunks)} chunks indexed."
        )
        return {
            "status": "Ready",
            "document_id": doc.id,
            "filename": doc.filename,
            "version": doc.version,
            "chunk_count": len(chunks),
            "modality": doc.modality,
        }

    except Exception as e:
        err_str = str(e)
        error_logger.error(f"Ingestion failed for document_id={document_id}: {err_str}")
        suggested = "Verify file integrity and ensure required local parsers/OCR are enabled."
        if "OCR" in err_str or "Tesseract" in err_str:
            suggested = "Install Tesseract or verify RapidOCR ONNX runtime is installed."
        elif "Whisper" in err_str or "AUDIO_ENABLED" in err_str:
            suggested = "Set AUDIO_ENABLED=true in .env and install faster-whisper (`pip install faster-whisper`)."
        elif "XML" in err_str:
            suggested = "Check that the XML file is well-formed and has valid closing tags."

        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first() if job_id else None
            if doc:
                _update_status(db, doc, job, "Failed", 100, error_msg=err_str, suggested_action=suggested)
        except Exception:
            pass
        return {
            "status": "Failed",
            "document_id": document_id,
            "error": err_str,
            "suggested_action": suggested,
        }
    finally:
        db.close()
