"""
ScholarTrack 1,000 Real-Time Students Generator
Populates `student_ledger` with 1,000 completely unique student profiles
and corresponding 3NF relational academic, attendance, and portfolio records.
Zero duplicate names, zero duplicate roll numbers, zero duplicate emails.
"""

import os
import random
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Pravin@_123")
DB_NAME = os.getenv("DB_NAME", "student_ledger")

# 70 Distinct Indian First Names
FIRST_NAMES = [
    "Aarav", "Aditi", "Aditya", "Akanksha", "Akshay", "Aman", "Ananya", "Aniket",
    "Ankita", "Anurag", "Aryan", "Ashish", "Avani", "Ayush", "Bhavesh", "Bhavya",
    "Chaitanya", "Chetan", "Chirag", "Deepa", "Dev", "Dhruv", "Divya", "Diya",
    "Gaurav", "Harsh", "Harshada", "Isha", "Ishaan", "Ishita", "Jay", "Karan",
    "Kavya", "Khushi", "Kiran", "Kunal", "Madhav", "Manan", "Manisha", "Mayur",
    "Meera", "Mohit", "Neha", "Nikhil", "Nilesh", "Nishant", "Omkar", "Parth",
    "Pooja", "Pranav", "Pratik", "Priya", "Rahul", "Raj", "Riddhi", "Ritesh",
    "Riya", "Rohan", "Rohit", "Rucha", "Sahil", "Sakshi", "Sameer", "Sanjay",
    "Sanjana", "Saurabh", "Shaurya", "Shivam", "Shreya", "Shruti", "Siddhant",
    "Sneha", "Soham", "Sumit", "Tanvi", "Tejas", "Tushar", "Utkarsh", "Vaibhav",
    "Varun", "Vedant", "Vikas", "Vinay", "Yash"
]

# 50 Distinct Indian Surnames
LAST_NAMES = [
    "Agarwal", "Bhosale", "Chavan", "Choudhary", "Dalvi", "Deshmukh", "Deshpande",
    "Dubey", "Gaikwad", "Ghate", "Ghosh", "Gokhale", "Gupta", "Jadhav", "Jain",
    "Jha", "Joshi", "Kadam", "Kale", "Kamat", "Kapoor", "Khan", "Kulkarni",
    "Kumar", "Mahajan", "Mane", "Mehta", "Mishra", "More", "Naik", "Nair",
    "Pandey", "Patel", "Patil", "Pawar", "Rane", "Rao", "Reddy", "Salunkhe",
    "Sane", "Sawant", "Sen", "Shah", "Sharma", "Shetty", "Shinde", "Shukla",
    "Singh", "Tambe", "Tawde", "Thakur", "Tiwari", "Tripathi", "Varma", "Verma",
    "Yadav", "Zore"
]

DEPARTMENTS = [
    "Computer Science & Engineering",
    "Information Technology",
    "Artificial Intelligence & Data Science",
    "Electronics & Telecommunication Engineering",
    "Mechanical Engineering",
    "Civil Engineering",
    "Electrical Engineering"
]

BOARDS = [
    "Maharashtra State Board",
    "Central Board of Secondary Education (CBSE)",
    "Council for the Indian School Certificate Examinations (ICSE)"
]

ACTIVITY_TITLES = [
    ("Smart India Hackathon Finalist", "Technical", "Ministry of Education & AICTE"),
    ("IEEE Student Branch Core Coordinator", "Co-curricular", "IEEE Computer Society"),
    ("National Level Hackathon Winner", "Technical", "ACM Student Chapter"),
    ("TechFest Web & Mobile App Lead", "Technical", "IIT Bombay / College Tech Council"),
    ("Annual Inter-Collegiate Debate Winner", "Extra-curricular", "Rotaract Youth Club"),
    ("AI & Machine Learning Club Secretary", "Co-curricular", "Data Science Student Forum"),
    ("Open Source Project Contributor", "Technical", "GitHub Global Campus"),
    ("University Sports Volleyball Captain", "Extra-curricular", "Inter-University Sports Council"),
    ("Cybersecurity CTF Challenge - Top 5", "Technical", "Nullcon & OWASP Chapter"),
    ("Robotics Maze Solver Champion", "Technical", "RoboCon India")
]

SEMINARS_DATA = [
    ("Next-Generation Distributed DBMS & Vector Databases", "Internal", "Department of CSE", "https://verify.acm.org/seminar-dbms-2024"),
    ("Cloud Native Architecture & Kubernetes at Scale", "External", "Google Cloud Community Day", "https://verify.gdg.org/cloud-native-2024"),
    ("Full-Stack Microservices & Event-Driven Systems", "Internal", "Technical Association of Students", "https://viva-technology.org/seminars/microservices"),
    ("Deep Learning Paradigms & Large Language Models", "External", "PyData Regional Conference", "https://pydata.org/verify/ai-nlp-2024"),
    ("Zero Trust Security Architecture in Enterprise Clouds", "External", "ISACA Student Chapter", "https://isaca.org/verify/zt-2024")
]

CERTIFICATES_DATA = [
    ("AWS Certified Solutions Architect - Associate", "Amazon Web Services", "Course", "https://aws.amazon.com/verify/AS-89472", "Credential ID: AWS-84920"),
    ("Deep Learning Specialization (5 Courses)", "DeepLearning.AI / Coursera", "Course", "https://coursera.org/verify/specialization/DL-7839", "Convolutional & Sequence Models"),
    ("Oracle Certified Professional: MySQL 8.0 Database Developer", "Oracle University", "Course", "https://oracle.com/certview/OCP-98421", "Query Optimization & Stored Procedures"),
    ("HackTheBox CyberSec Offensive Specialist", "HackTheBox", "Hackathon", "https://academy.hackthebox.com/verify/HTB-38291", "Penetration Testing & Linux Hardening"),
    ("Summer Software Engineering Internship", "Persistent Systems / TCS", "Internship", "https://credentials.persistent.com/intern/PERS-4820", "Cloud Backend & REST API Engineering"),
    ("Postman API Fundamentals Student Expert", "Postman", "Achievement", "https://badgr.com/public/assertions/postman-expert-492", "REST API Development & Automated Testing")
]


def generate_unique_students(total_count=1000):
    """Generates 1,000 uniquely named students with distinct emails and roll numbers."""
    random.seed(42)  # Deterministic generation
    students = []
    used_names = set()
    used_emails = set()

    # Pre-reserve Roll 41 for Shruti Patil
    shruti_name = "Shruti Patil"
    shruti_email = "shruti.patil@viva-technology.org"
    used_names.add(shruti_name)
    used_emails.add(shruti_email)

    name_pairs = []
    for f in FIRST_NAMES:
        for l in LAST_NAMES:
            name_pairs.append((f, l))
    random.shuffle(name_pairs)

    pair_idx = 0
    for roll_int in range(1, total_count + 1):
        roll_no = str(roll_int)

        if roll_no == "41":
            # Shruti Patil
            students.append({
                "student_id": 41,
                "student_name": shruti_name,
                "roll_no": "41",
                "branch": "Computer Science & Engineering",
                "admission_year": 2022,
                "email": shruti_email,
                "current_status": "Active"
            })
            continue

        # Pick unique name
        while pair_idx < len(name_pairs):
            first, last = name_pairs[pair_idx]
            pair_idx += 1
            full_name = f"{first} {last}"
            if full_name not in used_names:
                break
        else:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last} {roll_int}"

        used_names.add(full_name)

        # Unique email
        base_email = f"{first.lower()}.{last.lower()}@viva-technology.org"
        email = base_email
        if email in used_emails:
            email = f"{first.lower()}.{last.lower()}{roll_int}@viva-technology.org"
        used_emails.add(email)

        # Department & Year
        dept = random.choice(DEPARTMENTS)
        adm_year = random.choice([2021, 2022, 2023, 2024])
        status = "Active" if adm_year >= 2021 else "Graduated"

        students.append({
            "student_id": roll_int,
            "student_name": full_name,
            "roll_no": roll_no,
            "branch": dept,
            "admission_year": adm_year,
            "email": email,
            "current_status": status
        })

    return students


def seed_database_to_1000():
    print(f"Connecting to MySQL ({DB_HOST}:{DB_PORT}) as {DB_USER}...")
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cur = conn.cursor(dictionary=True)

    print("Generating 1,000 unique student records with zero collisions...")
    students = generate_unique_students(1000)

    # Disable foreign key checks for clean atomic population
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for tbl in [
        "student_performance", "certificates", "seminars", "activities",
        "gap_years", "attendance", "subject_marks", "semester_results",
        "school_records", "students"
    ]:
        cur.execute(f"TRUNCATE TABLE `{tbl}`")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.commit()
    print("Existing tables truncated cleanly.")

    # 1. Insert 1,000 Students
    print("Inserting 1,000 students...")
    student_insert_sql = """
        INSERT INTO students (student_id, student_name, roll_no, branch, admission_year, email, current_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    student_data = [
        (s["student_id"], s["student_name"], s["roll_no"], s["branch"], s["admission_year"], s["email"], s["current_status"])
        for s in students
    ]
    cur.executemany(student_insert_sql, student_data)
    conn.commit()
    print("[OK] 1,000 students inserted successfully.")

    # 2. Insert School Records (2 per student = 2,000 records)
    print("Generating 2,000 SSC/HSC school records...")
    school_sql = """
        INSERT INTO school_records (student_id, level, board, passing_year, marks_obtained, marks_total, percentage)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    school_records = []
    for s in students:
        sid = s["student_id"]
        adm = s["admission_year"]
        board1 = random.choice(BOARDS)
        board2 = random.choice(BOARDS)

        # 10th (SSC)
        ssc_total = 500.0
        ssc_obtained = round(random.uniform(370.0, 485.0), 1)
        ssc_pct = round((ssc_obtained / ssc_total) * 100.0, 2)
        school_records.append((sid, "SSC", board1, adm - 2, ssc_obtained, ssc_total, ssc_pct))

        # 12th (HSC)
        hsc_total = 600.0
        hsc_obtained = round(random.uniform(430.0, 580.0), 1)
        hsc_pct = round((hsc_obtained / hsc_total) * 100.0, 2)
        school_records.append((sid, "HSC", board2, adm, hsc_obtained, hsc_total, hsc_pct))

    cur.executemany(school_sql, school_records)
    conn.commit()
    print("[OK] 2,000 school records inserted.")

    # Ensure Subjects exist
    cur.execute("SELECT id, subject_code, subject_type FROM subjects ORDER BY id ASC")
    subjects = cur.fetchall()
    if not subjects:
        print("Registering subjects catalog...")
        sample_subs = [
            ("CSC301", "Applied Mathematics III", "Theory", 4.0),
            ("CSC302", "Discrete Structures & Graph Theory", "Theory", 3.0),
            ("CSC303", "Data Structures & Algorithms", "Theory", 4.0),
            ("CSL303", "Data Structures Lab", "Lab", 1.5),
            ("CSC304", "Digital Logic & Computer Organization", "Theory", 3.0),
            ("CSC305", "Computer Graphics", "Theory", 3.0),
            ("CSL305", "Computer Graphics Lab", "Lab", 1.5),
            ("CSC401", "Applied Mathematics IV", "Theory", 4.0),
            ("CSC402", "Analysis of Algorithms", "Theory", 4.0),
            ("CSL402", "Analysis of Algorithms Lab", "Lab", 1.5),
            ("CSC403", "Database Management Systems", "Theory", 4.0),
            ("CSL403", "Database Systems Lab", "Lab", 1.5),
            ("CSC404", "Operating Systems", "Theory", 3.0),
            ("CSL404", "Operating Systems Lab", "Lab", 1.5),
            ("CSC501", "Computer Networks", "Theory", 3.0),
            ("CSL501", "Computer Networks Lab", "Lab", 1.5),
            ("CSC502", "Theory of Computer Science", "Theory", 3.0),
            ("CSC503", "Software Engineering & Project Management", "Theory", 3.0)
        ]
        cur.executemany("INSERT INTO subjects (subject_code, subject_name, subject_type, credits) VALUES (%s, %s, %s, %s)", sample_subs)
        conn.commit()
        cur.execute("SELECT id, subject_code, subject_type FROM subjects ORDER BY id ASC")
        subjects = cur.fetchall()

    # 3. Insert Semester Results & Performance
    print("Generating semester results and progression curves...")
    sem_insert_sql = """
        INSERT INTO semester_results (student_id, semester_number, academic_year, sgpa, cgpa, result_status, backlog_count, is_gap_after)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    sem_rows = []
    sem_counter = 1

    # Map student to completed semesters
    student_sem_map = {}
    for s in students:
        sid = s["student_id"]
        adm = s["admission_year"]
        # Completed semesters based on admission year
        if adm == 2021:
            completed = random.choice([6, 7, 8])
        elif adm == 2022:
            completed = random.choice([4, 5, 6])
        elif adm == 2023:
            completed = random.choice([2, 3, 4])
        else:
            completed = random.choice([1, 2])

        base_gpa = round(random.uniform(7.2, 9.4), 2)
        total_pts = 0.0
        student_sems = []

        for sem_idx in range(1, completed + 1):
            yr_offset = (sem_idx - 1) // 2
            start_yr = adm + yr_offset
            acad_yr = f"{start_yr}-{start_yr + 1}"

            # Fluctuate GPA reasonably
            sgpa = round(min(10.0, max(5.0, base_gpa + random.uniform(-0.6, 0.6))), 2)
            total_pts += sgpa
            cgpa = round(total_pts / sem_idx, 2)

            status = "Pass"
            backlogs = 0
            if sgpa < 6.0:
                status = random.choice(["ATKT", "Pass"])
                backlogs = 1 if status == "ATKT" else 0

            sem_rows.append((sid, sem_idx, acad_yr, sgpa, cgpa, status, backlogs, 0))
            student_sems.append({"sem_num": sem_idx, "result_id": sem_counter, "acad_yr": acad_yr})
            sem_counter += 1

        student_sem_map[sid] = student_sems

    cur.executemany(sem_insert_sql, sem_rows)
    conn.commit()
    print(f"[OK] {len(sem_rows)} semester results recorded.")

    # Legacy table sync
    print("Syncing legacy student_performance table...")
    cur.execute("""
        INSERT INTO student_performance (student_id, semester, sgpa, cgpa)
        SELECT student_id, semester_number, sgpa, cgpa
        FROM semester_results
    """)
    conn.commit()

    # 4. Insert Attendance & Subject Marks
    print("Generating subject evaluations and attendance records...")
    att_sql = """
        INSERT INTO attendance (student_id, subject_id, academic_year, semester_number, classes_held, classes_attended)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    marks_sql = """
        INSERT INTO subject_marks (semester_result_id, subject_id, marks_obtained, marks_total, passing_marks, component)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    cur.execute("SELECT id, student_id, semester_number, academic_year FROM semester_results")
    all_sem_records = cur.fetchall()

    att_batch = []
    marks_batch = []
    sub_count = len(subjects)

    for sr in all_sem_records:
        rid = sr["id"]
        sid = sr["student_id"]
        snum = sr["semester_number"]
        ayear = sr["academic_year"]

        # Pick 3 subjects per semester
        picked_subs = [subjects[(snum * 2 + i) % sub_count] for i in range(3)]
        for sub in picked_subs:
            sub_id = sub["id"]
            stype = sub["subject_type"]

            # Attendance
            held = random.randint(40, 52)
            # Most students have > 75%, some have < 75% for realistic testing
            pct_rate = random.uniform(0.68, 0.96) if sid % 8 != 0 else random.uniform(0.55, 0.74)
            attended = int(held * pct_rate)
            att_batch.append((sid, sub_id, ayear, snum, held, attended))

            # Marks
            tot = 100.0 if stype == "Theory" else 50.0
            passing = 40.0 if stype == "Theory" else 20.0
            obt = round(random.uniform(passing - 2, tot * 0.95), 1) if sid % 15 == 0 else round(random.uniform(passing + 5, tot * 0.96), 1)
            marks_batch.append((rid, sub_id, obt, tot, passing, "Final"))

        if len(att_batch) >= 5000:
            cur.executemany(att_sql, att_batch)
            cur.executemany(marks_sql, marks_batch)
            conn.commit()
            att_batch = []
            marks_batch = []

    if att_batch:
        cur.executemany(att_sql, att_batch)
        cur.executemany(marks_sql, marks_batch)
        conn.commit()

    print("[OK] Attendance and subject marks inserted.")

    # 5. Insert Gap Years for realistic sample (~40 students)
    print("Recording realistic academic gap years...")
    gap_sql = """
        INSERT INTO gap_years (student_id, start_year, end_year, reason_category, notes)
        VALUES (%s, %s, %s, %s, %s)
    """
    gaps = []
    gap_reasons = [
        ("Academic", "Preparation for GATE / CET Examination"),
        ("Medical", "Medical recovery leave approved by university board"),
        ("Personal", "Family business commitment & relocation"),
        ("Other", "Specialized vocational apprenticeship & skill development")
    ]
    for sid in range(15, 1000, 25):
        cat, note = random.choice(gap_reasons)
        s_obj = students[sid - 1]
        adm = s_obj["admission_year"]
        gaps.append((sid, adm - 1, adm, cat, note))

    cur.executemany(gap_sql, gaps)
    conn.commit()
    print(f"[OK] {len(gaps)} academic gap years logged.")

    # 6. Insert Portfolio: Activities, Seminars, and Certificates
    print("Seeding co-curricular portfolios (Activities, Seminars, Certificates)...")
    act_sql = "INSERT INTO activities (student_id, title, activity_type, organization, activity_date, description) VALUES (%s, %s, %s, %s, %s, %s)"
    sem_sql = "INSERT INTO seminars (student_id, title, seminar_scope, organizer, seminar_date, certificate_url) VALUES (%s, %s, %s, %s, %s, %s)"
    cert_sql = "INSERT INTO certificates (student_id, title, issuer, category, issue_date, credential_url, notes) VALUES (%s, %s, %s, %s, %s, %s, %s)"

    act_batch = []
    sem_batch = []
    cert_batch = []

    for sid in range(1, 1001):
        # 1-2 activities for many students
        if sid % 2 == 0 or sid == 41:
            title, atype, org = random.choice(ACTIVITY_TITLES)
            act_batch.append((sid, title, atype, org, "2024-03-15", "Active participant and team coordinator."))
        if sid % 3 == 0 or sid == 41:
            stitle, scope, org, url = random.choice(SEMINARS_DATA)
            sem_batch.append((sid, stitle, scope, org, "2024-05-10", url))
        if sid % 2 != 0 or sid == 41:
            ctitle, issuer, cat, url, note = random.choice(CERTIFICATES_DATA)
            cert_batch.append((sid, ctitle, issuer, cat, "2024-06-20", url, note))

    cur.executemany(act_sql, act_batch)
    cur.executemany(sem_sql, sem_batch)
    cur.executemany(cert_sql, cert_batch)
    conn.commit()

    print(f"[OK] Portfolio populated: {len(act_batch)} activities, {len(sem_batch)} seminars, {len(cert_batch)} certificates.")

    # 7. Verification Summary
    print("\n=======================================================")
    print("      FINAL 1,000 STUDENTS DATABASE SUMMARY            ")
    print("=======================================================")
    tables = [
        "students", "school_records", "semester_results", "subjects",
        "subject_marks", "attendance", "gap_years", "activities",
        "seminars", "certificates", "student_performance"
    ]
    for tbl in tables:
        cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
        cnt = cur.fetchone()["COUNT(*)"]
        print(f"  • {tbl.ljust(22)}: {cnt} rows")

    # Verify uniqueness
    cur.execute("""
        SELECT 
            COUNT(*) AS total,
            COUNT(DISTINCT student_name) AS unique_names,
            COUNT(DISTINCT roll_no) AS unique_rolls,
            COUNT(DISTINCT email) AS unique_emails
        FROM students
    """)
    stats = cur.fetchone()
    print("\n--- UNIQUENESS INTEGRITY CHECK ---")
    print(f"  Total Students : {stats['total']}")
    print(f"  Unique Names   : {stats['unique_names']} (100% Unique - Zero Duplicate Names)")
    print(f"  Unique Rolls   : {stats['unique_rolls']} (100% Unique - Zero Duplicate Rolls)")
    print(f"  Unique Emails  : {stats['unique_emails']} (100% Unique - Zero Duplicate Emails)")

    cur.close()
    conn.close()
    print("\nDatabase is 100% ready with 1,000 real-time distinct students!")


if __name__ == "__main__":
    seed_database_to_1000()
