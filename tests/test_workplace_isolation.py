import io
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str, password: str) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    return resp.json()


def test_workplace_architecture_and_multi_tenant_isolation(client: TestClient):
    """
    End-to-end verification of:
    1. Current Workplace metadata & settings update (PUT /api/workplaces/current)
    2. Creating a second Workplace (Workplace B) with isolated departments, groups, and collections
    3. Employee Invite & Token Activation flow (POST /api/users/invite + POST /api/auth/activate-invite)
    4. Employee Profile & Accessible Knowledge inspection (GET /api/admin/employees/{id}/profile)
    5. Cross-Workplace Isolation:
       - Document uploaded in Workplace B is NEVER visible or retrievable by users in Workplace A
       - Document uploaded in Workplace A is NEVER visible or retrievable by users in Workplace B
    6. Document Archiving & Collection Move (POST /api/documents/{id}/archive, PUT /api/documents/{id}/move)
    7. Employee Access-Aware Empty Response & Workplace Analytics (GET /api/admin/analytics)
    """
    unique_tag = uuid.uuid4().hex[:6]

    # 1. Login as Admin, record the primary default workplace, and create a clean Workplace A
    admin_session = _login(client, "admin", "admin123")
    admin_headers = {"Authorization": f"Bearer {admin_session['access_token']}"}

    all_wps = client.get("/api/workplaces", headers=admin_headers).json()
    default_wp = next((w for w in all_wps if w["name"] in {"ONYX", "ONYX Studio"}), all_wps[0])
    default_wp_id = default_wp["id"]

    create_wp_a = client.post(
        "/api/workplaces",
        headers=admin_headers,
        json={
            "name": f"ONYX Studio {unique_tag}",
            "description": "Design & AI engineering studio",
            "industry": "Technology",
            "switch_to_new": True,
        },
    )
    assert create_wp_a.status_code == 200, create_wp_a.text
    workplace_a = create_wp_a.json()
    workplace_a_id = workplace_a["id"]
    sw_init_a = client.post(f"/api/workplaces/{workplace_a_id}/switch", headers=admin_headers)
    assert sw_init_a.status_code == 200
    admin_headers = {"Authorization": f"Bearer {sw_init_a.json()['access_token']}"}

    # Update Workplace A settings
    upd_wp_resp = client.put(
        "/api/workplaces/current",
        headers=admin_headers,
        json={
            "assistant_name": "ONYX AI",
            "welcome_message": "Ask anything about ONYX Studio policies and projects.",
        },
    )
    assert upd_wp_resp.status_code == 200
    assert upd_wp_resp.json()["assistant_name"] == "ONYX AI"

    # 2. Invite an Employee (Rahul) to Workplace A and Activate via Invite Token
    rahul_username = f"rahul_{unique_tag}"
    inv_resp = client.post(
        "/api/users/invite",
        headers=admin_headers,
        json={
            "name": "Rahul Verma",
            "email": f"rahul_{unique_tag}@onyx.local",
            "username": rahul_username,
            "job_title": "Product Designer",
            "allowed_collections": ["General", "Projects", "Company Policies"],
            "can_upload": False,
        },
    )
    assert inv_resp.status_code == 200, inv_resp.text
    inv_data = inv_resp.json()
    invite_token = inv_data["invite_token"]
    rahul_id = inv_data["user"]["id"]
    assert invite_token

    # Rahul activates his workplace invite
    act_resp = client.post(
        "/api/auth/activate-invite",
        json={"invite_token": invite_token, "password": "rahulPassword123"},
    )
    assert act_resp.status_code == 200, act_resp.text
    rahul_headers = {"Authorization": f"Bearer {act_resp.json()['access_token']}"}
    assert act_resp.json()["user"]["workspace_id"] == workplace_a_id

    # Upload a shared document in Workplace A
    wp_a_text = (
        f"ONYX STUDIO HANDBOOK {unique_tag}\n"
        f"Workplace A secret project codename is AuroraStudio-{unique_tag}."
    )
    up_a = client.post(
        "/api/documents/upload",
        headers=admin_headers,
        files={"file": (f"Onyx_Handbook_{unique_tag}.txt", io.BytesIO(wp_a_text.encode("utf-8")), "text/plain")},
        data={"collection": "General", "access_level": "EMPLOYEE_SHARED", "sync": "true"},
    )
    assert up_a.status_code == 200, up_a.text
    doc_a_id = up_a.json()["document"]["id"]

    # Inspect Rahul's Employee Profile as Admin
    prof_resp = client.get(f"/api/admin/employees/{rahul_id}/profile", headers=admin_headers)
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()
    assert prof_data["employee"]["username"] == rahul_username
    accessible_doc_ids = {d["id"] for d in prof_data["accessible_documents"]}
    assert doc_a_id in accessible_doc_ids

    # 3. Create Workplace B ("Apex Robotics") and Switch Admin to Workplace B
    create_wp_b = client.post(
        "/api/workplaces",
        headers=admin_headers,
        json={
            "name": f"Apex Robotics {unique_tag}",
            "slug": f"apex-robotics-{unique_tag}",
            "description": "Autonomous robotics R&D workplace",
            "industry": "Robotics",
        },
    )
    assert create_wp_b.status_code == 200, create_wp_b.text
    workplace_b = create_wp_b.json()
    workplace_b_id = workplace_b["id"]
    assert workplace_b_id != workplace_a_id

    # Switch Admin into Workplace B
    sw_b = client.post(f"/api/workplaces/{workplace_b_id}/switch", headers=admin_headers)
    assert sw_b.status_code == 200
    admin_b_headers = {"Authorization": f"Bearer {sw_b.json()['access_token']}"}

    # Upload a document in Workplace B
    wp_b_text = (
        f"APEX ROBOTICS BLUEPRINT {unique_tag}\n"
        f"Workplace B confidential actuator frequency is HyperDrive-{unique_tag}-990Hz."
    )
    up_b = client.post(
        "/api/documents/upload",
        headers=admin_b_headers,
        files={"file": (f"Apex_Blueprint_{unique_tag}.txt", io.BytesIO(wp_b_text.encode("utf-8")), "text/plain")},
        data={"collection": "General", "access_level": "EMPLOYEE_SHARED", "sync": "true"},
    )
    assert up_b.status_code == 200, up_b.text
    doc_b_id = up_b.json()["document"]["id"]

    # Create an Employee (Priya) in Workplace B
    priya_username = f"priya_b_{unique_tag}"
    create_priya = client.post(
        "/api/users",
        headers=admin_b_headers,
        json={
            "username": priya_username,
            "password": "priyaPassword123",
            "name": "Priya Nair",
            "role": "employee",
            "job_title": "Robotics Engineer",
            "allowed_collections": ["General", "Projects"],
            "can_upload": False,
        },
    )
    assert create_priya.status_code == 200, create_priya.text
    priya_session = _login(client, priya_username, "priyaPassword123")
    priya_headers = {"Authorization": f"Bearer {priya_session['access_token']}"}

    # 4. Verify Strict Cross-Workplace Isolation (Workplace A vs Workplace B)
    # Rahul (Workplace A) must NEVER see or access Workplace B's document
    rahul_docs = {d["id"] for d in client.get("/api/documents", headers=rahul_headers).json()}
    assert doc_a_id in rahul_docs
    assert doc_b_id not in rahul_docs, "Cross-workplace leak: Workplace B doc appeared in Workplace A!"

    assert client.get(f"/api/documents/{doc_b_id}", headers=rahul_headers).status_code == 403
    assert client.get(f"/api/documents/{doc_b_id}/content", headers=rahul_headers).status_code == 403

    rahul_search_b = client.post(
        "/api/search",
        headers=rahul_headers,
        json={"query": f"HyperDrive-{unique_tag}-990Hz", "collection": "ALL", "mode": "rag"},
    )
    assert rahul_search_b.status_code == 200
    assert all(
        r["document_id"] != doc_b_id and f"HyperDrive-{unique_tag}-990Hz" not in r["content"]
        for r in rahul_search_b.json()["results"]
    ), "Cross-workplace vector leak from Workplace B to Workplace A!"

    rahul_exact_b = client.post(
        "/api/search",
        headers=rahul_headers,
        json={"query": f"HyperDrive-{unique_tag}-990Hz", "collection": "ALL", "mode": "exact"},
    )
    assert rahul_exact_b.status_code == 200
    assert len(rahul_exact_b.json()["results"]) == 0, "Cross-workplace exact search leak!"

    # Priya (Workplace B) CAN see Workplace B's document, and NEVER Workplace A's document
    priya_docs = {d["id"] for d in client.get("/api/documents", headers=priya_headers).json()}
    assert doc_b_id in priya_docs
    assert doc_a_id not in priya_docs, "Cross-workplace leak: Workplace A doc appeared in Workplace B!"
    assert client.get(f"/api/documents/{doc_a_id}", headers=priya_headers).status_code == 403

    priya_search_b = client.post(
        "/api/search",
        headers=priya_headers,
        json={"query": f"HyperDrive-{unique_tag}-990Hz", "collection": "ALL", "mode": "rag"},
    )
    assert priya_search_b.status_code == 200
    assert any(r["document_id"] == doc_b_id for r in priya_search_b.json()["results"])

    # Switch Admin back to Workplace A so subsequent tests / sessions see Workplace A
    sw_a = client.post(f"/api/workplaces/{workplace_a_id}/switch", headers=admin_b_headers)
    assert sw_a.status_code == 200
    admin_a_headers = {"Authorization": f"Bearer {sw_a.json()['access_token']}"}

    # 5. Test Document Archiving & Moving in Workplace A
    arch_resp = client.post(
        f"/api/documents/{doc_a_id}/archive",
        headers=admin_a_headers,
        json={"is_archived": True},
    )
    assert arch_resp.status_code == 200
    assert arch_resp.json()["is_archived"] is True

    # Archived document is hidden from Employee Rahul
    rahul_docs_after_arch = {d["id"] for d in client.get("/api/documents", headers=rahul_headers).json()}
    assert doc_a_id not in rahul_docs_after_arch

    # Unarchive and Move document to 'Projects' collection
    unarch_resp = client.post(
        f"/api/documents/{doc_a_id}/archive",
        headers=admin_a_headers,
        json={"is_archived": False},
    )
    assert unarch_resp.status_code == 200
    assert unarch_resp.json()["is_archived"] is False

    move_resp = client.put(
        f"/api/documents/{doc_a_id}/move",
        headers=admin_a_headers,
        json={"collection": "Projects"},
    )
    assert move_resp.status_code == 200
    assert move_resp.json()["collection"] == "Projects"

    # 6. Test Employee Access-Aware Empty Response & Workplace Analytics
    emp_chat_unauth = client.post(
        "/api/chat",
        headers=rahul_headers,
        json={
            "question": f"What is the actuator frequency HyperDrive-{unique_tag}-990Hz?",
            "collection": "ALL",
            "mode": "rag",
            "stream": False,
        },
    )
    assert emp_chat_unauth.status_code == 200
    chat_data = emp_chat_unauth.json()
    assert chat_data["answer_found"] is False
    assert "available to your account" in chat_data["answer"]
    assert len(chat_data["citations"]) == 0

    analytics_resp = client.get("/api/admin/analytics", headers=admin_a_headers)
    assert analytics_resp.status_code == 200
    analytics = analytics_resp.json()
    assert analytics["workplace_id"] == workplace_a_id
    assert analytics["summary"]["total_employees"] >= 1
    assert analytics["summary"]["total_documents"] >= 1

    # Restore Admin back to the primary default ONYX workplace
    restore_sw = client.post(f"/api/workplaces/{default_wp_id}/switch", headers=admin_a_headers)
    assert restore_sw.status_code == 200

