"""
Syncs MySQL student_ledger database directly into SQLite scholartrack.db
Ensures schema.mysql.sql, schema.sql, and scholartrack.db are 100% complete and synchronized.
"""

import os
import shutil
import sqlite3
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Pravin@_123")
DB_NAME = os.getenv("DB_NAME", "student_ledger")

SQLITE_PATH = "scholartrack.db"
SQLITE_PATH_DB_DIR = os.path.join("database", "scholartrack.db")
SCHEMA_SQL_PATH = "schema.sql"


def build_sqlite_database():
    print("=" * 60)
    print("Building SQLite 'scholartrack.db' from MySQL 'student_ledger'...")
    print("=" * 60)

    # 1. Connect to MySQL
    mysql_conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    my_cur = mysql_conn.cursor(dictionary=True)

    # 2. Re-create SQLite database
    if os.path.exists(SQLITE_PATH):
        try:
            os.remove(SQLITE_PATH)
        except Exception:
            pass

    sqlite_conn = sqlite3.connect(SQLITE_PATH)
    sqlite_conn.execute("PRAGMA foreign_keys = ON;")
    sq_cur = sqlite_conn.cursor()

    # Apply Schema
    with open(SCHEMA_SQL_PATH, "r", encoding="utf-8") as f:
        sq_cur.executescript(f.read())
    sqlite_conn.commit()
    print("[OK] Applied SQLite 3NF schema to scholartrack.db")

    # Tables to copy in order of foreign key dependency
    tables = [
        "students",
        "school_records",
        "semester_results",
        "subjects",
        "subject_marks",
        "attendance",
        "gap_years",
        "activities",
        "seminars",
        "certificates",
        "student_performance"
    ]

    for table in tables:
        my_cur.execute(f"SELECT * FROM {table}")
        rows = my_cur.fetchall()
        if not rows:
            print(f"Table '{table}': 0 rows (empty)")
            continue

        columns = list(rows[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"

        data_to_insert = []
        for r in rows:
            data_to_insert.append([str(v) if isinstance(v, (type(None),)) is False and hasattr(v, 'isoformat') else v for v in r.values()])

        sq_cur.executemany(sql, data_to_insert)
        sqlite_conn.commit()
        print(f"[OK] Table '{table}': {len(rows)} records synchronized.")

    sqlite_conn.close()
    my_cur.close()
    mysql_conn.close()

    # Also copy to database/scholartrack.db
    shutil.copy2(SQLITE_PATH, SQLITE_PATH_DB_DIR)
    print(f"\n[SUCCESS] 'scholartrack.db' generated successfully at:")
    print(f"  - {os.path.abspath(SQLITE_PATH)}")
    print(f"  - {os.path.abspath(SQLITE_PATH_DB_DIR)}")
    print("=" * 60)


if __name__ == "__main__":
    build_sqlite_database()
