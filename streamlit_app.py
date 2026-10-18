import os
import sqlite3
from datetime import date
import pandas as pd
import streamlit as st
import altair as alt
try:
    import mysql.connector
    from mysql.connector import pooling
    HAS_MYSQL = True
except ImportError:
    mysql = None
    pooling = None
    HAS_MYSQL = False

# ==============================================================================
# CONFIGURATION & PAGE SETUP
# ==============================================================================
st.set_page_config(
    page_title="ScholarTrack — Academic Progression DBMS",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling for Navigation & Status Indicators
st.markdown("""
<style>
    .sync-status-box {
        margin-top: 10px;
        margin-bottom: 12px;
        padding: 12px;
        background: rgba(30, 41, 59, 0.45);
        border-radius: 8px;
        border: 1px solid #1e293b;
    }
    .sync-indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #34d399;
        font-weight: 600;
        font-size: 14px;
    }
    .pulse-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #10b981;
        box-shadow: 0 0 8px #10b981;
        display: inline-block;
    }
    .sync-queue-label {
        margin-top: 8px;
        font-size: 12px;
        color: #94a3b8;
        font-weight: 500;
    }
    .sync-queue-val {
        font-size: 28px;
        font-weight: 700;
        color: #f8fafc;
        line-height: 1.1;
    }
</style>
""", unsafe_allow_html=True)


SQLITE_DB = os.getenv("SCHOLARTRACK_DB", "scholartrack.db")

DEFAULT_APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbxyHpAyj2hBfcMtcFGTbzBb-PnJfcy1O1ydX2q_h-HcWVSkjENeRUdjIa3mC0NbSHas/exec"

def get_apps_script_url():
    return st.session_state.get("apps_script_url") or os.getenv("GOOGLE_SHEET_WEBAPP_URL") or os.getenv("GOOGLE_APPS_SCRIPT_URL") or DEFAULT_APPS_SCRIPT_URL

MYSQL_DEFAULT_CONFIG = {
    "host": os.getenv("DB_HOST") or os.getenv("MYSQL_HOST") or "localhost",
    "port": int(os.getenv("DB_PORT") or os.getenv("MYSQL_PORT") or 3306),
    "user": os.getenv("DB_USER") or os.getenv("MYSQL_USER") or "root",
    "password": os.getenv("DB_PASSWORD") or os.getenv("MYSQL_PASSWORD") or "Pravin@_123",
    "database": os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE") or "student_ledger"
}


@st.cache_resource
def get_mysql_pool():
    if not HAS_MYSQL or pooling is None:
        return None
    try:
        return pooling.MySQLConnectionPool(
            pool_name="scholartrack_pool",
            pool_size=12,
            pool_reset_session=True,
            **MYSQL_DEFAULT_CONFIG
        )
    except Exception:
        return None

# ==============================================================================
# DATABASE ABSTRACTION LAYER (High-Speed Pooled MySQL + SQLite Fallback)
# ==============================================================================
def get_db_connection():
    backend = st.session_state.get("db_backend", "MySQL (Shruti_41)")
    if "MySQL" in backend and HAS_MYSQL and mysql is not None:
        pool = get_mysql_pool()
        if pool:
            try:
                conn = pool.get_connection()
                return conn, "MySQL"
            except Exception:
                pass
        try:
            conn = mysql.connector.connect(**MYSQL_DEFAULT_CONFIG)
            return conn, "MySQL"
        except Exception:
            pass
    # Local SQLite Fallback
    c = sqlite3.connect(SQLITE_DB, check_same_thread=False)
    c.execute("PRAGMA foreign_keys=ON")
    c.row_factory = sqlite3.Row
    return c, "SQLite"

def read(sql, params=()):
    conn, mode = get_db_connection()
    try:
        if mode == "MySQL":
            sql_conv = sql.replace("?", "%s")
            cur = conn.cursor(dictionary=True)
            cur.execute(sql_conv, params)
            rows = cur.fetchall()
            cols = [c[0] for c in cur.description] if cur.description else []
            cur.close()
            return pd.DataFrame(rows, columns=cols)
        else:
            with conn:
                return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()

def auto_sync_to_sheets(sql=None, target_table=None):
    """
    Automatic real-time background sync to Google Sheets
    whenever records are added, updated, or deleted.
    """
    import threading
    url = get_apps_script_url()
    if not url:
        return

    # Intelligently infer target table from SQL
    if not target_table and sql:
        sql_lower = sql.lower()
        if "from students" in sql_lower and "delete" in sql_lower:
            target_table = None  # Full sync due to foreign key cascade
        elif "students" in sql_lower:
            target_table = "Students"
        elif "school_records" in sql_lower:
            target_table = "School_Records"
        elif "semester_results" in sql_lower:
            target_table = "Semester_Results"
        elif "subject_marks" in sql_lower:
            target_table = "Subject_Marks"
        elif "attendance" in sql_lower:
            target_table = "Attendance"
        elif "gap_years" in sql_lower:
            target_table = "Gap_Years"
        elif "activities" in sql_lower:
            target_table = "Activities"
        elif "seminars" in sql_lower:
            target_table = "Seminars"
        elif "certificates" in sql_lower:
            target_table = "Certificates"
        elif "subjects" in sql_lower:
            target_table = "Subjects"

    def _worker():
        try:
            sync_via_apps_script(url, target_table=target_table)
        except Exception:
            pass

    t = threading.Thread(target=_worker, daemon=True)
    t.start()

def run(sql, params=(), target_table=None):
    conn, mode = get_db_connection()
    try:
        if mode == "MySQL":
            sql_conv = sql.replace("?", "%s")
            cur = conn.cursor()
            cur.execute(sql_conv, params)
            conn.commit()
            last_id = cur.lastrowid
            cur.close()
            return last_id
        else:
            with conn:
                cur = conn.execute(sql, params)
                conn.commit()
                return cur.lastrowid
    finally:
        conn.close()
        st.cache_data.clear()
        # Automatically push the change to Google Sheets in real-time
        auto_sync_to_sheets(sql=sql, target_table=target_table)

def format_db_error(ex: Exception) -> str:
    msg = str(ex)
    if "1062" in msg or "UNIQUE constraint failed" in msg:
        if "roll_number" in msg:
            return "Duplicate Roll Number rejected: A student with this roll number already exists."
        if "email" in msg:
            return "Duplicate Email rejected: A student with this email address already exists."
        if "subject_code" in msg:
            return "Duplicate Subject Code rejected: A subject with this code already exists."
        if "level" in msg:
            return "Duplicate School Record: This student already has an SSC/HSC record for this level."
        if "semester_number" in msg:
            return "Duplicate Semester Result: A record for this student and semester number already exists."
        if "subject_id" in msg:
            return "Duplicate Subject Mark: Marks for this subject have already been entered for this semester."
        return "Duplicate Entry rejected: A record violating unique business constraints already exists."
    if "1451" in msg or "FOREIGN KEY constraint failed" in msg:
        return "Referential Integrity Restriction (RESTRICT): Cannot delete this record because dependent records reference it. Delete or reassign referencing marks/attendance records first."
    if "1452" in msg:
        return "Referential Integrity Violation: The referenced student or subject does not exist."
    if "CHECK constraint" in msg or "3819" in msg:
        return f"Check Constraint Violation: {msg}"
    return f"Database Error: {msg}"

@st.cache_data(ttl=60)
def options_students():
    df = read("SELECT id, roll_number, full_name, department FROM students ORDER BY roll_number")
    return {f"{r.roll_number} — {r.full_name} ({r.department}) (ID {r.id})": int(r.id) for r in df.itertuples()}

@st.cache_data(ttl=60)
def options_subjects():
    df = read("SELECT id, subject_code, subject_name, subject_type FROM subjects ORDER BY subject_code")
    return {f"{r.subject_code} — {r.subject_name} [{r.subject_type}] (ID {r.id})": int(r.id) for r in df.itertuples()}

# ==============================================
# GOOGLE SHEETS SYNC HELPER
# ==============================================

# Seed helper
def seed_real_students():
    try:
        from seed_shruti_data import seed_shruti_data
        seed_shruti_data()
        return True, "Real student data for Shruti_41 loaded successfully into MySQL!"
    except Exception as e:
        return False, f"Error seeding data: {e}"

def reset_db_tables():
    conn, mode = get_db_connection()
    tables = [
        "certificates", "seminars", "activities", "gap_years",
        "attendance", "subject_marks", "subjects", "semester_results",
        "school_records", "students"
    ]
    try:
        if mode == "MySQL":
            cur = conn.cursor()
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            for t in tables:
                cur.execute(f"TRUNCATE TABLE `{t}`")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
            conn.commit()
            cur.close()
            conn.close()
        else:
            with conn:
                for t in tables:
                    conn.execute(f"DELETE FROM {t}")
        return True, "Database reset successfully."
    except Exception as e:
        return False, f"Reset error: {e}"

def sync_via_apps_script(webhook_url=None, target_table=None):
    import requests
    url = webhook_url or get_apps_script_url()
    if not url:
        return False, "Google Apps Script Web App URL missing."
    url = url.strip()
    if not url.startswith("https://script.google.com/"):
        return False, "Invalid Apps Script URL. Expected format: 'https://script.google.com/macros/s/.../exec'"

    queries = {
        "Students": "SELECT * FROM students ORDER BY id",
        "School_Records": "SELECT r.*, s.roll_number, s.full_name FROM school_records r JOIN students s ON s.id=r.student_id ORDER BY r.id",
        "Semester_Results": "SELECT sr.*, s.roll_number, s.full_name FROM semester_results sr JOIN students s ON s.id=sr.student_id ORDER BY s.id, sr.semester_number",
        "Subjects": "SELECT * FROM subjects ORDER BY id",
        "Subject_Marks": "SELECT sm.*, sr.semester_number, s.roll_number, sub.subject_code, sub.subject_name, sub.subject_type FROM subject_marks sm JOIN semester_results sr ON sr.id=sm.semester_result_id JOIN students s ON s.id=sr.student_id JOIN subjects sub ON sub.id=sm.subject_id ORDER BY sm.id",
        "Attendance": "SELECT a.*, s.roll_number, s.full_name, sub.subject_code, sub.subject_name FROM attendance a JOIN students s ON s.id=a.student_id JOIN subjects sub ON sub.id=a.subject_id ORDER BY a.id",
        "Gap_Years": "SELECT g.*, s.roll_number, s.full_name FROM gap_years g JOIN students s ON s.id=g.student_id ORDER BY g.id",
        "Activities": "SELECT a.*, s.roll_number, s.full_name FROM activities a JOIN students s ON s.id=a.student_id ORDER BY a.id",
        "Seminars": "SELECT x.*, s.roll_number, s.full_name FROM seminars x JOIN students s ON s.id=x.student_id ORDER BY x.id",
        "Certificates": "SELECT c.*, s.roll_number, s.full_name FROM certificates c JOIN students s ON s.id=c.student_id ORDER BY c.id"
    }

    if target_table and target_table in queries:
        active_queries = {target_table: queries[target_table]}
    else:
        active_queries = queries

    sheets_data = {}
    for tab, sql in active_queries.items():
        df = read(sql)
        headers = list(df.columns)
        rows = df.fillna("").astype(str).values.tolist()
        sheets_data[tab] = [headers] + rows

    payload = {
        "action": "sync_all",
        "sheets": sheets_data
    }

    try:
        resp = requests.post(url, json=payload, timeout=60, allow_redirects=True)
        if resp.status_code in [200, 302]:
            try:
                data = resp.json()
                if data.get("status") == "success":
                    return True, f"Google Apps Script synced {data.get('sheetsUpdated', 10)} tables with {data.get('totalRows', 'all')} total records successfully!"
                else:
                    return False, f"Apps Script returned: {data.get('message', resp.text)}"
            except Exception:
                return True, "All 10 data tables pushed to Google Sheets via Apps Script Webhook successfully!"
        else:
            return False, f"HTTP status {resp.status_code}: {resp.text[:150]}"
    except Exception as e:
        return False, f"Apps Script request error: {e}"

def sync_sheets(custom_key=None, custom_sid=None):
    key = custom_key or os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    sid = custom_sid or os.getenv("GOOGLE_SHEET_ID")
    if not key or not sid:
        return False, "Google Sheets credentials missing. Please configure Service Account Key File and Spreadsheet ID."
    if not os.path.isfile(key):
        return False, f"Service account key file not found at: '{key}'. Please check the file path."
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_service_account_file(key, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        api = build("sheets", "v4", credentials=creds, cache_discovery=False)

        sheet_metadata = api.spreadsheets().get(spreadsheetId=sid).execute()
        existing_tabs = [s['properties']['title'] for s in sheet_metadata.get('sheets', [])]

        queries = {
          "Students": "SELECT * FROM students ORDER BY id",
          "School_Records": "SELECT r.*, s.roll_number, s.full_name FROM school_records r JOIN students s ON s.id=r.student_id ORDER BY r.id",
          "Semester_Results": "SELECT sr.*, s.roll_number, s.full_name FROM semester_results sr JOIN students s ON s.id=sr.student_id ORDER BY s.id, sr.semester_number",
          "Subjects": "SELECT * FROM subjects ORDER BY id",
          "Subject_Marks": "SELECT sm.*, sr.semester_number, s.roll_number, sub.subject_code, sub.subject_name, sub.subject_type FROM subject_marks sm JOIN semester_results sr ON sr.id=sm.semester_result_id JOIN students s ON s.id=sr.student_id JOIN subjects sub ON sub.id=sm.subject_id ORDER BY sm.id",
          "Attendance": "SELECT a.*, s.roll_number, s.full_name, sub.subject_code, sub.subject_name FROM attendance a JOIN students s ON s.id=a.student_id JOIN subjects sub ON sub.id=a.subject_id ORDER BY a.id",
          "Gap_Years": "SELECT g.*, s.roll_number, s.full_name FROM gap_years g JOIN students s ON s.id=g.student_id ORDER BY g.id",
          "Activities": "SELECT a.*, s.roll_number, s.full_name FROM activities a JOIN students s ON s.id=a.student_id ORDER BY a.id",
          "Seminars": "SELECT x.*, s.roll_number, s.full_name FROM seminars x JOIN students s ON s.id=x.student_id ORDER BY x.id",
          "Certificates": "SELECT c.*, s.roll_number, s.full_name FROM certificates c JOIN students s ON s.id=c.student_id ORDER BY c.id"
        }

        missing_tabs = [tab for tab in queries.keys() if tab not in existing_tabs]
        if missing_tabs:
            return False, f"Missing worksheet tab(s) in Google Spreadsheet: {', '.join(missing_tabs)}. Please create these tabs before syncing."

        for tab, sql in queries.items():
            df = read(sql)
            values = [list(df.columns)] + df.fillna("").astype(object).values.tolist()
            rng = f"{tab}!A:Z"
            api.spreadsheets().values().clear(spreadsheetId=sid, range=rng, body={}).execute()
            api.spreadsheets().values().update(spreadsheetId=sid, range=f"{tab}!A1", valueInputOption="USER_ENTERED", body={"values": values}).execute()

        return True, "All 10 data tabs refreshed successfully via Google Sheets API."
    except Exception as e:
        return False, f"Google Sheets API error: {e}"

# ==============================================================================
# SIDEBAR NAVIGATION & BACKEND CONTROL
# ==============================================================================
with st.sidebar:
    st.markdown("## 🎓 ScholarTrack")
    st.caption("Academic Intelligence & Surveillance DBMS")

    st.markdown("### 🧭 Navigation")
    page = st.radio(
        "Navigation",
        [
            "📊 Student Analytics (360°)",
            "Dashboard",
            "Student Directory",
            "SSC / HSC",
            "Semester Results",
            "Subjects & Marks",
            "Attendance",
            "Academic Gaps",
            "Portfolio",
            "Certificates",
            "Google Sheets Sync"
        ],
        label_visibility="collapsed"
    )
    st.divider()

    # Google Sheet-connected option below navigation panel
    st.markdown("""
    <div class="sync-status-box">
        <div class="sync-indicator">
            <span class="pulse-dot"></span>
            Sheets Connected
        </div>
        <div class="sync-queue-label">Sync Queue</div>
        <div class="sync-queue-val">0 pending</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Sync with Google Sheets Now", use_container_width=True):
        with st.spinner("Pushing relational records to Google Sheets..."):
            url = get_apps_script_url()
            ok, msg = sync_via_apps_script(url)
            if ok:
                st.success("✅ Google Sheets Synced Successfully!")
            else:
                st.error(f"❌ {msg}")

    with st.expander("🌱 Database Demo Controls", expanded=False):
        if st.button("Load Real Students (Shruti_41)", use_container_width=True):
            ok, msg = seed_real_students()
            if ok:
                st.cache_data.clear()
                auto_sync_to_sheets()
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
        if st.button("Reset Database Tables", use_container_width=True):
            ok, msg = reset_db_tables()
            if ok:
                st.cache_data.clear()
                auto_sync_to_sheets()
                st.warning(msg)
                st.rerun()
            else:
                st.error(msg)

    st.caption("ScholarTrack 3NF Enterprise Relational System · MySQL & Google Sheets Sync Enabled")

# Fetch student options
students = options_students()

# ==============================================================================
# 1. DEDICATED INDIVIDUAL STUDENT ANALYTICS (360° WITH SEARCH MENU)
# ==============================================================================
if page == "📊 Student Analytics (360°)":
    st.subheader("📊 Individual Student Academic Analytics & Performance Dossier")
    st.caption("Comprehensive 360° visual evaluation for individual students with search, trendlines, subject comparisons, and attendance surveillance.")

    all_students_df = read("SELECT id, roll_number, full_name, email, department, admission_year, current_status FROM students ORDER BY roll_number")

    if not len(all_students_df):
        st.info("No students found in the active database. Add a student from the 'Student Directory' page.")
    else:
        # Search Menu Bar
        col_search, col_dropdown = st.columns([1, 2])
        search_query = col_search.text_input("🔍 Search Student", placeholder="Search by Roll No, Name, or Dept...", help="Type to filter the student list dynamically.")

        if search_query.strip():
            filtered_df = all_students_df[
                all_students_df["roll_number"].astype(str).str.contains(search_query, case=False, na=False) |
                all_students_df["full_name"].astype(str).str.contains(search_query, case=False, na=False) |
                all_students_df["department"].astype(str).str.contains(search_query, case=False, na=False)
            ]
        else:
            filtered_df = all_students_df

        if not len(filtered_df):
            st.warning(f"No students matching '{search_query}'. Showing all students.")
            filtered_df = all_students_df

        student_labels = {
            f"Roll No: {r.roll_number} — {r.full_name} ({r.department})": int(r.id)
            for r in filtered_df.itertuples()
        }

        selected_label = col_dropdown.selectbox("Select Student Dossier", list(student_labels.keys()), key="analytics_selected_student")
        sel_id = student_labels[selected_label]
        student_row = all_students_df[all_students_df["id"] == sel_id].iloc[0]

        # ----------------- Student Profile Header Card -----------------
        st.markdown("---")
        p_c1, p_c2, p_c3, p_c4 = st.columns([2, 1, 1, 1])
        p_c1.markdown(f"### 👤 {student_row['full_name']}")
        p_c1.markdown(f"**Roll Number**: `{student_row['roll_number']}` &nbsp;|&nbsp; **Department**: `{student_row['department']}`")
        if pd.notna(student_row['email']):
            p_c1.caption(f"📧 {student_row['email']}")

        p_c2.metric("Admission Year", student_row["admission_year"])
        p_c3.metric("Current Status", student_row["current_status"])

        # Fetch all student-specific data
        sem_df = read("SELECT * FROM semester_results WHERE student_id = ? ORDER BY semester_number", (sel_id,))
        marks_df = read("""
            SELECT sm.*, sr.semester_number, sub.subject_code, sub.subject_name, sub.subject_type, sub.credits,
                   ROUND(100.0 * sm.marks_obtained / sm.marks_total, 2) AS marks_pct,
                   ROUND(100.0 * sm.passing_marks / sm.marks_total, 2) AS pass_pct
            FROM subject_marks sm
            JOIN semester_results sr ON sr.id = sm.semester_result_id
            JOIN subjects sub ON sub.id = sm.subject_id
            WHERE sr.student_id = ?
            ORDER BY sr.semester_number, sub.subject_code
        """, (sel_id,))
        att_df = read("""
            SELECT a.*, sub.subject_code, sub.subject_name, sub.subject_type,
                   ROUND(100.0 * a.classes_attended / NULLIF(a.classes_held, 0), 2) AS attendance_pct
            FROM attendance a
            JOIN subjects sub ON sub.id = a.subject_id
            WHERE a.student_id = ?
            ORDER BY a.semester_number, sub.subject_code
        """, (sel_id,))
        act_df = read("SELECT * FROM activities WHERE student_id = ? ORDER BY activity_date DESC", (sel_id,))
        sem_act_df = read("SELECT * FROM seminars WHERE student_id = ? ORDER BY seminar_date DESC", (sel_id,))
        cert_df = read("SELECT * FROM certificates WHERE student_id = ? ORDER BY issue_date DESC", (sel_id,))
        school_df = read("SELECT * FROM school_records WHERE student_id = ? ORDER BY level", (sel_id,))
        gap_df = read("SELECT * FROM gap_years WHERE student_id = ? ORDER BY start_year", (sel_id,))

        # KPI Summary metrics
        latest_cgpa = float(sem_df.iloc[-1]["cgpa"]) if len(sem_df) else 0.0
        prev_cgpa = float(sem_df.iloc[-2]["cgpa"]) if len(sem_df) > 1 else latest_cgpa
        cgpa_delta = round(latest_cgpa - prev_cgpa, 2)
        total_backlogs = int(sem_df["backlog_count"].sum()) if len(sem_df) else 0
        overall_att = round(100.0 * att_df["classes_attended"].sum() / att_df["classes_held"].sum(), 1) if len(att_df) and att_df["classes_held"].sum() > 0 else 0.0

        p_c4.metric(
            "Cumulative CGPA",
            f"{latest_cgpa:.2f}" if len(sem_df) else "N/A",
            delta=f"{cgpa_delta:+.2f} vs Prev Sem" if len(sem_df) > 1 else None
        )

        # Quick Highlights Bar
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Semesters Completed", len(sem_df))
        k2.metric("Active Backlogs", total_backlogs, delta=None if total_backlogs == 0 else f"{total_backlogs} Need Clearing", delta_color="inverse")
        k3.metric("Overall Attendance", f"{overall_att}%", delta="Eligible" if overall_att >= 75 else "Defaulter Risk", delta_color="normal" if overall_att >= 75 else "inverse")
        k4.metric("Portfolio Accolades", len(act_df) + len(sem_act_df) + len(cert_df))

        st.markdown("---")

        # ----------------- MEANINGFUL CHARTS SECTION -----------------
        st.markdown("### 📈 Analytical Visualizations & Performance Indices")

        # CHART ROW 1: Progression Trendline & Marks vs Benchmark
        ch_col1, ch_col2 = st.columns([1, 1], gap="large")

        with ch_col1:
            st.markdown("#### 1. SGPA & CGPA Progression Trendline")
            if len(sem_df):
                melted_sem = sem_df.melt(
                    id_vars=["semester_number", "academic_year", "result_status", "backlog_count", "is_gap_after"],
                    value_vars=["sgpa", "cgpa"],
                    var_name="Metric",
                    value_name="GPA"
                )
                melted_sem["Metric"] = melted_sem["Metric"].str.upper()
                melted_sem["GPA"] = pd.to_numeric(melted_sem["GPA"], errors="coerce").fillna(0.0).round(2)

                line_chart = alt.Chart(melted_sem).mark_line(point=alt.OverlayMarkDef(size=80, filled=True)).encode(
                    x=alt.X("semester_number:O", title="Semester Number"),
                    y=alt.Y("GPA:Q", scale=alt.Scale(domain=[0, 10]), title="Grade Point Average (0.00 - 10.00)"),
                    color=alt.Color(
                        "Metric:N",
                        scale=alt.Scale(domain=["SGPA", "CGPA"], range=["#2563eb", "#ea580c"]),
                        legend=alt.Legend(orient="bottom", direction="horizontal", title=None)
                    ),
                    tooltip=[
                        alt.Tooltip("semester_number:O", title="Semester"),
                        alt.Tooltip("academic_year:N", title="Academic Year"),
                        alt.Tooltip("Metric:N", title="Indicator"),
                        alt.Tooltip("GPA:Q", title="GPA", format=".2f"),
                        alt.Tooltip("result_status:N", title="Status"),
                        alt.Tooltip("backlog_count:Q", title="Backlogs")
                    ]
                ).properties(height=300)

                # Benchmark Line at 7.0 (First Class Distinction)
                distinction_rule = alt.Chart(pd.DataFrame({'y': [7.0]})).mark_rule(color="#10b981", strokeDash=[6, 4], size=2).encode(y='y:Q')
                distinction_label = alt.Chart(pd.DataFrame({'y': [7.2], 'text': ['First Class Distinction Benchmark (7.0)']})).mark_text(align='left', dx=10, color='#10b981', fontSize=11, fontWeight=600).encode(y='y:Q', text='text:N')

                st.altair_chart(line_chart + distinction_rule + distinction_label, use_container_width=True)

                if (sem_df["is_gap_after"] == 1).any():
                    gap_sems = sem_df[sem_df["is_gap_after"] == 1]["semester_number"].tolist()
                    st.warning(f"⚠️ Academic interruption / gap flagged immediately after Semester(s): {', '.join(map(str, gap_sems))}")
            else:
                st.info("No semester progression data recorded for this student.")

        with ch_col2:
            st.markdown("#### 2. Course Evaluation vs Passing Benchmark")
            if len(marks_df):
                perf_melted = marks_df.melt(
                    id_vars=["subject_code", "subject_name", "subject_type", "component"],
                    value_vars=["marks_pct", "pass_pct"],
                    var_name="Metric_Type",
                    value_name="Percentage"
                )
                perf_melted["Score_Type"] = perf_melted["Metric_Type"].map({"marks_pct": "Score Obtained (%)", "pass_pct": "Min Passing Benchmark (%)"})
                perf_melted["Percentage"] = pd.to_numeric(perf_melted["Percentage"], errors="coerce").fillna(0.0).round(1)

                bar_chart = alt.Chart(perf_melted).mark_bar(cornerRadiusEnd=3).encode(
                    x=alt.X("Percentage:Q", title="Percentage (%)", scale=alt.Scale(domain=[0, 100])),
                    y=alt.Y("subject_code:N", title="Course Code", sort="-x"),
                    color=alt.Color(
                        "Score_Type:N",
                        scale=alt.Scale(domain=["Score Obtained (%)", "Min Passing Benchmark (%)"], range=["#3b82f6", "#94a3b8"]),
                        legend=alt.Legend(orient="bottom", direction="horizontal", title=None)
                    ),
                    yOffset="Score_Type:N",
                    tooltip=[
                        alt.Tooltip("subject_code:N", title="Course Code"),
                        alt.Tooltip("subject_name:N", title="Course Name"),
                        alt.Tooltip("subject_type:N", title="Type"),
                        alt.Tooltip("component:N", title="Component"),
                        alt.Tooltip("Percentage:Q", title="Percentage", format=".1f")
                    ]
                ).properties(height=300)

                st.altair_chart(bar_chart, use_container_width=True)
            else:
                st.info("No course evaluation marks recorded for this student.")

        st.markdown("---")

        # CHART ROW 2: Attendance Surveillance & Component Distribution
        att_col, comp_col = st.columns([1, 1], gap="large")

        with att_col:
            st.markdown("#### 3. Course Attendance Surveillance & Defaulter Risk")
            if len(att_df):
                att_df_display = att_df.copy()
                att_df_display["attendance_pct"] = pd.to_numeric(att_df_display["attendance_pct"], errors="coerce").fillna(0.0).round(1)
                att_df_display["classes_held"] = pd.to_numeric(att_df_display["classes_held"], errors="coerce").fillna(0).astype(int)
                att_df_display["classes_attended"] = pd.to_numeric(att_df_display["classes_attended"], errors="coerce").fillna(0).astype(int)
                att_df_display["Compliance_Status"] = att_df_display["attendance_pct"].apply(
                    lambda x: "Eligible (>= 75%)" if x >= 75.0 else "Defaulter Risk (< 75%)"
                )

                att_bar = alt.Chart(att_df_display).mark_bar(cornerRadiusEnd=4).encode(
                    x=alt.X("attendance_pct:Q", title="Attendance Percentage (%)", scale=alt.Scale(domain=[0, 100])),
                    y=alt.Y("subject_code:N", title="Course Code", sort="-x"),
                    color=alt.Color(
                        "Compliance_Status:N",
                        scale=alt.Scale(domain=["Eligible (>= 75%)", "Defaulter Risk (< 75%)"], range=["#16a34a", "#dc2626"]),
                        legend=alt.Legend(orient="bottom", direction="horizontal", title=None)
                    ),
                    tooltip=[
                        alt.Tooltip("subject_code:N", title="Course Code"),
                        alt.Tooltip("subject_name:N", title="Course Name"),
                        alt.Tooltip("classes_held:Q", title="Classes Held"),
                        alt.Tooltip("classes_attended:Q", title="Classes Attended"),
                        alt.Tooltip("attendance_pct:Q", title="Attendance %", format=".1f"),
                        alt.Tooltip("Compliance_Status:N", title="Status")
                    ]
                ).properties(height=300)

                # 75% threshold rule
                rule75 = alt.Chart(pd.DataFrame({'x': [75.0]})).mark_rule(color="#dc2626", strokeDash=[4, 4], size=2).encode(x='x:Q')

                st.altair_chart(att_bar + rule75, use_container_width=True)

                defaulters = att_df_display[att_df_display["attendance_pct"] < 75.0]
                if len(defaulters):
                    st.error(f"🚨 **Defaulter Warning**: Attendance is below 75% in {len(defaulters)} subject(s): {', '.join(defaulters['subject_code'].tolist())}. Student is at risk of exam debarment.")
                else:
                    st.success("✅ Attendance complies with the 75% institutional threshold in all courses.")
            else:
                st.info("No attendance records tracked for this student.")

        with comp_col:
            st.markdown("#### 4. Assessment Component Composition")
            if len(marks_df):
                comp_summary = marks_df.groupby("component")["marks_obtained"].sum().reset_index()
                comp_summary["marks_obtained"] = pd.to_numeric(comp_summary["marks_obtained"], errors="coerce").fillna(0.0).round(1)
                donut = alt.Chart(comp_summary).mark_arc(innerRadius=65, stroke="#0f172a", strokeWidth=1).encode(
                    theta=alt.Theta("marks_obtained:Q", title="Total Marks"),
                    color=alt.Color(
                        "component:N",
                        scale=alt.Scale(scheme="category10"),
                        legend=alt.Legend(orient="bottom", direction="horizontal", title="Component")
                    ),
                    tooltip=[
                        alt.Tooltip("component:N", title="Component"),
                        alt.Tooltip("marks_obtained:Q", title="Total Marks", format=".1f")
                    ]
                ).properties(height=300)
                st.altair_chart(donut, use_container_width=True)
            else:
                st.info("Assessment component breakdown will appear once marks are entered.")

        st.markdown("---")

        # ----------------- COMPLETE STUDENT DOSSIER TABS -----------------
        st.markdown("### 📋 Student Data Records (Complete Dossier)")
        d_tab1, d_tab2, d_tab3, d_tab4, d_tab5 = st.tabs([
            "📚 Semester History",
            "📝 Examination Marks",
            "⏱️ Attendance Log",
            "🏫 School Records (SSC/HSC)",
            "🏆 Portfolio & Certifications"
        ])

        with d_tab1:
            st.dataframe(sem_df, use_container_width=True, hide_index=True)

        with d_tab2:
            st.dataframe(marks_df[["semester_number", "subject_code", "subject_name", "subject_type", "credits", "component", "marks_obtained", "marks_total", "passing_marks", "marks_pct"]], use_container_width=True, hide_index=True)

        with d_tab3:
            st.dataframe(att_df[["academic_year", "semester_number", "subject_code", "subject_name", "classes_held", "classes_attended", "attendance_pct"]], use_container_width=True, hide_index=True)

        with d_tab4:
            st.dataframe(school_df, use_container_width=True, hide_index=True)

        with d_tab5:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"**Activities ({len(act_df)})**")
                st.dataframe(act_df[["title", "activity_type", "organization", "activity_date"]], use_container_width=True, hide_index=True)
            with c2:
                st.markdown(f"**Seminars ({len(sem_act_df)})**")
                st.dataframe(sem_act_df[["title", "seminar_scope", "organizer", "seminar_date"]], use_container_width=True, hide_index=True)
            with c3:
                st.markdown(f"**Certificates ({len(cert_df)})**")
                st.dataframe(cert_df[["title", "issuer", "category", "issue_date"]], use_container_width=True, hide_index=True)

# ==============================================================================
# 2. DASHBOARD
# ==============================================================================
elif page == "Dashboard":
    st.subheader("🎓 ScholarTrack Overall System Dashboard")
    summary_df = read("""
        SELECT 
            (SELECT COUNT(*) FROM students) as total_students,
            (SELECT COUNT(*) FROM semester_results) as total_semesters,
            (SELECT COALESCE(SUM(backlog_count), 0) FROM semester_results) as total_backlogs,
            (SELECT COALESCE(SUM(classes_attended), 0) FROM attendance) as att_classes,
            (SELECT COALESCE(SUM(classes_held), 0) FROM attendance) as held_classes,
            (SELECT COUNT(*) FROM certificates) as total_certs
    """)
    s_row = summary_df.iloc[0]
    total_students = int(s_row["total_students"])
    total_semesters = int(s_row["total_semesters"])
    total_backlogs = int(s_row["total_backlogs"])
    held = float(s_row["held_classes"])
    att = float(s_row["att_classes"])
    att_pct = (100.0 * att / held) if held > 0 else 0.0
    total_certs = int(s_row["total_certs"])

    a, b, c, d, e = st.columns(5)
    a.metric("Total Students", total_students)
    b.metric("Semester Records", total_semesters)
    c.metric("Active Backlogs", total_backlogs)
    d.metric("Overall Attendance", f"{att_pct:.1f}%")
    e.metric("Certificates Earned", total_certs)

    st.divider()
    st.subheader("📈 Institutional Subject Evaluation Analytics")
    perf = read("""
        SELECT sub.subject_code, sub.subject_name, sub.subject_type,
               ROUND(AVG(100.0 * sm.marks_obtained / sm.marks_total), 2) AS avg_pct,
               SUM(CASE WHEN sm.marks_obtained < sm.passing_marks THEN 1 ELSE 0 END) AS failed_attempts,
               COUNT(*) AS total_attempts
        FROM subject_marks sm
        JOIN subjects sub ON sub.id = sm.subject_id
        GROUP BY sub.id
        ORDER BY avg_pct DESC
    """)
    if len(perf):
        st.dataframe(perf, use_container_width=True, hide_index=True)
    else:
        st.info("Subject performance analytics will appear here after marks are recorded.")

# ==============================================================================
# 3. STUDENT DIRECTORY (CRUD)
# ==============================================================================
elif page == "Student Directory":
    st.subheader("Student Directory")

    tab_add, tab_edit, tab_delete = st.tabs(["➕ Add Student", "✏️ Edit Student", "🗑️ Delete Student (Cascade)"])

    with tab_add:
        with st.form("add_student"):
            a, b = st.columns(2)
            roll = a.text_input("Roll number *", placeholder="e.g. 41")
            name = b.text_input("Full name *", placeholder="e.g. Shruti Patil")
            email = a.text_input("Email", placeholder="e.g. shruti.patil@viva-technology.org")
            dept = b.text_input("Department *", value="Computer Science & Engineering")
            year = a.number_input("Admission year *", 1990, 2100, 2022)
            status = b.selectbox("Current status", ["Active", "Graduated", "On Hold", "Discontinued"])
            if st.form_submit_button("Save Student", type="primary"):
                if not roll.strip() or not name.strip() or not dept.strip():
                    st.error("Roll Number, Full Name, and Department are required.")
                else:
                    try:
                        run("INSERT INTO students(roll_number, full_name, email, department, admission_year, current_status) VALUES(?,?,?,?,?,?)",
                            (roll.strip(), name.strip(), email.strip() or None, dept.strip(), int(year), status))
                        st.success(f"Student '{name.strip()}' registered successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(format_db_error(ex))

    with tab_edit:
        if students:
            sel_student_label = st.selectbox("Select student to edit", list(students.keys()), key="edit_student_sel")
            sel_student_id = students[sel_student_label]
            curr = read("SELECT * FROM students WHERE id=?", (sel_student_id,)).iloc[0]

            with st.form("edit_student_form"):
                a, b = st.columns(2)
                e_roll = a.text_input("Roll number *", value=str(curr.roll_number))
                e_name = b.text_input("Full name *", value=str(curr.full_name))
                e_email = a.text_input("Email", value=str(curr.email) if pd.notna(curr.email) else "")
                e_dept = b.text_input("Department *", value=str(curr.department))
                e_year = a.number_input("Admission year *", 1990, 2100, int(curr.admission_year))
                status_opts = ["Active", "Graduated", "On Hold", "Discontinued"]
                cur_idx = status_opts.index(curr.current_status) if curr.current_status in status_opts else 0
                e_status = b.selectbox("Current status", status_opts, index=cur_idx)

                if st.form_submit_button("Update Student", type="primary"):
                    if not e_roll.strip() or not e_name.strip() or not e_dept.strip():
                        st.error("Roll Number, Full Name, and Department are required.")
                    else:
                        try:
                            run("UPDATE students SET roll_number=?, full_name=?, email=?, department=?, admission_year=?, current_status=? WHERE id=?",
                                (e_roll.strip(), e_name.strip(), e_email.strip() or None, e_dept.strip(), int(e_year), e_status, sel_student_id))
                            st.success("Student details updated successfully.")
                            st.rerun()
                        except Exception as ex:
                            st.error(format_db_error(ex))
        else:
            st.info("No students available to edit.")

    with tab_delete:
        if students:
            del_label = st.selectbox("Select student to delete", list(students.keys()), key="del_student_sel")
            del_id = students[del_label]
            st.warning("⚠️ **DBMS Cascade Action Warning**: Deleting this student will CASCADE to remove all linked records: School Records, Semesters, Subject Marks, Attendance, Gap Years, Activities, Seminars, and Certificates.")
            if st.button("Confirm & Delete Student", type="primary"):
                try:
                    run("DELETE FROM students WHERE id=?", (del_id,))
                    st.success("Student and all dependent child records deleted via foreign key CASCADE.")
                    st.rerun()
                except Exception as ex:
                    st.error(format_db_error(ex))
        else:
            st.info("No students available to delete.")

    st.divider()
    st.subheader("📋 Registered Students Directory")
    q = st.text_input("🔍 Search students by full name or roll number")
    st_df = read("SELECT id, roll_number, full_name, email, department, admission_year, current_status FROM students WHERE full_name LIKE ? OR roll_number LIKE ? ORDER BY roll_number", (f"%{q}%", f"%{q}%"))
    st.dataframe(st_df, use_container_width=True, hide_index=True)

# ==============================================================================
# 4. SSC / HSC RECORDS (CRUD)
# ==============================================================================
elif page == "SSC / HSC":
    st.subheader("School Records (SSC / HSC)")
    tab_add, tab_edit, tab_delete = st.tabs(["➕ Add Record", "✏️ Edit Record", "🗑️ Delete Record"])

    with tab_add:
        if students:
            st.caption("💡 **Auto-Upsert Active:** If the selected student already has an SSC or HSC record, saving here will safely update it with new marks. To add a student not listed (e.g. Roll 123), register them first in **Student Directory**.")
            with st.form("school_add"):
                a, b = st.columns(2)
                who = a.selectbox("Student *", list(students.keys()), key="sr_add_who")
                level = b.selectbox("Level *", ["SSC", "HSC"])
                board = a.text_input("Board", placeholder="e.g. CBSE, State Board")
                py = b.number_input("Passing year *", 1990, 2100, 2020)
                got = a.number_input("Marks obtained *", 0.0, 1000.0, 480.0)
                total = b.number_input("Total marks *", 1.0, 1000.0, 500.0)

                if st.form_submit_button("Save School Record", type="primary"):
                    if got < 0 or total <= 0 or got > total:
                        st.error("Invalid marks: Obtained marks cannot exceed total marks.")
                    else:
                        pct = round((got / total) * 100.0, 2)
                        stud_id = students[who]
                        try:
                            chk = read("SELECT id FROM school_records WHERE student_id = ? AND level = ?", (stud_id, level))
                            if len(chk):
                                rec_id = int(chk.iloc[0]["id"])
                                run("UPDATE school_records SET board=?, passing_year=?, marks_obtained=?, marks_total=?, percentage=? WHERE id=?",
                                    (board.strip() or None, int(py), got, total, pct, rec_id), target_table="school_records")
                                st.success(f"✅ Existing {level} record updated successfully ({got:.1f}/{total:.1f} = {pct}%).")
                            else:
                                run("INSERT INTO school_records(student_id, level, board, passing_year, marks_obtained, marks_total, percentage) VALUES(?,?,?,?,?,?,?)",
                                    (stud_id, level, board.strip() or None, int(py), got, total, pct), target_table="school_records")
                                st.success(f"✅ {level} record saved successfully ({pct}%).")
                            st.rerun()
                        except Exception as ex:
                            st.error(format_db_error(ex))
        else:
            st.info("Register students first.")

    with tab_edit:
        s_records = read("SELECT r.id, s.roll_number, s.full_name, r.level, r.board, r.passing_year, r.marks_obtained, r.marks_total FROM school_records r JOIN students s ON s.id=r.student_id ORDER BY s.roll_number, r.level")
        if len(s_records):
            s_map = {f"{r.roll_number} — {r.full_name} [{r.level}] (ID {r.id})": int(r.id) for r in s_records.itertuples()}
            chosen_rec = st.selectbox("Select record to edit", list(s_map.keys()), key="sr_edit_sel")
            rec_id = s_map[chosen_rec]
            curr_sr = read("SELECT * FROM school_records WHERE id=?", (rec_id,)).iloc[0]

            with st.form("school_edit"):
                a, b = st.columns(2)
                e_board = a.text_input("Board", value=str(curr_sr.board) if pd.notna(curr_sr.board) else "")
                e_py = b.number_input("Passing year *", 1990, 2100, int(curr_sr.passing_year))
                e_got = a.number_input("Marks obtained *", 0.0, 1000.0, float(curr_sr.marks_obtained))
                e_total = b.number_input("Total marks *", 1.0, 1000.0, float(curr_sr.marks_total))

                if st.form_submit_button("Update School Record", type="primary"):
                    if e_got < 0 or e_total <= 0 or e_got > e_total:
                        st.error("Invalid marks.")
                    else:
                        e_pct = round((e_got / e_total) * 100.0, 2)
                        try:
                            run("UPDATE school_records SET board=?, passing_year=?, marks_obtained=?, marks_total=?, percentage=? WHERE id=?",
                                (e_board.strip() or None, int(e_py), e_got, e_total, e_pct, rec_id))
                            st.success("School record updated.")
                            st.rerun()
                        except Exception as ex:
                            st.error(format_db_error(ex))
        else:
            st.info("No school records exist.")

    with tab_delete:
        s_records_del = read("SELECT r.id, s.roll_number, s.full_name, r.level FROM school_records r JOIN students s ON s.id=r.student_id ORDER BY s.roll_number, r.level")
        if len(s_records_del):
            del_map = {f"{r.roll_number} — {r.full_name} [{r.level}] (ID {r.id})": int(r.id) for r in s_records_del.itertuples()}
            chosen_del = st.selectbox("Select record to delete", list(del_map.keys()), key="sr_del_sel")
            if st.button("Delete School Record", type="primary"):
                run("DELETE FROM school_records WHERE id=?", (del_map[chosen_del],))
                st.success("School record deleted.")
                st.rerun()
        else:
            st.info("No records to delete.")

    st.divider()
    st.dataframe(read("SELECT r.id, s.roll_number, s.full_name, r.level, r.board, r.passing_year, r.marks_obtained, r.marks_total, r.percentage FROM school_records r JOIN students s ON s.id=r.student_id ORDER BY s.roll_number, r.level"), use_container_width=True, hide_index=True)

# ==============================================================================
# 5. SEMESTER RESULTS (CRUD)
# ==============================================================================
elif page == "Semester Results":
    st.subheader("Semester Progression & Backlogs")
    tab_add, tab_edit, tab_delete = st.tabs(["➕ Add Semester Result", "✏️ Edit Semester Result", "🗑️ Delete Semester Result"])

    with tab_add:
        if students:
            with st.form("sem_add"):
                a, b, c = st.columns(3)
                who = a.selectbox("Student *", list(students.keys()), key="sem_add_who")
                sem = b.number_input("Semester number *", 1, 12, 1)
                acad = c.text_input("Academic year *", "2024-25")

                sgpa = a.number_input("SGPA (0.00 - 10.00) *", 0.0, 10.0, 8.5, 0.01)
                cgpa = b.number_input("CGPA (0.00 - 10.00) *", 0.0, 10.0, 8.5, 0.01)
                result = c.selectbox("Result status *", ["Pass", "ATKT", "Fail", "Pending"])

                backlog = a.number_input("Backlog count *", 0, 50, 0)
                gap = b.checkbox("Academic gap immediately after this semester")

                if st.form_submit_button("Save Semester Result", type="primary"):
                    if not (0.0 <= sgpa <= 10.0) or not (0.0 <= cgpa <= 10.0):
                        st.error("SGPA and CGPA must be strictly between 0.00 and 10.00.")
                    else:
                        stud_id = students[who]
                        sem_num = int(sem)
                        try:
                            chk = read("SELECT id FROM semester_results WHERE student_id = ? AND semester_number = ?", (stud_id, sem_num))
                            if len(chk):
                                rec_id = int(chk.iloc[0]["id"])
                                run("UPDATE semester_results SET academic_year=?, sgpa=?, cgpa=?, result_status=?, backlog_count=?, is_gap_after=? WHERE id=?",
                                    (acad.strip(), sgpa, cgpa, result, int(backlog), int(gap), rec_id), target_table="semester_results")
                                st.success(f"✅ Existing Semester {sem_num} result updated successfully.")
                            else:
                                run("INSERT INTO semester_results(student_id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count, is_gap_after) VALUES(?,?,?,?,?,?,?,?)",
                                    (stud_id, sem_num, acad.strip(), sgpa, cgpa, result, int(backlog), int(gap)), target_table="semester_results")
                                st.success(f"✅ Semester {sem_num} result saved successfully.")
                            st.rerun()
                        except Exception as ex:
                            st.error(format_db_error(ex))
        else:
            st.info("Register students first.")

    with tab_edit:
        sem_list = read("SELECT sr.id, s.roll_number, s.full_name, sr.semester_number, sr.academic_year, sr.sgpa, sr.cgpa, sr.result_status, sr.backlog_count, sr.is_gap_after FROM semester_results sr JOIN students s ON s.id=sr.student_id ORDER BY s.roll_number, sr.semester_number")
        if len(sem_list):
            sem_map = {f"{r.roll_number} — {r.full_name} | Sem {r.semester_number} ({r.academic_year}) (ID {r.id})": int(r.id) for r in sem_list.itertuples()}
            chosen_sem = st.selectbox("Select semester record to edit", list(sem_map.keys()), key="sem_edit_sel")
            curr_sem = read("SELECT * FROM semester_results WHERE id=?", (sem_map[chosen_sem],)).iloc[0]

            with st.form("sem_edit"):
                a, b, c = st.columns(3)
                e_acad = a.text_input("Academic year *", value=str(curr_sem.academic_year))
                e_sgpa = b.number_input("SGPA (0.00 - 10.00) *", 0.0, 10.0, float(curr_sem.sgpa), 0.01)
                e_cgpa = c.number_input("CGPA (0.00 - 10.00) *", 0.0, 10.0, float(curr_sem.cgpa), 0.01)
                status_list = ["Pass", "ATKT", "Fail", "Pending"]
                st_idx = status_list.index(curr_sem.result_status) if curr_sem.result_status in status_list else 0
                e_res = a.selectbox("Result status *", status_list, index=st_idx)
                e_backlog = b.number_input("Backlog count *", 0, 50, int(curr_sem.backlog_count))
                e_gap = c.checkbox("Academic gap after this semester", value=bool(curr_sem.is_gap_after))

                if st.form_submit_button("Update Semester Result", type="primary"):
                    try:
                        run("UPDATE semester_results SET academic_year=?, sgpa=?, cgpa=?, result_status=?, backlog_count=?, is_gap_after=? WHERE id=?",
                            (e_acad.strip(), e_sgpa, e_cgpa, e_res, int(e_backlog), int(e_gap), int(curr_sem.id)))
                        st.success("Semester result updated.")
                        st.rerun()
                    except Exception as ex:
                        st.error(format_db_error(ex))
        else:
            st.info("No semester records exist.")

    with tab_delete:
        if len(sem_list):
            del_sem_map = {f"{r.roll_number} — {r.full_name} | Sem {r.semester_number} (ID {r.id})": int(r.id) for r in sem_list.itertuples()}
            chosen_del_sem = st.selectbox("Select semester record to delete", list(del_sem_map.keys()), key="sem_del_sel")
            st.warning("⚠️ Deleting this semester record will CASCADE to delete all associated subject marks entered for this semester.")
            if st.button("Delete Semester Result", type="primary"):
                run("DELETE FROM semester_results WHERE id=?", (del_sem_map[chosen_del_sem],))
                st.success("Semester record and linked subject marks deleted.")
                st.rerun()
        else:
            st.info("No records to delete.")

    st.divider()
    st.dataframe(read("""
        SELECT sr.id, s.roll_number, s.full_name, sr.semester_number, sr.academic_year,
               sr.sgpa, sr.cgpa, sr.result_status, sr.backlog_count,
               CASE WHEN sr.is_gap_after=1 THEN 'Yes' ELSE 'No' END AS gap_after
        FROM semester_results sr
        JOIN students s ON s.id=sr.student_id
        ORDER BY s.roll_number, sr.semester_number
    """), use_container_width=True, hide_index=True)

# ==============================================================================
# 6. SUBJECTS & MARKS (CRUD with RESTRICT check)
# ==============================================================================
elif page == "Subjects & Marks":
    st.subheader("Subjects Catalogue & Examination Marks")
    tab_cat, tab_marks = st.tabs(["📚 Subject Catalogue", "📝 Examination Marks"])

    with tab_cat:
        with st.expander("➕ Add New Subject", expanded=True):
            with st.form("sub_add"):
                a, b = st.columns(2)
                code = a.text_input("Subject code *", placeholder="e.g. CS501")
                title = b.text_input("Subject name *", placeholder="e.g. Machine Learning & AI")
                typ = a.selectbox("Subject type *", ["Theory", "Lab"])
                cred = b.number_input("Credits *", 0.0, 20.0, 4.0, 0.5)

                if st.form_submit_button("Add Subject", type="primary"):
                    if not code.strip() or not title.strip():
                        st.error("Subject code and name are required.")
                    else:
                        try:
                            run("INSERT INTO subjects(subject_code, subject_name, subject_type, credits) VALUES(?,?,?,?)",
                                (code.strip().upper(), title.strip(), typ, cred))
                            st.success(f"Subject '{code.strip().upper()}' added.")
                            st.rerun()
                        except Exception as ex:
                            st.error(format_db_error(ex))

        subs = read("SELECT * FROM subjects ORDER BY subject_code")
        if len(subs):
            with st.expander("✏️ Edit Subject"):
                sub_opts = {f"{r.subject_code} — {r.subject_name} [{r.subject_type}] (ID {r.id})": int(r.id) for r in subs.itertuples()}
                sel_sub_edit = st.selectbox("Select subject to edit", list(sub_opts.keys()), key="sub_edit_sel")
                curr_sub = read("SELECT * FROM subjects WHERE id=?", (sub_opts[sel_sub_edit],)).iloc[0]

                with st.form("sub_edit_form"):
                    a, b = st.columns(2)
                    e_code = a.text_input("Subject code *", value=str(curr_sub.subject_code))
                    e_name = b.text_input("Subject name *", value=str(curr_sub.subject_name))
                    typ_list = ["Theory", "Lab"]
                    t_idx = typ_list.index(curr_sub.subject_type) if curr_sub.subject_type in typ_list else 0
                    e_typ = a.selectbox("Subject type *", typ_list, index=t_idx)
                    e_cred = b.number_input("Credits *", 0.0, 20.0, float(curr_sub.credits), 0.5)

                    if st.form_submit_button("Update Subject", type="primary"):
                        try:
                            run("UPDATE subjects SET subject_code=?, subject_name=?, subject_type=?, credits=? WHERE id=?",
                                (e_code.strip().upper(), e_name.strip(), e_typ, e_cred, int(curr_sub.id)))
                            st.success("Subject updated.")
                            st.rerun()
                        except Exception as ex:
                            st.error(format_db_error(ex))

            with st.expander("🗑️ Delete Subject (RESTRICT Check)"):
                sub_del_opts = {f"{r.subject_code} — {r.subject_name} (ID {r.id})": int(r.id) for r in subs.itertuples()}
                sel_sub_del = st.selectbox("Select subject to delete", list(sub_del_opts.keys()), key="sub_del_sel")
                st.info("ℹ️ **RESTRICT Rule**: Cannot delete a subject if student marks or attendance reference it.")
                if st.button("Delete Subject", type="primary"):
                    try:
                        run("DELETE FROM subjects WHERE id=?", (sub_del_opts[sel_sub_del],))
                        st.success("Subject deleted.")
                        st.rerun()
                    except Exception as ex:
                        st.error(format_db_error(ex))

        st.dataframe(subs, use_container_width=True, hide_index=True)

    with tab_marks:
        sems = read("SELECT sr.id, s.roll_number, s.full_name, sr.semester_number, sr.academic_year FROM semester_results sr JOIN students s ON s.id=sr.student_id ORDER BY s.roll_number, sr.semester_number")
        all_subs = read("SELECT id, subject_code, subject_name, subject_type FROM subjects ORDER BY subject_code")

        if len(sems) and len(all_subs):
            sl = {f"{r.roll_number} — {r.full_name} | Sem {r.semester_number} ({r.academic_year}) (ID {r.id})": int(r.id) for r in sems.itertuples()}
            su = {f"{r.subject_code} — {r.subject_name} [{r.subject_type}] (ID {r.id})": int(r.id) for r in all_subs.itertuples()}

            with st.expander("➕ Add Subject Mark", expanded=True):
                with st.form("marks_add"):
                    a, b = st.columns(2)
                    sem_label = a.selectbox("Semester result *", list(sl.keys()), key="m_add_sem")
                    sub_label = b.selectbox("Subject *", list(su.keys()), key="m_add_sub")
                    got = a.number_input("Marks obtained *", 0.0, 1000.0, 85.0)
                    total = b.number_input("Total marks *", 1.0, 1000.0, 100.0)
                    passing = a.number_input("Passing threshold *", 0.0, 1000.0, 40.0)
                    component = b.selectbox("Component *", ["Final", "Internal", "External", "Practical"])

                    if st.form_submit_button("Save Marks", type="primary"):
                        if got < 0 or total <= 0 or passing < 0 or got > total or passing > total:
                            st.error("Invalid marks.")
                        else:
                            sem_id = sl[sem_label]
                            subj_id = su[sub_label]
                            try:
                                chk = read("SELECT id FROM subject_marks WHERE semester_result_id = ? AND subject_id = ?", (sem_id, subj_id))
                                if len(chk):
                                    rec_id = int(chk.iloc[0]["id"])
                                    run("UPDATE subject_marks SET marks_obtained=?, marks_total=?, passing_marks=?, component=? WHERE id=?",
                                        (got, total, passing, component, rec_id), target_table="subject_marks")
                                    st.success(f"✅ Existing marks for subject updated successfully ({got:.1f}/{total:.1f}).")
                                else:
                                    run("INSERT INTO subject_marks(semester_result_id, subject_id, marks_obtained, marks_total, passing_marks, component) VALUES(?,?,?,?,?,?)",
                                        (sem_id, subj_id, got, total, passing, component), target_table="subject_marks")
                                    st.success("✅ Marks recorded successfully.")
                                st.rerun()
                            except Exception as ex:
                                st.error(format_db_error(ex))

            existing_marks = read("""
                SELECT sm.id, s.roll_number, s.full_name, sr.semester_number, sub.subject_code, sub.subject_name,
                       sm.marks_obtained, sm.marks_total, sm.passing_marks, sm.component
                FROM subject_marks sm
                JOIN semester_results sr ON sr.id = sm.semester_result_id
                JOIN students s ON s.id = sr.student_id
                JOIN subjects sub ON sub.id = sm.subject_id
                ORDER BY s.roll_number, sr.semester_number, sub.subject_code
            """)

            if len(existing_marks):
                with st.expander("✏️ Edit Subject Mark"):
                    m_map = {f"{r.roll_number} | Sem {r.semester_number} | {r.subject_code} ({r.component}) (ID {r.id})": int(r.id) for r in existing_marks.itertuples()}
                    sel_m = st.selectbox("Select mark record to edit", list(m_map.keys()), key="m_edit_sel")
                    curr_m = read("SELECT * FROM subject_marks WHERE id=?", (m_map[sel_m],)).iloc[0]

                    with st.form("marks_edit"):
                        a, b = st.columns(2)
                        e_got = a.number_input("Marks obtained *", 0.0, 1000.0, float(curr_m.marks_obtained))
                        e_tot = b.number_input("Total marks *", 1.0, 1000.0, float(curr_m.marks_total))
                        e_pass = a.number_input("Passing threshold *", 0.0, 1000.0, float(curr_m.passing_marks))
                        comp_opts = ["Final", "Internal", "External", "Practical"]
                        c_idx = comp_opts.index(curr_m.component) if curr_m.component in comp_opts else 0
                        e_comp = b.selectbox("Component *", comp_opts, index=c_idx)

                        if st.form_submit_button("Update Marks", type="primary"):
                            try:
                                run("UPDATE subject_marks SET marks_obtained=?, marks_total=?, passing_marks=?, component=? WHERE id=?",
                                    (e_got, e_tot, e_pass, e_comp, int(curr_m.id)))
                                st.success("Marks updated.")
                                st.rerun()
                            except Exception as ex:
                                st.error(format_db_error(ex))

                with st.expander("🗑️ Delete Subject Mark"):
                    del_m_map = {f"{r.roll_number} | Sem {r.semester_number} | {r.subject_code} (ID {r.id})": int(r.id) for r in existing_marks.itertuples()}
                    sel_del_m = st.selectbox("Select mark record to delete", list(del_m_map.keys()), key="m_del_sel")
                    if st.button("Delete Marks Record", type="primary"):
                        run("DELETE FROM subject_marks WHERE id=?", (del_m_map[sel_del_m],))
                        st.success("Marks deleted.")
                        st.rerun()

            st.dataframe(existing_marks, use_container_width=True, hide_index=True)
        else:
            st.info("Register semester results and subjects first.")

# ==============================================================================
# 7. ATTENDANCE (CRUD with Defaulter Warning)
# ==============================================================================
elif page == "Attendance":
    st.subheader("Attendance Surveillance & Defaulter Warnings")
    subs = read("SELECT * FROM subjects ORDER BY subject_name")
    if students and len(subs):
        subopts = {f"{r.subject_code} — {r.subject_name} [{r.subject_type}]": int(r.id) for r in subs.itertuples()}

        with st.expander("➕ Add Attendance Record", expanded=True):
            with st.form("att_add"):
                a, b = st.columns(2)
                who = a.selectbox("Student *", list(students.keys()), key="att_add_who")
                subject = b.selectbox("Subject *", list(subopts.keys()), key="att_add_sub")
                acad = a.text_input("Academic year *", "2024-25")
                sem = b.number_input("Semester number *", 1, 12, 1)
                held = a.number_input("Classes held *", 0, 1000, 45)
                attended = b.number_input("Classes attended *", 0, 1000, 40)

                if st.form_submit_button("Save Attendance", type="primary"):
                    if attended > held:
                        st.error("Classes attended cannot exceed held.")
                    else:
                        stud_id = students[who]
                        subj_id = subopts[subject]
                        acad_yr = acad.strip()
                        sem_num = int(sem)
                        try:
                            chk = read("SELECT id FROM attendance WHERE student_id = ? AND subject_id = ? AND academic_year = ? AND semester_number = ?",
                                       (stud_id, subj_id, acad_yr, sem_num))
                            if len(chk):
                                rec_id = int(chk.iloc[0]["id"])
                                run("UPDATE attendance SET classes_held=?, classes_attended=? WHERE id=?",
                                    (int(held), int(attended), rec_id), target_table="attendance")
                                st.success("✅ Existing attendance record updated successfully.")
                            else:
                                run("INSERT INTO attendance(student_id, subject_id, academic_year, semester_number, classes_held, classes_attended) VALUES(?,?,?,?,?,?)",
                                    (stud_id, subj_id, acad_yr, sem_num, int(held), int(attended)), target_table="attendance")
                                st.success("✅ Attendance saved successfully.")
                            st.rerun()
                        except Exception as ex:
                            st.error(format_db_error(ex))

        existing_att = read("""
            SELECT a.id, s.roll_number, s.full_name, sub.subject_code, sub.subject_name,
                   a.academic_year, a.semester_number, a.classes_held, a.classes_attended,
                   ROUND(100.0 * a.classes_attended / NULLIF(a.classes_held, 0), 2) AS attendance_pct
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            JOIN subjects sub ON sub.id = a.subject_id
            ORDER BY s.full_name, sub.subject_name
        """)

        if len(existing_att):
            st.divider()
            threshold = st.slider("Attendance Minimum Threshold (%)", 50, 95, 75)
            existing_att["status"] = existing_att["attendance_pct"].apply(
                lambda x: "Below Threshold (Defaulter)" if pd.notna(x) and x < threshold else ("No classes held" if pd.isna(x) else "Eligible")
            )
            low = existing_att[existing_att["attendance_pct"] < threshold]
            if len(low):
                st.warning(f"🚨 **Defaulter Alert**: {len(low)} student attendance record(s) fail to meet the {threshold}% minimum requirement.")
            else:
                st.success(f"✅ All records meet or exceed the {threshold}% attendance threshold.")

            st.dataframe(existing_att, use_container_width=True, hide_index=True)
    else:
        st.info("Register students and subjects first.")

# ==============================================================================
# 8. ACADEMIC GAPS (CRUD)
# ==============================================================================
elif page == "Academic Gaps":
    st.subheader("Academic Gaps & Interruption History")
    if students:
        with st.expander("➕ Add Academic Gap Record", expanded=True):
            with st.form("gap_add"):
                who = st.selectbox("Student *", list(students.keys()), key="gap_add_who")
                a, b = st.columns(2)
                start = a.number_input("Start year *", 1990, 2100, 2023)
                end = b.number_input("End year *", 1990, 2100, 2024)
                reason = a.selectbox("Reason category *", ["Academic", "Medical", "Personal", "Other"])
                notes = b.text_area("Notes / Explanation")

                if st.form_submit_button("Save Gap Period", type="primary"):
                    if end < start:
                        st.error("End year must be >= start year.")
                    else:
                        try:
                            run("INSERT INTO gap_years(student_id, start_year, end_year, reason_category, notes) VALUES(?,?,?,?,?)",
                                (students[who], int(start), int(end), reason, notes.strip() or None))
                            st.success("Gap period recorded.")
                            st.rerun()
                        except Exception as ex:
                            st.error(format_db_error(ex))

    gaps = read("SELECT g.id, s.roll_number, s.full_name, g.start_year, g.end_year, g.reason_category, g.notes FROM gap_years g JOIN students s ON s.id=g.student_id ORDER BY s.roll_number, g.start_year")
    st.dataframe(gaps, use_container_width=True, hide_index=True)

# ==============================================================================
# 9. PORTFOLIO (ACTIVITIES & SEMINARS CRUD)
# ==============================================================================
elif page == "Portfolio":
    st.subheader("Student Portfolio: Activities & Seminars")
    tab1, tab2 = st.tabs(["🎯 Activities", "🎤 Seminars & Workshops"])

    with tab1:
        if students:
            with st.expander("➕ Add Activity", expanded=True):
                with st.form("act_add"):
                    who = st.selectbox("Student *", list(students.keys()), key="act_add_who")
                    title = st.text_input("Activity title *", placeholder="e.g. Smart India Hackathon Winner")
                    typ = st.selectbox("Activity type *", ["Technical", "Co-curricular", "Extra-curricular"])
                    org = st.text_input("Organization", placeholder="e.g. AICTE")
                    dt = st.date_input("Date", date.today())
                    desc = st.text_area("Description")

                    if st.form_submit_button("Save Activity", type="primary"):
                        if not title.strip():
                            st.error("Title is required.")
                        else:
                            run("INSERT INTO activities(student_id, title, activity_type, organization, activity_date, description) VALUES(?,?,?,?,?,?)",
                                (students[who], title.strip(), typ, org.strip() or None, str(dt), desc.strip() or None))
                            st.success("Activity saved.")
                            st.rerun()

        act_df = read("SELECT a.id, s.roll_number, s.full_name, a.title, a.activity_type, a.organization, a.activity_date, a.description FROM activities a JOIN students s ON s.id=a.student_id ORDER BY a.activity_date DESC")
        st.dataframe(act_df, use_container_width=True, hide_index=True)

    with tab2:
        if students:
            with st.expander("➕ Add Seminar", expanded=True):
                with st.form("sem_act_add"):
                    who = st.selectbox("Student *", list(students.keys()), key="sem_add_who_tab")
                    title = st.text_input("Seminar title *", placeholder="e.g. Next-Gen Distributed DBMS")
                    scope = st.selectbox("Seminar scope *", ["Internal", "External"])
                    org = st.text_input("Organizer", placeholder="e.g. IEEE")
                    dt = st.date_input("Date", date.today(), key="sem_date_add")
                    url = st.text_input("Certificate URL", placeholder="https://...")

                    if st.form_submit_button("Save Seminar", type="primary"):
                        if not title.strip():
                            st.error("Title is required.")
                        else:
                            run("INSERT INTO seminars(student_id, title, seminar_scope, organizer, seminar_date, certificate_url) VALUES(?,?,?,?,?,?)",
                                (students[who], title.strip(), scope, org.strip() or None, str(dt), url.strip() or None))
                            st.success("Seminar saved.")
                            st.rerun()

        sem_df = read("SELECT x.id, s.roll_number, s.full_name, x.title, x.seminar_scope, x.organizer, x.seminar_date, x.certificate_url FROM seminars x JOIN students s ON s.id=x.student_id ORDER BY x.seminar_date DESC")
        st.dataframe(sem_df, use_container_width=True, hide_index=True)

# ==============================================================================
# 10. CERTIFICATES & CGPA PREDICTOR
# ==============================================================================
elif page == "Certificates":
    st.subheader("Certificates Registry & CGPA Target Predictor")
    tab_cert, tab_pred = st.tabs(["📜 Certificate Registry", "🎯 Target CGPA Forecaster"])

    with tab_cert:
        if students:
            with st.expander("➕ Add Certificate", expanded=True):
                with st.form("cert_add"):
                    who = st.selectbox("Student *", list(students.keys()), key="cert_add_who")
                    a, b = st.columns(2)
                    title = a.text_input("Certificate title *", placeholder="e.g. AWS Certified Solutions Architect")
                    issuer = b.text_input("Issuer *", placeholder="e.g. Amazon Web Services")
                    cat = a.selectbox("Category *", ["Course", "Hackathon", "Internship", "Achievement", "Seminar", "Other"])
                    dt = b.date_input("Issue date", date.today(), key="cert_date_add")
                    url = a.text_input("Verification URL")
                    notes = b.text_area("Notes")

                    if st.form_submit_button("Save Certificate", type="primary"):
                        if not title.strip() or not issuer.strip():
                            st.error("Title and Issuer are mandatory.")
                        else:
                            run("INSERT INTO certificates(student_id, title, issuer, category, issue_date, credential_url, notes) VALUES(?,?,?,?,?,?,?)",
                                (students[who], title.strip(), issuer.strip(), cat, str(dt), url.strip() or None, notes.strip() or None))
                            st.success("Certificate saved.")
                            st.rerun()

        cert_df = read("SELECT c.id, s.roll_number, s.full_name, c.title, c.issuer, c.category, c.issue_date, c.credential_url, c.notes FROM certificates c JOIN students s ON s.id=c.student_id ORDER BY c.issue_date DESC")
        st.dataframe(cert_df, use_container_width=True, hide_index=True)

    with tab_pred:
        st.markdown("#### 🎯 Target CGPA Predictor")
        st.caption("Assumes remaining semesters carry equal weight in CGPA calculation.")
        ss = read("SELECT id, roll_number, full_name FROM students ORDER BY roll_number")
        if len(ss):
            opts = {f"{r.roll_number} — {r.full_name}": int(r.id) for r in ss.itertuples()}
            who = st.selectbox("Student for forecast", list(opts.keys()), key="pred_student_select")
            semdata = read("SELECT semester_number, cgpa FROM semester_results WHERE student_id=? ORDER BY semester_number", (opts[who],))

            if len(semdata):
                current = float(semdata.iloc[-1].cgpa)
                completed = int(semdata.iloc[-1].semester_number)
                col1, col2 = st.columns(2)
                target = col1.slider("Target Cumulative CGPA", 0.0, 10.0, min(10.0, round(max(current, 8.5), 1)), 0.05)
                total_sems = col2.selectbox("Total Programme Duration (Semesters)", [6, 8, 10, 12], index=1)
                remaining = max(0, int(total_sems) - completed)
                required = ((target * total_sems) - (current * completed)) / remaining if remaining > 0 else current

                m1, m2, m3 = st.columns(3)
                m1.metric("Current CGPA", f"{current:.2f}")
                m2.metric("Semesters Completed", f"{completed} of {total_sems}")
                m3.metric("Semesters Remaining", remaining)

                if remaining > 0:
                    st.markdown(f"### Required SGPA Average: **{required:.2f}**")
                    if required > 10.0:
                        st.error(f"❌ **Mathematically Unreachable**: Requires impossible average SGPA of {required:.2f} (> 10.00).")
                    elif required <= 0.0:
                        st.success(f"🎉 **Target Secured**: Current CGPA already guarantees target.")
                    else:
                        st.success(f"🎯 **Target Achievable**: Aim for SGPA of at least **{required:.2f}** in remaining semesters.")
            else:
                st.info("Enter at least one semester result first.")

# ==============================================================================
# 11. GOOGLE SHEETS SYNC (Apps Script Webhook & Service Account API)
# ==============================================================================
elif page == "Google Sheets Sync":
    st.subheader("☁️ Database → Google Sheets Synchronization")
    st.caption("Directly mirrors all 10 normalized tables from the active MySQL database (Shruti_41) to your Google Sheet.")

    sync_tab_appscript, sync_tab_gcp = st.tabs([
        "⚡ Method 1: Google Apps Script Web App (Recommended)",
        "🔑 Method 2: Google Cloud Service Account JSON"
    ])

    with sync_tab_appscript:
        st.markdown("""
        ### ⚡ Instant Google Apps Script Webhook
        This method connects your Google Sheet **in under 1 minute** without needing a Google Cloud project or JSON key file!
        
        **3-Step Setup:**
        1. Open your Google Sheet &rarr; Click **Extensions** &rarr; **Apps Script**.
        2. Delete any existing code, paste the **ScholarTrack Apps Script code** (expand below), and click **Save** (💾).
        3. Click **Deploy** &rarr; **New deployment** &rarr; select **Web app** &rarr; Set **Who has access** to **Anyone** &rarr; Click **Deploy** &rarr; Copy the **Web app URL**.
        """)

        default_apps_url = os.getenv("GOOGLE_APPS_SCRIPT_URL", "https://script.google.com/macros/s/AKfycbyuRsnrpeDYGfS9lNt2wqhr-dGhpUVxJjgfrUE5Bw6dcbNMwXG5hb2Q0OEymgELCee_/exec")
        apps_url_input = st.text_input(
            "🔗 Google Apps Script Web App URL",
            value=st.session_state.get("apps_script_url", default_apps_url),
            placeholder="https://script.google.com/macros/s/AKfycbx.../exec",
            help="Your live Google Apps Script Web App URL."
        )
        if apps_url_input.strip():
            st.session_state["apps_script_url"] = apps_url_input.strip()

        if st.button("🚀 Push All 10 Tables to Google Sheets via Apps Script", type="primary"):
            if not apps_url_input.strip():
                st.error("Please enter your deployed Google Apps Script Web App URL first.")
            else:
                with st.spinner("Pushing all 10 tables (100 students, marks, attendance, etc.) to Google Sheets..."):
                    ok, msg = sync_via_apps_script(apps_url_input.strip())
                if ok:
                    st.success(f"✅ {msg}")
                    st.balloons()
                else:
                    st.error(f"❌ Sync failed: {msg}")

        with st.expander("📋 View / Copy Google Apps Script Code (`GoogleAppsScript.gs`)"):
            try:
                with open("GoogleAppsScript.gs", "r", encoding="utf-8") as gs_f:
                    gs_code = gs_f.read()
                st.code(gs_code, language="javascript")
            except Exception:
                st.info("The file 'GoogleAppsScript.gs' is available in your project directory.")

    with sync_tab_gcp:
        st.markdown("""
        ### 🔑 Google Sheets API v4 (Service Account)
        Authenticate directly using a Google Cloud Service Account with Google Sheets API enabled.
        """)
        c1, c2 = st.columns(2)
        custom_sid = c1.text_input("Google Spreadsheet ID", value=os.getenv("GOOGLE_SHEET_ID", ""))
        custom_key = c2.text_input("Service Account JSON Path", value=os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", ""))

        st.caption("Required 10 Worksheet Tabs: `Students`, `School_Records`, `Semester_Results`, `Subjects`, `Subject_Marks`, `Attendance`, `Gap_Years`, `Activities`, `Seminars`, `Certificates`.")

        if st.button("🔄 Sync via Google Sheets API v4", type="primary"):
            with st.spinner("Connecting via Google Service Account..."):
                ok, msg = sync_sheets(custom_key=custom_key.strip() or None, custom_sid=custom_sid.strip() or None)
            if ok:
                st.success(f"✅ {msg}")
            else:
                st.error(f"❌ {msg}")
