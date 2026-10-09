"""
Evaluation Suite for the 100% Local Multimodal RAG Knowledge System.
Creates sample evaluation documents in `tests/evaluation/` and evaluates:
- Easy questions
- Multi-document questions
- Exact-match questions
- Negative (unanswerable) questions
- Summarization questions
- Cross-document questions

Reports:
- Retrieval accuracy
- Answer accuracy
- Citation accuracy
- Unsupported-answer (hallucination) rate
- Average latency
"""

import io
import json
import sys
import time
from pathlib import Path
import docx
import fitz

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi.testclient import TestClient
from backend.auth.auth_handler import init_db_and_defaults
from backend.llm.llm_client import NOT_FOUND_RESPONSE
from backend.main import app


EVAL_DIR = ROOT_DIR / "tests" / "evaluation"


def build_evaluation_dataset() -> list[dict]:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    # 1. PDF Document: Engineering & Project Roadmap
    pdf_path = EVAL_DIR / "engineering_roadmap_2026.pdf"
    pdf_doc = fitz.open()
    p1 = pdf_doc.new_page()
    p1.insert_text(
        (50, 70),
        "ONYX Engineering Roadmap & Architecture 2026\n\n"
        "Project Titan is our next-generation local encryption engine scheduled for release on 15 November 2026.\n"
        "The primary encryption cipher used by Project Titan is AES-256-GCM with Argon2id key derivation.\n"
        "All production servers are hosted in the Mumbai Tier-4 Data Center (Facility Code: BOM-DC04).\n"
        "Refund Policy: Enterprise licenses include a 30-day unconditional money-back guarantee.",
        fontsize=11,
    )
    pdf_doc.save(str(pdf_path))
    pdf_doc.close()

    # 2. DOCX Document: Q1 Financial & Operations Report
    docx_path = EVAL_DIR / "q1_financial_operations.docx"
    d = docx.Document()
    d.add_heading("Q1 2026 Financial & Operations Report", level=1)
    d.add_paragraph(
        "In Q1 2026, total company revenue was $4.85 Million USD, driven by strong adoption of Project Titan."
    )
    d.add_heading("Expense Breakdown", level=2)
    d.add_paragraph(
        "The largest expense increase in Q1 2026 was caused by purchasing local GPU servers ($620,000) for the Mumbai BOM-DC04 facility."
    )
    d.save(str(docx_path))

    # 3. XML Document: Hardware Inventory & Support Contacts
    xml_path = EVAL_DIR / "hardware_inventory.xml"
    xml_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<inventory>
    <asset id="SRV-9082">
        <hostname>onyx-gpu-node-01</hostname>
        <location>BOM-DC04 Rack 14</location>
        <custodian>Vikramaditya Rao</custodian>
        <serial_number>SN-RTX-998120-IN</serial_number>
    </asset>
</inventory>
""",
        encoding="utf-8",
    )

    questions = [
        {
            "id": "Q1",
            "category": "easy",
            "question": "When is Project Titan scheduled for release and what encryption cipher does it use?",
            "expected_keywords": ["15 November 2026", "AES-256-GCM"],
            "expected_sources": ["engineering_roadmap_2026.pdf"],
            "answerable": True,
        },
        {
            "id": "Q2",
            "category": "multi-document",
            "question": "What was our Q1 2026 revenue and what caused the largest expense increase?",
            "expected_keywords": ["4.85 Million", "620,000"],
            "expected_sources": ["q1_financial_operations.docx"],
            "answerable": True,
        },
        {
            "id": "Q3",
            "category": "exact-match",
            "question": "What is the serial number and hostname of asset SRV-9082?",
            "expected_keywords": ["SN-RTX-998120-IN", "onyx-gpu-node-01"],
            "expected_sources": ["hardware_inventory.xml"],
            "answerable": True,
        },
        {
            "id": "Q4",
            "category": "cross-document",
            "question": "Which data center facility code hosts Project Titan and the new GPU servers?",
            "expected_keywords": ["BOM-DC04"],
            "expected_sources": ["engineering_roadmap_2026.pdf", "q1_financial_operations.docx"],
            "answerable": True,
        },
        {
            "id": "Q5",
            "category": "summarization",
            "question": "Summarize our Enterprise refund policy and Q1 2026 financial performance.",
            "expected_keywords": ["30-day", "4.85 Million"],
            "expected_sources": ["engineering_roadmap_2026.pdf", "q1_financial_operations.docx"],
            "answerable": True,
        },
        {
            "id": "Q6",
            "category": "negative",
            "question": "What is the stock ticker symbol of QuantumHyperDrive Corp on the Tokyo Stock Exchange?",
            "expected_keywords": [],
            "expected_sources": [],
            "answerable": False,
        },
        {
            "id": "Q7",
            "category": "negative",
            "question": "Who won the intergalactic chess tournament in 3045?",
            "expected_keywords": [],
            "expected_sources": [],
            "answerable": False,
        },
    ]

    dataset_file = EVAL_DIR / "evaluation_questions.json"
    dataset_file.write_text(json.dumps(questions, indent=2), encoding="utf-8")
    return questions


def run_evaluation() -> dict:
    init_db_and_defaults()
    client = TestClient(app)

    login_resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    questions = build_evaluation_dataset()

    # Upload the evaluation files
    for fname in ["engineering_roadmap_2026.pdf", "q1_financial_operations.docx", "hardware_inventory.xml"]:
        fpath = EVAL_DIR / fname
        client.post(
            "/api/documents/upload",
            headers=headers,
            files={"file": (fname, fpath.read_bytes(), "application/octet-stream")},
            data={"collection": "General", "sync": "true"},
        )

    retrieval_hits = 0
    answer_hits = 0
    citation_hits = 0
    unsupported_answers = 0
    answerable_count = 0
    negative_count = 0
    latencies_ms: list[float] = []

    print("=" * 72)
    print("  100% LOCAL MULTIMODAL RAG — EVALUATION BENCHMARK")
    print("=" * 72)

    for item in questions:
        t0 = time.perf_counter()
        resp = client.post(
            "/api/chat",
            headers=headers,
            json={"question": item["question"], "collection": "ALL", "mode": "rag", "top_k": 5},
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000
        latencies_ms.append(elapsed_ms)
        data = resp.json()

        answer = data.get("answer", "")
        citations = [c.get("filename", "") for c in data.get("citations", [])]
        retrieved_files = [
            c.get("filename", "")
            for c in data.get("observability", {}).get("retrieved_chunks", [])
        ]

        if item["answerable"]:
            answerable_count += 1
            # Check retrieval accuracy
            ret_ok = any(exp in retrieved_files for exp in item["expected_sources"])
            if ret_ok:
                retrieval_hits += 1

            # Check answer accuracy
            ans_ok = any(kw.lower() in answer.lower() for kw in item["expected_keywords"])
            if ans_ok:
                answer_hits += 1

            # Check citation accuracy
            cit_ok = any(exp in citations for exp in item["expected_sources"])
            if cit_ok:
                citation_hits += 1

            status_str = "PASS" if (ret_ok and ans_ok and cit_ok) else "PARTIAL"
        else:
            negative_count += 1
            # Negative question: must refuse to hallucinate
            refused = (not data.get("answer_found")) or (NOT_FOUND_RESPONSE.lower() in answer.lower())
            if refused:
                answer_hits += 1
                status_str = "PASS (Correctly Refused)"
            else:
                unsupported_answers += 1
                status_str = "FAIL (Hallucinated)"

        print(f"[{item['id']} | {item['category'].upper():14s}] {status_str} ({elapsed_ms:.1f} ms)")
        print(f"   Q: {item['question']}")
        print(f"   A: {answer.splitlines()[0] if answer else ''}...")

    total_q = len(questions)
    ret_acc = (retrieval_hits / max(1, answerable_count)) * 100.0
    ans_acc = (answer_hits / max(1, total_q)) * 100.0
    cit_acc = (citation_hits / max(1, answerable_count)) * 100.0
    unsupported_rate = (unsupported_answers / max(1, negative_count)) * 100.0
    avg_latency = sum(latencies_ms) / max(1, len(latencies_ms))

    summary = {
        "retrieval_accuracy_pct": round(ret_acc, 2),
        "answer_accuracy_pct": round(ans_acc, 2),
        "citation_accuracy_pct": round(cit_acc, 2),
        "unsupported_answer_rate_pct": round(unsupported_rate, 2),
        "average_latency_ms": round(avg_latency, 2),
    }

    print("-" * 72)
    print(f"Retrieval accuracy      : {summary['retrieval_accuracy_pct']:.1f}%")
    print(f"Answer accuracy         : {summary['answer_accuracy_pct']:.1f}%")
    print(f"Citation accuracy       : {summary['citation_accuracy_pct']:.1f}%")
    print(f"Unsupported-answer rate : {summary['unsupported_answer_rate_pct']:.1f}%")
    print(f"Average latency         : {summary['average_latency_ms']:.1f} ms")
    print("=" * 72)

    report_path = EVAL_DIR / "last_evaluation_report.json"
    report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    run_evaluation()
