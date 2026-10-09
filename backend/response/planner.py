import copy
import re
from typing import Any, Optional
from backend.response.calculator import calculator
from backend.response.renderer_data import extract_structured_data_from_chunks
from backend.response.schema import AllowedIntentType, ResponsePlan, StructuredResponse
from backend.response.validator import validate_and_repair_structured_response


def detect_query_intent(question: str) -> AllowedIntentType:
    q = question.lower().strip()
    if any(w in q for w in ["analyze", "analysis", "overview", "performance", "dashboard", "breakdown"]):
        return "analyze"
    if any(w in q for w in ["compare", "comparison", "versus", " vs ", "across", "highest", "lowest"]):
        return "compare"
    if any(w in q for w in ["by month", "monthly", "trend", "over time", "january", "chart", "plot", "graph", "visualize"]):
        return "visualize"
    if any(w in q for w in ["how much did", "increase", "growth", "percentage", "calculate", "total", "sum", "average"]):
        return "calculate"
    if any(w in q for w in ["show employee", "show all", "list", "table", "names and departments", "courses", "records", "salary", "salaries", "compensation", "payroll", "pay", "stipend", "wages", "bonus", "earnings", "income"]):
        return "list"
    if any(w in q for w in ["summarize", "summary"]):
        return "summarize"
    if any(w in q for w in ["explain", "how does", "why"]):
        return "explain"
    return "answer"


def apply_workspace_followup_command(
    previous_response: dict[str, Any],
    command_text: str,
) -> StructuredResponse:
    """
    Apply interactive workspace follow-up mutations directly to an existing StructuredResponse
    and increment its version (`v1 -> v2 -> v3`) while preserving undo history.
    """
    state = copy.deepcopy(previous_response)
    prev_snapshot = copy.deepcopy(previous_response)
    prev_snapshot.pop("history_versions", None)

    history = list(state.get("history_versions") or [])
    history.append(prev_snapshot)
    state["history_versions"] = history
    state["version"] = int(state.get("version", 1)) + 1

    cmd = command_text.lower().strip()
    components: list[dict[str, Any]] = list(state.get("components") or [])

    # Target specific component ID or general chart type switch
    target_id_match = re.search(r"\b(component_\d+|chart_\d+|table_\d+)\b", cmd)
    target_id = target_id_match.group(1) if target_id_match else None

    desired_chart_type = None
    for ctype in ["bar", "line", "pie", "area", "scatter"]:
        if re.search(rf"\b{ctype}\b", cmd):
            desired_chart_type = ctype
            break

    if desired_chart_type:
        modified = False
        for comp in components:
            if (target_id and comp.get("id") == target_id) or (not target_id and comp.get("type") == "chart"):
                comp["type"] = "chart"
                comp.setdefault("data", {})["chart_type"] = desired_chart_type
                modified = True
        if not modified:
            for comp in components:
                if comp.get("type") == "table":
                    t_data = comp.get("data", {})
                    cols = t_data.get("columns", [])
                    rows = t_data.get("rows", [])
                    if len(cols) >= 2 and rows:
                        x_key = cols[0]["key"] if isinstance(cols[0], dict) else str(cols[0])
                        y_key = cols[-1]["key"] if isinstance(cols[-1], dict) else str(cols[-1])
                        for col in cols[1:]:
                            ck = col["key"] if isinstance(col, dict) else str(col)
                            if calculator.to_number(rows[0].get(ck)) is not None:
                                y_key = ck
                                break
                        components.append(
                            {
                                "id": f"chart_0{len(components) + 1}",
                                "type": "chart",
                                "title": t_data.get("title", "Chart View"),
                                "data": {
                                    "chart_type": desired_chart_type,
                                    "title": t_data.get("title", "Chart View"),
                                    "x_axis": {"key": x_key, "label": x_key.replace("_", " ").title()},
                                    "y_axis": {"key": y_key, "label": y_key.replace("_", " ").title()},
                                    "series": [{"key": y_key, "label": y_key.replace("_", " ").title()}],
                                    "data": rows,
                                },
                            }
                        )
                        break

    if "make this a table" in cmd or "as a table" in cmd or "to a table" in cmd:
        has_table = any(c.get("type") == "table" for c in components)
        if not has_table:
            for comp in components:
                if comp.get("type") == "chart":
                    c_data = comp.get("data", {})
                    rows = c_data.get("data", [])
                    if rows and isinstance(rows[0], dict):
                        cols = [{"key": k, "label": k.replace("_", " ").title()} for k in rows[0].keys()]
                        components.append(
                            {
                                "id": f"table_0{len(components) + 1}",
                                "type": "table",
                                "title": c_data.get("title", "Structured Data Table"),
                                "data": {
                                    "title": c_data.get("title", "Structured Data Table"),
                                    "columns": cols,
                                    "rows": rows,
                                },
                            }
                        )
                        break

    top_n_match = re.search(r"top\s+(\d+)", cmd)
    if top_n_match:
        limit_n = int(top_n_match.group(1))
        for comp in components:
            if comp.get("type") == "table":
                rows = comp.get("data", {}).get("rows", [])
                if rows and isinstance(rows[0], dict):
                    num_keys = [k for k, v in rows[0].items() if calculator.to_number(v) is not None]
                    if num_keys:
                        comp["data"]["rows"] = calculator.sort_rows(rows, num_keys[-1], descending=True, limit=limit_n)
                    else:
                        comp["data"]["rows"] = rows[:limit_n]
            elif comp.get("type") == "chart":
                rows = comp.get("data", {}).get("data", [])
                y_key = comp.get("data", {}).get("y_axis", {}).get("key")
                if rows and y_key:
                    comp["data"]["data"] = calculator.sort_rows(rows, y_key, descending=True, limit=limit_n)

    rem_match = re.search(r"remove\s+the\s+(chart|table|stat|kpi|timeline|comparison)", cmd)
    if rem_match:
        rem_type = rem_match.group(1).lower()
        if rem_type == "kpi":
            rem_type = "stat"
        components = [c for c in components if c.get("type") != rem_type]

    if "percentage change" in cmd:
        for comp in components:
            if comp.get("type") == "chart":
                rows = comp.get("data", {}).get("data", [])
                y_key = comp.get("data", {}).get("y_axis", {}).get("key")
                if len(rows) >= 2 and y_key:
                    first_v = rows[0].get(y_key)
                    last_v = rows[-1].get(y_key)
                    pct = calculator.compute_percentage_change(first_v, last_v)
                    if pct is not None:
                        components.insert(
                            0,
                            {
                                "id": f"stat_pct_{state['version']}",
                                "type": "stat",
                                "title": "Calculated Percentage Change",
                                "data": {
                                    "label": "Overall Percentage Change",
                                    "value": round(pct, 2),
                                    "format": "percent",
                                    "change": round(pct, 2),
                                    "change_label": f"From {first_v} to {last_v}",
                                    "trend": "up" if pct >= 0 else "down",
                                },
                            },
                        )
                        break

    state["components"] = components
    return validate_and_repair_structured_response(
        raw_payload=state,
        fallback_text="Workspace updated.",
        fallback_sources=state.get("sources", []),
    )


def build_grounded_structured_response(
    question: str,
    answer_text: str,
    answer_found: bool,
    retrieved_chunks: list[dict[str, Any]],
    citations: list[dict[str, Any]],
    route: str = "documents",
    db_query_result: Optional[dict[str, Any]] = None,
) -> StructuredResponse:
    if not answer_found:
        return validate_and_repair_structured_response(
            raw_payload={
                "schema_version": "1.0",
                "version": 1,
                "title": "Knowledge Base Lookup",
                "intent": "answer",
                "response_type": "text",
                "components": [
                    {
                        "id": "text_01",
                        "type": "text",
                        "title": "Not Found in Knowledge Base",
                        "data": {"markdown": answer_text},
                    }
                ],
                "sources": [],
                "confidence": 1.0,
            },
            fallback_text=answer_text,
            fallback_sources=[],
        )

    intent = detect_query_intent(question)
    q_lower = question.lower().strip()
    extracted = extract_structured_data_from_chunks(retrieved_chunks, db_query_result=db_query_result)

    tables = extracted["tables"]
    time_series = extracted["time_series"]
    cat_series = extracted["categorical_series"]
    kpis = extracted["kpis"]
    timeline_events = extracted["timeline_events"]

    # Grounded Guardrail: If user asks for salary data, do not attach non-salary tables (e.g. revenue tables)
    is_salary_query = any(kw in q_lower for kw in ["salary", "salaries", "compensation", "payroll", "stipend", "wages", "earnings"])
    if is_salary_query:
        has_salary_table = any(
            any(kw in t.get("title", "").lower() for kw in ["salary", "compensation", "payroll", "stipend"])
            for t in tables
        )
        if not has_salary_table:
            tables = []
            kpis = []
            time_series = []
            cat_series = []
            answer_text = "I couldn't find any employee salary or payroll records in the uploaded knowledge base."
            return validate_and_repair_structured_response(
                raw_payload={
                    "schema_version": "1.0",
                    "version": 1,
                    "title": question[:70].strip().capitalize(),
                    "intent": "answer",
                    "response_type": "text",
                    "components": [
                        {
                            "id": "text_01",
                            "type": "text",
                            "title": "Not Found in Knowledge Base",
                            "data": {"markdown": answer_text},
                        }
                    ],
                    "sources": citations,
                    "confidence": 1.0,
                },
                fallback_text=answer_text,
                fallback_sources=citations,
            )

    components: list[dict[str, Any]] = []
    calculations_run: list[str] = []
    vis_choice: str = "none"

    is_simple_factual = (
        intent in {"answer", "explain", "lookup"}
        and not (tables or time_series or cat_series or kpis)
        and not any(
            kw in q_lower
            for kw in [
                "table", "chart", "plot", "graph", "trend", "by month", "monthly",
                "compare", "across", "all employees", "show employee", "analyze",
                "performance", "increase", "growth", "highest", "salary", "salaries",
                "compensation", "payroll", "pay", "stipend", "wages", "bonus", "earnings",
            ]
        )
    )

    if is_simple_factual:
        components.append(
            {
                "id": "text_01",
                "type": "text",
                "title": "Answer",
                "data": {"markdown": answer_text},
            }
        )
    else:
        # Always place a concise summary text block first for composite/analytical answers
        if intent in {"analyze", "summarize", "calculate", "compare", "visualize"}:
            components.append(
                {
                    "id": "summary_01",
                    "type": "text",
                    "title": "Executive Summary",
                    "data": {"markdown": answer_text},
                }
            )

        # Add KPI Stat cards when asking about increases, highest values, calculations, or composite analysis
        if kpis and (intent in {"calculate", "analyze", "compare"} or "increase" in q_lower or "highest" in q_lower):
            for idx, kpi in enumerate(kpis[:4], start=1):
                components.append(
                    {
                        "id": f"stat_{idx:02d}",
                        "type": "stat",
                        "title": kpi["label"],
                        "data": kpi,
                    }
                )
            calculations_run.append("kpi_extraction")
            vis_choice = "stat"

        # Deterministic growth/increase stat calculation from time_series when user asks "How much did ... increase?"
        if len(time_series) >= 2 and (intent in {"calculate", "analyze"} or "increase" in q_lower or "growth" in q_lower):
            first_v = time_series[0]["value"]
            last_v = time_series[-1]["value"]
            diff_v = calculator.compute_difference(first_v, last_v)
            pct_chg = calculator.compute_percentage_change(first_v, last_v)
            if pct_chg is not None and not any(c["id"] == "stat_growth_01" for c in components):
                calculations_run.append(f"difference={diff_v}, percentage_change={pct_chg:.2f}%")
                components.append(
                    {
                        "id": "stat_growth_01",
                        "type": "stat",
                        "title": "Calculated Revenue Increase",
                        "data": {
                            "label": f"Increase ({time_series[0]['period']} → {time_series[-1]['period']})",
                            "value": diff_v if diff_v is not None else last_v,
                            "format": "currency",
                            "currency": "INR" if "₹" in answer_text else "USD",
                            "change": round(pct_chg, 2),
                            "change_label": f"From {first_v:,.0f} ({time_series[0]['period']}) to {last_v:,.0f} ({time_series[-1]['period']})",
                            "trend": "up" if pct_chg >= 0 else "down",
                        },
                    }
                )
                vis_choice = "stat"

        # Add Line Chart when time-series data exists and question asks for monthly/trend/analyze
        if len(time_series) >= 2 and (
            intent in {"visualize", "analyze"} or "month" in q_lower or "trend" in q_lower or "january" in q_lower
        ):
            first_v = time_series[0]["value"]
            last_v = time_series[-1]["value"]
            pct_chg = calculator.compute_percentage_change(first_v, last_v)
            if pct_chg is not None:
                calculations_run.append(f"percentage_change={pct_chg:.2f}%")
                if not any(c["type"] == "stat" for c in components):
                    components.append(
                        {
                            "id": "stat_trend_01",
                            "type": "stat",
                            "title": "Period Growth",
                            "data": {
                                "label": f"Change ({time_series[0]['period']} → {time_series[-1]['period']})",
                                "value": calculator.compute_sum([x["value"] for x in time_series]),
                                "format": "currency",
                                "currency": "INR" if "₹" in answer_text else "USD",
                                "change": round(pct_chg, 2),
                                "change_label": f"{time_series[0]['period']} to {time_series[-1]['period']}",
                                "trend": "up" if pct_chg >= 0 else "down",
                            },
                        }
                    )
            components.append(
                {
                    "id": "chart_01",
                    "type": "chart",
                    "title": "Time-Series Trend",
                    "data": {
                        "chart_type": "line",
                        "title": "Monthly Trend",
                        "x_axis": {"key": "period", "label": "Period"},
                        "y_axis": {"key": "value", "label": "Value"},
                        "series": [{"key": "value", "label": "Value"}],
                        "data": time_series,
                    },
                }
            )
            vis_choice = "line"

        # Add Bar Chart when categorical comparisons exist and question asks to compare/highest/analyze
        elif len(cat_series) >= 2 and (
            intent in {"compare", "analyze", "visualize"}
            or "compare" in q_lower
            or "across" in q_lower
            or "highest" in q_lower
            or "bar chart" in q_lower
        ):
            sorted_cats = calculator.sort_rows(cat_series, "value", descending=True)
            top_cat = sorted_cats[0]
            calculations_run.append(f"max_category={top_cat['category']} ({top_cat['value']})")

            if "highest" in q_lower and not any(c["type"] == "stat" for c in components):
                components.append(
                    {
                        "id": "stat_max_01",
                        "type": "stat",
                        "title": f"Highest: {top_cat['category']}",
                        "data": {
                            "label": f"Top: {top_cat['category']}",
                            "value": top_cat["value"],
                            "format": "number",
                            "change_label": top_cat.get("metric", "Highest Value"),
                            "trend": "up",
                        },
                    }
                )

            components.append(
                {
                    "id": "chart_01",
                    "type": "chart",
                    "title": "Category Comparison",
                    "data": {
                        "chart_type": "bar",
                        "title": f"{cat_series[0].get('metric', 'Value')} Comparison",
                        "x_axis": {"key": "category", "label": "Category"},
                        "y_axis": {"key": "value", "label": cat_series[0].get("metric", "Value")},
                        "series": [{"key": "value", "label": cat_series[0].get("metric", "Value")}],
                        "data": sorted_cats,
                    },
                }
            )
            vis_choice = "bar"

        # Add Table when structured rows exist and user asks to list/show employees/table/analyze
        if tables and (
            intent in {"list", "analyze"}
            or "table" in q_lower
            or "employee" in q_lower
            or "department" in q_lower
            or "all " in q_lower
            or "marks" in q_lower
        ):
            for idx, tb in enumerate(tables, start=1):
                components.append(
                    {
                        "id": f"table_{idx:02d}",
                        "type": "table",
                        "title": tb["title"],
                        "data": tb,
                    }
                )
            if vis_choice == "none":
                vis_choice = "table"
        elif time_series and intent == "analyze":
            components.append(
                {
                    "id": "table_01",
                    "type": "table",
                    "title": "Period Breakdown Table",
                    "data": {
                        "title": "Period Breakdown Table",
                        "columns": [
                            {"key": "period", "label": "Period"},
                            {"key": "value", "label": "Value"},
                        ],
                        "rows": time_series,
                    },
                }
            )

        # Add Timeline if user specifically asks for timeline/schedule/roadmap dates
        if timeline_events and any(w in q_lower for w in ["timeline", "schedule", "deadlines", "milestones"]):
            components.append(
                {
                    "id": "timeline_01",
                    "type": "timeline",
                    "title": "Key Milestones & Dates",
                    "data": {"events": timeline_events},
                }
            )

        if not components:
            components.append(
                {
                    "id": "text_01",
                    "type": "text",
                    "title": "Answer",
                    "data": {"markdown": answer_text},
                }
            )

    if len(components) > 1:
        vis_choice = "composite"

    plan = ResponsePlan(
        intent=intent,
        route=route if route in {"documents", "database", "hybrid", "workspace_followup"} else "documents",
        visualization=vis_choice if vis_choice in {"none", "line", "bar", "pie", "area", "scatter", "table", "stat", "composite"} else "none",
        data_required=bool(tables or time_series or cat_series or kpis),
        calculations_run=calculations_run,
    )

    payload = {
        "schema_version": "1.0",
        "version": 1,
        "title": question[:70].strip().capitalize(),
        "intent": intent,
        "response_type": "text" if (len(components) == 1 and components[0]["type"] == "text") else ("single" if len(components) == 1 else "composite"),
        "components": components,
        "sources": citations,
        "confidence": 0.95,
        "plan": plan.model_dump(),
        "history_versions": [],
    }

    return validate_and_repair_structured_response(
        raw_payload=payload,
        fallback_text=answer_text,
        fallback_sources=citations,
    )
