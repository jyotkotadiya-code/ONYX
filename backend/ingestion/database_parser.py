from pathlib import Path
from typing import Any, Optional
from sqlalchemy import create_engine, inspect, text
from backend.core.logging_config import ingestion_logger
from backend.core.models import ParsedBlock
from backend.core.security import sanitize_identifier


def inspect_database_schema(connection_url_or_path: str) -> dict[str, Any]:
    """
    Inspect SQLite, PostgreSQL, or MySQL database schema locally.
    Returns list of tables, columns, primary keys, and row counts.
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
    insp = inspect(eng)
    tables_info = []

    with eng.connect() as conn:
        for table_name in insp.get_table_names():
            safe_table = sanitize_identifier(table_name)
            cols = [c["name"] for c in insp.get_columns(table_name)]
            pk_constraint = insp.get_pk_constraint(table_name) or {}
            pks = pk_constraint.get("constrained_columns") or []
            row_count = 0
            try:
                row_count = conn.execute(text(f'SELECT COUNT(*) FROM "{safe_table}"')).scalar() or 0
            except Exception:
                pass
            tables_info.append(
                {
                    "table": table_name,
                    "columns": cols,
                    "primary_keys": pks,
                    "row_count": int(row_count),
                }
            )
    eng.dispose()
    return {"database": db_name, "tables": tables_info}


def parse_database(
    connection_url_or_path: str,
    selected_tables: Optional[list[str]] = None,
    max_rows_per_table: int = 5000,
) -> tuple[list[ParsedBlock], dict[str, Any]]:
    """
    Serialize database rows into structured, semantically searchable blocks
    preserving database name, table, primary key, column names, and row ID.
    Never dumps the entire database into one giant unstructured string.
    """
    if "://" not in connection_url_or_path:
        db_path = Path(connection_url_or_path).resolve()
        conn_url = f"sqlite:///{db_path}"
        db_name = db_path.name
    else:
        conn_url = connection_url_or_path
        db_name = conn_url.split("/")[-1].split("?")[0] or "database"

    eng = create_engine(conn_url)
    insp = inspect(eng)
    all_tables = insp.get_table_names()

    if selected_tables:
        target_tables = [t for t in selected_tables if t in all_tables]
    else:
        target_tables = all_tables

    blocks: list[ParsedBlock] = []
    total_rows_indexed = 0

    with eng.connect() as conn:
        for table_name in target_tables:
            safe_table = sanitize_identifier(table_name)
            columns_meta = insp.get_columns(table_name)
            col_names = [c["name"] for c in columns_meta]
            pk_constraint = insp.get_pk_constraint(table_name) or {}
            pks = pk_constraint.get("constrained_columns") or []
            pk_col = pks[0] if pks else (col_names[0] if col_names else "rowid")

            result = conn.execute(text(f'SELECT * FROM "{safe_table}" LIMIT :lim'), {"lim": max_rows_per_table})
            rows = result.mappings().all()

            for idx, row in enumerate(rows, start=1):
                row_id_val = str(row.get(pk_col, idx))
                lines = [
                    f"Database: {db_name}",
                    f"Table: {table_name}",
                    f"Row ID ({pk_col}): {row_id_val}",
                ]
                for col in col_names:
                    val = row.get(col)
                    if val is not None and str(val).strip() != "":
                        lines.append(f"{col}: {val}")

                serialized_record = "\n".join(lines)
                blocks.append(
                    ParsedBlock(
                        text=serialized_record,
                        modality="database",
                        page_number=idx,
                        section_title=f"Table '{table_name}' — Row {row_id_val}",
                        table_name=table_name,
                        row_id=row_id_val,
                        extra_metadata={
                            "source_type": "database",
                            "database": db_name,
                            "table": table_name,
                            "primary_key": pk_col,
                            "row_id": row_id_val,
                            "columns": ", ".join(col_names),
                        },
                    )
                )
                total_rows_indexed += 1

    eng.dispose()
    meta = {
        "database": db_name,
        "tables_indexed": target_tables,
        "total_rows_indexed": total_rows_indexed,
        "page_count": max(1, len(target_tables)),
    }
    ingestion_logger.info(
        f"Parsed Database '{db_name}' ({len(target_tables)} tables, {total_rows_indexed} rows)."
    )
    return blocks, meta
