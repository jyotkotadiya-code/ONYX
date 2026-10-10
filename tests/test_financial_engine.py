import pytest
from backend.response.financial_engine import FinancialDataEngine, FinancialRecord


@pytest.fixture
def sample_financial_chunks():
    """
    Isolated test fixture reproducing the exact prompt dataset:
    January 2025: 10000
    February 2025: 15000
    March 2025: 12000
    January 2026: 20000
    February 2026: 18000
    March 2026: 24000
    """
    raw_content = (
        "Fiscal Revenue Statement:\n"
        "January 2025: 10000\n"
        "February 2025: 15000\n"
        "March 2025: 12000\n"
        "January 2026: 20000\n"
        "February 2026: 18000\n"
        "March 2026: 24000\n"
    )
    return [
        {
            "chunk_id": "test_chk_01",
            "content": raw_content,
            "citation": {"filename": "Quarterly_Financials.txt", "locator": "Page 1"},
            "modality": "text",
        }
    ]


def test_financial_record_extraction(sample_financial_chunks):
    records = FinancialDataEngine.extract_records(sample_financial_chunks)
    assert len(records) == 6
    periods = [r.period for r in records]
    assert "January 2025" in periods
    assert "March 2026" in periods
    assert all(r.amount > 0 for r in records)


def test_financial_engine_exact_calculations(sample_financial_chunks):
    records = FinancialDataEngine.extract_records(sample_financial_chunks)

    # 1. Total revenue for 2025 Q1 = 37000
    q_totals = FinancialDataEngine.calculate_period_totals(records, group_by="quarter")
    assert q_totals["2025 Q1"] == 37000.0

    # 2. Total revenue for 2026 Q1 = 62000
    assert q_totals["2026 Q1"] == 62000.0

    # 3. January 2025 revenue = 10000
    jan_2025 = [r for r in records if r.period == "January 2025"][0]
    assert jan_2025.amount == 10000.0

    # 4. Highest-revenue month in supplied dataset = March 2026 (24000)
    peak = FinancialDataEngine.find_highest_month(records)
    assert peak is not None
    assert peak.period == "March 2026"
    assert peak.amount == 24000.0

    # 5. Q1 year-over-year revenue increase = 25000
    # 6. Q1 year-over-year revenue growth = approximately 67.57%
    increase, growth_pct = FinancialDataEngine.calculate_growth(q_totals["2026 Q1"], q_totals["2025 Q1"])
    assert increase == 25000.0
    assert growth_pct == 67.57


def test_zero_denominator_growth_safety():
    # If previous amount is 0, growth percentage must safely return None without ZeroDivisionError
    inc, pct = FinancialDataEngine.calculate_growth(current_amount=5000.0, previous_amount=0.0)
    assert inc == 5000.0
    assert pct is None


def test_financial_query_natural_language_interpretation(sample_financial_chunks):
    # Test Question 1: "What is our total revenue for 2025 Q1?"
    res_q1 = FinancialDataEngine.execute_financial_query(
        "What is our total revenue for 2025 Q1?",
        sample_financial_chunks,
    )
    assert res_q1 is not None
    assert "37,000" in res_q1["answer"]

    # Test Question 2: "What is our total revenue for 2026 Q1?"
    res_q2 = FinancialDataEngine.execute_financial_query(
        "What is our total revenue for 2026 Q1?",
        sample_financial_chunks,
    )
    assert res_q2 is not None
    assert "62,000" in res_q2["answer"]

    # Test Question 3: "What was our revenue in January 2025?"
    res_jan = FinancialDataEngine.execute_financial_query(
        "What was our revenue in January 2025?",
        sample_financial_chunks,
    )
    assert res_jan is not None
    assert "10,000" in res_jan["answer"]

    # Test Question 4: "Which month had the highest sales?"
    res_peak = FinancialDataEngine.execute_financial_query(
        "Which month had the highest sales?",
        sample_financial_chunks,
    )
    assert res_peak is not None
    assert "March 2026" in res_peak["answer"]
    assert "24,000" in res_peak["answer"]

    # Test Question 5: "What is our Q1 year-over-year revenue growth?"
    res_growth = FinancialDataEngine.execute_financial_query(
        "What is our Q1 year-over-year revenue growth?",
        sample_financial_chunks,
    )
    assert res_growth is not None
    assert "25,000" in res_growth["answer"]
    assert "67.57%" in res_growth["answer"]


def test_sales_vs_revenue_conceptual_question(sample_financial_chunks):
    res_diff = FinancialDataEngine.execute_financial_query(
        "What is the difference between sales and revenue?",
        sample_financial_chunks,
    )
    assert res_diff is not None
    assert res_diff.get("is_conceptual") is True
    assert "Revenue" in res_diff["answer"]
    assert "Sales" in res_diff["answer"]
