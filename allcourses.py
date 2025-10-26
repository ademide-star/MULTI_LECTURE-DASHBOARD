import streamlit as st
import pandas as pd
import sqlite3
import os
import re
import json
import base64
from datetime import datetime, date, timedelta, time
from streamlit_autorefresh import st_autorefresh

# ===============================================================
# 🎯 PAGE CONFIGURATION - MUST BE FIRST STREAMLIT COMMAND
# ===============================================================

st.set_page_config(
    page_title="Multi-Course Dashboard", 
    page_icon="📚", 
    layout="wide"
)

# ===============================================================
# 🎨 CUSTOM STYLING - HIDE STREAMLIT ELEMENTS
# ===============================================================

st.markdown(
    """
    <style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Desktop: mimic wide layout */
    @media (min-width: 900px) {
        .block-container {
            max-width: 95% !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
        }
    }

    /* Mobile: make sure expanders are fully visible */
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
    
    /* MCQ Styling */
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
DEFAULT_ADMIN_PASSWORD = "bimpe2025class"  # Universal default password

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
        os.path.join(PERSISTENT_DATA_DIR, "course_management")  # New directory for course management
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    return True

# Initialize directories
ensure_directories()

        
# ===============================================================
# 🎯 COURSE MANAGEMENT SYSTEM
# ===============================================================

def get_courses_file():
    """Get the courses configuration file"""
    return os.path.join(PERSISTENT_DATA_DIR, "course_management", "courses_config.json")

def get_passwords_file():
    """Get the passwords configuration file"""
    return os.path.join(PERSISTENT_DATA_DIR, "course_management", "admin_passwords.json")

def load_courses_config():
    """Load courses configuration from JSON file"""
    try:
        courses_file = get_courses_file()
        if os.path.exists(courses_file):
            with open(courses_file, 'r') as f:
                return json.load(f)
        
        # Default courses if file doesn't exist
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
        
        # Drop the existing table if it exists (we'll recreate it with proper schema)
        c.execute("DROP TABLE IF EXISTS weekly_courses")
        
        # Create the table with the complete schema
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
        print("✅ Database table recreated with proper schema")
        return True
    except Exception as e:
        print(f"❌ Database fix failed: {e}")
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
        
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            return False
        else:
            print("✅ Database schema is correct")
            return True
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return False
# ===============================================================
# 🎯 AUTOMATED MCQ & GAP-FILLING SYSTEM
# ===============================================================

def get_mcq_file(course_code, week):
    """Get the MCQ questions file path for a specific course and week"""
    safe_week = week.replace(" ", "_").replace(":", "")
    return os.path.join(PERSISTENT_DATA_DIR, "mcq_questions", f"{course_code}_{safe_week}_mcq.json")

def save_mcq_questions(course_code, week, questions):
    """Save MCQ questions for a course and week"""
    try:
        # Get the MCQ directory
        mcq_file = get_file(course_code, "mcq")
        mcq_dir = os.path.dirname(mcq_file)
        
        # Create directory if it doesn't exist
        os.makedirs(mcq_dir, exist_ok=True)
        
        # Save to week-specific file
        week_file = os.path.join(mcq_dir, f"{week}_questions.json")
        
        with open(week_file, 'w') as f:
            json.dump(questions, f, indent=2)
        
        st.write(f"✅ Saved {len(questions)} questions to {week_file}")  # DEBUG
        return True
    except Exception as e:
        st.error(f"Error saving MCQ questions: {e}")
        return False
        

def load_mcq_questions(course_code, week):
    """Load MCQ questions for a given course and week"""
    try:
        # Get the file path for MCQ questions
        mcq_file = get_file(course_code, "mcq")
        mcq_dir = os.path.dirname(mcq_file)
        week_file = os.path.join(mcq_dir, f"{week}_questions.json")
    
        
        if os.path.exists(week_file):
            with open(week_file, 'r') as f:
                questions = json.load(f)

                return questions
    except Exception as e:
        st.write(f"❌ Error loading MCQ questions: {e}")  # DEBUG
        return []

def auto_grade_mcq_submission(questions, answers):
    """Automatically grade MCQ submissions and return score"""
    try:
        total_questions = len(questions)
        correct_answers = 0
        
        for i, question in enumerate(questions):
            if i < len(answers):
                user_answer = answers[i].strip().lower()
                correct_answer = question.get('correct_answer', '').strip().lower()
                
                # For multiple choice
                if question['type'] == 'mcq':
                    if user_answer == correct_answer:
                        correct_answers += 1
                
                # For gap filling - allow partial matches
                elif question['type'] == 'gap_fill':
                    # Split correct answers if multiple are acceptable
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
            # Check for existing submission
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
            # Create new dataframe with proper columns
            df = pd.DataFrame([submission_data])
        
        df.to_csv(classwork_file, index=False)
        return True
        
    except Exception as e:
        st.error(f"❌ Error saving MCQ submission: {e}")
        return False

def display_mcq_questions(questions):
    """Display MCQ questions to students"""
    answers = []
    
    for i, question in enumerate(questions):
        st.markdown(f'<div class="mcq-question">', unsafe_allow_html=True)
        
        if question['type'] == 'mcq':
            st.write(f"**Q{i+1}: {question['question']}**")
            options = question['options']
            
            # Display options
            selected_option = st.radio(
                f"Select your answer for Q{i+1}:",
                options=options,
                key=f"mcq_{i}",
                index=None
            )
            answers.append(selected_option if selected_option else "")
            
        elif question['type'] == 'gap_fill':
            st.write(f"**Q{i+1}: {question['question']}**")
            st.markdown('<div class="gap-filling">', unsafe_allow_html=True)
            user_answer = st.text_input(
                f"Your answer for Q{i+1}:",
                placeholder="Type your answer here...",
                key=f"gap_{i}"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            answers.append(user_answer if user_answer else "")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    return answers

# ===============================================================
# 🗄️ COURSE MANAGEMENT DATABASE FUNCTIONS
# ===============================================================

def init_course_db():
    """Initialize SQLite database for course storage with proper migration"""
    try:
        # First, ensure data directory exists
        ensure_data_directory()
        
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weekly_courses'")
        table_exists = c.fetchone() is not None
        
        if not table_exists:
            # Create table with all required columns
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
            print("✅ Created new weekly_courses table with full schema")
        else:
            # Table exists, check and add missing columns
            c.execute("PRAGMA table_info(weekly_courses)")
            existing_columns = [column[1] for column in c.fetchall()]
            
            # Define required columns
            required_columns = {
                'module_type': 'TEXT',
                'duration': 'TEXT', 
                'difficulty': 'TEXT',
                'objectives': 'TEXT',
                'notes': 'TEXT'
            }
            
            # Add missing columns
            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    c.execute(f'ALTER TABLE weekly_courses ADD COLUMN {column_name} {column_type}')
                    print(f"✅ Added missing column: {column_name}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        # Try emergency fix
        return emergency_database_fix()

def add_course_to_db(week_name, course_name, course_code, module_type="Lecture", duration="1-2 hours", difficulty="Beginner", objectives="", notes=""):
    """Add course to database with module metadata - SAFE VERSION"""
    try:
        # First ensure database is properly initialized
        init_course_db()
        
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        
        # Debug: Check table schema
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        print(f"📋 Database columns: {columns}")
        
        # Insert with all columns
        c.execute('''
            INSERT INTO weekly_courses 
            (week_name, course_name, course_code, module_type, duration, difficulty, objectives, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            week_name, 
            course_name, 
            course_code,
            module_type,
            duration,
            difficulty,
            objectives,
            notes,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        
        conn.commit()
        conn.close()
        print(f"✅ Successfully saved: {course_name} to week: {week_name}")
        return True
        
    except Exception as e:
        print(f"❌ Database error in add_course_to_db: {e}")
        
        # Emergency recovery - try with minimal columns
        try:
            conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
            c = conn.cursor()
            c.execute('''
                INSERT INTO weekly_courses 
                (week_name, course_name, course_code, created_at)
                VALUES (?, ?, ?, ?)
            ''', (week_name, course_name, course_code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit()
            conn.close()
            print(f"🔄 Saved with minimal columns: {course_name}")
            return True
        except Exception as e2:
            print(f"❌ Emergency save also failed: {e2}")
            return False
def get_weeks_from_db():
    """Get all unique weeks from database"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('SELECT DISTINCT week_name FROM weekly_courses ORDER BY created_at')
    weeks = [row[0] for row in c.fetchall()]
    conn.close()
    return weeks

def get_courses_by_week(week_name):
    """Get all courses for a specific week"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('SELECT course_name, course_code FROM weekly_courses WHERE week_name = ? ORDER BY id', (week_name,))
    courses = [{"name": row[0], "code": row[1]} for row in c.fetchall()]
    conn.close()
    return courses

def delete_week_from_db(week_name):
    """Delete a week and all its courses from database"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('DELETE FROM weekly_courses WHERE week_name = ?', (week_name,))
    conn.commit()
    conn.close()

def get_all_courses_from_db():
    """Get all courses from database with proper error handling"""
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        
        # Check if course_code column exists
        c = conn.cursor()
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'course_code' in columns:
            df = pd.read_sql_query('SELECT week_name, course_name, course_code, created_at FROM weekly_courses ORDER BY created_at', conn)
        else:
            # Fallback for older database structure
            df = pd.read_sql_query('SELECT week_name, course_name, created_at FROM weekly_courses ORDER BY created_at', conn)
            df['course_code'] = 'UNKNOWN'  # Add placeholder column
        
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

def migrate_old_database():
    """Migrate old database structure to new one if needed"""
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        
        # Check if we need to migrate
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'course_code' not in columns:
            st.info("🔄 Migrating database to new structure...")
            
            # Add the new column
            c.execute('ALTER TABLE weekly_courses ADD COLUMN course_code TEXT')
            
            # Update existing records with course codes
            for course_name, course_code in COURSES.items():
                c.execute('UPDATE weekly_courses SET course_code = ? WHERE course_name = ?', (course_code, course_name))
            
            # Set unknown for any remaining
            c.execute("UPDATE weekly_courses SET course_code = 'UNKNOWN' WHERE course_code IS NULL")
            
            conn.commit()
            st.success("✅ Database migration completed!")
        
        conn.close()
    except Exception as e:
        st.error(f"Migration error: {e}")


# ===============================================================
# 🔧 HELPER FUNCTIONS
# ===============================================================

def get_persistent_path(file_type, course_code="", filename=""):
    """Get persistent file paths that survive reboots"""
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

def get_file(course_code, file_type):
    """Get file path for course-specific files"""
    return get_persistent_path(file_type, course_code)
    
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
        "mcq": os.path.join(base_dir, "mcq_questions"),  # Directory for MCQ files
        "attendance_status": os.path.join(base_dir, "attendance_status.json"),
        "classwork_status": os.path.join(base_dir, "classwork_status.json")
    }
    
    return file_map.get(file_type, os.path.join(base_dir, f"{file_type}.csv"))
    
def clean_text(val):
    """Clean text values"""
    return str(val or "").strip()

def normalize_course_name(name):
    """Normalize course name formatting"""
    return name.replace("–", "-").replace("—", "-").strip()

def get_lecture_file(course_code):
    """Return a valid lecture CSV path"""
    if not course_code or not isinstance(course_code, str):
        st.warning("⚠️ Invalid or missing course code. Please reselect a course.")
        return None
    path = get_file(course_code, "lectures")
    return path

def ensure_scores_file(course_code):
    """Ensure scores file exists with proper columns"""
    scores_file = get_file(course_code, "scores")
    os.makedirs(os.path.dirname(scores_file), exist_ok=True)
    
    required_columns = ["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Total", "Grade"]
    
    if not os.path.exists(scores_file):
        # Create new scores file with proper columns
        df = pd.DataFrame(columns=required_columns)
        df.to_csv(scores_file, index=False)
        return df
    else:
        # Check if file has required columns
        try:
            df = pd.read_csv(scores_file)
            # Add any missing columns
            for col in required_columns:
                if col not in df.columns:
                    df[col] = "" if col == "Grade" else 0
            df.to_csv(scores_file, index=False)
            return df
        except:
            # If file is corrupted, recreate it
            df = pd.DataFrame(columns=required_columns)
            df.to_csv(scores_file, index=False)
            return df

# ===============================================================
# 📊 ATTENDANCE MANAGEMENT
# ===============================================================

def init_attendance_status():
    """Initialize attendance status file"""
    status_file = get_persistent_path("attendance_status")
    if not os.path.exists(status_file):
        with open(status_file, 'w') as f:
            json.dump({}, f)

def get_attendance_status(course_code, week):
    """Get attendance status for specific course and week"""
    init_attendance_status()
    status_file = get_persistent_path("attendance_status")
    
    try:
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        
        week_key = week.replace(" ", "")
        key = f"{course_code}_{week_key}"
        return status_data.get(key, {"is_open": False, "open_time": None})
    except Exception as e:
        return {"is_open": False, "open_time": None}

def set_attendance_status(course_code, week, is_open, open_time=None):
    """Set attendance status for specific course and week"""
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
            status_data[key] = {
                "is_open": False,
                "open_time": None
            }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error setting attendance status: {e}")
        return False

def has_marked_attendance(course_code, week, name, matric):
    """Check if student has already marked attendance"""
    try:
        attendance_folder = get_persistent_path("attendance")
        week_key = week.replace(" ", "")
        attendance_file = os.path.join(attendance_folder, f"attendance_{course_code}_{week_key}.csv")
        
        if not os.path.exists(attendance_file):
            return False
        
        df = pd.read_csv(attendance_file)
        df['Name'] = df['Name'].astype(str).str.strip().str.lower()
        df['Matric'] = df['Matric'].astype(str).str.strip().str.lower()
        
        name_clean = name.strip().lower()
        matric_clean = matric.strip().lower()
        
        existing = df[(df['Name'] == name_clean) & (df['Matric'] == matric_clean)]
        return len(existing) > 0
        
    except Exception as e:
        st.error(f"⚠️ Error checking attendance: {e}")
        return True

def mark_attendance_entry(course_code, name, matric, week):
    """Mark student attendance and save persistently"""
    try:
        attendance_folder = get_persistent_path("attendance")
        week_key = week.replace(" ", "")
        attendance_file = os.path.join(attendance_folder, f"attendance_{course_code}_{week_key}.csv")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_data = {
            'Name': [name.strip()],
            'Matric': [matric.strip()], 
            'Week': [week],
            'Timestamp': [timestamp]
        }
        
        new_df = pd.DataFrame(new_data)
        
        if os.path.exists(attendance_file):
            existing_df = pd.read_csv(attendance_file)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
            
        combined_df.to_csv(attendance_file, index=False)
        return True
        
    except Exception as e:
        st.error(f"⚠️ Error recording attendance: {e}")
        return False

# ===============================================================
# 📚 LECTURE MANAGEMENT
# ===============================================================

def load_lectures(course_code):
    """Load or create lecture CSV safely"""
    if not course_code:
        return pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment", "PDF_File", "Video_File"])
    
    lecture_file = get_file(course_code, "lectures")
    os.makedirs(os.path.dirname(lecture_file), exist_ok=True)
    
    # Create default CSV if missing
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
    
    # Safe load existing file
    try:
        df = pd.read_csv(lecture_file)
        # Ensure all required columns exist
        for col in ["Week", "Topic", "Brief", "Classwork", "Assignment", "PDF_File", "Video_File"]:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"⚠️ Could not read lecture file: {e}")
        return pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment", "PDF_File", "Video_File"])

# ===============================================================
# 🧩 CLASSWORK MANAGEMENT
# ===============================================================

def get_classwork_status(course_code, week):
    """Get classwork status for specific course and week"""
    try:
        status_file = get_persistent_path("attendance_status")
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        
        week_key = week.replace(" ", "")
        key = f"classwork_{course_code}_{week_key}"
        return status_data.get(key, {"is_open": False, "open_time": None})
    except Exception:
        return {"is_open": False, "open_time": None}

def set_classwork_status(course_code, week, is_open, open_time=None):
    """Set classwork status for specific course and week"""
    try:
        status_file = get_persistent_path("attendance_status")
        with open(status_file, 'r') as f:
            status_data = json.load(f)
        
        week_key = week.replace(" ", "")
        key = f"classwork_{course_code}_{week_key}"
        
        if is_open:
            status_data[key] = {
                "is_open": True,
                "open_time": open_time.isoformat() if open_time else datetime.now().isoformat()
            }
        else:
            status_data[key] = {
                "is_open": False,
                "open_time": None
            }
        
        with open(status_file, 'w') as f:
            json.dump(status_data, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error setting classwork status: {e}")
        return False

def is_classwork_open(course_code, week):
    """Check if classwork is open for submission"""
    status = get_classwork_status(course_code, week)
    return status.get("is_open", False)

def close_classwork_after_20min(course_code, week):
    """Auto-close classwork after 20 minutes"""
    status = get_classwork_status(course_code, week)
    
    if status.get("is_open", False) and status.get("open_time"):
        try:
            open_time = datetime.fromisoformat(status["open_time"])
            elapsed = (datetime.now() - open_time).total_seconds()
            
            if elapsed > 1200:  # 20 minutes in seconds
                set_classwork_status(course_code, week, False)
                return True
        except Exception as e:
            st.error(f"Error in classwork auto-close: {e}")
    
    return False

def save_classwork(name, matric, week, answers):
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
            # Check for existing submission
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
        st.error(f"❌ Error saving classwork: {e}")
        return False

# ===============================================================
# 🧩 CLASSWORK CONTROL PANEL (ADMIN)
# ===============================================================

def show_classwork_control(course_code):
    """Admin panel to open/close classwork for specific weeks"""
    st.header("🎛 Classwork Control Panel")
    
    selected_week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_classwork_week")
    
    # Get current status
    current_status = get_classwork_status(course_code, selected_week)
    is_currently_open = current_status.get("is_open", False)
    
    # Display current status
    if is_currently_open:
        st.success(f"✅ Classwork is CURRENTLY OPEN for {selected_week}")
    else:
        st.warning(f"🚫 Classwork is CURRENTLY CLOSED for {selected_week}")
    
    # Classwork control buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔓 OPEN Classwork", use_container_width=True, type="primary"):
            success = set_classwork_status(course_code, selected_week, True, datetime.now())
            if success:
                st.success(f"✅ Classwork OPENED for {selected_week}")
                st.rerun()
    with col2:
        if st.button("🔒 CLOSE Classwork", use_container_width=True, type="secondary"):
            success = set_classwork_status(course_code, selected_week, False)
            if success:
                st.warning(f"🚫 Classwork CLOSED for {selected_week}")
                st.rerun()
    
    # Auto-close countdown and functionality
    if is_currently_open and current_status.get("open_time"):
        try:
            open_time = datetime.fromisoformat(current_status["open_time"])
            elapsed = (datetime.now() - open_time).total_seconds()
            remaining = max(0, 1200 - elapsed)  # 20 minutes
            
            if remaining <= 0:
                set_classwork_status(course_code, selected_week, False)
                st.error(f"⏰ Classwork for {selected_week} has automatically closed after 20 minutes.")
                st.rerun()
            else:
                mins = int(remaining // 60)
                secs = int(remaining % 60)
                st.info(f"⏳ Classwork will auto-close in {mins:02d}:{secs:02d}")
        except Exception as e:
            st.error(f"Error in classwork auto-close: {e}")
    
    # Quick actions for multiple weeks
    st.subheader("📋 Quick Actions")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔓 OPEN All Weeks", use_container_width=True):
            for week_num in range(1, 16):
                set_classwork_status(course_code, f"Week {week_num}", True, datetime.now())
            st.success("✅ All weeks opened for classwork!")
            st.rerun()
    
    with col2:
        if st.button("🔒 CLOSE All Weeks", use_container_width=True):
            for week_num in range(1, 16):
                set_classwork_status(course_code, f"Week {week_num}", False)
            st.warning("🚫 All weeks closed for classwork!")
            st.rerun()
# ===============================================================
# 📁 FILE MANAGEMENT
# ===============================================================

def save_file(course_code, student_name, week, uploaded_file, folder_name):
    """Safely save uploaded file to appropriate course and folder"""
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
    """Log each upload to CSV file for admin tracking"""
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

# ===============================================================
# 🎥 VIDEO MANAGEMENT
# ===============================================================

def get_video_files(course_code):
    """Get list of video files for a course"""
    video_dir = get_persistent_path("video", course_code)
    
    if not os.path.exists(video_dir):
        return []
    
    video_files = sorted([f for f in os.listdir(video_dir) 
                         if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])
    return video_files

def upload_video(course_code, uploaded_video):
    """Upload video to persistent storage"""
    try:
        video_dir = get_persistent_path("video", course_code)
        os.makedirs(video_dir, exist_ok=True)
        
        safe_name = "".join(c for c in uploaded_video.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        # Handle duplicates
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



import streamlit as st
import pandas as pd
import sqlite3
import os
import re
import json
import base64
from datetime import datetime, date, timedelta, time
from streamlit_autorefresh import st_autorefresh

# ===============================================================
# 🎯 SYSTEM ADMIN CONFIGURATION
# ===============================================================

SYSTEM_ADMIN_PASSWORD = "systemadmin2025"  # Master system admin password
# ===============================================================
# 🗄️ COURSE MANAGEMENT DATABASE FUNCTIONS
# ===============================================================

def init_course_db():
    """Initialize SQLite database for course storage with proper migration"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    
    # Check if table exists and get its structure
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='weekly_courses'")
    table_exists = c.fetchone() is not None
    
    if table_exists:
        # Check if course_code column exists
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'course_code' not in columns:
            # Add the missing course_code column
            c.execute('ALTER TABLE weekly_courses ADD COLUMN course_code TEXT')
    
    # Create table with all required columns
    c.execute('''
        CREATE TABLE IF NOT EXISTS weekly_courses
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         week_name TEXT NOT NULL,
         course_name TEXT NOT NULL,
         course_code TEXT NOT NULL,
         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')
    conn.commit()
    conn.close()

def add_course_to_db(week_name, course_name, course_code):
    """Add course to database"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('INSERT INTO weekly_courses (week_name, course_name, course_code) VALUES (?, ?, ?)', 
              (week_name, course_name, course_code))
    conn.commit()
    conn.close()

def get_weeks_from_db():
    """Get all unique weeks from database"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('SELECT DISTINCT week_name FROM weekly_courses ORDER BY created_at')
    weeks = [row[0] for row in c.fetchall()]
    conn.close()
    return weeks

def get_courses_by_week(week_name):
    """Get all courses for a specific week"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('SELECT course_name, course_code FROM weekly_courses WHERE week_name = ? ORDER BY id', (week_name,))
    courses = [{"name": row[0], "code": row[1]} for row in c.fetchall()]
    conn.close()
    return courses

def delete_week_from_db(week_name):
    """Delete a week and all its courses from database"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    c.execute('DELETE FROM weekly_courses WHERE week_name = ?', (week_name,))
    conn.commit()
    conn.close()

def get_all_courses_from_db():
    """Get all courses from database with proper error handling"""
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        
        # Check if course_code column exists
        c = conn.cursor()
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'course_code' in columns:
            df = pd.read_sql_query('SELECT week_name, course_name, course_code, created_at FROM weekly_courses ORDER BY created_at', conn)
        else:
            # Fallback for older database structure
            df = pd.read_sql_query('SELECT week_name, course_name, created_at FROM weekly_courses ORDER BY created_at', conn)
            df['course_code'] = 'UNKNOWN'
        
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()

# ===============================================================
# 🏫 COURSE MANAGEMENT SYSTEM
# ===============================================================

def show_course_management():
    """Course management system for super admin"""
    st.header("🏫 Course Management System")
    
    # Load current courses
    courses = load_courses_config()
    
    tab1, tab2, tab3 = st.tabs(["📚 Manage Courses", "🔑 Manage Passwords", "📊 System Overview"])
    
    with tab1:
        st.subheader("Add/Remove Courses")
        
        # Add new course
        col1, col2 = st.columns(2)
        with col1:
            new_course_name = st.text_input("New Course Name", placeholder="e.g., CHEM 101 - Organic Chemistry")
        with col2:
            new_course_code = st.text_input("Course Code", placeholder="e.g., CHEM101").upper()
        
        if st.button("➕ Add Course", type="primary"):
            if new_course_name and new_course_code:
                if new_course_name in courses:
                    st.error("❌ Course name already exists!")
                else:
                    courses[new_course_name] = new_course_code
                    if save_courses_config(courses):
                        st.success(f"✅ Course '{new_course_name}' added successfully!")
                        st.rerun()
            else:
                st.error("❌ Please enter both course name and code.")
        
        # Display and manage existing courses
        st.subheader("Current Courses")
        if courses:
            for course_name, course_code in courses.items():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f'<div class="course-card">{course_name} <br><small>Code: {course_code}</small></div>', unsafe_allow_html=True)
                with col2:
                    if st.button("✏️", key=f"edit_{course_code}"):
                        st.session_state[f"editing_{course_code}"] = True
                with col3:
                    if st.button("🗑️", key=f"delete_{course_code}"):
                        del courses[course_name]
                        save_courses_config(courses)
                        st.success(f"✅ Course '{course_name}' deleted!")
                        st.rerun()
                
                # Edit course
                if st.session_state.get(f"editing_{course_code}", False):
                    with st.form(f"edit_form_{course_code}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            edited_name = st.text_input("Course Name", value=course_name, key=f"name_{course_code}")
                        with col2:
                            edited_code = st.text_input("Course Code", value=course_code, key=f"code_{course_code}").upper()
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("💾 Save Changes"):
                                if edited_name and edited_code:
                                    # Remove old entry and add new one
                                    del courses[course_name]
                                    courses[edited_name] = edited_code
                                    save_courses_config(courses)
                                    st.session_state[f"editing_{course_code}"] = False
                                    st.success("✅ Course updated successfully!")
                                    st.rerun()
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[f"editing_{course_code}"] = False
                                st.rerun()
        else:
            st.info("No courses added yet. Add courses using the form above.")
    
    with tab2:
        st.subheader("Manage Admin Passwords")
        
        passwords = load_admin_passwords()
        courses = load_courses_config()
        
        if courses:
            for course_name, course_code in courses.items():
                current_password = passwords.get(course_code, DEFAULT_ADMIN_PASSWORD)
                
                with st.expander(f"🔐 {course_name} ({course_code})", expanded=False):
                    st.info(f"Current password: **{current_password}**")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_password = st.text_input("New Password", type="password", key=f"new_pass_{course_code}")
                    with col2:
                        confirm_password = st.text_input("Confirm Password", type="password", key=f"confirm_pass_{course_code}")
                    
                    if st.button("🔄 Change Password", key=f"change_{course_code}"):
                        if new_password and confirm_password:
                            if new_password == confirm_password:
                                if set_course_password(course_code, new_password):
                                    st.success("✅ Password changed successfully!")
                                    st.rerun()
                            else:
                                st.error("❌ Passwords don't match!")
                        else:
                            st.error("❌ Please enter and confirm new password!")
                    
                    # Reset to default
                    if st.button("🔄 Reset to Default", key=f"reset_{course_code}"):
                        if set_course_password(course_code, DEFAULT_ADMIN_PASSWORD):
                            st.success("✅ Password reset to default!")
                            st.rerun()
        else:
            st.info("No courses available. Add courses first.")
    
    with tab3:
        st.subheader("System Overview")
        
        courses = load_courses_config()
        passwords = load_admin_passwords()
        
        st.metric("Total Courses", len(courses))
        
        # Course statistics
        if courses:
            st.subheader("Course Details")
            overview_data = []
            for course_name, course_code in courses.items():
                course_password = passwords.get(course_code, "Default")
                overview_data.append({
                    "Course Name": course_name,
                    "Course Code": course_code,
                    "Password Set": "Custom" if course_code in passwords else "Default"
                })
            
            overview_df = pd.DataFrame(overview_data)
            st.dataframe(overview_df, use_container_width=True)
            
def get_system_logs_file():
    """Get system logs file path"""
    return os.path.join(PERSISTENT_DATA_DIR, "system_logs.json")

def init_system_logs():
    """Initialize system logs file"""
    logs_file = get_system_logs_file()
    if not os.path.exists(logs_file):
        with open(logs_file, 'w') as f:
            json.dump({"lecturer_logs": [], "student_logs": []}, f)

def log_lecturer_activity(lecturer_name, course_code, action, details=""):
    """Log lecturer activities"""
    try:
        logs_file = get_system_logs_file()
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = {"lecturer_logs": [], "student_logs": []}
        
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "lecturer_name": lecturer_name,
            "course_code": course_code,
            "action": action,
            "details": details
        }
        
        logs["lecturer_logs"].append(log_entry)
        
        # Keep only last 1000 entries to prevent file from growing too large
        if len(logs["lecturer_logs"]) > 1000:
            logs["lecturer_logs"] = logs["lecturer_logs"][-1000:]
        
        with open(logs_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        print(f"Error logging lecturer activity: {e}")

def log_student_activity(student_name, matric, course_code, action, details=""):
    """Log student activities"""
    try:
        logs_file = get_system_logs_file()
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs = json.load(f)
        else:
            logs = {"lecturer_logs": [], "student_logs": []}
        
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "student_name": student_name,
            "matric": matric,
            "course_code": course_code,
            "action": action,
            "details": details
        }
        
        logs["student_logs"].append(log_entry)
        
        # Keep only last 1000 entries
        if len(logs["student_logs"]) > 1000:
            logs["student_logs"] = logs["student_logs"][-1000:]
        
        with open(logs_file, 'w') as f:
            json.dump(logs, f, indent=2)
            
    except Exception as e:
        print(f"Error logging student activity: {e}")

def get_lecturer_logs():
    """Get all lecturer logs"""
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
    """Get all student logs"""
    try:
        logs_file = get_system_logs_file()
        if os.path.exists(logs_file):
            with open(logs_file, 'r') as f:
                logs = json.load(f)
            return logs.get("student_logs", [])
        return []
    except:
        return []

# ===============================================================
# 🏢 SYSTEM ADMIN DASHBOARD
# ===============================================================

def show_system_admin_dashboard():
    """System Admin Dashboard with comprehensive monitoring"""
    st.title("🏢 System Administration Dashboard")
    
    # System Admin Authentication
    st.sidebar.subheader("🔐 System Admin Access")
    sys_admin_password = st.sidebar.text_input("System Admin Password", type="password", key="sys_admin_pass")
    
    if sys_admin_password != SYSTEM_ADMIN_PASSWORD:
        st.warning("Enter the System Admin password to continue")
        return
    
    st.success("✅ Logged in as System Administrator")
    
    # Initialize system logs
    init_system_logs()
    
    # Create tabs for different admin functions
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 System Overview", 
        "🏫 Course Management", # NEW TAB ADDED HERE
        "👩‍🏫 Lecturer Activity", 
        "🎓 Student Activity",
        "📈 Analytics",
        "🔧 System Settings",
        "🚨 Alert Center"
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

def show_system_overview():
    """System overview with key metrics"""
    st.header("📊 System Overview")
    
    # Load courses and logs
    courses = load_courses_config()
    lecturer_logs = get_lecturer_logs()
    student_logs = get_student_logs()
    
    # Key metrics
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
        total_activities = len(lecturer_logs) + len(student_logs)
        st.metric("Total Activities", total_activities)
    
    # Recent activity timeline
    st.subheader("🕒 Recent Activity Timeline")
    
    # Combine and sort recent logs
    all_logs = []
    for log in lecturer_logs[-20:]:  # Last 20 lecturer activities
        log['type'] = 'Lecturer'
        all_logs.append(log)
    
    for log in student_logs[-20:]:  # Last 20 student activities
        log['type'] = 'Student'
        all_logs.append(log)
    
    # Sort by timestamp
    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)
    
    if all_logs:
        for log in all_logs[:10]:  # Show last 10 activities
            if log['type'] == 'Lecturer':
                icon = "👩‍🏫"
                name = log['lecturer_name']
                action = log['action']
            else:
                icon = "🎓"
                name = log['student_name']
                action = log['action']
            
            st.write(f"{icon} **{name}** - {action} - *{log['timestamp']}*")
            if log.get('details'):
                st.caption(f"Details: {log['details']}")
            st.divider()
    else:
        st.info("No recent activity recorded")

def show_lecturer_activity():
    """Detailed lecturer activity logs"""
    st.header("👩‍🏫 Lecturer Activity Monitor")
    
    lecturer_logs = get_lecturer_logs()
    
    if not lecturer_logs:
        st.info("No lecturer activity recorded yet")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_filter = st.selectbox("Time Filter", ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days"])
    
    with col2:
        lecturers = sorted(set(log['lecturer_name'] for log in lecturer_logs))
        lecturer_filter = st.selectbox("Filter by Lecturer", ["All Lecturers"] + lecturers)
    
    with col3:
        actions = sorted(set(log['action'] for log in lecturer_logs))
        action_filter = st.selectbox("Filter by Action", ["All Actions"] + actions)
    
    # Filter logs
    filtered_logs = lecturer_logs
    
    if date_filter != "All Time":
        if date_filter == "Last 24 Hours":
            cutoff = datetime.now() - timedelta(hours=24)
        elif date_filter == "Last 7 Days":
            cutoff = datetime.now() - timedelta(days=7)
        else:  # Last 30 Days
            cutoff = datetime.now() - timedelta(days=30)
        
        filtered_logs = [log for log in filtered_logs if datetime.strptime(log['timestamp'], "%Y-%m-%d %H:%M:%S") > cutoff]
    
    if lecturer_filter != "All Lecturers":
        filtered_logs = [log for log in filtered_logs if log['lecturer_name'] == lecturer_filter]
    
    if action_filter != "All Actions":
        filtered_logs = [log for log in filtered_logs if log['action'] == action_filter]
    
    # Display logs
    if filtered_logs:
        st.subheader(f"📋 Activity Logs ({len(filtered_logs)} records)")
        
        # Convert to DataFrame for better display
        log_data = []
        for log in filtered_logs:
            log_data.append({
                'Timestamp': log['timestamp'],
                'Lecturer': log['lecturer_name'],
                'Course': log['course_code'],
                'Action': log['action'],
                'Details': log.get('details', '')
            })
        
        df = pd.DataFrame(log_data)
        st.dataframe(df, use_container_width=True)
        
        # Download option
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Lecturer Logs (CSV)",
            data=csv,
            file_name="lecturer_activity_logs.csv",
            mime="text/csv"
        )
        
        # Lecturer statistics
        st.subheader("📈 Lecturer Statistics")
        
        # Most active lecturers
        lecturer_activity = {}
        for log in filtered_logs:
            lecturer = log['lecturer_name']
            lecturer_activity[lecturer] = lecturer_activity.get(lecturer, 0) + 1
        
        if lecturer_activity:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Most Active Lecturers:**")
                for lecturer, count in sorted(lecturer_activity.items(), key=lambda x: x[1], reverse=True)[:5]:
                    st.write(f"• {lecturer}: {count} activities")
            
            with col2:
                st.write("**Common Actions:**")
                action_counts = {}
                for log in filtered_logs:
                    action = log['action']
                    action_counts[action] = action_counts.get(action, 0) + 1
                
                for action, count in sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                    st.write(f"• {action}: {count} times")
    else:
        st.info("No lecturer activity matching the filters")

def show_student_activity():
    """Detailed student activity logs"""
    st.header("🎓 Student Activity Monitor")
    
    student_logs = get_student_logs()
    
    if not student_logs:
        st.info("No student activity recorded yet")
        return
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        date_filter = st.selectbox("Time Filter", ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days"], key="student_date_filter")
    
    with col2:
        courses = sorted(set(log['course_code'] for log in student_logs))
        course_filter = st.selectbox("Filter by Course", ["All Courses"] + courses)
    
    with col3:
        actions = sorted(set(log['action'] for log in student_logs))
        action_filter = st.selectbox("Filter by Action", ["All Actions"] + actions, key="student_action_filter")
    
    # Filter logs
    filtered_logs = student_logs
    
    if date_filter != "All Time":
        if date_filter == "Last 24 Hours":
            cutoff = datetime.now() - timedelta(hours=24)
        elif date_filter == "Last 7 Days":
            cutoff = datetime.now() - timedelta(days=7)
        else:  # Last 30 Days
            cutoff = datetime.now() - timedelta(days=30)
        
        filtered_logs = [log for log in filtered_logs if datetime.strptime(log['timestamp'], "%Y-%m-%d %H:%M:%S") > cutoff]
    
    if course_filter != "All Courses":
        filtered_logs = [log for log in filtered_logs if log['course_code'] == course_filter]
    
    if action_filter != "All Actions":
        filtered_logs = [log for log in filtered_logs if log['action'] == action_filter]
    
    # Display logs
    if filtered_logs:
        st.subheader(f"📋 Student Activity Logs ({len(filtered_logs)} records)")
        
        # Convert to DataFrame for better display
        log_data = []
        for log in filtered_logs:
            log_data.append({
                'Timestamp': log['timestamp'],
                'Student': log['student_name'],
                'Matric': log['matric'],
                'Course': log['course_code'],
                'Action': log['action'],
                'Details': log.get('details', '')
            })
        
        df = pd.DataFrame(log_data)
        st.dataframe(df, use_container_width=True)
        
        # Download option
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Student Logs (CSV)",
            data=csv,
            file_name="student_activity_logs.csv",
            mime="text/csv"
        )
        
        # Student statistics
        st.subheader("📈 Student Engagement Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Most active students
            student_activity = {}
            for log in filtered_logs:
                student = f"{log['student_name']} ({log['matric']})"
                student_activity[student] = student_activity.get(student, 0) + 1
            
            if student_activity:
                st.write("**Most Active Students:**")
                for student, count in sorted(student_activity.items(), key=lambda x: x[1], reverse=True)[:5]:
                    st.write(f"• {student}: {count} activities")
        
        with col2:
            # Course engagement
            course_engagement = {}
            for log in filtered_logs:
                course = log['course_code']
                course_engagement[course] = course_engagement.get(course, 0) + 1
            
            if course_engagement:
                st.write("**Course Engagement:**")
                for course, count in sorted(course_engagement.items(), key=lambda x: x[1], reverse=True)[:5]:
                    st.write(f"• {course}: {count} activities")
    else:
        st.info("No student activity matching the filters")

def show_analytics():
    """System analytics and insights"""
    st.header("📈 System Analytics")
    
    lecturer_logs = get_lecturer_logs()
    student_logs = get_student_logs()
    courses = load_courses_config()
    
    if not lecturer_logs and not student_logs:
        st.info("No data available for analytics")
        return
    
    # Activity trends
    st.subheader("📊 Activity Trends")
    
    # Daily activity for last 7 days
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    
    lecturer_daily = {date: 0 for date in dates}
    student_daily = {date: 0 for date in dates}
    
    for log in lecturer_logs:
        log_date = log['timestamp'].split()[0]
        if log_date in lecturer_daily:
            lecturer_daily[log_date] += 1
    
    for log in student_logs:
        log_date = log['timestamp'].split()[0]
        if log_date in student_daily:
            student_daily[log_date] += 1
    
    # Create trend chart data
    trend_data = {
        'Date': dates,
        'Lecturer Activities': [lecturer_daily[date] for date in dates],
        'Student Activities': [student_daily[date] for date in dates]
    }
    
    trend_df = pd.DataFrame(trend_data)
    st.line_chart(trend_df.set_index('Date'))
    
    # System usage statistics
    st.subheader("🔍 Usage Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Lecturer Activity Distribution:**")
        lecturer_actions = {}
        for log in lecturer_logs:
            action = log['action']
            lecturer_actions[action] = lecturer_actions.get(action, 0) + 1
        
        for action, count in sorted(lecturer_actions.items(), key=lambda x: x[1], reverse=True):
            st.write(f"• {action}: {count}")
    
    with col2:
        st.write("**Student Activity Distribution:**")
        student_actions = {}
        for log in student_logs:
            action = log['action']
            student_actions[action] = student_actions.get(action, 0) + 1
        
        for action, count in sorted(student_actions.items(), key=lambda x: x[1], reverse=True):
            st.write(f"• {action}: {count}")

def show_system_settings():
    """System configuration settings"""
    st.header("🔧 System Settings")
    
    # System information
    st.subheader("ℹ️ System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("System Admin Password", "🔒 Secured")
        st.metric("Default Lecturer Password", "bimpe2025class")
    
    with col2:
        st.metric("Data Directory", PERSISTENT_DATA_DIR)
        st.metric("Log Retention", "1000 records per type")
    
    # Password management
    st.subheader("🔐 Password Management")
    
    with st.expander("Change System Admin Password"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        if st.button("Change System Admin Password"):
            if current_password != SYSTEM_ADMIN_PASSWORD:
                st.error("❌ Current password is incorrect")
            elif new_password != confirm_password:
                st.error("❌ New passwords don't match")
            elif not new_password:
                st.error("❌ New password cannot be empty")
            else:
                # In a real system, you'd update the password here
                st.success("✅ System admin password updated successfully!")
                st.info("Note: In production, this would update the system password")
    
    # System maintenance
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
    """System alerts and notifications"""
    st.header("🚨 Alert Center")
    
    # Check for system issues
    lecturer_logs = get_lecturer_logs()
    student_logs = get_student_logs()
    
    alerts = []
    
    # Check for no recent activity
    recent_lecturer = any(is_recent(log['timestamp'], 1) for log in lecturer_logs)
    if not recent_lecturer:
        alerts.append("⚠️ No lecturer activity in the last 24 hours")
    
    recent_student = any(is_recent(log['timestamp'], 1) for log in student_logs)
    if not recent_student:
        alerts.append("⚠️ No student activity in the last 24 hours")
    
    # Check for error patterns
    error_actions = [log for log in lecturer_logs + student_logs if 'error' in log.get('action', '').lower() or 'fail' in log.get('action', '').lower()]
    if error_actions:
        alerts.append(f"🚨 {len(error_actions)} error/failure actions detected")
    
    # Display alerts
    if alerts:
        for alert in alerts:
            st.error(alert)
    else:
        st.success("✅ All systems operational - No critical alerts")
    
    # Recent important events
    st.subheader("📋 Recent Important Events")
    
    important_events = []
    for log in lecturer_logs[-10:] + student_logs[-10:]:
        if any(keyword in log.get('action', '').lower() for keyword in ['password', 'login', 'error', 'submit', 'upload']):
            important_events.append(log)
    
    if important_events:
        for event in sorted(important_events, key=lambda x: x['timestamp'], reverse=True)[:5]:
            if 'lecturer_name' in event:
                st.write(f"👩‍🏫 **{event['lecturer_name']}** - {event['action']} - *{event['timestamp']}*")
            else:
                st.write(f"🎓 **{event['student_name']}** - {event['action']} - *{event['timestamp']}*")
    else:
        st.info("No important events to display")

def generate_system_report():
    """Generate comprehensive system report"""
    lecturer_logs = get_lecturer_logs()
    student_logs = get_student_logs()
    courses = load_courses_config()
    
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_courses": len(courses),
        "total_lecturer_activities": len(lecturer_logs),
        "total_student_activities": len(student_logs),
        "active_lecturers": len(set(log['lecturer_name'] for log in lecturer_logs)),
        "active_students": len(set(log['student_name'] for log in student_logs)),
        "courses": list(courses.values())
    }
    
    # Save report
    report_file = os.path.join(PERSISTENT_DATA_DIR, f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report

def is_recent(timestamp, days=1):
    """Check if timestamp is within the last N days"""
    try:
        log_time = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - log_time).days <= days
    except:
        return False

# ===============================================================
# 🔄 UPDATE EXISTING FUNCTIONS TO INCLUDE LOGGING
# ===============================================================

def update_admin_functions_with_logging(course_code, course_name):
    """Update admin functions to log activities"""
    # Example: When admin logs in
    log_lecturer_activity("Admin User", course_code, "Admin Login", f"Logged into {course_name}")
    
    # Add similar logging calls to other admin actions:
    # - When they change passwords
    # - When they upload materials
    # - When they create MCQ questions
    # - When they open/close classwork

def update_student_functions_with_logging(course_code, student_name, matric):
    """Update student functions to log activities"""
    # Example: When student logs in
    log_student_activity(student_name, matric, course_code, "Student Login")
    
    # Add similar logging calls to other student actions:
    # - When they submit assignments
    # - When they mark attendance
    # - When they submit MCQ answers
    # - When they download materials



# Helper functions for module management
def get_weeks_for_course_from_db(course_code):
    """Get all unique weeks/modules for a specific course"""
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        
        # Check if course_code column exists
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'course_code' in columns:
            c.execute('SELECT DISTINCT week_name FROM weekly_courses WHERE course_code = ? ORDER BY created_at', 
                     (course_code,))
        else:
            c.execute('SELECT DISTINCT week_name FROM weekly_courses ORDER BY created_at')
        
        weeks = [row[0] for row in c.fetchall()]
        conn.close()
        return weeks
    except:
        return []

def get_module_details(week_name, course_code):
    """Get detailed information about a specific module"""
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        c = conn.cursor()
        
        # Check if additional columns exist
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'course_code' in columns and 'module_type' in columns:
            c.execute('''
                SELECT course_name, course_code, module_type, duration, difficulty, objectives, notes, created_at 
                FROM weekly_courses 
                WHERE week_name = ? AND course_code = ? 
                ORDER BY id
            ''', (week_name, course_code))
        else:
            c.execute('SELECT course_name, course_code FROM weekly_courses WHERE week_name = ? ORDER BY id', (week_name,))
        
        results = []
        for row in c.fetchall():
            module_info = {
                'course_name': row[0],
                'course_code': row[1]
            }
            # Add additional fields if they exist
            if len(row) > 2:
                module_info.update({
                    'module_type': row[2],
                    'duration': row[3],
                    'difficulty': row[4],
                    'objectives': row[5],
                    'notes': row[6],
                    'created_at': row[7]
                })
            results.append(module_info)
        
        conn.close()
        return results
    except Exception as e:
        st.error(f"Error getting module details: {e}")
        return []
# Add these helper functions for course-specific operations
def get_courses_by_week_for_course(week_name, course_code):
    """Get all courses for a specific week and course"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    
    # Check if course_code column exists
    c.execute("PRAGMA table_info(weekly_courses)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'course_code' in columns:
        c.execute('SELECT course_name, course_code FROM weekly_courses WHERE week_name = ? AND course_code = ? ORDER BY id', 
                 (week_name, course_code))
    else:
        c.execute('SELECT course_name, course_code FROM weekly_courses WHERE week_name = ? ORDER BY id', (week_name,))
    
    courses = [{"name": row[0], "code": row[1]} for row in c.fetchall()]
    conn.close()
    return courses

def delete_week_for_course(week_name, course_code):
    """Delete a week and all its courses for a specific course from database"""
    conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
    c = conn.cursor()
    
    # Check if course_code column exists
    c.execute("PRAGMA table_info(weekly_courses)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'course_code' in columns:
        c.execute('DELETE FROM weekly_courses WHERE week_name = ? AND course_code = ?', (week_name, course_code))
    else:
        c.execute('DELETE FROM weekly_courses WHERE week_name = ?', (week_name,))
    
    conn.commit()
    conn.close()

def get_courses_for_course_from_db(course_code):
    """Get all courses from database for a specific course with proper error handling"""
    try:
        conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
        
        # Check if course_code column exists
        c = conn.cursor()
        c.execute("PRAGMA table_info(weekly_courses)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'course_code' in columns:
            df = pd.read_sql_query(
                'SELECT week_name, course_name, course_code, created_at FROM weekly_courses WHERE course_code = ? ORDER BY created_at', 
                conn, params=(course_code,)
            )
        else:
            # Fallback for older database structure
            df = pd.read_sql_query('SELECT week_name, course_name, created_at FROM weekly_courses ORDER BY created_at', conn)
            df['course_code'] = 'UNKNOWN'
        
        conn.close()
        return df
    except Exception as e:
        st.error(f"Database error: {e}")
        return pd.DataFrame()
        
        
def show_student_modules(course_code, course_name, student_name, matric_number):
    """Student view of weekly schedules"""
    st.header("📚 Weekly Schedules")
    
    weeks = get_weeks_simple(course_code)
    
    if not weeks:
        st.info("📝 No weekly schedules have been published yet. Check back later!")
        return
    
    st.success(f"✅ Found {len(weeks)} weekly schedules for {course_name}")
    
    for i, week in enumerate(weeks, 1):
        courses = get_courses_by_week_simple(week, course_code)
        
        with st.expander(f"📅 {week} ({len(courses)} courses)", expanded=i == 1):
            st.write("**📚 Courses this week:**")
            for j, course in enumerate(courses, 1):
                st.write(f"{j}. **{course}**")  


def show_course_management():
    """Course management system for super admin with bulk import"""
    st.header("🏫 Course Management System")
    
    # Load current courses
    courses = load_courses_config()
    
    tab1, tab2, tab3, tab4 = st.tabs(["📚 Manage Courses", "📥 Bulk Import", "🔑 Manage Passwords", "📊 System Overview"])
    
    with tab1:
        st.subheader("Add/Remove Courses")
        
        # Individual course addition (keep existing functionality)
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
                        st.success(f"✅ Course '{new_course_name}' added successfully!")
                        st.rerun()
            else:
                st.error("❌ Please enter both course name and code.")
        
        # Display and manage existing courses
        st.subheader("Current Courses")
        if courses:
            # Convert to list with indices to ensure unique keys
            course_list = list(courses.items())
            
            for idx, (course_name, course_code) in enumerate(course_list):
                # Create a unique container for each course
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f'<div class="course-card">{course_name} <br><small>Code: {course_code}</small></div>', unsafe_allow_html=True)
                    with col2:
                        # Use unique key with index and course_name
                        edit_key = f"edit_{idx}_{course_name.replace(' ', '_')}"
                        if st.button("✏️", key=edit_key):
                            st.session_state[edit_key] = True
                    with col3:
                        # Use unique key with index and course_name
                        delete_key = f"delete_{idx}_{course_name.replace(' ', '_')}"
                        if st.button("🗑️", key=delete_key):
                            del courses[course_name]
                            save_courses_config(courses)
                            st.success(f"✅ Course '{course_name}' deleted!")
                            st.rerun()
                    
                    # Edit course - use the same unique key
                    if st.session_state.get(edit_key, False):
                        with st.form(f"edit_form_{idx}_{course_name.replace(' ', '_')}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                edited_name = st.text_input("Course Name", value=course_name, key=f"name_{idx}_{course_code}")
                            with col2:
                                edited_code = st.text_input("Course Code", value=course_code, key=f"code_{idx}_{course_code}").upper()
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.form_submit_button("💾 Save Changes", key=f"save_{idx}_{course_code}"):
                                    if edited_name and edited_code:
                                        # Remove old entry and add new one
                                        del courses[course_name]
                                        courses[edited_name] = edited_code
                                        save_courses_config(courses)
                                        st.session_state[edit_key] = False
                                        st.success("✅ Course updated successfully!")
                                        st.rerun()
                            with col2:
                                if st.form_submit_button("❌ Cancel", key=f"cancel_{idx}_{course_code}"):
                                    st.session_state[edit_key] = False
                                    st.rerun()
        else:
            st.info("No courses added yet. Add courses using the form above or bulk import.")
    
    with tab2:
        st.subheader("📥 Bulk Course Import")
        
        st.info("""
        **Bulk Import Instructions:**
        - Enter one course per line
        - Format: `Course Name | Course Code` or `Course Name, Course Code`
        - You can use comma (,) or pipe (|) as separators
        - Example formats:
        ```
        CHEM 101 - Organic Chemistry, CHEM101
        MATH 201 - Calculus | MATH201
        PHYS 101 - Physics | PHYS101
        ```
        """)
        
        # Bulk course input
        bulk_courses_text = st.text_area(
            "Paste courses here:",
            height=200,
            placeholder="CHEM 101 - Organic Chemistry,\nMATH 201 - Calculus,\nPHYS 101 - Physics",
            key="bulk_courses_textarea"
        )
        
        # Separator option
        col1, col2 = st.columns(2)
        with col1:
            separator = st.selectbox("Separator", [",", "|", "Tab", "Custom"], key="separator_select")
            if separator == "Custom":
                custom_sep = st.text_input("Custom separator", value=";", key="custom_sep")
                separator = custom_sep
            elif separator == "Tab":
                separator = "\t"
        
        with col2:
            st.write("**Preview:**")
            if bulk_courses_text:
                lines = [line.strip() for line in bulk_courses_text.split('\n') if line.strip()]
                st.write(f"Found {len(lines)} courses to import")
        
        # Import options
        col1, col2 = st.columns(2)
        with col1:
            import_mode = st.radio("Import Mode", ["Add new only", "Replace all courses"], key="import_mode")
        
        with col2:
            remove_duplicates = st.checkbox("Remove duplicate course code", value=True, key="remove_duplicates")
            auto_generate_codes = st.checkbox("Auto-generate missing codes", key="auto_generate_codes")
        
        if st.button("🚀 Import Courses", type="primary", key="import_courses_btn"):
            if bulk_courses_text:
                results = process_bulk_courses(
                    bulk_courses_text, 
                    courses, 
                    separator, 
                    import_mode, 
                    remove_duplicates,
                    auto_generate_codes
                )
                display_import_results(results)
            else:
                st.error("❌ Please paste some courses to import!")
    
    with tab3:
        st.subheader("Manage Admin Passwords")
        
        passwords = load_admin_passwords()
        courses = load_courses_config()
        
        if courses:
            # Bulk password reset
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
            
            # Individual course passwords
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
                                    st.success("✅ Password changed successfully!")
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
            default_passwords = len(courses) - custom_passwords
            st.metric("Default Passwords", default_passwords)
        
        # Course statistics
        if courses:
            st.subheader("Course Details")
            overview_data = []
            for course_name, course_code in courses.items():
                course_password = "Custom" if course_code in passwords else "Default"
                overview_data.append({
                    "Course Name": course_name,
                    "Course Code": course_code,
                    "Password": course_password
                })
            
            overview_df = pd.DataFrame(overview_data)
            st.dataframe(overview_df, use_container_width=True)
            
            # Export courses
            st.subheader("Export Courses")
            csv_data = overview_df.to_csv(index=False)
            st.download_button(
                label="📥 Export Courses to CSV",
                data=csv_data,
                file_name="courses_export.csv",
                mime="text/csv",
                key="export_courses_btn"
            )

def process_bulk_courses(bulk_text, existing_courses, separator, import_mode, skip_duplicates, auto_generate_codes):
    """Process bulk course import"""
    results = {
        'success': [],
        'errors': [],
        'duplicates': [],
        'total_processed': 0
    }
    
    lines = [line.strip() for line in bulk_text.split('\n') if line.strip()]
    results['total_processed'] = len(lines)
    
    # If replacing all, clear existing courses first
    if import_mode == "Replace all courses":
        existing_courses.clear()
    
    for i, line in enumerate(lines, 1):
        try:
            # Split the line by separator
            if separator in line:
                parts = [part.strip() for part in line.split(separator)]
            else:
                # Try to split by common separators
                if ',' in line:
                    parts = [part.strip() for part in line.split(',')]
                elif '|' in line:
                    parts = [part.strip() for part in line.split('|')]
                elif '\t' in line:
                    parts = [part.strip() for part in line.split('\t')]
                else:
                    # If no separator, try to extract code from name
                    parts = [line]
            
            # Extract course name and code
            if len(parts) >= 2:
                course_name = parts[0]
                course_code = parts[1].upper()
            else:
                course_name = parts[0]
                if auto_generate_codes:
                    # Auto-generate code from name (extract uppercase letters and numbers)
                    code_match = re.findall(r'[A-Z]+\s*\d+', course_name)
                    if code_match:
                        course_code = code_match[0].replace(' ', '')
                    else:
                        # Generate from first letters
                        words = course_name.split()
                        if len(words) >= 2:
                            course_code = (words[0][0] + words[1][0]).upper() + "101"
                        else:
                            course_code = course_name[:6].upper().replace(' ', '')
                else:
                    results['errors'].append(f"Line {i}: Cannot extract course code - '{line}'")
                    continue
            
            # Validate
            if not course_name or not course_code:
                results['errors'].append(f"Line {i}: Missing course name or code - '{line}'")
                continue
            
            # Check for duplicates
            if course_name in existing_courses:
                results['duplicates'].append(f"Line {i}: Course name exists - '{course_name}'")
                continue
            
            if skip_duplicates and course_code in existing_courses.values():
                results['duplicates'].append(f"Line {i}: Course code exists - '{course_code}'")
                continue
            
            # Add course
            existing_courses[course_name] = course_code
            results['success'].append(f"'{course_name}' - {course_code}")
            
        except Exception as e:
            results['errors'].append(f"Line {i}: Error processing - '{line}' - {str(e)}")
    
    # Save if we have successful imports
    if results['success']:
        save_courses_config(existing_courses)
    
    return results

def display_import_results(results):
    """Display the results of bulk import"""
    st.subheader("📊 Import Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Successful", len(results['success']))
    
    with col2:
        st.metric("Errors", len(results['errors']))
    
    with col3:
        st.metric("Duplicates", len(results['duplicates']))
    
    # Show successful imports
    if results['success']:
        st.success(f"✅ Successfully imported {len(results['success'])} courses:")
        for success in results['success']:
            st.write(f"• {success}")
    
    # Show errors
    if results['errors']:
        st.error(f"❌ {len(results['errors'])} errors occurred:")
        for error in results['errors']:
            st.write(f"• {error}")
    
    # Show duplicates
    if results['duplicates']:
        st.warning(f"⚠️ {len(results['duplicates'])} duplicates skipped:")
        for duplicate in results['duplicates']:
            st.write(f"• {duplicate}")
    
    if results['success']:
        st.rerun()            
# ===============================================================
# 📊 SCORES MANAGEMENT
# ===============================================================

def load_student_scores(course_code, student_name, student_matric):
    """Load scores for specific student"""
    scores_file = get_file(course_code, "scores")
    
    # Ensure scores file exists with proper structure
    ensure_scores_file(course_code)
    
    if not os.path.exists(scores_file):
        return pd.DataFrame()
    
    try:
        scores_df = pd.read_csv(scores_file)
        
        # Check if required columns exist
        if "StudentName" not in scores_df.columns or "MatricNo" not in scores_df.columns:
            st.warning("Scores file format is incorrect. Please contact admin.")
            return pd.DataFrame()
            
        # Filter for current student
        student_scores = scores_df[
            (scores_df["StudentName"].astype(str).str.strip().str.lower() == student_name.lower()) &
            (scores_df["MatricNo"].astype(str).str.strip().str.lower() == student_matric.lower())
        ]
        return student_scores
    except Exception as e:
        st.error(f"Error loading scores: {e}")
        return pd.DataFrame()

def compute_grade(total_score):
    """Compute grade based on total score"""
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
        
def calculate_final_grade(student_scores):
    """Calculate final grade after 15 weeks including exam"""
    if student_scores.empty:
        return None, None, None, None, None, None
    
    try:
        # Filter out weeks without scores and separate exam
        valid_scores = student_scores[
            (student_scores['Assignment'] > 0) | 
            (student_scores['Test'] > 0) | 
            (student_scores['Practical'] > 0) |
            (student_scores['Classwork'] > 0)
        ]
        
        if valid_scores.empty:
            return None, None, None, None, None, None
        
        # Calculate averages for continuous assessment (Weeks 1-15)
        ca_scores = valid_scores[valid_scores['Week'] != 'Exam']
        
        if ca_scores.empty:
            assignment_avg = test_avg = practical_avg = classwork_avg = 0
        else:
            assignment_avg = ca_scores['Assignment'].mean()
            test_avg = ca_scores['Test'].mean()
            practical_avg = ca_scores['Practical'].mean()
            classwork_avg = ca_scores['Classwork'].mean()
        
        # Get exam score
        exam_scores = valid_scores[valid_scores['Week'] == 'Exam']
        if exam_scores.empty:
            exam_score = 0
        else:
            exam_score = exam_scores['Exam'].iloc[0]
        
        # Calculate final total with weights
        final_total = round(
            assignment_avg * 0.08 +      # 8%
            test_avg * 0.08 +            # 8%
            practical_avg * 0.05 +       # 5%
            classwork_avg * 0.09 +       # 9%
            exam_score * 0.70,           # 70%
            1
        )
        
        final_grade = compute_grade(final_total)
        
        return final_total, final_grade, assignment_avg, test_avg, practical_avg, classwork_avg, exam_score
        
    except Exception as e:
        st.error(f"Error calculating final grade: {e}")
        return None, None, None, None, None, None, None
        
def get_student_activity_summary(course_code, student_name, student_matric):
    """Get comprehensive activity summary for student"""
    summary = {
        "attendance_count": 0,
        "classwork_count": 0,
        "assignment_count": 0,
        "drawing_count": 0,
        "seminar_count": 0,
        "recent_activity": []
    }
    
    # Count attendance
    for week_num in range(1, 16):
        week = f"Week {week_num}"
        if has_marked_attendance(course_code, week, student_name, student_matric):
            summary["attendance_count"] += 1
            summary["recent_activity"].append(f"✅ Attended {week}")
    
    # Count classwork submissions
    classwork_file = get_file(course_code, "classwork")
    if os.path.exists(classwork_file):
        try:
            classwork_df = pd.read_csv(classwork_file)
            student_classwork = classwork_df[
                (classwork_df['Name'].str.lower() == student_name.lower()) & 
                (classwork_df['Matric'].str.lower() == student_matric.lower())
            ]
            summary["classwork_count"] = len(student_classwork)
            for _, row in student_classwork.iterrows():
                summary["recent_activity"].append(f"📝 Submitted classwork for {row['Week']}")
        except:
            pass
    
    # Count file submissions
    submission_types = ["assignment", "drawing", "seminar"]
    for sub_type in submission_types:
        upload_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, sub_type)
        if os.path.exists(upload_dir):
            files = os.listdir(upload_dir)
            student_files = [f for f in files if student_name.lower() in f.lower() and student_matric.lower() in f.lower()]
            count = len(student_files)
            
            if sub_type == "assignment":
                summary["assignment_count"] = count
            elif sub_type == "drawing":
                summary["drawing_count"] = count
            elif sub_type == "seminar":
                summary["seminar_count"] = count
                
            for file in student_files:
                # Extract week from filename
                week_match = re.search(r'Week_?\s?(\d+)', file, re.IGNORECASE)
                week = week_match.group(0) if week_match else "Unknown Week"
                summary["recent_activity"].append(f"📎 Submitted {sub_type} for {week}")
    
    # Sort recent activity by timestamp (newest first)
    summary["recent_activity"] = summary["recent_activity"][-10:]  # Keep last 10 activities
    
    return summary

# ===============================================================
# 🎥 VIDEO MANAGEMENT
# ===============================================================

def get_video_files(course_code):
    """Get list of video files for a course"""
    video_dir = get_persistent_path("video", course_code)
    
    if not os.path.exists(video_dir):
        return []
    
    video_files = sorted([f for f in os.listdir(video_dir) 
                         if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])
    return video_files

def upload_video(course_code, uploaded_video):
    """Upload video to persistent storage"""
    try:
        video_dir = get_persistent_path("video", course_code)
        os.makedirs(video_dir, exist_ok=True)
        
        safe_name = "".join(c for c in uploaded_video.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        
        # Handle duplicates
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
# 🌐 GLOBAL ACTIVITY FUNCTIONS
# ===============================================================

def get_global_attendance_summary():
    """Get attendance summary across all courses"""
    courses = ["MCB221", "BCH201", "BIO203", "BIO113", "BIO306"]
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
            "Average per Week": round(total_students / max(weeks_with_data, 1), 1) if weeks_with_data > 0 else 0
        })
    
    return pd.DataFrame(summary_data)

def get_global_submissions_summary():
    """Get submissions summary across all courses"""
    courses = ["MCB221", "BCH201", "BIO203", "BIO113", "BIO306"]
    submission_types = ["assignment", "drawing", "seminar"]
    summary_data = []
    
    for course in courses:
        course_data = {"Course": course}
        total_files = 0
        
        for sub_type in submission_types:
            upload_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course, sub_type)
            count = 0
            if os.path.exists(upload_dir):
                count = len([f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))])
            course_data[sub_type.capitalize()] = count
            total_files += count
        
        course_data["Total Files"] = total_files
        summary_data.append(course_data)
    
    return pd.DataFrame(summary_data)

# ===============================================================
# 📊 ATTENDANCE VIEWING FUNCTIONS
# ===============================================================

def view_attendance_records(course_code, week):
    """Display attendance records for a specific course and week"""
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
        
        # Display the dataframe
        st.dataframe(df, use_container_width=True)
        
        # Show statistics
        total_students = len(df)
        st.info(f"**Total students attended:** {total_students}")
        
        # Provide download option
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"attendance_{course_code}_{week_key}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Error loading attendance records: {e}")

def show_attendance_summary(course_code):
    """Show summary of attendance across all weeks"""
    try:
        summary_data = []
        
        for week_num in range(1, 16):
            week = f"Week {week_num}"
            week_key = week.replace(" ", "")
            attendance_file = os.path.join(get_persistent_path("attendance"), f"attendance_{course_code}_{week_key}.csv")
            
            if os.path.exists(attendance_file):
                df = pd.read_csv(attendance_file)
                student_count = len(df)
                
                # Get attendance status
                status_data = get_attendance_status(course_code, week)
                is_open = status_data.get("is_open", False)
                status = "🟢 OPEN" if is_open else "🔴 CLOSED"
                
                summary_data.append({
                    "Week": week,
                    "Students Attended": student_count,
                    "Status": status
                })
            else:
                status_data = get_attendance_status(course_code, week)
                is_open = status_data.get("is_open", False)
                status = "🟢 OPEN" if is_open else "🔴 CLOSED"
                
                summary_data.append({
                    "Week": week,
                    "Students Attended": 0,
                    "Status": status
                })
        
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
            st.dataframe(summary_df, use_container_width=True)
            
            # Calculate totals
            total_students = summary_df["Students Attended"].sum()
            weeks_with_attendance = len(summary_df[summary_df["Students Attended"] > 0])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Attendance Records", total_students)
            with col2:
                st.metric("Weeks with Attendance", weeks_with_attendance)
        else:
            st.info("No attendance records found for any week.")
            
    except Exception as e:
        st.error(f"Error generating attendance summary: {e}")

def view_student_attendance_details(course_code, week):
    """Display detailed student attendance with search and filtering"""
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
        
        # Display basic stats
        total_students = len(df)
        st.info(f"**Total students attended:** {total_students}")
        
        # Search and filter functionality
        col1, col2 = st.columns(2)
        
        with col1:
            search_name = st.text_input("🔍 Search by Name", placeholder="Enter student name...")
        
        with col2:
            search_matric = st.text_input("🔍 Search by Matric", placeholder="Enter matric number...")
        
        # Filter dataframe based on search
        filtered_df = df.copy()
        
        if search_name:
            filtered_df = filtered_df[filtered_df['Name'].str.contains(search_name, case=False, na=False)]
        
        if search_matric:
            filtered_df = filtered_df[filtered_df['Matric'].str.contains(search_matric, case=False, na=False)]
        
        # Display the filtered results
        if not filtered_df.empty:
            st.write(f"**Showing {len(filtered_df)} students:**")
            
            # Display in a nice table format
            for idx, row in filtered_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.write(f"**{row['Name']}**")
                    with col2:
                        st.write(f"`{row['Matric']}`")
                    with col3:
                        st.write(f"_{row['Timestamp']}_")
                    st.divider()
            
            # Also show as dataframe for bulk operations
            with st.expander("📋 View as Data Table"):
                st.dataframe(filtered_df[['Name', 'Matric', 'Timestamp']], use_container_width=True)
                
        else:
            st.warning("No students found matching your search criteria.")
        
        # Download options
        st.subheader("📥 Download Options")
        col1, col2 = st.columns(2)
        
        with col1:
            # Download filtered results
            csv_filtered = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Filtered Results (CSV)",
                data=csv_filtered,
                file_name=f"attendance_{course_code}_{week_key}_filtered.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            # Download all results
            csv_all = df.to_csv(index=False)
            st.download_button(
                label="📥 Download All Records (CSV)",
                data=csv_all,
                file_name=f"attendance_{course_code}_{week_key}_all.csv",
                mime="text/csv",
                use_container_width=True
            )
        
    except Exception as e:
        st.error(f"Error loading student attendance details: {e}")

def view_all_students_attendance(course_code):
    """View attendance for all students across all weeks"""
    try:
        st.subheader(f"📊 Complete Student Attendance - {course_code}")
        
        # Collect data from all weeks
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
        
        # Combine all data
        combined_df = pd.concat(all_attendance, ignore_index=True)
        
        # Search functionality
        col1, col2 = st.columns(2)
        with col1:
            search_student = st.text_input("🔍 Search Student", placeholder="Name or Matric...", key="search_all")
        
        with col2:
            selected_week = st.selectbox(
                "Filter by Week", 
                ["All Weeks"] + [f"Week {i}" for i in range(1, 16)],
                key="filter_week"
            )
        
        # Filter data
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
        
        # Display summary statistics
        st.subheader("📈 Summary")
        total_records = len(filtered_combined)
        unique_students = filtered_combined['Matric'].nunique()
        weeks_covered = filtered_combined['Week'].nunique()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Attendance Records", total_records)
        with col2:
            st.metric("Unique Students", unique_students)
        with col3:
            st.metric("Weeks Covered", weeks_covered)
        
        # Student-wise attendance count
        st.subheader("👥 Student Attendance Summary")
        student_summary = filtered_combined.groupby(['Name', 'Matric']).size().reset_index(name='Attendance Count')
        student_summary = student_summary.sort_values('Attendance Count', ascending=False)
        
        st.dataframe(student_summary, use_container_width=True)
        
        # Detailed records
        st.subheader("📋 Detailed Records")
        st.dataframe(filtered_combined[['Name', 'Matric', 'Week', 'Timestamp']], use_container_width=True)
        
        # Download options
        st.subheader("📥 Download Reports")
        col1, col2 = st.columns(2)
        
        with col1:
            csv_detailed = filtered_combined.to_csv(index=False)
            st.download_button(
                label="📥 Download Detailed Records",
                data=csv_detailed,
                file_name=f"attendance_{course_code}_detailed.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            csv_summary = student_summary.to_csv(index=False)
            st.download_button(
                label="📥 Download Student Summary",
                data=csv_summary,
                file_name=f"attendance_{course_code}_student_summary.csv",
                mime="text/csv",
                use_container_width=True
            )
        
    except Exception as e:
        st.error(f"Error loading complete attendance: {e}")

# ===============================================================
# 🧩 CLASSWORK VIEWING FUNCTIONS
# ===============================================================

def view_classwork_submissions(course_code, week):
    """View classwork submissions for a specific week"""
    try:
        classwork_file = get_file(course_code, "classwork")
        
        if not os.path.exists(classwork_file):
            st.warning(f"No classwork submissions found for {course_code} - {week}")
            return
        
        df = pd.read_csv(classwork_file)
        
        if df.empty:
            st.warning(f"No classwork submissions found for {course_code} - {week}")
            return
        
        # Filter by week
        week_submissions = df[df['Week'] == week]
        
        if week_submissions.empty:
            st.warning(f"No classwork submissions found for {course_code} - {week}")
            return
        
        st.success(f"📝 Classwork Submissions for {course_code} - {week}")
        
        # Display submissions
        for idx, row in week_submissions.iterrows():
            with st.expander(f"🧩 {row['Name']} ({row['Matric']}) - {row['Timestamp']}", expanded=False):
                st.write(f"**Student:** {row['Name']} ({row['Matric']})")
                st.write(f"**Submitted:** {row['Timestamp']}")
                
                # Parse and display answers
                try:
                    answers = json.loads(row['Answers'])
                    st.write("**Answers:**")
                    for i, answer in enumerate(answers):
                        if answer.strip():  # Only show non-empty answers
                            st.write(f"**Q{i+1}:** {answer}")
                            st.divider()
                except:
                    st.write("**Answers:** Unable to parse answers")
        
        # Download option
        csv_data = week_submissions.to_csv(index=False)
        st.download_button(
            label="📥 Download Classwork Submissions",
            data=csv_data,
            file_name=f"classwork_{course_code}_{week.replace(' ', '')}.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"Error loading classwork submissions: {e}")

def view_all_classwork_submissions(course_code):
    """View all classwork submissions with filtering options"""
    try:
        classwork_file = get_file(course_code, "classwork")
        
        if not os.path.exists(classwork_file):
            st.info("No classwork submissions found yet.")
            return
        
        df = pd.read_csv(classwork_file)
        
        if df.empty:
            st.info("No classwork submissions found yet.")
            return
        
        st.subheader(f"📚 All Classwork Submissions - {course_code}")
        
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            selected_week = st.selectbox(
                "Filter by Week",
                ["All Weeks"] + sorted(df['Week'].unique()),
                key="classwork_week_filter"
            )
        
        with col2:
            search_student = st.text_input("🔍 Search Student", placeholder="Name or Matric...", key="classwork_search")
        
        # Filter data
        filtered_df = df.copy()
        
        if selected_week != "All Weeks":
            filtered_df = filtered_df[filtered_df['Week'] == selected_week]
        
        if search_student:
            filtered_df = filtered_df[
                filtered_df['Name'].str.contains(search_student, case=False, na=False) |
                filtered_df['Matric'].str.contains(search_student, case=False, na=False)
            ]
        
        if filtered_df.empty:
            st.warning("No classwork submissions found matching your criteria.")
            return
        
        # Display summary
        st.subheader("📊 Summary")
        total_submissions = len(filtered_df)
        unique_students = filtered_df['Matric'].nunique()
        weeks_covered = filtered_df['Week'].nunique()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Submissions", total_submissions)
        with col2:
            st.metric("Unique Students", unique_students)
        with col3:
            st.metric("Weeks Covered", weeks_covered)
        
        # Student submission count
        st.subheader("👥 Student Submission Summary")
        student_summary = filtered_df.groupby(['Name', 'Matric']).size().reset_index(name='Submissions Count')
        student_summary = student_summary.sort_values('Submissions Count', ascending=False)
        
        st.dataframe(student_summary, use_container_width=True)
        
        # Detailed view
        st.subheader("📋 Detailed Submissions")
        
        for week in sorted(filtered_df['Week'].unique()):
            week_data = filtered_df[filtered_df['Week'] == week]
            with st.expander(f"📅 {week} - {len(week_data)} submissions", expanded=False):
                for idx, row in week_data.iterrows():
                    with st.container():
                        st.write(f"**{row['Name']} ({row['Matric']})** - {row['Timestamp']}")
                        
                        try:
                            answers = json.loads(row['Answers'])
                            for i, answer in enumerate(answers):
                                if answer.strip():
                                    st.write(f"Q{i+1}: {answer}")
                            st.divider()
                        except:
                            st.write("Unable to display answers")
                            st.divider()
        
        # Download options
        st.subheader("📥 Download Options")
        col1, col2 = st.columns(2)
        
        with col1:
            csv_detailed = filtered_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Detailed Records",
                data=csv_detailed,
                file_name=f"classwork_{course_code}_detailed.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            csv_summary = student_summary.to_csv(index=False)
            st.download_button(
                label="📥 Download Student Summary",
                data=csv_summary,
                file_name=f"classwork_{course_code}_student_summary.csv",
                mime="text/csv",
                use_container_width=True
            )
        
    except Exception as e:
        st.error(f"Error loading classwork submissions: {e}")


# ===============================================================
# 🧩 AUTOMATED CLASSWORK SECTION WITH OPEN/CLOSE CONTROL
# ===============================================================

def display_mcq_questions(questions):
    """Display MCQ questions and collect answers"""
    answers = []
    for i, question in enumerate(questions):
        st.write(f"**Q{i+1}: {question['question']}**")
        
        if question['type'] == 'mcq':
            # Display multiple choice options
            options = question['options']
            selected_option = st.radio(
                f"Select your answer for Q{i+1}:",
                options=list(options.keys()),
                format_func=lambda x: f"{x}: {options[x]}",
                key=f"mcq_{i}"
            )
            answers.append(selected_option)
        else:  # gap_fill
            # Display text input for gap filling
            answer = st.text_input(
                f"Your answer for Q{i+1}:",
                placeholder="Type your answer here...",
                key=f"gap_{i}"
            )
            answers.append(answer)
    
    return answers

def auto_grade_mcq_submission(questions, answers):
    """Auto-grade MCQ submissions"""
    correct = 0
    total = len(questions)
    
    for i, question in enumerate(questions):
        if i < len(answers):
            user_answer = answers[i].strip()
            correct_answer = question['correct_answer']
            
            if question['type'] == 'mcq':
                # For MCQ, check if selected option matches correct answer
                if user_answer.upper() == correct_answer.upper():
                    correct += 1
            else:
                # For gap filling, check if answer matches any of the correct options
                correct_options = [opt.strip() for opt in correct_answer.split('|')]
                if user_answer.lower() in [opt.lower() for opt in correct_options]:
                    correct += 1
    
    score = round((correct / total) * 100, 1) if total > 0 else 0
    return score, correct, total

def save_mcq_submission(course_code, week, student_name, student_matric, answers, score):
    """Save MCQ submission to file"""
    try:
        classwork_file = get_file(course_code, "classwork")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(classwork_file), exist_ok=True)
        
        # Prepare submission data
        submission = {
            'Name': student_name,
            'Matric': student_matric,
            'Week': week,
            'Type': 'MCQ',
            'Answers': json.dumps(answers),
            'Score': score,
            'Timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Load existing data or create new DataFrame
        if os.path.exists(classwork_file):
            df = pd.read_csv(classwork_file)
        else:
            df = pd.DataFrame(columns=['Name', 'Matric', 'Week', 'Type', 'Answers', 'Score', 'Timestamp'])
        
        # Remove any previous submission by this student for this week
        mask = (
            (df['Name'] == student_name) & 
            (df['Matric'] == student_matric) & 
            (df['Week'] == week) &
            (df['Type'] == 'MCQ')
        )
        df = df[~mask]
        
        # Add new submission
        df = pd.concat([df, pd.DataFrame([submission])], ignore_index=True)
        
        # Save to file
        df.to_csv(classwork_file, index=False)
        return True
        
    except Exception as e:
        st.error(f"Error saving submission: {e}")
        return False

# ===============================================================
# 🔧 HELPER FUNCTIONS FOR CLASSWORK SCORING
# ===============================================================

def update_classwork_score(course_code, student_name, student_matric, week, score):
    """Update classwork score in the main scores file"""
    try:
        scores_file = get_file(course_code, "scores")
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(scores_file), exist_ok=True)
        
        # Load existing scores or create new DataFrame
        if os.path.exists(scores_file):
            scores_df = pd.read_csv(scores_file)
        else:
            scores_df = pd.DataFrame(columns=[
                "StudentName", "MatricNo", "Week", "Assignment", "Test", 
                "Practical", "Exam", "Classwork", "Total", "Grade"
            ])
        
        # Find existing entry for this student and week
        mask = (
            (scores_df["StudentName"].astype(str).str.strip().str.lower() == student_name.lower()) &
            (scores_df["MatricNo"].astype(str).str.strip().str.lower() == student_matric.lower()) &
            (scores_df["Week"].astype(str).str.strip().str.lower() == week.lower())
        )
        
        if mask.any():
            # Update existing entry
            scores_df.loc[mask, "Classwork"] = score
            # Recalculate total for weekly entries (not Exam)
            if week != "Exam":
                assignment_score = scores_df.loc[mask, "Assignment"].iloc[0] if "Assignment" in scores_df.columns else 0
                test_score = scores_df.loc[mask, "Test"].iloc[0] if "Test" in scores_df.columns else 0
                practical_score = scores_df.loc[mask, "Practical"].iloc[0] if "Practical" in scores_df.columns else 0
                
                weekly_total = round(
                    assignment_score * 0.08 + 
                    test_score * 0.08 + 
                    practical_score * 0.05 + 
                    score * 0.09, 
                    1
                )
                scores_df.loc[mask, "Total"] = weekly_total
                scores_df.loc[mask, "Grade"] = compute_grade(weekly_total)
        else:
            # Create new entry for weekly classwork
            if week != "Exam":
                weekly_total = round(score * 0.09, 1)  # Only classwork contribution
                new_row = {
                    "StudentName": student_name.title(),
                    "MatricNo": student_matric.upper(),
                    "Week": week,
                    "Assignment": 0,
                    "Test": 0,
                    "Practical": 0,
                    "Exam": 0,
                    "Classwork": score,
                    "Total": weekly_total,
                    "Grade": compute_grade(weekly_total)
                }
                scores_df = pd.concat([scores_df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Save updated scores
        scores_df.to_csv(scores_file, index=False)
        return True
        
    except Exception as e:
        st.error(f"Error updating classwork score: {e}")
        return False


def compute_grade(score):
    """Compute grade based on score percentage"""
    if score >= 70:
        return "A"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C"
    elif score >= 45:
        return "D"
    elif score >= 40:
        return "E"
    else:
        return "F"

def display_weekly_lecture_materials(course_code, week, student_name, student_matric):
    """Display lecture materials for a specific week"""
    try:
        lectures_df = load_lectures(course_code)
        
        if lectures_df.empty:
            st.info(f"No lecture materials available for {week} yet.")
            return
        
        # Find the row for the selected week
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
            
            # Assignment section
            if row["Assignment"] and str(row["Assignment"]).strip():
                st.markdown(f"**Assignment:** {row['Assignment']}")
        
        with col2:
            # PDF access
            pdf_file = row.get("PDF_File", "")
            if not isinstance(pdf_file, str):
                pdf_file = str(pdf_file) if pdf_file is not None else ""
            pdf_file = pdf_file.strip()
            
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
                    st.error(f"⚠️ Error loading PDF: {e}")
            else:
                st.info("No PDF available")
    
    except Exception as e:
        st.error(f"Error loading lecture materials: {e}")
# ===============================================================
# 📊 FINAL GRADE CALCULATION FUNCTIONS
# ===============================================================

def calculate_final_grade(student_scores):
    """Calculate final grade for a student based on all scores"""
    try:
        if student_scores.empty:
            return None, None, 0, 0, 0, 0, 0
        
        # Separate weekly scores and exam score
        weekly_scores = student_scores[student_scores['Week'] != 'Exam']
        exam_scores = student_scores[student_scores['Week'] == 'Exam']
        
        # Calculate averages for continuous assessment
        assignment_avg = weekly_scores['Assignment'].mean() if not weekly_scores.empty and 'Assignment' in weekly_scores.columns else 0
        test_avg = weekly_scores['Test'].mean() if not weekly_scores.empty and 'Test' in weekly_scores.columns else 0
        practical_avg = weekly_scores['Practical'].mean() if not weekly_scores.empty and 'Practical' in weekly_scores.columns else 0
        classwork_avg = weekly_scores['Classwork'].mean() if not weekly_scores.empty and 'Classwork' in weekly_scores.columns else 0
        
        # Get exam score
        exam_score = exam_scores['Exam'].iloc[0] if not exam_scores.empty and 'Exam' in exam_scores.columns else 0
        
        # Calculate final total (CA 30% + Exam 70%)
        ca_total = (
            (assignment_avg * 0.08) + 
            (test_avg * 0.08) + 
            (practical_avg * 0.05) + 
            (classwork_avg * 0.09)
        )
        exam_contribution = exam_score * 0.70
        final_total = ca_total + exam_contribution
        
        # Compute final grade
        final_grade = compute_grade(final_total)
        
        return final_total, final_grade, assignment_avg, test_avg, practical_avg, classwork_avg, exam_score
        
    except Exception as e:
        st.error(f"Error calculating final grade: {e}")
        return None, None, 0, 0, 0, 0, 0

def display_classwork_section(course_code, week, student_name, student_matric):
    """Display classwork section for the selected week - PREVENTS DOUBLE SUBMISSION"""
    try:
        st.markdown("---")
        st.subheader(f"🧩 Classwork - {week}")
        
        # Check for automated MCQ questions for this week
        mcq_questions = load_mcq_questions(course_code, week)
        
        if mcq_questions and len(mcq_questions) > 0:
            st.markdown("### 🧩 Automated Classwork Questions")
            
            # Check if classwork is open
            classwork_status = is_classwork_open(course_code, week)
            close_classwork_after_20min(course_code, week)  # Auto-close check

            # Display classwork status
            if classwork_status:
                st.success("✅ Classwork is OPEN - You can submit your answers")
                
                # Show auto-close countdown if open
                current_status = get_classwork_status(course_code, week)
                if current_status.get("is_open", False) and current_status.get("open_time"):
                    try:
                        open_time = datetime.fromisoformat(current_status["open_time"])
                        elapsed = (datetime.now() - open_time).total_seconds()
                        remaining = max(0, 1200 - elapsed)  # 20 minutes
                        
                        if remaining > 0:
                            mins = int(remaining // 60)
                            secs = int(remaining % 60)
                            st.info(f"⏳ Classwork will auto-close in {mins:02d}:{secs:02d}")
                    except:
                        pass
            else:
                st.warning("🚫 Classwork is CLOSED - You cannot submit answers at this time")

            # Check if already submitted - STRICTER CHECK
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

            # PREVENT DOUBLE SUBMISSION - Show different UI if already submitted
            if already_submitted:
                st.warning(f"⚠️ You have already submitted this classwork. Your score: **{previous_score}%**")
                st.info("📝 You cannot submit again for this week. If you believe this is an error, contact your lecturer.")
                
                # Show submission details
                with st.expander("📋 View Your Submission", expanded=False):
                    st.write(f"**Student:** {submission_data['Name']} ({submission_data['Matric']})")
                    st.write(f"**Week:** {submission_data['Week']}")
                    st.write(f"**Score:** {submission_data['Score']}%")
                    st.write(f"**Submitted:** {submission_data['Timestamp']}")
                    
                    # Show answers if available
                    try:
                        answers = json.loads(submission_data['Answers'])
                        st.write("**Your Answers:**")
                        for i, (question, answer) in enumerate(zip(mcq_questions, answers)):
                            st.write(f"**Q{i+1}:** {question['question']}")
                            st.write(f"**Your Answer:** {answer}")
                            
                            # Show correct answer for learning purposes
                            correct_answer = question['correct_answer']
                            if question['type'] == 'mcq':
                                st.write(f"**Correct Answer:** {correct_answer} - {question['options'].get(correct_answer, '')}")
                            else:
                                st.write(f"**Correct Answer(s):** {correct_answer}")
                            st.markdown("---")
                    except:
                        st.write("Unable to display answer details")
            
            elif classwork_status:
                with st.form(f"mcq_form_{week.replace(' ', '_')}"):
                    st.write("**Answer the following questions:**")
                    answers = display_mcq_questions(mcq_questions)
                    
                    submit_mcq = st.form_submit_button(
                        "🚀 Submit Classwork Answers", 
                        use_container_width=True,
                        # Disable button if already submitted (extra safety)
                        disabled=already_submitted
                    )

                    if submit_mcq:
                        if not student_name or not student_matric:
                            st.error("❌ Please set your identity first using the form above.")
                        elif any(not str(answer).strip() for answer in answers):
                            st.error("❌ Please answer all questions before submitting.")
                        else:
                            # DOUBLE CHECK: Ensure no submission exists (race condition protection)
                            if os.path.exists(classwork_file):
                                df_check = pd.read_csv(classwork_file)
                                existing_check = df_check[
                                    (df_check['Name'].astype(str).str.strip().str.lower() == student_name.lower()) & 
                                    (df_check['Matric'].astype(str).str.strip().str.lower() == student_matric.lower()) & 
                                    (df_check['Week'].astype(str).str.strip().str.lower() == week.lower()) &
                                    (df_check['Type'] == 'MCQ')
                                ]
                                if not existing_check.empty:
                                    st.error("❌ Submission already exists! You cannot submit twice.")
                                    return
                            
                            # Auto-grade submission
                            score, correct, total = auto_grade_mcq_submission(mcq_questions, answers)
                            
                            # Save submission
                            success = save_mcq_submission(course_code, week, student_name, student_matric, answers, score)
                            if success:
                                # Update classwork score in main scores file
                                update_classwork_score(course_code, student_name, student_matric, week, score)
                                
                                st.balloons()
                                st.success(f"🎉 Classwork submitted successfully! Score: **{score}%** ({correct}/{total} correct)")
                                st.info("📝 You cannot submit again for this week.")
                                st.rerun()
                            else:
                                st.error("❌ Failed to save your submission. Please try again.")
            else:
                st.info("⏳ Classwork for this week is currently closed. Please wait for your lecturer to open it.")
                
                # Show questions in read-only mode when closed
                st.markdown("---")
                st.write("**Questions Preview (Read-only):**")
                for i, question in enumerate(mcq_questions):
                    st.write(f"**Q{i+1}: {question['question']}**")
                    if question['type'] == 'mcq':
                        st.write("Options:")
                        for opt, text in question['options'].items():
                            st.write(f"- {opt}: {text}")
                    st.write("")  # Add spacing
        else:
            st.info(f"No automated classwork assigned for {week} yet.")
            st.write("💡 *If you believe there should be classwork, please ask your lecturer to check the Admin dashboard.*")
    
    except Exception as e:
        st.error(f"Error displaying classwork section: {e}")

def show_student_course_description(course_code, course_name):
    """Student view of course description"""
    st.header(f"📝 {course_name} - Course Information")
    
    # Load course description
    course_info = load_course_description(course_code)
    
    if not course_info:
        st.info("📋 Course description is being prepared by your lecturer. Check back soon!")
        return
    
    # Display the course description using the same preview function
    display_course_description_preview(course_info)
# ===============================================================
# 🎓 STUDENT VIEW - FIXED VERSION
# ===============================================================

def student_view(course_code, course_name):
    """Student dashboard view with persistent storage and scores viewing"""
    try:
        ensure_directories()
        
        st.title(f"🎓 Student Dashboard - {course_code, course_name}")
        
        # Initialize student identity
        if "student_identity" not in st.session_state:
            st.session_state.student_identity = {"name": "", "matric": ""}
        
        student_name = st.session_state.student_identity["name"]
        student_matric = st.session_state.student_identity["matric"]
        
        # Student Identity Section
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
                    st.success("✅ Identity saved successfully!")
                    st.rerun()
                else:
                    st.error("❌ Please enter both name and matric number.")
        
        if student_name and student_matric:
            st.success(f"**Logged in as:** {student_name} ({student_matric})")
        else:
            st.warning("⚠️ Please set your identity above to view your scores and submit work.")
            return
         # Student authentication
        st.subheader("🔐 Student Access")
        student_name = st.text_input("Enter Your Full Name", key=f"student_name_{course_code}")
        matric_number = st.text_input("Enter Your Matric Number", key=f"matric_{course_code}")
        
        if not student_name or not matric_number:
            st.warning("Please enter your name and matric number to continue.")
            return   
         # Store student info in session state
        st.session_state["student_name"] = student_name
        st.session_state["matric_number"] = matric_number
        st.session_state["course_code"] = course_code
        st.session_state["course_name"] = course_name
        
        st.success(f"✅ Welcome, {student_name} ({matric_number})!")
        
        # Week selection in sidebar for consistent navigation
        st.sidebar.header("📅 Week Navigation")
        selected_week = st.sidebar.selectbox(
            "Select Week", 
            [f"Week {i}" for i in range(1, 16)],
            key="student_main_week_selector"
        )
        
        # Create tabs for different sections
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
             "📝 About Course",  # NEW TAB ADDED
            "📖 Lecture & Classwork", 
            "🎥 Video Lectures", 
            "🕒 Attendance",
            "📤 Submissions",
            "📊 My Progress"
        ])

        with tab1:
            # ===============================================================
            # 📝 COURSE DESCRIPTION (STUDENT VIEW)
            # ===============================================================
            show_student_course_description(course_code, course_name)
            
        with tab2:
            # ===============================================================
            # 📖 LECTURE MATERIALS & CLASSWORK FOR SELECTED WEEK
            # ===============================================================
            st.header(f"📚 {course_code} - {selected_week}")
            
            # Display lecture materials for selected week
            display_weekly_lecture_materials(course_code, selected_week, student_name, student_matric)
            
            # Display classwork for selected week
            display_classwork_section(course_code, selected_week, student_name, student_matric)
        
        with tab3:
            # ===============================================================
            # 🎥 VIDEO LECTURES SECTION
            # ===============================================================
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
                                st.error(f"⚠️ Cannot play this video: {str(e)}")
                                st.info("The video format might not be supported in your browser. Try downloading it instead.")
                        
                        with col2:
                            try:
                                with open(video_path, "rb") as vid_file:
                                    st.download_button(
                                        label="📥 Download Video",
                                        data=vid_file,
                                        file_name=video,
                                        mime="video/mp4",
                                        key=f"student_download_{i}",
                                        use_container_width=True
                                    )
                            except Exception as e:
                                st.error("Download unavailable")
            else:
                st.info("No video lectures available yet. Check back later for uploaded content.")

        with tab4:
            # ===============================================================
            # 🕒 ATTENDANCE SECTION
            # ===============================================================
            st.header("🕒 Mark Attendance")
            
            with st.form(f"{course_code}_attendance_form"):
                # Pre-fill with session state values
                name = st.text_input("Full Name", value=student_name, key=f"{course_code}_student_name")
                matric = st.text_input("Matric Number", value=student_matric, key=f"{course_code}_student_matric")
                
                # Use the selected week from sidebar
                st.write(f"**Selected Week:** {selected_week}")
                
                submit_attendance = st.form_submit_button("✅ Mark Attendance", use_container_width=True)

            if submit_attendance:
                if not name.strip() or not matric.strip():
                    st.warning("Please enter your full name and matric number.")
                else:
                    # Save identity to session state
                    st.session_state.student_identity = {"name": name.strip(), "matric": matric.strip()}
                    student_name = name.strip()
                    student_matric = matric.strip()
                    
                    # Check if attendance is open
                    status_data = get_attendance_status(course_code, selected_week)
                    is_attendance_open = status_data.get("is_open", False)
                    
                    if not is_attendance_open:
                        st.error("🚫 Attendance for this course is currently closed. Please wait for your lecturer to open it.")
                    elif has_marked_attendance(course_code, selected_week, student_name, student_matric):
                        st.info("✅ Attendance already marked for this week.")
                    else:
                        ok = mark_attendance_entry(course_code, student_name, student_matric, selected_week)
                        if ok:
                            st.session_state["attended_week"] = str(selected_week)
                            st.success(f"🎉 Attendance recorded successfully for {course_code} - {selected_week}.")
                            st.balloons()
                        else:
                            st.error("⚠️ Failed to record attendance. Try again later.")

        with tab5:
            # ===============================================================
            # 📤 STUDENT SUBMISSIONS SECTION
            # ===============================================================
            st.header("📤 Submit Assignments")
            
            # Assignment submission
            st.subheader("📝 Assignment Submission")
            with st.form("assignment_upload_form"):
                st.write(f"**Selected Week:** {selected_week}")
                assignment_file = st.file_uploader("Upload Assignment File", type=["pdf", "doc", "docx", "txt", "zip"], key="assignment_upload")
                submit_assignment = st.form_submit_button("📤 Submit Assignment", use_container_width=True)
                
                if submit_assignment:
                    if not assignment_file:
                        st.error("❌ Please select a file to upload.")
                    else:
                        existing_check = check_existing_submission(course_code, student_matric, selected_week, "assignment")
                        if not existing_check.empty:
                            st.error("❌ Submission already exists! You cannot submit twice.")
                        else:
                            file_path = save_file(course_code, student_name, selected_week, assignment_file, "assignment")
                            if file_path:
                                log_submission(course_code, student_matric, student_name, selected_week, assignment_file.name, "assignment")
                                st.success(f"✅ Assignment submitted successfully: {assignment_file.name}")
                           

            # Drawing submission
            st.subheader("🎨 Drawing Submission")
            with st.form("drawing_upload_form"):
                st.write(f"**Selected Week:** {selected_week}")
                drawing_file = st.file_uploader("Upload Drawing File", type=["jpg", "jpeg", "png", "gif", "pdf"], key="drawing_upload")
                submit_drawing = st.form_submit_button("📤 Submit Drawing", use_container_width=True)
                
                if submit_drawing:
                    if not drawing_file:
                        st.error("❌ Please select a file to upload.")
                    else:
                        existing_check = check_existing_submission(course_code, student_matric, selected_week, "drawing")
                        if not existing_check.empty:
                            st.error("❌ Submission already exists! You cannot submit twice.")
                        else:
                            file_path = save_file(course_code, student_name, selected_week, drawing_file, "drawing")
                            if file_path:
                                log_submission(course_code, student_matric, student_name, selected_week, drawing_file.name, "drawing")
                                st.success(f"✅ Drawing submitted successfully: {drawing_file.name}")
                            

            # Seminar submission
            st.subheader("📊 Seminar Submission")
            with st.form("seminar_upload_form"):
                st.write(f"**Selected Week:** {selected_week}")
                seminar_file = st.file_uploader("Upload Seminar File", type=["pdf", "ppt", "pptx", "doc", "docx"], key="seminar_upload")
                submit_seminar = st.form_submit_button("📤 Submit Seminar", use_container_width=True)
                
                if submit_seminar:
                    if not seminar_file:
                        st.error("❌ Please select a file to upload.")
                    else:
                        existing_check = check_existing_submission(course_code, student_matric, selected_week, "seminar")
                        if not existing_check.empty:
                            st.error("❌ Submission already exists! You cannot submit twice.")
                        else:
                            file_path = save_file(course_code, student_name, selected_week, seminar_file, "seminar")
                        
                            if file_path:
                                log_submission(course_code, student_matric, student_name, selected_week, seminar_file.name, "seminar")
                                st.success(f"✅ Seminar submitted successfully: {seminar_file.name}")
                   

        with tab6:
            # ===============================================================
            # 📊 SCORES VIEWING SECTION - FIXED VERSION
            # ===============================================================
            st.header("📊 My Scores & Grades")
            
            def load_student_scores(course_code, student_name, student_matric):
                """Load scores for specific student"""
                scores_file = get_file(course_code, "scores")
                
                if not os.path.exists(scores_file):
                    return pd.DataFrame()
                
                try:
                    scores_df = pd.read_csv(scores_file)
                    
                    # Check if required columns exist
                    if "StudentName" not in scores_df.columns or "MatricNo" not in scores_df.columns:
                        return pd.DataFrame()
                        
                    # Filter for current student
                    student_scores = scores_df[
                        (scores_df["StudentName"].astype(str).str.strip().str.lower() == student_name.lower()) &
                        (scores_df["MatricNo"].astype(str).str.strip().str.lower() == student_matric.lower())
                    ]
                    return student_scores
                except Exception as e:
                    st.error(f"Error loading scores: {e}")
                    return pd.DataFrame()

            student_scores = load_student_scores(course_code, student_name, student_matric)
            
            if not student_scores.empty:
                # Display weekly scores
                st.subheader("📋 Weekly Scores")
                display_columns = ["Week", "Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"]
                # Only show columns that exist in the dataframe
                available_columns = [col for col in display_columns if col in student_scores.columns]
                display_df = student_scores[available_columns].copy()
                
                # Format percentages
                for col in ["Assignment", "Test", "Practical", "Exam", "Classwork", "Total"]:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) and x != 0 else "N/A")
                
                st.dataframe(display_df, use_container_width=True)
                
                # FINAL GRADE CALCULATION AFTER 15 WEEKS + EXAM
                st.subheader("🎓 Final Grade Calculation")
                
                # Use the fixed calculate_final_grade function
                result = calculate_final_grade(student_scores)
                
                if result[0] is not None:  # Check if final_total is not None
                    final_total, final_grade, assignment_avg, test_avg, practical_avg, classwork_avg, exam_score = result
                    
                    st.info("""
                    **Grading Breakdown:**
                    - Continuous Assessment (15 weeks average): 30%
                      - Assignment (8%): Average of 15 weeks
                      - Test (8%): Average of 15 weeks  
                      - Practical (5%): Average of 15 weeks
                      - Classwork (9%): Average of 15 weeks
                    - Exam (After 15 weeks): 70%
                    """)
                    
                    # Display the calculation breakdown
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("📝 Assignment Average", f"{assignment_avg:.1f}%")
                        st.metric("📊 Test Average", f"{test_avg:.1f}%")
                        st.metric("🔬 Practical Average", f"{practical_avg:.1f}%")
                        st.metric("🧩 Classwork Average", f"{classwork_avg:.1f}%")
                    
                    with col2:
                        st.metric("📚 Exam Score", f"{exam_score:.1f}%")
                        st.metric("📈 Continuous Assessment (30%)", f"{(assignment_avg*0.08 + test_avg*0.08 + practical_avg*0.05 + classwork_avg*0.09):.1f}%")
                        st.metric("🎯 Exam Contribution (70%)", f"{(exam_score * 0.70):.1f}%")
                    
                    # Final result
                    st.success(f"## 🎉 Final Grade: {final_total:.1f}% - {final_grade}")
                    
                    # Progress bars for visualization
                    st.subheader("📊 Grade Breakdown")
                    
                    ca_total = assignment_avg*0.08 + test_avg*0.08 + practical_avg*0.05 + classwork_avg*0.09
                    exam_contribution = exam_score * 0.70
                    
                    st.write("**Continuous Assessment (30%):**")
                    st.progress(min(ca_total / 30, 1.0))  # Ensure progress doesn't exceed 1.0
                    st.write(f"Assignment: {assignment_avg:.1f}% × 8% = {assignment_avg*0.08:.1f}%")
                    st.write(f"Test: {test_avg:.1f}% × 8% = {test_avg*0.08:.1f}%") 
                    st.write(f"Practical: {practical_avg:.1f}% × 5% = {practical_avg*0.05:.1f}%")
                    st.write(f"Classwork: {classwork_avg:.1f}% × 9% = {classwork_avg*0.09:.1f}%")
                    
                    st.write("**Exam (70%):**")
                    st.progress(min(exam_contribution / 70, 1.0))  # Ensure progress doesn't exceed 1.0
                    st.write(f"Exam: {exam_score:.1f}% × 70% = {exam_contribution:.1f}%")
                    
                else:
                    st.info("📊 Complete your 15 weeks of continuous assessment and exam to see your final grade.")
                    st.info("💡 You need scores for all 15 weeks plus an exam score to calculate your final grade.")
                
            else:
                st.info("📊 No scores recorded yet for your account. Scores will appear here once your lecturer grades your work.")
            
            # ===============================================================
            # 📈 ACTIVITY SUMMARY SECTION
            # ===============================================================
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
            
            # Recent Activity
            st.subheader("🕒 Recent Activity")
            if activity_summary["recent_activity"]:
                for activity in activity_summary["recent_activity"][-5:]:  # Show last 5 activities
                    st.write(f"• {activity}")
            else:
                st.info("No recent activity. Start by marking attendance or submitting assignments!")

        st.markdown("---")
        st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    except Exception as e:
        st.error(f"An error occurred in the student dashboard: {str(e)}")
        st.info("Please refresh the page and try again. If the problem persists, contact your administrator.")
        


    

# ===============================================================
# 📊 COURSE MANAGER SECTION (SIMPLIFIED - ABOUT COURSE & DATA ONLY)
# ===============================================================

def show_course_manager(course_code, course_name):
    """Simplified course manager - only course description and data management"""
    st.header(f"📚 Course Manager - {course_name}")
    
    # Create tabs for course management
    cm_tab1, cm_tab2 = st.tabs(["📝 About Course", "⚙️ Course Data"])
    
    with cm_tab1:
        # ===============================================================
        # 📝 COURSE DESCRIPTION
        # ===============================================================
        st.subheader("📝 Course Description & Information")
        
        # Load existing course description
        course_info = load_course_description(course_code)
        
        with st.form(f"course_description_form_{course_code}"):
            st.info("💡 Provide comprehensive course information for students")
            
            # Course overview
            course_overview = st.text_area(
                "**Course Overview & Description**",
                value=course_info.get('overview', ''),
                height=120,
                placeholder="Describe the course objectives, learning outcomes, and what students will achieve...",
                key=f"overview_{course_code}"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Learning objectives
                learning_outcomes = st.text_area(
                    "**Learning Outcomes**",
                    value=course_info.get('outcomes', ''),
                    height=100,
                    placeholder="What students will be able to do after completing this course...",
                    key=f"outcomes_{course_code}"
                )
                
                # Prerequisites
                prerequisites = st.text_area(
                    "**Prerequisites**",
                    value=course_info.get('prerequisites', ''),
                    height=80,
                    placeholder="Required knowledge or courses before taking this one...",
                    key=f"prerequisites_{course_code}"
                )
            
            with col2:
                # Assessment methods
                assessment = st.text_area(
                    "**Assessment Methods**",
                    value=course_info.get('assessment', ''),
                    height=100,
                    placeholder="Exams, assignments, projects, etc...",
                    key=f"assessment_{course_code}"
                )
                
                # Required materials
                materials = st.text_area(
                    "**Required Materials**",
                    value=course_info.get('materials', ''),
                    height=80,
                    placeholder="Textbooks, software, tools needed...",
                    key=f"materials_{course_code}"
                )
            
            # Course schedule overview
            schedule_overview = st.text_area(
                "**Course Schedule Overview**",
                value=course_info.get('schedule', ''),
                height=80,
                placeholder="Brief overview of weekly topics and major milestones...",
                key=f"schedule_{course_code}"
            )
            
            # Instructor information
            st.subheader("👨‍🏫 Instructor Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                instructor_name = st.text_input(
                    "Instructor Name",
                    value=course_info.get('instructor_name', ''),
                    placeholder="Dr. John Smith",
                    key=f"instructor_name_{course_code}"
                )
                
                instructor_email = st.text_input(
                    "Email",
                    value=course_info.get('instructor_email', ''),
                    placeholder="john.smith@university.edu",
                    key=f"instructor_email_{course_code}"
                )
            
            with col2:
                office_hours = st.text_input(
                    "Office Hours",
                    value=course_info.get('office_hours', ''),
                    placeholder="Monday 2-4 PM, Wednesday 10-12 PM",
                    key=f"office_hours_{course_code}"
                )
                
                office_location = st.text_input(
                    "Office Location",
                    value=course_info.get('office_location', ''),
                    placeholder="Building A, Room 205",
                    key=f"office_location_{course_code}"
                )
            
            # Contact policies
            contact_policy = st.text_area(
                "**Contact Policy**",
                value=course_info.get('contact_policy', ''),
                height=60,
                placeholder="Best ways to contact you and response times...",
                key=f"contact_policy_{course_code}"
            )
            
            # Save course description
            col1, col2 = st.columns([3, 1])
            with col1:
                if st.form_submit_button("💾 Save Course Description", type="primary", use_container_width=True):
                    course_data = {
                        'overview': course_overview,
                        'outcomes': learning_outcomes,
                        'prerequisites': prerequisites,
                        'assessment': assessment,
                        'materials': materials,
                        'schedule': schedule_overview,
                        'instructor_name': instructor_name,
                        'instructor_email': instructor_email,
                        'office_hours': office_hours,
                        'office_location': office_location,
                        'contact_policy': contact_policy,
                        'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    if save_course_description(course_code, course_data):
                        st.success("✅ Course description saved successfully!")
                        log_lecturer_activity("Admin", course_code, "Updated Course Description", 
                                            "Course information updated")
                    else:
                        st.error("❌ Failed to save course description")
            
            with col2:
                if st.form_submit_button("🔄 Reset Form", use_container_width=True):
                    st.rerun()
        
        # Preview section
        st.divider()
        st.subheader("👁️ Course Description Preview")
        st.info("This is how students will see the course information:")
        
        display_course_description_preview(course_info)
    
    with cm_tab2:
        # ===============================================================
        # ⚙️ COURSE DATA MANAGEMENT
        # ===============================================================
        st.subheader("Course Data Management")
        
        st.info("💡 Manage your course information and data")
        
        # Course information summary
        course_info = load_course_description(course_code)
        if course_info:
            st.subheader("📊 Course Information Status")
            
            # Calculate completeness
            info_completeness = calculate_info_completeness(course_info)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Description Completeness", f"{info_completeness}%")
            with col2:
                # Count filled fields
                filled_fields = len([v for v in course_info.values() if v])
                total_fields = len(course_info)
                st.metric("Fields Completed", f"{filled_fields}/{total_fields}")
            with col3:
                last_updated = course_info.get('last_updated', 'Never')
                st.metric("Last Updated", last_updated.split()[0] if last_updated != 'Never' else 'Never')
            
            # Progress bar for completeness
            st.progress(info_completeness / 100)
            
        # Data management options
        st.subheader("📤 Export Course Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Export course description as JSON
            if course_info:
                json_data = json.dumps(course_info, indent=2)
                st.download_button(
                    label="📥 Download Course Info (JSON)",
                    data=json_data,
                    file_name=f"{course_code}_course_description.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"export_info_{course_code}"
                )
            else:
                st.button(
                    "📥 Download Course Info (JSON)",
                    disabled=True,
                    help="No course information available to export",
                    use_container_width=True
                )
        
        with col2:
            # Export course description as CSV
            if course_info:
                # Convert to CSV format
                csv_data = []
                for key, value in course_info.items():
                    if key != 'last_updated':  # Skip timestamp for cleaner CSV
                        csv_data.append(f"{key},{value}")
                
                csv_content = "\n".join(csv_data)
                st.download_button(
                    label="📥 Download Course Info (CSV)",
                    data=csv_content,
                    file_name=f"{course_code}_course_description.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key=f"export_csv_{course_code}"
                )
            else:
                st.button(
                    "📥 Download Course Info (CSV)",
                    disabled=True,
                    help="No course information available to export",
                    use_container_width=True
                )
        
        # Course data reset options
        st.subheader("🔄 Data Management")
        
        with st.expander("Reset Course Information", expanded=False):
            st.warning("⚠️ This will delete all course description data. This action cannot be undone!")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Reset Course Description", type="secondary", use_container_width=True):
                    if reset_course_description(course_code):
                        st.success("✅ Course description reset successfully!")
                        log_lecturer_activity("Admin", course_code, "Reset Course Description", 
                                            "All course information cleared")
                        st.rerun()
                    else:
                        st.error("❌ Failed to reset course description")
            
            with col2:
                if st.button("📋 View Raw Data", type="secondary", use_container_width=True):
                    st.json(course_info if course_info else {"message": "No course data available"})

# ===============================================================
# 🔧 COURSE DESCRIPTION HELPER FUNCTIONS
# ===============================================================

def load_course_description(course_code):
    """Load course description from JSON file"""
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
    """Save course description to JSON file"""
    try:
        desc_file = os.path.join(PERSISTENT_DATA_DIR, "course_descriptions.json")
        
        # Load existing descriptions
        if os.path.exists(desc_file):
            with open(desc_file, 'r') as f:
                all_descriptions = json.load(f)
        else:
            all_descriptions = {}
        
        # Update with new data
        all_descriptions[course_code] = course_data
        
        # Save back to file
        with open(desc_file, 'w') as f:
            json.dump(all_descriptions, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error saving course description: {e}")
        return False

def reset_course_description(course_code):
    """Reset course description to empty"""
    try:
        desc_file = os.path.join(PERSISTENT_DATA_DIR, "course_descriptions.json")
        
        if os.path.exists(desc_file):
            with open(desc_file, 'r') as f:
                all_descriptions = json.load(f)
            
            # Remove this course's description
            if course_code in all_descriptions:
                del all_descriptions[course_code]
            
            # Save back to file
            with open(desc_file, 'w') as f:
                json.dump(all_descriptions, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error resetting course description: {e}")
        return False

def display_course_description_preview(course_info):
    """Display course description in a student-friendly format"""
    if not course_info:
        st.info("No course description available yet. Use the form above to create one.")
        return
    
    # Course Overview
    if course_info.get('overview'):
        st.subheader("🎯 Course Overview")
        st.write(course_info['overview'])
    
    # Learning Outcomes
    if course_info.get('outcomes'):
        st.subheader("📚 Learning Outcomes")
        st.write(course_info['outcomes'])
    
    # Instructor Information
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
    
    # Course Details
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
    
    # Contact Policy
    if course_info.get('contact_policy'):
        st.subheader("📞 Contact Policy")
        st.write(course_info['contact_policy'])
    
    # Last updated
    if course_info.get('last_updated'):
        st.caption(f"Last updated: {course_info['last_updated']}")

def calculate_info_completeness(course_info):
    """Calculate how complete the course information is"""
    if not course_info:
        return 0
    
    required_fields = ['overview', 'outcomes', 'instructor_name', 'assessment']
    filled_fields = [field for field in required_fields if course_info.get(field)]
    return int((len(filled_fields) / len(required_fields)) * 100)
# Remove the duplicate function definition at the end of the file

def admin_view(course_code, course_name):
    """Admin dashboard view with password management"""
    try:
        # Admin authentication with course-specific password
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
        
        # Password management section
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
        
        ensure_directories()
        
        # Create tabs for better organization - INCLUDING COURSE MANAGER
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
            "📚 Course Manager",  # NEW TAB ADDED
            "📖 Lecture Management", 
            "🎥 Video Management", 
            "🕒 Attendance Control",
            "📊 Attendance Records",
            "🧩 Classwork Control", 
            "📝 MCQ Management",  # NEW TAB FOR MCQ
            "📝 Classwork Submissions",
            "📝 Grading System",
            "📂 Student Submissions"
        ])
        
        with tab1:
            # ===============================================================
            # 📚 COURSE MANAGER (INTEGRATED) - FIXED: PASS PARAMETERS
            # ===============================================================
            show_course_manager(course_code, course_name)  # ADD PARAMETERS HERE
        
        with tab2:
            # ===============================================================
            # 📖 LECTURE MANAGEMENT
            # ===============================================================
            st.header("📖 Lecture Management")

            # Load lectures
            lectures_df = load_lectures(course_code)
            st.session_state["lectures_df"] = lectures_df

            # Add/Edit Lecture Section - REMOVED NESTED EXPANDER
            st.subheader("📘 Add / Edit Lecture Materials & Assignment")
            week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)], key="lecture_week_select")
    
            # Find or create row for this week
            if week in lectures_df["Week"].values:
                row_idx = lectures_df[lectures_df["Week"] == week].index[0]
            else:
                new_row = {"Week": week, "Topic": "", "Brief": "", "Assignment": "", "PDF_File": ""}
                lectures_df = pd.concat([lectures_df, pd.DataFrame([new_row])], ignore_index=True)
                row_idx = lectures_df[lectures_df["Week"] == week].index[0]
                st.session_state["lectures_df"] = lectures_df

            # Text input fields
            topic = st.text_input("Topic", value=lectures_df.at[row_idx, "Topic"], key=f"topic_{week}")
            brief = st.text_area("Brief Description", value=lectures_df.at[row_idx, "Brief"], key=f"brief_{week}")
            assignment = st.text_area("Assignment", value=lectures_df.at[row_idx, "Assignment"], key=f"assignment_{week}")

            # PDF Upload section
            st.markdown("**Upload PDF Files (Permanent Storage)**")
            pdf_dir = get_persistent_path("pdf", course_code)
            os.makedirs(pdf_dir, exist_ok=True)

            lecture_pdf = st.file_uploader("Lecture PDF", type=["pdf"], key=f"pdf_{week}")

            # Handle current PDF
            current_pdf = lectures_df.at[row_idx, "PDF_File"]
            current_pdf = str(current_pdf) if current_pdf is not None else ""
            current_pdf = current_pdf.strip()
    
            if current_pdf and os.path.exists(current_pdf):
                st.success(f"📎 Current PDF: {os.path.basename(current_pdf)}")
        
                with open(current_pdf, "rb") as pdf_file:
                    file_size = os.path.getsize(current_pdf) / (1024 * 1024)
                    st.download_button(
                        label=f"📥 Download Current PDF ({file_size:.1f}MB)",
                        data=pdf_file,
                        file_name=os.path.basename(current_pdf),
                        mime="application/pdf",
                        key=f"download_{week}"
                    )
        
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
                        st.error(f"❌ Error removing PDF: {e}")

            # Handle new PDF upload
            if lecture_pdf is not None:
                safe_name = "".join(c for c in lecture_pdf.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                safe_name = safe_name.replace(' ', '_')
        
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
                    st.rerun()
            
                except Exception as e:
                    st.error(f"❌ Error saving PDF: {str(e)}")

            # Automated MCQ Section for this week - SEPARATE SECTION INSTEAD OF NESTED EXPANDER
            st.markdown("---")
            st.subheader("🧩 Automated MCQ Questions")
    
            # Load existing MCQ questions for this week
            existing_questions = load_mcq_questions(course_code, week)
    
            # MCQ Creation Section - USING CONTAINER INSTEAD OF EXPANDER
            st.markdown("#### Create Automated MCQ/Gap-Filling Questions")
            with st.container():
                st.write("**Add New Question:**")
        
                with st.form(f"mcq_creation_form_{week}"):
                    question_type = st.selectbox("Question Type", ["Multiple Choice (MCQ)", "Gap Filling"], key=f"question_type_{week}")
                    question_text = st.text_area("Question Text", placeholder="Enter your question here...", key=f"question_text_{week}")
            
                    if question_type == "Multiple Choice (MCQ)":
                        col1, col2 = st.columns(2)
                        with col1:
                            option_a = st.text_input("Option A", placeholder="First option", key=f"option_a_{week}")
                            option_b = st.text_input("Option B", placeholder="Second option", key=f"option_b_{week}")
                            option_e = st.text_input("Option E", placeholder="Fifth option", key=f"option_e_{week}")
                        with col2:
                            option_c = st.text_input("Option C", placeholder="Third option", key=f"option_c_{week}")
                            option_d = st.text_input("Option D", placeholder="Fourth option", key=f"option_d_{week}")
                
                        correct_answer = st.selectbox("Correct Answer", ["A", "B", "C", "D", "E"], key=f"correct_answer_{week}")
                        options = {
                            "A": option_a,
                            "B": option_b, 
                            "C": option_c,
                            "D": option_d,
                            "E": option_e
                        }
                
                    else:  # Gap Filling
                        correct_answer = st.text_input("Correct Answer(s)", 
                                        placeholder="For multiple correct answers, separate with | (e.g., Paris|France capital)",
                                        key=f"gap_answer_{week}")
                        st.caption("💡 Use | to separate multiple acceptable answers")
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
                            st.success("✅ Question added successfully!")
                            st.rerun()
    
            # Display existing MCQ questions for this week
            if existing_questions:
                st.write(f"**Existing Questions for {week}:**")
                for i, question in enumerate(existing_questions):
                    # Using container for each question instead of expander
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Question {i+1}:** {question['question']}")
                            st.write(f"*Type:* {question['type'].replace('_', ' ').title()}")
                    
                            if question['type'] == 'mcq':
                                st.write("*Options:*")
                                for opt, text in question['options'].items():
                                    st.write(f"  {opt}: {text}")
                    
                            st.write(f"*Correct Answer:* {question['correct_answer']}")
                            st.markdown("---")
                
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_q_{week}_{i}"):
                                existing_questions.pop(i)
                                save_mcq_questions(course_code, week, existing_questions)
                                st.success("✅ Question deleted!")
                                st.rerun()
        
                # Clear all questions for this week
                if st.button("🚨 Clear All Questions", key=f"clear_all_{week}", type="secondary"):
                    if save_mcq_questions(course_code, week, []):
                        st.success("✅ All questions cleared!")
                        st.rerun()
            else:
                st.info("No MCQ questions added for this week yet.")

            # Save button for lecture materials
            st.markdown("---")
            if st.button("💾 SAVE ALL LECTURE MATERIALS", key=f"save_all_{week}", type="primary", use_container_width=True):
                try:
                    lectures_df.at[row_idx, "Topic"] = topic
                    lectures_df.at[row_idx, "Brief"] = brief
                    lectures_df.at[row_idx, "Assignment"] = assignment
            
                    lectures_df.to_csv(get_file(course_code, "lectures"), index=False)
                    st.session_state["lectures_df"] = lectures_df
                    st.success("🎉 All lecture materials saved successfully!")
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error saving to file: {e}")
        
        with tab3:
            # ===============================================================
            # 🎥 VIDEO MANAGEMENT
            # ===============================================================
            st.header("🎥 Video Lecture Management")
            
            # Video upload section
            st.subheader("📤 Upload New Video")
            uploaded_video = st.file_uploader(
                "Upload Lecture Video (MP4 recommended, max 200MB)", 
                type=["mp4", "mov", "avi", "mkv"], 
                key=f"{course_code}_video_upload"
            )
            
            if uploaded_video is not None:
                file_size = uploaded_video.size / (1024 * 1024)
                st.write(f"**File:** {uploaded_video.name}")
                st.write(f"**Size:** {file_size:.2f} MB")
                
                MAX_FILE_SIZE = 200
                if file_size > MAX_FILE_SIZE:
                    st.error(f"❌ File too large! Please upload videos under {MAX_FILE_SIZE}MB.")
                else:
                    success, message = upload_video(course_code, uploaded_video)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

            # Display existing videos
            st.subheader("📚 Video Library")
            video_files = get_video_files(course_code)
            
            if video_files:
                st.success(f"✅ Found {len(video_files)} permanently stored videos")
                
                for i, video in enumerate(video_files):
                    video_path = get_persistent_path("video", course_code, video)
                    
                    # Using container instead of expander for video items
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**🎬 {video}**")
                            try:
                                st.video(video_path, start_time=0)
                                file_size = os.path.getsize(video_path) / (1024 * 1024)
                                st.caption(f"Size: {file_size:.2f} MB (Permanently Stored)")
                            except Exception as e:
                                st.error(f"❌ Cannot preview video: {str(e)}")
                        
                        with col2:
                            try:
                                with open(video_path, "rb") as vid_file:
                                    st.download_button(
                                        label="📥 Download",
                                        data=vid_file,
                                        file_name=video,
                                        mime="video/mp4",
                                        key=f"download_video_{i}"
                                    )
                            except Exception as e:
                                st.error(f"Download unavailable: {str(e)}")
                            
                            if st.button("🗑️ Delete", key=f"delete_video_{i}"):
                                try:
                                    os.remove(video_path)
                                    st.success(f"✅ Video deleted: {video}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Failed to delete: {str(e)}")
                        st.markdown("---")
            else:
                st.info("No videos in permanent storage yet. Upload videos above.")

        with tab4:
            # ===============================================================
            # 🕒 ATTENDANCE CONTROL
            # ===============================================================
            st.header("🎛 Attendance Control")
            
            selected_week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_attendance_week_select")
            
            # Get current status
            current_status = get_attendance_status(course_code, selected_week)
            is_currently_open = current_status.get("is_open", False)
            
            # Display current status
            if is_currently_open:
                st.success(f"✅ Attendance is CURRENTLY OPEN for {course_code} - {selected_week}")
            else:
                st.warning(f"🚫 Attendance is CURRENTLY CLOSED for {course_code} - {selected_week}")
            
            # Attendance control buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔓 OPEN Attendance", use_container_width=True, type="primary", key="open_attendance_btn"):
                    success = set_attendance_status(course_code, selected_week, True, datetime.now())
                    if success:
                        st.success(f"✅ Attendance OPENED for {course_code} - {selected_week}")
                        st.rerun()
            with col2:
                if st.button("🔒 CLOSE Attendance", use_container_width=True, type="secondary", key="close_attendance_btn"):
                    success = set_attendance_status(course_code, selected_week, False)
                    if success:
                        st.warning(f"🚫 Attendance CLOSED for {course_code} - {selected_week}")
                        st.rerun()
            
            # Auto-close functionality
            if is_currently_open and current_status.get("open_time"):
                try:
                    open_time = datetime.fromisoformat(current_status["open_time"])
                    elapsed = (datetime.now() - open_time).total_seconds()
                    remaining = max(0, 600 - elapsed)  # 10 minutes
                    
                    if remaining <= 0:
                        set_attendance_status(course_code, selected_week, False)
                        st.error(f"⏰ Attendance for {course_code} - {selected_week} has automatically closed after 10 minutes.")
                        st.rerun()
                    else:
                        mins = int(remaining // 60)
                        secs = int(remaining % 60)
                        st.info(f"⏳ Attendance will auto-close in {mins:02d}:{secs:02d}")
                except Exception as e:
                    st.error(f"Error in auto-close: {e}")

        with tab5:
            # ===============================================================
            # 📊 ATTENDANCE RECORDS
            # ===============================================================
            st.header("📊 Attendance Records")
            
            # Create tabs for different viewing options
            att_tab1, att_tab2, att_tab3 = st.tabs([
                "👥 Student Details", 
                "📈 Weekly Summary", 
                "📋 Complete History"
            ])
            
            with att_tab1:
                st.subheader("Student Attendance Details")
                view_week = st.selectbox(
                    "Select Week to View", 
                    [f"Week {i}" for i in range(1, 16)], 
                    key=f"{course_code}_attendance_view_week"
                )
                view_student_attendance_details(course_code, view_week)
            
            with att_tab2:
                st.subheader("Weekly Attendance Summary")
                show_attendance_summary(course_code)
            
            with att_tab3:
                view_all_students_attendance(course_code)

            # 🌐 GLOBAL OVERVIEW
            st.header("🌐 Global Attendance Overview")

            if st.button("🔄 Refresh Global Overview", type="secondary", key="refresh_global_attendance"):
                global_df = get_global_attendance_summary()
                
                if not global_df.empty:
                    st.dataframe(global_df, use_container_width=True)
                    
                    # Show some metrics
                    total_all_courses = global_df["Total Attendance Records"].sum()
                    st.metric("Total Attendance Across All Courses", total_all_courses)
                else:
                    st.info("No attendance data found for any course.")

        with tab6:
            # ===============================================================
            # 🧩 CLASSWORK CONTROL
            # ===============================================================
            st.header("🎛 Classwork Control")
            
            classwork_week = st.selectbox("Select Week for Classwork", [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_classwork_control_week")
            
            current_classwork_status = get_classwork_status(course_code, classwork_week)
            is_classwork_open = current_classwork_status.get("is_open", False)
            
            if is_classwork_open:
                st.success(f"✅ Classwork is CURRENTLY OPEN for {course_code} - {classwork_week}")
            else:
                st.warning(f"🚫 Classwork is CURRENTLY CLOSED for {course_code} - {classwork_week}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔓 OPEN Classwork", use_container_width=True, type="primary", key="open_classwork_btn"):
                    success = set_classwork_status(course_code, classwork_week, True, datetime.now())
                    if success:
                        st.success(f"✅ Classwork OPENED for {course_code} - {classwork_week}")
                        st.rerun()
            with col2:
                if st.button("🔒 CLOSE Classwork", use_container_width=True, type="secondary", key="close_classwork_btn"):
                    success = set_classwork_status(course_code, classwork_week, False)
                    if success:
                        st.warning(f"🚫 Classwork CLOSED for {course_code} - {classwork_week}")
                        st.rerun()
            
            if is_classwork_open and current_classwork_status.get("open_time"):
                try:
                    open_time = datetime.fromisoformat(current_classwork_status["open_time"])
                    elapsed = (datetime.now() - open_time).total_seconds()
                    remaining = max(0, 1200 - elapsed)
                    
                    if remaining <= 0:
                        set_classwork_status(course_code, classwork_week, False)
                        st.error(f"⏰ Classwork for {course_code} - {classwork_week} has automatically closed after 20 minutes.")
                        st.rerun()
                    else:
                        mins = int(remaining // 60)
                        secs = int(remaining % 60)
                        st.info(f"⏳ Classwork will auto-close in {mins:02d}:{secs:02d}")
                except Exception as e:
                    st.error(f"Error in classwork auto-close: {e}")
        
        with tab7:
            # ===============================================================
            # 📝 AUTOMATED MCQ MANAGEMENT
            # ===============================================================
            st.header("🧩 Automated MCQ & Gap-Filling Management")
            
            mcq_week = st.selectbox("Select Week for MCQ", [f"Week {i}" for i in range(1, 16)], key="mcq_management_week")
            
            st.subheader("📝 Create Automated Questions")
            
            # Load existing questions
            existing_questions = load_mcq_questions(course_code, mcq_week)
            
            with st.form("mcq_creation_form_main"):
                st.write("**Add New Question:**")
                
                question_type = st.selectbox("Question Type", ["Multiple Choice (MCQ)", "Gap Filling"], key="question_type_main")
                question_text = st.text_area("Question Text", placeholder="Enter your question here...", key="question_text_main")
                
                if question_type == "Multiple Choice (MCQ)":
                    col1, col2 = st.columns(2)
                    with col1:
                        option_a = st.text_input("Option A", placeholder="First option", key="option_a_main")
                        option_b = st.text_input("Option B", placeholder="Second option", key="option_b_main")
                    with col2:
                        option_c = st.text_input("Option C", placeholder="Third option", key="option_c_main")
                        option_d = st.text_input("Option D", placeholder="Fourth option", key="option_d_main")
                    
                    correct_answer = st.selectbox("Correct Answer", ["A", "B", "C", "D"], key="correct_answer_main")
                    options = {
                        "A": option_a,
                        "B": option_b, 
                        "C": option_c,
                        "D": option_d
                    }
                    
                else:  # Gap Filling
                    correct_answer = st.text_input("Correct Answer(s)", 
                                                 placeholder="For multiple correct answers, separate with | (e.g., Paris|France capital)",
                                                 key="gap_answer_main")
                    st.caption("💡 Use | to separate multiple acceptable answers")
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
                    if save_mcq_questions(course_code, mcq_week, existing_questions):
                        st.success("✅ Question added successfully!")
                        st.rerun()
            
            # Display existing questions
            st.subheader("📋 Existing Questions")
            if existing_questions:
                for i, question in enumerate(existing_questions):
                    # Using container instead of expander for each question
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Question {i+1}:** {question['question']}")
                            st.write(f"*Type:* {question['type'].replace('_', ' ').title()}")
                            
                            if question['type'] == 'mcq':
                                st.write("*Options:*")
                                for opt, text in question['options'].items():
                                    st.write(f"  {opt}: {text}")
                            
                            st.write(f"*Correct Answer:* {question['correct_answer']}")
                            st.markdown("---")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_question_{i}"):
                                existing_questions.pop(i)
                                save_mcq_questions(course_code, mcq_week, existing_questions)
                                st.success("✅ Question deleted!")
                                st.rerun()
                
                # Clear all questions
                if st.button("🚨 Clear All Questions", type="secondary", key="clear_all_questions"):
                    if save_mcq_questions(course_code, mcq_week, []):
                        st.success("✅ All questions cleared!")
                        st.rerun()
            else:
                st.info("No questions added yet. Create questions using the form above.")
            
            # Preview for students
            st.subheader("👁️ Student Preview")
            if existing_questions:
                st.info("This is how students will see the questions:")
                display_mcq_questions(existing_questions)
            else:
                st.warning("No questions to preview. Add questions first.")

        with tab8:
            # ===============================================================
            # 📝 CLASSWORK SUBMISSIONS (INCLUDING MCQ)
            # ===============================================================
            st.header("📝 Classwork Submissions")
            
            cw_tab1, cw_tab2 = st.tabs(["📅 Weekly Submissions", "📚 All Submissions"])
            
            with cw_tab1:
                st.subheader("Weekly Classwork Submissions")
                cw_week = st.selectbox("Select Week to View", [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_classwork_view_week")
                
                try:
                    classwork_file = get_file(course_code, "classwork")
                    
                    if not os.path.exists(classwork_file):
                        st.warning(f"No classwork submissions found for {course_code} - {cw_week}")
                    else:
                        df = pd.read_csv(classwork_file)
                        
                        if df.empty:
                            st.warning(f"No classwork submissions found for {course_code} - {cw_week}")
                        else:
                            week_submissions = df[df['Week'] == cw_week]
                            
                            if week_submissions.empty:
                                st.warning(f"No classwork submissions found for {course_code} - {cw_week}")
                            else:
                                st.success(f"📝 Classwork Submissions for {course_code} - {cw_week}")
                                
                                # Separate MCQ and text submissions
                                mcq_submissions = week_submissions[week_submissions['Type'] == 'MCQ']
                                text_submissions = week_submissions[week_submissions['Type'] != 'MCQ']
                                
                                if not mcq_submissions.empty:
                                    st.subheader("🧩 MCQ Submissions (Auto-graded)")
                                    for idx, row in mcq_submissions.iterrows():
                                        # Using container instead of expander
                                        with st.container():
                                            st.write(f"**🎯 {row['Name']} ({row['Matric']}) - Score: {row['Score']}%**")
                                            st.write(f"*Student:* {row['Name']} ({row['Matric']})")
                                            st.write(f"*Score:* {row['Score']}%")
                                            st.write(f"*Submitted:* {row['Timestamp']}")
                                            st.markdown("---")
                                
                                if not text_submissions.empty:
                                    st.subheader("📝 Text Submissions")
                                    for idx, row in text_submissions.iterrows():
                                        # Using container instead of expander
                                        with st.container():
                                            st.write(f"**📄 {row['Name']} ({row['Matric']})**")
                                            st.write(f"*Student:* {row['Name']} ({row['Matric']})")
                                            st.write(f"*Submitted:* {row['Timestamp']}")
                                            try:
                                                answers = json.loads(row['Answers'])
                                                st.write("**Answers:**")
                                                for i, answer in enumerate(answers):
                                                    if answer.strip():
                                                        st.write(f"**Q{i+1}:** {answer}")
                                                        st.divider()
                                            except:
                                                st.write("**Answers:** Unable to parse answers")
                                            st.markdown("---")
                                
                                # Download option
                                csv_data = week_submissions.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Classwork Submissions",
                                    data=csv_data,
                                    file_name=f"classwork_{course_code}_{cw_week.replace(' ', '')}.csv",
                                    mime="text/csv",
                                    use_container_width=True,
                                    key="download_classwork_submissions"
                                )
                                
                except Exception as e:
                    st.error(f"Error loading classwork submissions: {e}")

        with tab9:
            # ===============================================================
            # 📝 GRADING SYSTEM WITH FINAL GRADE CALCULATION
            # ===============================================================
            st.header("📝 Grading System")
            
            # Display grading weights
            st.info("""
            **Grading Weights (After 15 Weeks + Exam):**
            - Continuous Assessment (15 weeks average): 30%
              - Assignment: 8% 
              - Test: 8%
              - Practical: 5%
              - Classwork: 9%
            - Exam (After 15 weeks): 70%
            """)
            
            # Ensure scores file exists with proper structure
            scores_df = ensure_scores_file(course_code)
            scores_file = get_file(course_code, "scores")
            
            # Option 1: Manual Grade Entry
            st.subheader("📋 Manual Grade Entry")
            with st.form("manual_grading_form"):
                col1, col2 = st.columns(2)
                with col1:
                    student_name = st.text_input("Student Name", key="grade_name")
                    week = st.selectbox("Week", [f"Week {i}" for i in range(1, 16)] + ["Exam"], key="grade_week")
                    assignment_score = st.number_input("Assignment Score (0-100)", min_value=0, max_value=100, value=0, key="assignment_score")
                    test_score = st.number_input("Test Score (0-100)", min_value=0, max_value=100, value=0, key="test_score")
                with col2:
                    student_matric = st.text_input("Matric Number", key="grade_matric")
                    practical_score = st.number_input("Practical Score (0-100)", min_value=0, max_value=100, value=0, key="practical_score")
                    exam_score = st.number_input("Exam Score (0-100)", min_value=0, max_value=100, value=0, key="exam_score")
                    classwork_score = st.number_input("Classwork Score (0-100)", min_value=0, max_value=100, value=0, key="classwork_score")
                
                submit_grade = st.form_submit_button("💾 Save Grade", use_container_width=True)
                
                if submit_grade:
                    if not student_name or not student_matric:
                        st.error("Please enter student name and matric number.")
                    else:
                        # For weekly scores, calculate weekly total
                        if week != "Exam":
                            weekly_total = round(
                                assignment_score * 0.08 + 
                                test_score * 0.08 + 
                                practical_score * 0.05 + 
                                classwork_score * 0.09, 
                                1
                            )
                            weekly_grade = compute_grade(weekly_total)
                        else:
                            # For exam, we don't calculate weekly total
                            weekly_total = 0
                            weekly_grade = ""
                        
                        # Load current scores
                        scores_df = pd.read_csv(scores_file)
                        
                        # Check if entry exists
                        mask = (
                            (scores_df["StudentName"].astype(str).str.lower() == student_name.lower()) &
                            (scores_df["MatricNo"].astype(str).str.lower() == student_matric.lower()) &
                            (scores_df["Week"].astype(str).str.lower() == week.lower())
                        )
                        
                        if mask.any():
                            # Update existing entry
                            scores_df.loc[mask, [
                                "Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"
                            ]] = [assignment_score, test_score, practical_score, exam_score, classwork_score, weekly_total, weekly_grade]
                        else:
                            # Add new entry
                            new_row = {
                                "StudentName": student_name.title(),
                                "MatricNo": student_matric.upper(),
                                "Week": week,
                                "Assignment": assignment_score,
                                "Test": test_score,
                                "Practical": practical_score,
                                "Exam": exam_score,
                                "Classwork": classwork_score,
                                "Total": weekly_total,
                                "Grade": weekly_grade
                            }
                            scores_df = pd.concat([scores_df, pd.DataFrame([new_row])], ignore_index=True)
                        
                        scores_df.to_csv(scores_file, index=False)
                        st.success(f"✅ Grade saved for {student_name} ({student_matric}) - {week}")

            # Option 2: CSV Upload for Bulk Grading
            st.subheader("📁 Bulk Grade Upload (CSV)")
            uploaded_csv = st.file_uploader(
                "Upload CSV with columns: StudentName, MatricNo, Week, Assignment, Test, Practical, Exam, Classwork", 
                type=["csv"],
                key="grade_csv_upload"
            )
            
            if uploaded_csv is not None:
                try:
                    uploaded_df = pd.read_csv(uploaded_csv)
                    
                    # Validate required columns
                    required_cols = ["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Classwork"]
                    if all(col in uploaded_df.columns for col in required_cols):
                        # Calculate totals based on week type
                        def calculate_row_total(row):
                            if row['Week'] != 'Exam':
                                return round(
                                    row['Assignment'] * 0.08 + 
                                    row['Test'] * 0.08 + 
                                    row['Practical'] * 0.05 + 
                                    row['Classwork'] * 0.09, 
                                    1
                                )
                            return 0
                        
                        uploaded_df["Total"] = uploaded_df.apply(calculate_row_total, axis=1)
                        uploaded_df["Grade"] = uploaded_df["Total"].apply(compute_grade)
                        
                        # Load current scores
                        if os.path.exists(scores_file):
                            existing_df = pd.read_csv(scores_file)
                        else:
                            existing_df = pd.DataFrame(columns=required_cols + ["Total", "Grade"])
                        
                        # Update or add each row
                        for _, row in uploaded_df.iterrows():
                            mask = (
                                (existing_df["StudentName"].astype(str).str.lower() == str(row["StudentName"]).lower()) &
                                (existing_df["MatricNo"].astype(str).str.lower() == str(row["MatricNo"]).lower()) &
                                (existing_df["Week"].astype(str).str.lower() == str(row["Week"]).lower())
                            )
                            if mask.any():
                                existing_df.loc[mask, ["Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"]] = [
                                    row["Assignment"], row["Test"], row["Practical"], row["Exam"], row["Classwork"], row["Total"], row["Grade"]
                                ]
                            else:
                                new_row = {
                                    "StudentName": row["StudentName"],
                                    "MatricNo": row["MatricNo"],
                                    "Week": row["Week"],
                                    "Assignment": row["Assignment"],
                                    "Test": row["Test"],
                                    "Practical": row["Practical"],
                                    "Exam": row["Exam"],
                                    "Classwork": row["Classwork"],
                                    "Total": row["Total"],
                                    "Grade": row["Grade"]
                                }
                                existing_df = pd.concat([existing_df, pd.DataFrame([new_row])], ignore_index=True)
                        
                        existing_df.to_csv(scores_file, index=False)
                        st.success(f"✅ Successfully processed {len(uploaded_df)} grade records!")
                        st.dataframe(existing_df, use_container_width=True)
                    else:
                        missing_cols = [col for col in required_cols if col not in uploaded_df.columns]
                        st.error(f"❌ CSV missing required columns: {', '.join(missing_cols)}")
                        
                except Exception as e:
                    st.error(f"❌ Error processing CSV: {e}")

            # Display current grades with final calculation
            st.subheader("📊 Current Grades & Final Calculations")
            if os.path.exists(scores_file):
                try:
                    scores_df = pd.read_csv(scores_file)
                    if not scores_df.empty:
                        # Show individual scores
                        st.dataframe(scores_df, use_container_width=True)
                        
                        # Calculate and show final grades for each student
                        st.subheader("🎓 Final Grade Calculations")
                        
                        # Group by student
                        students = scores_df[['StudentName', 'MatricNo']].drop_duplicates()
                        
                        final_grades_data = []
                        for _, student in students.iterrows():
                            student_name = student['StudentName']
                            matric = student['MatricNo']
                            
                            student_scores = scores_df[
                                (scores_df['StudentName'] == student_name) & 
                                (scores_df['MatricNo'] == matric)
                            ]
                            
                            final_total, final_grade, assignment_avg, test_avg, practical_avg, classwork_avg, exam_score = calculate_final_grade(student_scores)
                            
                            if final_total is not None:
                                final_grades_data.append({
                                    'StudentName': student_name,
                                    'MatricNo': matric,
                                    'CA_Assignment_Avg': round(assignment_avg, 1),
                                    'CA_Test_Avg': round(test_avg, 1),
                                    'CA_Practical_Avg': round(practical_avg, 1),
                                    'CA_Classwork_Avg': round(classwork_avg, 1),
                                    'Exam_Score': exam_score,
                                    'Final_Total': final_total,
                                    'Final_Grade': final_grade
                                })
                        
                        if final_grades_data:
                            final_df = pd.DataFrame(final_grades_data)
                            st.dataframe(final_df, use_container_width=True)
                            
                            # Download options
                            col1, col2 = st.columns(2)
                            with col1:
                                csv_all = scores_df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download All Scores CSV",
                                    data=csv_all,
                                    file_name=f"{course_code}_all_scores.csv",
                                    mime="text/csv",
                                    use_container_width=True,
                                    key="download_all_scores"
                                )
                            
                            with col2:
                                csv_final = final_df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Final Grades CSV",
                                    data=csv_final,
                                    file_name=f"{course_code}_final_grades.csv",
                                    mime="text/csv",
                                    use_container_width=True,
                                    key="download_final_grades"
                                )
                        else:
                            st.info("No complete data available for final grade calculation.")
                    else:
                        st.info("No grades recorded yet.")
                except Exception as e:
                    st.error(f"Error loading grades: {e}")
            else:
                st.info("No grades file found yet.")

        with tab10:
            # ===============================================================
            # 📂 VIEW STUDENT SUBMISSIONS
            # ===============================================================
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
                    unique_key = f"{course_code}_{upload_type}_{file}"
                    
                    # Using container instead of expander for file items
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**📎 {file}**")
                            try:
                                file_size = os.path.getsize(file_path) / (1024 * 1024)
                                st.write(f"*Size:* {file_size:.2f} MB")
                                
                                # Extract student info from filename
                                parts = file.split('_')
                                if len(parts) >= 2:
                                    st.write(f"*Student:* {parts[0]} ({parts[1]})")
                                if len(parts) >= 3:
                                    st.write(f"*Week:* {parts[2]}")
                                    
                            except:
                                st.write("*Size:* Unknown")
                        
                        with col2:
                            try:
                                with open(file_path, "rb") as fh:
                                    st.download_button(
                                        label="⬇️ Download",
                                        data=fh,
                                        file_name=file,
                                        mime="application/octet-stream",
                                        key=f"{unique_key}_download"
                                    )
                            except Exception:
                                st.warning("⚠️ Cannot open file for download.")
                        st.markdown("---")

        st.markdown("---")
        st.markdown(f"*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    except Exception as e:
        st.error(f"An error occurred in the admin dashboard: {str(e)}")
        st.info("Please refresh the page and try again. If the problem persists, contact your administrator.")

def test_database_connection():
    """Test if database is working properly"""
    st.sidebar.subheader("🔧 Database Test")
    if st.sidebar.button("Test Database"):
        if init_course_db() and check_database_schema():
            st.sidebar.success("✅ Database is working correctly!")
        else:
            st.sidebar.error("❌ Database has issues!")
            
        # Show current schema
        try:
            conn = sqlite3.connect(os.path.join(PERSISTENT_DATA_DIR, 'courses.db'))
            c = conn.cursor()
            c.execute("PRAGMA table_info(weekly_courses)")
            columns = c.fetchall()
            conn.close()
            
            st.sidebar.write("Current Schema:")
            for col in columns:
                st.sidebar.write(f"- {col[1]} ({col[2]})")
        except Exception as e:
            st.sidebar.error(f"Schema check failed: {e}")



# 🚀 UPDATE MAIN APPLICATION
# ===============================================================

def main():
    """Main application with System Admin role"""
     # ... your existing main code ...
    test_database_connection()  # Add this line
# ================================================
    # Application Header
    st.subheader("Multi-Course Learning Management System")
    st.title("🎓 University Course Portal")
    
    # Auto-refresh
    st_autorefresh(interval=86_400_000, key="daily_refresh")
    
    # Sidebar navigation
    st.sidebar.title("🎓 Navigation")
    
    # Role Selection
    if "role" not in st.session_state:
        st.session_state["role"] = None
    
    role = st.sidebar.radio("Select Role", ["Select", "Student", "Admin", "System Admin"], key="role_selector")
    
    if role != "Select":
        st.session_state["role"] = role
    else:
        st.session_state["role"] = None
    
    # Load courses
    COURSES = load_courses_config()
    
    # Route based on role
    if st.session_state["role"] == "System Admin":
        show_system_admin_dashboard()
    elif st.session_state["role"] == "Admin" and COURSES:
        course = st.sidebar.selectbox("Select Course:", list(COURSES.keys()))
        course_code = COURSES[course]
        course_name = course
        admin_view(course_code, course_name)
    elif st.session_state["role"] == "Student" and COURSES:
        course = st.sidebar.selectbox("Select Course:", list(COURSES.keys()))
        course_code = COURSES[course]
        course_name = course
        student_view(course_code, course_name)
    else:
        if not COURSES:
            st.warning("⚠️ No courses available. Please contact system administrator.")
        else:
            st.warning("👆 Please select your role from the sidebar to continue.")

    
    # Add CSS for course cards
st.markdown("""
    <style>
    .course-card {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #4CAF50;
        margin: 5px 0;
        }
    </style>
""", unsafe_allow_html=True)
    
# Footer
st.markdown("""
    <style>
    .custom-footer {
        position: relative;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #f0f2f6;
        color: #333;
        text-align: center;
        padding: 8px;
        font-size: 15px;
        font-weight: 500;
        border-top: 1px solid #ccc;
        margin-top: 2rem;
    }
    </style>
    <div class="custom-footer">
        Developed by <b>Adebimpe-John Omolola</b> | © 2025 | Advanced LMS with System Monitoring
    </div>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
























































