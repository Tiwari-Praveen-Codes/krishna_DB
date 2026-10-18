-- ==============================================================================
-- ScholarTrack Academic Progression DBMS — SQLite 3 Schema
-- Database: scholartrack.db
-- Relational 3NF Architecture with Foreign Keys, Check Constraints & Indexes
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------------------------
-- 1. STUDENTS TABLE (Core Student Profiles)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_name TEXT NOT NULL,
    roll_no TEXT NOT NULL UNIQUE,
    branch TEXT NOT NULL,
    admission_year INTEGER NOT NULL CHECK(admission_year BETWEEN 1900 AND 2100),
    email TEXT UNIQUE,
    current_status TEXT NOT NULL DEFAULT 'Active' CHECK(current_status IN ('Active', 'Graduated', 'On Hold', 'Discontinued')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_students_roll_no ON students (roll_no);
CREATE INDEX IF NOT EXISTS idx_students_name ON students (student_name);
CREATE INDEX IF NOT EXISTS idx_students_branch ON students (branch);

-- ------------------------------------------------------------------------------
-- 2. SCHOOL RECORDS TABLE (Prior Education: SSC & HSC)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS school_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    level TEXT NOT NULL CHECK(level IN ('SSC', 'HSC')),
    board TEXT NOT NULL,
    passing_year INTEGER NOT NULL CHECK(passing_year BETWEEN 1900 AND 2100),
    marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
    marks_total REAL NOT NULL CHECK(marks_total > 0 AND marks_obtained <= marks_total),
    percentage REAL NOT NULL CHECK(percentage >= 0.0 AND percentage <= 100.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, level)
);

CREATE INDEX IF NOT EXISTS idx_school_student ON school_records (student_id);

-- ------------------------------------------------------------------------------
-- 3. SEMESTER RESULTS TABLE (Academic Progression Tracking)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS semester_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    semester_number INTEGER NOT NULL CHECK(semester_number BETWEEN 1 AND 10),
    academic_year TEXT NOT NULL,
    sgpa REAL NOT NULL CHECK(sgpa >= 0.0 AND sgpa <= 10.0),
    cgpa REAL NOT NULL CHECK(cgpa >= 0.0 AND cgpa <= 10.0),
    result_status TEXT NOT NULL DEFAULT 'Pass' CHECK(result_status IN ('Pass', 'ATKT', 'Fail', 'Pending')),
    backlog_count INTEGER NOT NULL DEFAULT 0 CHECK(backlog_count >= 0),
    is_gap_after INTEGER NOT NULL DEFAULT 0 CHECK(is_gap_after IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, semester_number)
);

CREATE INDEX IF NOT EXISTS idx_sem_results_student ON semester_results (student_id);
CREATE INDEX IF NOT EXISTS idx_sem_results_year ON semester_results (academic_year);

-- ------------------------------------------------------------------------------
-- 4. SUBJECTS TABLE (Course Registry)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_code TEXT NOT NULL UNIQUE,
    subject_name TEXT NOT NULL,
    subject_type TEXT NOT NULL CHECK(subject_type IN ('Theory', 'Lab')),
    credits REAL NOT NULL DEFAULT 3.0 CHECK(credits >= 0.0 AND credits <= 10.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_subjects_code ON subjects (subject_code);

-- ------------------------------------------------------------------------------
-- 5. SUBJECT MARKS TABLE (Detailed Exam Breakdown)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS subject_marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    semester_result_id INTEGER NOT NULL REFERENCES semester_results(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
    marks_obtained REAL NOT NULL CHECK(marks_obtained >= 0),
    marks_total REAL NOT NULL CHECK(marks_total > 0 AND marks_obtained <= marks_total),
    passing_marks REAL NOT NULL DEFAULT 40.0 CHECK(passing_marks >= 0 AND passing_marks <= marks_total),
    component TEXT NOT NULL DEFAULT 'Final' CHECK(component IN ('Internal', 'External', 'Practical', 'Final')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(semester_result_id, subject_id, component)
);

CREATE INDEX IF NOT EXISTS idx_marks_sem_result ON subject_marks (semester_result_id);
CREATE INDEX IF NOT EXISTS idx_marks_subject ON subject_marks (subject_id);

-- ------------------------------------------------------------------------------
-- 6. ATTENDANCE TABLE (Held vs Attended Monitoring)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE RESTRICT,
    academic_year TEXT NOT NULL,
    semester_number INTEGER NOT NULL CHECK(semester_number BETWEEN 1 AND 10),
    classes_held INTEGER NOT NULL CHECK(classes_held >= 0),
    classes_attended INTEGER NOT NULL CHECK(classes_attended >= 0 AND classes_attended <= classes_held),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, subject_id, academic_year, semester_number)
);

CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance (student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_subject ON attendance (subject_id);

-- ------------------------------------------------------------------------------
-- 7. GAP YEARS TABLE (Documented Academic Gaps)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gap_years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL CHECK(end_year >= start_year),
    reason_category TEXT NOT NULL CHECK(reason_category IN ('Academic', 'Medical', 'Personal', 'Other')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_gap_years_student ON gap_years (student_id);

-- ------------------------------------------------------------------------------
-- 8. ACTIVITIES TABLE (Technical & Co-Curricular Portfolio)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    activity_type TEXT NOT NULL CHECK(activity_type IN ('Technical', 'Co-curricular', 'Extra-curricular')),
    organization TEXT,
    activity_date DATE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_activities_student ON activities (student_id);

-- ------------------------------------------------------------------------------
-- 9. SEMINARS TABLE (Paper Presentations & Expert Talks)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS seminars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    seminar_scope TEXT NOT NULL CHECK(seminar_scope IN ('Internal', 'External')),
    organizer TEXT,
    seminar_date DATE,
    certificate_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_seminars_student ON seminars (student_id);

-- ------------------------------------------------------------------------------
-- 10. CERTIFICATES TABLE (Verified Credentials & Badges)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    issuer TEXT NOT NULL,
    category TEXT NOT NULL CHECK(category IN ('Course', 'Hackathon', 'Internship', 'Achievement', 'Seminar', 'Other')),
    issue_date DATE,
    credential_url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_certificates_student ON certificates (student_id);

-- ------------------------------------------------------------------------------
-- 11. LEGACY TABLE (Preserved for Backward Compatibility)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(student_id) ON DELETE CASCADE,
    semester INTEGER NOT NULL,
    sgpa REAL,
    cgpa REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_id, semester)
);
