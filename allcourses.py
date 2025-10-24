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
    </style>
    """,
    unsafe_allow_html=True
)

# ===============================================================
# 🗂 CONSTANTS AND DIRECTORIES
# ===============================================================

PERSISTENT_DATA_DIR = "persistent_data"
ATTENDANCE_STATUS_FILE = "attendance_status.json"

# Course Definitions
COURSES = {
    "MCB 221 – General Microbiology": "MCB221",
    "BCH 201 – General Biochemistry": "BCH201", 
    "BIO 203 – General Physiology": "BIO203",
    "BIO 113 – Virus Bacteria Lower Plants": "BIO113",
    "BIO 306 – Systematic Biology": "BIO306",
}

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
        os.path.join(PERSISTENT_DATA_DIR, "student_uploads", "seminar")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    return True

# Initialize directories
ensure_directories()
# ===============================================================
# 🎯 AUTOMATED MCQ & GAP-FILLING SYSTEM
# ===============================================================

def get_mcq_file(course_code, week):
    """Get the MCQ questions file path for a specific course and week"""
    safe_week = week.replace(" ", "_").replace(":", "")
    return os.path.join(PERSISTENT_DATA_DIR, "mcq_questions", f"{course_code}_{safe_week}_mcq.json")

def save_mcq_questions(course_code, week, questions):
    """Save MCQ questions to JSON file"""
    try:
        mcq_file = get_mcq_file(course_code, week)
        os.makedirs(os.path.dirname(mcq_file), exist_ok=True)
        
        with open(mcq_file, 'w') as f:
            json.dump(questions, f, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving MCQ questions: {e}")
        return False

def load_mcq_questions(course_code, week):
    """Load MCQ questions from JSON file"""
    try:
        mcq_file = get_mcq_file(course_code, week)
        if os.path.exists(mcq_file):
            with open(mcq_file, 'r') as f:
                return json.load(f)
        return []
    except Exception as e:
        st.error(f"Error loading MCQ questions: {e}")
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
            st.info("📊 Database updated: Added course_code column to existing table")
    
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
        "attendance_status": os.path.join(base_dir, "data", "attendance_status.json"),
        "scores": os.path.join(base_dir, "scores", f"{course_code.lower()}_scores.csv")
    }
    
    return file_paths.get(file_type, os.path.join(base_dir, "data", filename))

def get_file(course_code, file_type):
    """Get file path for course-specific files"""
    return get_persistent_path(file_type, course_code)

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

# ===============================================================
# 📊 COURSE MANAGER SECTION (INTEGRATED INTO ADMIN)
# ===============================================================

def show_course_manager():
    """Course management integrated into admin view"""
    st.header("📚 Course Manager")
    
    # Initialize and migrate database
    init_course_db()
    migrate_old_database()
    
    # Create tabs for course management
    cm_tab1, cm_tab2, cm_tab3 = st.tabs(["➕ Add Weekly Courses", "📋 View Courses", "⚙️ Manage Data"])
    
    with cm_tab1:
        st.subheader("Add Weekly Courses")
        
        week_name = st.text_input("**Week Name** (e.g., 'Week 1', 'Spring Semester Week 1'):", key="week_name_input")
        
        st.subheader("📚 Add Courses for this Week")
        course_input = st.text_area("**Enter courses** (one per line):", height=200,
                                   placeholder="MCB 221 – General Microbiology\nBCH 201 – General Biochemistry\nBIO 203 – General Physiology",
                                   key="course_text_area")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("💾 Save Courses to Database", type="primary", key="save_courses_btn"):
                if week_name and course_input:
                    courses_list = [course.strip() for course in course_input.split('\n') if course.strip()]
                    saved_count = 0
                    
                    # Add each course to database
                    for course in courses_list:
                        course_code = COURSES.get(course, "UNKNOWN")
                        try:
                            add_course_to_db(week_name, course, course_code)
                            saved_count += 1
                        except Exception as e:
                            st.error(f"Error saving {course}: {e}")
                    
                    if saved_count > 0:
                        st.success(f"✅ Successfully added {saved_count} courses for {week_name}!")
                        st.balloons()
                    else:
                        st.error("❌ No courses were saved. Please check the course names.")
                else:
                    st.error("❌ Please provide both week name and courses.")
        
        with col2:
            if st.button("🔄 Clear Form", key="clear_form_btn"):
                st.rerun()
    
    with cm_tab2:
        st.subheader("View All Courses")
        
        weeks = get_weeks_from_db()
        
        if not weeks:
            st.info("ℹ️ No courses available. Add some courses first!")
        else:
            # Show all weeks in expanders
            for week in weeks:
                courses = get_courses_by_week(week)
                with st.expander(f"📅 {week} ({len(courses)} courses)"):
                    for i, course in enumerate(courses, 1):
                        st.write(f"{i}. **{course['name']}** ({course['code']})")
    
    with cm_tab3:
        st.subheader("Data Management")
        
        st.info("💾 Your course data is automatically saved in a local SQLite database that persists across reboots.")
        
        # Show database info
        try:
            df = get_all_courses_from_db()
            
            if not df.empty:
                st.subheader("📊 Database Contents")
                st.dataframe(df)
                
                # Statistics
                total_courses = len(df)
                total_weeks = df['week_name'].nunique()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total Weeks", total_weeks)
                with col2:
                    st.metric("Total Courses", total_courses)
                
                # Export option
                st.subheader("📤 Export Data")
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Courses CSV",
                    data=csv,
                    file_name="all_courses.csv",
                    mime="text/csv"
                )
                
                # Delete option
                st.subheader("🗑️ Delete Data")
                weeks_to_delete = st.multiselect("Select weeks to delete:", df['week_name'].unique())
                if st.button("🚨 Delete Selected Weeks", type="secondary"):
                    for week in weeks_to_delete:
                        delete_week_from_db(week)
                    st.success(f"✅ Deleted {len(weeks_to_delete)} weeks!")
                    st.rerun()
                    
            else:
                st.info("ℹ️ No data available in the database.")
                
        except Exception as e:
            st.error(f"❌ Error accessing database: {e}")
            
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
# 🎓 STUDENT VIEW
# ===============================================================

def student_view(course_code):
    """Student dashboard view with persistent storage and scores viewing"""
    try:
        ensure_directories()
        
        st.title(f"🎓 Student Dashboard - {course_code}")
        
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

        # ===============================================================
        # 📊 SCORES VIEWING SECTION
        # ===============================================================
        if student_name and student_matric:
            # Load and display student scores
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
                    return pd.DataFrame()

            student_scores = load_student_scores(course_code, student_name, student_matric)
            
            if not student_scores.empty:
                # Display weekly scores
                st.subheader("📋 Weekly Scores")
                display_columns = ["Week", "Assignment", "Test", "Practical", "Exam", "Classwork", "Total", "Grade"]
                display_df = student_scores[display_columns].copy()
                
                # Format percentages
                for col in ["Assignment", "Test", "Practical", "Exam", "Classwork", "Total"]:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) and x != 0 else "N/A")
                
                st.dataframe(display_df, use_container_width=True)
                
                # FINAL GRADE CALCULATION AFTER 15 WEEKS + EXAM
                st.subheader("🎓 Final Grade Calculation")
                
                final_total, final_grade, assignment_avg, test_avg, practical_avg, classwork_avg, exam_score = calculate_final_grade(student_scores)
                
                if final_total is not None:
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
                    st.progress(ca_total / 30)
                    st.write(f"Assignment: {assignment_avg:.1f}% × 8% = {assignment_avg*0.08:.1f}%")
                    st.write(f"Test: {test_avg:.1f}% × 8% = {test_avg*0.08:.1f}%") 
                    st.write(f"Practical: {practical_avg:.1f}% × 5% = {practical_avg*0.05:.1f}%")
                    st.write(f"Classwork: {classwork_avg:.1f}% × 9% = {classwork_avg*0.09:.1f}%")
                    
                    st.write("**Exam (70%):**")
                    st.progress(exam_contribution / 70)
                    st.write(f"Exam: {exam_score:.1f}% × 70% = {exam_contribution:.1f}%")
                    
                else:
                    st.info("📊 Complete your 15 weeks of continuous assessment and exam to see your final grade.")
                
            else:
                st.info("📊 No scores recorded yet for your account. Scores will appear here once your lecturer grades your work.")
        
        else:
            st.warning("⚠️ Please set your identity above to view your scores.")
            
       
        # ===============================================================
        # 📈 ACTIVITY SUMMARY SECTION
        # ===============================================================
        if student_name and student_matric:
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

        # ===============================================================
        # 🕒 ATTENDANCE SECTION
        # ===============================================================
        st.header("🕒 Mark Attendance")
        
        with st.form(f"{course_code}_attendance_form"):
            # Pre-fill with session state values
            name = st.text_input("Full Name", value=student_name, key=f"{course_code}_student_name")
            matric = st.text_input("Matric Number", value=student_matric, key=f"{course_code}_student_matric")
            week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_att_week")
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
                status_data = get_attendance_status(course_code, week)
                is_attendance_open = status_data.get("is_open", False)
                
                if not is_attendance_open:
                    st.error("🚫 Attendance for this course is currently closed. Please wait for your lecturer to open it.")
                elif has_marked_attendance(course_code, week, student_name, student_matric):
                    st.info("✅ Attendance already marked for this week.")
                else:
                    ok = mark_attendance_entry(course_code, student_name, student_matric, week)
                    if ok:
                        st.session_state["attended_week"] = str(week)
                        st.success(f"🎉 Attendance recorded successfully for {course_code} - {week}.")
                        st.balloons()
                    else:
                        st.error("⚠️ Failed to record attendance. Try again later.")

        # ===============================================================
        # 📖 LECTURE MATERIALS
        # ===============================================================
        st.header(f"📚 {course_code} Lecture Materials")
        
        lectures_df = load_lectures(course_code)
        
        if lectures_df.empty or lectures_df["Week"].isna().all():
            st.info("No lecture materials available yet. Check back later!")
        else:
            # Display each week's materials
            for _, row in lectures_df.iterrows():
                if pd.isna(row["Week"]) or row["Week"] == "":
                    continue
                    
                week = row["Week"]
                    
                with st.expander(f"📖 {row['Week']}: {row['Topic']}", expanded=False):
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
                                        key=f"student_pdf_{row['Week'].replace(' ', '_')}"
                                    )
                                    st.success("✅ PDF available")
                            except Exception as e:
                                st.error(f"⚠️ Error loading PDF: {e}")
                        else:
                            st.info("No PDF available")


# ===============================================================
# 🧩 AUTOMATED CLASSWORK SECTION (REPLACES OLD CLASSWORK)
# ===============================================================

# Check for automated MCQ questions for this week
        mcq_questions = load_mcq_questions(course_code, week)

        if mcq_questions:
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

    # Check if already submitted
                classwork_file = get_file(course_code, "classwork")
                already_submitted = False
                previous_score = 0
    
                if os.path.exists(classwork_file):
                    df = pd.read_csv(classwork_file)
                    existing = df[
                        (df['Name'] == student_name) & 
                        (df['Matric'] == student_matric) & 
                        (df['Week'] == week) &
                        (df['Type'] == 'MCQ')
        ]
                    already_submitted = not existing.empty
                    if already_submitted:
                        previous_score = existing.iloc[0]['Score']

                if already_submitted:
                    st.warning(f"⚠️ You have already submitted this classwork. Your score: **{previous_score}%**")
        
                    if st.button("🔄 Retake Classwork", key=f"retake_{week}"):
            # Remove previous submission
                        df = df.drop(existing.index)
                        df.to_csv(classwork_file, index=False)
                        st.success("✅ Previous submission cleared. You can retake now.")
                        st.rerun()
    
                    elif classwork_status:
                        with st.form(f"mcq_form_{week.replace(' ', '_')}"):
                            st.write("**Answer the following questions:**")
                            answers = display_mcq_questions(mcq_questions)
            
                            submit_mcq = st.form_submit_button(
                                "🚀 Submit Classwork Answers", 
                                use_container_width=True
            )

                            if submit_mcq:
                                if not student_name or not student_matric:
                                    st.error("❌ Please set your identity first using the form above.")
                                elif any(not answer.strip() for answer in answers):
                                    st.error("❌ Please answer all questions before submitting.")
                                else:
                    # Auto-grade submission
                                    score, correct, total = auto_grade_mcq_submission(mcq_questions, answers)
                    
                    # Save submission
                                    success = save_mcq_submission(course_code, week, student_name, student_matric, answers, score)
                                    if success:
                        # Update classwork score in main scores file
                                        update_classwork_score(course_code, student_name, student_matric, week, score)
                        
                                        st.balloons()
                                        st.success(f"🎉 Classwork submitted successfully! Score: **{score}%** ({correct}/{total} correct)")
                                        st.rerun()
            else:
                st.info("⏳ Classwork for this week is currently closed. Please wait for your lecturer to open it.")
        else:
            st.info("No automated classwork assigned for this week yet.")
        
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

        # ===============================================================
        # 📤 STUDENT SUBMISSIONS SECTION
        # ===============================================================
        if student_name and student_matric:
            st.header("📤 Submit Assignments")
            
            # Assignment submission
            st.subheader("📝 Assignment Submission")
            with st.form("assignment_upload_form"):
                assignment_week = st.selectbox("Select Week for Assignment", [f"Week {i}" for i in range(1, 16)], key="assignment_week")
                assignment_file = st.file_uploader("Upload Assignment File", type=["pdf", "doc", "docx", "txt", "zip"], key="assignment_upload")
                submit_assignment = st.form_submit_button("📤 Submit Assignment", use_container_width=True)
                
                if submit_assignment:
                    if not assignment_file:
                        st.error("❌ Please select a file to upload.")
                    else:
                        file_path = save_file(course_code, student_name, assignment_week, assignment_file, "assignment")
                        if file_path:
                            log_submission(course_code, student_matric, student_name, assignment_week, assignment_file.name, "assignment")
                            st.success(f"✅ Assignment submitted successfully: {assignment_file.name}")

            # Drawing submission
            st.subheader("🎨 Drawing Submission")
            with st.form("drawing_upload_form"):
                drawing_week = st.selectbox("Select Week for Drawing", [f"Week {i}" for i in range(1, 16)], key="drawing_week")
                drawing_file = st.file_uploader("Upload Drawing File", type=["jpg", "jpeg", "png", "gif", "pdf"], key="drawing_upload")
                submit_drawing = st.form_submit_button("📤 Submit Drawing", use_container_width=True)
                
                if submit_drawing:
                    if not drawing_file:
                        st.error("❌ Please select a file to upload.")
                    else:
                        file_path = save_file(course_code, student_name, drawing_week, drawing_file, "drawing")
                        if file_path:
                            log_submission(course_code, student_matric, student_name, drawing_week, drawing_file.name, "drawing")
                            st.success(f"✅ Drawing submitted successfully: {drawing_file.name}")

            # Seminar submission
            st.subheader("📊 Seminar Submission")
            with st.form("seminar_upload_form"):
                seminar_week = st.selectbox("Select Week for Seminar", [f"Week {i}" for i in range(1, 16)], key="seminar_week")
                seminar_file = st.file_uploader("Upload Seminar File", type=["pdf", "ppt", "pptx", "doc", "docx"], key="seminar_upload")
                submit_seminar = st.form_submit_button("📤 Submit Seminar", use_container_width=True)
                
                if submit_seminar:
                    if not seminar_file:
                        st.error("❌ Please select a file to upload.")
                    else:
                        file_path = save_file(course_code, student_name, seminar_week, seminar_file, "seminar")
                        if file_path:
                            log_submission(course_code, student_matric, student_name, seminar_week, seminar_file.name, "seminar")
                            st.success(f"✅ Seminar submitted successfully: {seminar_file.name}")

        st.markdown("---")
        st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    except Exception as e:
        st.error(f"An error occurred in the student dashboard: {str(e)}")
        st.info("Please refresh the page and try again. If the problem persists, contact your administrator.")


# ===============================================================
# 👩‍🏫 ADMIN VIEW (WITH INTEGRATED COURSE MANAGER)
# ===============================================================

def admin_view(course_code):
    """Admin dashboard view with integrated course manager"""
    try:
        # Admin authentication
        ADMIN_PASS = "bimpe2025class"
        password = st.text_input("Enter Admin Password", type="password", key="admin_password_input")
        
        if password != ADMIN_PASS:
            st.warning("Enter the correct Admin password to continue.")
            return
        
        st.session_state["role"] = "Admin"
        st.success(f"✅ Logged in as Admin - {course_code}")
        
        ensure_directories()
        
        st.title("👩‍🏫 Admin Dashboard")
        
        # Create tabs for better organization - INCLUDING COURSE MANAGER
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10= st.tabs([
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
            # 📚 COURSE MANAGER (INTEGRATED)
            # ===============================================================
            show_course_manager()
        
        with tab2:
            # ===============================================================
            # 📖 LECTURE MANAGEMENT
            # ===============================================================
            st.header("📖 Lecture Management")

# Load lectures
            lectures_df = load_lectures(course_code)
            st.session_state["lectures_df"] = lectures_df

# Add/Edit Lecture Section
            with st.expander("📘 Add / Edit Lecture Materials & Assignment", expanded=True):
                week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)])
    
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

    # Automated MCQ Section for this week
                st.markdown("---")
                st.subheader("🧩 Automated MCQ Questions")
    
    # Load existing MCQ questions for this week
                existing_questions = load_mcq_questions(course_code, week)
    
                with st.expander("Create Automated MCQ/Gap-Filling Questions", expanded=False):
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
                        with st.expander(f"Question {i+1}: {question['question'][:50]}...", expanded=False):
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                st.write(f"**Type:** {question['type'].replace('_', ' ').title()}")
                                st.write(f"**Question:** {question['question']}")
                    
                                if question['type'] == 'mcq':
                                    st.write("**Options:**")
                                    for opt, text in question['options'].items():
                                        st.write(f"{opt}: {text}")
                    
                                        st.write(f"**Correct Answer:** {question['correct_answer']}")
                
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
                    
                    with st.expander(f"🎬 {video}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
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
                                        key=f"download_{i}"
                                    )
                            except Exception as e:
                                st.error(f"Download unavailable: {str(e)}")
                            
                            if st.button("🗑️ Delete", key=f"delete_{i}"):
                                try:
                                    os.remove(video_path)
                                    st.success(f"✅ Video deleted: {video}")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Failed to delete: {str(e)}")
            else:
                st.info("No videos in permanent storage yet. Upload videos above.")

        with tab4:
            # ===============================================================
            # 🕒 ATTENDANCE CONTROL
            # ===============================================================
            st.header("🎛 Attendance Control")
            
            selected_week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_week_select")
            
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
                if st.button("🔓 OPEN Attendance", use_container_width=True, type="primary"):
                    success = set_attendance_status(course_code, selected_week, True, datetime.now())
                    if success:
                        st.success(f"✅ Attendance OPENED for {course_code} - {selected_week}")
                        st.rerun()
            with col2:
                if st.button("🔒 CLOSE Attendance", use_container_width=True, type="secondary"):
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
                    key=f"{course_code}_view_week"
                )
                view_student_attendance_details(course_code, view_week)
            
            with att_tab2:
                st.subheader("Weekly Attendance Summary")
                show_attendance_summary(course_code)
            
            with att_tab3:
                view_all_students_attendance(course_code)

            # 🌐 GLOBAL OVERVIEW
            st.header("🌐 Global Attendance Overview")

            if st.button("🔄 Refresh Global Overview", type="secondary"):
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
            
            classwork_week = st.selectbox("Select Week for Classwork", [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_classwork_week")
            
            current_classwork_status = get_classwork_status(course_code, classwork_week)
            is_classwork_open = current_classwork_status.get("is_open", False)
            
            if is_classwork_open:
                st.success(f"✅ Classwork is CURRENTLY OPEN for {course_code} - {classwork_week}")
            else:
                st.warning(f"🚫 Classwork is CURRENTLY CLOSED for {course_code} - {classwork_week}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔓 OPEN Classwork", use_container_width=True, type="primary"):
                    success = set_classwork_status(course_code, classwork_week, True, datetime.now())
                    if success:
                        st.success(f"✅ Classwork OPENED for {course_code} - {classwork_week}")
                        st.rerun()
            with col2:
                if st.button("🔒 CLOSE Classwork", use_container_width=True, type="secondary"):
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
                    
        with tab6:  # Classwork Control tab
            show_classwork_control(course_code)
            
        with tab7:
            # ===============================================================
            # 📝 AUTOMATED MCQ MANAGEMENT
            # ===============================================================
            st.header("🧩 Automated MCQ & Gap-Filling Management")
            
            mcq_week = st.selectbox("Select Week for MCQ", [f"Week {i}" for i in range(1, 16)], key="mcq_week")
            
            st.subheader("📝 Create Automated Questions")
            
            # Load existing questions
            existing_questions = load_mcq_questions(course_code, mcq_week)
            
            with st.form("mcq_creation_form"):
                st.write("**Add New Question:**")
                
                question_type = st.selectbox("Question Type", ["Multiple Choice (MCQ)", "Gap Filling"], key="question_type")
                question_text = st.text_area("Question Text", placeholder="Enter your question here...")
                
                if question_type == "Multiple Choice (MCQ)":
                    col1, col2 = st.columns(2)
                    with col1:
                        option_a = st.text_input("Option A", placeholder="First option")
                        option_b = st.text_input("Option B", placeholder="Second option")
                    with col2:
                        option_c = st.text_input("Option C", placeholder="Third option")
                        option_d = st.text_input("Option D", placeholder="Fourth option")
                    
                    correct_answer = st.selectbox("Correct Answer", ["A", "B", "C", "D"])
                    options = {
                        "A": option_a,
                        "B": option_b, 
                        "C": option_c,
                        "D": option_d
                    }
                    
                else:  # Gap Filling
                    correct_answer = st.text_input("Correct Answer(s)", 
                                                 placeholder="For multiple correct answers, separate with | (e.g., Paris|France capital)")
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
                    with st.expander(f"Question {i+1}: {question['question'][:50]}...", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**Type:** {question['type'].replace('_', ' ').title()}")
                            st.write(f"**Question:** {question['question']}")
                            
                            if question['type'] == 'mcq':
                                st.write("**Options:**")
                                for opt, text in question['options'].items():
                                    st.write(f"{opt}: {text}")
                            
                            st.write(f"**Correct Answer:** {question['correct_answer']}")
                        
                        with col2:
                            if st.button("🗑️ Delete", key=f"delete_q_{i}"):
                                existing_questions.pop(i)
                                save_mcq_questions(course_code, mcq_week, existing_questions)
                                st.success("✅ Question deleted!")
                                st.rerun()
                
                # Clear all questions
                if st.button("🚨 Clear All Questions", type="secondary"):
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
                cw_week = st.selectbox("Select Week to View", [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_cw_week_view")
                
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
                                        with st.expander(f"🎯 {row['Name']} ({row['Matric']}) - Score: {row['Score']}%", expanded=False):
                                            st.write(f"**Student:** {row['Name']} ({row['Matric']})")
                                            st.write(f"**Score:** {row['Score']}%")
                                            st.write(f"**Submitted:** {row['Timestamp']}")
                                
                                if not text_submissions.empty:
                                    st.subheader("📝 Text Submissions")
                                    for idx, row in text_submissions.iterrows():
                                        with st.expander(f"📄 {row['Name']} ({row['Matric']})", expanded=False):
                                            st.write(f"**Student:** {row['Name']} ({row['Matric']})")
                                            st.write(f"**Submitted:** {row['Timestamp']}")
                                            try:
                                                answers = json.loads(row['Answers'])
                                                st.write("**Answers:**")
                                                for i, answer in enumerate(answers):
                                                    if answer.strip():
                                                        st.write(f"**Q{i+1}:** {answer}")
                                                        st.divider()
                                            except:
                                                st.write("**Answers:** Unable to parse answers")
                                
                                # Download option
                                csv_data = week_submissions.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Classwork Submissions",
                                    data=csv_data,
                                    file_name=f"classwork_{course_code}_{cw_week.replace(' ', '')}.csv",
                                    mime="text/csv",
                                    use_container_width=True
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
                key="grade_csv"
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
                                    use_container_width=True
                                )
                            
                            with col2:
                                csv_final = final_df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Download Final Grades CSV",
                                    data=csv_final,
                                    file_name=f"{course_code}_final_grades.csv",
                                    mime="text/csv",
                                    use_container_width=True
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
                    
                    with st.expander(f"📎 {file}", expanded=False):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write(f"**File:** {file}")
                            try:
                                file_size = os.path.getsize(file_path) / (1024 * 1024)
                                st.write(f"**Size:** {file_size:.2f} MB")
                                
                                # Extract student info from filename
                                parts = file.split('_')
                                if len(parts) >= 2:
                                    st.write(f"**Student:** {parts[0]} ({parts[1]})")
                                if len(parts) >= 3:
                                    st.write(f"**Week:** {parts[2]}")
                                    
                            except:
                                st.write("**Size:** Unknown")
                        
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
        st.markdown(f"*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
    except Exception as e:
        st.error(f"An error occurred in the admin dashboard: {str(e)}")
        st.info("Please refresh the page and try again. If the problem persists, contact your administrator.")


# ===============================================================
# 🚀 MAIN APPLICATION
# ===============================================================

def main():
    """Main application with navigation"""
    
    # Application Header
    st.subheader("Department of Biological Sciences, Sikiru Adetona College of Education Omu-Ijebu")
    st.title("📚 Multi-Course Portal")
    
    # Auto-refresh (once per day)
    st_autorefresh(interval=86_400_000, key="daily_refresh")
    
    # Sidebar navigation
    st.sidebar.title("🎓 Navigation")
    
    # Role Selection
    if "role" not in st.session_state:
        st.session_state["role"] = None
    
    role = st.sidebar.radio("Select Role", ["Select", "Student", "Admin"], key="role_selector")
    
    if role != "Select":
        st.session_state["role"] = role
    else:
        st.session_state["role"] = None
    
    # Course Selection (for Student and Admin views)
    if st.session_state["role"] in ["Student", "Admin"]:
        course = st.sidebar.selectbox("Select Course:", list(COURSES.keys()))
        course_code = COURSES[course]
        st.sidebar.markdown("---")
    
    # Main content area based on role
    if st.session_state["role"] == "Admin":
        admin_view(course_code)
    elif st.session_state["role"] == "Student":
        student_view(course_code)
    else:
        st.warning("👆 Please select your role from the sidebar to continue.")

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
        Developed by <b>Mide</b> | © 2025 | Integrated Course Management System
    </div>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main()













