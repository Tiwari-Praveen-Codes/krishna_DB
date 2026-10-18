"""
Unit and Integration Tests for ScholarTrack Students API
Validates:
- Student listing, search by name and roll number
- Student registration with duplicate roll and email handling
- Input validation (missing required fields, admission year range)
- Student profile editing and status updates
- Student deletion
- Token-protected export authorization check
"""

import os
import json
import pytest
from app import app, get_db_connection


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_get_students_list(client):
    """Verifies that GET /api/students returns an array of students with expected fields."""
    response = client.get("/api/students")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    if len(data) > 0:
        first = data[0]
        assert "student_id" in first
        assert "student_name" in first
        assert "roll_no" in first


def test_student_search(client):
    """Verifies student search query 'q' by name and roll number."""
    response = client.get("/api/students?q=41")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    # Check that any returned student matches '41' in name, roll, or branch
    for item in data:
        assert "41" in str(item["roll_no"]) or "41" in str(item["student_name"]) or "41" in str(item.get("branch", ""))


def test_add_student_validation_missing_fields(client):
    """Verifies rejection when mandatory fields are omitted."""
    response = client.post("/api/students", json={
        "student_name": "Incomplete Student"
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False
    assert "required" in data["message"].lower()


def test_add_student_invalid_admission_year(client):
    """Verifies that admission years outside 1900-2100 are rejected."""
    response = client.post("/api/students", json={
        "student_name": "Time Traveler",
        "roll_no": "ROLL-TEST-9999",
        "branch": "Computer Science",
        "admission_year": 1850
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data["success"] is False


def test_student_export_unauthorized(client):
    """Verifies that GET /api/students/export rejects requests with missing or invalid token."""
    response = client.get("/api/students/export")
    assert response.status_code == 401

    response_bad_token = client.get("/api/students/export", headers={"X-API-Token": "invalid_wrong_token"})
    assert response_bad_token.status_code == 401


def test_student_export_authorized(client):
    """Verifies that GET /api/students/export succeeds with correct X-API-Token."""
    token = os.environ.get("STUDENTLEDGER_API_TOKEN", "scholar_track_secure_token_2026")
    response = client.get("/api/students/export", headers={"X-API-Token": token})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)


def test_student_lifecycle_crud(client):
    """
    Tests complete lifecycle: Create, Read, Update, Delete with unique test roll number.
    Ensures rollback or explicit cleanup so test data does not linger.
    """
    test_roll = "TEST_ROLL_TEMP_789"
    test_email = "test.temporary.student@viva-technology.org"

    # Ensure clean starting state
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE roll_no = %s", (test_roll,))
    conn.commit()
    cur.close()
    conn.close()

    # 1. Create
    create_res = client.post("/api/students", json={
        "student_name": "Automated Test Student",
        "roll_no": test_roll,
        "branch": "Information Technology",
        "admission_year": 2023,
        "email": test_email
    })
    assert create_res.status_code == 201
    created_data = json.loads(create_res.data)
    assert created_data["success"] is True
    student_id = created_data["student_id"]

    # 2. Duplicate roll check
    dup_res = client.post("/api/students", json={
        "student_name": "Duplicate Student",
        "roll_no": test_roll,
        "branch": "Information Technology",
        "admission_year": 2023,
        "email": "another.email@example.com"
    })
    assert dup_res.status_code == 409

    # 3. Read
    detail_res = client.get(f"/api/students/{student_id}")
    assert detail_res.status_code == 200
    detail_data = json.loads(detail_res.data)
    assert detail_data["student"]["student_name"] == "Automated Test Student"

    # 4. Update
    update_res = client.put(f"/api/students/{student_id}", json={
        "student_name": "Updated Test Student",
        "roll_no": test_roll,
        "branch": "Data Science",
        "admission_year": 2023,
        "email": test_email,
        "current_status": "Active"
    })
    assert update_res.status_code == 200

    # 5. Delete
    delete_res = client.delete(f"/api/students/{student_id}")
    assert delete_res.status_code == 200
    del_data = json.loads(delete_res.data)
    assert del_data["success"] is True

    # 6. Verify deleted
    verify_res = client.get(f"/api/students/{student_id}")
    assert verify_res.status_code == 404
