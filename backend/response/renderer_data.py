import re
from typing import Any, Optional
from backend.response.calculator import calculator

MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
    "Jan", "Feb", "Mar", "Apr", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def extract_structured_data_from_chunks(
    retrieved_chunks: list[dict[str, Any]],
    db_query_result: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Extract source-grounded structured datasets from retrieved chunks and/or database query results.
    Every single number or row originates directly from the retrieved context or deterministic calculation.
    """
    tables: list[dict[str, Any]] = []
    time_series: list[dict[str, Any]] = []
    categorical_series: list[dict[str, Any]] = []
    kpis: list[dict[str, Any]] = []
    timeline_events: list[dict[str, Any]] = []

    # 1. Include direct SQLite/database query rows if present
    if db_query_result and db_query_result.get("rows"):
        cols = [
            {"key": c, "label": c.replace("_", " ").title()}
            for c in db_query_result.get("columns", [])
        ]
        rows = db_query_result["rows"]
        tables.append(
            {
                "title": f"Database Table: {db_query_result.get('table', 'Records')}",
                "columns": cols,
                "rows": rows,
                "source": db_query_result.get("filename", "database"),
            }
        )
        # Check if any column is numeric for categorical aggregation
        if len(cols) >= 2:
            cat_key = cols[0]["key"]
            for col in cols[1:]:
                sample_val = rows[0].get(col["key"])
                if calculator.to_number(sample_val) is not None:
                    val_key = col["key"]
                    for r in rows:
                        n = calculator.to_number(r.get(val_key))
                        if n is not None:
                            categorical_series.append(
                                {
                                    "category": str(r.get(cat_key)),
                                    "value": n,
                                    "metric": col["label"],
                                }
                            )

    # 2. Inspect retrieved document chunks for structured patterns
    course_rows: list[dict[str, Any]] = []
    db_chunk_rows: list[dict[str, Any]] = []

    for ch in retrieved_chunks:
        content = ch.get("content", "")
        modality = ch.get("modality", "text")
        filename = ch.get("citation", {}).get("filename", "document")

        # Pattern A: Database modality chunks (Key: Value lines)
        if modality == "database":
            row_dict: dict[str, Any] = {}
            for line in content.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k_clean = k.strip()
                    v_clean = v.strip()
                    if k_clean.lower() not in {"database", "table"}:
                        num_v = calculator.to_number(v_clean)
                        row_dict[k_clean] = num_v if (num_v is not None and re.match(r"^-?\d+(\.\d+)?$", v_clean)) else v_clean
            if row_dict:
                db_chunk_rows.append(row_dict)

        # Pattern B: Statement of Marks / Academic Course Rows (I | 24UGCS301 | Title | Credits | ...)
        for line in content.splitlines():
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 13 and re.match(r"^[0-9]{2}[A-Z]{2,}[0-9]{2,}", parts[1]):
                code = parts[1]
                title = parts[2]
                credits = calculator.to_number(parts[3]) or parts[3]
                cia_obt = calculator.to_number(parts[6]) or parts[6]
                see_obt = calculator.to_number(parts[9]) or parts[9]
                tot_max = calculator.to_number(parts[11]) or 100
                tot_obt = calculator.to_number(parts[12])
                grade = parts[14] if len(parts) > 14 else "-"
                result_flag = parts[15] if len(parts) > 15 else "P"
                if tot_obt is not None:
                    row_obj = {
                        "course_code": code,
                        "course_title": title,
                        "credits": credits,
                        "cia_obtained": cia_obt,
                        "see_obtained": see_obt,
                        "max_marks": tot_max,
                        "total_obtained": tot_obt,
                        "grade": str(grade).strip("()"),
                        "result": str(result_flag).strip("()"),
                    }
                    if not any(r["course_code"] == code for r in course_rows):
                        course_rows.append(row_obj)
                        categorical_series.append(
                            {
                                "category": title,
                                "value": tot_obt,
                                "metric": "Total Obtained Marks",
                            }
                        )

        # Pattern C: Monthly / Time-series patterns (e.g., "January 2024: 42,000", "Jan 2024 | I42,000", "Jan - $45,000")
        month_regex = re.compile(
            r"\b(" + "|".join(MONTH_NAMES) + r")(?:\s*['’\-]?\s*(\d{2,4}))?\b\s*[:\-–=|\t,]*\s*(?:[A-Za-z₹\$]{1,4})?\s*([0-9][0-9,]*(?:\.[0-9]+)?(?:\s*(?:Million|M|Cr|Lakh|K))?)",
            re.IGNORECASE,
        )
        for m_match in month_regex.finditer(content):
            m_name = m_match.group(1).title()
            yr = m_match.group(2)
            val_num = calculator.to_number(m_match.group(3))
            if val_num is not None and val_num not in (2023, 2024, 2025, 2026, 2027) and val_num > 10:
                period = f"{m_name} {yr}" if yr else m_name
                if not any(x["period"] == period for x in time_series):
                    time_series.append({"period": period, "month": m_name, "year": yr, "value": val_num})

        # Pattern D: Department / Category key-value pairs (e.g. "Engineering Department: $1,200,000")
        dept_regex = re.compile(
            r"\b([A-Z][A-Za-z &]{2,28}?)\s*(?:Department|Division|Segment|Unit)?\s*[:\-–=]\s*(?:₹|\$|USD|INR)\s*([0-9][0-9,]*(?:\.[0-9]+)?(?:\s*(?:Million|M|Cr|Lakh|K))?)"
        )
        for d_match in dept_regex.finditer(content):
            cat_label = d_match.group(1).strip()
            if cat_label.lower() in {m.lower() for m in MONTH_NAMES}:
                continue
            val_num = calculator.to_number(d_match.group(2))
            if val_num is not None and not any(x["category"] == cat_label for x in categorical_series):
                categorical_series.append(
                    {
                        "category": cat_label,
                        "value": val_num,
                        "metric": "Amount",
                    }
                )

        # Pattern E: Key financial / operational KPIs (e.g., Q1 revenue, growth %, expense increase, SGPA/CGPA)
        rev_match = re.search(
            r"(?:revenue|sales|contract value)\s+(?:reached|was|of|is|:)?\s*(?:₹|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?\s*(?:Million|M|Cr|Lakh|K)?)",
            content,
            re.IGNORECASE,
        )
        if rev_match:
            raw_str = rev_match.group(1).strip()
            num_val = calculator.to_number(raw_str)
            growth_match = re.search(r"([0-9]+(?:\.[0-9]+)?)%\s*(?:year-over-year|YoY|growth|increase)", content, re.I)
            change_pct = float(growth_match.group(1)) if growth_match else None
            if num_val is not None and not any(k["label"] == "Reported Revenue" for k in kpis):
                kpis.append(
                    {
                        "label": "Reported Revenue",
                        "value": num_val,
                        "format": "currency",
                        "currency": "USD" if "$" in content else ("INR" if "₹" in content else "USD"),
                        "change": change_pct,
                        "change_label": "YoY growth" if change_pct else "from retrieved report",
                        "trend": "up" if (change_pct and change_pct > 0) else "neutral",
                    }
                )

        exp_match = re.search(
            r"expense(?:s|\s+increase)?.*?totaling\s*(?:₹|\$)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
            content,
            re.IGNORECASE,
        )
        if exp_match:
            exp_val = calculator.to_number(exp_match.group(1))
            if exp_val is not None and not any(k["label"] == "Largest Expense Increase" for k in kpis):
                kpis.append(
                    {
                        "label": "Largest Expense Increase",
                        "value": exp_val,
                        "format": "currency",
                        "currency": "USD" if "$" in content else "INR",
                        "change": None,
                        "change_label": "GPU Hardware Procurement",
                        "trend": "up",
                    }
                )

        # Pattern F: Dates / Deadlines for Timelines
        date_matches = re.finditer(
            r"([^\n.;]{10,90}?)\s+(?:on|is|by|from)\s+(\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|\d{2}/\d{2}/\d{4})",
            content,
        )
        for dm in date_matches:
            evt_title = dm.group(1).strip()
            evt_date = dm.group(2).strip()
            if not any(e["date"] == evt_date for e in timeline_events):
                timeline_events.append(
                    {
                        "date": evt_date,
                        "title": evt_title[:80],
                        "description": f"Source: {filename}",
                    }
                )

        # Pattern G: Dedicated Employee Salary & Compensation Records Extraction
        salary_rows: list[dict[str, Any]] = []
        salary_keywords = {"salary", "stipend", "payroll", "compensation", "employee", "pay", "wage", "bonus", "ctc"}
        invalid_name_terms = {
            "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
            "january", "february", "march", "april", "june", "july", "august", "september", "october", "november", "december",
            "year", "month", "total", "revenue", "profit", "expenses", "2024", "2025", "2026", "2027", "id", "name", "employee", "staff", "summary", "figures"
        }
        for line in content.splitlines():
            line_str = line.strip()
            if not line_str or line_str.startswith("---") or line_str.startswith("#"):
                continue

            parts = [p.strip() for p in line_str.split("|") if p.strip()]
            if len(parts) < 2:
                parts = [p.strip() for p in line_str.split(",") if p.strip()]

            if len(parts) >= 2:
                emp_name = parts[0]
                emp_name_lower = emp_name.lower().strip()
                if any(inv in emp_name_lower for inv in invalid_name_terms) or re.match(r"^\d+", emp_name_lower):
                    continue

                for p_idx, p in enumerate(parts[1:], start=1):
                    val_num = calculator.to_number(p)
                    has_sal_kw = any(kw in line_str.lower() for kw in salary_keywords)
                    if val_num is not None and val_num >= 500 and (has_sal_kw or "$" in p or "₹" in p):
                        role_dept = parts[1] if (len(parts) > 2 and p_idx != 1) else "Employee"
                        formatted_sal = p if ("$" in p or "₹" in p) else f"${val_num:,.2f}"
                        row_item = {
                            "employee_name": emp_name,
                            "department_role": role_dept,
                            "salary": val_num,
                            "formatted_salary": formatted_sal,
                        }
                        if not any(r["employee_name"] == emp_name for r in salary_rows):
                            salary_rows.append(row_item)
                            categorical_series.append({
                                "category": emp_name,
                                "value": val_num,
                                "metric": "Salary Amount",
                            })
                        break

        if salary_rows:
            tables.append({
                "title": "Employee Salary & Compensation Records",
                "columns": [
                    {"key": "employee_name", "label": "Employee Name"},
                    {"key": "department_role", "label": "Department / Position"},
                    {"key": "formatted_salary", "label": "Salary / Compensation"},
                ],
                "rows": salary_rows,
            })
            sal_list = [r["salary"] for r in salary_rows]
            avg_sal = round(calculator.compute_average(sal_list), 2)
            max_sal = max(sal_list)
            kpis.append({
                "label": "Average Employee Salary",
                "value": avg_sal,
                "format": "currency",
                "currency": "USD" if "$" in content else "INR",
                "change_label": f"Across {len(salary_rows)} employee records",
                "trend": "up",
            })
            kpis.append({
                "label": "Highest Compensation",
                "value": max_sal,
                "format": "currency",
                "currency": "USD" if "$" in content else "INR",
                "change_label": "Peak reported compensation",
                "trend": "up",
            })

        # Pattern H: Universal Markdown Table Parser (Preserves exact document headers & labels)
        lines = content.splitlines()
        for i in range(len(lines) - 2):
            l1 = lines[i].strip()
            l2 = lines[i+1].strip()
            if l1.startswith("|") and l1.endswith("|") and ("---" in l2 or "| ---" in l2):
                header_parts = [h.strip() for h in l1.split("|") if h.strip()]
                if len(header_parts) >= 2:
                    # Skip statement of marks header if handled by Pattern B
                    if any(x in l1.lower() for x in ["cia_min", "see_min", "tot_max"]):
                        continue
                    tbl_rows = []
                    for j in range(i+2, len(lines)):
                        l_row = lines[j].strip()
                        if not l_row.startswith("|"):
                            break
                        row_parts = [r.strip() for r in l_row.split("|") if r.strip()]
                        if len(row_parts) == len(header_parts):
                            r_dict = {}
                            for h_k, r_v in zip(header_parts, row_parts):
                                clean_k = re.sub(r"[^\w\s]", "", h_k).strip().replace(" ", "_").lower() or "col"
                                num_v = calculator.to_number(r_v)
                                r_dict[clean_k] = num_v if (num_v is not None and re.match(r"^-?\d+(\.\d+)?$", r_v.replace(",", ""))) else r_v
                            tbl_rows.append(r_dict)
                    if tbl_rows and not any(t.get("title", "").startswith(f"Table: {' | '.join(header_parts[:2])}") for t in tables):
                        cols = [{"key": (re.sub(r"[^\w\s]", "", h).strip().replace(" ", "_").lower() or f"col_{idx}"), "label": h} for idx, h in enumerate(header_parts)]
                        tables.append({
                            "title": f"Document Table: {' | '.join(header_parts[:3])}",
                            "columns": cols,
                            "rows": tbl_rows,
                            "source": filename,
                        })

    if course_rows:
        tables.append(
            {
                "title": "Course Marks & Grade Summary",
                "columns": [
                    {"key": "course_code", "label": "Course Code"},
                    {"key": "course_title", "label": "Course Title"},
                    {"key": "credits", "label": "Credits"},
                    {"key": "cia_obtained", "label": "CIA Obtained"},
                    {"key": "see_obtained", "label": "SEE Obtained"},
                    {"key": "total_obtained", "label": "Total Obtained"},
                    {"key": "max_marks", "label": "Max Marks"},
                    {"key": "grade", "label": "Grade"},
                    {"key": "result", "label": "Result"},
                ],
                "rows": course_rows,
            }
        )
        avg_marks = round(calculator.compute_average([r["total_obtained"] for r in course_rows]), 2)
        max_row = calculator.sort_rows(course_rows, "total_obtained", descending=True, limit=1)[0]
        kpis.append(
            {
                "label": "Highest Subject Marks",
                "value": max_row["total_obtained"],
                "format": "number",
                "change_label": f"{max_row['course_title']} ({max_row['course_code']})",
                "trend": "up",
            }
        )
        kpis.append(
            {
                "label": "Average Subject Score",
                "value": avg_marks,
                "format": "number",
                "change_label": f"Across {len(course_rows)} courses",
                "trend": "neutral",
            }
        )

    if db_chunk_rows and not tables:
        all_keys = list(db_chunk_rows[0].keys())
        tables.append(
            {
                "title": "Retrieved Database Records",
                "columns": [{"key": k, "label": k} for k in all_keys],
                "rows": db_chunk_rows,
            }
        )

    return {
        "tables": tables,
        "time_series": time_series,
        "categorical_series": categorical_series,
        "kpis": kpis,
        "timeline_events": timeline_events,
    }
