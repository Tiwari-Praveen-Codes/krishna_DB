"""
ScholarTrack Database Initialization & Migration Utility
Connects to MySQL, initializes schema, creates constraints,
and safely imports or seeds verified student progression data.
"""

import os
import sys
import mysql.connector
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Pravin@_123")
DB_NAME = os.getenv("DB_NAME", "student_ledger")


def get_admin_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD
    )


def get_database_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def init_database():
    print(f"Connecting to MySQL at {DB_HOST}:{DB_PORT} as {DB_USER}...")
    admin_conn = get_admin_connection()
    admin_cur = admin_conn.cursor()

    # Create target database
    admin_cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    print(f"Database `{DB_NAME}` ensured.")
    admin_cur.close()
    admin_conn.close()

    conn = get_database_connection()
    cur = conn.cursor()

    # Read and execute schema.sql
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as f:
            sql_script = f.read()

        # Split statements safely
        statements = [stmt.strip() for stmt in sql_script.split(";") if stmt.strip()]
        for stmt in statements:
            # Skip database creation statements since we're connected to target DB
            if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE "):
                continue
            try:
                cur.execute(stmt)
            except mysql.connector.Error as err:
                # Ignore table/index already exists warnings
                if err.errno not in (1050, 1061):
                    print(f"Notice on statement: {err}")
        conn.commit()
        print("Schema initialization completed.")

    # Check student count
    cur.execute("SELECT COUNT(*) FROM students")
    student_count = cur.fetchone()[0]
    print(f"Current student count in `{DB_NAME}`: {student_count}")

    # If empty, check if we can migrate from shruti_41 or seed
    if student_count == 0:
        print("Seeding initial dataset into student_ledger...")
        try:
            admin_conn = get_admin_connection()
            admin_cur = admin_conn.cursor(dictionary=True)
            admin_cur.execute("SHOW DATABASES LIKE 'shruti_41'")
            has_shruti = admin_cur.fetchone()

            if has_shruti:
                print("Found source data in `shruti_41`. Transferring 100 students and relational records...")
                # Transfer students
                admin_cur.execute("SELECT * FROM `shruti_41`.`students` ORDER BY id ASC")
                students = admin_cur.fetchall()
                for s in students:
                    cur.execute("""
                        INSERT INTO students (student_id, student_name, roll_no, branch, admission_year, email, current_status)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        s['id'],
                        s.get('full_name') or s.get('student_name', ''),
                        s.get('roll_number') or s.get('roll_no', ''),
                        s.get('department') or s.get('branch', 'Computer Science & Engineering'),
                        s.get('admission_year', 2022),
                        s.get('email', f"student{s['id']}@viva-technology.org"),
                        s.get('current_status', 'Active')
                    ))
                conn.commit()
                print(f"Imported {len(students)} students.")

                # Transfer school_records
                admin_cur.execute("SELECT * FROM `shruti_41`.`school_records`")
                for r in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO school_records (id, student_id, level, board, passing_year, marks_obtained, marks_total, percentage)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (r['id'], r['student_id'], r['level'], r['board'], r['passing_year'], r['marks_obtained'], r['marks_total'], r['percentage']))
                conn.commit()

                # Transfer subjects
                admin_cur.execute("SELECT * FROM `shruti_41`.`subjects`")
                for sub in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO subjects (id, subject_code, subject_name, subject_type, credits)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (sub['id'], sub['subject_code'], sub['subject_name'], sub['subject_type'], sub.get('credits', 3.0)))
                conn.commit()

                # Transfer semester_results
                admin_cur.execute("SELECT * FROM `shruti_41`.`semester_results`")
                for sem in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO semester_results (id, student_id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count, is_gap_after)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (sem['id'], sem['student_id'], sem['semester_number'], sem['academic_year'], sem['sgpa'], sem['cgpa'], sem['result_status'], sem['backlog_count'], sem['is_gap_after']))
                conn.commit()

                # Transfer subject_marks
                admin_cur.execute("SELECT * FROM `shruti_41`.`subject_marks`")
                for m in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO subject_marks (id, semester_result_id, subject_id, marks_obtained, marks_total, passing_marks, component)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (m['id'], m['semester_result_id'], m['subject_id'], m['marks_obtained'], m['marks_total'], m.get('passing_marks', 40.0), m.get('component', 'Final')))
                conn.commit()

                # Transfer attendance
                admin_cur.execute("SELECT * FROM `shruti_41`.`attendance`")
                for a in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO attendance (id, student_id, subject_id, academic_year, semester_number, classes_held, classes_attended)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (a['id'], a['student_id'], a['subject_id'], a['academic_year'], a['semester_number'], a['classes_held'], a['classes_attended']))
                conn.commit()

                # Transfer gap_years
                admin_cur.execute("SELECT * FROM `shruti_41`.`gap_years`")
                for g in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO gap_years (id, student_id, start_year, end_year, reason_category, notes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (g['id'], g['student_id'], g['start_year'], g['end_year'], g['reason_category'], g.get('notes', '')))
                conn.commit()

                # Transfer activities
                admin_cur.execute("SELECT * FROM `shruti_41`.`activities`")
                for act in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO activities (id, student_id, title, activity_type, organization, activity_date, description)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (act['id'], act['student_id'], act['title'], act['activity_type'], act['organization'], act['activity_date'], act['description']))
                conn.commit()

                # Transfer seminars
                admin_cur.execute("SELECT * FROM `shruti_41`.`seminars`")
                for sem in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO seminars (id, student_id, title, seminar_scope, organizer, seminar_date, certificate_url)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (sem['id'], sem['student_id'], sem['title'], sem['seminar_scope'], sem['organizer'], sem['seminar_date'], sem['certificate_url']))
                conn.commit()

                # Transfer certificates
                admin_cur.execute("SELECT * FROM `shruti_41`.`certificates`")
                for c in admin_cur.fetchall():
                    cur.execute("""
                        INSERT IGNORE INTO certificates (id, student_id, title, issuer, category, issue_date, credential_url, notes)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (c['id'], c['student_id'], c['title'], c['issuer'], c['category'], c['issue_date'], c['credential_url'], c.get('notes', '')))
                conn.commit()

                admin_cur.close()
                admin_conn.close()
                print("Successfully populated `student_ledger` from `shruti_41`!")
        except Exception as e:
            print(f"Import notice: {e}")

    # Populate legacy table `student_performance` from `semester_results` if empty
    cur.execute("SELECT COUNT(*) FROM student_performance")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT IGNORE INTO student_performance (student_id, semester, sgpa, cgpa)
            SELECT student_id, semester_number, sgpa, cgpa
            FROM semester_results
        """)
        conn.commit()
        print("Legacy student_performance populated for backwards compatibility.")

    # Verification summary
    print("\n--- DATABASE VERIFICATION SUMMARY ---")
    tables = [
        'students', 'school_records', 'semester_results', 'subjects',
        'subject_marks', 'attendance', 'gap_years', 'activities',
        'seminars', 'certificates', 'student_performance'
    ]
    for tbl in tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt = cur.fetchone()[0]
        print(f"  • {tbl}: {cnt} rows")

    cur.close()
    conn.close()
    print("Database ready.")


if __name__ == "__main__":
    init_database()
