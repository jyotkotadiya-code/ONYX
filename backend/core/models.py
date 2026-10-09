from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class DocumentChunk:
    """Common internal multimodal chunk representation across all file types."""

    id: str
    document_id: str
    content: str
    modality: str  # "text", "pdf", "scanned_pdf", "docx", "xml", "image", "database", "audio"
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: Optional[list[float]] = None

    def to_chroma_metadata(self) -> dict[str, Any]:
        """Convert metadata to flat primitives (str, int, float, bool) required by ChromaDB."""
        clean: dict[str, Any] = {
            "document_id": str(self.document_id),
            "chunk_id": str(self.id),
            "modality": str(self.modality),
        }
        for k, v in self.metadata.items():
            if v is None:
                continue
            if isinstance(v, (str, int, float, bool)):
                clean[k] = v
            else:
                clean[k] = str(v)
        return clean


@dataclass
class ParsedBlock:
    """Intermediate block produced by file parsers before intelligent chunking."""

    text: str
    modality: str
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    table_name: Optional[str] = None
    row_id: Optional[str] = None
    timestamp_start: Optional[float] = None
    timestamp_end: Optional[float] = None
    confidence: Optional[float] = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)
