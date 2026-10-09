from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

AllowedComponentType = Literal[
    "text",
    "table",
    "chart",
    "stat",
    "list",
    "timeline",
    "comparison",
    "code",
    "source",
]

AllowedResponseType = Literal[
    "text",
    "single",
    "composite",
]

AllowedIntentType = Literal[
    "answer",
    "summarize",
    "compare",
    "analyze",
    "calculate",
    "visualize",
    "list",
    "lookup",
    "explain",
]

ALLOWED_COMPONENT_TYPES_SET = {
    "text",
    "table",
    "chart",
    "stat",
    "list",
    "timeline",
    "comparison",
    "code",
    "source",
}


class Source(BaseModel):
    document_id: str = ""
    filename: str
    page: Optional[int] = None
    chunk_id: Optional[str] = None
    locator: Optional[str] = None
    modality: Optional[str] = "text"
    collection: Optional[str] = "General"
    label: Optional[str] = None


class Component(BaseModel):
    id: str = Field(..., description="Unique component identifier, e.g. component_01, chart_01, table_01")
    type: AllowedComponentType
    title: Optional[str] = None
    data: dict[str, Any] = Field(default_factory=dict)


class ResponsePlan(BaseModel):
    intent: AllowedIntentType = "answer"
    route: Literal["documents", "database", "hybrid", "workspace_followup"] = "documents"
    visualization: Optional[Literal["none", "line", "bar", "pie", "area", "scatter", "table", "stat", "composite"]] = "none"
    data_required: bool = False
    calculations_run: list[str] = Field(default_factory=list)


class StructuredResponse(BaseModel):
    schema_version: str = "1.0"
    version: int = 1
    title: str = "Knowledge Workspace"
    intent: AllowedIntentType = "answer"
    response_type: AllowedResponseType = "text"
    components: list[Component] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    confidence: Optional[float] = 0.95
    plan: Optional[ResponsePlan] = None
    history_versions: list[dict[str, Any]] = Field(default_factory=list)
