"""
ScholarTrack Google Sheets Synchronization Module
Provides authentic one-way synchronization from MySQL to Google Sheets
using the official Google Sheets API v4.
"""

import os
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


TABLE_MAPPINGS = [
    {
        "table": "students",
        "tab_name": "Students",
        "columns": ["student_id", "student_name", "roll_no", "branch", "admission_year", "email", "current_status", "created_at"],
        "headers": ["Student ID", "Full Name", "Roll No", "Branch / Department", "Admission Year", "Email", "Status", "Created At"]
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
        "headers": ["ID", "Student ID", "Start Year", "End Year", "Category", "Notes"]
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

LAST_SYNC_INFO = {
    "last_sync_time": None,
    "status": "Never synchronized",
    "tables_synced": 0,
    "rows_synced": 0,
    "error": None
}


def get_sheets_service(service_account_file: str):
    """Initializes Google Sheets API client using service account file."""
    if not service_account_file or not os.path.exists(service_account_file):
        raise FileNotFoundError(f"Service account file '{service_account_file}' was not found.")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_file(
        service_account_file, scopes=scopes
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def ensure_worksheet_tabs(service, spreadsheet_id: str):
    """Ensures all 10 worksheet tabs exist in the Google Sheet."""
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    existing_sheets = [s["properties"]["title"] for s in sheet_metadata.get("sheets", [])]

    add_requests = []
    for mapping in TABLE_MAPPINGS:
        tab_name = mapping["tab_name"]
        if tab_name not in existing_sheets:
            add_requests.append({
                "addSheet": {
                    "properties": {
                        "title": tab_name
                    }
                }
            })

    if add_requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": add_requests}
        ).execute()


def sync_all_tables_to_sheets(get_db_conn_func, service_account_file: str = None, spreadsheet_id: str = None):
    """
    Synchronizes all 10 MySQL tables into corresponding Google Sheets tabs.
    Returns status dictionary.
    """
    global LAST_SYNC_INFO

    service_account_file = service_account_file or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    spreadsheet_id = spreadsheet_id or os.getenv("GOOGLE_SHEET_ID")

    if not service_account_file or not spreadsheet_id:
        error_msg = "Google Sheets credentials or Sheet ID not configured in environment variables (GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_SHEET_ID)."
        LAST_SYNC_INFO["status"] = "BLOCKED"
        LAST_SYNC_INFO["error"] = error_msg
        return {
            "success": False,
            "status": "BLOCKED",
            "message": error_msg,
            "details": {
                "service_account_configured": bool(service_account_file),
                "sheet_id_configured": bool(spreadsheet_id)
            }
        }

    if not os.path.exists(service_account_file):
        error_msg = f"Service account credentials file not found on disk: {service_account_file}"
        LAST_SYNC_INFO["status"] = "BLOCKED"
        LAST_SYNC_INFO["error"] = error_msg
        return {
            "success": False,
            "status": "BLOCKED",
            "message": error_msg
        }

    try:
        service = get_sheets_service(service_account_file)
        ensure_worksheet_tabs(service, spreadsheet_id)

        conn = get_db_conn_func()
        cur = conn.cursor(dictionary=True)

        total_rows = 0
        synced_tables = []

        try:
            for mapping in TABLE_MAPPINGS:
                tbl = mapping["table"]
                tab = mapping["tab_name"]
                cols = mapping["columns"]
                headers = mapping["headers"]

                col_str = ", ".join([f"`{c}`" for c in cols])
                cur.execute(f"SELECT {col_str} FROM `{tbl}`")
                db_rows = cur.fetchall()

                # Build row arrays
                values = [headers]
                for r in db_rows:
                    row_data = []
                    for c in cols:
                        val = r.get(c)
                        if isinstance(val, (datetime,)):
                            val = val.strftime("%Y-%m-%d %H:%M:%S")
                        elif val is None:
                            val = ""
                        else:
                            val = str(val)
                        row_data.append(val)
                    values.append(row_data)

                # Clear old data in the tab
                service.spreadsheets().values().clear(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{tab}'!A:Z"
                ).execute()

                # Write fresh data
                body = {"values": values}
                result = service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{tab}'!A1",
                    valueInputOption="USER_ENTERED",
                    body=body
                ).execute()

                updated_rows = result.get("updatedRows", len(values))
                total_rows += (len(values) - 1)
                synced_tables.append({"table": tbl, "tab": tab, "rows": len(values) - 1})

        finally:
            cur.close()
            conn.close()

        sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        LAST_SYNC_INFO = {
            "last_sync_time": sync_time,
            "status": "SUCCESS",
            "tables_synced": len(synced_tables),
            "rows_synced": total_rows,
            "error": None
        }

        return {
            "success": True,
            "status": "SUCCESS",
            "message": f"Successfully synchronized {len(synced_tables)} tables ({total_rows} total rows) to Google Sheets.",
            "last_sync_time": sync_time,
            "tables": synced_tables
        }

    except HttpError as http_err:
        err_msg = f"Google Sheets API Error ({http_err.resp.status}): {http_err._get_reason()}"
        LAST_SYNC_INFO["status"] = "FAILED"
        LAST_SYNC_INFO["error"] = err_msg
        return {"success": False, "status": "FAILED", "message": err_msg}

    except Exception as e:
        err_msg = f"Sync operation failed: {str(e)}"
        LAST_SYNC_INFO["status"] = "FAILED"
        LAST_SYNC_INFO["error"] = err_msg
        return {"success": False, "status": "FAILED", "message": err_msg}
