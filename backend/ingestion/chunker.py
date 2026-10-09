import re
from datetime import datetime, timezone
from typing import Any
from backend.core.config import settings
from backend.core.models import DocumentChunk, ParsedBlock


def _split_into_sentences(paragraph: str) -> list[str]:
    # Split on sentence-ending punctuation while keeping delimiters attached
    parts = re.split(r"(?<=[.!?।])\s+", paragraph.strip())
    return [p.strip() for p in parts if p.strip()]


def chunk_parsed_blocks(
    blocks: list[ParsedBlock],
    document_id: str,
    filename: str,
    file_type: str,
    collection: str,
    owner: str,
    content_hash: str,
    version: int = 1,
    access_level: str = "EMPLOYEE_SHARED",
    department_id: str = "",
    workplace_id: str = "",
    collection_id: str = "",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    """
    Intelligent hierarchy-aware chunker:
    Document Structure -> Heading -> Paragraph -> Sentence -> Token/Character Limits.
    Database rows and compact XML/Table blocks stay intact when within limits.
    Includes workplace_id, collection_id, department_id, and access_level on every vector chunk.
    """
    target_size = chunk_size or settings.CHUNK_SIZE
    overlap_size = chunk_overlap or settings.CHUNK_OVERLAP
    created_iso = datetime.now(timezone.utc).isoformat()

    chunks: list[DocumentChunk] = []
    chunk_counter = 0

    for block in blocks:
        raw_text = (block.text or "").strip()
        if not raw_text:
            continue

        # Database rows or small structured blocks fit inside a single chunk directly
        if block.modality == "database" or len(raw_text) <= target_size:
            chunk_counter += 1
            cid = f"{document_id}_v{version}_c{chunk_counter}"
            meta: dict[str, Any] = {
                "workplace_id": workplace_id or "",
                "workspace_id": workplace_id or "",
                "document_id": document_id,
                "collection_id": collection_id or "",
                "filename": filename,
                "file_type": file_type,
                "page_number": block.page_number or 1,
                "section_title": block.section_title or "",
                "chunk_id": cid,
                "chunk_index": chunk_counter,
                "source": filename,
                "created_at": created_iso,
                "collection": collection,
                "owner": owner,
                "content_hash": content_hash,
                "version": version,
                "access_level": access_level,
                "department_id": department_id or "",
            }
            if block.table_name:
                meta["table"] = block.table_name
            if block.row_id:
                meta["row_id"] = block.row_id
            if block.confidence is not None:
                meta["confidence"] = block.confidence
            meta.update(block.extra_metadata)

            chunks.append(
                DocumentChunk(
                    id=cid,
                    document_id=document_id,
                    content=raw_text,
                    modality=block.modality,
                    metadata=meta,
                )
            )
            continue

        # Split larger blocks by paragraph first, then by sentence
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", raw_text) if p.strip()]
        units: list[str] = []
        for para in paragraphs:
            if len(para) <= target_size:
                units.append(para)
            else:
                sentences = _split_into_sentences(para)
                for s in sentences:
                    if len(s) <= target_size:
                        units.append(s)
                    else:
                        step = max(100, target_size - overlap_size)
                        for i in range(0, len(s), step):
                            units.append(s[i : i + target_size])

        current_parts: list[str] = []
        current_len = 0

        for unit in units:
            unit_len = len(unit)
            if current_parts and (current_len + unit_len + 2 > target_size):
                chunk_counter += 1
                cid = f"{document_id}_v{version}_c{chunk_counter}"
                chunk_text = "\n\n".join(current_parts).strip()
                if block.section_title and not chunk_text.startswith(block.section_title):
                    chunk_text = f"[{block.section_title}]\n{chunk_text}"

                meta = {
                    "workplace_id": workplace_id or "",
                    "workspace_id": workplace_id or "",
                    "document_id": document_id,
                    "collection_id": collection_id or "",
                    "filename": filename,
                    "file_type": file_type,
                    "page_number": block.page_number or 1,
                    "section_title": block.section_title or "",
                    "chunk_id": cid,
                    "chunk_index": chunk_counter,
                    "source": filename,
                    "created_at": created_iso,
                    "collection": collection,
                    "owner": owner,
                    "content_hash": content_hash,
                    "version": version,
                    "access_level": access_level,
                    "department_id": department_id or "",
                }
                meta.update(block.extra_metadata)
                chunks.append(
                    DocumentChunk(
                        id=cid,
                        document_id=document_id,
                        content=chunk_text,
                        modality=block.modality,
                        metadata=meta,
                    )
                )

                overlap_parts: list[str] = []
                overlap_acc = 0
                for prev_u in reversed(current_parts):
                    if overlap_acc + len(prev_u) <= overlap_size:
                        overlap_parts.insert(0, prev_u)
                        overlap_acc += len(prev_u)
                    else:
                        break
                current_parts = overlap_parts + [unit]
                current_len = sum(len(x) for x in current_parts)
            else:
                current_parts.append(unit)
                current_len += unit_len + 2

        if current_parts:
            chunk_counter += 1
            cid = f"{document_id}_v{version}_c{chunk_counter}"
            chunk_text = "\n\n".join(current_parts).strip()
            if block.section_title and not chunk_text.startswith(block.section_title):
                chunk_text = f"[{block.section_title}]\n{chunk_text}"

            meta = {
                "workplace_id": workplace_id or "",
                "workspace_id": workplace_id or "",
                "document_id": document_id,
                "collection_id": collection_id or "",
                "filename": filename,
                "file_type": file_type,
                "page_number": block.page_number or 1,
                "section_title": block.section_title or "",
                "chunk_id": cid,
                "chunk_index": chunk_counter,
                "source": filename,
                "created_at": created_iso,
                "collection": collection,
                "owner": owner,
                "content_hash": content_hash,
                "version": version,
                "access_level": access_level,
                "department_id": department_id or "",
            }
            meta.update(block.extra_metadata)
            chunks.append(
                DocumentChunk(
                    id=cid,
                    document_id=document_id,
                    content=chunk_text,
                    modality=block.modality,
                    metadata=meta,
                )
            )

    return chunks
