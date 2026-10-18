"""
ScholarTrack -> Google Sheets Web App Synchronizer
Connects to local MySQL (student_ledger) and pushes all 1,000 student records
and semester evaluations directly into Google Sheets via the Apps Script Web App URL.
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


def get_db_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )


def fetch_data_from_mysql():
    """Fetches students, semester results, and aggregate stats from MySQL."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Fetch Students
        print(f"[1/4] Fetching students from MySQL ({DB_NAME}.students)...")
        cursor.execute("""
            SELECT student_id, student_name, roll_no, branch, admission_year, email, current_status
            FROM students
            ORDER BY student_id ASC
        """)
        students = cursor.fetchall()
        print(f"      Retrieved {len(students)} student records.")

        # 2. Fetch Semester Results
        print("[2/4] Fetching semester evaluations...")
        cursor.execute("""
            SELECT id, student_id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count
            FROM semester_results
            ORDER BY student_id ASC, semester_number ASC
        """)
        semester_results = cursor.fetchall()
        print(f"      Retrieved {len(semester_results)} semester evaluations.")

        # 3. Fetch KPI metrics
        print("[3/4] Aggregating DBMS KPI metrics...")
        cursor.execute("SELECT COUNT(*) AS total_students FROM students")
        total_students = cursor.fetchone()["total_students"]

        cursor.execute("SELECT COUNT(*) AS total_records, ROUND(AVG(cgpa), 2) AS average_cgpa FROM semester_results")
        perf_data = cursor.fetchone()

        cursor.execute("SELECT COUNT(*) AS total_activities FROM activities")
        total_activities = cursor.fetchone()["total_activities"]

        metrics = {
            "total_students": total_students,
            "total_records": perf_data["total_records"],
            "average_cgpa": float(perf_data["average_cgpa"]) if perf_data["average_cgpa"] else 0.0,
            "total_activities": total_activities
        }

        return students, semester_results, metrics

    finally:
        cursor.close()
        conn.close()


def sync_to_google_sheet(webapp_url: str = None):
    url = webapp_url or WEBAPP_URL
    print("\n" + "=" * 65)
    print("[SCHOLARTRACK] -> GOOGLE SHEETS LIVE SYNCHRONIZER")
    print("=" * 65)
    print(f"Destination: {url}")

    start_time = time.time()
    students, semester_results, metrics = fetch_data_from_mysql()

    payload = {
        "action": "sync_all",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "students": students,
        "semester_results": semester_results,
        "metrics": metrics
    }

    print(f"\n[4/4] Transmitting {len(students)} students and {len(semester_results)} evaluations to Google Sheets Web App...")

    try:
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=90,
            allow_redirects=True
        )

        elapsed = time.time() - start_time

        print(f"Server HTTP Status: {response.status_code}")

        try:
            res_json = response.json()
            if res_json.get("status") == "success":
                print("\n" + "=" * 65)
                print(">>> [SUCCESS] GOOGLE SHEETS SYNCHRONIZATION COMPLETED!")
                print("=" * 65)
                print(f"- Total Students Synced: {len(students)}")
                print(f"- Total Semester Evaluations: {len(semester_results)}")
                print(f"- Time Taken: {elapsed:.2f} seconds")
                if "tabs_updated" in res_json:
                    for t in res_json["tabs_updated"]:
                        print(f"  * Tab '{t.get('tab')}': {t.get('row_count')} rows written")
                print("=" * 65)
                return True, res_json
            else:
                print(f"\n[NOTICE] Response from Apps Script: {res_json}")
                return False, res_json
        except Exception:
            # If Google Apps Script returned HTML (happens if new version isn't deployed yet)
            text_preview = response.text[:300].strip()
            print("\n" + "-" * 65)
            print("[NOTICE] Web App received request, but returned HTML instead of JSON.")
            print("Preview:", text_preview)
            print("\nREMINDER FOR DEPLOYMENT IN GOOGLE APPS SCRIPT:")
            print("1. Open Google Sheet > Extensions > Apps Script.")
            print("2. Paste code from 'google_sheets_code.gs' into Code.gs.")
            print("3. Click 'Deploy' > 'Manage deployments' > Edit (pencil icon).")
            print("4. Select 'Version: New version' and click 'Deploy'.")
            print("-" * 65)
            return False, {"raw": response.text}


    except Exception as e:
        print(f"\n[ERROR] Failed to reach Google Sheets Web App: {e}")
        return False, {"error": str(e)}


if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else WEBAPP_URL
    sync_to_google_sheet(url_arg)
