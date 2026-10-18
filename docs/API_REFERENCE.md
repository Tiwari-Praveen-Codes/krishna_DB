# ScholarTrack REST API Reference Manual

## 1. Overview & Authentication
ScholarTrack provides a RESTful JSON API for student academic management.
- **Base URL:** `http://localhost:5000`
- **Default Headers:** `Content-Type: application/json`
- **Protected Export Endpoint:** Requires `X-API-Token: <STUDENTLEDGER_API_TOKEN>` header.

---

## 2. API Endpoints Catalog

### 2.1 Students Module

#### `GET /api/students`
Returns an array of students.
- **Query Parameters:** `q` (optional): search filter matching name, roll number, or department.
- **Response (200 OK):**
```json
[
  {
    "student_id": 41,
    "student_name": "Shruti Patil",
    "roll_no": "41",
    "branch": "Computer Science & Engineering",
    "admission_year": 2022,
    "email": "shruti.patil@viva-technology.org",
    "current_status": "Active"
  }
]
```

#### `GET /api/students/<int:student_id>`
Retrieves a single student's complete profile.
- **Response (200 OK):** `{"success": true, "student": {...}}`
- **Response (404 Not Found):** `{"success": false, "message": "Student not found"}`

#### `POST /api/students`
Registers a new student profile.
- **Request Body:**
```json
{
  "student_name": "Rohan Verma",
  "roll_no": "42",
  "branch": "Information Technology",
  "admission_year": 2022,
  "email": "rohan.verma@viva-technology.org"
}
```
- **Response (201 Created):** `{"success": true, "message": "Student added successfully!", "student_id": 42}`
- **Validation Errors:** `400 Bad Request` (missing fields or year outside 1900-2100), `409 Conflict` (duplicate roll or email).

#### `PUT /api/students/<int:student_id>`
Updates an existing student's profile.
- **Response (200 OK):** `{"success": true, "message": "Student updated successfully."}`

#### `DELETE /api/students/<int:student_id>`
Deletes a student record and cascades deletions through relational tables.
- **Response (200 OK):** `{"success": true, "message": "Student deleted successfully."}`

#### `GET /api/students/export` (Token Protected)
Secure export of the entire directory.
- **Required Header:** `X-API-Token: scholar_track_secure_token_2026`
- **Response (200 OK):** JSON array of all registered students.
- **Response (401 Unauthorized):** `{"message": "Unauthorized"}`

---

### 2.2 Progression & Dashboard

#### `GET /api/students/<int:student_id>/performance` (Preserved Legacy Endpoint)
Returns student details and semester progression list.
- **Response (200 OK):**
```json
{
  "success": true,
  "student": { "student_id": 41, "student_name": "Shruti Patil", "roll_no": "41" },
  "performance": [
    { "semester": 1, "sgpa": 8.70, "cgpa": 8.70, "result_status": "Pass" },
    { "semester": 2, "sgpa": 8.95, "cgpa": 8.83, "result_status": "Pass" }
  ]
}
```

#### `GET /api/students/<int:student_id>/dashboard`
Returns aggregated progression data, school records, gap indicator, and portfolio counts.
- **Response (200 OK):**
```json
{
  "success": true,
  "student": { ... },
  "progression": [ ... ],
  "gap_years": [ ... ],
  "has_gap": false,
  "school_records": [ ... ],
  "metrics": {
    "latest_cgpa": 8.92,
    "completed_semesters": 4,
    "total_backlogs": 0,
    "activities_count": 2,
    "seminars_count": 2,
    "certificates_count": 3
  }
}
```

---

### 2.3 Attendance & Analytics

#### `GET /api/students/<int:student_id>/attendance`
Retrieves course attendance with customizable warning threshold.
- **Query Parameter:** `threshold` (default `75.0`)
- **Response (200 OK):**
```json
{
  "success": true,
  "threshold": 75.0,
  "records": [
    {
      "subject_code": "CSC501",
      "subject_name": "Database Management Systems",
      "classes_held": 45,
      "classes_attended": 42,
      "attendance_percentage": 93.33,
      "is_warning": 0
    }
  ],
  "summary": {
    "total_held": 270,
    "total_attended": 248,
    "overall_percentage": 91.85,
    "warnings_count": 0,
    "is_critical": false
  }
}
```

#### `GET /api/students/<int:student_id>/subject-analytics`
Theory vs Lab performance comparison and failed attempts.
- **Response (200 OK):**
```json
{
  "success": true,
  "overall_average": 82.4,
  "total_evaluations": 18,
  "failed_attempts": 0,
  "type_breakdown": [
    { "subject_type": "Theory", "avg_percentage": 79.5, "total_marks_obtained": 1431, "total_marks_possible": 1800 },
    { "subject_type": "Lab", "avg_percentage": 88.2, "total_marks_obtained": 794, "total_marks_possible": 900 }
  ]
}
```

---

### 2.4 CGPA Target Predictor

#### `POST /api/predict-cgpa`
Computes required SGPA for remaining semesters.
- **Request Body:**
```json
{
  "current_cgpa": 8.10,
  "completed_sems": 4,
  "total_sems": 8,
  "desired_cgpa": 8.50
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "current_cgpa": 8.1,
  "completed_semesters": 4,
  "remaining_semesters": 4,
  "desired_cgpa": 8.5,
  "required_sgpa": 8.9,
  "achievable": true,
  "status": "ACHIEVABLE",
  "formula": "[(8.50 × 8) - (8.10 × 4)] / 4 = 8.90",
  "advice": "You need to maintain an average SGPA of at least 8.90 across your remaining 4 semesters.",
  "assumptions": "Calculation assumes equal weight across all semesters..."
}
```

---

### 2.5 Google Sheets Synchronization

#### `POST /api/sync/google-sheets`
Triggers real one-way synchronization to Google Sheets.
- **Response (200 OK - when configured):**
```json
{
  "success": true,
  "status": "SUCCESS",
  "message": "Successfully synchronized 10 tables (3200 total rows) to Google Sheets.",
  "last_sync_time": "2026-10-18 20:25:00",
  "tables": [
    { "table": "students", "tab": "Students", "rows": 100 }
  ]
}
```
- **Response (503 Service Unavailable - when unconfigured):**
```json
{
  "success": false,
  "status": "BLOCKED",
  "message": "Google Sheets credentials or Sheet ID not configured in environment variables..."
}
```

#### `GET /api/sync/google-sheets/status`
Returns configuration state and last synchronization timestamp.
