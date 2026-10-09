import re
from pathlib import Path
from typing import Any, Optional
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from backend.core.config import settings
from backend.core.security import sanitize_identifier
from backend.database.executor import execute_readonly_query
from backend.database.sqlite_db import Document


def is_internal_system_database(connection_or_path: str) -> bool:
    """Prevent any user or query planner from inspecting or querying the internal RBAC/Auth metadata database."""
    try:
        internal_db = str(settings.resolve_path(settings.SQLITE_DB_PATH)).lower().replace("\\", "/")
        candidate = str(connection_or_path).lower().replace("sqlite:///", "").replace("\\", "/")
        if "app.db" in candidate or internal_db in candidate:
            return True
        p = Path(connection_or_path.replace("sqlite:///", ""))
        if p.exists() and str(p.resolve()).lower().replace("\\", "/") == internal_db:
            return True
    except Exception:
        pass
    return False


def plan_and_execute_database_query(
    db: Session,
    question: str,
    allowed_collections: Optional[list[str]] = None,
    selected_collection: Optional[str] = None,
    authorized_document_ids: Optional[list[str]] = None,
) -> Optional[dict[str, Any]]:
    """
    Inspect indexed database documents in the user's authorized document scope,
    plan a read-only SELECT query when a question matches a database table/columns,
    and return structured rows + source metadata.
    """
    q = db.query(Document).filter(Document.modality == "database", Document.status == "Ready")
    if authorized_document_ids is not None:
        if len(authorized_document_ids) == 0:
            return None
        q = q.filter(Document.id.in_(authorized_document_ids))
    if selected_collection and selected_collection.upper() != "ALL":
        q = q.filter(Document.collection_name == selected_collection)
    elif allowed_collections is not None and "*" not in allowed_collections and authorized_document_ids is None:
        q = q.filter(Document.collection_name.in_(allowed_collections))

    db_docs = q.all()
    if not db_docs:
        return None

    q_lower = question.lower()

    for doc in db_docs:
        file_path = doc.file_path
        if is_internal_system_database(file_path):
            continue
        if "://" not in file_path and not Path(file_path).exists():
            continue
        conn_url = f"sqlite:///{Path(file_path).resolve()}" if "://" not in file_path else file_path

        try:
            eng = create_engine(conn_url)
            insp = inspect(eng)
            tables = insp.get_table_names()

            for tbl in tables:
                safe_tbl = sanitize_identifier(tbl)
                cols_info = insp.get_columns(tbl)
                col_names = [c["name"] for c in cols_info]

                # Check if question references the table name (or singular form) or any column name
                tbl_singular = tbl.lower().rstrip("s")
                matches_table = (tbl.lower() in q_lower) or (len(tbl_singular) >= 3 and tbl_singular in q_lower)
                matching_cols = [c for c in col_names if c.lower().replace("_", " ") in q_lower or c.lower() in q_lower]

                if matches_table or len(matching_cols) >= 1:
                    sql = f'SELECT * FROM "{safe_tbl}" LIMIT 200'
                    exec_res = execute_readonly_query(file_path, sql)
                    if exec_res["rows"]:
                        eng.dispose()
                        return {
                            "document_id": doc.id,
                            "filename": doc.filename,
                            "collection": doc.collection_name,
                            "table": tbl,
                            "columns": exec_res["columns"],
                            "rows": exec_res["rows"],
                            "sql": exec_res["sql"],
                        }
            eng.dispose()
        except Exception:
            continue

    return None
