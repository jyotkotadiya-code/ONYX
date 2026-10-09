import json
import re
from typing import Any, Optional
from pydantic import ValidationError
from backend.core.logging_config import error_logger
from backend.response.schema import (
    ALLOWED_COMPONENT_TYPES_SET,
    Component,
    Source,
    StructuredResponse,
)

DANGEROUS_HTML_PATTERNS = re.compile(
    r"<\s*(script|iframe|object|embed|style|link|meta|form|input|button)[^>]*>.*?</\s*\1\s*>|<\s*(script|iframe|object|embed|input|img\s+[^>]*onerror)[^>]*>",
    re.IGNORECASE | re.DOTALL,
)


def sanitize_markdown_text(text: str) -> str:
    """Strip dangerous HTML/script tags from markdown text."""
    if not text:
        return ""
    cleaned = DANGEROUS_HTML_PATTERNS.sub("", str(text))
    cleaned = re.sub(r"javascript\s*:", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def validate_and_repair_structured_response(
    raw_payload: dict[str, Any] | str,
    fallback_text: str = "",
    fallback_sources: Optional[list[dict[str, Any]]] = None,
    max_repair_attempts: int = 2,
) -> StructuredResponse:
    """
    Strictly validate a StructuredResponse dict or JSON string against Pydantic schema.
    - Rejects any unknown or unallowed component types (e.g. 'execute_shell').
    - Sanitizes markdown text against dangerous HTML/JS.
    - Performs up to `max_repair_attempts` structural repairs if fields are missing.
    - Falls back cleanly to a valid `text` StructuredResponse if validation still fails.
    """
    sources_models = [
        Source(
            document_id=str(s.get("document_id", "")),
            filename=str(s.get("filename", s.get("document", "source"))),
            page=s.get("page_number") or s.get("page") or 1,
            chunk_id=s.get("chunk_id", ""),
            locator=s.get("locator", f"Page {s.get('page_number', 1)}"),
            modality=s.get("modality", "text"),
            collection=s.get("collection", "General"),
            label=s.get("label", f"📄 {s.get('filename', 'source')}"),
        )
        for s in (fallback_sources or [])
    ]

    parsed_dict: Optional[dict[str, Any]] = None
    if isinstance(raw_payload, dict):
        parsed_dict = raw_payload
    elif isinstance(raw_payload, str):
        # Attempt to extract JSON object from string
        txt = raw_payload.strip()
        if txt.startswith("```"):
            txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt, flags=re.I).strip()
        try:
            parsed_dict = json.loads(txt)
        except Exception:
            match = re.search(r"\{.*\}", txt, re.DOTALL)
            if match:
                try:
                    parsed_dict = json.loads(match.group(0))
                except Exception:
                    parsed_dict = None

    if parsed_dict and isinstance(parsed_dict, dict):
        for attempt in range(max_repair_attempts + 1):
            try:
                # Filter out any unauthorized component types (Security Rule #32)
                raw_components = parsed_dict.get("components", [])
                safe_components: list[dict[str, Any]] = []
                for idx, comp in enumerate(raw_components, start=1):
                    if not isinstance(comp, dict):
                        continue
                    c_type = str(comp.get("type", "")).lower().strip()
                    if c_type not in ALLOWED_COMPONENT_TYPES_SET:
                        error_logger.error(
                            f"Security Validator rejected unauthorized component type: '{c_type}'"
                        )
                        continue
                    c_id = comp.get("id") or f"{c_type}_{idx:02d}"
                    c_data = comp.get("data")
                    if not isinstance(c_data, dict):
                        # Repair flat component structure if needed
                        c_data = {
                            k: v
                            for k, v in comp.items()
                            if k not in {"id", "type", "title"}
                        }
                    if c_type == "text":
                        md = c_data.get("markdown") or c_data.get("content") or fallback_text
                        c_data["markdown"] = sanitize_markdown_text(md)

                    safe_components.append(
                        {
                            "id": str(c_id),
                            "type": c_type,
                            "title": comp.get("title") or c_data.get("title"),
                            "data": c_data,
                        }
                    )

                if not safe_components:
                    raise ValueError("No valid components remained after security filtering.")

                parsed_dict["schema_version"] = "1.0"
                parsed_dict["components"] = safe_components
                if not parsed_dict.get("sources"):
                    parsed_dict["sources"] = [s.model_dump() for s in sources_models]

                if len(safe_components) == 1 and safe_components[0]["type"] == "text":
                    parsed_dict["response_type"] = "text"
                elif len(safe_components) == 1:
                    parsed_dict["response_type"] = "single"
                else:
                    parsed_dict["response_type"] = "composite"

                return StructuredResponse.model_validate(parsed_dict)
            except (ValidationError, ValueError) as e:
                error_logger.error(f"StructuredResponse validation repair attempt {attempt + 1}: {e}")
                parsed_dict["intent"] = "answer"
                parsed_dict["response_type"] = "text"

    # Guaranteed safe fallback to normal text response
    return StructuredResponse(
        schema_version="1.0",
        version=1,
        title="Knowledge Response",
        intent="answer",
        response_type="text",
        components=[
            Component(
                id="text_01",
                type="text",
                title="Answer",
                data={"markdown": sanitize_markdown_text(fallback_text)},
            )
        ],
        sources=sources_models,
        confidence=0.9,
    )
