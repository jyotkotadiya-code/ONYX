import re
from pathlib import Path
from typing import Any
from defusedxml import ElementTree as DefusedET
from backend.core.logging_config import ingestion_logger
from backend.core.models import ParsedBlock


def _humanize_tag(tag: str) -> str:
    # Strip XML namespace if present
    if "}" in tag:
        tag = tag.split("}", 1)[1]
    tag = re.sub(r"[_-]+", " ", tag)
    tag = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", tag)
    return tag.strip().title()


def _serialize_element(elem, depth: int = 0) -> list[str]:
    lines: list[str] = []
    tag_label = _humanize_tag(elem.tag)
    attrs = [f"{_humanize_tag(k)}: {v}" for k, v in (elem.attrib or {}).items()]
    text = (elem.text or "").strip()
    children = list(elem)

    if not children:
        # Leaf node
        val_parts = []
        if text:
            val_parts.append(text)
        if attrs:
            val_parts.append(f"({', '.join(attrs)})")
        if val_parts:
            lines.append(f"{tag_label}: {' '.join(val_parts)}")
    else:
        header = tag_label
        if attrs:
            header += f" ({', '.join(attrs)})"
        lines.append(header)
        if text:
            lines.append(f"Description: {text}")
        for child in children:
            lines.extend(_serialize_element(child, depth + 1))
    return lines


def parse_xml(file_path: Path) -> tuple[list[ParsedBlock], dict[str, Any]]:
    """
    Validate XML safely using defusedxml (blocks XXE / billion laughs attacks),
    preserve hierarchy, and convert tags into semantically searchable structured blocks.
    """
    raw_content = file_path.read_text(encoding="utf-8", errors="replace")
    try:
        root = DefusedET.fromstring(raw_content)
    except Exception as e:
        raise ValueError(f"Invalid or malformed XML file '{file_path.name}': {e}")

    root_label = _humanize_tag(root.tag)
    blocks: list[ParsedBlock] = []
    children = list(root)

    if children:
        for idx, child in enumerate(children, start=1):
            child_label = _humanize_tag(child.tag)
            serialized_lines = _serialize_element(child)
            block_text = "\n".join(serialized_lines).strip()
            if block_text:
                blocks.append(
                    ParsedBlock(
                        text=block_text,
                        modality="xml",
                        page_number=idx,
                        section_title=f"{root_label} > {child_label} #{idx}",
                        extra_metadata={"root_tag": root_label, "record_tag": child_label},
                    )
                )
    else:
        serialized_lines = _serialize_element(root)
        block_text = "\n".join(serialized_lines).strip()
        if block_text:
            blocks.append(
                ParsedBlock(
                    text=block_text,
                    modality="xml",
                    page_number=1,
                    section_title=root_label,
                    extra_metadata={"root_tag": root_label},
                )
            )

    meta = {
        "root_tag": root_label,
        "record_count": len(blocks),
        "page_count": max(1, len(blocks)),
    }
    ingestion_logger.info(
        f"Parsed XML '{file_path.name}' (root={root_label}) into {len(blocks)} structured semantic blocks."
    )
    return blocks, meta
