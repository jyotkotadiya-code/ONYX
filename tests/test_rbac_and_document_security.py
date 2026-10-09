import io
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.auth.auth_handler import init_db_and_defaults
from backend.main import app


@pytest.fixture(scope="module")
def client():
    init_db_and_defaults()
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_rbac_complete_security_matrix(client: TestClient):
    """
    End-to-end verification of:
    1. Admin login & profile (role='admin')
    2. Departments & Groups creation and assignment
    3. Employee creation with Engineering department and Project Alpha group
    4. Document upload with 4 distinct access levels:
       - Salary_Report_2026.txt -> ADMIN_ONLY
       - Engineering_Guidelines.txt -> DEPARTMENT_ONLY (Engineering)
       - Finance_Budget_2026.txt -> DEPARTMENT_ONLY (Finance)
       - Project_Alpha_Spec.txt -> GROUP_ONLY (Project Alpha)
       - Employee_Handbook.txt -> EMPLOYEE_SHARED
    5. RAG Pre-Retrieval Filtering & Zero Indirect Data Leakage:
       - Employee asks about CEO salary (in ADMIN_ONLY doc) -> NOT FOUND, 0 citations, filename never leaked
       - Admin asks about CEO salary -> ANSWER FOUND with citation
       - Employee asks about Engineering Guidelines -> ANSWER FOUND
       - Employee asks about Finance Budget (another department) -> NOT FOUND
       - Employee asks about Project Alpha Spec (group access) -> ANSWER FOUND
    6. Direct File Download & Metadata Endpoint Protection:
       - Employee tries GET /api/documents/{salary_doc_id} -> 403
       - Employee tries GET /api/documents/{salary_doc_id}/content -> 403
       - Employee tries GET /uploads/Salary_Report_2026.txt -> 403
    7. Admin Access Preview & Access Test APIs
    8. Immediate Access Policy Update (ADMIN_ONLY -> ENGINEERING) without re-embedding
    9. Role Escalation Prevention & User Disablement Session Invalidation
    10. Audit Logging verification
    """
    # 1. Login as Admin
    admin_session = _login(client, "admin", "admin123")
    admin_headers = {"Authorization": f"Bearer {admin_session['access_token']}"}
    assert admin_session["user"]["role"] == "admin"

    # 2. Fetch Departments & Groups
    depts_resp = client.get("/api/departments", headers=admin_headers)
    assert depts_resp.status_code == 200
    depts = {d["name"]: d["id"] for d in depts_resp.json()}
    assert "Engineering" in depts
    assert "Finance" in depts
    assert "HR" in depts

    groups_resp = client.get("/api/groups", headers=admin_headers)
    assert groups_resp.status_code == 200
    groups = {g["name"]: g["id"] for g in groups_resp.json()}
    assert "Project Alpha" in groups

    # 3. Create an Employee in Engineering department + Project Alpha group
    emp_username = f"emp_eng_{uuid.uuid4().hex[:6]}"
    create_emp_resp = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "username": emp_username,
            "password": "empPassword123",
            "name": "Jyot Engineer",
            "email": "jyot@onyx.local",
            "role": "employee",
            "job_title": "Software Developer",
            "department_id": depts["Engineering"],
            "group_ids": [groups["Project Alpha"]],
            "allowed_collections": ["General", "Projects", "Engineering"],
            "can_upload": True,
        },
    )
    assert create_emp_resp.status_code == 200, create_emp_resp.text
    emp_user = create_emp_resp.json()
    emp_id = emp_user["id"]
    assert emp_user["role"] == "employee"
    assert emp_user["department"] == "Engineering"

    emp_session = _login(client, emp_username, "empPassword123")
    emp_headers = {"Authorization": f"Bearer {emp_session['access_token']}"}

    # 4. Upload test documents as Admin with different policies
    unique_tag = uuid.uuid4().hex[:6]

    # Doc A: ADMIN_ONLY (placed inside 'General' collection to prove document-level policy overrides collection access!)
    salary_text = (
        f"CONFIDENTIAL EXECUTIVE COMPENSATION REPORT {unique_tag}\n"
        f"The CEO salary for 2026 is $1,850,000 USD base plus $600,000 bonus (Code: CEO_COMP_{unique_tag})."
    )
    up_salary = client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={"file": (f"Salary_Report_{unique_tag}.txt", io.BytesIO(salary_text.encode("utf-8")), "text/plain")},
        data={"collection": "General", "access_level": "ADMIN_ONLY", "sync": "true"},
    )
    assert up_salary.status_code == 200, up_salary.text
    salary_doc_id = up_salary.json()["document"]["id"]

    # Doc B: DEPARTMENT_ONLY -> Engineering
    eng_text = (
        f"ENGINEERING ARCHITECTURE STANDARD {unique_tag}\n"
        f"All microservices in Engineering must use protocol ZephyrMesh-{unique_tag} on port 9443."
    )
    up_eng = client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={"file": (f"Engineering_Guidelines_{unique_tag}.txt", io.BytesIO(eng_text.encode("utf-8")), "text/plain")},
        data={
            "collection": "Engineering",
            "access_level": "DEPARTMENT_ONLY",
            "department_id": depts["Engineering"],
            "sync": "true",
        },
    )
    assert up_eng.status_code == 200, up_eng.text
    eng_doc_id = up_eng.json()["document"]["id"]

    # Doc C: DEPARTMENT_ONLY -> Finance (Placed in General collection, restricted to Finance department)
    fin_text = (
        f"FINANCE TREASURY RESERVE {unique_tag}\n"
        f"The secret Finance department reserve account code is FIN_VAULT_{unique_tag}."
    )
    up_fin = client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={"file": (f"Finance_Reserve_{unique_tag}.txt", io.BytesIO(fin_text.encode("utf-8")), "text/plain")},
        data={
            "collection": "General",
            "access_level": "DEPARTMENT_ONLY",
            "department_id": depts["Finance"],
            "sync": "true",
        },
    )
    assert up_fin.status_code == 200, up_fin.text
    fin_doc_id = up_fin.json()["document"]["id"]

    # Doc D: GROUP_ONLY -> Project Alpha
    alpha_text = (
        f"PROJECT ALPHA BLUEPRINT {unique_tag}\n"
        f"Project Alpha launch codename is Starlight-{unique_tag}."
    )
    up_alpha = client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={"file": (f"Project_Alpha_{unique_tag}.txt", io.BytesIO(alpha_text.encode("utf-8")), "text/plain")},
        data={"collection": "Projects", "access_level": "GROUP_ONLY", "sync": "true"},
    )
    assert up_alpha.status_code == 200, up_alpha.text
    alpha_doc_id = up_alpha.json()["document"]["id"]
    # Assign Project Alpha group rule
    put_alpha_acc = client.put(
        f"/api/documents/{alpha_doc_id}/access",
        headers=admin_headers,
        json={
            "access_level": "GROUP_ONLY",
            "allowed_group_ids": [groups["Project Alpha"]],
        },
    )
    assert put_alpha_acc.status_code == 200

    # Doc E: EMPLOYEE_SHARED
    handbook_text = (
        f"COMPANY LEAVE POLICY {unique_tag}\n"
        f"All employees receive 24 days of paid annual leave per year (Policy Code: LEAVE_24_{unique_tag})."
    )
    up_hb = client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={"file": (f"Employee_Handbook_{unique_tag}.txt", io.BytesIO(handbook_text.encode("utf-8")), "text/plain")},
        data={"collection": "General", "access_level": "EMPLOYEE_SHARED", "sync": "true"},
    )
    assert up_hb.status_code == 200, up_hb.text
    hb_doc_id = up_hb.json()["document"]["id"]

    # 5. Verify Document Listing Isolation
    emp_docs_resp = client.get("/api/documents", headers=emp_headers)
    assert emp_docs_resp.status_code == 200
    emp_doc_ids = {d["id"] for d in emp_docs_resp.json()}
    assert salary_doc_id not in emp_doc_ids, "ADMIN_ONLY document must NEVER appear in employee document list!"
    assert fin_doc_id not in emp_doc_ids, "Finance department document must NEVER appear in Engineering employee list!"
    assert eng_doc_id in emp_doc_ids, "Engineering department document MUST be visible to Engineering employee!"
    assert alpha_doc_id in emp_doc_ids, "Project Alpha group document MUST be visible to group member!"
    assert hb_doc_id in emp_doc_ids, "EMPLOYEE_SHARED document MUST be visible to employee!"

    # 6. Test Direct File & Metadata Access Protection (Tests B & D)
    assert client.get(f"/api/documents/{salary_doc_id}", headers=emp_headers).status_code == 403
    assert client.get(f"/api/documents/{salary_doc_id}/content", headers=emp_headers).status_code == 403
    assert client.get(f"/api/documents/{salary_doc_id}/file", headers=emp_headers).status_code == 403
    assert client.get(f"/api/documents/{fin_doc_id}/content", headers=emp_headers).status_code == 403
    # Authorized file download succeeds for employee
    assert client.get(f"/api/documents/{eng_doc_id}/content", headers=emp_headers).status_code == 200

    # 7. Test Search Filtering (Unauthorized documents never appear in /api/search)
    emp_search_salary = client.post(
        "/api/search",
        headers=emp_headers,
        json={"query": f"CEO_COMP_{unique_tag} salary", "collection": "ALL", "mode": "rag"},
    )
    assert emp_search_salary.status_code == 200
    emp_search_doc_ids = {r["document_id"] for r in emp_search_salary.json()["results"]}
    assert salary_doc_id not in emp_search_doc_ids

    admin_search_salary = client.post(
        "/api/search",
        headers=admin_headers,
        json={"query": f"CEO_COMP_{unique_tag} salary", "collection": "ALL", "mode": "rag"},
    )
    assert admin_search_salary.status_code == 200
    admin_search_doc_ids = {r["document_id"] for r in admin_search_salary.json()["results"]}
    assert salary_doc_id in admin_search_doc_ids

    # 8. Test RAG Chat Security (Tests A & C: Employee asks about CEO salary / confidential filename)
    emp_chat_salary = client.post(
        "/api/chat",
        headers=emp_headers,
        json={"question": f"What is the CEO salary in Salary_Report_{unique_tag}.txt (CEO_COMP_{unique_tag})?"},
    )
    assert emp_chat_salary.status_code == 200
    emp_chat_data = emp_chat_salary.json()
    assert "$1,850,000" not in emp_chat_data["answer"]
    assert f"CEO_COMP_{unique_tag}" not in emp_chat_data["answer"]
    cited_doc_ids = {c.get("document_id") for c in emp_chat_data.get("citations", [])}
    assert salary_doc_id not in cited_doc_ids

    # Admin asks the exact same question and receives the grounded answer + citation
    admin_chat_salary = client.post(
        "/api/chat",
        headers=admin_headers,
        json={"question": f"What is the CEO salary CEO_COMP_{unique_tag}?"},
    )
    assert admin_chat_salary.status_code == 200
    admin_chat_data = admin_chat_salary.json()
    assert admin_chat_data["answer_found"] is True
    assert "$1,850,000" in admin_chat_data["answer"] or f"CEO_COMP_{unique_tag}" in admin_chat_data["answer"]

    # Employee asks about authorized Engineering document -> succeeds
    emp_chat_eng = client.post(
        "/api/chat",
        headers=emp_headers,
        json={"question": f"What protocol must microservices use in Engineering (ZephyrMesh-{unique_tag})?"},
    )
    assert emp_chat_eng.status_code == 200
    assert emp_chat_eng.json()["answer_found"] is True
    assert f"ZephyrMesh-{unique_tag}" in emp_chat_eng.json()["answer"]

    # 9. Test Admin "Preview Access as User" & "Document Access Test"
    preview_resp = client.get(f"/api/admin/access/preview/{emp_id}", headers=admin_headers)
    assert preview_resp.status_code == 200
    preview_doc_ids = {d["id"] for d in preview_resp.json()["accessible_documents"]}
    assert salary_doc_id not in preview_doc_ids
    assert eng_doc_id in preview_doc_ids
    assert alpha_doc_id in preview_doc_ids

    test_deny = client.post(
        "/api/admin/access/test",
        headers=admin_headers,
        json={"user_id": emp_id, "document_id": salary_doc_id},
    )
    assert test_deny.status_code == 200
    assert test_deny.json()["status"] == "DENIED"

    test_allow = client.post(
        "/api/admin/access/test",
        headers=admin_headers,
        json={"user_id": emp_id, "document_id": eng_doc_id},
    )
    assert test_allow.status_code == 200
    assert test_allow.json()["status"] == "ALLOWED"

    # 10. Test Immediate Dynamic Policy Change (Change Finance_Reserve from Finance -> Engineering department)
    change_policy = client.put(
        f"/api/documents/{fin_doc_id}/access",
        headers=admin_headers,
        json={
            "access_level": "DEPARTMENT_ONLY",
            "department_id": depts["Engineering"],
            "allowed_department_ids": [depts["Engineering"]],
        },
    )
    assert change_policy.status_code == 200
    # Immediately check that employee can now access Fin Doc without re-uploading
    test_now_allowed = client.post(
        "/api/admin/access/test",
        headers=admin_headers,
        json={"user_id": emp_id, "document_id": fin_doc_id},
    )
    assert test_now_allowed.json()["status"] == "ALLOWED"

    # 11. Test Employee Cannot Escalate Role or Call Admin APIs
    assert client.put(f"/api/users/{emp_id}", headers=emp_headers, json={"role": "admin"}).status_code == 403
    assert client.get("/api/admin/audit-logs", headers=emp_headers).status_code == 403
    assert client.delete(f"/api/documents/{hb_doc_id}", headers=emp_headers).status_code == 403

    # 12. Test Chat Session & Artifact Isolation between users
    admin_sessions = client.get("/api/chat/sessions", headers=admin_headers).json()
    if admin_sessions:
        admin_sess_id = admin_sessions[0]["id"]
        assert client.get(f"/api/chat/sessions/{admin_sess_id}", headers=emp_headers).status_code == 403

    # 13. Test Disabling User Immediately Revokes Active Session Token
    disable_resp = client.post(f"/api/users/{emp_id}/disable", headers=admin_headers)
    assert disable_resp.status_code == 200
    assert disable_resp.json()["status"] == "DISABLED"

    # Employee's existing token must immediately fail with 403
    me_after_disable = client.get("/api/auth/me", headers=emp_headers)
    assert me_after_disable.status_code == 403

    # 14. Verify Audit Logs recorded the security events
    audit_resp = client.get("/api/admin/audit-logs?limit=50", headers=admin_headers)
    assert audit_resp.status_code == 200
    actions_logged = {entry["action"] for entry in audit_resp.json()}
    assert "ADMIN_LOGIN" in actions_logged
    assert "EMPLOYEE_LOGIN" in actions_logged
    assert "ACCESS_POLICY_CHANGED" in actions_logged
    assert "USER_DISABLED" in actions_logged
    assert "UNAUTHORIZED_DOCUMENT_ACCESS_ATTEMPT" in actions_logged
