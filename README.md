# ScholarTrack — Student Academic Progression DBMS

ScholarTrack is an enterprise-grade Academic Progression Management System built for higher education engineering institutions. It provides comprehensive tracking of student academic progression, historical schooling (SSC/HSC), semester-wise SGPA and CGPA trends, subject marks breakdown (Theory vs Lab), attendance monitoring with automated defaulter alerts, academic gap years, co-curricular portfolios, an interactive CGPA target predictor, and genuine cloud synchronization to Google Sheets using the official Google Sheets API v4.

---

## 1. Core Features & Capabilities

- **Normalized 3NF Relational Schema:** 10 core tables in MySQL 8.0 enforcing primary keys, foreign keys (`ON DELETE CASCADE` / `ON DELETE RESTRICT`), unique constraints, and check constraints.
- **Academic Progression Dashboard:** Dynamic Chart.js line charts plotting SGPA and CGPA trends across semesters, visible gap-year indicators, backlog counts, and official result statuses (`Pass`, `ATKT`, `Fail`, `Pending`).
- **Complete CRUD Operations:** Full create, read, update, and delete capabilities for students, school records, semester results, subjects, marks, attendance, gap years, activities, seminars, and certificates.
- **Attendance & Analytics:** Configurable attendance warning threshold (defaults to 75%), automatic defaulter flags, theory vs lab score comparison, and failed attempt calculations.
- **CGPA Target Predictor:** Interactive mathematical calculator forecasting the exact required average SGPA across remaining semesters with mathematical formula display and credit-weighting assumption notes.
- **Google Sheets Cloud Integration:** Authentic one-way synchronization to 10 automated worksheet tabs using Google Sheets API v4 with idempotent updates and structured status reporting.
- **API Security:** Environment-driven database configuration, token-protected export endpoint (`X-API-Token`), parameterized SQL queries (`%s`), and non-destructive legacy migration support.

---

## 2. Architecture & Directory Structure

```
ScholarTrack/
├── app.py                         # Main Flask backend application server
├── google_sheets_sync.py          # Google Sheets API v4 synchronization module
├── requirements.txt               # Python package dependencies
├── .env.example                   # Template environment variables file
├── .env                           # Active environment credentials (git-ignored)
├── .gitignore                     # Git ignore rules protecting secrets & venvs
├── pytest.ini                     # Pytest test discovery configuration
├── PROJECT_STATUS.md              # Project status tracking and implementation matrix
├── README.md                      # Primary project documentation
│
├── database/
│   ├── schema.sql                 # Complete MySQL 3NF database schema with constraints
│   ├── init_db.py                 # Automated database initialization & seeding script
│   └── migrations/
│       ├── 001_initial_schema.sql # Initial schema migration
│       └── 002_migrate_legacy_performance.sql # Safe non-destructive legacy migration
│
├── templates/
│   └── index.html                 # Master dashboard template (7 module tabs & modals)
│
├── static/
│   ├── css/
│   │   └── style.css              # Master glassmorphism responsive stylesheet
│   ├── js/
│   │   └── app.js                 # Complete frontend engine & Chart.js integration
│   ├── style.css                  # Backwards-compatible style link
│   └── script.js                  # Backwards-compatible script link
│
├── docs/
│   ├── DATABASE_SCHEMA.md         # Schema documentation, 3NF proofs, and Mermaid ERD
│   ├── API_REFERENCE.md           # REST API endpoints, request bodies, and responses
│   ├── USER_AND_TECHNICAL_REPORT.md # User guide and 3-5 minute viva demonstration steps
│   └── TESTING.md                 # Testing report and edge case verification
│
└── tests/
    ├── test_students_api.py       # Student CRUD, search, export token security tests
    ├── test_academic_api.py       # Academic progression, dashboard, attendance tests
    └── test_validation.py         # CGPA predictor, constraint violation, sync tests
```

---

## 3. Prerequisites

- **Operating System:** Windows 10/11, macOS, or Linux.
- **Python:** Python 3.10+ (tested and verified on Python 3.14).
- **MySQL:** MySQL Server 8.0+ running locally (or remote MySQL instance).

---

## 4. Installation & Setup (Windows PowerShell)

### Step 1: Clone or Open Workspace
```powershell
cd "c:\Users\pt489\OneDrive\Desktop\Murthy"
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` and verify database credentials:
```powershell
Copy-Item .env.example .env
```
Ensure your `.env` contains:
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=Pravin@_123
DB_NAME=student_ledger

STUDENTLEDGER_API_TOKEN=scholar_track_secure_token_2026
SECRET_KEY=scholartrack_super_secret_session_key_2026

GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
GOOGLE_SHEET_ID=
```

### Step 3: Install Python Dependencies
```powershell
python -m pip install -r requirements.txt
```

### Step 4: Initialize MySQL Database & Seed Data
Run the automated database setup utility to create the database, build the 10 tables, and seed the verified 100 students dataset:
```powershell
python database/init_db.py
```

### Step 5: Start the Application Server
```powershell
python app.py
```
Open your browser and navigate to:
```
http://localhost:5000
```

---

## 5. Google Sheets Synchronization Setup

1. Create a Google Cloud Platform (GCP) project and enable the **Google Sheets API**.
2. Create a **Service Account** and download its credentials as a JSON file (e.g. `credentials.json`).
3. Place `credentials.json` in the project root (it is git-ignored for safety).
4. Create a new Google Spreadsheet in Google Drive and copy the Sheet ID from its URL:
   `https://docs.google.com/spreadsheets/d/<GOOGLE_SHEET_ID>/edit`
5. Share the Google Sheet with the Service Account email (give **Editor** permissions).
6. Set the values in `.env`:
   ```ini
   GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
   GOOGLE_SHEET_ID=your_sheet_id_here
   ```
7. Click **Sync Now to Google Sheets** in the web dashboard or call `POST /api/sync/google-sheets`.

---

## 6. Testing & Quality Assurance

Run the automated test suite using `pytest`:
```powershell
# Run all automated tests
python -m pytest -q

# Run syntax compilation check
python -m compileall -x "[\\/]\.venv" .
```
**Test Results:** 23 tests passed in ~4.2 seconds across student CRUD, academic progression, attendance warnings, and CGPA predictor edge cases.

---

## 7. Viva Voce Quick Demonstration Sequence (3–5 Minutes)

1. **Dashboard & Progression Chart (1 Min):**
   - Open `http://localhost:5000`. Show Shruti Patil (Roll 41).
   - Point out the SGPA/CGPA line chart and gap year indicator badge.
2. **Attendance Defaulter Warning (1 Min):**
   - Switch to **Attendance & Analytics**.
   - Show how setting the threshold to 75% highlights any subject below 75% with a red alert badge.
3. **Database Constraints (1 Min):**
   - Attempt to register a student with existing Roll Number `41` -> Handled gracefully with HTTP 409 Conflict.
   - Attempt to enter attendance with Attended > Held -> Rejected with HTTP 400 Bad Request.
4. **CGPA Target Predictor (1 Min):**
   - In **CGPA Predictor**, input Current: 8.0, Completed: 4, Target: 8.5 -> Displays exact formula and required SGPA of 9.00.
   - Enter an impossible target (Target: 9.9) -> Flags `Mathematically Impossible`.
5. **Google Sheets & API Security (1 Min):**
   - Show Google Sheets Sync tab and 10 worksheet tabs mapping.
   - Demonstrate that `/api/students/export` without token returns `401 Unauthorized`.
