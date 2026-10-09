import re
from pathlib import Path
from typing import Any, Optional
from sqlalchemy import create_engine, inspect, text
from backend.core.security import sanitize_identifier

FORBIDDEN_SQL_KEYWORDS = re.compile(
    r"\b(DROP|DELETE|UPDATE|INSERT|ALTER|CREATE|TRUNCATE|REPLACE|GRANT|REVOKE|ATTACH|DETACH|PRAGMA)\b",
    re.IGNORECASE,
)


class SQLValidationError(ValueError):
    """Raised when a proposed SQL query violates read-only or schema allowlist rules."""


def validate_readonly_sql(
    sql_query: str,
    allowed_tables: Optional[list[str]] = None,
) -> str:
    """
    Validate that a SQL query is strictly a single-statement read-only SELECT query
    and references only allowed tables.
    Blocks DROP, DELETE, UPDATE, INSERT, ALTER, CREATE, TRUNCATE, and multi-statement ';'.
    """
    if not sql_query or not sql_query.strip():
        raise SQLValidationError("SQL query cannot be empty.")

    cleaned = sql_query.strip().rstrip(";").strip()
    if ";" in cleaned:
        raise SQLValidationError("Multi-statement SQL queries are blocked by security policy.")

    if not re.match(r"^(SELECT|WITH)\b", cleaned, re.IGNORECASE):
        raise SQLValidationError("Only read-only SELECT queries are permitted.")

    match = FORBIDDEN_SQL_KEYWORDS.search(cleaned)
    if match:
        raise SQLValidationError(
            f"Forbidden SQL keyword detected: '{match.group(1).upper()}'. Only read-only SELECT queries are allowed."
        )

    if allowed_tables is not None:
        allowed_lower = {t.lower() for t in allowed_tables}
        from_tables = re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", cleaned, re.IGNORECASE)
        for tbl in from_tables:
            if tbl.lower() not in allowed_lower:
                raise SQLValidationError(f"Table '{tbl}' is not in the allowed schema tables.")

    if not re.search(r"\bLIMIT\s+\d+\b", cleaned, re.IGNORECASE):
        cleaned = f"{cleaned} LIMIT 200"

    return cleaned
