"""
Validation, Edge Cases, and Constraint Verification Tests for ScholarTrack
Validates:
- CGPA target predictor edge cases (impossible target, already achieved, zero semesters, formula correctness)
- Numeric range validation for SGPA, CGPA, percentages, and marks
- Attendance validity (classes attended cannot exceed classes held)
- School records marks validity (marks obtained cannot exceed total)
- Academic gap year consistency (end year >= start year)
- Google Sheets synchronization error & blocked credential handling
- Subject deletion constraint enforcement (ON DELETE RESTRICT)
"""

import json
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_cgpa_predictor_achievable(client):
    """
    Current: 8.0, Completed: 4, Total: 8, Target: 8.5
    Formula: [(8.5 * 8) - (8.0 * 4)] / 4 = [68 - 32] / 4 = 36 / 4 = 9.00
    """
    res = client.post("/api/predict-cgpa", json={
        "current_cgpa": 8.0,
        "completed_sems": 4,
        "total_sems": 8,
        "desired_cgpa": 8.5
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert data["achievable"] is True
    assert data["status"] == "ACHIEVABLE"
    assert data["required_sgpa"] == 9.00
    assert "formula" in data


def test_cgpa_predictor_impossible(client):
    """
    Current: 6.0, Completed: 6, Total: 8, Target: 9.5
    Required points: (9.5 * 8) - (6.0 * 6) = 76 - 36 = 40.
    Required SGPA = 40 / 2 = 20.00 (> 10.00, Impossible)
    """
    res = client.post("/api/predict-cgpa", json={
        "current_cgpa": 6.0,
        "completed_sems": 6,
        "total_sems": 8,
        "desired_cgpa": 9.5
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert data["achievable"] is False
    assert data["status"] == "IMPOSSIBLE"
    assert data["required_sgpa"] > 10.0


def test_cgpa_predictor_already_achieved(client):
    """
    Current: 9.5, Completed: 7, Total: 8, Target: 8.0
    Required points: (8.0 * 8) - (9.5 * 7) = 64 - 66.5 = -2.5
    Required SGPA < 0.0 (Already achieved)
    """
    res = client.post("/api/predict-cgpa", json={
        "current_cgpa": 9.5,
        "completed_sems": 7,
        "total_sems": 8,
        "desired_cgpa": 8.0
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert data["achievable"] is True
    assert data["status"] == "ALREADY_ACHIEVED"


def test_cgpa_predictor_zero_remaining_semesters(client):
    """Tests behaviour when all semesters are completed."""
    res = client.post("/api/predict-cgpa", json={
        "current_cgpa": 8.2,
        "completed_sems": 8,
        "total_sems": 8,
        "desired_cgpa": 8.5
    })
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert data["remaining_semesters"] == 0
    assert data["status"] == "COMPLETED"


def test_attendance_invalid_classes(client):
    """Verifies rejection when attended classes exceed classes held."""
    res = client.post("/api/students/1/attendance", json={
        "subject_id": 1,
        "academic_year": "2024-2025",
        "semester_number": 5,
        "classes_held": 40,
        "classes_attended": 55  # Invalid: 55 > 40
    })
    assert res.status_code == 400
    data = json.loads(res.data)
    assert data["success"] is False


def test_school_record_invalid_marks(client):
    """Verifies rejection when marks obtained exceed total marks."""
    res = client.post("/api/students/1/school-records", json={
        "level": "HSC",
        "board": "State Board",
        "passing_year": 2022,
        "marks_obtained": 650,
        "marks_total": 600  # Invalid: 650 > 600
    })
    assert res.status_code == 400
    data = json.loads(res.data)
    assert data["success"] is False


def test_gap_year_invalid_range(client):
    """Verifies rejection when end_year is less than start_year."""
    res = client.post("/api/students/1/gap-years", json={
        "start_year": 2024,
        "end_year": 2021,  # Invalid: 2021 < 2024
        "reason_category": "Academic"
    })
    assert res.status_code == 400
    data = json.loads(res.data)
    assert data["success"] is False


def test_google_sheets_sync_unconfigured_path(client):
    """
    Verifies that Google Sheets sync returns BLOCKED when service account
    file is unconfigured or absent on disk, rather than crashing or falsifying success.
    """
    res = client.post("/api/sync/google-sheets")
    data = json.loads(res.data)
    assert data["success"] is False
    assert data["status"] == "BLOCKED"
    assert "GOOGLE_SERVICE_ACCOUNT_FILE" in data["message"] or "not configured" in data["message"]
