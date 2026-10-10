import pytest
from backend.database.sql_validator import validate_readonly_sql
from backend.response.calculator import calculator
from backend.response.planner import (
    apply_workspace_followup_command,
    build_grounded_structured_response,
    detect_query_intent,
)
from backend.response.validator import validate_and_repair_structured_response


SAMPLE_CHUNKS = [
    {
        "chunk_id": "c_policy_1",
        "document_id": "doc_policy",
        "content": (
            "Enterprise Refund Policy: Customers on the Enterprise Annual Plan are eligible for a "
            "full 100% refund within 45 calendar days of initial contract signing."
        ),
        "citation": {
            "document_id": "doc_policy",
            "chunk_id": "c_policy_1",
            "filename": "enterprise_policy.docx",
            "page_number": 1,
            "locator": "section=Refund Policy",
        },
    },
    {
        "chunk_id": "c_fin_1",
        "document_id": "doc_fin",
        "content": (
            "Q1 2026 Financial Report:\n"
            "January: ₹20,000\n"
            "February: ₹25,000\n"
            "March: ₹31,000\n"
            "April: ₹35,000\n"
            "May: ₹42,000\n"
            "June: ₹50,000\n"
            "Department Revenue Breakdown:\n"
            "Engineering: ₹120,000\n"
            "Sales: ₹95,000\n"
            "Operations: ₹65,000\n"
            "Q1 Milestones:\n"
            "2026-01-15: Launched Local Vector Store v1\n"
            "2026-02-20: Completed Security Audit\n"
            "2026-03-30: Deployed Multimodal OCR Pipeline"
        ),
        "citation": {
            "document_id": "doc_fin",
            "chunk_id": "c_fin_1",
            "filename": "q1_financial_report.pdf",
            "page_number": 4,
            "locator": "page=4",
        },
    },
]

SAMPLE_DB_RESULT = {
    "document_id": "doc_db_1",
    "filename": "company_records.sqlite",
    "collection": "General",
    "table": "employees",
    "columns": ["emp_id", "name", "department", "salary"],
    "rows": [
        {"emp_id": "EMP-101", "name": "Aarav Patel", "department": "AI Research", "salary": 145000},
        {"emp_id": "EMP-102", "name": "Priya Sharma", "department": "Security", "salary": 138000},
        {"emp_id": "EMP-184", "name": "Rohan Desai", "department": "Infrastructure", "salary": 152000},
    ],
    "sql": 'SELECT * FROM "employees" LIMIT 200',
}


def test_scenario_1_refund_policy_returns_text_only():
    """
    Test 1: 'What is our refund policy?' -> Expected: Text only (anti-over-visualization rule #35).
    """
    resp = build_grounded_structured_response(
        question="What is our refund policy?",
        answer_text="Enterprise customers receive a 100% refund within 45 calendar days.",
        answer_found=True,
        retrieved_chunks=[SAMPLE_CHUNKS[0]],
        citations=[SAMPLE_CHUNKS[0]["citation"]],
    )
    assert resp.response_type == "text"
    assert len(resp.components) == 1
    assert resp.components[0].type == "text"


def test_scenario_2_employee_names_and_departments_returns_table():
    """
    Test 2: 'Show employee names and departments' -> Expected: Table.
    """
    resp = build_grounded_structured_response(
        question="Show employee names and departments",
        answer_text="Here are the employees and their departments from company_records.sqlite.",
        answer_found=True,
        retrieved_chunks=SAMPLE_CHUNKS,
        citations=[SAMPLE_CHUNKS[0]["citation"]],
        route="database",
        db_query_result=SAMPLE_DB_RESULT,
    )
    comp_types = [c.type for c in resp.components]
    assert "table" in comp_types
    tbl = next(c for c in resp.components if c.type == "table")
    assert len(tbl.data["rows"]) == 3


def test_scenario_3_revenue_by_month_returns_line_chart():
    """
    Test 3: 'Show revenue by month' -> Expected: Line chart.
    """
    resp = build_grounded_structured_response(
        question="Show revenue by month",
        answer_text="Monthly revenue grew steadily from January (₹20,000) through June (₹50,000).",
        answer_found=True,
        retrieved_chunks=SAMPLE_CHUNKS,
        citations=[SAMPLE_CHUNKS[1]["citation"]],
    )
    comp_types = [c.type for c in resp.components]
    assert "chart" in comp_types
    chart_comp = next(c for c in resp.components if c.type == "chart")
    assert chart_comp.data["chart_type"] == "line"
    assert chart_comp.data["data"][0]["month"] == "January"
    assert chart_comp.data["data"][0]["value"] == 20000


def test_scenario_4_highest_revenue_department_returns_text_and_stat_or_bar():
    """
    Test 4: 'Which department has the highest revenue?' -> Expected: Text + Stat or Bar chart.
    """
    resp = build_grounded_structured_response(
        question="Which department has the highest revenue?",
        answer_text="Engineering has the highest revenue at ₹120,000.",
        answer_found=True,
        retrieved_chunks=SAMPLE_CHUNKS,
        citations=[SAMPLE_CHUNKS[1]["citation"]],
    )
    comp_types = [c.type for c in resp.components]
    assert "text" in comp_types
    assert ("stat" in comp_types) or ("chart" in comp_types)


def test_scenario_5_compare_revenue_across_departments_returns_bar_chart():
    """
    Test 5: 'Compare revenue across departments' -> Expected: Bar chart (+ comparison/table).
    """
    resp = build_grounded_structured_response(
        question="Compare revenue across departments",
        answer_text="Engineering leads with ₹120,000 followed by Sales (₹95,000) and Operations (₹65,000).",
        answer_found=True,
        retrieved_chunks=SAMPLE_CHUNKS,
        citations=[SAMPLE_CHUNKS[1]["citation"]],
    )
    comp_types = [c.type for c in resp.components]
    assert "chart" in comp_types
    chart_comp = next(c for c in resp.components if c.type == "chart")
    assert chart_comp.data["chart_type"] == "bar"


def test_scenario_6_how_much_did_revenue_increase_returns_stat_and_explanation():
    """
    Test 6: 'How much did revenue increase?' -> Expected: Stat + explanation with deterministic calculation.
    """
    resp = build_grounded_structured_response(
        question="How much did revenue increase?",
        answer_text="Revenue increased by ₹30,000 (+150.0%) from January to June.",
        answer_found=True,
        retrieved_chunks=SAMPLE_CHUNKS,
        citations=[SAMPLE_CHUNKS[1]["citation"]],
    )
    comp_types = [c.type for c in resp.components]
    assert "text" in comp_types
    assert "stat" in comp_types
    stat_comp = next(c for c in resp.components if c.type == "stat")
    # 20,000 -> 50,000 is +150% increase (+30,000 difference)
    assert stat_comp.data["change"] == 150.0


def test_scenario_7_analyze_q1_performance_returns_composite_response():
    """
    Test 7: 'Analyze Q1 performance' -> Expected: Composite response (text + stat + chart + table/timeline).
    """
    resp = build_grounded_structured_response(
        question="Analyze Q1 performance",
        answer_text="Q1 performance showed strong monthly revenue growth and milestone completion.",
        answer_found=True,
        retrieved_chunks=SAMPLE_CHUNKS,
        citations=[SAMPLE_CHUNKS[1]["citation"]],
    )
    assert resp.response_type == "composite"
    comp_types = [c.type for c in resp.components]
    assert "text" in comp_types
    assert "chart" in comp_types
    assert len(resp.components) >= 3


def test_security_rejects_unauthorized_component_and_sanitizes_html():
    """
    Verify that 'execute_shell' or unknown component types are rejected and repaired,
    and script tags in markdown are stripped.
    """
    malicious_payload = {
        "schema_version": "1.0",
        "response_type": "composite",
        "components": [
            {
                "id": "bad_01",
                "type": "execute_shell",
                "data": {"command": "rm -rf /"},
            },
            {
                "id": "text_01",
                "type": "text",
                "data": {"markdown": "Safe text <script>alert('xss')</script> here."},
            },
        ],
        "sources": [],
    }
    validated = validate_and_repair_structured_response(
        raw_payload=malicious_payload,
        fallback_text="Fallback explanation",
    )
    types = [c.type for c in validated.components]
    assert "execute_shell" not in types
    assert len(validated.components) == 1
    assert "<script>" not in validated.components[0].data["markdown"]


def test_sql_validator_blocks_destructive_queries():
    """
    Verify read-only SQL enforcement: SELECT is allowed; DROP/DELETE/UPDATE/INSERT are blocked.
    """
    safe_sql = validate_readonly_sql("SELECT name, department FROM employees")
    assert "LIMIT" in safe_sql.upper()

    for dangerous in [
        "DROP TABLE employees",
        "DELETE FROM employees WHERE 1=1",
        "UPDATE employees SET salary = 0",
        "INSERT INTO employees VALUES (1, 'x')",
        "SELECT * FROM employees; DROP TABLE employees",
    ]:
        with pytest.raises(ValueError):
            validate_readonly_sql(dangerous)


def test_workspace_followup_commands_and_version_history():
    """
    Verify interactive workspace follow-up mutations ('Make this a table', 'Change chart_02 to a bar chart')
    and version history incrementing (v1 -> v2 -> v3).
    """
    v1 = build_grounded_structured_response(
        question="Show revenue by month",
        answer_text="Monthly revenue from January to June.",
        answer_found=True,
        retrieved_chunks=SAMPLE_CHUNKS,
        citations=[SAMPLE_CHUNKS[1]["citation"]],
    ).model_dump()
    assert v1["version"] == 1

    v2 = apply_workspace_followup_command(v1, "Make this a table").model_dump()
    assert v2["version"] == 2
    assert len(v2["history_versions"]) == 1
    assert any(c["type"] == "table" for c in v2["components"])

    v3 = apply_workspace_followup_command(v2, "Show this as a bar chart").model_dump()
    assert v3["version"] == 3
    assert len(v3["history_versions"]) == 2
    chart_comp = next(c for c in v3["components"] if c["type"] == "chart")
    assert chart_comp["data"]["chart_type"] == "bar"


def test_text_only_workspace_transformation_buttons():
    """
    Directly tests the user's reported bug where a workspace with ONLY text
    could not be transformed when clicking 'Make Table', 'Bar Chart', 'Line Chart', etc.
    """
    raw_markdown = (
        "Based on the uploaded knowledge base:\n\n"
        "- Jan 2024: 42,000 [sample_organization_monthly_revenue_24_months.pdf — Page 2]\n"
        "- Feb 2024: 44,500 [sample_organization_monthly_revenue_24_months.pdf — Page 2]\n"
        "- Mar 2024: 43,800 [sample_organization_monthly_revenue_24_months.pdf — Page 2]\n"
        "- Apr 2024: 47,200 [sample_organization_monthly_revenue_24_months.pdf — Page 2]\n"
    )
    text_only_ws = {
        "schema_version": "1.0",
        "version": 1,
        "title": "Revenue report",
        "intent": "answer",
        "response_type": "text",
        "components": [
            {
                "id": "text_01",
                "type": "text",
                "title": "Answer",
                "data": {"markdown": raw_markdown},
            }
        ],
        "sources": [{"filename": "sample_organization_monthly_revenue_24_months.pdf", "locator": "Page 2"}],
        "confidence": 1.0,
        "history_versions": [],
    }

    # 1. User clicks 'Make Table' -> must create table!
    ws_table = apply_workspace_followup_command(text_only_ws, "Make this a table").model_dump()
    assert ws_table["version"] == 2
    assert any(c["type"] == "table" for c in ws_table["components"])
    table_comp = next(c for c in ws_table["components"] if c["type"] == "table")
    assert len(table_comp["data"]["rows"]) == 4

    # 2. User clicks 'Bar Chart' -> must create bar chart!
    ws_bar = apply_workspace_followup_command(text_only_ws, "Show this as a bar chart").model_dump()
    assert ws_bar["version"] == 2
    assert any(c["type"] == "chart" for c in ws_bar["components"])
    bar_comp = next(c for c in ws_bar["components"] if c["type"] == "chart")
    assert bar_comp["data"]["chart_type"] == "bar"
    assert len(bar_comp["data"]["data"]) == 4

    # 3. User clicks 'Line Chart' -> must create line chart!
    ws_line = apply_workspace_followup_command(text_only_ws, "Show this as a line chart").model_dump()
    assert ws_line["version"] == 2
    line_comp = next(c for c in ws_line["components"] if c["type"] == "chart")
    assert line_comp["data"]["chart_type"] == "line"

    # 4. User clicks 'Add percentage change' -> must create stat card!
    ws_pct = apply_workspace_followup_command(text_only_ws, "Add percentage change").model_dump()
    assert any(c["type"] == "stat" for c in ws_pct["components"])

