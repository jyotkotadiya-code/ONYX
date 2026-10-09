from typing import Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
from backend.core.config import settings
from backend.core.logging_config import app_logger, error_logger
from backend.core.models import DocumentChunk


class LocalVectorStore:
    """
    Persistent local ChromaDB vector store (`./data/vector_db`).
    Zero cloud dependencies; anonymized telemetry disabled.
    """

    COLLECTION_NAME = "onyx_multimodal_knowledge"

    def __init__(self) -> None:
        self.db_path = str(settings.resolve_path(settings.VECTOR_DB_PATH))
        self._client: Optional[chromadb.ClientAPI] = None
        self._collection = None

    def _get_collection(self):
        if self._collection is not None:
            return self._collection
        self._client = chromadb.PersistentClient(
            path=self.db_path,
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
        )
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        return self._collection

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> int:
        if not chunks:
            return 0
        col = self._get_collection()
        ids = [c.id for c in chunks]
        documents = [c.content for c in chunks]
        metadatas = [c.to_chroma_metadata() for c in chunks]
        embeddings = [c.embedding for c in chunks if c.embedding is not None]

        if len(embeddings) != len(chunks):
            raise ValueError("All DocumentChunks must have computed embeddings before vector DB upsert.")

        col.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        app_logger.info(f"Upserted {len(chunks)} chunks into local ChromaDB.")
        return len(chunks)

    def delete_by_document_id(self, document_id: str) -> None:
        col = self._get_collection()
        try:
            col.delete(where={"document_id": str(document_id)})
            app_logger.info(f"Deleted vectors for document_id={document_id} from ChromaDB.")
        except Exception as e:
            error_logger.error(f"Error deleting vectors for document {document_id}: {e}")

    def delete_by_collection_name(self, collection_name: str) -> None:
        col = self._get_collection()
        try:
            col.delete(where={"collection": str(collection_name)})
            app_logger.info(f"Deleted vectors for collection={collection_name} from ChromaDB.")
        except Exception as e:
            error_logger.error(f"Error deleting vectors for collection {collection_name}: {e}")

    def update_document_access_metadata(
        self,
        document_id: str,
        access_level: str,
        department_id: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> None:
        """
        Update authorization metadata on existing ChromaDB vectors immediately when an admin
        changes a document's access policy, without needing to re-compute embeddings.
        """
        col = self._get_collection()
        try:
            existing = col.get(
                where={"document_id": str(document_id)},
                include=["metadatas"],
            )
            ids = existing.get("ids", [])
            metas = existing.get("metadatas", [])
            if not ids or not metas:
                return
            updated_metas = []
            for m in metas:
                new_m = dict(m or {})
                new_m["access_level"] = str(access_level)
                new_m["department_id"] = str(department_id or "")
                if collection_name:
                    new_m["collection"] = str(collection_name)
                updated_metas.append(new_m)
            col.update(ids=ids, metadatas=updated_metas)
            app_logger.info(
                f"Updated vector access metadata for document_id={document_id} -> access_level={access_level}"
            )
        except Exception as e:
            error_logger.error(f"Failed updating vector access metadata for {document_id}: {e}")

    def query_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        allowed_collections: Optional[list[str]] = None,
        selected_collection: Optional[str] = None,
        authorized_document_ids: Optional[list[str]] = None,
    ) -> list[dict[str, Any]]:
        col = self._get_collection()
        total_count = col.count()
        if total_count == 0:
            return []

        # CRITICAL SECURITY RULE: If authorized_document_ids is explicitly provided (e.g. for an employee),
        # filter strictly at the vector database level BEFORE similarity retrieval.
        if authorized_document_ids is not None:
            if len(authorized_document_ids) == 0:
                return []
            if len(authorized_document_ids) == 1:
                doc_filter: dict[str, Any] = {"document_id": str(authorized_document_ids[0])}
            else:
                doc_filter = {"document_id": {"$in": [str(did) for did in authorized_document_ids]}}

            if selected_collection and selected_collection.upper() != "ALL":
                where_filter: Optional[dict[str, Any]] = {
                    "$and": [doc_filter, {"collection": selected_collection}]
                }
            else:
                where_filter = doc_filter
        else:
            where_filter = None
            if selected_collection and selected_collection.upper() != "ALL":
                if allowed_collections is not None and "*" not in allowed_collections:
                    if selected_collection not in allowed_collections:
                        return []
                where_filter = {"collection": selected_collection}
            elif allowed_collections is not None and "*" not in allowed_collections:
                if not allowed_collections:
                    return []
                if len(allowed_collections) == 1:
                    where_filter = {"collection": allowed_collections[0]}
                else:
                    where_filter = {"collection": {"$in": allowed_collections}}

        n_results = min(max(top_k, 1), total_count)
        try:
            res = col.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            error_logger.error(f"ChromaDB query failed: {e}")
            return []

        ids = res.get("ids", [[]])[0]
        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        results = []
        allowed_doc_set = set(str(x) for x in authorized_document_ids) if authorized_document_ids is not None else None
        for cid, doc, meta, dist in zip(ids, docs, metas, dists):
            meta_dict = meta or {}
            if allowed_doc_set is not None and str(meta_dict.get("document_id", "")) not in allowed_doc_set:
                continue
            # Cosine distance in Chroma is (1 - cosine_similarity)
            similarity = max(0.0, min(1.0, 1.0 - float(dist)))
            results.append(
                {
                    "chunk_id": cid,
                    "content": doc,
                    "metadata": meta_dict,
                    "distance": float(dist),
                    "similarity": round(similarity, 4),
                }
            )
        return results

    def count(self) -> int:
        try:
            return self._get_collection().count()
        except Exception:
            return 0

    def get_status(self) -> dict[str, Any]:
        try:
            cnt = self.count()
            return {
                "status": "online",
                "engine": "ChromaDB (Persistent Local)",
                "path": self.db_path,
                "vector_count": cnt,
            }
        except Exception as e:
            return {
                "status": "offline",
                "engine": "ChromaDB",
                "path": self.db_path,
                "error": str(e),
            }


    def reset(self) -> None:
        try:
            if self._client is not None:
                try:
                    self._client.delete_collection(self.COLLECTION_NAME)
                except Exception:
                    pass
            self._collection = None
            self._get_collection()
            app_logger.info("Reset local ChromaDB vector store.")
        except Exception as e:
            error_logger.error(f"Error resetting vector store: {e}")


vector_store = LocalVectorStore()
