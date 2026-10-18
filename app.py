"""
ScholarTrack Academic Progression Management System
Flask Backend Server & Relational DBMS Integration Layer
"""

import os
import hmac
import math
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import mysql.connector
from dotenv import load_dotenv

from google_sheets_sync import sync_all_tables_to_sheets, LAST_SYNC_INFO

# Load environment configuration
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "scholartrack_secret_key_84920")

# MySQL Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Pravin@_123")
DB_NAME = os.getenv("DB_NAME", "student_ledger")


def get_db_connection():
    """Returns a fresh MySQL connection using configured environment parameters."""
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


# ==============================================================================
# 1. FRONTEND ROUTE
# ==============================================================================
@app.route("/")
def home():
    """Serves the main academic progression dashboard."""
    return render_template("index.html")


# ==============================================================================
# 2. SYSTEM STATS & METRICS
# ==============================================================================
@app.route("/api/stats", methods=["GET"])
def get_system_stats():
    """Returns aggregate database counts and academic metrics."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) AS total_students FROM students")
        total_students = cur.fetchone()["total_students"]

        cur.execute("SELECT COUNT(*) AS total_records FROM semester_results")
        total_records = cur.fetchone()["total_records"]

        cur.execute("SELECT ROUND(AVG(cgpa), 2) AS avg_cgpa FROM semester_results WHERE cgpa > 0")
        avg_row = cur.fetchone()
        avg_cgpa = avg_row["avg_cgpa"] if avg_row and avg_row["avg_cgpa"] is not None else 0.0

        cur.execute("""
            SELECT 
                (SELECT COUNT(*) FROM activities) +
                (SELECT COUNT(*) FROM seminars) +
                (SELECT COUNT(*) FROM certificates) AS total_portfolio
        """)
        total_portfolio = cur.fetchone()["total_portfolio"]

        return jsonify({
            "success": True,
            "total_students": total_students,
            "total_records": total_records,
            "average_cgpa": avg_cgpa,
            "total_activities": total_portfolio
        })
    except mysql.connector.Error as err:
        app.logger.exception("Database error while fetching stats")
        return jsonify({"success": False, "message": "Failed to load system stats"}), 500
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 3. STUDENT CRUD & SEARCH (Preserving Existing Contracts)
# ==============================================================================
@app.route("/api/students", methods=["GET"])
def get_students():
    """
    Returns list of students. Supports search query 'q' by name or roll number.
    Preserves exact contract: student_id, student_name, roll_no.
    """
    search_query = request.args.get("q", "").strip()
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        if search_query:
            term = f"%{search_query}%"
            cur.execute("""
                SELECT student_id, student_name, roll_no, branch, admission_year, email, current_status
                FROM students
                WHERE student_name LIKE %s OR roll_no LIKE %s
                ORDER BY student_id ASC
            """, (term, term))
        else:
            cur.execute("""
                SELECT student_id, student_name, roll_no, branch, admission_year, email, current_status
                FROM students
                ORDER BY student_id ASC
            """)

        students = cur.fetchall()
        return jsonify(students)
    except mysql.connector.Error:
        app.logger.exception("Database error while fetching students")
        return jsonify({"success": False, "message": "Database query error"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>", methods=["GET"])
def get_student_detail(student_id):
    """Retrieves full details for a single student."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT student_id, student_name, roll_no, branch, admission_year, email, current_status, created_at
            FROM students
            WHERE student_id = %s
        """, (student_id,))
        student = cur.fetchone()
        if not student:
            return jsonify({"success": False, "message": "Student not found"}), 404
        return jsonify({"success": True, "student": student})
    except mysql.connector.Error:
        app.logger.exception("Error fetching student details")
        return jsonify({"success": False, "message": "Database error"}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/students", methods=["POST"])
def add_student():
    """
    Adds a new student. Enforces 100 student limit, valid admission year,
    and unique roll number. Returns 201 on success.
    """
    data = request.get_json(silent=True) or {}
    student_name = str(data.get("student_name", "")).strip()
    roll_no = str(data.get("roll_no", "")).strip()
    branch = str(data.get("branch", "")).strip()
    admission_year = data.get("admission_year")
    email = str(data.get("email", "")).strip()

    if not student_name or not roll_no or not branch or not admission_year:
        return jsonify({"success": False, "message": "Please fill all required fields."}), 400

    try:
        admission_year = int(admission_year)
        if admission_year < 1900 or admission_year > 2100:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Enter a valid admission year (1900-2100)."}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("SELECT COUNT(*) AS total FROM students")
        total = cur.fetchone()["total"]
        max_limit = int(os.getenv("MAX_STUDENTS", 1000))
        if not app.config.get("TESTING") and total >= max_limit:
            return jsonify({"success": False, "message": f"Maximum limit of {max_limit} students reached."}), 400

        cur.execute("SELECT student_id FROM students WHERE roll_no = %s", (roll_no,))
        if cur.fetchone():
            return jsonify({"success": False, "message": "This roll number already exists."}), 409

        if email:
            cur.execute("SELECT student_id FROM students WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({"success": False, "message": "This email address is already registered."}), 409

        cur.execute("""
            INSERT INTO students (student_name, roll_no, branch, admission_year, email)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_name, roll_no, branch, admission_year, email or None))
        conn.commit()
        new_id = cur.lastrowid

        return jsonify({
            "success": True,
            "message": "Student added successfully!",
            "student_id": new_id
        }), 201

    except mysql.connector.Error:
        conn.rollback()
        app.logger.exception("Database error while adding student")
        return jsonify({"success": False, "message": "Database error while adding student."}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>", methods=["PUT"])
def update_student(student_id):
    """Updates an existing student's profile."""
    data = request.get_json(silent=True) or {}
    student_name = str(data.get("student_name", "")).strip()
    roll_no = str(data.get("roll_no", "")).strip()
    branch = str(data.get("branch", "")).strip()
    admission_year = data.get("admission_year")
    email = str(data.get("email", "")).strip()
    current_status = data.get("current_status", "Active")

    if not student_name or not roll_no or not branch or not admission_year:
        return jsonify({"success": False, "message": "All required fields must be supplied."}), 400

    try:
        admission_year = int(admission_year)
        if admission_year < 1900 or admission_year > 2100:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Valid admission year is required."}), 400

    valid_statuses = ("Active", "Graduated", "On Hold", "Discontinued")
    if current_status not in valid_statuses:
        return jsonify({"success": False, "message": f"Invalid status. Must be one of {valid_statuses}."}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("SELECT student_id FROM students WHERE student_id = %s", (student_id,))
        if not cur.fetchone():
            return jsonify({"success": False, "message": "Student not found."}), 404

        cur.execute("SELECT student_id FROM students WHERE roll_no = %s AND student_id != %s", (roll_no, student_id))
        if cur.fetchone():
            return jsonify({"success": False, "message": "Roll number belongs to another student."}), 409

        if email:
            cur.execute("SELECT student_id FROM students WHERE email = %s AND student_id != %s", (email, student_id))
            if cur.fetchone():
                return jsonify({"success": False, "message": "Email belongs to another student."}), 409

        cur.execute("""
            UPDATE students
            SET student_name = %s, roll_no = %s, branch = %s, admission_year = %s, email = %s, current_status = %s
            WHERE student_id = %s
        """, (student_name, roll_no, branch, admission_year, email or None, current_status, student_id))
        conn.commit()

        return jsonify({"success": True, "message": "Student updated successfully."})
    except mysql.connector.Error:
        conn.rollback()
        app.logger.exception("Error updating student")
        return jsonify({"success": False, "message": "Database error while updating student."}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>", methods=["DELETE"])
def delete_student(student_id):
    """Deletes a student and all related cascading relational records."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT student_name FROM students WHERE student_id = %s", (student_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Student not found."}), 404

        cur.execute("DELETE FROM students WHERE student_id = %s", (student_id,))
        conn.commit()
        return jsonify({"success": True, "message": f"Student '{row['student_name']}' deleted successfully."})
    except mysql.connector.Error:
        conn.rollback()
        app.logger.exception("Error deleting student")
        return jsonify({"success": False, "message": "Database error while deleting student."}), 500
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 4. TOKEN-PROTECTED STUDENT EXPORT (Preserved Contract)
# ==============================================================================
@app.route("/api/students/export", methods=["GET"])
def export_students():
    """Exports student directory protected with X-API-Token authentication."""
    expected_token = os.environ.get("STUDENTLEDGER_API_TOKEN", "scholar_track_secure_token_2026")
    supplied_token = request.headers.get("X-API-Token", "")

    if not expected_token or not hmac.compare_digest(supplied_token, expected_token):
        return jsonify({"message": "Unauthorized"}), 401

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT student_id, student_name, roll_no, branch, admission_year, email, current_status
            FROM students
            ORDER BY student_id ASC
        """)
        students = cur.fetchall()
        return jsonify(students)
    except mysql.connector.Error:
        app.logger.exception("Student export API error")
        return jsonify({"success": False, "message": "Database error"}), 500
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 5. ACADEMIC PERFORMANCE (Preserved Contract & Progression Dashboard)
# ==============================================================================
@app.route("/api/students/<int:student_id>/performance", methods=["GET"])
def get_student_performance(student_id):
    """
    Preserved endpoint returning student details and semester progression list.
    Reads from normalized semester_results with fallback to student_performance.
    """
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT student_id, student_name, roll_no, branch, admission_year, email, current_status
            FROM students
            WHERE student_id = %s
        """, (student_id,))
        student = cur.fetchone()

        if not student:
            return jsonify({"success": False, "message": "Student not found"}), 404

        # Read from semester_results
        cur.execute("""
            SELECT 
                id,
                semester_number AS semester,
                semester_number,
                academic_year,
                sgpa,
                cgpa,
                result_status,
                backlog_count,
                is_gap_after
            FROM semester_results
            WHERE student_id = %s
            ORDER BY semester_number ASC
        """, (student_id,))
        performance = cur.fetchall()

        # If empty in semester_results, fallback check on legacy student_performance
        if not performance:
            cur.execute("""
                SELECT id, semester, semester AS semester_number, sgpa, cgpa, 'Pass' AS result_status, 0 AS backlog_count, 0 AS is_gap_after
                FROM student_performance
                WHERE student_id = %s
                ORDER BY semester ASC
            """, (student_id,))
            performance = cur.fetchall()

        return jsonify({
            "success": True,
            "student": student,
            "performance": performance
        })
    except mysql.connector.Error:
        app.logger.exception("Academic performance API error")
        return jsonify({"success": False, "message": "Database error. Check Flask terminal."}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/dashboard", methods=["GET"])
def get_student_dashboard(student_id):
    """
    Returns unified comprehensive dashboard payload for selected student:
    - Profile summary
    - SGPA & CGPA progression
    - Gap year indicators & documented gaps
    - Backlog summary and completion status
    - SSC/HSC school records
    - Portfolio totals
    """
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    try:
        cur.execute("""
            SELECT student_id, student_name, roll_no, branch, admission_year, email, current_status
            FROM students
            WHERE student_id = %s
        """, (student_id,))
        student = cur.fetchone()
        if not student:
            return jsonify({"success": False, "message": "Student not found"}), 404

        # Semester progression
        cur.execute("""
            SELECT id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count, is_gap_after
            FROM semester_results
            WHERE student_id = %s
            ORDER BY semester_number ASC
        """, (student_id,))
        semesters = cur.fetchall()

        # Documented gap years
        cur.execute("""
            SELECT id, start_year, end_year, reason_category, notes
            FROM gap_years
            WHERE student_id = %s
            ORDER BY start_year ASC
        """, (student_id,))
        gap_years = cur.fetchall()

        # School records
        cur.execute("""
            SELECT id, level, board, passing_year, marks_obtained, marks_total, percentage
            FROM school_records
            WHERE student_id = %s
            ORDER BY level DESC
        """, (student_id,))
        school_records = cur.fetchall()

        # Count activities, seminars, certificates
        cur.execute("SELECT COUNT(*) AS total FROM activities WHERE student_id = %s", (student_id,))
        act_cnt = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM seminars WHERE student_id = %s", (student_id,))
        sem_cnt = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) AS total FROM certificates WHERE student_id = %s", (student_id,))
        cert_cnt = cur.fetchone()["total"]

        # Calculate metrics & distributions
        latest_cgpa = semesters[-1]["cgpa"] if semesters else 0.0
        total_backlogs = sum(s.get("backlog_count", 0) for s in semesters)
        has_gap = len(gap_years) > 0 or any(s.get("is_gap_after") for s in semesters)

        grade_distribution = {"Distinction": 0, "First Class": 0, "Higher Second": 0, "Pass Class": 0}
        for s in semesters:
            sg = float(s.get("sgpa") or 0.0)
            if sg >= 8.5:
                grade_distribution["Distinction"] += 1
            elif sg >= 7.5:
                grade_distribution["First Class"] += 1
            elif sg >= 6.5:
                grade_distribution["Higher Second"] += 1
            else:
                grade_distribution["Pass Class"] += 1

        # Subject marks analytics for bar charts
        cur.execute("""
            SELECT s.subject_code, s.subject_name, s.subject_type, sm.marks_obtained, sm.marks_total, sm.passing_marks
            FROM subject_marks sm
            JOIN semester_results sr ON sm.semester_result_id = sr.id
            JOIN subjects s ON sm.subject_id = s.id
            WHERE sr.student_id = %s
            ORDER BY sr.semester_number DESC, s.subject_code ASC
            LIMIT 6
        """, (student_id,))
        subject_marks_chart = cur.fetchall()

        # Attendance compliance for bar charts
        cur.execute("""
            SELECT s.subject_code, a.classes_held, a.classes_attended,
                   ROUND((a.classes_attended / a.classes_held) * 100, 1) AS attendance_pct
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            WHERE a.student_id = %s AND a.classes_held > 0
            ORDER BY a.semester_number DESC, s.subject_code ASC
            LIMIT 6
        """, (student_id,))
        attendance_chart = cur.fetchall()

        # Theory vs Lab average
        cur.execute("""
            SELECT s.subject_type, ROUND(AVG((sm.marks_obtained / sm.marks_total) * 100), 1) AS avg_pct
            FROM subject_marks sm
            JOIN semester_results sr ON sm.semester_result_id = sr.id
            JOIN subjects s ON sm.subject_id = s.id
            WHERE sr.student_id = %s
            GROUP BY s.subject_type
        """, (student_id,))
        theory_lab_pie = cur.fetchall()

        return jsonify({
            "success": True,
            "student": student,
            "progression": semesters,
            "gap_years": gap_years,
            "has_gap": has_gap,
            "school_records": school_records,
            "analytics": {
                "grade_distribution": grade_distribution,
                "subject_marks_chart": subject_marks_chart,
                "attendance_chart": attendance_chart,
                "theory_lab_pie": theory_lab_pie
            },
            "metrics": {
                "latest_cgpa": latest_cgpa,
                "completed_semesters": len(semesters),
                "total_backlogs": total_backlogs,
                "activities_count": act_cnt,
                "seminars_count": sem_cnt,
                "certificates_count": cert_cnt
            }
        })
    except mysql.connector.Error:
        app.logger.exception("Error assembling student dashboard")
        return jsonify({"success": False, "message": "Failed to assemble dashboard data"}), 500
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 6. SCHOOL RECORDS (SSC & HSC) CRUD
# ==============================================================================
@app.route("/api/students/<int:student_id>/school-records", methods=["GET"])
def get_school_records(student_id):
    """Retrieves SSC and HSC records for a student."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, student_id, level, board, passing_year, marks_obtained, marks_total, percentage
            FROM school_records
            WHERE student_id = %s
            ORDER BY level DESC
        """, (student_id,))
        return jsonify({"success": True, "records": cur.fetchall()})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/school-records", methods=["POST"])
def add_school_record(student_id):
    """Adds a new SSC or HSC record for a student."""
    data = request.get_json(silent=True) or {}
    level = data.get("level")
    board = str(data.get("board", "")).strip()
    passing_year = data.get("passing_year")
    marks_obtained = data.get("marks_obtained")
    marks_total = data.get("marks_total")

    if level not in ("SSC", "HSC") or not board or passing_year is None or marks_obtained is None or marks_total is None:
        return jsonify({"success": False, "message": "Valid level (SSC/HSC), board, passing year, and marks are required."}), 400

    try:
        passing_year = int(passing_year)
        marks_obtained = float(marks_obtained)
        marks_total = float(marks_total)
        if marks_total <= 0 or marks_obtained < 0 or marks_obtained > marks_total:
            raise ValueError
        percentage = round((marks_obtained / marks_total) * 100.0, 2)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid marks or passing year values."}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Check uniqueness per student & level
        cur.execute("SELECT id FROM school_records WHERE student_id = %s AND level = %s", (student_id, level))
        if cur.fetchone():
            return jsonify({"success": False, "message": f"{level} record already exists for this student."}), 409

        cur.execute("""
            INSERT INTO school_records (student_id, level, board, passing_year, marks_obtained, marks_total, percentage)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (student_id, level, board, passing_year, marks_obtained, marks_total, percentage))
        conn.commit()
        return jsonify({"success": True, "message": f"{level} record added successfully.", "id": cur.lastrowid}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"success": False, "message": str(err)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/school-records/<int:record_id>", methods=["PUT"])
def update_school_record(record_id):
    """Updates an existing school record."""
    data = request.get_json(silent=True) or {}
    board = str(data.get("board", "")).strip()
    passing_year = data.get("passing_year")
    marks_obtained = data.get("marks_obtained")
    marks_total = data.get("marks_total")

    try:
        passing_year = int(passing_year)
        marks_obtained = float(marks_obtained)
        marks_total = float(marks_total)
        if marks_total <= 0 or marks_obtained < 0 or marks_obtained > marks_total:
            raise ValueError
        percentage = round((marks_obtained / marks_total) * 100.0, 2)
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid marks or passing year."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE school_records
            SET board = %s, passing_year = %s, marks_obtained = %s, marks_total = %s, percentage = %s
            WHERE id = %s
        """, (board, passing_year, marks_obtained, marks_total, percentage, record_id))
        conn.commit()
        return jsonify({"success": True, "message": "School record updated."})
    finally:
        cur.close()
        conn.close()


@app.route("/api/school-records/<int:record_id>", methods=["DELETE"])
def delete_school_record(record_id):
    """Deletes a school record."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM school_records WHERE id = %s", (record_id,))
        conn.commit()
        return jsonify({"success": True, "message": "School record removed."})
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 7. SEMESTER RESULTS CRUD
# ==============================================================================
@app.route("/api/students/<int:student_id>/semester-results", methods=["GET"])
def get_semester_results(student_id):
    """Lists all semester results for a student."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, student_id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count, is_gap_after
            FROM semester_results
            WHERE student_id = %s
            ORDER BY semester_number ASC
        """, (student_id,))
        return jsonify({"success": True, "results": cur.fetchall()})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/semester-results", methods=["POST"])
def add_semester_result(student_id):
    """Creates a semester result record for a student."""
    data = request.get_json(silent=True) or {}
    semester_number = data.get("semester_number")
    academic_year = str(data.get("academic_year", "")).strip()
    sgpa = data.get("sgpa")
    cgpa = data.get("cgpa")
    result_status = data.get("result_status", "Pass")
    backlog_count = data.get("backlog_count", 0)
    is_gap_after = 1 if data.get("is_gap_after") else 0

    if not semester_number or not academic_year or sgpa is None or cgpa is None:
        return jsonify({"success": False, "message": "Semester, academic year, SGPA, and CGPA are required."}), 400

    try:
        semester_number = int(semester_number)
        sgpa = float(sgpa)
        cgpa = float(cgpa)
        backlog_count = int(backlog_count)
        if semester_number < 1 or semester_number > 10:
            return jsonify({"success": False, "message": "Semester must be between 1 and 10."}), 400
        if sgpa < 0.0 or sgpa > 10.0 or cgpa < 0.0 or cgpa > 10.0:
            return jsonify({"success": False, "message": "SGPA and CGPA must be between 0.0 and 10.0."}), 400
        if backlog_count < 0:
            return jsonify({"success": False, "message": "Backlog count cannot be negative."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid numeric values supplied."}), 400

    if result_status not in ("Pass", "ATKT", "Fail", "Pending"):
        return jsonify({"success": False, "message": "Invalid result status."}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Check duplicate semester for student
        cur.execute("""
            SELECT id FROM semester_results
            WHERE student_id = %s AND semester_number = %s
        """, (student_id, semester_number))
        if cur.fetchone():
            return jsonify({"success": False, "message": f"Semester {semester_number} record already exists."}), 409

        cur.execute("""
            INSERT INTO semester_results
            (student_id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count, is_gap_after)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (student_id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count, is_gap_after))
        conn.commit()
        new_id = cur.lastrowid

        # Keep legacy student_performance in sync
        cur.execute("""
            INSERT INTO student_performance (student_id, semester, sgpa, cgpa)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE sgpa = VALUES(sgpa), cgpa = VALUES(cgpa)
        """, (student_id, semester_number, sgpa, cgpa))
        conn.commit()

        return jsonify({"success": True, "message": f"Semester {semester_number} result recorded.", "id": new_id}), 201
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"success": False, "message": str(err)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/semester-results/<int:result_id>", methods=["PUT"])
def update_semester_result(result_id):
    """Updates SGPA, CGPA, status, and backlogs of a semester result."""
    data = request.get_json(silent=True) or {}
    sgpa = data.get("sgpa")
    cgpa = data.get("cgpa")
    result_status = data.get("result_status", "Pass")
    backlog_count = data.get("backlog_count", 0)
    is_gap_after = 1 if data.get("is_gap_after") else 0
    academic_year = str(data.get("academic_year", "")).strip()

    try:
        sgpa = float(sgpa)
        cgpa = float(cgpa)
        backlog_count = int(backlog_count)
        if sgpa < 0.0 or sgpa > 10.0 or cgpa < 0.0 or cgpa > 10.0 or backlog_count < 0:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid SGPA/CGPA or backlog count."}), 400

    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT student_id, semester_number FROM semester_results WHERE id = %s", (result_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Record not found."}), 404

        cur.execute("""
            UPDATE semester_results
            SET sgpa = %s, cgpa = %s, result_status = %s, backlog_count = %s, is_gap_after = %s,
                academic_year = COALESCE(NULLIF(%s, ''), academic_year)
            WHERE id = %s
        """, (sgpa, cgpa, result_status, backlog_count, is_gap_after, academic_year, result_id))

        # Also sync legacy table
        cur.execute("""
            UPDATE student_performance
            SET sgpa = %s, cgpa = %s
            WHERE student_id = %s AND semester = %s
        """, (sgpa, cgpa, row["student_id"], row["semester_number"]))

        conn.commit()
        return jsonify({"success": True, "message": "Semester result updated."})
    finally:
        cur.close()
        conn.close()


@app.route("/api/semester-results/<int:result_id>", methods=["DELETE"])
def delete_semester_result(result_id):
    """Deletes a semester result and cascading marks."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT student_id, semester_number FROM semester_results WHERE id = %s", (result_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"success": False, "message": "Record not found."}), 404

        cur.execute("DELETE FROM semester_results WHERE id = %s", (result_id,))
        cur.execute("DELETE FROM student_performance WHERE student_id = %s AND semester = %s", (row["student_id"], row["semester_number"]))
        conn.commit()
        return jsonify({"success": True, "message": "Semester result deleted."})
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 8. SUBJECTS & SUBJECT MARKS CRUD
# ==============================================================================
@app.route("/api/subjects", methods=["GET"])
def get_subjects():
    """Lists all available subjects."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, subject_code, subject_name, subject_type, credits FROM subjects ORDER BY subject_code ASC")
        return jsonify({"success": True, "subjects": cur.fetchall()})
    finally:
        cur.close()
        conn.close()


@app.route("/api/subjects", methods=["POST"])
def add_subject():
    """Adds a new subject to the curriculum."""
    data = request.get_json(silent=True) or {}
    code = str(data.get("subject_code", "")).strip().upper()
    name = str(data.get("subject_name", "")).strip()
    stype = data.get("subject_type", "Theory")
    credits = data.get("credits", 3.0)

    if not code or not name or stype not in ("Theory", "Lab"):
        return jsonify({"success": False, "message": "Subject code, name, and type (Theory/Lab) are required."}), 400

    try:
        credits = float(credits)
        if credits < 0 or credits > 10:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Credits must be a number between 0 and 10."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO subjects (subject_code, subject_name, subject_type, credits)
            VALUES (%s, %s, %s, %s)
        """, (code, name, stype, credits))
        conn.commit()
        return jsonify({"success": True, "message": "Subject registered.", "id": cur.lastrowid}), 201
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({"success": False, "message": "Subject code already exists."}), 409
        return jsonify({"success": False, "message": str(err)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
def delete_subject(subject_id):
    """Deletes a subject; enforces ON DELETE RESTRICT if referenced by academic marks."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM subjects WHERE id = %s", (subject_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Subject removed."})
    except mysql.connector.Error as err:
        if err.errno == 1451:
            return jsonify({
                "success": False,
                "message": "Cannot delete subject: referenced by student academic marks or attendance records."
            }), 409
        return jsonify({"success": False, "message": str(err)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/semester-results/<int:result_id>/marks", methods=["GET"])
def get_semester_marks(result_id):
    """Retrieves all subject marks for a given semester result."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT sm.id, sm.semester_result_id, sm.subject_id, s.subject_code, s.subject_name, s.subject_type,
                   sm.marks_obtained, sm.marks_total, sm.passing_marks, sm.component,
                   ROUND((sm.marks_obtained / sm.marks_total) * 100, 2) AS percentage,
                   CASE WHEN sm.marks_obtained >= sm.passing_marks THEN 'Pass' ELSE 'Fail' END AS pass_status
            FROM subject_marks sm
            JOIN subjects s ON sm.subject_id = s.id
            WHERE sm.semester_result_id = %s
            ORDER BY s.subject_code ASC
        """, (result_id,))
        return jsonify({"success": True, "marks": cur.fetchall()})
    finally:
        cur.close()
        conn.close()


@app.route("/api/semester-results/<int:result_id>/marks", methods=["POST"])
def add_subject_mark(result_id):
    """Adds a subject mark record to a semester result."""
    data = request.get_json(silent=True) or {}
    subject_id = data.get("subject_id")
    marks_obtained = data.get("marks_obtained")
    marks_total = data.get("marks_total", 100.0)
    passing_marks = data.get("passing_marks", 40.0)
    component = data.get("component", "Final")

    if not subject_id or marks_obtained is None:
        return jsonify({"success": False, "message": "Subject ID and marks obtained are required."}), 400

    try:
        subject_id = int(subject_id)
        marks_obtained = float(marks_obtained)
        marks_total = float(marks_total)
        passing_marks = float(passing_marks)
        if marks_obtained < 0 or marks_obtained > marks_total or marks_total <= 0:
            return jsonify({"success": False, "message": "Marks obtained must be between 0 and maximum marks."}), 400
        if passing_marks < 0 or passing_marks > marks_total:
            return jsonify({"success": False, "message": "Passing marks must be between 0 and maximum marks."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid numeric mark values."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO subject_marks (semester_result_id, subject_id, marks_obtained, marks_total, passing_marks, component)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (result_id, subject_id, marks_obtained, marks_total, passing_marks, component))
        conn.commit()
        return jsonify({"success": True, "message": "Subject mark recorded.", "id": cur.lastrowid}), 201
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify({"success": False, "message": "Mark entry for this subject and component already exists."}), 409
        return jsonify({"success": False, "message": str(err)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/marks/<int:mark_id>", methods=["DELETE"])
def delete_subject_mark(mark_id):
    """Deletes a subject mark record."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM subject_marks WHERE id = %s", (mark_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Mark record removed."})
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 9. ATTENDANCE & SUBJECT ANALYTICS
# ==============================================================================
@app.route("/api/students/<int:student_id>/attendance", methods=["GET"])
def get_student_attendance(student_id):
    """Retrieves detailed attendance records for a student."""
    threshold = float(request.args.get("threshold", 75.0))
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT a.id, a.student_id, a.subject_id, s.subject_code, s.subject_name, s.subject_type,
                   a.academic_year, a.semester_number, a.classes_held, a.classes_attended,
                   CASE WHEN a.classes_held > 0 
                        THEN ROUND((a.classes_attended / a.classes_held) * 100, 2)
                        ELSE 0.0 END AS attendance_percentage,
                   CASE WHEN a.classes_held > 0 AND (a.classes_attended / a.classes_held) * 100 < %s
                        THEN 1 ELSE 0 END AS is_warning
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.id
            WHERE a.student_id = %s
            ORDER BY a.semester_number ASC, s.subject_code ASC
        """, (threshold, student_id))
        records = cur.fetchall()

        # Summary calculations
        total_held = sum(r["classes_held"] for r in records)
        total_attended = sum(r["classes_attended"] for r in records)
        overall_pct = round((total_attended / total_held * 100), 2) if total_held > 0 else 0.0
        warnings_count = sum(1 for r in records if r["is_warning"] == 1)

        return jsonify({
            "success": True,
            "threshold": threshold,
            "records": records,
            "summary": {
                "total_held": total_held,
                "total_attended": total_attended,
                "overall_percentage": overall_pct,
                "warnings_count": warnings_count,
                "is_critical": overall_pct < threshold
            }
        })
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/attendance", methods=["POST"])
def add_student_attendance(student_id):
    """Records attendance figures for a subject and semester."""
    data = request.get_json(silent=True) or {}
    subject_id = data.get("subject_id")
    academic_year = str(data.get("academic_year", "")).strip()
    semester_number = data.get("semester_number")
    classes_held = data.get("classes_held")
    classes_attended = data.get("classes_attended")

    if not subject_id or not academic_year or semester_number is None or classes_held is None or classes_attended is None:
        return jsonify({"success": False, "message": "All attendance fields are required."}), 400

    try:
        subject_id = int(subject_id)
        semester_number = int(semester_number)
        classes_held = int(classes_held)
        classes_attended = int(classes_attended)
        if classes_held < 0 or classes_attended < 0 or classes_attended > classes_held:
            return jsonify({"success": False, "message": "Attended classes cannot exceed classes held or be negative."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid integer values for classes."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO attendance (student_id, subject_id, academic_year, semester_number, classes_held, classes_attended)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE classes_held = VALUES(classes_held), classes_attended = VALUES(classes_attended)
        """, (student_id, subject_id, academic_year, semester_number, classes_held, classes_attended))
        conn.commit()
        return jsonify({"success": True, "message": "Attendance saved successfully.", "id": cur.lastrowid}), 201
    finally:
        cur.close()
        conn.close()


@app.route("/api/attendance/<int:attendance_id>", methods=["DELETE"])
def delete_attendance(attendance_id):
    """Deletes an attendance entry."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM attendance WHERE id = %s", (attendance_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Attendance record deleted."})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/subject-analytics", methods=["GET"])
def get_subject_analytics(student_id):
    """
    Computes subject analytics:
    - Theory vs Lab performance metrics
    - Average marks percentage
    - Marks obtained vs total
    - Passing threshold checks
    - Failed subject attempts count
    """
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT 
                s.subject_type,
                COUNT(sm.id) AS total_evaluations,
                ROUND(AVG((sm.marks_obtained / sm.marks_total) * 100), 2) AS avg_percentage,
                SUM(sm.marks_obtained) AS total_marks_obtained,
                SUM(sm.marks_total) AS total_marks_possible,
                SUM(CASE WHEN sm.marks_obtained < sm.passing_marks THEN 1 ELSE 0 END) AS failed_attempts
            FROM subject_marks sm
            JOIN semester_results sr ON sm.semester_result_id = sr.id
            JOIN subjects s ON sm.subject_id = s.id
            WHERE sr.student_id = %s
            GROUP BY s.subject_type
        """, (student_id,))
        breakdown = cur.fetchall()

        cur.execute("""
            SELECT 
                s.subject_code,
                s.subject_name,
                s.subject_type,
                sm.marks_obtained,
                sm.marks_total,
                sm.passing_marks,
                ROUND((sm.marks_obtained / sm.marks_total) * 100, 2) AS percentage,
                CASE WHEN sm.marks_obtained >= sm.passing_marks THEN 'Pass' ELSE 'Fail' END AS status
            FROM subject_marks sm
            JOIN semester_results sr ON sm.semester_result_id = sr.id
            JOIN subjects s ON sm.subject_id = s.id
            WHERE sr.student_id = %s
            ORDER BY sr.semester_number ASC, s.subject_code ASC
        """, (student_id,))
        detailed = cur.fetchall()

        total_evals = len(detailed)
        total_failed = sum(1 for m in detailed if m["status"] == "Fail")
        overall_avg = round(sum(m["percentage"] for m in detailed) / total_evals, 2) if total_evals > 0 else 0.0

        return jsonify({
            "success": True,
            "overall_average": overall_avg,
            "total_evaluations": total_evals,
            "failed_attempts": total_failed,
            "type_breakdown": breakdown,
            "evaluations": detailed
        })
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 10. ACADEMIC GAP YEARS CRUD
# ==============================================================================
@app.route("/api/students/<int:student_id>/gap-years", methods=["GET"])
def get_student_gap_years(student_id):
    """Retrieves all documented gap years for a student."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, student_id, start_year, end_year, reason_category, notes
            FROM gap_years
            WHERE student_id = %s
            ORDER BY start_year ASC
        """, (student_id,))
        return jsonify({"success": True, "gap_years": cur.fetchall()})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/gap-years", methods=["POST"])
def add_student_gap_year(student_id):
    """Adds an academic gap year entry."""
    data = request.get_json(silent=True) or {}
    start_year = data.get("start_year")
    end_year = data.get("end_year")
    category = data.get("reason_category", "Academic")
    notes = str(data.get("notes", "")).strip()

    valid_cats = ("Academic", "Medical", "Personal", "Other")
    if category not in valid_cats or start_year is None or end_year is None:
        return jsonify({"success": False, "message": f"Start year, end year, and valid category ({valid_cats}) required."}), 400

    try:
        start_year = int(start_year)
        end_year = int(end_year)
        if end_year < start_year or start_year < 1990:
            return jsonify({"success": False, "message": "End year must be greater than or equal to start year."}), 400
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid year values."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO gap_years (student_id, start_year, end_year, reason_category, notes)
            VALUES (%s, %s, %s, %s, %s)
        """, (student_id, start_year, end_year, category, notes))
        conn.commit()
        return jsonify({"success": True, "message": "Gap year recorded.", "id": cur.lastrowid}), 201
    finally:
        cur.close()
        conn.close()


@app.route("/api/gap-years/<int:gap_id>", methods=["DELETE"])
def delete_gap_year(gap_id):
    """Deletes a gap year record."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM gap_years WHERE id = %s", (gap_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Gap year record deleted."})
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 11. ACTIVITIES, SEMINARS & CERTIFICATES CRUD
# ==============================================================================
@app.route("/api/students/<int:student_id>/activities", methods=["GET"])
def get_student_activities(student_id):
    """Retrieves activities for a student with optional category filter."""
    act_type = request.args.get("type", "").strip()
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        if act_type:
            cur.execute("""
                SELECT id, student_id, title, activity_type, organization, activity_date, description
                FROM activities
                WHERE student_id = %s AND activity_type = %s
                ORDER BY activity_date DESC
            """, (student_id, act_type))
        else:
            cur.execute("""
                SELECT id, student_id, title, activity_type, organization, activity_date, description
                FROM activities
                WHERE student_id = %s
                ORDER BY activity_date DESC
            """, (student_id,))
        return jsonify({"success": True, "activities": cur.fetchall()})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/activities", methods=["POST"])
def add_student_activity(student_id):
    """Adds an activity entry."""
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    act_type = data.get("activity_type")
    organization = str(data.get("organization", "")).strip()
    activity_date = data.get("activity_date")
    description = str(data.get("description", "")).strip()

    valid_types = ("Technical", "Co-curricular", "Extra-curricular")
    if not title or act_type not in valid_types:
        return jsonify({"success": False, "message": f"Title and valid activity type ({valid_types}) required."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO activities (student_id, title, activity_type, organization, activity_date, description)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, title, act_type, organization or None, activity_date or None, description or None))
        conn.commit()
        return jsonify({"success": True, "message": "Activity recorded.", "id": cur.lastrowid}), 201
    finally:
        cur.close()
        conn.close()


@app.route("/api/activities/<int:activity_id>", methods=["DELETE"])
def delete_activity(activity_id):
    """Deletes an activity entry."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM activities WHERE id = %s", (activity_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Activity removed."})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/seminars", methods=["GET"])
def get_student_seminars(student_id):
    """Retrieves seminars for a student."""
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("""
            SELECT id, student_id, title, seminar_scope, organizer, seminar_date, certificate_url
            FROM seminars
            WHERE student_id = %s
            ORDER BY seminar_date DESC
        """, (student_id,))
        return jsonify({"success": True, "seminars": cur.fetchall()})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/seminars", methods=["POST"])
def add_student_seminar(student_id):
    """Adds a seminar entry."""
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    scope = data.get("seminar_scope")
    organizer = str(data.get("organizer", "")).strip()
    seminar_date = data.get("seminar_date")
    certificate_url = str(data.get("certificate_url", "")).strip()

    if not title or scope not in ("Internal", "External"):
        return jsonify({"success": False, "message": "Title and scope (Internal/External) are required."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO seminars (student_id, title, seminar_scope, organizer, seminar_date, certificate_url)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (student_id, title, scope, organizer or None, seminar_date or None, certificate_url or None))
        conn.commit()
        return jsonify({"success": True, "message": "Seminar recorded.", "id": cur.lastrowid}), 201
    finally:
        cur.close()
        conn.close()


@app.route("/api/seminars/<int:seminar_id>", methods=["DELETE"])
def delete_seminar(seminar_id):
    """Deletes a seminar record."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM seminars WHERE id = %s", (seminar_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Seminar record deleted."})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/certificates", methods=["GET"])
def get_student_certificates(student_id):
    """Retrieves certificates and achievements for a student."""
    cat = request.args.get("category", "").strip()
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        if cat:
            cur.execute("""
                SELECT id, student_id, title, issuer, category, issue_date, credential_url, notes
                FROM certificates
                WHERE student_id = %s AND category = %s
                ORDER BY issue_date DESC
            """, (student_id, cat))
        else:
            cur.execute("""
                SELECT id, student_id, title, issuer, category, issue_date, credential_url, notes
                FROM certificates
                WHERE student_id = %s
                ORDER BY issue_date DESC
            """, (student_id,))
        return jsonify({"success": True, "certificates": cur.fetchall()})
    finally:
        cur.close()
        conn.close()


@app.route("/api/students/<int:student_id>/certificates", methods=["POST"])
def add_student_certificate(student_id):
    """Adds a certificate or achievement record."""
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    issuer = str(data.get("issuer", "")).strip()
    category = data.get("category")
    issue_date = data.get("issue_date")
    credential_url = str(data.get("credential_url", "")).strip()
    notes = str(data.get("notes", "")).strip()

    valid_cats = ("Course", "Hackathon", "Internship", "Achievement", "Seminar", "Other")
    if not title or not issuer or category not in valid_cats:
        return jsonify({"success": False, "message": f"Title, issuer, and valid category ({valid_cats}) required."}), 400

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO certificates (student_id, title, issuer, category, issue_date, credential_url, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (student_id, title, issuer, category, issue_date or None, credential_url or None, notes or None))
        conn.commit()
        return jsonify({"success": True, "message": "Certificate added.", "id": cur.lastrowid}), 201
    finally:
        cur.close()
        conn.close()


@app.route("/api/certificates/<int:certificate_id>", methods=["DELETE"])
def delete_certificate(certificate_id):
    """Deletes a certificate record."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM certificates WHERE id = %s", (certificate_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Certificate removed."})
    finally:
        cur.close()
        conn.close()


# ==============================================================================
# 12. CGPA TARGET PREDICTOR
# ==============================================================================
@app.route("/api/predict-cgpa", methods=["POST"])
def predict_cgpa():
    """
    Computes required average SGPA for remaining semesters to achieve a target CGPA.
    Formula:
      Target SGPA = [(Desired CGPA * Total Sems) - (Current CGPA * Completed Sems)] / Remaining Sems
    """
    data = request.get_json(silent=True) or {}
    try:
        current_cgpa = float(data.get("current_cgpa", 0.0))
        completed_sems = int(data.get("completed_sems", 0))
        total_sems = int(data.get("total_sems", 8))
        desired_cgpa = float(data.get("desired_cgpa", 0.0))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "All calculator inputs must be valid numeric values."}), 400

    if completed_sems < 0 or total_sems <= 0 or completed_sems > total_sems:
        return jsonify({"success": False, "message": "Completed semesters must be between 0 and total programme semesters."}), 400

    if current_cgpa < 0.0 or current_cgpa > 10.0 or desired_cgpa < 0.0 or desired_cgpa > 10.0:
        return jsonify({"success": False, "message": "CGPA values must range between 0.00 and 10.00."}), 400

    remaining_sems = total_sems - completed_sems

    if remaining_sems == 0:
        achieved = current_cgpa >= desired_cgpa
        return jsonify({
            "success": True,
            "remaining_semesters": 0,
            "status": "COMPLETED",
            "required_sgpa": None,
            "message": f"Programme completed. Final CGPA is {current_cgpa:.2f} (Target was {desired_cgpa:.2f}).",
            "achievable": achieved,
            "assumptions": "Zero remaining semesters. No further grade updates possible."
        })

    # Mathematical calculation
    total_target_points = desired_cgpa * total_sems
    current_earned_points = current_cgpa * completed_sems
    required_points = total_target_points - current_earned_points
    required_sgpa = round(required_points / remaining_sems, 2)

    formula_str = f"[({desired_cgpa:.2f} × {total_sems}) - ({current_cgpa:.2f} × {completed_sems})] / {remaining_sems} = {required_sgpa:.2f}"

    if required_sgpa > 10.0:
        achievable = False
        status = "IMPOSSIBLE"
        advice = f"Mathematically impossible: requires an average SGPA of {required_sgpa:.2f}, which exceeds the maximum scale of 10.00."
    elif required_sgpa <= 0.0:
        achievable = True
        status = "ALREADY_ACHIEVED"
        advice = f"Target already guaranteed! Minimum passing SGPA of 4.00 in remaining semesters will yield a final CGPA higher than {desired_cgpa:.2f}."
    else:
        achievable = True
        status = "ACHIEVABLE"
        advice = f"You need to maintain an average SGPA of at least {required_sgpa:.2f} across your remaining {remaining_sems} semesters."

    return jsonify({
        "success": True,
        "current_cgpa": current_cgpa,
        "completed_semesters": completed_sems,
        "remaining_semesters": remaining_sems,
        "desired_cgpa": desired_cgpa,
        "required_sgpa": required_sgpa,
        "achievable": achievable,
        "status": status,
        "formula": formula_str,
        "advice": advice,
        "assumptions": "Calculation assumes equal weight across all semesters. Official university CGPA calculations weight credits per semester, which may alter actual required performance."
    })


# ==============================================================================
# 13. GOOGLE SHEETS GENUINE SYNCHRONIZATION
# ==============================================================================
@app.route("/api/sync/google-sheets", methods=["POST"])
def trigger_google_sheets_sync():
    """
    Triggers authentic one-way synchronization of all 10 MySQL tables
    to destination Google Sheet tabs using the official Google Sheets API v4.
    If 'method' parameter is 'webapp', routes to Apps Script Webhook.
    """
    data = request.get_json(silent=True) or {}
    method = data.get("method") or request.args.get("method")

    if method == "webapp":
        return trigger_google_sheets_webapp_sync()

    result = sync_all_tables_to_sheets(get_db_connection)
    status_code = 200 if result.get("success") else (503 if result.get("status") == "BLOCKED" else 500)
    return jsonify(result), status_code


@app.route("/api/sync/google-sheets-webapp", methods=["POST"])
def trigger_google_sheets_webapp_sync():
    """
    Pushes 1,000 students and evaluations directly to the Google Apps Script Web App URL.
    """
    webapp_url = os.getenv("GOOGLE_SHEET_WEBAPP_URL", "").strip()
    if not webapp_url:
        data = request.get_json(silent=True) or {}
        webapp_url = data.get("webapp_url", "").strip()

    if not webapp_url:
        return jsonify({
            "success": False,
            "status": "BLOCKED",
            "message": "GOOGLE_SHEET_WEBAPP_URL is not configured."
        }), 400

    try:
        from sync_to_google_sheet_webapp import fetch_data_from_mysql
        import requests as req
        import time

        students, semester_results, metrics = fetch_data_from_mysql()
        payload = {
            "action": "sync_all",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "students": students,
            "semester_results": semester_results,
            "metrics": metrics
        }

        resp = req.post(webapp_url, json=payload, headers={"Content-Type": "application/json"}, timeout=60, allow_redirects=True)
        try:
            res_data = resp.json()
        except Exception:
            res_data = {"raw": resp.text[:200]}

        LAST_SYNC_INFO["last_sync_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        LAST_SYNC_INFO["status"] = "Success (Web App)" if resp.status_code == 200 else "Failed"
        LAST_SYNC_INFO["rows_synced"] = len(students) + len(semester_results)
        LAST_SYNC_INFO["tables_synced"] = 2

        return jsonify({
            "success": resp.status_code == 200,
            "method": "google_apps_script_webapp",
            "webapp_url": webapp_url,
            "students_synced": len(students),
            "semesters_synced": len(semester_results),
            "response": res_data
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "method": "google_apps_script_webapp",
            "error": str(e)
        }), 500



@app.route("/api/sync/google-sheets/status", methods=["GET"])
def get_google_sheets_status():
    """Returns the current status of Google Sheets synchronization."""
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    service_acc = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    webapp_url = os.getenv("GOOGLE_SHEET_WEBAPP_URL", "")
    is_configured = bool(webapp_url or (sheet_id and service_acc and os.path.exists(service_acc)))

    return jsonify({
        "success": True,
        "configured": is_configured,
        "method": "google_apps_script_webapp" if webapp_url else "service_account",
        "webapp_url": webapp_url if webapp_url else "Not Configured",
        "sheet_id": sheet_id if sheet_id else "Not Configured",
        "service_account_file": service_acc if service_acc else "Not Configured",
        "last_sync": LAST_SYNC_INFO
    })



# ==============================================================================
# 14. SAFE MIGRATION ENDPOINT (Non-Destructive)
# ==============================================================================
@app.route("/api/admin/migrate-legacy", methods=["POST"])
def migrate_legacy_performance():
    """Safely synchronizes records between student_performance and semester_results."""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO semester_results (student_id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count, is_gap_after)
            SELECT 
                sp.student_id,
                sp.semester,
                CONCAT(COALESCE(s.admission_year + FLOOR((sp.semester - 1) / 2), 2022), '-', COALESCE(s.admission_year + FLOOR((sp.semester - 1) / 2) + 1, 2023)),
                COALESCE(sp.sgpa, 0.0),
                COALESCE(sp.cgpa, 0.0),
                CASE WHEN COALESCE(sp.sgpa, 0.0) >= 4.0 THEN 'Pass' ELSE 'ATKT' END,
                0,
                0
            FROM student_performance sp
            JOIN students s ON sp.student_id = s.student_id
            ON DUPLICATE KEY UPDATE sgpa = VALUES(sgpa), cgpa = VALUES(cgpa)
        """)
        conn.commit()
        migrated = cur.rowcount
        return jsonify({"success": True, "message": f"Successfully evaluated legacy records. Rows affected: {migrated}"})
    except mysql.connector.Error as err:
        conn.rollback()
        return jsonify({"success": False, "message": str(err)}), 500
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "0") in ("1", "true", "True")
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=debug_mode)