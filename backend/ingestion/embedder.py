from backend.core.models import DocumentChunk
from backend.embeddings.embedding_service import embedding_service


def embed_document_chunks(chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    """Compute local embeddings for a list of DocumentChunk objects."""
    if not chunks:
        return []
    texts = [c.content for c in chunks]
    vectors = embedding_service.embed_documents(texts)
    for chunk, vec in zip(chunks, vectors):
        chunk.embedding = vec
    return chunks
