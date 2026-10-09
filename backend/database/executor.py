from pathlib import Path
from typing import Any, Optional
from sqlalchemy import create_engine, inspect, text
from backend.database.sql_validator import validate_readonly_sql


def execute_readonly_query(
    connection_url_or_path: str,
    sql_query: str,
    params: Optional[dict[str, Any]] = None,
    max_rows: int = 500,
) -> dict[str, Any]:
    """
    Validate and execute a read-only SELECT query against a local SQLite/PostgreSQL/MySQL database.
    Returns columns and unrounded row dictionaries.
    """
    if "://" not in connection_url_or_path:
        db_path = Path(connection_url_or_path).resolve()
        if not db_path.exists():
            raise FileNotFoundError(f"Database file not found: {db_path}")
        conn_url = f"sqlite:///{db_path}"
        db_name = db_path.name
    else:
        conn_url = connection_url_or_path
        db_name = conn_url.split("/")[-1].split("?")[0] or "database"

    eng = create_engine(conn_url)
    try:
        insp = inspect(eng)
        allowed_tables = insp.get_table_names()
        validated_sql = validate_readonly_sql(sql_query, allowed_tables=allowed_tables)

        with eng.connect() as conn:
            result = conn.execute(text(validated_sql), params or {})
            columns = list(result.keys())
            raw_rows = result.mappings().fetchmany(max_rows)
            rows = [dict(r) for r in raw_rows]

        return {
            "database": db_name,
            "sql": validated_sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
    finally:
        eng.dispose()
