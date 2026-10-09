import json
import re
import time
from typing import Any, Optional
from rank_bm25 import BM25Okapi
from sqlalchemy.orm import Session
from backend.core.config import settings
from backend.core.logging_config import retrieval_logger
from backend.core.security import wrap_untrusted_document_chunk
from backend.database.sqlite_db import ChunkRecord
from backend.database.vector_store import vector_store
from backend.embeddings.embedding_service import embedding_service


def _tokenize_for_bm25(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_\-\u0900-\u097F\u0A80-\u0AFF]+", text.lower())


def format_citation(meta: dict[str, Any]) -> dict[str, Any]:
    modality = meta.get("modality", "text")
    filename = meta.get("filename") or meta.get("source") or "document"
    doc_id = meta.get("document_id", "")
    page_num = meta.get("page_number", 1)
    section = meta.get("section_title", "")
    chunk_id = meta.get("chunk_id", "")

    if modality == "database" or meta.get("source_type") == "database":
        db_name = meta.get("database") or filename
        table = meta.get("table", "records")
        row_id = meta.get("row_id", str(page_num))
        label = f"🗄 {db_name} — Table: {table}, Row ID: {row_id}"
        locator = f"Table: {table} | Row ID: {row_id}"
    elif modality in {"pdf", "scanned_pdf"}:
        label = f"📄 {filename} — Page {page_num}"
        locator = f"Page {page_num}"
    elif modality in {"docx", "doc"}:
        sec_str = f'Section "{section}"' if section else f"Part {page_num}"
        label = f"📄 {filename} — {sec_str}"
        locator = sec_str
    elif modality == "image":
        label = f"🖼 {filename} — OCR Image"
        locator = f"Image ({meta.get('width', '?')}x{meta.get('height', '?')})"
    elif modality == "audio":
        ts = meta.get("timestamp", f"Segment {page_num}")
        label = f"🎙 {filename} — {ts}"
        locator = ts
    else:
        loc = section if section else f"Chunk {page_num}"
        label = f"📄 {filename} — {loc}"
        locator = loc

    return {
        "document_id": doc_id,
        "chunk_id": chunk_id,
        "filename": filename,
        "modality": modality,
        "page_number": page_num,
        "section_title": section,
        "table": meta.get("table"),
        "row_id": meta.get("row_id"),
        "collection": meta.get("collection", "General"),
        "label": label,
        "locator": locator,
    }


class LocalRetriever:
    """
    Supports:
    1. Normal RAG (Vector Similarity + Hybrid BM25 keyword boost for names/IDs/numbers)
    2. Exact Search Mode (Exact phrase / ID / invoice number / database record matching + BM25)
    Enforces collection-level access permissions on every query.
    """

    def retrieve(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        mode: str = "rag",  # "rag" (semantic + hybrid) or "exact" (exact/keyword search)
        allowed_collections: Optional[list[str]] = None,
        selected_collection: Optional[str] = None,
        authorized_document_ids: Optional[list[str]] = None,
        workplace_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        k = top_k or settings.TOP_K
        clean_query = query.strip()
        if not clean_query:
            return {
                "chunks": [],
                "citations": [],
                "assembled_context": "",
                "embedding_time_ms": 0.0,
                "retrieval_time_ms": 0.0,
            }

        t_start = time.perf_counter()
        resolved_wp_id = workplace_id or workspace_id

        # CRITICAL SECURITY RULE: If authorized_document_ids is provided, filter relational chunks strictly
        # by authorized_document_ids (which are already workplace-scoped) BEFORE any BM25 or vector search.
        chunk_query = db.query(ChunkRecord)
        if resolved_wp_id:
            chunk_query = chunk_query.filter(
                (ChunkRecord.workspace_id == resolved_wp_id) | (ChunkRecord.workspace_id == None)
            )
        if authorized_document_ids is not None:
            if len(authorized_document_ids) == 0:
                return {
                    "chunks": [],
                    "citations": [],
                    "assembled_context": "",
                    "embedding_time_ms": 0.0,
                    "retrieval_time_ms": 0.0,
                }
            chunk_query = chunk_query.filter(ChunkRecord.document_id.in_(authorized_document_ids))

        if selected_collection and selected_collection.upper() != "ALL":
            if allowed_collections is not None and "*" not in allowed_collections:
                if selected_collection not in allowed_collections and authorized_document_ids is None:
                    return {
                        "chunks": [],
                        "citations": [],
                        "assembled_context": "",
                        "embedding_time_ms": 0.0,
                        "retrieval_time_ms": 0.0,
                    }
            chunk_query = chunk_query.filter(ChunkRecord.collection_name == selected_collection)
        elif allowed_collections is not None and "*" not in allowed_collections and authorized_document_ids is None:
            if not allowed_collections:
                return {
                    "chunks": [],
                    "citations": [],
                    "assembled_context": "",
                    "embedding_time_ms": 0.0,
                    "retrieval_time_ms": 0.0,
                }
            chunk_query = chunk_query.filter(ChunkRecord.collection_name.in_(allowed_collections))

        permitted_records = chunk_query.all()
        if not permitted_records:
            return {
                "chunks": [],
                "citations": [],
                "assembled_context": "",
                "embedding_time_ms": 0.0,
                "retrieval_time_ms": 0.0,
            }

        # Step 1: Compute query embedding if mode != "exact"
        t_emb0 = time.perf_counter()
        if mode.lower() == "exact":
            query_vec = None
            emb_time_ms = 0.0
        else:
            query_vec = embedding_service.embed_query(clean_query)
            emb_time_ms = round((time.perf_counter() - t_emb0) * 1000, 2)

        # Step 2: Vector search candidates (filtered by authorized_document_ids at ChromaDB level)
        vector_results_map: dict[str, dict[str, Any]] = {}
        if query_vec is not None:
            vec_hits = vector_store.query_similar(
                query_embedding=query_vec,
                top_k=max(k * 3, 15),
                allowed_collections=allowed_collections,
                selected_collection=selected_collection,
                authorized_document_ids=authorized_document_ids,
            )
            for hit in vec_hits:
                vector_results_map[hit["chunk_id"]] = hit

        # Step 3: Exact substring & BM25 keyword scoring over permitted chunks
        query_lower = clean_query.lower()
        query_tokens = _tokenize_for_bm25(clean_query)

        corpus_tokens = [_tokenize_for_bm25(rec.content) for rec in permitted_records]
        bm25_scores = [0.0] * len(permitted_records)
        if query_tokens and any(corpus_tokens):
            try:
                bm25 = BM25Okapi(corpus_tokens)
                raw_scores = bm25.get_scores(query_tokens)
                max_b = float(max(raw_scores)) if len(raw_scores) > 0 else 0.0
                if max_b > 0:
                    bm25_scores = [float(s) / max_b for s in raw_scores]
            except Exception:
                pass

        combined_candidates: list[dict[str, Any]] = []
        for idx, rec in enumerate(permitted_records):
            meta = json.loads(rec.metadata_json or "{}")
            vec_hit = vector_results_map.get(rec.id)
            vec_sim = float(vec_hit["similarity"]) if vec_hit else 0.0
            bm25_norm = bm25_scores[idx]

            content_lower = rec.content.lower()
            exact_phrase_match = query_lower in content_lower
            token_overlap = (
                sum(1 for t in set(query_tokens) if len(t) > 1 and t in content_lower)
                / max(1, len(set(query_tokens)))
                if query_tokens
                else 0.0
            )

            if mode.lower() == "exact":
                if not exact_phrase_match and token_overlap == 0 and bm25_norm == 0:
                    continue
                final_score = (0.65 if exact_phrase_match else 0.0) + 0.25 * bm25_norm + 0.10 * token_overlap
                final_score = min(1.0, round(final_score, 4))
            else:
                # Hybrid semantic + lexical score
                exact_boost = 0.18 if exact_phrase_match else 0.0
                final_score = round(
                    min(1.0, 0.72 * vec_sim + 0.20 * bm25_norm + 0.08 * token_overlap + exact_boost),
                    4,
                )

            if final_score > 0.01:
                citation = format_citation(meta)
                combined_candidates.append(
                    {
                        "chunk_id": rec.id,
                        "document_id": rec.document_id,
                        "content": rec.content,
                        "modality": rec.modality,
                        "page_number": rec.page_number or 1,
                        "section_title": rec.section_title or "",
                        "collection": rec.collection_name,
                        "similarity": final_score,
                        "vector_similarity": round(vec_sim, 4),
                        "keyword_score": round(bm25_norm, 4),
                        "exact_match": exact_phrase_match,
                        "metadata": meta,
                        "citation": citation,
                    }
                )

        combined_candidates.sort(key=lambda x: x["similarity"], reverse=True)
        top_chunks = combined_candidates[:k]

        # Deduplicate citations while preserving order
        seen_cit_keys = set()
        citations = []
        for ch in top_chunks:
            cit = ch["citation"]
            key = f"{cit['filename']}::{cit['locator']}"
            if key not in seen_cit_keys:
                seen_cit_keys.add(key)
                citations.append(cit)

        # Assemble prompt-injection-safe context for the LLM
        wrapped_excerpts = []
        for idx, ch in enumerate(top_chunks, start=1):
            cit = ch["citation"]
            wrapped_excerpts.append(
                wrap_untrusted_document_chunk(
                    content=ch["content"],
                    filename=cit["filename"],
                    locator=cit["locator"],
                    chunk_index=idx,
                )
            )
        assembled_context = "\n\n".join(wrapped_excerpts)
        total_ret_ms = round((time.perf_counter() - t_start) * 1000, 2)

        retrieval_logger.info(
            f"Retrieved {len(top_chunks)} chunks for query='{clean_query[:60]}' (mode={mode}, emb={emb_time_ms}ms, total={total_ret_ms}ms)"
        )
        return {
            "chunks": top_chunks,
            "citations": citations,
            "assembled_context": assembled_context,
            "embedding_time_ms": emb_time_ms,
            "retrieval_time_ms": total_ret_ms,
        }


retriever = LocalRetriever()
