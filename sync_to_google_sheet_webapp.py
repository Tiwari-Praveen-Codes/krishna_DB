"""
ScholarTrack -> Google Sheets Web App Synchronizer
Connects to local MySQL (student_ledger) and pushes all 10 normalized tables
directly into the matching Google Sheets tabs:
1. Students
2. School_Records
3. Semester_Results
4. Subjects
5. Subject_Marks
6. Attendance
7. Gap_Years
8. Activities
9. Seminars
10. Certificates
"""

import os
import sys
import time
import requests
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

# MySQL Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Pravin@_123")
DB_NAME = os.getenv("DB_NAME", "student_ledger")

# Google Apps Script Web App URL
DEFAULT_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbxyHpAyj2hBfcMtcFGTbzBb-PnJfcy1O1ydX2q_h-HcWVSkjENeRUdjIa3mC0NbSHas/exec"
WEBAPP_URL = os.getenv("GOOGLE_SHEET_WEBAPP_URL", DEFAULT_WEBAPP_URL)

TABLE_MAPPINGS = [
    {
        "table": "students",
        "tab_name": "Students",
        "columns": ["student_id", "student_name", "roll_no", "branch", "admission_year", "email", "current_status"],
        "headers": ["Student ID", "Full Name", "Roll No", "Branch / Department", "Admission Year", "Email", "Status"]
    },
    {
        "table": "school_records",
        "tab_name": "School_Records",
        "columns": ["id", "student_id", "level", "board", "passing_year", "marks_obtained", "marks_total", "percentage"],
        "headers": ["ID", "Student ID", "Level", "Board", "Passing Year", "Marks Obtained", "Marks Total", "Percentage (%)"]
    },
    {
        "table": "semester_results",
        "tab_name": "Semester_Results",
        "columns": ["id", "student_id", "semester_number", "academic_year", "sgpa", "cgpa", "result_status", "backlog_count", "is_gap_after"],
        "headers": ["ID", "Student ID", "Semester", "Academic Year", "SGPA", "CGPA", "Result Status", "Backlog Count", "Gap After"]
    },
    {
        "table": "subjects",
        "tab_name": "Subjects",
        "columns": ["id", "subject_code", "subject_name", "subject_type", "credits"],
        "headers": ["ID", "Subject Code", "Subject Name", "Type", "Credits"]
    },
    {
        "table": "subject_marks",
        "tab_name": "Subject_Marks",
        "columns": ["id", "semester_result_id", "subject_id", "marks_obtained", "marks_total", "passing_marks", "component"],
        "headers": ["ID", "Semester Result ID", "Subject ID", "Marks Obtained", "Marks Total", "Passing Marks", "Component"]
    },
    {
        "table": "attendance",
        "tab_name": "Attendance",
        "columns": ["id", "student_id", "subject_id", "academic_year", "semester_number", "classes_held", "classes_attended"],
        "headers": ["ID", "Student ID", "Subject ID", "Academic Year", "Semester", "Classes Held", "Classes Attended"]
    },
    {
        "table": "gap_years",
        "tab_name": "Gap_Years",
        "columns": ["id", "student_id", "start_year", "end_year", "reason_category", "notes"],
        "headers": ["ID", "Student ID", "Start Year", "End Year", "Reason Category", "Notes"]
    },
    {
        "table": "activities",
        "tab_name": "Activities",
        "columns": ["id", "student_id", "title", "activity_type", "organization", "activity_date", "description"],
        "headers": ["ID", "Student ID", "Title", "Type", "Organization", "Activity Date", "Description"]
    },
    {
        "table": "seminars",
        "tab_name": "Seminars",
        "columns": ["id", "student_id", "title", "seminar_scope", "organizer", "seminar_date", "certificate_url"],
        "headers": ["ID", "Student ID", "Title", "Scope", "Organizer", "Date", "Certificate URL"]
    },
    {
        "table": "certificates",
        "tab_name": "Certificates",
        "columns": ["id", "student_id", "title", "issuer", "category", "issue_date", "credential_url", "notes"],
        "headers": ["ID", "Student ID", "Title", "Issuer", "Category", "Issue Date", "Credential URL", "Notes"]
    }
]


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def format_row_value(val):
    if val is None:
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


def sync_single_tab(mapping, url, conn):
    """Pulls rows from MySQL table and pushes to Google Apps Script tab."""
    table = mapping["table"]
    tab_name = mapping["tab_name"]
    cols = ", ".join(f"`{c}`" for c in mapping["columns"])
    headers = mapping["headers"]

    cursor = conn.cursor()
    cursor.execute(f"SELECT {cols} FROM `{table}`")
    raw_rows = cursor.fetchall()
    cursor.close()

    formatted_rows = []
    for r in raw_rows:
        formatted_rows.append([format_row_value(v) for v in r])

    print(f"[*] Syncing '{tab_name}' ({len(formatted_rows)} rows from MySQL `{table}`)...", end=" ", flush=True)

    payload = {
        "action": "sync_tab",
        "tab_name": tab_name,
        "headers": headers,
        "rows": formatted_rows
    }

    try:
        t0 = time.time()
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,
            allow_redirects=True
        )
        t_diff = time.time() - t0

        if resp.status_code == 200:
            try:
                res_json = resp.json()
                if res_json.get("status") == "success":
                    print(f"[OK] ({t_diff:.1f}s)")
                    return True, len(formatted_rows)
                else:
                    print(f"[WARN] Apps Script returned: {res_json.get('message', res_json)}")
                    return False, len(formatted_rows)
            except Exception:
                print(f"[HTML/200] Apps Script received data ({t_diff:.1f}s)")
                return True, len(formatted_rows)
        else:
            print(f"[FAIL] HTTP {resp.status_code}")
            return False, 0
    except Exception as e:
        print(f"[ERROR] {e}")
        return False, 0


def sync_all_tabs_to_google_sheet(webapp_url: str = None):
    url = webapp_url or WEBAPP_URL
    print("\n" + "=" * 65)
    print("[SCHOLARTRACK] -> FULL 10-TABLE GOOGLE SHEETS LIVE SYNC")
    print("=" * 65)
    print(f"Target Web App: {url}")
    print(f"MySQL Source:   {DB_HOST}:{DB_PORT} / {DB_NAME}\n")

    conn = get_db_connection()
    total_synced_tables = 0
    total_synced_rows = 0
    start_time = time.time()

    try:
        for idx, mapping in enumerate(TABLE_MAPPINGS, 1):
            print(f"[{idx}/10] ", end="")
            success, rows_count = sync_single_tab(mapping, url, conn)
            if success:
                total_synced_tables += 1
                total_synced_rows += rows_count

        total_elapsed = time.time() - start_time
        print("\n" + "=" * 65)
        print(f"[SUMMARY] Synchronized {total_synced_tables}/10 tables ({total_synced_rows:,} rows total) in {total_elapsed:.1f}s")
        print("=" * 65)
        return True, total_synced_rows

    finally:
        conn.close()


if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else WEBAPP_URL
    sync_all_tabs_to_google_sheet(url_arg)
