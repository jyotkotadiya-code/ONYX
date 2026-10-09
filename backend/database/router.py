import re
from typing import Literal, Optional
from sqlalchemy.orm import Session
from backend.database.sqlite_db import Document


RouteType = Literal["documents", "database", "hybrid", "workspace_followup"]

FOLLOWUP_PATTERNS = [
    re.compile(r"\b(make|turn|convert|change|switch|show)\s+(this|it|component_\d+|chart_\d+|table_\d+)\s+(into|to|as)\b", re.I),
    re.compile(r"\b(change|switch)\s+the\s+.*?\bchart\s+to\b", re.I),
    re.compile(r"\bonly\s+show\s+(the\s+)?top\s+\d+\b", re.I),
    re.compile(r"\badd\s+percentage\s+change\b", re.I),
    re.compile(r"\bremove\s+the\s+(chart|table|stat|kpi|timeline|comparison)\b", re.I),
    re.compile(r"\bexport\s+(this\s+)?as\s+csv\b", re.I),
]


def route_user_query(
    db: Session,
    question: str,
    has_active_workspace: bool = False,
) -> RouteType:
    """
    Route a user question to:
    - 'workspace_followup': if modifying an existing structured workspace component
    - 'database': if specifically querying structured database records
    - 'hybrid': if comparing/combining database records with document knowledge
    - 'documents': standard document RAG
    """
    q_clean = question.strip()
    if has_active_workspace:
        for pat in FOLLOWUP_PATTERNS:
            if pat.search(q_clean):
                return "workspace_followup"

    q_lower = q_clean.lower()
    has_db_docs = db.query(Document).filter(Document.modality == "database", Document.status == "Ready").count() > 0

    db_keywords = {"database", "table", "employee", "employees", "row", "sql", "emp_id", "department", "departments"}
    doc_keywords = {"report", "policy", "plan", "roadmap", "pdf", "document", "strategy", "notes", "Marks", "course"}

    mentions_db = has_db_docs and any(k in q_lower for k in db_keywords)
    mentions_doc = any(k.lower() in q_lower for k in doc_keywords)

    if mentions_db and mentions_doc:
        return "hybrid"
    if mentions_db and ("show all" in q_lower or "list" in q_lower or "employee" in q_lower):
        return "database"
    return "documents"
