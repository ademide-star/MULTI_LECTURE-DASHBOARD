import streamlit as st
import pandas as pd
import sqlite3
import os
import re
import json
import base64
import csv
from io import BytesIO
from datetime import datetime, date, timedelta, time
from streamlit_autorefresh import st_autorefresh

# ===============================================================
# 🎯 PAGE CONFIGURATION - MUST BE FIRST STREAMLIT COMMAND
# ===============================================================

st.set_page_config(
    page_title="Multi-Course Learning Management System Education Prism",
    page_icon="📚",
    layout="wide"
)

# ===============================================================
# 🎨 CUSTOM STYLING - HIDE STREAMLIT ELEMENTS
# ===============================================================

st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    @media (min-width: 900px) {
        .block-container {
            max-width: 95% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    }

    @media (max-width: 899px) {
        .block-container {
            max-width: 100% !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .streamlit-expanderHeader {
            font-size: 1.1rem !important;
        }
    }

    section[data-testid="stSidebar"] {
        min-width: 250px !important;
        max-width: 250px !important;
    }
    button[kind="header"] {
        display: none !important;
    }

    .mcq-question {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 15px;
        border-left: 4px solid #4CAF50;
    }
    .mcq-option {
        padding: 10px;
        margin: 5px 0;
        border-radius: 5px;
        background-color: white;
        border: 1px solid #ddd;
    }
    .mcq-option:hover {
        background-color: #e9ecef;
    }
    .gap-filling {
        background-color: #fff3cd;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .course-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ===============================================================
# 🗂 CONSTANTS AND DIRECTORIES
# ===============================================================

PERSISTENT_DATA_DIR = "persistent_data"
ATTENDANCE_STATUS_FILE = "attendance_status.json"
DEFAULT_ADMIN_PASSWORD = "sacoetec2025"
SYSTEM_ADMIN_PASSWORD = "systemadmin2025"

# ===============================================================
# 🗂 DIRECTORY MANAGEMENT
# ===============================================================

def ensure_directories():
    """Create all required directories"""
    directories = [
        PERSISTENT_DATA_DIR,
        os.path.join(PERSISTENT_DATA_DIR, "pdfs"),
        os.path.join(PERSISTENT_DATA_DIR, "videos"),
        os.path.join(PERSISTENT_DATA_DIR, "data"),
        os.path.join(PERSISTENT_DATA_DIR, "attendance"),
        os.path.join(PERSISTENT_DATA_DIR, "classwork"),
        os.path.join(PERSISTENT_DATA_DIR, "seminar"),
        os.path.join(PERSISTENT_DATA_DIR, "lectures"),
        os.path.join(PERSISTENT_DATA_DIR, "scores"),
        os.path.join(PERSISTENT_DATA_DIR, "student_uploads"),
        os.path.join(PERSISTENT_DATA_DIR, "student_uploads", "assignment"),
        os.path.join(PERSISTENT_DATA_DIR, "student_uploads", "drawing"),
        os.path.join(PERSISTENT_DATA_DIR, "student_uploads", "seminar"),
        os.path.join(PERSISTENT_DATA_DIR, "mcq_questions"),
        os.path.join(PERSISTENT_DATA_DIR, "course_management"),
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    return True

ensure_directories()

# ===============================================================
# 🎯 COURSE MANAGEMENT SYSTEM
# ===============================================================

def get_courses_file():
    """Get the courses configuration file path"""
    return os.path.join(PERSISTENT_DATA_DIR, "course_management", "courses_config.json")

def get_passwords_file():
    """Get the passwords configuration file path"""
    return os.path.join(PERSISTENT_DATA_DIR, "course_management", "admin_passwords.json")

def load_courses_config():
    """Load courses configuration from JSON file"""
    try:
        courses_file = get_courses_file()
        if os.path.exists(courses_file):
            with open(courses_file, 'r') as f:
                return json.load(f)
        default_courses = {
            "MCB 221 – General Microbiology": "MCB221",
            "BCH 201 – General Biochemistry": "BCH201",
            "BIO 203 – General Physiology": "BIO203",
            "BIO 113 – Virus Bacteria Lower Plants": "BIO113",
            "BIO 306 – Systematic Biology": "BIO306",
        }
        save_courses_config(default_courses)
        return default_courses
    except Exception as e:
        st.error(f"Error loading courses config: {e}")
        return {}

def save_courses_config(courses):
    """Save courses configuration to JSON file"""
    try:
        courses_file = get_courses_file()
        os.makedirs(os.path.dirname(courses_file), exist_ok=True)
        with open(courses_file, 'w') as f:
            json.dump(courses, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving courses config: {e}")
        return False

def load_admin_passwords():
    """Load admin passwords from JSON file"""
    try:
        passwords_file = get_passwords_file()
        if os.path.exists(passwords_file):
            with open(passwords_file, 'r') as f:
                return json.load(f)
        return {}
    except Exception as e:
        st.error(f"Error loading passwords: {e}")
        return {}

def save_admin_passwords(passwords):
    """Save admin passwords to JSON file"""
    try:
        passwords_file = get_passwords_file()
        os.makedirs(os.path.dirname(passwords_file), exist_ok=True)
        with open(passwords_file, 'w') as f:
            json.dump(passwords, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving passwords: {e}")
        return False

def get_course_password(course_code):
    """Get password for a specific course, fallback to default"""
    passwords = load_admin_passwords()
    return passwords.get(course_code, DEFAULT_ADMIN_PASSWORD)

def set_course_password(course_code, new_password):
    """Set new password for a specific course"""
    passwords = load_admin_passwords()
    passwords[course_code] = new_password
    return save_admin_passwords(passwords)

def verify_admin_password(course_code, password):
    """Verify admin password for a course"""
    correct_password = get_course_password(course_code)
    return password == correct_password

# ===============================================================
# 🗄️ DATABASE MIGRATION FUNCTIONS
# ===============================================================

def emergency_database_fix():
    """Emergency function to fix database schema issues"""
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS weekly_courses")
        c.execute('''
            CREATE TABLE weekly_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_name TEXT NOT NULL,
                course_name TEXT NOT NULL,
                course_code TEXT NOT NULL,
                module_type TEXT,
                duration TEXT,
                difficulty TEXT,
                objectives TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database fix failed: {e}")
        return False

def check_database_schema():
    """Check if database has the correct schema"""
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        conn.close()
        required_columns = ['week_name', 'course_name', 'course_code', 'module_type', 'duration', 'difficulty', 'objectives', 'notes']
        missing_columns = [col for col in required_columns if col not in columns]
        return len(missing_columns) == 0
    except Exception as e:
        print(f"Error checking schema: {e}")
        return False

# ===============================================================
# 🎯 AUTOMATED MCQ & GAP-FILLING SYSTEM
# ===============================================================

def get_mcq_file(course_code, week):
    folder = "mcq_data"
    os.makedirs(folder, exist_ok=True)
    filename = f"{folder}/{course_code}_week_{week}_mcq.json"
    return filename

def load_mcq_questions(course_code, week):
    """Load MCQ/Gap-fill questions for a specific week"""
    filename = get_mcq_file(course_code, week)
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data
        except Exception as e:
            st.error(f"Error loading questions: {e}")
            return []
    return []

def save_mcq_questions(course_code, week, questions):
    """Save MCQ/Gap-fill questions for a specific week"""
    filename = get_mcq_file(course_code, week)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=4)
        return True
    except Exception as e:
        st.error(f"Error saving questions: {e}")
        return False

def auto_grade_mcq_submission(questions, answers):
    """Automatically grade MCQ submissions and return score"""
    try:
        total_questions = len(questions)
        correct_answers = 0
        for i, question in enumerate(questions):
            if i < len(answers):
                user_answer = str(answers[i]).strip().lower()
                correct_answer = question.get('correct_answer', '').strip().lower()
                if question['type'] == 'mcq':
                    if user_answer == correct_answer:
                        correct_answers += 1
                elif question['type'] == 'gap_fill':
                    correct_options = [opt.strip().lower() for opt in correct_answer.split('|')]
                    if user_answer in correct_options:
                        correct_answers += 1
        score_percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
        return round(score_percentage, 1), correct_answers, total_questions
    except Exception as e:
        st.error(f"Error in auto-grading: {e}")
        return 0, 0, 0

def save_mcq_submission(course_code, week, student_name, student_matric, answers, score):
    """Save MCQ submission with automatic grading"""
    try:
        classwork_file = get_file(course_code, "classwork")
        os.makedirs(os.path.dirname(classwork_file), exist_ok=True)
        submission_data = {
            'Name': student_name,
            'Matric': student_matric,
            'Week': week,
            'Type': 'MCQ',
            'Answers': json.dumps(answers),
            'Score': score,
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if os.path.exists(classwork_file):
            df = pd.read_csv(classwork_file)
            existing = df[
                (df['Name'] == student_name) &
                (df['Matric'] == student_matric) &
                (df['Week'] == week) &
                (df['Type'] == 'MCQ')
            ]
            if not existing.empty:
                st.warning("⚠️ You have already submitted MCQ for this week.")
                return False
            df = pd.concat([df, pd.DataFrame([submission_data])], ignore_index=True)
        else:
            df = pd.DataFrame([submission_data])
        df.to_csv(classwork_file, index=False)
        return True
    except Exception as e:
        st.error(f"Error saving MCQ submission: {e}")
        return False

def display_mcq_questions(questions):
    """Display MCQ questions and collect answers"""
    answers = []
    for i, question in enumerate(questions):
        st.write(f"**Q{i+1}: {question['question']}**")
        if question['type'] == 'mcq':
            options = question['options']
            selected_option = st.radio(
                f"Select your answer for Q{i+1}:",
                options=list(options.keys()),
                format_func=lambda x, opts=options: f"{x}: {opts[x]}",
                key=f"mcq_{i}"
            )
            answers.append(selected_option if selected_option else "")
        elif question['type'] == 'gap_fill':
            user_answer = st.text_input(
                f"Your answer for Q{i+1}:",
                placeholder="Type your answer here...",
                key=f"gap_{i}"
            )
            answers.append(user_answer if user_answer else "")
    return answers

def parse_bulk_questions(bulk_text):
    """Parse bulk text containing multiple questions and options"""
    questions = []
    lines = bulk_text.strip().split('\n')
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith('MCQ:'):
            question_text = line[4:].strip()
            options = {}
            correct_answer = None
            i += 1
            while i < len(lines):
                option_line = lines[i].strip()
                if option_line.startswith('Correct:'):
                    correct_answer = option_line[8:].strip()
                    i += 1
                    break
                elif option_line.startswith(('A.', 'B.', 'C.', 'D.', 'E.')):
                    option_key = option_line[0]
                    option_value = option_line[2:].strip()
                    options[option_key] = option_value
                i += 1
            if question_text and options and correct_answer:
                questions.append({
                    "type": "mcq",
                    "question": question_text,
                    "options": options,
                    "correct_answer": correct_answer
                })
        elif line.startswith('GAP:'):
            question_text = line[4:].strip()
            correct_answer = None
            i += 1
            while i < len(lines):
                answer_line = lines[i].strip()
                if answer_line.startswith('Correct:'):
                    correct_answer = answer_line[8:].strip()
                    i += 1
                    break
                i += 1
            if question_text and correct_answer:
                questions.append({
                    "type": "gap_fill",
                    "question": question_text,
                    "options": {},
                    "correct_answer": correct_answer
                })
        else:
            i += 1
    return questions

# ===============================================================
# 🗄️ COURSE MANAGEMENT DATABASE FUNCTIONS
# ===============================================================

def init_course_db():
    """Initialize SQLite database for course storage with proper migration"""
    try:
        ensure_directories()  # FIX #10: was ensure_data_directory()
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weekly_courses'")
        table_exists = c.fetchone() is not None
        if not table_exists:
            c.execute('''
                CREATE TABLE weekly_courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    week_name TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    course_code TEXT NOT NULL,
                    module_type TEXT,
                    duration TEXT,
                    difficulty TEXT,
                    objectives TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            c.execute("PRAGMA table_info(weekly_courses)")
            existing_columns = [column[1] for column in c.fetchall()]
            required_columns = {
                'module_type': 'TEXT',
                'duration': 'TEXT',
                'difficulty': 'TEXT',
                'objectives': 'TEXT',
                'notes': 'TEXT'
            }
            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    c.execute(f'ALTER TABLE weekly_courses ADD COLUMN {column_name} {column_type}')
            if 'course_code' not in existing_columns:
                c.execute('ALTER TABLE weekly_courses ADD COLUMN course_code TEXT')
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database initialization error: {e}")
        return emergency_database_fix()

def add_course_to_db(week_name, course_name, course_code, module_type="Lecture", duration="1-2 hours", difficulty="Beginner", objectives="", notes=""):
    """Add course to database"""
    try:
        init_course_db()
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        c.execute('''
            INSERT INTO weekly_courses
            (week_name, course_name, course_code, module_type, duration, difficulty, objectives, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (week_name, course_name, course_code, module_type, duration, difficulty, objectives, notes,
              datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Database error in add_course_to_db: {e}")
        return False

def get_weeks_from_db():
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('SELECT DISTINCT week_name FROM weekly_courses ORDER BY created_at')
    weeks = [row[0] for row in c.fetchall()]
    conn.close()
    return weeks

def get_courses_by_week(week_name):
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('SELECT course_name, course_code FROM weekly_courses WHERE week_name = ? ORDER BY id', (week_name,))
    courses = [{"name": row[0], "code": row[1]} for row in c.fetchall()]
    conn.close()
    return courses

def delete_week_from_db(week_name):
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('DELETE FROM weekly_courses WHERE week_name = ?', (week_name,))
    conn.commit()
    conn.close()

def get_all_courses_from_db():
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        if 'course_code' in columns:
            df = pd.read_sql_query('SELECT week_name, course_name, course_code, created_at FROM weekly_courses ORDER BY created_at', conn)
        else:
            df = pd.read_sql_query('SELECT week_name, course_name, created_at FROM weekly_courses ORDER BY created_at', conn)
            df['course_code'] = 'UNKNOWN'
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def get_weeks_for_course_from_db(course_code):
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        if 'course_code' in columns:
            c.execute('SELECT DISTINCT week_name FROM weekly_courses WHERE course_code = ? ORDER BY created_at', (course_code,))
        else:
            c.execute('SELECT DISTINCT week_name FROM weekly_courses ORDER BY created_at')
        weeks = [row[0] for row in c.fetchall()]
        conn.close()
        return weeks
    except:
        return []

def get_courses_for_course_from_db(course_code):
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        if 'course_code' in columns:
            df = pd.read_sql_query(
                'SELECT week_name, course_name, course_code, created_at FROM weekly_courses WHERE course_code = ? ORDER BY created_at',
                conn, params=(course_code,)
            )
        else:
            df = pd.read_sql_query('SELECT week_name, course_name, created_at FROM weekly_courses ORDER BY created_at', conn)
            df['course_code'] = 'UNKNOWN'
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def delete_week_for_course(week_name, course_code):
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute("PRAGMA table_info(weekly_courses)")
    columns = [column[1] for column in c.fetchall()]
    if 'course_code' in columns:
        c.execute('DELETE FROM weekly_courses WHERE week_name = ? AND course_code = ?', (week_name, course_code))
    else:
        c.execute('DELETE FROM weekly_courses WHERE week_name = ?', (week_name,))
    conn.commit()
    conn.close()

# ===============================================================
# 🔧 HELPER FUNCTIONS
# ===============================================================

def get_persistent_path(file_type, course_code="", filename=""):
    """Get persistent file paths"""
    base_dir = PERSISTENT_DATA_DIR
    file_paths = {
        "pdf": os.path.join(base_dir, "pdfs", course_code, filename) if filename else os.path.join(base_dir, "pdfs", course_code),
        "video": os.path.join(base_dir, "videos", course_code, filename) if filename else os.path.join(base_dir, "videos", course_code),
        "attendance": os.path.join(base_dir, "attendance", filename) if filename else os.path.join(base_dir, "attendance"),
        "classwork": os.path.join(base_dir, "classwork", f"{course_code}_classwork.csv"),
        "seminar": os.path.join(base_dir, "seminar", f"{course_code}_seminar.csv"),
        "lectures": os.path.join(base_dir, "lectures", f"{course_code}_lectures.csv"),
        "mcq": os.path.join(base_dir, "mcq_questions"),
        "attendance_status": os.path.join(base_dir, "data", "attendance_status.json"),
        "scores": os.path.join(base_dir, "scores", f"{course_code.lower()}_scores.csv")
    }
    return file_paths.get(file_type, os.path.join(base_dir, "data", filename))

# FIX #11: Only ONE definition of get_file() — the correct one using course_code subdirectory
def get_file(course_code, file_type):
    """Get file path for different file types"""
    base_dir = os.path.join(PERSISTENT_DATA_DIR, course_code)
    os.makedirs(base_dir, exist_ok=True)
    file_map = {
        "students": os.path.join(base_dir, "students.csv"),
        "lectures": os.path.join(base_dir, "lectures.csv"),
        "attendance": os.path.join(base_dir, "attendance.csv"),
        "classwork": os.path.join(base_dir, "classwork.csv"),
        "scores": os.path.join(base_dir, "scores.csv"),
        "mcq": os.path.join(base_dir, "mcq_questions"),
        "attendance_status": os.path.join(base_dir, "attendance_status.json"),
        "classwork_status": os.path.join(base_dir, "classwork_status.json")
    }
    return file_map.get(file_type, os.path.join(base_dir, f"{file_type}.csv"))

def clean_text(val):
    return str(val or "").strip()

def normalize_course_name(name):
    return name.replace("–", "-").replace("—", "-").strip()

def get_lecture_file(course_code):
    if not course_code or not isinstance(course_code, str):
        st.warning("⚠️ Invalid or missing course code.")
        return None
    return get_file(course_code, "lectures")

def ensure_scores_file(course_code):
    """Ensure scores file exists with proper columns"""
    scores_file = get_file(course_code, "scores")
    os.makedirs(os.path.dirname(scores_file), exist_ok=True)
    required_columns = ["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"]
    if not os.path.exists(scores_file):
        df = pd.DataFrame(columns=required_columns)
        df.to_csv(scores_file, index=False)
        return df
    else:
        try:
            df = pd.read_csv(scores_file)
            for col in required_columns:
                if col not in df.columns:
                    df[col] = "" if col == "Grade" else 0
            df.to_csv(scores_file, index=False)
            return df
        except:
            df = pd.DataFrame(columns=required_columns)
            df.to_csv(scores_file, index=False)
            return df

# ===============================================================
# 📊 ATTENDANCE MANAGEMENT
# ===============================================================

def init_attendance_status():
    status_file = get_persistent_path("attendance_status")
    os.makedirs(os.path.dirname(status_file), exist_ok=True)
    if not os.path.exists(status_file):
        with open(status_file, 'w') as f:
            json.dump({}, f)

def get_attendance_status(course_code, week):
    init_attendance_status()
    status_file = get_persistent_path("attendance_status")
    try:
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        week_key = week.replace(" ", "")
        key = f"{course_code}_{week_key}"
        return status_data.get(key, {"is_open": False, "open_time": None})
    except Exception:
        return {"is_open": False, "open_time": None}

def set_attendance_status(course_code, week, is_open, open_time=None):
    init_attendance_status()
    status_file = get_persistent_path("attendance_status")
    try:
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        week_key = week.replace(" ", "")
        key = f"{course_code}_{week_key}"
        if is_open:
            status_data[key] = {
                "is_open": True,
                "open_time": open_time.isoformat() if open_time else datetime.now().isoformat()
            }
        else:
            status_data[key] = {"is_open": False, "open_time": None}
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error setting attendance status: {e}")
        return False

def has_marked_attendance(course_code, week, name, matric):
    try:
        attendance_folder = get_persistent_path("attendance")
        week_key = week.replace(" ", "")
        attendance_file = os.path.join(attendance_folder, f"attendance_{course_code}_{week_key}.csv")
        if not os.path.exists(attendance_file):
            return False
        df = pd.read_csv(attendance_file)
        df['Name'] = df['Name'].astype(str).str.strip().str.lower()
        df['Matric'] = df['Matric'].astype(str).str.strip().str.lower()
        existing = df[(df['Name'] == name.strip().lower()) & (df['Matric'] == matric.strip().lower())]
        return len(existing) > 0
    except Exception as e:
        st.error(f"Error checking attendance: {e}")
        return True

def mark_attendance_entry(course_code, name, matric, week):
    try:
        attendance_folder = get_persistent_path("attendance")
        week_key = week.replace(" ", "")
        attendance_file = os.path.join(attendance_folder, f"attendance_{course_code}_{week_key}.csv")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_data = {'Name': [name.strip()], 'Matric': [matric.strip()], 'Week': [week], 'Timestamp': [timestamp]}
        new_df = pd.DataFrame(new_data)
        if os.path.exists(attendance_file):
            existing_df = pd.read_csv(attendance_file)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        combined_df.to_csv(attendance_file, index=False)
        return True
    except Exception as e:
        st.error(f"Error recording attendance: {e}")
        return False

# ===============================================================
# 🧩 CLASSWORK STATUS
# ===============================================================

# FIX #4: Only ONE definition of get_classwork_status_file() — takes (course_code, week)
def get_classwork_status_file(course_code, week):
    """Get classwork status file path for a specific course and week"""
    status_dir = os.path.join(PERSISTENT_DATA_DIR, course_code, "classwork_status")
    os.makedirs(status_dir, exist_ok=True)
    week_key = week.replace(" ", "_")
    return os.path.join(status_dir, f"{week_key}_status.json")

def get_classwork_status(course_code, week):
    """Get classwork status for specific course and week"""
    status_file = get_classwork_status_file(course_code, week)
    default_status = {"is_open": False, "open_time": None, "answers_released": False}
    try:
        with open(status_file, 'r') as f:
            loaded_status = json.load(f)
            default_status.update(loaded_status)
        return default_status
    except:
        return default_status

def set_classwork_status(course_code, week, is_open, open_time=None):
    """Set classwork status for specific course and week"""
    try:
        status_file = get_classwork_status_file(course_code, week)
        status = get_classwork_status(course_code, week)
        status["is_open"] = is_open
        status["open_time"] = open_time.isoformat() if (is_open and open_time) else (datetime.now().isoformat() if is_open else None)
        with open(status_file, 'w') as f:
            json.dump(status, f)
        return True
    except Exception as e:
        st.error(f"Error setting classwork status: {e}")
        return False

def are_answers_released(course_code, week):
    status = get_classwork_status(course_code, week)
    return status.get("answers_released", False)

def set_classwork_answers_released(course_code, week, released):
    try:
        status_file = get_classwork_status_file(course_code, week)
        status = get_classwork_status(course_code, week)
        status["answers_released"] = released
        with open(status_file, 'w') as f:
            json.dump(status, f)
        return True
    except Exception as e:
        st.error(f"Error setting answer release status: {e}")
        return False

def is_classwork_open(course_code, week):
    status = get_classwork_status(course_code, week)
    return status.get("is_open", False)

def close_classwork_after_20min(course_code, week):
    status = get_classwork_status(course_code, week)
    if status.get("is_open", False) and status.get("open_time"):
        try:
            open_time = datetime.fromisoformat(status["open_time"])
            elapsed = (datetime.now() - open_time).total_seconds()
            if elapsed > 1200:
                set_classwork_status(course_code, week, False)
                return True
        except Exception as e:
            st.error(f"Error in classwork auto-close: {e}")
    return False

# FIX #5: save_classwork now accepts course_code as parameter
def save_classwork(course_code, name, matric, week, answers):
    """Save classwork submissions"""
    try:
        classwork_file = get_file(course_code, "classwork")
        submission_data = {
            'Name': name,
            'Matric': matric,
            'Week': week,
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Answers': json.dumps(answers)
        }
        if os.path.exists(classwork_file):
            df = pd.read_csv(classwork_file)
            existing = df[(df['Name'] == name) & (df['Matric'] == matric) & (df['Week'] == week)]
            if not existing.empty:
                st.warning("⚠️ You have already submitted classwork for this week.")
                return False
            df = pd.concat([df, pd.DataFrame([submission_data])], ignore_index=True)
        else:
            df = pd.DataFrame([submission_data])
        df.to_csv(classwork_file, index=False)
        st.success("✅ Classwork submitted successfully!")
        return True
    except Exception as e:
        st.error(f"Error saving classwork: {e}")
        return False

# ===============================================================
# 📁 FILE MANAGEMENT
# ===============================================================

def save_file(course_code, student_name, week, uploaded_file, folder_name):
    """Safely save uploaded file"""
    if uploaded_file is None:
        return None
    upload_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, folder_name)
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = re.sub(r'[^A-Za-z0-9_-]', '_', student_name.strip())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(upload_dir, f"{safe_name}_{week}_{timestamp}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def log_submission(course_code, matric, student_name, week, file_name, upload_type):
    """Log each upload to CSV file"""
    log_file = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", f"{course_code}_submissions_log.csv")
    new_entry = pd.DataFrame([{
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Matric": matric,
        "Student Name": student_name,
        "Week": week,
        "File": file_name,
        "Type": upload_type
    }])
    if os.path.exists(log_file):
        existing = pd.read_csv(log_file)
        updated = pd.concat([existing, new_entry], ignore_index=True)
    else:
        updated = new_entry
    updated.to_csv(log_file, index=False)

def get_submission_file(course_code, week, student_id):
    """Get the file path for a student's submission"""
    safe_week = week.replace(" ", "_").replace(":", "").lower()
    safe_student_id = str(student_id).replace(" ", "_").replace(":", "").lower()
    submissions_dir = os.path.join("data", "courses", course_code, "submissions", safe_week)
    os.makedirs(submissions_dir, exist_ok=True)
    return os.path.join(submissions_dir, f"{safe_student_id}_submission.json")

def check_existing_submission(course_code, week, student_id):
    """Check if a student has already submitted an assignment"""
    try:
        if not all([course_code, week, student_id]):
            return False, None
        submission_file = get_submission_file(course_code, week, student_id)
        if os.path.exists(submission_file):
            with open(submission_file, 'r') as f:
                submission_data = json.load(f)
            if submission_data.get('submission_text') or submission_data.get('submission_file'):
                return True, submission_data
        return False, None
    except Exception as e:
        st.error(f"Error checking existing submission: {e}")
        return False, None

def save_submission(course_code, week, student_id, submission_data):
    try:
        submission_file = get_submission_file(course_code, week, student_id)
        submission_data['submission_time'] = datetime.now().isoformat()
        submission_data['student_id'] = student_id
        submission_data['week'] = week
        submission_data['course_code'] = course_code
        with open(submission_file, 'w') as f:
            json.dump(submission_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving submission: {e}")
        return False

def get_all_submissions_data(course_code, week=None):
    try:
        submissions_data = []
        course_dir = os.path.join("data", "courses", course_code, "submissions")
        if not os.path.exists(course_dir):
            return pd.DataFrame()
        weeks = [week] if week else os.listdir(course_dir)
        for week_folder in weeks:
            week_path = os.path.join(course_dir, week_folder)
            if not os.path.isdir(week_path):
                continue
            for file in os.listdir(week_path):
                if file.endswith('_submission.json'):
                    file_path = os.path.join(week_path, file)
                    try:
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                        matric = file.replace('_submission.json', '')
                        submissions_data.append({
                            'Matric': matric,
                            'Student Name': data.get('student_name', 'Unknown'),
                            'Week': data.get('week', week_folder),
                            'Submission Time': data.get('submission_time', ''),
                            'File Name': data.get('submission_file', ''),
                            'Submission Text': data.get('submission_text', ''),
                            'JSON File': file
                        })
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
                        continue
        return pd.DataFrame(submissions_data)
    except Exception as e:
        st.error(f"Error getting submissions data: {e}")
        return pd.DataFrame()

def download_assignment_file(course_code, week, matric):
    try:
        submission_file = get_submission_file(course_code, week, matric)
        if os.path.exists(submission_file):
            with open(submission_file, 'r') as f:
                data = json.load(f)
            if data.get('submission_file'):
                file_path = data.get('file_path', '')
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        return f.read(), data['submission_file']
            return json.dumps(data, indent=2).encode(), f"{matric}_submission.json"
        return None, None
    except Exception as e:
        st.error(f"Error downloading assignment: {e}")
        return None, None

def get_student_list_csv(course_code):
    try:
        submissions_df = get_all_submissions_data(course_code)
        if submissions_df.empty:
            return None, "No submissions found"
        student_list = []
        for matric in submissions_df['Matric'].unique():
            student_data = submissions_df[submissions_df['Matric'] == matric].iloc[0]
            submission_count = len(submissions_df[submissions_df['Matric'] == matric])
            student_list.append({
                'Matric Number': matric,
                'Student Name': student_data['Student Name'],
                'Total Submissions': submission_count,
                'Weeks Submitted': ', '.join(submissions_df[submissions_df['Matric'] == matric]['Week'].unique()),
                'Last Submission': submissions_df[submissions_df['Matric'] == matric]['Submission Time'].max()
            })
        student_df = pd.DataFrame(student_list)
        return student_df.to_csv(index=False), f"{course_code}_student_list.csv"
    except Exception as e:
        st.error(f"Error generating student list: {e}")
        return None, None

def get_weekly_submissions_csv(course_code, week):
    try:
        submissions_df = get_all_submissions_data(course_code, week)
        if submissions_df.empty:
            return None, f"No submissions found for {week}"
        weekly_df = submissions_df[['Matric', 'Student Name', 'Submission Time', 'File Name']]
        return weekly_df.to_csv(index=False), f"{course_code}_{week}_submissions.csv"
    except Exception as e:
        st.error(f"Error generating weekly submissions: {e}")
        return None, None

# ===============================================================
# 🎥 VIDEO MANAGEMENT  (FIX #12: only ONE definition each)
# ===============================================================

def get_video_files(course_code):
    """Get list of video files for a course"""
    video_dir = get_persistent_path("video", course_code)
    if not os.path.exists(video_dir):
        return []
    return sorted([f for f in os.listdir(video_dir)
                   if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])

def upload_video(course_code, uploaded_video):
    """Upload video to persistent storage"""
    try:
        video_dir = get_persistent_path("video", course_code)
        os.makedirs(video_dir, exist_ok=True)
        safe_name = "".join(c for c in uploaded_video.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        base_name, ext = os.path.splitext(safe_name)
        save_path = os.path.join(video_dir, safe_name)
        counter = 1
        while os.path.exists(save_path):
            save_path = os.path.join(video_dir, f"{base_name}_{counter}{ext}")
            counter += 1
        with open(save_path, "wb") as f:
            f.write(uploaded_video.getbuffer())
        return True, f"✅ Video uploaded successfully: {os.path.basename(save_path)}"
    except Exception as e:
        return False, f"❌ Error uploading video: {str(e)}"

# ===============================================================
# 📚 LECTURE MANAGEMENT
# ===============================================================

def load_lectures(course_code):
    """Load or create lecture CSV safely"""
    if not course_code:
        return pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment", "PDF_File", "Video_File"])
    lecture_file = get_file(course_code, "lectures")
    os.makedirs(os.path.dirname(lecture_file), exist_ok=True)
    if not os.path.exists(lecture_file):
        df_default = pd.DataFrame({
            "Week": [f"Week {i}" for i in range(1, 16)],
            "Topic": [""] * 15,
            "Brief": [""] * 15,
            "Classwork": [""] * 15,
            "Assignment": [""] * 15,
            "PDF_File": [""] * 15,
            "Video_File": [""] * 15,
        })
        df_default.to_csv(lecture_file, index=False)
        return df_default
    try:
        df = pd.read_csv(lecture_file)
        for col in ["Week", "Topic", "Brief", "Classwork", "Assignment", "PDF_File", "Video_File"]:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"Could not read lecture file: {e}")
        return pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment", "PDF_File", "Video_File"])

# ===============================================================
# 📊 SCORES MANAGEMENT
# ===============================================================

def compute_grade(total_score):
    try:
        total = float(total_score)
        if total >= 70: return "A"
        if total >= 60: return "B"
        if total >= 50: return "C"
        if total >= 45: return "D"
        if total >= 40: return "E"
        return "F"
    except:
        return ""

# FIX #13: Only ONE definition of calculate_final_grade()
def calculate_final_grade(student_scores):
    """Calculate final grade for a student based on all scores"""
    try:
        if student_scores.empty:
            return None, None, 0, 0, 0, 0, 0
        weekly_scores = student_scores[student_scores['Week'] != 'Exam']
        exam_scores = student_scores[student_scores['Week'] == 'Exam']
        assignment_avg = weekly_scores['Assignment'].mean() if not weekly_scores.empty and 'Assignment' in weekly_scores.columns else 0
        test_avg = weekly_scores['Test'].mean() if not weekly_scores.empty and 'Test' in weekly_scores.columns else 0
        practical_avg = weekly_scores['Practical'].mean() if not weekly_scores.empty and 'Practical' in weekly_scores.columns else 0
        classwork_avg = weekly_scores['Classwork'].mean() if not weekly_scores.empty and 'Classwork' in weekly_scores.columns else 0
        exam_score = exam_scores['Exam'].iloc[0] if not exam_scores.empty and 'Exam' in exam_scores.columns else 0
        ca_total = (assignment_avg * 0.08) + (test_avg * 0.08) + (practical_avg * 0.05) + (classwork_avg * 0.09)
        exam_contribution = exam_score * 0.70
        final_total = round(ca_total + exam_contribution, 1)
        final_grade = compute_grade(final_total)
        return final_total, final_grade, assignment_avg, test_avg, practical_avg, classwork_avg, exam_score
    except Exception as e:
        st.error(f"Error calculating final grade: {e}")
        return None, None, 0, 0, 0, 0, 0

def load_student_scores(course_code, student_name, student_matric):
    scores_file = get_file(course_code, "scores")
    ensure_scores_file(course_code)
    if not os.path.exists(scores_file):
        return pd.DataFrame()
    try:
        scores_df = pd.read_csv(scores_file)
        if "StudentName" not in scores_df.columns or "MatricNo" not in scores_df.columns:
            return pd.DataFrame()
        return scores_df[
            (scores_df["StudentName"].astype(str).str.strip().str.lower() == student_name.lower()) &
            (scores_df["MatricNo"].astype(str).str.strip().str.lower() == student_matric.lower())
        ]
    except Exception as e:
        st.error(f"Error loading scores: {e}")
        return pd.DataFrame()

def update_classwork_score(course_code, student_name, student_matric, week, score):
    try:
        scores_file = get_file(course_code, "scores")
        os.makedirs(os.path.dirname(scores_file), exist_ok=True)
        if os.path.exists(scores_file):
            scores_df = pd.read_csv(scores_file)
        else:
            scores_df = pd.DataFrame(columns=["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"])
        mask = (
            (scores_df["StudentName"].astype(str).str.strip().str.lower() == student_name.lower()) &
            (scores_df["MatricNo"].astype(str).str.strip().str.lower() == student_matric.lower()) &
            (scores_df["Week"].astype(str).str.strip().str.lower() == week.lower())
        )
        if mask.any():
            scores_df.loc[mask, "Classwork"] = score
        else:
            weekly_total = round(score * 0.09, 1)
            new_row = {
                "StudentName": student_name.title(),
                "MatricNo": student_matric.upper(),
                "Week": week,
                "Assignment": 0, "Test": 0, "Practical": 0, "Exam": 0,
                "Classwork": score,
                "Total": weekly_total,
                "Grade": compute_grade(weekly_total)
            }
            scores_df = pd.concat([scores_df, pd.DataFrame([new_row])], ignore_index=True)
        scores_df.to_csv(scores_file, index=False)
        return True
    except Exception as e:
        st.error(f"Error updating classwork score: {e}")
        return False

def get_student_activity_summary(course_code, student_name, student_matric):
    summary = {
        "attendance_count": 0,
        "classwork_count": 0,
        "assignment_count": 0,
        "drawing_count": 0,
        "seminar_count": 0,
        "recent_activity": []
    }
    for week_num in range(1, 16):
        week = f"Week {week_num}"
        if has_marked_attendance(course_code, week, student_name, student_matric):
            summary["attendance_count"] += 1
            summary["recent_activity"].append(f"✅ Attended {week}")
    classwork_file = get_file(course_code, "classwork")
    if os.path.exists(classwork_file):
        try:
            classwork_df = pd.read_csv(classwork_file)
            student_classwork = classwork_df[
                (classwork_df['Name'].str.lower() == student_name.lower()) &
                (classwork_df['Matric'].str.lower() == student_matric.lower())
            ]
            summary["classwork_count"] = len(student_classwork)
        except:
            pass
    for sub_type in ["assignment", "drawing", "seminar"]:
        upload_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, sub_type)
        if os.path.exists(upload_dir):
            files = os.listdir(upload_dir)
            student_files = [f for f in files if student_name.lower() in f.lower() and student_matric.lower() in f.lower()]
            count = len(student_files)
            summary[f"{sub_type}_count"] = count
    summary["recent_activity"] = summary["recent_activity"][-10:]
    return summary

# ===============================================================
# 📊 ATTENDANCE VIEWING FUNCTIONS
# ===============================================================

def view_attendance_records(course_code, week):
    try:
        week_key = week.replace(" ", "")
        attendance_file = os.path.join(get_persistent_path("attendance"), f"attendance_{course_code}_{week_key}.csv")
        if not os.path.exists(attendance_file):
            st.warning(f"No attendance records found for {course_code} - {week}")
            return
        df = pd.read_csv(attendance_file)
        if df.empty:
            st.warning(f"No attendance records found for {course_code} - {week}")
            return
        st.success(f"📊 Attendance Records for {course_code} - {week}")
        st.dataframe(df, use_container_width=True)
        st.info(f"**Total students attended:** {len(df)}")
        csv = df.to_csv(index=False)
        st.download_button(label="📥 Download CSV", data=csv,
                           file_name=f"attendance_{course_code}_{week_key}.csv",
                           mime="text/csv", use_container_width=True)
    except Exception as e:
        st.error(f"Error loading attendance records: {e}")

def show_attendance_summary(course_code):
    try:
        summary_data = []
        for week_num in range(1, 16):
            week = f"Week {week_num}"
            week_key = week.replace(" ", "")
            attendance_file = os.path.join(get_persistent_path("attendance"), f"attendance_{course_code}_{week_key}.csv")
            status_data = get_attendance_status(course_code, week)
            is_open = status_data.get("is_open", False)
            status = "🟢 OPEN" if is_open else "🔴 CLOSED"
            if os.path.exists(attendance_file):
                df = pd.read_csv(attendance_file)
                summary_data.append({"Week": week, "Students Attended": len(df), "Status": status})
            else:
                summary_data.append({"Week": week, "Students Attended": 0, "Status": status})
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            total_students = summary_df["Students Attended"].sum()
            weeks_with_attendance = len(summary_df[summary_df["Students Attended"] > 0])
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Attendance Records", total_students)
            with col2:
                st.metric("Weeks with Attendance", weeks_with_attendance)
    except Exception as e:
        st.error(f"Error generating attendance summary: {e}")

def view_student_attendance_details(course_code, week):
    try:
        week_key = week.replace(" ", "")
        attendance_file = os.path.join(get_persistent_path("attendance"), f"attendance_{course_code}_{week_key}.csv")
        if not os.path.exists(attendance_file):
            st.warning(f"No attendance records found for {course_code} - {week}")
            return
        df = pd.read_csv(attendance_file)
        if df.empty:
            st.warning(f"No attendance records found for {course_code} - {week}")
            return
        st.success(f"👥 Student Attendance for {course_code} - {week}")
        st.info(f"**Total students attended:** {len(df)}")
        col1, col2 = st.columns(2)
        with col1:
            search_name = st.text_input("🔍 Search by Name", placeholder="Enter student name...")
        with col2:
            search_matric = st.text_input("🔍 Search by Matric", placeholder="Enter matric number...")
        filtered_df = df.copy()
        if search_name:
            filtered_df = filtered_df[filtered_df['Name'].str.contains(search_name, case=False, na=False)]
        if search_matric:
            filtered_df = filtered_df[filtered_df['Matric'].str.contains(search_matric, case=False, na=False)]
        if not filtered_df.empty:
            st.dataframe(filtered_df, use_container_width=True)
        else:
            st.warning("No students found matching your search criteria.")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Download Filtered", filtered_df.to_csv(index=False),
                               f"attendance_{course_code}_{week_key}_filtered.csv", "text/csv", use_container_width=True)
        with col2:
            st.download_button("📥 Download All", df.to_csv(index=False),
                               f"attendance_{course_code}_{week_key}_all.csv", "text/csv", use_container_width=True)
    except Exception as e:
        st.error(f"Error loading student attendance details: {e}")

def view_all_students_attendance(course_code):
    try:
        st.subheader(f"📊 Complete Student Attendance - {course_code}")
        all_attendance = []
        for week_num in range(1, 16):
            week = f"Week {week_num}"
            week_key = week.replace(" ", "")
            attendance_file = os.path.join(get_persistent_path("attendance"), f"attendance_{course_code}_{week_key}.csv")
            if os.path.exists(attendance_file):
                df = pd.read_csv(attendance_file)
                if not df.empty:
                    df['Week'] = week
                    all_attendance.append(df)
        if not all_attendance:
            st.info(f"No attendance records found for {course_code}")
            return
        combined_df = pd.concat(all_attendance, ignore_index=True)
        col1, col2 = st.columns(2)
        with col1:
            search_student = st.text_input("🔍 Search Student", placeholder="Name or Matric...", key="search_all")
        with col2:
            selected_week = st.selectbox("Filter by Week", ["All Weeks"] + [f"Week {i}" for i in range(1, 16)], key="filter_week")
        filtered_combined = combined_df.copy()
        if search_student:
            filtered_combined = filtered_combined[
                filtered_combined['Name'].str.contains(search_student, case=False, na=False) |
                filtered_combined['Matric'].str.contains(search_student, case=False, na=False)
            ]
        if selected_week != "All Weeks":
            filtered_combined = filtered_combined[filtered_combined['Week'] == selected_week]
        if filtered_combined.empty:
            st.warning("No attendance records found matching your criteria.")
            return
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(filtered_combined))
        with col2:
            st.metric("Unique Students", filtered_combined['Matric'].nunique())
        with col3:
            st.metric("Weeks Covered", filtered_combined['Week'].nunique())
        student_summary = filtered_combined.groupby(['Name', 'Matric']).size().reset_index(name='Attendance Count')
        st.subheader("👥 Student Attendance Summary")
        st.dataframe(student_summary.sort_values('Attendance Count', ascending=False), use_container_width=True)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Download Detailed Records", filtered_combined.to_csv(index=False),
                               f"attendance_{course_code}_detailed.csv", "text/csv", use_container_width=True)
        with col2:
            st.download_button("📥 Download Student Summary", student_summary.to_csv(index=False),
                               f"attendance_{course_code}_student_summary.csv", "text/csv", use_container_width=True)
    except Exception as e:
        st.error(f"Error loading complete attendance: {e}")

def get_global_attendance_summary():
    courses = list(load_courses_config().values())
    summary_data = []
    for course in courses:
        total_students = 0
        weeks_with_data = 0
        for week_num in range(1, 16):
            week = f"Week {week_num}"
            week_key = week.replace(" ", "")
            attendance_file = os.path.join(get_persistent_path("attendance"), f"attendance_{course}_{week_key}.csv")
            if os.path.exists(attendance_file):
                try:
                    df = pd.read_csv(attendance_file)
                    total_students += len(df)
                    weeks_with_data += 1
                except:
                    pass
        summary_data.append({
            "Course": course,
            "Total Attendance Records": total_students,
            "Weeks with Data": weeks_with_data,
            "Average per Week": round(total_students / max(weeks_with_data, 1), 1)
        })
    return pd.DataFrame(summary_data)

# ===============================================================
# 🧩 CLASSWORK VIEWING FUNCTIONS
# ===============================================================

def view_classwork_submissions(course_code, week):
    try:
        classwork_file = get_file(course_code, "classwork")
        if not os.path.exists(classwork_file):
            st.warning(f"No classwork submissions found for {course_code} - {week}")
            return
        df = pd.read_csv(classwork_file)
        if df.empty:
            st.warning(f"No classwork submissions found for {course_code} - {week}")
            return
        week_submissions = df[df['Week'] == week]
        if week_submissions.empty:
            st.warning(f"No classwork submissions found for {course_code} - {week}")
            return
        st.success(f"📝 Classwork Submissions for {course_code} - {week}")
        for idx, row in week_submissions.iterrows():
            with st.expander(f"🧩 {row['Name']} ({row['Matric']}) - {row['Timestamp']}", expanded=False):
                st.write(f"**Student:** {row['Name']} ({row['Matric']})")
                st.write(f"**Submitted:** {row['Timestamp']}")
                try:
                    answers = json.loads(row['Answers'])
                    st.write("**Answers:**")
                    for i, answer in enumerate(answers):
                        if str(answer).strip():
                            st.write(f"**Q{i+1}:** {answer}")
                except:
                    st.write("Unable to parse answers")
        st.download_button("📥 Download Classwork Submissions", week_submissions.to_csv(index=False),
                           f"classwork_{course_code}_{week.replace(' ', '')}.csv", "text/csv", use_container_width=True)
    except Exception as e:
        st.error(f"Error loading classwork submissions: {e}")

# ===============================================================
# 🧩 CLASSWORK DISPLAY FOR STUDENTS
# ===============================================================

def display_classwork_section(course_code, week, student_name, student_matric):
    """Display classwork section for the selected week"""
    try:
        st.markdown("---")
        st.subheader(f"🧩 Classwork - {week}")
        mcq_questions = load_mcq_questions(course_code, week)
        if not mcq_questions or len(mcq_questions) == 0:
            st.info(f"No automated classwork assigned for {week} yet.")
            return

        classwork_status = is_classwork_open(course_code, week)
        answers_released = are_answers_released(course_code, week)
        close_classwork_after_20min(course_code, week)

        if not classwork_status and not answers_released:
            st.info("🔒 Classwork for this week is currently hidden.")
            return

        if classwork_status:
            st.success("✅ Classwork is OPEN - You can submit your answers")
            current_status = get_classwork_status(course_code, week)
            if current_status.get("open_time"):
                try:
                    open_time = datetime.fromisoformat(current_status["open_time"])
                    remaining = max(0, 600 - (datetime.now() - open_time).total_seconds())
                    if remaining > 0:
                        st.info(f"⏳ Auto-closes in {int(remaining//60):02d}:{int(remaining%60):02d}")
                except:
                    pass
        elif answers_released:
            st.info("📚 Classwork is CLOSED - Answers are now available for review")
        else:
            st.warning("🚫 Classwork is CLOSED")

        # Check if already submitted
        classwork_file = get_file(course_code, "classwork")
        already_submitted = False
        previous_score = 0
        submission_data = None
        if os.path.exists(classwork_file):
            try:
                df = pd.read_csv(classwork_file)
                existing = df[
                    (df['Name'].astype(str).str.strip().str.lower() == student_name.lower()) &
                    (df['Matric'].astype(str).str.strip().str.lower() == student_matric.lower()) &
                    (df['Week'].astype(str).str.strip().str.lower() == week.lower()) &
                    (df['Type'] == 'MCQ')
                ]
                already_submitted = not existing.empty
                if already_submitted:
                    submission_data = existing.iloc[0]
                    previous_score = submission_data['Score']
            except Exception as e:
                st.error(f"Error checking previous submissions: {e}")

        if already_submitted:
            st.warning(f"⚠️ You have already submitted this classwork. Your score: **{previous_score}%**")
            with st.expander("📋 View Your Submission", expanded=False):
                st.write(f"**Score:** {previous_score}%")
                st.write(f"**Submitted:** {submission_data['Timestamp']}")
                try:
                    answers = json.loads(submission_data['Answers'])
                    for i, (question, answer) in enumerate(zip(mcq_questions, answers)):
                        st.write(f"**Q{i+1}:** {question['question']}")
                        st.write(f"**Your Answer:** {answer}")
                        if answers_released:
                            correct_answer = question['correct_answer']
                            if question['type'] == 'mcq':
                                st.write(f"**Correct:** {correct_answer} - {question['options'].get(correct_answer, '')}")
                            else:
                                st.write(f"**Correct:** {correct_answer}")
                        else:
                            st.info("🔒 Correct answers will be released by your lecturer.")
                        st.markdown("---")
                except:
                    st.write("Unable to display answer details")
        elif classwork_status:
            with st.form(f"mcq_form_{week.replace(' ', '_')}"):
                st.write("**Answer the following questions:**")
                answers = display_mcq_questions(mcq_questions)
                submit_mcq = st.form_submit_button("🚀 Submit Classwork Answers", use_container_width=True)
                if submit_mcq:
                    if not student_name or not student_matric:
                        st.error("❌ Please set your identity first.")
                    elif any(not str(a).strip() for a in answers):
                        st.error("❌ Please answer all questions before submitting.")
                    else:
                        # Double-check no existing submission
                        double_check = False
                        if os.path.exists(classwork_file):
                            df_check = pd.read_csv(classwork_file)
                            existing_check = df_check[
                                (df_check['Name'].astype(str).str.strip().str.lower() == student_name.lower()) &
                                (df_check['Matric'].astype(str).str.strip().str.lower() == student_matric.lower()) &
                                (df_check['Week'].astype(str).str.strip().str.lower() == week.lower()) &
                                (df_check['Type'] == 'MCQ')
                            ]
                            double_check = not existing_check.empty
                        if double_check:
                            st.error("❌ Submission already exists! You cannot submit twice.")
                        else:
                            score, correct, total = auto_grade_mcq_submission(mcq_questions, answers)
                            success = save_mcq_submission(course_code, week, student_name, student_matric, answers, score)
                            if success:
                                update_classwork_score(course_code, student_name, student_matric, week, score)
                                st.balloons()
                                st.success(f"🎉 Submitted! Score: **{score}%** ({correct}/{total} correct)")
                                st.rerun()
                            else:
                                st.error("❌ Failed to save submission. Please try again.")
        else:
            st.info("⏳ Classwork is closed. Wait for your lecturer to open it.")
    except Exception as e:
        st.error(f"Error displaying classwork section: {e}")

def display_weekly_lecture_materials(course_code, week, student_name, student_matric):
    try:
        lectures_df = load_lectures(course_code)
        if lectures_df.empty:
            st.info(f"No lecture materials available for {week} yet.")
            return
        week_row = lectures_df[lectures_df["Week"] == week]
        if week_row.empty:
            st.info(f"No lecture materials available for {week} yet.")
            return
        row = week_row.iloc[0]
        st.subheader(f"📖 {row['Topic']}")
        col1, col2 = st.columns([3, 1])
        with col1:
            if row["Brief"] and str(row["Brief"]).strip():
                st.markdown(f"**Description:** {row['Brief']}")
            if row["Assignment"] and str(row["Assignment"]).strip():
                st.markdown(f"**Assignment:** {row['Assignment']}")
        with col2:
            pdf_file = str(row.get("PDF_File", "") or "").strip()
            if pdf_file and os.path.exists(pdf_file):
                try:
                    with open(pdf_file, "rb") as pdf_file_obj:
                        file_size = os.path.getsize(pdf_file) / (1024 * 1024)
                        st.download_button(
                            label=f"📥 Download PDF ({file_size:.1f}MB)",
                            data=pdf_file_obj,
                            file_name=os.path.basename(pdf_file),
                            mime="application/pdf",
                            key=f"student_pdf_{week.replace(' ', '_')}"
                        )
                        st.success("✅ PDF available")
                except Exception as e:
                    st.error(f"Error loading PDF: {e}")
            else:
                st.info("No PDF available")
    except Exception as e:
        st.error(f"Error loading lecture materials: {e}")

# ===============================================================
# 📢 PDF ANNOUNCEMENTS
# ===============================================================

def ensure_announcement_directories(course_code):
    pdf_dir = get_pdf_announcements_dir(course_code)
    metadata_dir = os.path.dirname(get_announcements_metadata_file(course_code))
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)

def get_pdf_announcements_dir(course_code):
    return f"data/{course_code}/announcements/pdfs"

def get_announcements_metadata_file(course_code):
    return f"data/{course_code}/announcements/metadata.json"

def get_pdf_file_path(course_code, filename):
    return os.path.join(get_pdf_announcements_dir(course_code), filename)

def save_announcement_metadata(announcement_data):
    try:
        course_code = announcement_data['course_code']
        metadata_file = get_announcements_metadata_file(course_code)
        os.makedirs(os.path.dirname(metadata_file), exist_ok=True)
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        existing_data.append(announcement_data)
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error saving announcement metadata: {e}")
        return False

def load_announcements_metadata(course_code, active_only=True):
    try:
        metadata_file = get_announcements_metadata_file(course_code)
        if not os.path.exists(metadata_file):
            return []
        with open(metadata_file, 'r', encoding='utf-8') as f:
            announcements = json.load(f)
        if active_only:
            current_date = datetime.now().date()
            active = []
            for ann in announcements:
                if not ann.get('is_active', True):
                    continue
                expiry_date = ann.get('expiry_date')
                if expiry_date:
                    try:
                        if datetime.strptime(expiry_date, "%Y-%m-%d").date() < current_date:
                            continue
                    except ValueError:
                        pass
                active.append(ann)
            return active
        return announcements
    except Exception as e:
        st.error(f"Error loading announcements: {e}")
        return []

def update_announcement_status(course_code, filename, is_active):
    try:
        metadata_file = get_announcements_metadata_file(course_code)
        if not os.path.exists(metadata_file):
            return False
        with open(metadata_file, 'r', encoding='utf-8') as f:
            announcements = json.load(f)
        for ann in announcements:
            if ann['filename'] == filename:
                ann['is_active'] = is_active
                break
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(announcements, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        st.error(f"Error updating announcement status: {e}")
        return False

def delete_announcement(course_code, filename):
    try:
        metadata_file = get_announcements_metadata_file(course_code)
        if not os.path.exists(metadata_file):
            return False
        with open(metadata_file, 'r', encoding='utf-8') as f:
            announcements = json.load(f)
        to_delete = None
        updated = []
        for ann in announcements:
            if ann['filename'] == filename:
                to_delete = ann
            else:
                updated.append(ann)
        if to_delete:
            file_path = to_delete.get('file_path') or get_pdf_file_path(course_code, filename)
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(updated, f, indent=2, ensure_ascii=False)
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting announcement: {e}")
        return False

def deactivate_expired_announcements(course_code):
    try:
        metadata_file = get_announcements_metadata_file(course_code)
        if not os.path.exists(metadata_file):
            return 0
        with open(metadata_file, 'r', encoding='utf-8') as f:
            announcements = json.load(f)
        current_date = datetime.now().date()
        deactivated_count = 0
        for ann in announcements:
            if not ann.get('is_active', True):
                continue
            expiry_date = ann.get('expiry_date')
            if expiry_date:
                try:
                    if datetime.strptime(expiry_date, "%Y-%m-%d").date() < current_date:
                        ann['is_active'] = False
                        deactivated_count += 1
                except ValueError:
                    continue
        if deactivated_count > 0:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(announcements, f, indent=2, ensure_ascii=False)
        return deactivated_count
    except Exception as e:
        st.error(f"Error deactivating expired announcements: {e}")
        return 0

def export_announcements_to_csv(course_code):
    try:
        announcements = load_announcements_metadata(course_code, active_only=False)
        if not announcements:
            return None
        df = pd.DataFrame(announcements)
        columns_to_keep = ['title', 'description', 'original_name', 'upload_date', 'expiry_date', 'priority', 'is_active', 'file_size']
        available_columns = [col for col in columns_to_keep if col in df.columns]
        return df[available_columns].to_csv(index=False)
    except Exception as e:
        st.error(f"Error exporting announcements: {e}")
        return None

def display_pdf_announcements_admin(course_code):
    """Admin panel for PDF announcements"""
    st.header(f"📢 PDF Announcements - {course_code}")
    ensure_announcement_directories(course_code)
    tab1, tab2 = st.tabs(["Upload New PDF", "Manage Existing PDFs"])

    with tab1:
        st.subheader("Upload Seminar Topics PDF")
        with st.form(f"pdf_upload_form_{course_code}", clear_on_submit=True):
            uploaded_pdf = st.file_uploader("Choose PDF file", type=['pdf'], key=f"pdf_upload_{course_code}")
            announcement_title = st.text_input("Announcement Title*", placeholder="e.g., BCH201 Seminar Topics - Week 1")
            announcement_description = st.text_area("Description", placeholder="Brief description...")
            expiry_date = st.date_input("Expiry Date (Optional)", value=None)
            col1, col2 = st.columns(2)
            with col1:
                priority = st.selectbox("Priority", ["Normal", "High"])
            with col2:
                is_active = st.checkbox("Active", value=True)
            submitted = st.form_submit_button("📤 Upload PDF Announcement")
            if submitted:
                if uploaded_pdf is not None and announcement_title.strip():
                    try:
                        file_size = len(uploaded_pdf.getvalue()) / (1024 * 1024)
                        if file_size > 10:
                            st.error("❌ File size too large. Maximum: 10MB")
                        else:
                            pdf_dir = get_pdf_announcements_dir(course_code)
                            os.makedirs(pdf_dir, exist_ok=True)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            safe_name = "".join(c for c in uploaded_pdf.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip().replace(' ', '_')
                            filename = f"{timestamp}_{safe_name}"
                            file_path = os.path.join(pdf_dir, filename)
                            counter = 1
                            base_name, ext = os.path.splitext(filename)
                            while os.path.exists(file_path):
                                filename = f"{base_name}_{counter}{ext}"
                                file_path = os.path.join(pdf_dir, filename)
                                counter += 1
                            with open(file_path, "wb") as f:
                                f.write(uploaded_pdf.getbuffer())
                            announcement_data = {
                                'course_code': course_code,
                                'title': announcement_title.strip(),
                                'description': announcement_description,
                                'filename': filename,
                                'original_name': uploaded_pdf.name,
                                'upload_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                'expiry_date': expiry_date.strftime("%Y-%m-%d") if expiry_date else '',
                                'priority': priority,
                                'is_active': is_active,
                                'file_size': f"{file_size:.1f} MB",
                                'type': 'seminar_topics',
                                'file_path': file_path
                            }
                            if save_announcement_metadata(announcement_data):
                                st.success(f"✅ PDF uploaded successfully!")
                            else:
                                st.error("❌ Failed to save metadata")
                                if os.path.exists(file_path):
                                    os.remove(file_path)
                    except Exception as e:
                        st.error(f"❌ Error uploading PDF: {str(e)}")
                else:
                    if uploaded_pdf is None:
                        st.error("❌ Please select a PDF file")
                    if not announcement_title.strip():
                        st.error("❌ Please provide an announcement title")

    with tab2:
        st.subheader("Manage PDF Announcements")
        announcements = load_announcements_metadata(course_code, active_only=False)
        if not announcements:
            st.info("📭 No PDF announcements found for this course.")
            return
        col_search, col_filter = st.columns(2)
        with col_search:
            search_term = st.text_input("🔍 Search announcements", placeholder="Search by title...")
        with col_filter:
            status_filter = st.selectbox("Filter by status", ["All", "Active", "Inactive"])
        filtered_announcements = announcements
        if search_term:
            filtered_announcements = [a for a in filtered_announcements if search_term.lower() in a['title'].lower()]
        if status_filter != "All":
            filtered_announcements = [a for a in filtered_announcements if a.get('is_active', True) == (status_filter == "Active")]
        if not filtered_announcements:
            st.info("No announcements match your search criteria.")
            return
        for announcement in filtered_announcements:
            ann_key = f"{announcement['filename']}_{announcement['upload_date']}"
            with st.expander(f"📄 {announcement['title']} - {announcement['upload_date']}", expanded=False):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**Description:** {announcement.get('description', 'No description')}")
                    st.write(f"**File:** {announcement['original_name']}")
                    st.write(f"**Size:** {announcement.get('file_size', 'N/A')}")
                    st.write(f"**Status:** {'🟢 Active' if announcement.get('is_active', True) else '🔴 Inactive'}")
                with col2:
                    new_status = st.selectbox("Status", ["Active", "Inactive"],
                                              index=0 if announcement.get('is_active', True) else 1,
                                              key=f"status_{ann_key}")
                    if st.button("Update Status", key=f"update_{ann_key}"):
                        if update_announcement_status(course_code, announcement['filename'], new_status == "Active"):
                            st.success("✅ Status updated!")
                            st.rerun()
                    file_path = announcement.get('file_path') or get_pdf_file_path(course_code, announcement['filename'])
                    if file_path and os.path.exists(file_path):
                        with open(file_path, "rb") as file:
                            st.download_button("📥 Download", data=file,
                                               file_name=announcement['original_name'],
                                               mime="application/pdf",
                                               key=f"download_{ann_key}",
                                               use_container_width=True)
                    else:
                        st.error("❌ File not found on server")
                    if st.button("🗑️ Delete", key=f"delete_{ann_key}", use_container_width=True):
                        if delete_announcement(course_code, announcement['filename']):
                            st.success("✅ Announcement deleted!")
                            st.rerun()

def display_pdf_announcements_student(course_code):
    """Student view for PDF announcements"""
    st.header(f"📢 Course Announcements - {course_code}")
    deactivated_count = deactivate_expired_announcements(course_code)
    if deactivated_count > 0:
        st.info(f"📢 {deactivated_count} expired announcement(s) have been deactivated.")
    announcements = load_announcements_metadata(course_code, active_only=True)
    if announcements:
        announcements.sort(key=lambda x: x['upload_date'], reverse=True)
        for announcement in announcements:
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            with col1:
                if announcement.get('priority') == 'High':
                    st.error(f"🚨 **{announcement['title']}**")
                else:
                    st.subheader(f"📄 {announcement['title']}")
            with col2:
                st.write(f"**Date:** {announcement['upload_date'].split()[0]}")
            if announcement.get('description'):
                st.write(announcement['description'])
            col1, col2 = st.columns([2, 1])
            with col1:
                st.write(f"**File:** {announcement['original_name']}")
                st.write(f"**Size:** {announcement.get('file_size', 'N/A')}")
                if announcement.get('expiry_date'):
                    try:
                        expiry_date = datetime.strptime(announcement['expiry_date'], "%Y-%m-%d").date()
                        days_remaining = (expiry_date - datetime.now().date()).days
                        if days_remaining <= 7 and days_remaining >= 0:
                            st.warning(f"⚠️ Expires in {days_remaining} days")
                    except:
                        pass
            with col2:
                file_path = announcement.get('file_path') or get_pdf_file_path(course_code, announcement['filename'])
                if file_path and os.path.exists(file_path):
                    with open(file_path, "rb") as file:
                        st.download_button("📥 Download PDF", data=file,
                                           file_name=announcement['original_name'],
                                           mime="application/pdf",
                                           key=f"download_{announcement['filename']}",
                                           use_container_width=True)
                else:
                    st.error("File not available")
    else:
        st.info("📝 No active announcements for this course.")

# ===============================================================
# 📝 SEMINAR FUNCTIONS
# ===============================================================

def check_existing_seminar_submission(course_code, student_matric):
    try:
        with open("seminar_submissions.csv", "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['course_code'] == course_code and row['student_matric'] == student_matric:
                    return True, row
        return False, None
    except FileNotFoundError:
        return False, None

def save_seminar_file(course_code, student_name, student_matric, file):
    try:
        file_extension = file.name.split('.')[-1]
        file_path = f"./seminar/{course_code}/{student_matric}_{student_name}.{file_extension}"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def log_seminar_submission(course_code, student_matric, student_name, topic, file_name):
    try:
        with open("seminar_submissions.csv", "a", newline='') as file:
            fieldnames = ['course_code', 'student_matric', 'student_name', 'topic', 'file_name', 'file_path', 'timestamp']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            file_path = f"./seminar/{course_code}/{student_matric}_{student_name}.{file_name.split('.')[-1]}"
            writer.writerow({
                'course_code': course_code,
                'student_matric': student_matric,
                'student_name': student_name,
                'topic': topic,
                'file_name': file_name,
                'file_path': file_path,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    except Exception as e:
        st.error(f"Error logging submission: {e}")

def get_seminar_submissions(course_code):
    try:
        submissions = []
        with open("seminar_submissions.csv", "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['course_code'] == course_code:
                    submissions.append(row)
        return submissions
    except FileNotFoundError:
        return []

def get_seminar_feedback(student_matric, course_code):
    try:
        with open("seminar_feedback.csv", "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['student_matric'] == student_matric and row['course_code'] == course_code:
                    return row.get('feedback_text', '') or "Feedback file provided"
        return None
    except FileNotFoundError:
        return None

# FIX #6: Added missing get_seminar_feedback_file_path()
def get_seminar_feedback_file_path(student_matric, course_code):
    """Get the file path for a student's seminar feedback PDF"""
    return f"./seminar_feedback/{course_code}/{student_matric}_feedback.pdf"

def save_seminar_feedback(student_matric, course_code, feedback_file=None, feedback_text=""):
    try:
        feedback_data = {
            'student_matric': student_matric,
            'course_code': course_code,
            'feedback_text': feedback_text,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if feedback_file:
            file_path = get_seminar_feedback_file_path(student_matric, course_code)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(feedback_file.getbuffer())
            feedback_data['feedback_file'] = file_path
        with open("seminar_feedback.csv", "a", newline='') as file:
            fieldnames = ['student_matric', 'course_code', 'feedback_text', 'feedback_file', 'timestamp']
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if file.tell() == 0:
                writer.writeheader()
            writer.writerow(feedback_data)
        return True
    except Exception as e:
        st.error(f"Error saving feedback: {e}")
        return False

# ===============================================================
# 📝 COURSE DESCRIPTION FUNCTIONS
# ===============================================================

def load_course_description(course_code):
    try:
        desc_file = os.path.join(PERSISTENT_DATA_DIR, "course_descriptions.json")
        if os.path.exists(desc_file):
            with open(desc_file, 'r') as f:
                all_descriptions = json.load(f)
                return all_descriptions.get(course_code, {})
        return {}
    except Exception as e:
        print(f"Error loading course description: {e}")
        return {}

def save_course_description(course_code, course_data):
    try:
        desc_file = os.path.join(PERSISTENT_DATA_DIR, "course_descriptions.json")
        if os.path.exists(desc_file):
            with open(desc_file, 'r') as f:
                all_descriptions = json.load(f)
        else:
            all_descriptions = {}
        all_descriptions[course_code] = course_data
        with open(desc_file, 'w') as f:
            json.dump(all_descriptions, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving course description: {e}")
        return False

def reset_course_description(course_code):
    try:
        desc_file = os.path.join(PERSISTENT_DATA_DIR, "course_descriptions.json")
        if os.path.exists(desc_file):
            with open(desc_file, 'r') as f:
                all_descriptions = json.load(f)
            if course_code in all_descriptions:
                del all_descriptions[course_code]
            with open(desc_file, 'w') as f:
                json.dump(all_descriptions, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error resetting course description: {e}")
        return False

def display_course_description_preview(course_info):
    if not course_info:
        st.info("No course description available yet.")
        return
    if course_info.get('overview'):
        st.subheader("🎯 Course Overview")
        st.write(course_info['overview'])
    if course_info.get('outcomes'):
        st.subheader("📚 Learning Outcomes")
        st.write(course_info['outcomes'])
    if course_info.get('instructor_name'):
        st.subheader("👨‍🏫 Instructor Information")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Name:** {course_info['instructor_name']}")
            if course_info.get('instructor_email'):
                st.write(f"**Email:** {course_info['instructor_email']}")
        with col2:
            if course_info.get('office_hours'):
                st.write(f"**Office Hours:** {course_info['office_hours']}")
            if course_info.get('office_location'):
                st.write(f"**Office Location:** {course_info['office_location']}")
    col1, col2 = st.columns(2)
    with col1:
        if course_info.get('prerequisites'):
            st.subheader("📋 Prerequisites")
            st.write(course_info['prerequisites'])
        if course_info.get('materials'):
            st.subheader("📖 Required Materials")
            st.write(course_info['materials'])
    with col2:
        if course_info.get('assessment'):
            st.subheader("📊 Assessment Methods")
            st.write(course_info['assessment'])
        if course_info.get('schedule'):
            st.subheader("🗓️ Course Schedule")
            st.write(course_info['schedule'])
    if course_info.get('contact_policy'):
        st.subheader("📞 Contact Policy")
        st.write(course_info['contact_policy'])
    if course_info.get('last_updated'):
        st.caption(f"Last updated: {course_info['last_updated']}")

def calculate_info_completeness(course_info):
    if not course_info:
        return 0
    required_fields = ['overview', 'outcomes', 'instructor_name', 'assessment']
    filled_fields = [f for f in required_fields if course_info.get(f)]
    return int((len(filled_fields) / len(required_fields)) * 100)

def show_student_course_description(course_code, course_name):
    st.header(f"📝 {course_name} - Course Information")
    course_info = load_course_description(course_code)
    if not course_info:
        st.info("📋 Course description is being prepared by your lecturer. Check back soon!")
        return
    display_course_description_preview(course_info)

# ===============================================================
# 📊 SYSTEM LOGGING
# ===============================================================

def get_system_logs_file():
    return os.path.join(PERSISTENT_DATA_DIR, "system_logs.json")

def init_system_logs():
    logs_file = get_system_logs_file()
    if not os.path.exists(logs_file):
        with open(logs_file, 'w') as f:
            json.dump({"lecturer_logs": [], "student_logs": []}, f)

def log_lecturer_activity(lecturer_name, course_code, action, details=""):
    try:
        logs_file = get_system_logs_file()
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = {"lecturer_logs": [], "student_logs": []}
        logs["lecturer_logs"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lecturer_name": lecturer_name,
            "course_code": course_code,
            "action": action,
            "details": details
        })
        if len(logs["lecturer_logs"]) > 1000:
            logs["lecturer_logs"] = logs["lecturer_logs"][-1000:]
        with open(logs_file, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Error logging lecturer activity: {e}")

def log_student_activity(student_name, matric, course_code, action, details=""):
    try:
        logs_file = get_system_logs_file()
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = {"lecturer_logs": [], "student_logs": []}
        logs["student_logs"].append({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "student_name": student_name,
            "matric": matric,
            "course_code": course_code,
            "action": action,
            "details": details
        })
        if len(logs["student_logs"]) > 1000:
            logs["student_logs"] = logs["student_logs"][-1000:]
        with open(logs_file, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Error logging student activity: {e}")

def get_lecturer_logs():
    try:
        logs_file = get_system_logs_file()
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs = json.load(f)
            return logs.get("lecturer_logs", [])
        return []
    except:
        return []

def get_student_logs():
    try:
        logs_file = get_system_logs_file()
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs = json.load(f)
            return logs.get("student_logs", [])
        return []
    except:
        return []

def is_recent(timestamp, days=1):
    try:
        log_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - log_time).days <= days
    except:
        return False

@st.cache_data(ttl=60)
def get_lecturer_logs_cached():
    return get_lecturer_logs()

@st.cache_data(ttl=60)
def get_student_logs_cached():
    return get_student_logs()

@st.cache_data(ttl=300)
def load_courses_config_cached():
    return load_courses_config()

def generate_system_report():
    lecturer_logs = get_lecturer_logs_cached()
    student_logs = get_student_logs_cached()
    courses = load_courses_config_cached()
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_courses": len(courses),
        "total_lecturer_activities": len(lecturer_logs),
        "total_student_activities": len(student_logs),
        "active_lecturers": len(set(log['lecturer_name'] for log in lecturer_logs)),
        "active_students": len(set(log['student_name'] for log in student_logs)),
        "courses": list(courses.values())
    }
    report_file = os.path.join(PERSISTENT_DATA_DIR, f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    return report

# ===============================================================
# 🏫 COURSE MANAGEMENT (ADMIN)
# ===============================================================

def show_course_manager(course_code, course_name):
    st.header(f"📚 Course Manager - {course_name}")
    cm_tab1, cm_tab2 = st.tabs(["📝 About Course", "⚙️ Course Data"])

    with cm_tab1:
        st.subheader("📝 Course Description & Information")
        course_info = load_course_description(course_code)
        with st.form(f"course_description_form_{course_code}"):
            course_overview = st.text_area("**Course Overview & Description**",
                                           value=course_info.get('overview', ''), height=120,
                                           placeholder="Describe the course objectives...",
                                           key=f"overview_{course_code}")
            col1, col2 = st.columns(2)
            with col1:
                learning_outcomes = st.text_area("**Learning Outcomes**", value=course_info.get('outcomes', ''), height=100,
                                                 key=f"outcomes_{course_code}")
                prerequisites = st.text_area("**Prerequisites**", value=course_info.get('prerequisites', ''), height=80,
                                             key=f"prerequisites_{course_code}")
            with col2:
                assessment = st.text_area("**Assessment Methods**", value=course_info.get('assessment', ''), height=100,
                                          key=f"assessment_{course_code}")
                materials = st.text_area("**Required Materials**", value=course_info.get('materials', ''), height=80,
                                         key=f"materials_{course_code}")
            schedule_overview = st.text_area("**Course Schedule Overview**", value=course_info.get('schedule', ''), height=80,
                                             key=f"schedule_{course_code}")
            st.subheader("👨‍🏫 Instructor Information")
            col1, col2 = st.columns(2)
            with col1:
                instructor_name = st.text_input("Instructor Name", value=course_info.get('instructor_name', ''),
                                                key=f"instructor_name_{course_code}")
                instructor_email = st.text_input("Email", value=course_info.get('instructor_email', ''),
                                                 key=f"instructor_email_{course_code}")
            with col2:
                office_hours = st.text_input("Office Hours", value=course_info.get('office_hours', ''),
                                             key=f"office_hours_{course_code}")
                office_location = st.text_input("Office Location", value=course_info.get('office_location', ''),
                                                key=f"office_location_{course_code}")
            contact_policy = st.text_area("**Contact Policy**", value=course_info.get('contact_policy', ''), height=60,
                                          key=f"contact_policy_{course_code}")
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.form_submit_button("💾 Save Course Description", type="primary", use_container_width=True):
                    course_data = {
                        'overview': course_overview, 'outcomes': learning_outcomes, 'prerequisites': prerequisites,
                        'assessment': assessment, 'materials': materials, 'schedule': schedule_overview,
                        'instructor_name': instructor_name, 'instructor_email': instructor_email,
                        'office_hours': office_hours, 'office_location': office_location,
                        'contact_policy': contact_policy,
                        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    if save_course_description(course_code, course_data):
                        st.success("✅ Course description saved successfully!")
                    else:
                        st.error("❌ Failed to save course description")
            with col2:
                if st.form_submit_button("🔄 Reset Form", use_container_width=True):
                    st.rerun()
        st.divider()
        st.subheader("👁️ Course Description Preview")
        display_course_description_preview(course_info)

    with cm_tab2:
        st.subheader("Course Data Management")
        course_info = load_course_description(course_code)
        if course_info:
            info_completeness = calculate_info_completeness(course_info)
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Description Completeness", f"{info_completeness}%")
            with col2:
                filled_fields = len([v for v in course_info.values() if v])
                st.metric("Fields Completed", f"{filled_fields}/{len(course_info)}")
            with col3:
                last_updated = course_info.get('last_updated', 'Never')
                st.metric("Last Updated", last_updated.split()[0] if last_updated != 'Never' else 'Never')
            st.progress(info_completeness / 100)
        st.subheader("📤 Export Course Data")
        col1, col2 = st.columns(2)
        with col1:
            if course_info:
                st.download_button("📥 Download Course Info (JSON)", json.dumps(course_info, indent=2),
                                   f"{course_code}_course_description.json", "application/json",
                                   use_container_width=True, key=f"export_info_{course_code}")
        with col2:
            if course_info:
                csv_lines = [f"{k},{v}" for k, v in course_info.items() if k != 'last_updated']
                st.download_button("📥 Download Course Info (CSV)", "\n".join(csv_lines),
                                   f"{course_code}_course_description.csv", "text/csv",
                                   use_container_width=True, key=f"export_csv_{course_code}")
        st.subheader("🔄 Data Management")
        with st.expander("Reset Course Information", expanded=False):
            st.warning("⚠️ This will delete all course description data!")
            if st.button("🗑️ Reset Course Description", type="secondary", use_container_width=True):
                if reset_course_description(course_code):
                    st.success("✅ Course description reset!")
                    st.rerun()

# ===============================================================
# 🏢 SYSTEM ADMIN DASHBOARD
# ===============================================================

def process_bulk_courses(bulk_text, existing_courses, separator, import_mode, skip_duplicates, auto_generate_codes):
    results = {'success': [], 'errors': [], 'duplicates': [], 'total_processed': 0}
    lines = [line.strip() for line in bulk_text.split('\n') if line.strip()]
    results['total_processed'] = len(lines)
    if import_mode == "Replace all courses":
        existing_courses.clear()
    for i, line in enumerate(lines, 1):
        try:
            if separator in line:
                parts = [p.strip() for p in line.split(separator)]
            elif ',' in line:
                parts = [p.strip() for p in line.split(',')]
            elif '|' in line:
                parts = [p.strip() for p in line.split('|')]
            else:
                parts = [line]
            if len(parts) >= 2:
                course_name = parts[0]
                course_code = parts[1].upper()
            else:
                course_name = parts[0]
                if auto_generate_codes:
                    code_match = re.findall(r'[A-Z]+\s*\d+', course_name)
                    if code_match:
                        course_code = code_match[0].replace(' ', '')
                    else:
                        words = course_name.split()
                        course_code = (words[0][0] + words[1][0]).upper() + "101" if len(words) >= 2 else course_name[:6].upper().replace(' ', '')
                else:
                    results['errors'].append(f"Line {i}: Cannot extract course code - '{line}'")
                    continue
            if not course_name or not course_code:
                results['errors'].append(f"Line {i}: Missing course name or code - '{line}'")
                continue
            if course_name in existing_courses:
                results['duplicates'].append(f"Line {i}: Course name exists - '{course_name}'")
                continue
            if skip_duplicates and course_code in existing_courses.values():
                results['duplicates'].append(f"Line {i}: Course code exists - '{course_code}'")
                continue
            existing_courses[course_name] = course_code
            results['success'].append(f"'{course_name}' - {course_code}")
        except Exception as e:
            results['errors'].append(f"Line {i}: Error - '{line}' - {str(e)}")
    if results['success']:
        save_courses_config(existing_courses)
    return results

def display_import_results(results):
    st.subheader("📊 Import Results")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Successful", len(results['success']))
    with col2:
        st.metric("Errors", len(results['errors']))
    with col3:
        st.metric("Duplicates", len(results['duplicates']))
    if results['success']:
        st.success(f"✅ Successfully imported {len(results['success'])} courses:")
        for s in results['success']:
            st.write(f"• {s}")
    if results['errors']:
        st.error(f"❌ {len(results['errors'])} errors:")
        for e in results['errors']:
            st.write(f"• {e}")
    if results['duplicates']:
        st.warning(f"⚠️ {len(results['duplicates'])} duplicates skipped:")
        for d in results['duplicates']:
            st.write(f"• {d}")
    if results['success']:
        st.rerun()

def show_course_management():
    st.header("🏫 Course Management System")
    courses = load_courses_config()
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Manage Courses", "📥 Bulk Import", "🔑 Manage Passwords", "📊 System Overview"])

    with tab1:
        st.subheader("Add/Remove Courses")
        col1, col2 = st.columns(2)
        with col1:
            new_course_name = st.text_input("New Course Name", placeholder="e.g., CHEM 101 - Organic Chemistry")
        with col2:
            new_course_code = st.text_input("Course Code", placeholder="e.g., CHEM101").upper()
        if st.button("➕ Add Course", type="primary", key="add_course_btn"):
            if new_course_name and new_course_code:
                if new_course_name in courses:
                    st.error("❌ Course name already exists!")
                else:
                    courses[new_course_name] = new_course_code
                    if save_courses_config(courses):
                        st.success(f"✅ Course '{new_course_name}' added!")
                        st.rerun()
            else:
                st.error("❌ Please enter both course name and code.")
        st.subheader("Current Courses")
        if courses:
            course_list = list(courses.items())
            for idx, (course_name, course_code) in enumerate(course_list):
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f'<div class="course-card">{course_name}<br><small>Code: {course_code}</small></div>', unsafe_allow_html=True)
                    with col2:
                        edit_key = f"edit_{idx}_{course_name.replace(' ', '_')}"
                        if st.button("✏️", key=edit_key):
                            st.session_state[edit_key] = True
                    with col3:
                        delete_key = f"delete_{idx}_{course_name.replace(' ', '_')}"
                        if st.button("🗑️", key=delete_key):
                            del courses[course_name]
                            save_courses_config(courses)
                            st.success(f"✅ Course '{course_name}' deleted!")
                            st.rerun()
                    if st.session_state.get(edit_key, False):
                        with st.form(f"edit_form_{idx}_{course_name.replace(' ', '_')}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                edited_name = st.text_input("Course Name", value=course_name, key=f"name_{idx}_{course_code}")
                            with col2:
                                edited_code = st.text_input("Course Code", value=course_code, key=f"code_{idx}_{course_code}").upper()
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save Changes"):
                                    if edited_name and edited_code:
                                        del courses[course_name]
                                        courses[edited_name] = edited_code
                                        save_courses_config(courses)
                                        st.session_state[edit_key] = False
                                        st.success("✅ Course updated!")
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Cancel"):
                                    st.session_state[edit_key] = False
                                    st.rerun()
        else:
            st.info("No courses added yet.")

    with tab2:
        st.subheader("📥 Bulk Course Import")
        st.info("Format: `Course Name | Course Code` or `Course Name, Course Code` (one per line)")
        bulk_courses_text = st.text_area("Paste courses here:", height=200, key="bulk_courses_textarea")
        col1, col2 = st.columns(2)
        with col1:
            separator = st.selectbox("Separator", [",", "|", "Tab", "Custom"], key="separator_select")
            if separator == "Custom":
                separator = st.text_input("Custom separator", value=";", key="custom_sep")
            elif separator == "Tab":
                separator = "\t"
        with col2:
            st.write("**Preview:**")
            if bulk_courses_text:
                lines = [line.strip() for line in bulk_courses_text.split('\n') if line.strip()]
                st.write(f"Found {len(lines)} courses to import")
        col1, col2 = st.columns(2)
        with col1:
            import_mode = st.radio("Import Mode", ["Add new only", "Replace all courses"], key="import_mode")
        with col2:
            remove_duplicates = st.checkbox("Remove duplicate course code", value=True, key="remove_duplicates")
            auto_generate_codes = st.checkbox("Auto-generate missing codes", key="auto_generate_codes")
        if st.button("🚀 Import Courses", type="primary", key="import_courses_btn"):
            if bulk_courses_text:
                results = process_bulk_courses(bulk_courses_text, courses, separator, import_mode, remove_duplicates, auto_generate_codes)
                display_import_results(results)
            else:
                st.error("❌ Please paste some courses to import!")

    with tab3:
        st.subheader("Manage Admin Passwords")
        passwords = load_admin_passwords()
        courses = load_courses_config()
        if courses:
            st.write("**Bulk Password Operations:**")
            col1, col2 = st.columns(2)
            with col1:
                new_bulk_password = st.text_input("Set same password for all courses", type="password", key="bulk_password")
                if st.button("🔑 Apply to All Courses", key="apply_bulk_password"):
                    if new_bulk_password:
                        for course_code in courses.values():
                            set_course_password(course_code, new_bulk_password)
                        st.success("✅ Password applied to all courses!")
                        st.rerun()
            with col2:
                if st.button("🔄 Reset All to Default", key="reset_all_passwords"):
                    for course_code in courses.values():
                        set_course_password(course_code, DEFAULT_ADMIN_PASSWORD)
                    st.success("✅ All passwords reset to default!")
                    st.rerun()
            st.divider()
            course_list = list(courses.items())
            for idx, (course_name, course_code) in enumerate(course_list):
                current_password = passwords.get(course_code, DEFAULT_ADMIN_PASSWORD)
                with st.expander(f"🔐 {course_name} ({course_code})", expanded=False):
                    st.info(f"Current password: **{current_password}**")
                    col1, col2 = st.columns(2)
                    with col1:
                        new_password = st.text_input("New Password", type="password", key=f"new_pass_{idx}_{course_code}")
                    with col2:
                        confirm_password = st.text_input("Confirm Password", type="password", key=f"confirm_pass_{idx}_{course_code}")
                    if st.button("🔄 Change Password", key=f"change_{idx}_{course_code}"):
                        if new_password and confirm_password:
                            if new_password == confirm_password:
                                if set_course_password(course_code, new_password):
                                    st.success("✅ Password changed!")
                                    st.rerun()
                            else:
                                st.error("❌ Passwords don't match!")
                        else:
                            st.error("❌ Please enter and confirm new password!")
        else:
            st.info("No courses available. Add courses first.")

    with tab4:
        st.subheader("System Overview")
        courses = load_courses_config()
        passwords = load_admin_passwords()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Courses", len(courses))
        with col2:
            custom_passwords = len([code for code in courses.values() if code in passwords])
            st.metric("Custom Passwords", custom_passwords)
        with col3:
            st.metric("Default Passwords", len(courses) - custom_passwords)
        if courses:
            overview_data = [{"Course Name": n, "Course Code": c, "Password": "Custom" if c in passwords else "Default"}
                             for n, c in courses.items()]
            st.dataframe(pd.DataFrame(overview_data), use_container_width=True)
            st.download_button("📥 Export Courses to CSV", pd.DataFrame(overview_data).to_csv(index=False),
                               "courses_export.csv", "text/csv", key="export_courses_btn")

def show_system_overview():
    st.header("📊 System Overview")
    courses = load_courses_config_cached()
    lecturer_logs = get_lecturer_logs_cached()
    student_logs = get_student_logs_cached()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Courses", len(courses))
    with col2:
        active_lecturers = len(set(log['lecturer_name'] for log in lecturer_logs if is_recent(log['timestamp'], 7)))
        st.metric("Active Lecturers (7d)", active_lecturers)
    with col3:
        active_students = len(set(log['student_name'] for log in student_logs if is_recent(log['timestamp'], 7)))
        st.metric("Active Students (7d)", active_students)
    with col4:
        st.metric("Total Activities", len(lecturer_logs) + len(student_logs))
    st.subheader("🕒 Recent Activity Timeline")
    all_logs = []
    for log in lecturer_logs[-20:]:
        log_copy = dict(log)
        log_copy['type'] = 'Lecturer'
        all_logs.append(log_copy)
    for log in student_logs[-20:]:
        log_copy = dict(log)
        log_copy['type'] = 'Student'
        all_logs.append(log_copy)
    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    if all_logs:
        for log in all_logs[:10]:
            if log['type'] == 'Lecturer':
                st.write(f"👩‍🏫 **{log['lecturer_name']}** - {log['action']} - *{log['timestamp']}*")
            else:
                st.write(f"🎓 **{log['student_name']}** - {log['action']} - *{log['timestamp']}*")
            if log.get('details'):
                st.caption(f"Details: {log['details']}")
            st.divider()
    else:
        st.info("No recent activity recorded")

def show_lecturer_activity():
    st.header("👩‍🏫 Lecturer Activity Monitor")
    lecturer_logs = get_lecturer_logs_cached()
    if not lecturer_logs:
        st.info("No lecturer activity recorded yet")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        date_filter = st.selectbox("Time Filter", ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days"])
    with col2:
        lecturers = sorted(set(log['lecturer_name'] for log in lecturer_logs))
        lecturer_filter = st.selectbox("Filter by Lecturer", ["All Lecturers"] + lecturers)
    with col3:
        actions = sorted(set(log['action'] for log in lecturer_logs))
        action_filter = st.selectbox("Filter by Action", ["All Actions"] + actions)
    filtered_logs = lecturer_logs
    if date_filter != "All Time":
        cutoff = datetime.now() - timedelta(hours=24 if "24" in date_filter else (7 if "7" in date_filter else 30)*24)
        filtered_logs = [log for log in filtered_logs if datetime.strptime(log['timestamp'], "%Y-%m-%d %H:%M:%S") > cutoff]
    if lecturer_filter != "All Lecturers":
        filtered_logs = [log for log in filtered_logs if log['lecturer_name'] == lecturer_filter]
    if action_filter != "All Actions":
        filtered_logs = [log for log in filtered_logs if log['action'] == action_filter]
    if filtered_logs:
        log_data = [{'Timestamp': l['timestamp'], 'Lecturer': l['lecturer_name'], 'Course': l['course_code'], 'Action': l['action'], 'Details': l.get('details', '')} for l in filtered_logs]
        df = pd.DataFrame(log_data)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Lecturer Logs (CSV)", df.to_csv(index=False), "lecturer_activity_logs.csv", "text/csv")
    else:
        st.info("No lecturer activity matching the filters")

def show_student_activity():
    st.header("🎓 Student Activity Monitor")
    student_logs = get_student_logs_cached()
    if not student_logs:
        st.info("No student activity recorded yet")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        date_filter = st.selectbox("Time Filter", ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days"], key="student_date_filter")
    with col2:
        courses = sorted(set(log['course_code'] for log in student_logs))
        course_filter = st.selectbox("Filter by Course", ["All Courses"] + courses)
    with col3:
        actions = sorted(set(log['action'] for log in student_logs))
        action_filter = st.selectbox("Filter by Action", ["All Actions"] + actions, key="student_action_filter")
    filtered_logs = student_logs
    if date_filter != "All Time":
        cutoff = datetime.now() - timedelta(hours=24 if "24" in date_filter else (7 if "7" in date_filter else 30)*24)
        filtered_logs = [log for log in filtered_logs if datetime.strptime(log['timestamp'], "%Y-%m-%d %H:%M:%S") > cutoff]
    if course_filter != "All Courses":
        filtered_logs = [log for log in filtered_logs if log['course_code'] == course_filter]
    if action_filter != "All Actions":
        filtered_logs = [log for log in filtered_logs if log['action'] == action_filter]
    if filtered_logs:
        log_data = [{'Timestamp': l['timestamp'], 'Student': l['student_name'], 'Matric': l['matric'], 'Course': l['course_code'], 'Action': l['action'], 'Details': l.get('details', '')} for l in filtered_logs]
        df = pd.DataFrame(log_data)
        st.dataframe(df, use_container_width=True)
        st.download_button("📥 Download Student Logs (CSV)", df.to_csv(index=False), "student_activity_logs.csv", "text/csv")
    else:
        st.info("No student activity matching the filters")

def show_analytics():
    st.header("📈 System Analytics")
    lecturer_logs = get_lecturer_logs_cached()
    student_logs = get_student_logs_cached()
    if not lecturer_logs and not student_logs:
        st.info("No data available for analytics")
        return
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    lecturer_daily = {d: 0 for d in dates}
    student_daily = {d: 0 for d in dates}
    for log in lecturer_logs:
        log_date = log['timestamp'].split()[0]
        if log_date in lecturer_daily:
            lecturer_daily[log_date] += 1
    for log in student_logs:
        log_date = log['timestamp'].split()[0]
        if log_date in student_daily:
            student_daily[log_date] += 1
    trend_df = pd.DataFrame({
        'Date': dates,
        'Lecturer Activities': [lecturer_daily[d] for d in dates],
        'Student Activities': [student_daily[d] for d in dates]
    })
    st.line_chart(trend_df.set_index('Date'))

def show_system_settings():
    st.header("🔧 System Settings")
    st.subheader("ℹ️ System Information")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("System Admin Password", "🔒 Secured")
    with col2:
        st.metric("Data Directory", PERSISTENT_DATA_DIR)
    st.subheader("🛠️ System Maintenance")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Clear All Logs", type="secondary"):
            logs_file = get_system_logs_file()
            if os.path.exists(logs_file):
                with open(logs_file, 'w') as f:
                    json.dump({"lecturer_logs": [], "student_logs": []}, f)
                st.success("✅ All system logs cleared!")
    with col2:
        if st.button("📊 Generate System Report", type="primary"):
            generate_system_report()
            st.success("✅ System report generated!")

def show_alert_center():
    st.header("🚨 Alert Center")
    lecturer_logs = get_lecturer_logs_cached()
    student_logs = get_student_logs_cached()
    alerts = []
    if not any(is_recent(log['timestamp'], 1) for log in lecturer_logs):
        alerts.append("⚠️ No lecturer activity in the last 24 hours")
    if not any(is_recent(log['timestamp'], 1) for log in student_logs):
        alerts.append("⚠️ No student activity in the last 24 hours")
    error_actions = [log for log in lecturer_logs + student_logs if 'error' in log.get('action', '').lower() or 'fail' in log.get('action', '').lower()]
    if error_actions:
        alerts.append(f"🚨 {len(error_actions)} error/failure actions detected")
    if alerts:
        for alert in alerts:
            st.error(alert)
    else:
        st.success("✅ All systems operational - No critical alerts")

def show_system_admin_dashboard():
    st.title("🏢 System Administration Dashboard")
    st.sidebar.subheader("🔐 System Admin Access")
    sys_admin_password = st.sidebar.text_input("System Admin Password", type="password", key="sys_admin_pass")
    if sys_admin_password != SYSTEM_ADMIN_PASSWORD:
        st.warning("Enter the System Admin password to continue")
        return
    st.success("✅ Logged in as System Administrator")
    init_system_logs()
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 System Overview", "🏫 Course Management", "👩‍🏫 Lecturer Activity",
        "🎓 Student Activity", "📈 Analytics", "🔧 System Settings", "🚨 Alert Center"
    ])
    with tab1:
        show_system_overview()
    with tab2:
        show_course_management()
    with tab3:
        show_lecturer_activity()
    with tab4:
        show_student_activity()
    with tab5:
        show_analytics()
    with tab6:
        show_system_settings()
    with tab7:
        show_alert_center()

# ===============================================================
# 🎓 STUDENT VIEW
# ===============================================================

def student_view(course_code, course_name):
    """Student dashboard view"""
    try:
        ensure_directories()
        st.title(f"🎓 Student Dashboard - {course_name}")

        if "student_identity" not in st.session_state:
            st.session_state.student_identity = {"name": "", "matric": ""}

        student_name = st.session_state.student_identity["name"]
        student_matric = st.session_state.student_identity["matric"]

        st.subheader("👤 Student Identity")
        with st.form("student_identity_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Full Name", value=student_name, placeholder="Enter your full name")
            with col2:
                new_matric = st.text_input("Matric Number", value=student_matric, placeholder="Enter your matric number")
            save_identity = st.form_submit_button("💾 Save Identity", use_container_width=True)
            if save_identity:
                if new_name.strip() and new_matric.strip():
                    st.session_state.student_identity = {"name": new_name.strip(), "matric": new_matric.strip()}
                    student_name = new_name.strip()
                    student_matric = new_matric.strip()
                    st.success("✅ Identity saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Please enter both name and matric number.")

        if not student_name or not student_matric:
            st.warning("⚠️ Please set your identity above to continue.")
            return

        st.success(f"**Logged in as:** {student_name} ({student_matric})")

        st.sidebar.header("📅 Week Navigation")
        selected_week = st.sidebar.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)], key="student_main_week_selector")

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "📝 About Course", "📖 Lecture & Classwork", "🎥 Video Lectures",
            "🕒 Attendance", "📤 Submissions", "📢 Announcements",
            "📝 Seminar Feedback", "📊 My Progress"
        ])

        with tab1:
            show_student_course_description(course_code, course_name)

        with tab2:
            st.header(f"📚 {course_code} - {selected_week}")
            display_weekly_lecture_materials(course_code, selected_week, student_name, student_matric)
            display_classwork_section(course_code, selected_week, student_name, student_matric)

        with tab3:
            st.header("🎥 Video Lectures")
            video_files = get_video_files(course_code)
            if video_files:
                st.success(f"Found {len(video_files)} video lecture(s) available!")
                for i, video in enumerate(video_files):
                    video_path = get_persistent_path("video", course_code, video)
                    with st.expander(f"🎬 {video}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            try:
                                st.video(video_path, start_time=0)
                                file_size = os.path.getsize(video_path) / (1024 * 1024)
                                st.caption(f"File size: {file_size:.2f} MB")
                            except Exception as e:
                                st.error(f"Cannot play this video: {str(e)}")
                        with col2:
                            try:
                                with open(video_path, "rb") as vid_file:
                                    st.download_button("📥 Download Video", data=vid_file,
                                                       file_name=video, mime="video/mp4",
                                                       key=f"student_download_{i}",
                                                       use_container_width=True)
                            except Exception as e:
                                st.error("Download unavailable")
            else:
                st.info("No video lectures available yet.")

        with tab4:
            st.header("🕒 Mark Attendance")
            with st.form(f"{course_code}_attendance_form"):
                name = st.text_input("Full Name", value=student_name, key=f"{course_code}_student_name")
                matric = st.text_input("Matric Number", value=student_matric, key=f"{course_code}_student_matric")
                st.write(f"**Selected Week:** {selected_week}")
                submit_attendance = st.form_submit_button("✅ Mark Attendance", use_container_width=True)
            if submit_attendance:
                if not name.strip() or not matric.strip():
                    st.warning("Please enter your full name and matric number.")
                else:
                    st.session_state.student_identity = {"name": name.strip(), "matric": matric.strip()}
                    student_name = name.strip()
                    student_matric = matric.strip()
                    status_data = get_attendance_status(course_code, selected_week)
                    if not status_data.get("is_open", False):
                        st.error("🚫 Attendance for this course is currently closed.")
                    elif has_marked_attendance(course_code, selected_week, student_name, student_matric):
                        st.info("✅ Attendance already marked for this week.")
                    else:
                        if mark_attendance_entry(course_code, student_name, student_matric, selected_week):
                            st.success(f"🎉 Attendance recorded for {course_code} - {selected_week}.")
                            st.balloons()
                        else:
                            st.error("⚠️ Failed to record attendance.")

        with tab5:
            # ===============================================================
            # FIX #3 & #14: FIXED INDENTATION - All submission logic is now
            # properly inside the `if submit_*:` block so files are only
            # saved when the button is actually clicked, not on every re-render
            # ===============================================================
            st.header("📤 Submit Assignments")

            # --- Assignment Submission ---
            st.subheader("📝 Assignment Submission")
            with st.form("assignment_upload_form"):
                st.write(f"**Selected Week:** {selected_week}")
                assignment_file = st.file_uploader("Upload Assignment File",
                                                   type=["pdf", "doc", "docx", "txt", "zip"],
                                                   key="assignment_upload")
                submit_assignment = st.form_submit_button("📤 Submit Assignment", use_container_width=True)

            # All submission logic OUTSIDE the form widget but INSIDE the if-block
            if submit_assignment:
                if not assignment_file:
                    st.error("❌ Please select a file to upload.")
                else:
                    has_submission, existing_data = check_existing_submission(
                        course_code, selected_week, student_matric)
                    if has_submission:
                        st.error("❌ Submission already exists! You cannot submit twice.")
                    else:
                        file_path = save_file(course_code, student_name, selected_week, assignment_file, "assignment")
                        if file_path:
                            log_submission(course_code, student_matric, student_name,
                                           selected_week, assignment_file.name, "assignment")
                            st.success(f"✅ Assignment submitted successfully: {assignment_file.name}")

            # --- Drawing Submission ---
            st.subheader("🎨 Drawing Submission")
            with st.form("drawing_upload_form"):
                st.write(f"**Selected Week:** {selected_week}")
                drawing_file = st.file_uploader("Upload Drawing File",
                                                type=["jpg", "jpeg", "png", "gif", "pdf"],
                                                key="drawing_upload")
                submit_drawing = st.form_submit_button("📤 Submit Drawing", use_container_width=True)

            if submit_drawing:
                if not drawing_file:
                    st.error("❌ Please select a file to upload.")
                else:
                    has_submission, existing_data = check_existing_submission(
                        course_code, selected_week, student_matric)
                    if has_submission:
                        st.error("❌ Submission already exists! You cannot submit twice.")
                    else:
                        file_path = save_file(course_code, student_name, selected_week, drawing_file, "drawing")
                        if file_path:
                            log_submission(course_code, student_matric, student_name,
                                           selected_week, drawing_file.name, "drawing")
                            st.success(f"✅ Drawing submitted successfully: {drawing_file.name}")

            # --- Seminar Submission ---
            st.subheader("📊 Seminar Submission")
            with st.form("seminar_upload_form"):
                st.write("**Note:** Seminar submission is once per semester")
                seminar_file = st.file_uploader("Upload Seminar File",
                                                type=["pdf", "ppt", "pptx", "doc", "docx"],
                                                key="seminar_upload")
                seminar_topic = st.text_input("Enter your seminar topic:")
                submit_seminar = st.form_submit_button("📤 Submit Seminar", use_container_width=True)

            if submit_seminar:
                if not seminar_file:
                    st.error("❌ Please select a file to upload.")
                elif not seminar_topic:
                    st.error("❌ Please enter your seminar topic.")
                else:
                    has_submission, existing_data = check_existing_seminar_submission(course_code, student_matric)
                    if has_submission:
                        st.error("❌ Seminar already submitted! You can only submit once per semester.")
                    else:
                        file_path = save_seminar_file(course_code, student_name, student_matric, seminar_file)
                        if file_path:
                            log_seminar_submission(course_code, student_matric, student_name,
                                                   seminar_topic, seminar_file.name)
                            st.success(f"✅ Seminar submitted successfully: {seminar_file.name}")

        with tab6:
            display_pdf_announcements_student(course_code)

        with tab7:
            st.subheader("📥 Seminar Feedback")
            feedback = get_seminar_feedback(student_matric, course_code)
            if feedback:
                st.success("You have feedback for your seminar!")
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("**Instructor Feedback:**")
                    if isinstance(feedback, str) and feedback != "Feedback file provided":
                        st.info(feedback)
                    else:
                        st.info("Check the downloaded feedback file for detailed comments")
                with col2:
                    # FIX #6: Use the now-defined get_seminar_feedback_file_path()
                    feedback_file_path = get_seminar_feedback_file_path(student_matric, course_code)
                    if feedback_file_path and os.path.exists(feedback_file_path):
                        with open(feedback_file_path, "rb") as file:
                            st.download_button("📥 Download Feedback PDF", data=file,
                                               file_name="Seminar_Feedback.pdf", mime="application/pdf")
            else:
                st.info("No feedback available for your seminar yet")

        with tab8:
            st.header("📊 My Scores & Grades")
            student_scores = load_student_scores(course_code, student_name, student_matric)
            if not student_scores.empty:
                st.subheader("📋 Weekly Scores")
                display_columns = ["Week", "Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"]
                available_columns = [col for col in display_columns if col in student_scores.columns]
                st.dataframe(student_scores[available_columns], use_container_width=True)
                st.subheader("🎓 Final Grade Calculation")
                result = calculate_final_grade(student_scores)
                if result[0] is not None:
                    final_total, final_grade, assignment_avg, test_avg, practical_avg, classwork_avg, exam_score = result
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📝 Assignment Average", f"{assignment_avg:.1f}%")
                        st.metric("📊 Test Average", f"{test_avg:.1f}%")
                        st.metric("🔬 Practical Average", f"{practical_avg:.1f}%")
                        st.metric("🧩 Classwork Average", f"{classwork_avg:.1f}%")
                    with col2:
                        st.metric("📚 Exam Score", f"{exam_score:.1f}%")
                        ca_total = assignment_avg*0.08 + test_avg*0.08 + practical_avg*0.05 + classwork_avg*0.09
                        st.metric("📈 CA Contribution (30%)", f"{ca_total:.1f}%")
                        st.metric("🎯 Exam Contribution (70%)", f"{exam_score*0.70:.1f}%")
                    st.success(f"## 🎉 Final Grade: {final_total:.1f}% - {final_grade}")
                else:
                    st.info("📊 Complete your 15 weeks + exam to see your final grade.")
            else:
                st.info("📊 No scores recorded yet.")

            st.header("📈 My Activity Summary")
            activity_summary = get_student_activity_summary(course_code, student_name, student_matric)
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Weeks Attended", activity_summary["attendance_count"])
            with col2:
                st.metric("Classwork Submitted", activity_summary["classwork_count"])
            with col3:
                st.metric("Assignments", activity_summary["assignment_count"])
            with col4:
                st.metric("Drawings", activity_summary["drawing_count"])
            with col5:
                st.metric("Seminars", activity_summary["seminar_count"])
            if activity_summary["recent_activity"]:
                st.subheader("🕒 Recent Activity")
                for activity in activity_summary["recent_activity"][-5:]:
                    st.write(f"• {activity}")

        st.markdown("---")
        st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    except Exception as e:
        st.error(f"An error occurred in the student dashboard: {str(e)}")
        st.info("Please refresh the page and try again.")

# ===============================================================
# 👩‍🏫 ADMIN VIEW
# ===============================================================

def admin_view(course_code, course_name):
    """Admin dashboard view"""
    try:
        st.subheader(f"🔐 Admin Access - {course_name}")
        password = st.text_input("Enter Admin Password", type="password", key=f"admin_password_{course_code}")
        if not password:
            st.warning(f"Enter the admin password for {course_name} to continue.")
            return
        if not verify_admin_password(course_code, password):
            st.error("❌ Incorrect password. Please try again.")
            return

        st.session_state["role"] = "Admin"
        st.session_state["current_course"] = course_code
        st.success(f"✅ Logged in as Admin - {course_name}")
        ensure_directories()
        st.title(f"👩‍🏫 {course_name} Admin Dashboard")

        with st.expander("🔐 Password Management", expanded=False):
            st.subheader("Change Course Password")
            current_password = get_course_password(course_code)
            st.info(f"Current password: **{current_password}**")
            col1, col2 = st.columns(2)
            with col1:
                new_password = st.text_input("New Password", type="password", key=f"new_pass_admin_{course_code}")
            with col2:
                confirm_password = st.text_input("Confirm Password", type="password", key=f"confirm_pass_admin_{course_code}")
            if st.button("🔄 Change Password", type="primary", key=f"change_pass_btn_{course_code}"):
                if new_password and confirm_password:
                    if new_password == confirm_password:
                        if set_course_password(course_code, new_password):
                            st.success("✅ Password changed successfully!")
                            st.rerun()
                    else:
                        st.error("❌ Passwords don't match!")
                else:
                    st.error("❌ Please enter and confirm new password!")

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
            "📚 Course Manager", "📖 Lecture Management", "🎥 Video Management",
            "🕒 Attendance Control", "📊 Attendance Records", "🧩 Classwork Control",
            "📝 MCQ Management", "📝 Classwork Submissions", "📝 Grading System",
            "📂 Student Submissions", "📢 Announcements", "📊 Seminar Submissions"
        ])

        with tab1:
            show_course_manager(course_code, course_name)

        with tab2:
            st.header("📖 Lecture Management")
            lectures_df = load_lectures(course_code)
            st.session_state["lectures_df"] = lectures_df
            st.subheader("📘 Add / Edit Lecture Materials & Assignment")
            week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)], key="lecture_week_select")

            if week in lectures_df["Week"].values:
                row_idx = lectures_df[lectures_df["Week"] == week].index[0]
            else:
                new_row = {"Week": week, "Topic": "", "Brief": "", "Assignment": "", "PDF_File": ""}
                lectures_df = pd.concat([lectures_df, pd.DataFrame([new_row])], ignore_index=True)
                row_idx = lectures_df[lectures_df["Week"] == week].index[0]
                st.session_state["lectures_df"] = lectures_df

            topic = st.text_input("Topic", value=lectures_df.at[row_idx, "Topic"], key=f"topic_{week}")
            brief = st.text_area("Brief Description", value=lectures_df.at[row_idx, "Brief"], key=f"brief_{week}")
            assignment = st.text_area("Assignment", value=lectures_df.at[row_idx, "Assignment"], key=f"assignment_{week}")

            st.markdown("**Upload PDF Files (Permanent Storage)**")
            pdf_dir = get_persistent_path("pdf", course_code)
            os.makedirs(pdf_dir, exist_ok=True)
            lecture_pdf = st.file_uploader("Lecture PDF", type=["pdf"], key=f"pdf_{week}")

            current_pdf = str(lectures_df.at[row_idx, "PDF_File"] or "").strip()
            if current_pdf and os.path.exists(current_pdf):
                st.success(f"📎 Current PDF: {os.path.basename(current_pdf)}")
                with open(current_pdf, "rb") as pdf_file:
                    file_size = os.path.getsize(current_pdf) / (1024 * 1024)
                    st.download_button(f"📥 Download Current PDF ({file_size:.1f}MB)", data=pdf_file,
                                       file_name=os.path.basename(current_pdf),
                                       mime="application/pdf", key=f"download_{week}")
                if st.button("🗑️ Remove PDF", key=f"remove_{week}"):
                    try:
                        if os.path.exists(current_pdf):
                            os.remove(current_pdf)
                        lectures_df.at[row_idx, "PDF_File"] = ""
                        st.session_state["lectures_df"] = lectures_df
                        lectures_df.to_csv(get_file(course_code, "lectures"), index=False)
                        st.success("✅ PDF removed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error removing PDF: {e}")

            if lecture_pdf is not None:
                safe_name = "".join(c for c in lecture_pdf.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip().replace(' ', '_')
                pdf_filename = f"{course_code}_{week.replace(' ', '')}_{safe_name}"
                pdf_path = get_persistent_path("pdf", course_code, pdf_filename)
                try:
                    with st.spinner("Uploading PDF to permanent storage..."):
                        with open(pdf_path, "wb") as f:
                            f.write(lecture_pdf.getbuffer())
                    lectures_df.at[row_idx, "PDF_File"] = pdf_path
                    st.session_state["lectures_df"] = lectures_df
                    lectures_df.to_csv(get_file(course_code, "lectures"), index=False)
                    st.success(f"✅ PDF uploaded successfully: {lecture_pdf.name}")
                except Exception as e:
                    st.error(f"Error saving PDF: {str(e)}")

            # Bulk MCQ Import
            st.markdown("---")
            st.subheader("🧩 Automated MCQ Questions")
            existing_questions = load_mcq_questions(course_code, week) or []

            st.markdown("#### 📥 Bulk Import Questions")
            with st.expander("Click to expand bulk import"):
                st.markdown("""
                **MCQ format:**
                ```
                MCQ: Question text?
                A. Option 1
                B. Option 2
                C. Option 3
                D. Option 4
                Correct: A
                ```
                **GAP format:**
                ```
                GAP: The answer is ________.
                Correct: answer|alternative
                ```
                """)
                bulk_text = st.text_area("Paste your questions here:", height=300,
                                         placeholder="Paste multiple questions in the format shown above...",
                                         key=f"bulk_import_{week}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("📥 Import Questions", key=f"import_{week}"):
                        if bulk_text.strip():
                            new_questions = parse_bulk_questions(bulk_text)
                            if new_questions:
                                existing_questions.extend(new_questions)
                                if save_mcq_questions(course_code, week, existing_questions):
                                    st.success(f"✅ Imported {len(new_questions)} questions!")
                                    st.rerun()
                            else:
                                st.error("❌ No valid questions found. Check the format.")
                        else:
                            st.warning("⚠️ Please paste some questions first.")

            # MCQ Creation Form
            st.markdown("#### Create New Question")
            with st.form(f"mcq_creation_form_{week}"):
                question_type = st.selectbox("Question Type", ["Multiple Choice (MCQ)", "Gap Filling"], key=f"question_type_{week}")
                question_text = st.text_area("Question Text", placeholder="Enter your question here...", key=f"question_text_{week}")
                if question_type == "Multiple Choice (MCQ)":
                    col1, col2 = st.columns(2)
                    with col1:
                        option_a = st.text_input("Option A", key=f"option_a_{week}")
                        option_b = st.text_input("Option B", key=f"option_b_{week}")
                        option_e = st.text_input("Option E", key=f"option_e_{week}")
                    with col2:
                        option_c = st.text_input("Option C", key=f"option_c_{week}")
                        option_d = st.text_input("Option D", key=f"option_d_{week}")
                    correct_answer = st.selectbox("Correct Answer", ["A", "B", "C", "D", "E"], key=f"correct_answer_{week}")
                    options = {"A": option_a, "B": option_b, "C": option_c, "D": option_d, "E": option_e}
                else:
                    correct_answer = st.text_input("Correct Answer(s)", placeholder="Use | for multiple answers",
                                                   key=f"gap_answer_{week}")
                    options = {}
                add_question = st.form_submit_button("➕ Add Question")
                if add_question and question_text:
                    new_question = {
                        "type": "mcq" if question_type == "Multiple Choice (MCQ)" else "gap_fill",
                        "question": question_text,
                        "options": options,
                        "correct_answer": correct_answer
                    }
                    existing_questions.append(new_question)
                    if save_mcq_questions(course_code, week, existing_questions):
                        st.success("✅ Question added!")
                        st.rerun()

            # Display existing questions
            if existing_questions:
                st.write(f"**Existing Questions for {week}:**")
                for i, question in enumerate(existing_questions):
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Q{i+1}:** {question['question']}")
                            st.write(f"*Type:* {question['type'].replace('_', ' ').title()}")
                            if question['type'] == 'mcq':
                                for opt, text in question['options'].items():
                                    st.write(f"  {opt}: {text}")
                            st.write(f"*Correct:* {question['correct_answer']}")
                            st.markdown("---")
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_q_{week}_{i}"):
                                existing_questions.pop(i)
                                save_mcq_questions(course_code, week, existing_questions)
                                st.success("✅ Question deleted!")
                                st.rerun()
                if st.button("🚨 Clear All Questions", key=f"clear_all_{week}", type="secondary"):
                    if save_mcq_questions(course_code, week, []):
                        st.success("✅ All questions cleared!")
                        st.rerun()
            else:
                st.info("No MCQ questions added for this week yet.")

            st.markdown("---")
            if st.button("💾 SAVE ALL LECTURE MATERIALS", key=f"save_all_{week}", type="primary", use_container_width=True):
                try:
                    lectures_df.at[row_idx, "Topic"] = topic
                    lectures_df.at[row_idx, "Brief"] = brief
                    lectures_df.at[row_idx, "Assignment"] = assignment
                    lectures_df.to_csv(get_file(course_code, "lectures"), index=False)
                    st.session_state["lectures_df"] = lectures_df
                    st.success("🎉 All lecture materials saved!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")

        with tab3:
            st.header("🎥 Video Lecture Management")
            uploaded_video = st.file_uploader("Upload Lecture Video (MP4 recommended, max 200MB)",
                                              type=["mp4", "mov", "avi", "mkv"],
                                              key=f"{course_code}_video_upload")
            if uploaded_video is not None:
                file_size = uploaded_video.size / (1024 * 1024)
                st.write(f"**File:** {uploaded_video.name}")
                st.write(f"**Size:** {file_size:.2f} MB")
                if file_size > 200:
                    st.error("❌ File too large! Please upload videos under 200MB.")
                else:
                    success, message = upload_video(course_code, uploaded_video)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            st.subheader("📚 Video Library")
            video_files = get_video_files(course_code)
            if video_files:
                for i, video in enumerate(video_files):
                    video_path = get_persistent_path("video", course_code, video)
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**🎬 {video}**")
                            try:
                                st.video(video_path, start_time=0)
                                file_size = os.path.getsize(video_path) / (1024 * 1024)
                                st.caption(f"Size: {file_size:.2f} MB")
                            except Exception as e:
                                st.error(f"Cannot preview: {str(e)}")
                        with col2:
                            try:
                                with open(video_path, "rb") as vid_file:
                                    st.download_button("📥 Download", data=vid_file,
                                                       file_name=video, mime="video/mp4",
                                                       key=f"download_video_{i}")
                            except Exception as e:
                                st.error(f"Download unavailable")
                            if st.button("🗑️ Delete", key=f"delete_video_{i}"):
                                try:
                                    os.remove(video_path)
                                    st.success(f"✅ Video deleted: {video}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Failed to delete: {str(e)}")
                        st.markdown("---")
            else:
                st.info("No videos in storage yet.")

        with tab4:
            st.header("🎛 Attendance Control")
            selected_week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)],
                                         key=f"{course_code}_attendance_week_select")
            current_status = get_attendance_status(course_code, selected_week)
            is_currently_open = current_status.get("is_open", False)
            if is_currently_open:
                st.success(f"✅ Attendance is CURRENTLY OPEN for {course_code} - {selected_week}")
            else:
                st.warning(f"🚫 Attendance is CURRENTLY CLOSED for {course_code} - {selected_week}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔓 OPEN Attendance", use_container_width=True, type="primary", key="open_attendance_btn"):
                    if set_attendance_status(course_code, selected_week, True, datetime.now()):
                        st.success(f"✅ Attendance OPENED for {course_code} - {selected_week}")
                        st.rerun()
            with col2:
                if st.button("🔒 CLOSE Attendance", use_container_width=True, type="secondary", key="close_attendance_btn"):
                    if set_attendance_status(course_code, selected_week, False):
                        st.warning(f"🚫 Attendance CLOSED for {course_code} - {selected_week}")
                        st.rerun()
            if is_currently_open and current_status.get("open_time"):
                try:
                    open_time = datetime.fromisoformat(current_status["open_time"])
                    remaining = max(0, 600 - (datetime.now() - open_time).total_seconds())
                    if remaining <= 0:
                        set_attendance_status(course_code, selected_week, False)
                        st.error("⏰ Attendance has automatically closed after 10 minutes.")
                        st.rerun()
                    else:
                        st.info(f"⏳ Auto-closes in {int(remaining//60):02d}:{int(remaining%60):02d}")
                except Exception as e:
                    st.error(f"Error in auto-close: {e}")

        with tab5:
            st.header("📊 Attendance Records")
            att_tab1, att_tab2, att_tab3 = st.tabs(["👥 Student Details", "📈 Weekly Summary", "📋 Complete History"])
            with att_tab1:
                view_week = st.selectbox("Select Week to View", [f"Week {i}" for i in range(1, 16)],
                                         key=f"{course_code}_attendance_view_week")
                view_student_attendance_details(course_code, view_week)
            with att_tab2:
                show_attendance_summary(course_code)
            with att_tab3:
                view_all_students_attendance(course_code)
            st.header("🌐 Global Attendance Overview")
            if st.button("🔄 Refresh Global Overview", type="secondary", key="refresh_global_attendance"):
                global_df = get_global_attendance_summary()
                if not global_df.empty:
                    st.dataframe(global_df, use_container_width=True)
                    st.metric("Total Attendance Across All Courses", global_df["Total Attendance Records"].sum())
                else:
                    st.info("No attendance data found.")

        with tab6:
            st.header("🎛 Classwork Control")
            classwork_week = st.selectbox("Select Week for Classwork", [f"Week {i}" for i in range(1, 16)],
                                          key=f"{course_code}_classwork_control_week")
            current_classwork_status = get_classwork_status(course_code, classwork_week)
            is_classwork_currently_open = current_classwork_status.get("is_open", False)
            answers_released = current_classwork_status.get("answers_released", False)
            col1, col2, col3 = st.columns(3)
            with col1:
                if is_classwork_currently_open:
                    st.success("✅ Classwork OPEN")
                else:
                    st.warning("🚫 Classwork CLOSED")
            with col2:
                if answers_released:
                    st.success("📚 Answers RELEASED")
                else:
                    st.info("🔒 Answers HIDDEN")
            with col3:
                if is_classwork_currently_open or answers_released:
                    st.success("👀 Visible to Students")
                else:
                    st.error("🙈 Hidden from Students")
            st.subheader("Control Classwork Visibility")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔓 OPEN Classwork", use_container_width=True, type="primary", key="open_classwork_btn"):
                    if set_classwork_status(course_code, classwork_week, True, datetime.now()):
                        st.success(f"✅ Classwork OPENED for {course_code} - {classwork_week}")
                        st.rerun()
            with col2:
                if st.button("🔒 CLOSE Classwork", use_container_width=True, type="secondary", key="close_classwork_btn"):
                    if set_classwork_status(course_code, classwork_week, False):
                        st.warning(f"🚫 Classwork CLOSED for {course_code} - {classwork_week}")
                        st.rerun()
            st.subheader("Control Answer Visibility")
            col3, col4 = st.columns(2)
            with col3:
                if st.button("📚 RELEASE Answers", use_container_width=True, type="primary", key="release_answers_btn"):
                    if set_classwork_answers_released(course_code, classwork_week, True):
                        st.success(f"✅ Answers RELEASED for {course_code} - {classwork_week}")
                        st.rerun()
            with col4:
                if st.button("🔒 HIDE Answers", use_container_width=True, type="secondary", key="hide_answers_btn"):
                    if set_classwork_answers_released(course_code, classwork_week, False):
                        st.warning(f"🔒 Answers HIDDEN for {course_code} - {classwork_week}")
                        st.rerun()
            if is_classwork_currently_open and current_classwork_status.get("open_time"):
                try:
                    open_time = datetime.fromisoformat(current_classwork_status["open_time"])
                    remaining = max(0, 1200 - (datetime.now() - open_time).total_seconds())
                    if remaining <= 0:
                        set_classwork_status(course_code, classwork_week, False)
                        st.error("⏰ Classwork has automatically closed after 20 minutes.")
                        st.rerun()
                    else:
                        st.info(f"⏳ Auto-closes in {int(remaining//60):02d}:{int(remaining%60):02d}")
                except Exception as e:
                    st.error(f"Error in classwork auto-close: {e}")

        with tab7:
            st.header("🧩 Automated MCQ & Gap-Filling Management")
            mcq_week = st.selectbox("Select Week for MCQ", [f"Week {i}" for i in range(1, 16)], key="mcq_management_week")
            existing_questions_main = load_mcq_questions(course_code, mcq_week) or []
            st.subheader("📝 Create Automated Questions")
            with st.form("mcq_creation_form_main"):
                question_type = st.selectbox("Question Type", ["Multiple Choice (MCQ)", "Gap Filling"], key="question_type_main")
                question_text = st.text_area("Question Text", placeholder="Enter your question here...", key="question_text_main")
                if question_type == "Multiple Choice (MCQ)":
                    col1, col2 = st.columns(2)
                    with col1:
                        option_a = st.text_input("Option A", key="option_a_main")
                        option_b = st.text_input("Option B", key="option_b_main")
                        option_e = st.text_input("Option E", key="option_e_main")
                    with col2:
                        option_c = st.text_input("Option C", key="option_c_main")
                        option_d = st.text_input("Option D", key="option_d_main")
                    correct_answer = st.selectbox("Correct Answer", ["A", "B", "C", "D", "E"], key="correct_answer_main")
                    options = {"A": option_a, "B": option_b, "C": option_c, "D": option_d, "E": option_e}
                else:
                    correct_answer = st.text_input("Correct Answer(s)",
                                                   placeholder="Use | for multiple acceptable answers",
                                                   key="gap_answer_main")
                    options = {}
                add_question = st.form_submit_button("➕ Add Question")
                if add_question and question_text:
                    new_question = {
                        "type": "mcq" if question_type == "Multiple Choice (MCQ)" else "gap_fill",
                        "question": question_text,
                        "options": options,
                        "correct_answer": correct_answer
                    }
                    existing_questions_main.append(new_question)
                    if save_mcq_questions(course_code, mcq_week, existing_questions_main):
                        st.success("✅ Question added!")
                        st.rerun()
            if existing_questions_main:
                st.subheader("📋 Existing Questions")
                for i, question in enumerate(existing_questions_main):
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Q{i+1}:** {question['question']}")
                            st.write(f"*Type:* {question['type'].replace('_', ' ').title()}")
                            if question['type'] == 'mcq':
                                for opt, text in question['options'].items():
                                    st.write(f"  {opt}: {text}")
                            st.write(f"*Correct:* {question['correct_answer']}")
                            st.markdown("---")
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_question_{i}"):
                                existing_questions_main.pop(i)
                                save_mcq_questions(course_code, mcq_week, existing_questions_main)
                                st.success("✅ Question deleted!")
                                st.rerun()
                if st.button("🚨 Clear All Questions", type="secondary", key="clear_all_questions"):
                    if save_mcq_questions(course_code, mcq_week, []):
                        st.success("✅ All questions cleared!")
                        st.rerun()
            else:
                st.info("No questions added yet.")

        with tab8:
            st.header("📝 Classwork Submissions")
            cw_tab1, cw_tab2 = st.tabs(["📅 Weekly Submissions", "📚 All Submissions"])
            with cw_tab1:
                cw_week = st.selectbox("Select Week to View", [f"Week {i}" for i in range(1, 16)],
                                       key=f"{course_code}_classwork_view_week")
                view_classwork_submissions(course_code, cw_week)
            with cw_tab2:
                classwork_file = get_file(course_code, "classwork")
                if os.path.exists(classwork_file):
                    df = pd.read_csv(classwork_file)
                    if not df.empty:
                        st.dataframe(df, use_container_width=True)
                        st.download_button("📥 Download All Classwork", df.to_csv(index=False),
                                           f"classwork_{course_code}_all.csv", "text/csv")
                    else:
                        st.info("No classwork submissions yet.")
                else:
                    st.info("No classwork submissions yet.")

        with tab9:
            st.header("📝 Grading System")
            st.info("""
            **Grading Weights (After 15 Weeks + Exam):**
            - Assignment & Seminar: 8% (average of 15 weeks)
            - Test: 8% (average of 15 weeks)
            - Practical: 5% (average of 15 weeks)
            - Classwork: 9% (average of 15 weeks)
            - Exam (After 15 weeks): 70%
            """)
            scores_df = ensure_scores_file(course_code)
            scores_file = get_file(course_code, "scores")
            st.subheader("📋 Manual Grade Entry")
            with st.form("manual_grading_form"):
                col1, col2 = st.columns(2)
                with col1:
                    g_student_name = st.text_input("Student Name", key="grade_name")
                    g_week = st.selectbox("Week", [f"Week {i}" for i in range(1, 16)] + ["Exam"], key="grade_week")
                    g_assignment = st.number_input("Assignment Score (0-100)", 0, 100, 0, key="assignment_score")
                    g_test = st.number_input("Test Score (0-100)", 0, 100, 0, key="test_score")
                with col2:
                    g_matric = st.text_input("Matric Number", key="grade_matric")
                    g_practical = st.number_input("Practical Score (0-100)", 0, 100, 0, key="practical_score")
                    g_exam = st.number_input("Exam Score (0-100)", 0, 100, 0, key="exam_score")
                    g_classwork = st.number_input("Classwork Score (0-100)", 0, 100, 0, key="classwork_score")
                submit_grade = st.form_submit_button("💾 Save Grade", use_container_width=True)
                if submit_grade:
                    if not g_student_name or not g_matric:
                        st.error("Please enter student name and matric number.")
                    else:
                        if g_week != "Exam":
                            weekly_total = round(g_assignment*0.08 + g_test*0.08 + g_practical*0.05 + g_classwork*0.09, 1)
                            weekly_grade = compute_grade(weekly_total)
                        else:
                            weekly_total = 0
                            weekly_grade = ""
                        current_df = pd.read_csv(scores_file)
                        mask = (
                            (current_df["StudentName"].astype(str).str.lower() == g_student_name.lower()) &
                            (current_df["MatricNo"].astype(str).str.lower() == g_matric.lower()) &
                            (current_df["Week"].astype(str).str.lower() == g_week.lower())
                        )
                        if mask.any():
                            current_df.loc[mask, ["Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"]] = [
                                g_assignment, g_test, g_practical, g_exam, g_classwork, weekly_total, weekly_grade]
                        else:
                            new_row = {
                                "StudentName": g_student_name.title(), "MatricNo": g_matric.upper(),
                                "Week": g_week, "Assignment": g_assignment, "Test": g_test,
                                "Practical": g_practical, "Exam": g_exam, "Classwork": g_classwork,
                                "Total": weekly_total, "Grade": weekly_grade
                            }
                            current_df = pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True)
                        current_df.to_csv(scores_file, index=False)
                        st.success(f"✅ Grade saved for {g_student_name} ({g_matric}) - {g_week}")

            # CSV Upload
            st.subheader("📁 Bulk Grade Upload (CSV)")
            uploaded_csv = st.file_uploader(
                "Upload CSV with columns: StudentName, MatricNo, Week, Assignment, Test, Practical, Exam, Classwork",
                type=["csv"], key="grade_csv_upload")
            if uploaded_csv is not None:
                try:
                    uploaded_df = pd.read_csv(uploaded_csv)
                    required_cols = ["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Classwork"]
                    if all(col in uploaded_df.columns for col in required_cols):
                        def calc_row_total(row):
                            if row['Week'] != 'Exam':
                                return round(row['Assignment']*0.08 + row['Test']*0.08 + row['Practical']*0.05 + row['Classwork']*0.09, 1)
                            return 0
                        uploaded_df["Total"] = uploaded_df.apply(calc_row_total, axis=1)
                        uploaded_df["Grade"] = uploaded_df["Total"].apply(compute_grade)
                        existing_df = pd.read_csv(scores_file) if os.path.exists(scores_file) else pd.DataFrame(columns=required_cols + ["Total", "Grade"])
                        for _, row in uploaded_df.iterrows():
                            mask = (
                                (existing_df["StudentName"].astype(str).str.lower() == str(row["StudentName"]).lower()) &
                                (existing_df["MatricNo"].astype(str).str.lower() == str(row["MatricNo"]).lower()) &
                                (existing_df["Week"].astype(str).str.lower() == str(row["Week"]).lower())
                            )
                            if mask.any():
                                existing_df.loc[mask, ["Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"]] = [
                                    row["Assignment"], row["Test"], row["Practical"], row["Exam"], row["Classwork"], row["Total"], row["Grade"]]
                            else:
                                existing_df = pd.concat([existing_df, pd.DataFrame([row])], ignore_index=True)
                        existing_df.to_csv(scores_file, index=False)
                        st.success(f"✅ Processed {len(uploaded_df)} grade records!")
                        st.dataframe(existing_df, use_container_width=True)
                    else:
                        missing = [col for col in required_cols if col not in uploaded_df.columns]
                        st.error(f"❌ CSV missing columns: {', '.join(missing)}")
                except Exception as e:
                    st.error(f"❌ Error processing CSV: {e}")

            # Display grades
            st.subheader("📊 Current Grades & Final Calculations")
            if os.path.exists(scores_file):
                try:
                    scores_df = pd.read_csv(scores_file)
                    if not scores_df.empty:
                        st.dataframe(scores_df, use_container_width=True)
                        st.subheader("🎓 Final Grade Calculations")
                        students = scores_df[['StudentName', 'MatricNo']].drop_duplicates()
                        final_grades_data = []
                        for _, student in students.iterrows():
                            s_name = student['StudentName']
                            s_matric = student['MatricNo']
                            s_scores = scores_df[(scores_df['StudentName'] == s_name) & (scores_df['MatricNo'] == s_matric)]
                            result = calculate_final_grade(s_scores)
                            if result[0] is not None:
                                ft, fg, aa, ta, pa, ca, es = result
                                final_grades_data.append({
                                    'StudentName': s_name, 'MatricNo': s_matric,
                                    'CA_Assignment_Avg': round(aa, 1), 'CA_Test_Avg': round(ta, 1),
                                    'CA_Practical_Avg': round(pa, 1), 'CA_Classwork_Avg': round(ca, 1),
                                    'Exam_Score': es, 'Final_Total': ft, 'Final_Grade': fg
                                })
                        if final_grades_data:
                            final_df = pd.DataFrame(final_grades_data)
                            st.dataframe(final_df, use_container_width=True)
                            col1, col2 = st.columns(2)
                            with col1:
                                st.download_button("📥 Download All Scores", scores_df.to_csv(index=False),
                                                   f"{course_code}_all_scores.csv", "text/csv",
                                                   use_container_width=True, key="download_all_scores")
                            with col2:
                                st.download_button("📥 Download Final Grades", final_df.to_csv(index=False),
                                                   f"{course_code}_final_grades.csv", "text/csv",
                                                   use_container_width=True, key="download_final_grades")
                        else:
                            st.info("No complete data for final grade calculation.")
                    else:
                        st.info("No grades recorded yet.")
                except Exception as e:
                    st.error(f"Error loading grades: {e}")

        with tab10:
            st.header("📂 View Student Submissions")
            upload_types = ["assignment", "drawing", "seminar"]
            for upload_type in upload_types:
                st.subheader(f"📄 {upload_type.capitalize()} Submissions")
                upload_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, upload_type)
                if not os.path.exists(upload_dir):
                    st.info(f"No {upload_type} submissions yet.")
                    continue
                files = sorted([f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))])
                if not files:
                    st.info(f"No {upload_type} submissions yet.")
                    continue
                for file in files:
                    file_path = os.path.join(upload_dir, file)
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**📎 {file}**")
                            try:
                                file_size = os.path.getsize(file_path) / (1024 * 1024)
                                st.write(f"*Size:* {file_size:.2f} MB")
                                parts = file.split('_')
                                if len(parts) >= 2:
                                    st.write(f"*Student:* {parts[0]}")
                            except:
                                pass
                        with col2:
                            try:
                                with open(file_path, "rb") as fh:
                                    st.download_button("⬇️ Download", data=fh, file_name=file,
                                                       mime="application/octet-stream",
                                                       key=f"{course_code}_{upload_type}_{file}_download")
                            except Exception:
                                st.warning("⚠️ Cannot open file for download.")
                        st.markdown("---")

            st.subheader("📊 Submission Management")
            if 'student_list_data' not in st.session_state:
                st.session_state.student_list_data = None
            if 'student_list_filename' not in st.session_state:
                st.session_state.student_list_filename = None
            if st.button("📥 Generate Student List CSV"):
                csv_data, filename = get_student_list_csv(course_code)
                if csv_data:
                    st.session_state.student_list_data = csv_data
                    st.session_state.student_list_filename = filename
                    st.success("✅ Student list generated!")
                else:
                    st.warning("No student data available")
            if st.session_state.student_list_data:
                st.download_button("⬇️ Download Student List", data=st.session_state.student_list_data,
                                   file_name=st.session_state.student_list_filename, mime="text/csv")

            st.write("### Weekly Submissions")
            weeks = [f"Week {i}" for i in range(1, 16)]
            selected_week_dl = st.selectbox("Select Week for Download", weeks, key="weekly_download")
            if 'weekly_data' not in st.session_state:
                st.session_state.weekly_data = None
            if 'weekly_filename' not in st.session_state:
                st.session_state.weekly_filename = None
            if st.button("📥 Generate Weekly Submissions CSV"):
                csv_data, filename = get_weekly_submissions_csv(course_code, selected_week_dl)
                if csv_data:
                    st.session_state.weekly_data = csv_data
                    st.session_state.weekly_filename = filename
                    st.success(f"✅ {selected_week_dl} submissions generated!")
                else:
                    st.warning(f"No submissions found for {selected_week_dl}")
            if st.session_state.weekly_data:
                st.download_button(f"⬇️ Download {selected_week_dl} Submissions",
                                   data=st.session_state.weekly_data,
                                   file_name=st.session_state.weekly_filename, mime="text/csv")

        with tab11:
            display_pdf_announcements_admin(course_code)

        with tab12:
            st.subheader("📊 Seminar Submissions Management")
            # FIX #9: Use load_courses_config().values() instead of get_courses_file()
            all_courses = list(load_courses_config().values())
            admin_course = st.selectbox("Select Course", all_courses, key="seminar_course_admin")
            submissions = get_seminar_submissions(admin_course)
            if submissions:
                st.write(f"**Found {len(submissions)} seminar submissions**")
                for i, submission in enumerate(submissions):
                    with st.expander(f"📝 {submission['student_name']} - {submission['topic']}", expanded=False):
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"**Matric:** {submission['student_matric']}")
                            st.write(f"**Topic:** {submission['topic']}")
                            st.write(f"**File:** {submission['file_name']}")
                            st.write(f"**Submitted:** {submission['timestamp']}")
                            # FIX #7: Replaced undefined download_file() with proper st.download_button
                            file_path = submission.get('file_path', '')
                            if file_path and os.path.exists(file_path):
                                with open(file_path, "rb") as fh:
                                    st.download_button("📥 Download Submission", data=fh,
                                                       file_name=submission['file_name'],
                                                       mime="application/octet-stream",
                                                       key=f"download_seminar_{i}")
                            else:
                                st.info("File not available for download")
                        with col2:
                            st.write("**Current Feedback:**")
                            current_feedback = get_seminar_feedback(submission['student_matric'], admin_course)
                            if current_feedback:
                                st.info(current_feedback)
                            else:
                                st.write("No feedback yet")
                        with col3:
                            with st.form(key=f"seminar_feedback_form_{i}"):
                                feedback_file = st.file_uploader("Upload Feedback PDF", type=["pdf"],
                                                                  key=f"seminar_feedback_pdf_{i}")
                                feedback_text = st.text_area("Or write feedback:", key=f"seminar_feedback_text_{i}")
                                send_feedback = st.form_submit_button("📤 Send Feedback")
                                if send_feedback:
                                    if feedback_file or feedback_text:
                                        success = save_seminar_feedback(
                                            submission['student_matric'], admin_course,
                                            feedback_file, feedback_text)
                                        if success:
                                            st.success("✅ Feedback sent!")
                                        else:
                                            st.error("❌ Failed to send feedback")
                                    else:
                                        st.error("❌ Please provide feedback")
            else:
                st.info(f"No seminar submissions found for {admin_course}")

    except Exception as e:
        st.error(f"An error occurred in admin view: {str(e)}")

# ===============================================================
# 🚀 MAIN APPLICATION
# ===============================================================

def main():
    """Main application"""
    st.subheader("Multi-Course Learning Management System – Education Prism")
    st.title("🎓 Integrated Learning System")
    st_autorefresh(interval=86_400_000, key="daily_refresh")
    st.sidebar.title("🎓 Navigation")
    if "role" not in st.session_state:
        st.session_state["role"] = None
    role = st.sidebar.radio("Select Role", ["Select", "Student", "Admin", "System Admin"], key="role_selector")
    if role != "Select":
        st.session_state["role"] = role
    else:
        st.session_state["role"] = None

    COURSES = load_courses_config()

    if st.session_state["role"] == "System Admin":
        show_system_admin_dashboard()
    elif st.session_state["role"] == "Admin" and COURSES:
        course = st.sidebar.selectbox("Select Course:", list(COURSES.keys()))
        course_code = COURSES[course]
        admin_view(course_code, course)
    elif st.session_state["role"] == "Student" and COURSES:
        course = st.sidebar.selectbox("Select Course:", list(COURSES.keys()))
        course_code = COURSES[course]
        student_view(course_code, course)
    else:
        if not COURSES:
            st.warning("⚠️ No courses available. Please contact system administrator.")
        else:
            st.info("👆 Please select your role from the sidebar to continue.")

    st.markdown("""
        <style>
        .custom-footer {
            position: relative; left: 0; bottom: 0; width: 100%;
            background-color: #f0f2f6; color: #333; text-align: center;
            padding: 8px; font-size: 18px; font-weight: 500;
            border-top: 1px solid #ccc; margin-top: 2rem;
        }
        </style>
        <div class="custom-footer">
            Developed by <b>Adebimpe-John Omolola</b> | © 2025 | Advanced LMS with System Monitoring
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
