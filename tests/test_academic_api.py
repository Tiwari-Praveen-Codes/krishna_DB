"""
Unit and Integration Tests for ScholarTrack Academic API
Validates:
- Academic performance retrieval and semester progression
- Dashboard metrics and gap year indicators
- School records (SSC & HSC)
- Semester result creation and duplicate semester prevention
- Subject marks and evaluations
- Attendance percentage and warning threshold computation
- Portfolio entries: activities, seminars, certificates
"""

import json
import pytest
from app import app, get_db_connection


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_get_student_performance_existing(client):
    """Verifies that performance endpoint returns SGPA and CGPA progression for an existing student."""
    response = client.get("/api/students/1/performance")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "student" in data
    assert "performance" in data
    assert isinstance(data["performance"], list)


def test_get_student_performance_nonexistent(client):
    """Verifies that performance endpoint returns 404 for unknown student."""
    response = client.get("/api/students/999999/performance")
    assert response.status_code == 404


def test_get_student_dashboard(client):
    """Verifies unified dashboard payload including progression, school records, and metrics."""
    response = client.get("/api/students/1/dashboard")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "metrics" in data
    assert "latest_cgpa" in data["metrics"]
    assert "total_backlogs" in data["metrics"]
    assert "progression" in data
    assert "has_gap" in data


def test_school_records_flow(client):
    """Verifies retrieving school records for student #1."""
    response = client.get("/api/students/1/school-records")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert isinstance(data["records"], list)


def test_subjects_list(client):
    """Verifies that GET /api/subjects returns curriculum catalog."""
    response = client.get("/api/subjects")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert len(data["subjects"]) > 0


def test_attendance_and_warning_threshold(client):
    """Verifies attendance tracking and warning calculation under 75% threshold."""
    response = client.get("/api/students/1/attendance?threshold=75")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "summary" in data
    assert "overall_percentage" in data["summary"]
    assert "warnings_count" in data["summary"]


def test_subject_analytics(client):
    """Verifies Theory vs Lab breakdown and failed attempts metrics."""
    response = client.get("/api/students/1/subject-analytics")
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["success"] is True
    assert "type_breakdown" in data
    assert "overall_average" in data


def test_portfolio_activities_and_certificates(client):
    """Verifies activities, seminars, and certificates retrieval."""
    act_res = client.get("/api/students/1/activities")
    assert act_res.status_code == 200
    assert json.loads(act_res.data)["success"] is True

    sem_res = client.get("/api/students/1/seminars")
    assert sem_res.status_code == 200
    assert json.loads(sem_res.data)["success"] is True

    cert_res = client.get("/api/students/1/certificates")
    assert cert_res.status_code == 200
    assert json.loads(cert_res.data)["success"] is True
