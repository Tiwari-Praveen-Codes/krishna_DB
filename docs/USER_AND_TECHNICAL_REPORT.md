# ScholarTrack User and Technical Viva Report

## 1. System Overview & Technology Stack
ScholarTrack is a full-stack Academic Progression Management System engineered for engineering and university faculties.
- **Backend Architecture:** Python 3.14, Flask, MySQL Connector, RESTful JSON API.
- **Database Engine:** MySQL 8.0 Community Server (`student_ledger`), normalized in Third Normal Form (3NF).
- **Frontend Layer:** Vanilla JavaScript, Modern CSS Glassmorphism Design System, Chart.js 4.x.
- **Cloud Integration:** Google Sheets API v4 using Service Account authorization with 10 automated worksheet tabs.

---

## 2. Graphical User Interface Operation Guide

### 2.1 Overview & Progression Dashboard
1. Launch the application (`python app.py`) and browse to `http://localhost:5000`.
2. The **Top Banner** immediately indicates active student context (e.g. Shruti Patil, Roll 41, Computer Science & Engineering).
3. The **Interactive Line Chart** plots semester-by-semester SGPA (blue line with fill) and CGPA (emerald line) up to the current semester.
4. If the student took an academic gap year, a warning badge (e.g. `⚠️ Academic Gap Year`) is automatically illuminated above the chart.
5. The **Semester Log Table** displays numerical SGPA, CGPA, official result status (`Pass`, `ATKT`, `Fail`), and backlog counts.

### 2.2 Student Directory & CRUD Management
1. Click **Student Directory** in the left sidebar navigation.
2. Use the live **Search Box** to filter across 100 students by name (e.g., "Shruti"), roll number (e.g., "41"), or department.
3. Click any row or click **Select** to dynamically bind the entire dashboard to that student.
4. Click **+ Register Student** to open the registration modal. Validate unique roll numbers and email addresses.
5. Click **Edit** to modify names, branches, admission years, or academic status (`Active`, `Graduated`, `On Hold`, `Discontinued`).
6. Click **Delete** to trigger referential integrity cascades.

### 2.3 Academics, School Records & Gap Years
1. In **Academic Progression**, click **+ Add Semester Result** to record a new semester's SGPA/CGPA.
2. In the semester row, click **View Marks** to inspect individual subject marks (Theory vs Lab), maximum marks, passing threshold, and pass/fail status.
3. Add or review secondary education (**SSC** and **HSC**) boards, passing years, and percentages.
4. Record documented **Gap Years** with reason categories (Academic CET/GATE, Medical, Personal).

### 2.4 Attendance Defaulter Tracking & Subject Analytics
1. Click **Attendance & Analytics**.
2. View classes held, attended, overall percentage, and the count of defaulter warnings.
3. Adjust the **Warning Threshold** input (default: 75%). Any subject below the threshold will immediately display a red alert badge (`⚠️ 68.5% (Below 75%)`).
4. Review the **Theory vs Lab Breakdown** panel to assess relative laboratory practical mastery vs theoretical examinations.

### 2.5 CGPA Target Predictor
1. Navigate to **CGPA Target Predictor**.
2. Input:
   - Current CGPA (e.g. `8.10`)
   - Completed Semesters (e.g. `4`)
   - Total Programme Semesters (e.g. `8`)
   - Desired Graduation CGPA (e.g. `8.50`)
3. Click **Compute Required SGPA**.
4. The system calculates:
   $$\text{Target SGPA} = \frac{(8.50 \times 8) - (8.10 \times 4)}{4} = \frac{68.0 - 32.4}{4} = 8.90$$
5. Edge cases handled:
   - Target > 10.00: Displays red `Mathematically Impossible` banner.
   - Target already achieved: Displays blue `Target Already Met / Guaranteed` banner.
   - Programme finished (0 remaining sems): Displays final status summary.

### 2.6 Google Sheets Cloud Synchronization
1. Click **Google Sheets Sync**.
2. View current Sheet ID and Service Account configuration status.
3. Click **Sync Now to Google Sheets**.
4. If credentials are unset, the system gracefully reports `BLOCKED` with a setup checklist rather than crashing.
5. When configured, 10 independent tabs (`Students`, `School_Records`, `Semester_Results`, `Subjects`, `Subject_Marks`, `Attendance`, `Gap_Years`, `Activities`, `Seminars`, `Certificates`) are populated idempotently.

---

## 3. Schema Constraints & Viva Demonstration Guide

During the examination, demonstrate relational database integrity using this 3–5 minute sequence:

### Step 1: Demonstrate 3NF Normalization (1 Minute)
- **Action:** Open `database/schema.sql` and the Overview table.
- **Explanation:** *"Our database follows 3NF. Student profiles exist only once in `students`. Subjects like Database Systems exist once in `subjects`. `subject_marks` and `attendance` reference `subjects.id` via foreign keys rather than storing redundant subject names or comma-separated lists."*

### Step 2: Demonstrate Constraint Enforcement & Error Trapping (1.5 Minutes)
- **Constraint 1 (Unique Roll Number):**
  - Attempt to register a student with Roll Number `41` (already assigned to Shruti Patil).
  - **Result:** API responds with HTTP 409 Conflict: `"This roll number already exists."`
- **Constraint 2 (Attendance Integrity):**
  - Attempt to log attendance with Classes Attended = 50 and Classes Held = 40.
  - **Result:** Form & backend reject with HTTP 400: `"Attended classes cannot exceed classes held."`
- **Constraint 3 (Foreign Key Restrict):**
  - Attempt to delete a subject from `/api/subjects/<id>` that has marks associated with it.
  - **Result:** MySQL triggers `ON DELETE RESTRICT` (Error 1451). Backend responds with HTTP 409: `"Cannot delete subject: referenced by student academic marks or attendance records."`

### Step 3: Demonstrate Interactive Analytics & CGPA Predictor (1.5 Minutes)
- **Action:** Select student Shruti Patil. Show the SGPA/CGPA line chart and attendance analytics.
- **Action:** Open the CGPA Target Predictor. Input Current: `8.0`, Completed: `4`, Target: `8.5`. Show formula output of `9.00`.
- **Action:** Input an impossible target (Target: `9.90` with completed `4` at `6.0`). Show immediate mathematically impossible detection.

### Step 4: Demonstrate Google Sheets Integration & Security (1 Minute)
- **Action:** Open Google Sheets Sync tab. Show the 10 worksheet tabs architecture.
- **Action:** Open `GET /api/students/export` without `X-API-Token` header -> returns `401 Unauthorized`.
- **Action:** Add `X-API-Token: scholar_track_secure_token_2026` -> returns full authenticated export.
- **Explanation:** *"All credentials reside in environment variables (`.env`). Secrets are protected by `.gitignore` and never committed or exposed in client JavaScript."*
