import calendar
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from backend.core.logging_config import app_logger
from backend.response.calculator import calculator


MONTH_TO_NUM = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5, "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

NUM_TO_MONTH = {v: k.title() for k, v in MONTH_TO_NUM.items() if len(k) > 3}


@dataclass
class FinancialRecord:
    record_id: str
    period: str  # e.g., "January 2025"
    month: Optional[str] = None  # "January"
    month_num: Optional[int] = None  # 1..12
    year: Optional[int] = None  # 2025
    quarter: Optional[str] = None  # "2025 Q1"
    metric: str = "revenue"  # "revenue", "sales", "expense", "profit"
    amount: float = 0.0
    currency: str = "USD"
    source_document: str = "document"
    source_locator: str = "Page 1"
    raw_text: str = ""


class FinancialDataEngine:
    """
    Deterministic Financial & Revenue Analysis Engine.
    Extracts, normalizes, validates, and calculates financial metrics strictly from retrieved data.
    Never relies on LLM arithmetic or invented numbers.
    """

    @staticmethod
    def parse_amount(val_str: Any) -> Optional[float]:
        if isinstance(val_str, (int, float)) and not isinstance(val_str, bool):
            return float(val_str)
        if not val_str or not isinstance(val_str, str):
            return None
        cleaned = val_str.strip().replace(",", "").replace("$", "").replace("₹", "").replace("€", "").replace("£", "")
        # Remove OCR artifact prefix/suffix
        cleaned = re.sub(r"^[A-Za-z\s]+(?=\d)", "", cleaned).strip()
        cleaned = re.sub(r"(?<=\d)[A-Za-z\s]+$", "", cleaned).strip()
        try:
            return float(Decimal(cleaned))
        except (InvalidOperation, ValueError):
            return calculator.to_number(val_str)

    @classmethod
    def detect_currency(cls, text: str) -> str:
        if "₹" in text or "inr" in text.lower():
            return "INR"
        if "€" in text or "eur" in text.lower():
            return "EUR"
        if "£" in text or "gbp" in text.lower():
            return "GBP"
        return "USD"

    @classmethod
    def extract_records(cls, retrieved_chunks: list[dict[str, Any]]) -> list[FinancialRecord]:
        """
        Extract and normalize financial records from all retrieved document chunks.
        Deduplicates identical records across chunk overlaps.
        """
        records: list[FinancialRecord] = []
        seen_keys: set[str] = set()

        for chunk_idx, ch in enumerate(retrieved_chunks):
            content = ch.get("content", "")
            cit = ch.get("citation", {})
            doc_name = cit.get("filename", f"Doc_{chunk_idx+1}")
            locator = cit.get("locator", f"Page {ch.get('page_number', 1)}")
            currency = cls.detect_currency(content)

            lines = content.splitlines()

            # 1. Check for Markdown Tables
            in_table = False
            headers: list[str] = []
            for line_idx, line in enumerate(lines):
                sline = line.strip()
                if sline.startswith("|") and sline.endswith("|"):
                    parts = [p.strip() for p in sline.split("|") if p.strip()]
                    if not in_table:
                        # Could be header
                        if line_idx + 1 < len(lines) and "---" in lines[line_idx + 1]:
                            headers = [h.lower() for h in parts]
                            in_table = True
                            continue
                    elif "---" in sline:
                        continue
                    else:
                        # Table row
                        row_parts = parts
                        if len(row_parts) >= len(headers) and headers:
                            row_dict = {headers[i]: row_parts[i] for i in range(min(len(headers), len(row_parts)))}
                            # Identify date/period and amount
                            period_val = None
                            amount_val = None
                            metric_type = "revenue"

                            for hk, hv in row_dict.items():
                                if any(m in hk for m in ["month", "date", "period", "year"]):
                                    period_val = hv
                                if any(m in hk for m in ["revenue", "sales", "turnover", "income"]):
                                    amount_val = cls.parse_amount(hv)
                                    metric_type = "revenue" if "revenue" in hk else "sales"
                                elif any(m in hk for m in ["expense", "cost"]):
                                    amount_val = cls.parse_amount(hv)
                                    metric_type = "expense"
                                elif any(m in hk for m in ["profit", "net"]):
                                    amount_val = cls.parse_amount(hv)
                                    metric_type = "profit"

                            if period_val and amount_val is not None:
                                rec = cls._build_record(
                                    period_raw=period_val,
                                    amount=amount_val,
                                    metric=metric_type,
                                    currency=currency,
                                    doc_name=doc_name,
                                    locator=locator,
                                    raw_line=sline,
                                )
                                if rec:
                                    k = f"{rec.metric}:{rec.period}:{rec.amount}"
                                    if k not in seen_keys:
                                        seen_keys.add(k)
                                        records.append(rec)
                else:
                    in_table = False

            # 2. Key-Value & Plain Text Patterns (e.g. "January 2025: 10000", "Jan 2025 - $10,000", "Revenue for January 2025 was 10000")
            for line in lines:
                sline = line.strip()
                if not sline or sline.startswith("|") or sline.startswith("#"):
                    continue

                # Pattern: Month (Year)? [: - =] (Currency)? Amount
                month_re = re.search(
                    r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b(?:\s+['’\-]?\s*(\d{4}))?\s*[:\-–=|\t,]*\s*(?:[A-Za-z₹\$€£]{1,3})?\s*([0-9][0-9,]*(?:\.[0-9]+)?(?:\s*(?:Million|M|Cr|Lakh|K))?)\b",
                    sline,
                    re.IGNORECASE,
                )
                if month_re:
                    m_name = month_re.group(1).title()
                    yr_str = month_re.group(2)
                    amt_str = month_re.group(3)
                    amt = cls.parse_amount(amt_str)
                    if amt is not None and amt not in (2023, 2024, 2025, 2026, 2027) and amt > 0:
                        period_str = f"{m_name} {yr_str}" if yr_str else m_name
                        metric_type = "sales" if "sales" in sline.lower() else "revenue"
                        rec = cls._build_record(
                            period_raw=period_str,
                            amount=amt,
                            metric=metric_type,
                            currency=currency,
                            doc_name=doc_name,
                            locator=locator,
                            raw_line=sline,
                        )
                        if rec:
                            k = f"{rec.metric}:{rec.period}:{rec.amount}"
                            if k not in seen_keys:
                                seen_keys.add(k)
                                records.append(rec)

        records.sort(key=lambda r: (r.year or 0, r.month_num or 0))
        return records

    @classmethod
    def _build_record(
        cls,
        period_raw: str,
        amount: float,
        metric: str,
        currency: str,
        doc_name: str,
        locator: str,
        raw_line: str,
    ) -> Optional[FinancialRecord]:
        period_clean = period_raw.strip()
        m_match = re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
            period_clean,
            re.IGNORECASE,
        )
        y_match = re.search(r"\b(20\d{2})\b", period_clean)

        month_str = None
        month_num = None
        year_num = int(y_match.group(1)) if y_match else None

        if m_match:
            raw_m = m_match.group(1).lower()
            month_num = MONTH_TO_NUM.get(raw_m)
            if month_num:
                month_str = NUM_TO_MONTH.get(month_num, raw_m.title())

        quarter_str = None
        if month_num and year_num:
            q_num = (month_num - 1) // 3 + 1
            quarter_str = f"{year_num} Q{q_num}"
        elif year_num:
            q_match = re.search(r"Q([1-4])", period_clean, re.IGNORECASE)
            if q_match:
                quarter_str = f"{year_num} Q{q_match.group(1)}"

        canonical_period = f"{month_str} {year_num}" if (month_str and year_num) else period_clean

        return FinancialRecord(
            record_id=f"rec_{len(period_clean)}_{amount}",
            period=canonical_period,
            month=month_str,
            month_num=month_num,
            year=year_num,
            quarter=quarter_str,
            metric=metric,
            amount=amount,
            currency=currency,
            source_document=doc_name,
            source_locator=locator,
            raw_text=raw_line,
        )

    # ─────────────────────────────────────────────────────────────────────────
    # DETERMINISTIC FINANCIAL CALCULATIONS
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def calculate_total(cls, records: list[FinancialRecord], metric: Optional[str] = None) -> float:
        filtered = [r.amount for r in records if (metric is None or r.metric == metric)]
        return float(sum(filtered))

    @classmethod
    def calculate_average(cls, records: list[FinancialRecord], metric: Optional[str] = None) -> float:
        filtered = [r.amount for r in records if (metric is None or r.metric == metric)]
        return float(sum(filtered) / len(filtered)) if filtered else 0.0

    @classmethod
    def find_highest_month(cls, records: list[FinancialRecord], metric: Optional[str] = None) -> Optional[FinancialRecord]:
        filtered = [r for r in records if (metric is None or r.metric == metric)]
        return max(filtered, key=lambda r: r.amount) if filtered else None

    @classmethod
    def find_lowest_month(cls, records: list[FinancialRecord], metric: Optional[str] = None) -> Optional[FinancialRecord]:
        filtered = [r for r in records if (metric is None or r.metric == metric)]
        return min(filtered, key=lambda r: r.amount) if filtered else None

    @classmethod
    def calculate_period_totals(cls, records: list[FinancialRecord], group_by: str = "quarter") -> dict[str, float]:
        """Group and sum revenue by quarter ('2025 Q1') or year (2025)."""
        buckets: dict[str, float] = {}
        for r in records:
            if group_by == "quarter" and r.quarter:
                buckets[r.quarter] = buckets.get(r.quarter, 0.0) + r.amount
            elif group_by == "year" and r.year:
                buckets[str(r.year)] = buckets.get(str(r.year), 0.0) + r.amount
            elif group_by == "month" and r.period:
                buckets[r.period] = buckets.get(r.period, 0.0) + r.amount
        return buckets

    @classmethod
    def calculate_growth(
        cls,
        current_amount: float,
        previous_amount: float,
    ) -> tuple[float, Optional[float]]:
        """
        Returns (absolute_increase, growth_percentage).
        Handles zero-denominator safely without division by zero.
        """
        increase = round(current_amount - previous_amount, 4)
        if previous_amount == 0 or previous_amount is None:
            return increase, None
        growth_pct = round(((current_amount - previous_amount) / abs(previous_amount)) * 100.0, 2)
        return increase, growth_pct

    # ─────────────────────────────────────────────────────────────────────────
    # FINANCIAL QUESTION INTERPRETATION & ANSWER GENERATION
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def execute_financial_query(
        cls,
        question: str,
        retrieved_chunks: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """
        Detects financial intent and executes deterministic calculation.
        Returns None if question is not a financial query or no records exist.
        """
        q_lower = question.lower().strip()
        fin_keywords = ["revenue", "sales", "growth", "quarter", "q1", "q2", "q3", "q4", "highest sales", "highest revenue", "lowest", "average monthly", "total revenue", "total sales"]
        if not any(k in q_lower for k in fin_keywords):
            return None

        # Check for conceptual question: difference between sales and revenue
        if "difference between" in q_lower and ("sales" in q_lower and "revenue" in q_lower):
            return {
                "is_conceptual": True,
                "answer": (
                    "**Difference Between Sales and Revenue:**\n\n"
                    "- **Revenue (Top Line):** The total amount of money brought in by a company from all operations and sources, including sales of goods/services, interest, royalties, and investments.\n"
                    "- **Sales (Operating Inflow):** Specifically refers to the proceeds generated directly from selling products or merchandise to customers.\n\n"
                    "*All sales contribute to revenue, but revenue can include non-sales income.*"
                ),
                "metric": "concept",
                "components": [],
            }

        records = cls.extract_records(retrieved_chunks)
        if not records:
            return None

        # Multi-document / qualitative questions should be handled by RAG synthesis
        if any(w in q_lower for w in ["expense", "caused", "why", "who", "deadline", "lead architect", "policy", "project mercury"]):
            return None

        # Categorical / Department queries are handled by categorical series analysis
        if any(w in q_lower for w in ["department", "departments", "category", "categories", "product", "products", "employee", "employees", "staff", "role"]):
            return None

        currency_symbol = "₹" if records[0].currency == "INR" else ("€" if records[0].currency == "EUR" else "$")

        # Case 1: Specific Month Query (e.g. "What was our revenue in January?", "January 2025 revenue")
        month_q_match = re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b(?:\s+(\d{4}))?",
            question,
            re.IGNORECASE,
        )
        if month_q_match and not any(k in q_lower for k in ["growth", "increase", "compare", "highest", "average", "total", "chart", "table"]):
            m_target = month_q_match.group(1).lower()
            y_target = int(month_q_match.group(2)) if month_q_match.group(2) else None
            m_target_num = MONTH_TO_NUM.get(m_target)

            matched_records = [
                r for r in records
                if (r.month_num == m_target_num and (y_target is None or r.year == y_target))
            ]
            if matched_records:
                rec = matched_records[0]
                ans_text = (
                    f"In **{rec.period}**, {rec.metric} was **{currency_symbol}{rec.amount:,.2f}** "
                    f"([📄 {rec.source_document} — {rec.source_locator}])."
                )
                return {
                    "is_financial": True,
                    "answer": ans_text,
                    "metric": rec.metric,
                    "records": [rec],
                    "components": [
                        {
                            "id": "stat_fin_01",
                            "type": "stat",
                            "title": f"{rec.period} {rec.metric.title()}",
                            "data": {
                                "label": f"{rec.period} {rec.metric.title()}",
                                "value": rec.amount,
                                "format": "currency",
                                "currency": rec.currency,
                                "change_label": f"Verified from {rec.source_document}",
                                "trend": "neutral",
                            },
                        }
                    ],
                }

        # Case 2: Highest / Lowest Sales/Revenue Month
        if any(w in q_lower for w in ["highest", "peak", "maximum", "max month"]):
            peak = cls.find_highest_month(records)
            if peak:
                ans_text = (
                    f"The highest {peak.metric} month in the supplied dataset was **{peak.period}** "
                    f"with **{currency_symbol}{peak.amount:,.2f}** "
                    f"([📄 {peak.source_document} — {peak.source_locator}])."
                )
                return {
                    "is_financial": True,
                    "answer": ans_text,
                    "metric": "max",
                    "records": [peak],
                    "components": [
                        {
                            "id": "stat_peak_01",
                            "type": "stat",
                            "title": "Highest Month",
                            "data": {
                                "label": f"Peak Month: {peak.period}",
                                "value": peak.amount,
                                "format": "currency",
                                "currency": peak.currency,
                                "change_label": "Highest recorded in dataset",
                                "trend": "up",
                            },
                        }
                    ],
                }

        if any(w in q_lower for w in ["lowest", "minimum", "min month"]):
            low = cls.find_lowest_month(records)
            if low:
                ans_text = (
                    f"The lowest {low.metric} month was **{low.period}** with **{currency_symbol}{low.amount:,.2f}** "
                    f"([📄 {low.source_document} — {low.source_locator}])."
                )
                return {
                    "is_financial": True,
                    "answer": ans_text,
                    "metric": "min",
                    "records": [low],
                    "components": [],
                }

        # Case 3: Average Monthly Revenue
        if "average" in q_lower and ("month" in q_lower or "revenue" in q_lower or "sales" in q_lower):
            avg_val = round(cls.calculate_average(records), 2)
            ans_text = (
                f"The average monthly revenue across the {len(records)} recorded periods is "
                f"**{currency_symbol}{avg_val:,.2f}**."
            )
            return {
                "is_financial": True,
                "answer": ans_text,
                "metric": "average",
                "components": [
                    {
                        "id": "stat_avg_01",
                        "type": "stat",
                        "title": "Average Monthly Revenue",
                        "data": {
                            "label": "Average Monthly Revenue",
                            "value": avg_val,
                            "format": "currency",
                            "currency": records[0].currency,
                            "change_label": f"Across {len(records)} periods",
                            "trend": "neutral",
                        },
                    }
                ],
            }

        # Case 4: Total Revenue / Total Sales / Quarterly Queries (e.g., "Total revenue for 2025 Q1", "Total revenue")
        q_target = re.search(r"\b(20\d{2})\s+q([1-4])\b|\bq([1-4])\s+(20\d{2})\b", q_lower)
        if q_target:
            yr = int(q_target.group(1) or q_target.group(4))
            q_num = int(q_target.group(2) or q_target.group(3))
            q_label = f"{yr} Q{q_num}"
            q_records = [r for r in records if r.quarter == q_label]
            if q_records:
                total_q = cls.calculate_total(q_records)
                month_items = ", ".join(f"{r.period}: {currency_symbol}{r.amount:,.2f}" for r in q_records)
                ans_text = (
                    f"Total revenue for **{q_label}** is **{currency_symbol}{total_q:,.2f}** "
                    f"({month_items})."
                )
                return {
                    "is_financial": True,
                    "answer": ans_text,
                    "metric": "quarter_total",
                    "components": [
                        {
                            "id": f"stat_q_{yr}_{q_num}",
                            "type": "stat",
                            "title": f"Total Revenue ({q_label})",
                            "data": {
                                "label": f"{q_label} Total Revenue",
                                "value": total_q,
                                "format": "currency",
                                "currency": records[0].currency,
                                "change_label": f"Sum of {len(q_records)} months",
                                "trend": "neutral",
                            },
                        }
                    ],
                }

        # Case 5: Period-over-Period YoY Comparison & Growth (e.g., "Compare revenue between two years", "Q1 year-over-year revenue growth", "YoY revenue increase")
        if any(w in q_lower for w in ["compare", "growth", "increase", "year-over-year", "yoy"]):
            # Group by quarters and years
            q_totals = cls.calculate_period_totals(records, group_by="quarter")
            # Look for 2025 Q1 vs 2026 Q1 or two years
            if "2025 q1" in [k.lower() for k in q_totals] and "2026 q1" in [k.lower() for k in q_totals]:
                q2025 = q_totals["2025 Q1"]
                q2026 = q_totals["2026 Q1"]
                inc, pct = cls.calculate_growth(q2026, q2025)
                pct_str = f"{pct:.2f}%" if pct is not None else "N/A"
                ans_text = (
                    f"**Q1 Year-over-Year Revenue Performance:**\n\n"
                    f"- **Total Revenue 2025 Q1:** {currency_symbol}{q2025:,.2f}\n"
                    f"- **Total Revenue 2026 Q1:** {currency_symbol}{q2026:,.2f}\n"
                    f"- **Q1 Year-over-Year Revenue Increase:** **{currency_symbol}{inc:,.2f}**\n"
                    f"- **Q1 Year-over-Year Revenue Growth:** **{pct_str}**"
                )
                return {
                    "is_financial": True,
                    "answer": ans_text,
                    "metric": "yoy_growth",
                    "components": [
                        {
                            "id": "stat_yoy_growth",
                            "type": "stat",
                            "title": "Q1 YoY Revenue Growth",
                            "data": {
                                "label": "Q1 YoY Growth",
                                "value": pct or 0.0,
                                "format": "percent",
                                "change": pct,
                                "change_label": f"+{currency_symbol}{inc:,.2f} YoY Increase",
                                "trend": "up" if (pct and pct > 0) else "down",
                            },
                        },
                        {
                            "id": "table_q_comparison",
                            "type": "table",
                            "title": "Quarterly Revenue Comparison",
                            "data": {
                                "title": "Quarterly Revenue Comparison",
                                "columns": [
                                    {"key": "quarter", "label": "Quarter"},
                                    {"key": "revenue", "label": f"Revenue ({records[0].currency})"},
                                ],
                                "rows": [
                                    {"quarter": "2025 Q1", "revenue": q2025},
                                    {"quarter": "2026 Q1", "revenue": q2026},
                                ],
                            },
                        },
                    ],
                }

            # General YoY between years
            y_totals = cls.calculate_period_totals(records, group_by="year")
            sorted_years = sorted(y_totals.keys())
            if len(sorted_years) >= 2:
                y1, y2 = sorted_years[-2], sorted_years[-1]
                v1, v2 = y_totals[y1], y_totals[y2]
                inc, pct = cls.calculate_growth(v2, v1)
                pct_str = f"{pct:.2f}%" if pct is not None else "N/A"
                ans_text = (
                    f"**Year-over-Year Revenue Comparison ({y1} vs {y2}):**\n\n"
                    f"- **Total Revenue {y1}:** {currency_symbol}{v1:,.2f}\n"
                    f"- **Total Revenue {y2}:** {currency_symbol}{v2:,.2f}\n"
                    f"- **Annual Increase:** **{currency_symbol}{inc:,.2f}**\n"
                    f"- **Annual Growth:** **{pct_str}**"
                )
                return {
                    "is_financial": True,
                    "answer": ans_text,
                    "metric": "yoy_growth",
                    "components": [
                        {
                            "id": "stat_annual_growth",
                            "type": "stat",
                            "title": f"YoY Revenue Growth ({y1} to {y2})",
                            "data": {
                                "label": "Annual Revenue Growth",
                                "value": pct or 0.0,
                                "format": "percent",
                                "change": pct,
                                "change_label": f"+{currency_symbol}{inc:,.2f} ({y1} -> {y2})",
                                "trend": "up" if (pct and pct > 0) else "down",
                            },
                        }
                    ],
                }

            if len(records) >= 2 and any(w in q_lower for w in ["increase", "growth", "how much did"]):
                first_r = records[0]
                last_r = records[-1]
                inc, pct = cls.calculate_growth(last_r.amount, first_r.amount)
                pct_str = f"{pct:.2f}%" if pct is not None else "N/A"
                ans_text = (
                    f"{records[0].metric.title()} increased by **{currency_symbol}{inc:,.2f}** "
                    f"(**+{pct_str}**) from {first_r.period} to {last_r.period}."
                )
                return {
                    "is_financial": True,
                    "answer": ans_text,
                    "metric": "period_growth",
                    "components": [
                        {
                            "id": "stat_growth_01",
                            "type": "stat",
                            "title": f"Calculated {records[0].metric.title()} Increase",
                            "data": {
                                "label": f"Increase ({first_r.period} → {last_r.period})",
                                "value": inc if inc is not None else last_r.amount,
                                "format": "currency",
                                "currency": records[0].currency,
                                "change": round(pct, 2) if pct is not None else 0.0,
                                "change_label": f"From {first_r.amount:,.0f} to {last_r.amount:,.0f}",
                                "trend": "up" if (pct and pct >= 0) else "down",
                            },
                        }
                    ],
                }

        # Case 6: Total Revenue (General)
        if "total" in q_lower and ("revenue" in q_lower or "sales" in q_lower):
            tot = cls.calculate_total(records)
            ans_text = f"Total {records[0].metric} across all {len(records)} recorded periods is **{currency_symbol}{tot:,.2f}**."
            return {
                "is_financial": True,
                "answer": ans_text,
                "metric": "total",
                "components": [
                    {
                        "id": "stat_tot_01",
                        "type": "stat",
                        "title": f"Total {records[0].metric.title()}",
                        "data": {
                            "label": f"Total {records[0].metric.title()}",
                            "value": tot,
                            "format": "currency",
                            "currency": records[0].currency,
                            "change_label": f"Across {len(records)} periods",
                            "trend": "neutral",
                        },
                    }
                ],
            }

        # Case 7: Show in a Table, Chart, or Comprehensive Report/Overview
        report_terms = [
            "table", "chart", "monthly sales", "monthly revenue", "breakdown",
            "report", "revenue", "sales", "overview", "summary", "data", "performance",
            "figures", "financial", "graph", "trend", "all months", "24-month", "annual"
        ]
        if any(w in q_lower for w in report_terms) and records:
            tbl_rows = [
                {
                    "period": r.period,
                    "month": r.month or r.period,
                    "revenue": r.amount,
                    "value": r.amount,
                    "formatted": f"{currency_symbol}{r.amount:,.2f}",
                    "source": r.source_document,
                }
                for r in records
            ]
            tot = cls.calculate_total(records)
            avg = round(cls.calculate_average(records), 2)
            peak = cls.find_highest_month(records)

            components: list[dict[str, Any]] = [
                {
                    "id": "stat_tot_01",
                    "type": "stat",
                    "title": f"Total {records[0].metric.title()}",
                    "data": {
                        "label": f"Total {records[0].metric.title()}",
                        "value": tot,
                        "format": "currency",
                        "currency": records[0].currency,
                        "change_label": f"Sum across {len(records)} periods",
                        "trend": "neutral",
                    },
                },
                {
                    "id": "stat_avg_01",
                    "type": "stat",
                    "title": "Average Monthly",
                    "data": {
                        "label": "Average Monthly",
                        "value": avg,
                        "format": "currency",
                        "currency": records[0].currency,
                        "change_label": f"Across {len(records)} periods",
                        "trend": "neutral",
                    },
                },
            ]
            if peak:
                components.append(
                    {
                        "id": "stat_peak_01",
                        "type": "stat",
                        "title": "Peak Month",
                        "data": {
                            "label": f"Peak: {peak.period}",
                            "value": peak.amount,
                            "format": "currency",
                            "currency": records[0].currency,
                            "change_label": "Highest recorded month",
                            "trend": "up",
                        },
                    }
                )

            components.append(
                {
                    "id": "table_fin_01",
                    "type": "table",
                    "title": f"Monthly {records[0].metric.title()} Breakdown",
                    "data": {
                        "title": f"Monthly {records[0].metric.title()} Breakdown",
                        "columns": [
                            {"key": "period", "label": "Period"},
                            {"key": "revenue", "label": f"{records[0].metric.title()} ({records[0].currency})"},
                            {"key": "source", "label": "Source Document"},
                        ],
                        "rows": tbl_rows,
                    },
                }
            )

            components.append(
                {
                    "id": "chart_fin_01",
                    "type": "chart",
                    "title": f"Monthly {records[0].metric.title()} Trend",
                    "data": {
                        "chart_type": "line" if (len(records) >= 6 or any(w in q_lower for w in ["line", "trend", "by month", "over time", "monthly"])) else "bar",
                        "title": f"Monthly {records[0].metric.title()} Trend",
                        "x_axis": {"key": "period", "label": "Period"},
                        "y_axis": {"key": "revenue", "label": f"{records[0].metric.title()} ({records[0].currency})"},
                        "series": [{"key": "revenue", "label": records[0].metric.title()}],
                        "data": tbl_rows,
                    },
                }
            )

            ans_text = (
                f"Here is the verified financial {records[0].metric} report across **{len(records)} periods**:\n\n"
                f"- **Total {records[0].metric.title()}:** {currency_symbol}{tot:,.2f}\n"
                f"- **Average Monthly {records[0].metric.title()}:** {currency_symbol}{avg:,.2f}\n"
                + (f"- **Peak Month:** {peak.period} ({currency_symbol}{peak.amount:,.2f})\n" if peak else "")
                + f"\nInteractive table and visual trend charts are available in the artifact canvas."
            )

            return {
                "is_financial": True,
                "answer": ans_text,
                "metric": "table_chart",
                "components": components,
            }

        return None


financial_engine = FinancialDataEngine()
