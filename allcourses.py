import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, date, timedelta, time
from streamlit_autorefresh import st_autorefresh
import zipfile
import io
import json
import base64


ATTENDANCE_FILE = "attendance.csv"
LECTURE_FILE = "lectures.csv"
CLASSWORK_FILE = "classwork_submissions.csv"
SEMINAR_FILE = "seminar_submissions.csv"
MODULES_DIR = "modules"
SEMINAR_DIR = os.path.join(MODULES_DIR, "seminars")
CLASSWORK_STATUS_FILE = "classwork_status.csv"

os.makedirs(MODULES_DIR, exist_ok=True)
os.makedirs(SEMINAR_DIR, exist_ok=True)

# ✅ PAGE CONFIGURATION
st.set_page_config(page_title="Multi-Course Dashboard", page_icon="📚", layout="wide")

# ===============================================================
# 🔐 ROLE SELECTION & ACCESS CONTROL
# ===============================================================
if "role" not in st.session_state:
    st.session_state["role"] = None

st.sidebar.title("🔐 Login Panel")
role = st.sidebar.radio("Select Role", ["Select", "Student", "Admin"], key="role_selector")

if role != "Select":
    st.session_state["role"] = role
else:
    st.session_state["role"] = None

# ===============================================================
# 🧩 UI STYLE
# ===============================================================
st.markdown(
    """
    <style>
    footer {visibility: hidden;}
    #MainMenu {visibility: hidden;}
    .viewerBadge_container__1QSob,
    .viewerBadge_link__1S137,
    .viewerBadge_text__1JaDK { display: none !important; }
    .custom-footer {
        position: fixed; left: 0; bottom: 0;
        width: 100%; background-color: #f0f2f6;
        color: #333; text-align: center; padding: 8px;
        font-size: 15px; font-weight: 500;
        border-top: 1px solid #ccc;
    }
    </style>
    <div class="custom-footer">
        Developed by <b>Mide</b> | © 2025 | 
        <a href="https://example.com" target="_blank" style="text-decoration:none; color:#1f77b4;">
            Visit our website
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)
# ===============================================================
# 🎓 MAIN APP HEADER
# ===============================================================
st.subheader("Department of Biological Sciences, Sikiru Adetona College of Education Omu-Ijebu")
st.title("📚 Multi-Course Portal")
st_autorefresh(interval=86_400_000, key="daily_refresh")  # refresh daily

# ===============================================================
# 📘 COURSE SELECTION
# ===============================================================
COURSES = {
    "MCB 221 – General Microbiology": "MCB221",
    "BCH 201 – General Biochemistry": "BCH201",
    "BIO 203 – General Physiology": "BIO203",
    "BIO 113 – Virus Bacteria Lower Plants": "BIO113",
    "BIO 306 – Systematic Biology": "BIO306",

}
course = st.selectbox("Select Course:", list(COURSES.keys()))
course_code = COURSES[course]

# ===============================================================
# 📂 DIRECTORY SETUP
# ===============================================================
MODULES_DIR = "modules"
LECTURE_DIR = "lectures"
UPLOAD_DIR = "student_uploads"
LOG_DIR = "records"

for folder in [MODULES_DIR, LECTURE_DIR, UPLOAD_DIR, LOG_DIR]:
    os.makedirs(folder, exist_ok=True)

course_dir = os.path.join(MODULES_DIR, course_code)
os.makedirs(course_dir, exist_ok=True)

UPLOADS_DIR = os.path.join(UPLOAD_DIR, course_code)
os.makedirs(UPLOADS_DIR, exist_ok=True)

def load_lectures(course_code):
    """Load lecture file safely for a given course."""
    LECTURE_FILE = get_file(course_code, "lectures")

    if not os.path.exists(LECTURE_FILE):
        # Try to create a blank one so students don't see an error
        os.makedirs(os.path.dirname(LECTURE_FILE), exist_ok=True)
        df = pd.DataFrame(columns=["Week", "Topic", "Brief", "Assignment", "Classwork"])
        df.to_csv(LECTURE_FILE, index=False)
        return df

    try:
        df = pd.read_csv(LECTURE_FILE)
        required_cols = ["Week", "Topic", "Brief", "Assignment", "Classwork"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        st.error(f"Error loading lecture file: {e}")
        return pd.DataFrame(columns=["Week", "Topic", "Brief", "Assignment", "Classwork"])

# Fixed helper functions
def has_marked_attendance(course_code, week, name, matric):
    try:
        attendance_file = f"attendance_{course_code}_{week.replace(' ', '')}.csv"
        
        if not os.path.exists(attendance_file):
            return False
        
        df = pd.read_csv(attendance_file)
        
        # Convert to string and clean data
        df['Name'] = df['Name'].astype(str).str.strip().str.lower()
        df['Matric'] = df['Matric'].astype(str).str.strip().str.lower()
        
        name_clean = name.strip().lower()
        matric_clean = matric.strip().lower()
        
        # Check for existing entry
        existing = df[(df['Name'] == name_clean) & (df['Matric'] == matric_clean)]
        return len(existing) > 0
        
    except Exception as e:
        st.error(f"⚠️ Error checking attendance: {e}")
        return True  # Prevent marking if error


def mark_attendance_entry(course_code, name, matric, week):
    try:
        attendance_file = f"attendance_{course_code}_{week.replace(' ', '')}.csv"
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

import json
import os
from datetime import datetime

ATTENDANCE_STATUS_FILE = "attendance_status.json"

def init_attendance_status():
    """Initialize the attendance status file if it doesn't exist"""
    if not os.path.exists(ATTENDANCE_STATUS_FILE):
        default_status = {}
        with open(ATTENDANCE_STATUS_FILE, 'w') as f:
            json.dump(default_status, f)

def get_attendance_status(course_code, week):
    """Get attendance status for a specific course and week"""
    init_attendance_status()
    
    try:
        with open(ATTENDANCE_STATUS_FILE, 'r') as f:
            status_data = json.load(f)
        
        week_key = week.replace(" ", "")
        key = f"{course_code}_{week_key}"
        
        return status_data.get(key, False)
    except:
        return False

def set_attendance_status(course_code, week, is_open, open_time=None):
    """Set attendance status for a specific course and week"""
    init_attendance_status()
    
    try:
        with open(ATTENDANCE_STATUS_FILE, 'r') as f:
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
        
        with open(ATTENDANCE_STATUS_FILE, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error setting attendance status: {e}")
        return False

def get_all_attendance_status():
    """Get all attendance status for debugging"""
    init_attendance_status()
    
    try:
        with open(ATTENDANCE_STATUS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_file(course_code, student_name, matric, week, file_obj, upload_type):
    upload_dir = os.path.join("student_uploads", course_code, upload_type)
    os.makedirs(upload_dir, exist_ok=True)
    ext = file_obj.name.split(".")[-1]
    filename = f"{student_name}_{matric}_{week}.{ext}"
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as f:
        f.write(file_obj.getbuffer())
    return file_path

def ensure_default_lectures_file(course_code):
    """Ensure a valid lectures CSV exists for each new course (auto-create if missing)."""
    folder = "data"
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, f"{course_code.lower()}_lectures.csv")

    # Only create if missing
    if not os.path.exists(filepath):
        # Define starter content per course (you can expand anytime)
        default_data = {
            "BIO113": [
                ["Week 1", "Viruses, Bacteria and Lower Plants – Introduction", 
                 "Overview of viruses, bacteria, and lower plants; classification, importance, and general features.", 
                 "List three differences between viruses and bacteria; Describe the importance of lower plants in nature.", 
                 "Write short notes on: (a) Viral structure (b) Bacterial reproduction (c) Algal types."],
                ["Week 2", "Viruses and Their Reproduction", 
                 "Structure of viruses; replication cycles (lytic and lysogenic); economic importance.", 
                 "Explain the difference between the lytic and lysogenic cycles.", 
                 "Draw and label the structure of a typical virus."]
            ],
            "BIO306": [
                ["Week 1", "Introduction to Systematic Biology", 
                 "Meaning and scope of taxonomy and systematics. Classification principles.", 
                 "Differentiate between taxonomy and systematics.", 
                 "List and explain the five kingdoms of classification."]
            ]
        }

        # Create either default or empty DataFrame
        if course_code in default_data:
            df = pd.DataFrame(default_data[course_code], 
                              columns=["Week", "Topic", "Brief", "Classwork", "Assignment"])
        else:
            df = pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment"])

        df.to_csv(filepath, index=False)
        st.success(f"✅ Created a new default lecture file for {course_code}. You can edit it later.")
    
    return filepath

# ===============================================================
# 📁 HELPER FUNCTION
# ===============================================================
def get_file(course_code, filetype):
    """Return the file path for a given course and file type."""
    filename = f"{course_code}_{filetype}.csv"
    return os.path.join(LOG_DIR, filename)

def get_file(course_code, file_type):
    base_path = "data"
    file_map = {
        "lectures": f"{course_code}_lectures.csv",
        "attendance": f"{course_code}_attendance.csv",
        "submissions": f"{course_code}_submissions.csv",
    }
    return os.path.join(base_path, file_map[file_type])

def admin_view():
    st.title("Admin Dashboard")

    course_code = "BIO133"
    st.header("📋 Attendance Records")

    attendance_file = get_file(course_code, "attendance")
    if os.path.exists(attendance_file):
        attendance_df = pd.read_csv(attendance_file)
        if not attendance_df.empty:
            st.dataframe(attendance_df)
        else:
            st.info("No attendance records yet.")
    else:
        st.warning("Attendance file not found!")

    st.header("📝 Student Submissions")

    submission_file = get_file(course_code, "submissions")
    if os.path.exists(submission_file):
        submissions_df = pd.read_csv(submission_file)
        if not submissions_df.empty:
            st.dataframe(submissions_df)
        else:
            st.info("No student submissions yet.")
    else:
        st.warning("Submission file not found!")

def init_lectures(course_code, default_weeks):
    """Create or load lectures CSV for a course. Returns DataFrame."""
    LECTURE_FILE = get_file(course_code, "lectures")
    
    # ✅ Ensure directory exists
    os.makedirs(os.path.dirname(LECTURE_FILE), exist_ok=True)
    
    if not os.path.exists(LECTURE_FILE):
        lecture_data = {
            "Week": [f"Week {i+1}" for i in range(len(default_weeks))],
            "Topic": default_weeks,
            "Brief": [""] * len(default_weeks),
            "Assignment": [""] * len(default_weeks),
            "Classwork": [""] * len(default_weeks),
        }
        pd.DataFrame(lecture_data).to_csv(LECTURE_FILE, index=False)
        
    df = pd.read_csv(LECTURE_FILE)
    for col in ["Brief", "Assignment", "Classwork"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")
    return df


def save_file(course_code, student_name, week, uploaded_file, upload_type):
    """Save uploaded file persistently."""
    folder = os.path.join(UPLOAD_DIR, course_code, upload_type)
    os.makedirs(folder, exist_ok=True)
    filename = f"{student_name}_{week}_{uploaded_file.name}"
    file_path = os.path.join(folder, filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def log_submission(course_code, matric, student_name, week, file_name, upload_type):
    """Log each submission permanently."""
    log_path = os.path.join(LOG_DIR, f"{course_code}_uploads.csv")
    log_data = {
        "Matric": [matric],
        "Name": [student_name],
        "Week": [week],
        "File": [file_name],
        "Type": [upload_type],
        "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    }
    new_entry = pd.DataFrame(log_data)
    if os.path.exists(log_path):
        df = pd.read_csv(log_path)
        df = pd.concat([df, new_entry], ignore_index=True)
    else:
        df = new_entry
    df.to_csv(log_path, index=False)


# =========================================================
# ✅ FINAL — Unified Attendance Helper Functions
# =========================================================
LOG_DIR = "attendance"
os.makedirs(LOG_DIR, exist_ok=True)

def has_marked_attendance(course_code, week, name, matric):
    """Check if student already marked attendance."""
    path = os.path.join(LOG_DIR, f"{course_code}_attendance.csv")
    if not os.path.exists(path):
        return False
    df = pd.read_csv(path)
    return ((df["Name"].str.strip().str.lower() == name.strip().lower()) &
            (df["Matric"].str.strip().str.lower() == matric.strip().lower()) &
            (df["Week"].astype(str).str.strip().str.lower() == week.strip().lower())
           ).any()

def mark_attendance_entry(course_code, name, matric, week):
    """Mark student attendance and save persistently."""
    path = os.path.join(LOG_DIR, f"{course_code}_attendance.csv")
    os.makedirs(LOG_DIR, exist_ok=True)

    data = {
        "Name": [name.strip()],
        "Matric": [matric.strip()],
        "Week": [week],
        "Timestamp": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    }

    new_row = pd.DataFrame(data)
    if os.path.exists(path):
        df = pd.read_csv(path)
        df = pd.concat([df, new_row], ignore_index=True)
    else:
        df = new_row

    df.to_csv(path, index=False)
    return True


def view_and_download_files(course_code, file_type, week):
    """Displays uploaded files for a given type and week, with ZIP download."""
    base_dir = os.path.join("student_uploads", course_code, file_type)

    if os.path.exists(base_dir):
        all_files = []
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if week.replace(" ", "_") in file or week in root:
                    file_path = os.path.join(root, file)
                    uploader_name = os.path.basename(root)
                    all_files.append({
                        "Student": uploader_name,
                        "File Name": file,
                        "File Path": file_path
                    })
        if all_files:
            df_files = pd.DataFrame(all_files)
            st.dataframe(df_files[["Student", "File Name"]])

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for item in all_files:
                    zipf.write(item["File Path"], arcname=f"{item['Student']}/{item['File Name']}")
            st.download_button(
                label=f"📦 Download All {file_type.capitalize()}s for {week}",
                data=zip_buffer.getvalue(),
                file_name=f"{course_code}_{week.replace(' ', '_')}_{file_type}s.zip",
                mime="application/zip"
            )
        else:
            st.info(f"No {file_type} submissions found for {week}.")
    else:
        st.info(f"No {file_type} submission directory found yet.")

def get_file(course_code, filename):
    """Return filename of the form <COURSECODE>_<filename>.csv (in current dir)."""
    return f"{course_code}_{filename}.csv"

def ensure_data_files():
    """Create a few CSVs with headers if they don't exist (safe to call repeatedly)."""
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)

    files = {
        "attendance_records.csv": ["StudentName", "Matric", "CourseCode", "Week", "Status", "Timestamp"],
        "assignment_records.csv": ["StudentName", "Matric", "CourseCode", "Week", "FilePath", "Score", "Timestamp"],
        "classwork_records.csv": ["StudentName", "Matric", "CourseCode", "Week", "Score", "Timestamp"],
        "seminar_records.csv": ["StudentName", "Matric", "CourseCode", "Week", "Topic", "Score", "Timestamp"],
        "scores.csv": ["StudentName", "Matric", "CourseCode", "ClassworkAvg", "SeminarAvg", "AssignmentAvg", "TotalCA", "LastUpdated"],
    }

    for filename, headers in files.items():
        file_path = os.path.join(data_dir, filename)
        if not os.path.exists(file_path):
            pd.DataFrame(columns=headers).to_csv(file_path, index=False)

# call once
ensure_data_files()

# -----------------------------
# ATTENDANCE + SUBMISSION HELPERS
# -----------------------------
def has_marked_attendance(course_code, week, matric, name):
    try:
        df = pd.read_csv(os.path.join("attendance", f"{course_code}_attendance.csv"))
        # Ensure columns exist
        if "Name" not in df.columns or "Week" not in df.columns:
            return False

        # Check case-insensitive match
        return any(
            (df["Name"].astype(str).str.upper() == str(name).upper()) &
            (df["Week"].astype(str).str.upper() == str(week).upper())
        )
    except FileNotFoundError:
        return False
    except Exception as e:
        st.error(f"⚠️ Error checking attendance: {e}")
        return False


def save_file(course_code, name, week, matric, uploaded_file, file_type):
    """Save an uploaded file to submissions/<course>/<file_type>/ and log it."""
    folder_path = os.path.join("submissions", course_code, file_type)
    os.makedirs(folder_path, exist_ok=True)
    safe_name = re.sub(r"\s+", "_", name.strip())
    file_path = os.path.join(folder_path, f"{safe_name}_{week}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Log upload summary
    csv_log = os.path.join("records", f"{course_code}_{file_type}_uploads.csv")
    log_df = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d %H:%M:%S"), name, week, uploaded_file.name]],
                          columns=["Timestamp", "Name", "Week", "File"])
    if os.path.exists(csv_log):
        old = pd.read_csv(csv_log)
        log_df = pd.concat([old, log_df], ignore_index=True)
    log_df.to_csv(csv_log, index=False)

    # Keep a central submissions log for the course
    record_file = os.path.join("submissions", f"{course_code}_submissions.csv")
    record = pd.DataFrame([{"Name": name, "Week": week, "FileName": uploaded_file.name, "Type": file_type, "Path": file_path}])

    if os.path.exists(record_file):
        existing = pd.read_csv(record_file)
        updated = pd.concat([existing, record], ignore_index=True)
        updated.to_csv(record_file, index=False)
    else:
        record.to_csv(record_file, index=False)
    return file_path

def normalize_course_name(name: str):
    return name.replace("–", "-").replace("—", "-").strip()

def get_course_code(course_name):
    name = normalize_course_name(course_name)
    mapping = {
        "BIO 113 - Virus Bacteria Lower Plants": "BIO113",
        "BIO 203 - General Physiology": "BIO203",
        "BIO 306 - Systematic Biology": "BIO306",
        # etc...
    }
    return mapping.get(name)

# -----------------------------
# SCORES HELPERS
# -----------------------------
def get_score_file(course_code, score_type):
    folder_path = os.path.join("submissions", course_code)
    os.makedirs(folder_path, exist_ok=True)
    return os.path.join(folder_path, f"{score_type}_scores.csv")

def record_score(course_code, score_type, name, matric, week, score, remarks=""):
    score_file = get_score_file(course_code, score_type)
    df = pd.read_csv(score_file) if os.path.exists(score_file) else pd.DataFrame(columns=["StudentName", "Matric", "Week", "Score", "Remarks"])

    existing = (
        (df["Matric"].astype(str).str.lower() == matric.strip().lower()) &
        (df["Week"] == week)
    )
    if existing.any():
        df.loc[existing, ["Score", "Remarks"]] = [score, remarks]
    else:
        new_row = {"StudentName": name.strip(), "Matric": matric.strip(), "Week": week, "Score": score, "Remarks": remarks}
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(score_file, index=False)
    st.success(f"✅ {score_type.capitalize()} score updated for {name} ({week})")

@st.cache_data(ttl=30)
    
def get_student_scores_cached(course_code, matric):
    score_types = ["classwork", "seminar", "assignment"]
    results = {}

    for stype in score_types:
        f = get_score_file(course_code, stype)
        if os.path.exists(f):
            df = pd.read_csv(f)
            df = df[df["Matric"].astype(str).str.lower() == matric.strip().lower()]
            results[stype] = df[["Week", "Score"]].to_dict("records") if not df.empty else []
        else:
            results[stype] = []

    return results

# -----------------------------
# CLASSWORK WINDOW CONTROL
# -----------------------------
def is_classwork_open(course_code, week):
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork_status")
    if not os.path.exists(CLASSWORK_STATUS_FILE):
        return False
    df = pd.read_csv(CLASSWORK_STATUS_FILE)
    if week not in df["Week"].values:
        return False
    row = df[df["Week"] == week].iloc[0]
    return int(row.get("IsOpen", 0)) == 1


def open_classwork(course_code, week):
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork_status")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df = pd.read_csv(CLASSWORK_STATUS_FILE) if os.path.exists(CLASSWORK_STATUS_FILE) else pd.DataFrame(columns=["Week", "IsOpen", "OpenTime"])
    if week in df["Week"].values:
        df.loc[df["Week"] == week, ["IsOpen", "OpenTime"]] = [1, now]
    else:
        df = pd.concat([df, pd.DataFrame([{"Week": week, "IsOpen": 1, "OpenTime": now}])], ignore_index=True)
    df.to_csv(CLASSWORK_STATUS_FILE, index=False)


def close_classwork_after_20min(course_code):
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork_status")
    if not os.path.exists(CLASSWORK_STATUS_FILE):
        return
    df = pd.read_csv(CLASSWORK_STATUS_FILE)
    now = datetime.now()
    changed = False
    for idx, row in df.iterrows():
        if int(row.get("IsOpen", 0)) == 1 and pd.notnull(row.get("OpenTime")):
            open_time = pd.to_datetime(row["OpenTime"]).to_pydatetime()
            if (now - open_time).total_seconds() > 20 * 60:
                df.at[idx, "IsOpen"] = 0
                df.at[idx, "OpenTime"] = None
                changed = True
    if changed:
        df.to_csv(CLASSWORK_STATUS_FILE, index=False)
        
def save_classwork(course_code, name, matric, week, answers):
    """Save classwork answers to a CSV file after validation."""
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork_answers")

    # Ensure attendance and activation
    if "attended_week" not in st.session_state:
        st.warning("⚠️ You must mark attendance before submitting classwork.")
        return
    if not st.session_state.get("classwork_open", False):
        st.warning("🚫 Classwork is not open yet. Please wait for your lecturer.")
        return

    # Create CSV if missing
    if not os.path.exists(CLASSWORK_STATUS_FILE):
        pd.DataFrame(columns=["StudentName", "Matric", "Week", "Answers", "Timestamp"]).to_csv(CLASSWORK_STATUS_FILE, index=False)

    # Append new record
    df = pd.read_csv(CLASSWORK_STATUS_FILE)
    answers_str = "; ".join([f"Q{i+1}: {ans.strip()}" for i, ans in enumerate(answers) if ans.strip()])
    new_row = {
        "StudentName": name.strip(),
        "Matric": matric.strip(),
        "Week": week,
        "Answers": answers_str,
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(CLASSWORK_STATUS_FILE, index=False)

    st.success(f"✅ Classwork answers saved for {name} ({week})")


def save_file(course_code, student_name, week, uploaded_file, folder_name):
    """Safely save uploaded file to the appropriate course and folder."""
    if uploaded_file is None:
        return None  # handled at caller level

    upload_dir = os.path.join("student_uploads", course_code, folder_name)
    os.makedirs(upload_dir, exist_ok=True)
    safe_name = re.sub(r'[^A-Za-z0-9_-]', '_', student_name.strip())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(upload_dir, f"{safe_name}_{week}_{timestamp}_{uploaded_file.name}")

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path
    
def log_submission(course_code, matric, student_name, week, file_name, upload_type):
    """Log each upload to a CSV file for admin tracking."""
    log_file = os.path.join(UPLOADS_DIR, f"{course_code}_submissions_log.csv")
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

def display_module_pdf(week):
    """Display the PDF module for a specific week."""
    pdf_path = os.path.join(LECTURE_DIR, f"{course_code}_W{week}_module.pdf")
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button("📥 Download Module PDF", f, file_name=os.path.basename(pdf_path))
    else:
        st.info("Module PDF not available.")

def display_module_pdf(week):
    pdf_path = f"{MODULES_DIR}/{week.replace(' ','_')}.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path,"rb") as f:
            st.download_button(label=f"📥 Download {week} Module PDF", data=f, file_name=f"{week}_module.pdf", mime="application/pdf")
    else:
        st.info("Lecture PDF module not yet uploaded.")

def ensure_default_lectures_file(file_path):
    """Ensure lecture file exists; create a default one if missing."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    if not os.path.exists(file_path):
        df = pd.DataFrame({
            "Week": ["Week 1", "Week 2", "Week 3"],
            "Topic": ["Introduction", "Cell Structure", "Microbial Physiology"],
            "Brief": ["Overview of microbiology", "Structure and function of cells", "Basic metabolism in microbes"],
            "Assignment": ["Read Chapter 1", "Draw bacterial cell", "Submit enzyme report"],
            "Classwork": ["Define microbiology;", "Label cell parts;", "Explain glycolysis;"]
        })
        df.to_csv(file_path, index=False)
    return pd.read_csv(file_path)

# ===========================================
# 🔧 UNIVERSAL LECTURE LOADER (NO FILE NEEDED)
# ===========================================
def get_lecture_brief(course_code):
    """Return the lecture brief for any course directly."""
    lectures = {
        "MCB221": [
            {
                "Week": "Week 1",
                "Topic": "Introduction to Microbiology",
                "Brief": "Definition, history, branches, and importance of microbiology.",
                "Classwork": "List three branches of microbiology;",
                "Assignment": "Write a short note on the history of microbiology;"
            },
            {
                "Week": "Week 2",
                "Topic": "Microscopy",
                "Brief": "Types, principles, and care of microscopes.",
                "Classwork": "Draw and label a compound microscope;",
                "Assignment": "Explain the principle of light microscopy;"
            },
        ],
        "BIO113": [
            {
                "Week": "Week 1",
                "Topic": "Viruses: Structure and Reproduction",
                "Brief": "Structure of viruses, modes of replication, and classification.",
                "Classwork": "List five viral diseases;",
                "Assignment": "Explain the lytic and lysogenic cycles;"
            },
            {
                "Week": "Week 2",
                "Topic": "Bacteria and Lower Plants",
                "Brief": "Morphology, cell wall structure, and reproduction of bacteria and algae.",
                "Classwork": "Label parts of a bacterial cell;",
                "Assignment": "Discuss the economic importance of algae;"
            },
        ],
        # Add more courses below in the same pattern 👇
        # "CHM101": [ ... ],
        # "PHY111": [ ... ],
    }

    return lectures.get(course_code, [])

BASE_DIR = "database"
os.makedirs(BASE_DIR, exist_ok=True)

def get_file(course_code, file_type):
    """Generate a valid file path for different file types."""
    file_map = {
        "attendance": os.path.join(BASE_DIR, f"{course_code}_attendance.csv"),
        "attendance_form": os.path.join(BASE_DIR, f"{course_code}_attendance.csv"),
        "lectures": os.path.join(BASE_DIR, f"{course_code}_lectures.csv"),
        "scores": os.path.join(BASE_DIR, f"{course_code}_scores.csv"),
    }
    return file_map.get(file_type, "")

def has_marked_attendance(course_code, week, name, matric=None):
    """Check if a student has already marked attendance for a specific course and week."""
    try:
        # 📁 Define the folder and weekly file
        attendance_folder = os.path.join("data", "attendance")
        file_path = os.path.join(attendance_folder, f"{course_code}_Week_{week}.csv")

        # 🚫 If file doesn't exist yet
        if not os.path.exists(file_path):
            return False

        # ✅ Load attendance file
        df = pd.read_csv(file_path)

        # ✅ Normalize column names
        df.columns = [str(c).strip().title().replace(" ", "") for c in df.columns]

        # ✅ Check if the student has already marked attendance
        if matric:
            already = df[
                (df["Studentname"].str.lower() == name.strip().lower()) &
                (df["Matric"].str.lower() == matric.strip().lower())
            ]
        else:
            already = df[
                (df["Studentname"].str.lower() == name.strip().lower())
            ]

        return not already.empty

    except Exception as e:
        st.error(f"⚠️ Error checking attendance: {e}")
        return False

def mark_attendance_entry(course_code, name, matric, week):
    """Save attendance in week-by-week files, with safety checks and no duplicates."""
    try:
        # 📁 Folder for attendance files
        attendance_folder = os.path.join("data", "attendance")
        os.makedirs(attendance_folder, exist_ok=True)

        # 📄 File for the current week
        file_path = os.path.join(attendance_folder, f"{course_code}_Week_{week}.csv")

        # ✅ Load or create the file
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
            except Exception:
                # File exists but broken, recreate cleanly
                df = pd.DataFrame(columns=["StudentName", "Matric", "Week", "Status", "Timestamp"])
        else:
            df = pd.DataFrame(columns=["StudentName", "Matric", "Week", "Status", "Timestamp"])

        # ✅ Normalize columns
        df.columns = [str(c).strip().title().replace(" ", "") for c in df.columns]
        required = ["StudentName", "Matric", "Week", "Status", "Timestamp"]
        for col in required:
            if col not in df.columns:
                df[col] = None

        # ✅ Clean dataframe
        df = df.loc[:, ~df.columns.duplicated()]
        df = df.loc[:, ~df.columns.str.contains("^Unnamed", case=False, na=False)]
        df.reset_index(drop=True, inplace=True)

        # ✅ Convert columns to strings
        for col in ["StudentName", "Matric", "Week"]:
            df[col] = df[col].astype(str).fillna("")

        # ✅ Prevent duplicate attendance for same student + week
        already = df[
            (df["StudentName"].str.lower() == name.strip().lower()) &
            (df["Matric"].str.lower() == matric.strip().lower())
        ]
        if not already.empty:
            return False  # Already marked

        # ✅ Append new attendance record
        new_entry = {
            "StudentName": name.strip(),
            "Matric": matric.strip(),
            "Week": str(week),
            "Status": "Present",
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Error saving attendance: {e}")
        return False



# ---------------------- Helper ---------------------- #
def clean_text(val):
    return str(val or "").strip()

def load_lectures(course_code):
    """Load lecture CSV or create new if missing"""
    try:
        file_path = get_file(course_code, "lectures")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        if not os.path.exists(file_path):
            pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment"]).to_csv(file_path, index=False)
            st.info(f"📘 Created new lecture file for {course_code}. Lecture content will appear once added by Admin.")

        lectures_df = pd.read_csv(file_path)
        st.session_state["lectures_df"] = lectures_df
        return lectures_df

    except Exception as e:
        st.error(f"⚠️ Unable to load lecture file for {course_code}: {e}")
        st.stop()

def get_remaining_time(course_code, week):
    """Check remaining seconds of classwork based on admin timer"""
    key = f"{course_code}_{week}_cw_end"
    if key in st.session_state:
        remaining = st.session_state[key] - datetime.now()
        return max(int(remaining.total_seconds()), 0)
    return 0

# =============================================
# PERSISTENT STORAGE FUNCTIONS
# =============================================

ATTENDANCE_STATUS_FILE = "attendance_status.json"

def init_attendance_status():
    """Initialize the attendance status file if it doesn't exist"""
    if not os.path.exists(ATTENDANCE_STATUS_FILE):
        default_status = {}
        with open(ATTENDANCE_STATUS_FILE, 'w') as f:
            json.dump(default_status, f)

def get_attendance_status(course_code, week):
    """Get attendance status for a specific course and week"""
    init_attendance_status()
    
    try:
        with open(ATTENDANCE_STATUS_FILE, 'r') as f:
            status_data = json.load(f)
        
        week_key = week.replace(" ", "")
        key = f"{course_code}_{week_key}"
        
        return status_data.get(key, {"is_open": False, "open_time": None})
    except Exception as e:
        st.error(f"Error reading attendance status: {e}")
        return {"is_open": False, "open_time": None}

def set_attendance_status(course_code, week, is_open, open_time=None):
    """Set attendance status for a specific course and week"""
    init_attendance_status()
    
    try:
        with open(ATTENDANCE_STATUS_FILE, 'r') as f:
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
        
        with open(ATTENDANCE_STATUS_FILE, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error setting attendance status: {e}")
        return False

def get_all_attendance_status():
    """Get all attendance status for debugging"""
    init_attendance_status()
    
    try:
        with open(ATTENDANCE_STATUS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def has_marked_attendance(course_code, week, name, matric):
    """Check if student has already marked attendance"""
    try:
        week_key = week.replace(" ", "")
        attendance_file = f"attendance_{course_code}_{week_key}.csv"
        
        if not os.path.exists(attendance_file):
            return False
        
        df = pd.read_csv(attendance_file)
        
        # Convert to string and clean data
        df['Name'] = df['Name'].astype(str).str.strip().str.lower()
        df['Matric'] = df['Matric'].astype(str).str.strip().str.lower()
        
        name_clean = name.strip().lower()
        matric_clean = matric.strip().lower()
        
        # Check for existing entry
        existing = df[(df['Name'] == name_clean) & (df['Matric'] == matric_clean)]
        return len(existing) > 0
        
    except Exception as e:
        st.error(f"⚠️ Error checking attendance: {e}")
        return True  # Prevent marking if error

def get_file(course_code, file_type):
    """Get file path for course-specific files"""
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    
    if file_type == "lectures":
        return os.path.join(data_dir, f"{course_code}_lectures.csv")
    elif file_type == "classwork":
        return os.path.join(data_dir, f"{course_code}_classwork.csv")
    elif file_type == "seminar":
        return os.path.join(data_dir, f"{course_code}_seminar.csv")
    else:
        return os.path.join(data_dir, f"{course_code}_{file_type}.csv")

def get_video_files(course_code):
    """Get list of video files for a course"""
    base_dir = "data"
    video_dir = os.path.join(base_dir, course_code, "videos")
    
    if not os.path.exists(video_dir):
        return []
    
    video_files = sorted([f for f in os.listdir(video_dir) 
                         if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])
    return video_files

def delete_video(course_code, video_name):
    """Delete a video file"""
    try:
        base_dir = "data"
        video_dir = os.path.join(base_dir, course_code, "videos")
        video_path = os.path.join(video_dir, video_name)
        
        if os.path.exists(video_path):
            os.remove(video_path)
            return True
        return False
    except Exception as e:
        st.error(f"Error deleting video: {e}")
        return False

import os
import pandas as pd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import streamlit as st

LECTURE_FILE = get_file(course_code, "lectures")
# ===============================================================
# 🧱 HELPER: Ensure All Required Directories Exist
# ===============================================================
def ensure_directories():
    """Create all required folders used in student/admin dashboards."""
    dirs = [
        "data",
        "uploads",
        "student_uploads",
        "scores",
        "modules",
        "classwork_status",
        "video_lectures",
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

# Classwork status management

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
                return True  # Classwork was closed
        except Exception as e:
            st.error(f"Error in classwork auto-close: {e}")
    
    return False  # Classwork remains open

def save_classwork(name, matric, week, answers):
    """Save classwork submissions"""
    try:
        classwork_file = CLASSWORK_FILE
        
        # Create submission data
        submission_data = {
            'Name': name,
            'Matric': matric,
            'Week': week,
            'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'Answers': json.dumps(answers)  # Store answers as JSON string
        }
        
        # Save to CSV
        if os.path.exists(classwork_file):
            df = pd.read_csv(classwork_file)
            # Check if student already submitted for this week
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
        
def get_classwork_status(course_code, week):
    """Get classwork status for a specific course and week"""
    try:
        with open(ATTENDANCE_STATUS_FILE, 'r') as f:
            status_data = json.load(f)
        
        week_key = week.replace(" ", "")
        key = f"classwork_{course_code}_{week_key}"
        
        return status_data.get(key, {"is_open": False, "open_time": None})
    except Exception as e:
        return {"is_open": False, "open_time": None}

def set_classwork_status(course_code, week, is_open, open_time=None):
    """Set classwork status for a specific course and week"""
    try:
        with open(ATTENDANCE_STATUS_FILE, 'r') as f:
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
        
        with open(ATTENDANCE_STATUS_FILE, 'w') as f:
            json.dump(status_data, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Error setting classwork status: {e}")
        return False
                        
# ===============================================================
# 🎓 STUDENT VIEW DASHBOARD
# ===============================================================
def student_view(course_code):
    if st.session_state.get("role") != "Student":
        return
    # Initialize student identity in session state
    if "student_identity" not in st.session_state:
        st.session_state.student_identity = {"name": "", "matric": ""}
    
    # Get student identity from session state
    student_name = st.session_state.student_identity["name"]
    student_matric = st.session_state.student_identity["matric"]
    # ✅ Always ensure required folders exist first
    ensure_directories()

    st.title("🎓 Student Dashboard")
    st.info("Welcome! Access your lectures, upload assignments, and mark attendance here.")
    # 🔄 Auto-refresh after attendance marking
    if st.session_state.get("refresh_needed", False):
        st.session_state["refresh_needed"] = False  # Reset flag
        st.rerun()
        # ✅ Display success/info message after refresh
    if "attendance_message" in st.session_state:
        msg = st.session_state["attendance_message"]
        if "successfully" in msg:
            st.success(msg)
        else:
            st.info(msg)
        del st.session_state["attendance_message"]

    # 🎓 COURSE SELECTION
    course_code = st.selectbox(
        "Select Course",
        ["MCB221", "BCH201", "BIO203", "BIO113", "BIO306"]
    )

    # ===============================================================
    # 📘 LOAD LECTURES WITH PDF SUPPORT
    # ===============================================================
    try:
        if "lectures_df" in st.session_state and st.session_state["lectures_df"] is not None:
            lectures_df = st.session_state["lectures_df"]
        else:
            LECTURE_FILE = get_file(course_code, "lectures")
            os.makedirs(os.path.dirname(LECTURE_FILE), exist_ok=True)

            if not os.path.exists(LECTURE_FILE):
                # Create blank structure if missing
                lectures_df = pd.DataFrame(
                    columns=["Week", "Topic", "Brief", "Assignment", "Classwork", "PDF_File"]
                )
                lectures_df.to_csv(LECTURE_FILE, index=False)
            else:
                lectures_df = pd.read_csv(LECTURE_FILE)

        # Ensure essential columns exist
        for col in ["Week", "Topic", "Brief", "Assignment", "Classwork", "PDF_File"]:
            if col not in lectures_df.columns:
                lectures_df[col] = ""

        st.session_state["lectures_df"] = lectures_df

    except Exception as e:
        st.error(f"⚠️ Error loading lecture file: {e}")
        return


# 🕒 ATTENDANCE FORM
# -------------------------------
    with st.form(f"{course_code}_attendance_form"):
        name = st.text_input("Full Name", 
                        value=student_name,  # Pre-fill with existing name
                        key=f"{course_code}_student_name")
        matric = st.text_input("Matric Number", 
                          value=student_matric,  # Pre-fill with existing matric
                          key=f"{course_code}_student_matric")
        week = st.selectbox(
            "Select Week",
            [f"Week {i}" for i in range(1, 16)],
            key=f"{course_code}_att_week"
    )
        submit_attendance = st.form_submit_button("✅ Mark Attendance", use_container_width=True)

# -------------------------------
# 🧾 ATTENDANCE VALIDATION
# -------------------------------
    if submit_attendance:
        if not name.strip() or not matric.strip():
            st.warning("Please enter your full name and matric number.")
            st.stop()

    # Save identity to session state
        st.session_state.student_identity = {"name": name.strip(), "matric": matric.strip()}
    
    # ✅ Use the EXACT same key format as admin
        week_key = week.replace(" ", "")
        attendance_key = f"att_open_{course_code}_{week_key}"
    
    # Rest of your attendance validation code...

        # -------------------------------
# 🧾 ATTENDANCE VALIDATION
# -------------------------------
    if submit_attendance:
        if not name.strip() or not matric.strip():
            st.warning("Please enter your full name and matric number.")
            st.stop()

    # ✅ Check if attendance is open
        status_data = get_attendance_status(course_code, week)
        is_attendance_open = status_data.get("is_open", False)

        if not is_attendance_open:
            st.error("🚫 Attendance for this course is currently closed. Please wait for your lecturer to open it.")
            st.stop()

    # ✅ Prevent duplicate marking
        if has_marked_attendance(course_code, week, name, matric):
            st.session_state["attendance_message"] = f"✅ Attendance already marked for {course_code} - Week {week}."
            st.session_state["refresh_needed"] = True
            st.rerun()

    # ✅ Mark attendance
        ok = mark_attendance_entry(course_code, name, matric, week)
        if ok:
            st.session_state["attendance_message"] = f"🎉 Attendance recorded successfully for {course_code} - Week {week}."
            st.session_state["refresh_needed"] = True
            st.rerun()
        else:
            st.error("⚠️ Failed to record attendance. Try again later.")
        
     # ===============================================================
    # 📖 DISPLAY LECTURES WITH PDF DOWNLOADS AND CLASSWORK
    # ===============================================================
    st.header(f"📚 {course_code} Lecture Materials")
    
    # Define CLASSWORK_FILE here
    CLASSWORK_FILE = get_file(course_code, "classwork")
    
    if lectures_df.empty or lectures_df["Week"].isna().all():
        st.info("No lecture materials available yet. Check back later!")
        return

    # Display each week's materials
    for _, row in lectures_df.iterrows():
        if pd.isna(row["Week"]) or row["Week"] == "":
            continue
            
        week = row["Week"]  # Define week variable for this iteration
            
        with st.expander(f"📖 {row['Week']}: {row['Topic']}", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if row["Brief"] and str(row["Brief"]).strip():
                    st.markdown(f"**Description:** {row['Brief']}")
                
                # 🧩 Classwork Section - FIXED: use session state identity
                classwork_text = str(row.get("Classwork", "") or "").strip()
                if classwork_text:
                    st.markdown("### 🧩 Classwork Questions")

    # Split questions by semicolon
                    questions = [q.strip() for q in classwork_text.split(";") if q.strip()]

                    if questions:
        # Check if classwork is open
                        classwork_status = is_classwork_open(course_code, week)

                        with st.form(f"cw_form_{week.replace(' ', '_')}"):  # Unique key for each week
                            st.write("**Answer the following questions:**")

            # Create answer inputs
                            answers = []
                            for i, question in enumerate(questions):
                                st.write(f"**Q{i+1}:** {question}")
                                answer = st.text_area(
                                    f"Your answer for Q{i+1}",
                                        placeholder=f"Type your answer for Q{i+1} here...",
                                        key=f"q{i}_{week.replace(' ', '_')}",  # Unique key
                                        height=100,
                                        disabled=not classwork_status
                )
                                answers.append(answer)
                                if i < len(questions) - 1:  # Don't add divider after last question
                                    st.divider()

            # Submit button
                            submit_cw = st.form_submit_button(
                                "📤 Submit Classwork Answers", 
                                    disabled=not classwork_status,
                                    use_container_width=True
            )

            # Auto-close check
                            close_classwork_after_20min(course_code, week)

                            if submit_cw:
                # Use session state identity instead of form inputs
                                if not student_name or not student_matric:
                                    st.error("❌ Please mark attendance first to set your identity, or enter your name and matric number in the attendance form.")
                                elif any(not answer.strip() for answer in answers):
                                    st.error("❌ Please answer all questions before submitting.")
                                else:
                    # Save classwork using session state identity
                                    success = save_classwork(student_name, student_matric, week, answers)
                                    if success:
                                        st.balloons()
                                        st.rerun()  # Refresh to show success message
                    else:
                        st.info("No classwork questions available for this week.")
                else:
                    st.info("No classwork assigned for this week yet.")

                # Assignment section
                if row["Assignment"] and str(row["Assignment"]).strip():
                    st.markdown(f"**Assignment:** {row['Assignment']}")
            
            with col2:
                # 🎯 FIXED: PDF Download for students with safe existence check
                pdf_file = row.get("PDF_File", "")
                pdf_file_exists = False
                
                if pdf_file and isinstance(pdf_file, str) and pdf_file.strip():
                    try:
                        pdf_file_exists = os.path.exists(pdf_file)
                    except (TypeError, OSError):
                        pdf_file_exists = False
                
                if pdf_file_exists:
                    try:
                        with open(pdf_file, "rb") as pdf_file_obj:
                            st.download_button(
                                label="📥 Download PDF",
                                data=pdf_file_obj,
                                file_name=os.path.basename(pdf_file),
                                mime="application/pdf",
                                key=f"student_pdf_{row['Week'].replace(' ', '_')}"
                            )
                    except Exception as e:
                        st.error(f"⚠️ Error loading PDF: {e}")
                else:
                    st.info("No PDF available")
      # ===============================================================
        # 🎓 Student Dashboard — View Scores
        # ===============================================================
    st.title("🎓 Student Dashboard — View Scores")

    courses = ["BIO113", "BIO306", "BIO203", "BCH201", "MCB221"]
    course_code = st.selectbox("Select Your Course", courses)
    matric_no = st.text_input("Enter Your Matric Number").strip().upper()
    score_file = os.path.join("scores", f"{course_code.lower()}_scores.csv")

    if os.path.exists(score_file):
        df = pd.read_csv(score_file)

        if matric_no:
            student_scores = df[df["MatricNo"].astype(str).str.upper() == matric_no]
            if not student_scores.empty:
                st.success(f"✅ Scores for Matric Number: {matric_no}")
                st.dataframe(student_scores, use_container_width=True)
                st.download_button(
                    "⬇️ Download Your Scores as CSV",
                    student_scores.to_csv(index=False).encode(),
                    file_name=f"{matric_no}_scores.csv",
                    mime="text/csv"
                    )
            else:
                st.info("No scores found for this matric number yet.")
        else:
            st.warning("Please enter your matric number to view scores.")
            st.warning("Scores have not been uploaded for this course yet.")

        # ===============================================================
        # 📄 ASSIGNMENT, DRAWING & SEMINAR UPLOADS
        # ===============================================================
    st.divider()
    st.subheader("📄 Assignment, Drawing & Seminar Uploads")

        # 📝 Assignment
    student_name_a = st.text_input("Full Name", key=f"{course_code}_a_name")
    matric_a = st.text_input("Matric Number", key=f"{course_code}_a_matric")
    selected_week_a = st.selectbox("Select Week for Assignment", lectures_df["Week"].tolist(), key=f"{course_code}_a_week")
    uploaded_assignment = st.file_uploader("Upload Assignment", type=["pdf", "docx", "jpg", "png"], key=f"{course_code}_a_file")

    if st.button("📤 Submit Assignment", key=f"{course_code}_a_btn"):
        if not student_name_a or not matric_a:
            st.warning("⚠️ Please enter your name and matric number.")
        elif not uploaded_assignment:
            st.warning("⚠️ Please upload your file.")
        else:
            file_path = save_file(course_code, student_name_a, selected_week_a, uploaded_assignment, "assignment")
            if file_path:
                log_submission(course_code, matric_a, student_name_a, selected_week_a, uploaded_assignment.name, "Assignment")
                st.success(f"✅ {student_name_a} ({matric_a}) — Assignment uploaded successfully!")

        # 🎨 Drawing
    st.divider()
    student_name_d = st.text_input("Full Name", key=f"{course_code}_d_name")
    matric_d = st.text_input("Matric Number", key=f"{course_code}_d_matric")
    selected_week_d = st.selectbox("Select Week for Drawing", lectures_df["Week"].tolist(), key=f"{course_code}_d_week")
    uploaded_drawing = st.file_uploader("Upload Drawing", type=["pdf", "jpg", "png"], key=f"{course_code}_d_file")

    if st.button("📤 Submit Drawing", key=f"{course_code}_d_btn"):
        if not student_name_d or not matric_d:
            st.warning("⚠️ Please enter your name and matric number.")
        elif not uploaded_drawing:
            st.warning("⚠️ Please upload your drawing.")
        else:
            file_path = save_file(course_code, student_name_d, selected_week_d, uploaded_drawing, "drawing")
            if file_path:
                log_submission(course_code, matric_d, student_name_d, selected_week_d, uploaded_drawing.name, "Drawing")
                st.success(f"✅ {student_name_d} ({matric_d}) — Drawing uploaded successfully!")

        # 🎤 Seminar
    st.divider()
    student_name_s = st.text_input("Full Name", key=f"{course_code}_s_name")
    matric_s = st.text_input("Matric Number", key=f"{course_code}_s_matric")
    selected_week_s = st.selectbox("Select Week for Seminar", lectures_df["Week"].tolist(), key=f"{course_code}_s_week")
    uploaded_seminar = st.file_uploader("Upload Seminar", type=["pdf", "pptx", "docx"], key=f"{course_code}_s_file")

    if st.button("📤 Submit Seminar", key=f"{course_code}_s_btn"):
        if not student_name_s or not matric_s:
            st.warning("⚠️ Please enter your name and matric number.")
        elif not uploaded_seminar:
            st.warning("⚠️ Please upload your seminar file.")
        else:
            file_path = save_file(course_code, student_name_s, selected_week_s, uploaded_seminar, "seminar")
            if file_path:
                log_submission(course_code, matric_s, student_name_s, selected_week_s, uploaded_seminar.name, "Seminar")
                st.success(f"✅ {student_name_s} ({matric_s}) — Seminar uploaded successfully!")

            # ===============================================================
    # 🎥 VIDEO LECTURES SECTION - ADD TO STUDENT DASHBOARD
    # ===============================================================
    st.header("🎥 Video Lectures")
    
    # Create video directory path (same as admin)
    base_dir = "data"
    video_dir = os.path.join(base_dir, course_code, "videos")
    
    video_files = []
    if os.path.exists(video_dir):
        video_files = sorted([f for f in os.listdir(video_dir) 
                            if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])
    
    if video_files:
        st.success(f"Found {len(video_files)} video lecture(s) available!")
        
        for i, video in enumerate(video_files):
            video_path = os.path.join(video_dir, video)
            
            with st.expander(f"🎬 {video}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    try:
                        # Display video
                        st.video(video_path)
                        
                        # Show video info
                        file_size = os.path.getsize(video_path) / (1024 * 1024)
                        st.caption(f"File size: {file_size:.2f} MB")
                        
                    except Exception as e:
                        st.error(f"⚠️ Cannot play this video: {str(e)}")
                        st.info("The video format might not be supported in your browser. Try downloading it instead.")
                
                with col2:
                    # Download button for students
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


def view_attendance_records(course_code, week):
    """Display attendance records for a specific course and week"""
    try:
        week_key = week.replace(" ", "")
        attendance_file = f"attendance_{course_code}_{week_key}.csv"
        
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
            attendance_file = f"attendance_{course_code}_{week_key}.csv"
            
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

def get_all_courses_attendance():
    """Get attendance summary for all courses"""
    courses = ["MCB221", "BCH201", "BIO203", "BIO113", "BIO306"]
    all_courses_data = []
    
    for course in courses:
        total_students = 0
        weeks_with_data = 0
        
        for week_num in range(1, 16):
            week = f"Week {week_num}"
            week_key = week.replace(" ", "")
            attendance_file = f"attendance_{course}_{week_key}.csv"
            
            if os.path.exists(attendance_file):
                try:
                    df = pd.read_csv(attendance_file)
                    total_students += len(df)
                    weeks_with_data += 1
                except:
                    pass
        
        all_courses_data.append({
            "Course": course,
            "Total Students": total_students,
            "Weeks Recorded": weeks_with_data
        })
    
    return pd.DataFrame(all_courses_data)


def view_student_attendance_details(course_code, week):
    """Display detailed student attendance with search and filtering"""
    try:
        week_key = week.replace(" ", "")
        attendance_file = f"attendance_{course_code}_{week_key}.csv"
        
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
            attendance_file = f"attendance_{course_code}_{week_key}.csv"
            
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
        
def admin_view(course_code):

    st.title("👩‍🏫 Admin Dashboard")

    # -------------------------
    # Authentication
    # -------------------------
    ADMIN_PASS = "bimpe2025class"
    password = st.text_input("Enter Admin Password", type="password", key="admin_password_input")

    if password != ADMIN_PASS:
        st.warning("Enter the correct Admin password to continue.")
        return

    st.session_state["role"] = "Admin"
    st.success(f"✅ Logged in as Admin {course_code}")

    # -------------------------
    # Directory & File Setup
    # -------------------------
    base_dir = "student_uploads"
    scores_dir = "scores"
    modules_dir = "modules"
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(scores_dir, exist_ok=True)
    os.makedirs(modules_dir, exist_ok=True)

   
    # -------------------------
    # Lecture Management
    # -------------------------
    st.header("📚 Lecture Management")
    LECTURE_FILE = get_file(course_code, "lectures")
    ATTENDANCE_FILE = get_file(course_code, "attendance")
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork")
    SEMINAR_FILE = get_file(course_code, "seminar")
    CLASSWORK_FILE = get_file(course_code, "classwork_submissions")

    # Load lectures CSV safely
    if os.path.exists(LECTURE_FILE):
        lectures_df = pd.read_csv(LECTURE_FILE)
        # Clean column names
        lectures_df.columns = lectures_df.columns.str.strip()
    else:
        lectures_df = pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment"])

    # Ensure all required columns exist
    for col in ["Week", "Topic", "Brief", "Classwork", "Assignment"]:
        if col not in lectures_df.columns:
            lectures_df[col] = ""

    # Store in session state
    st.session_state["lectures_df"] = lectures_df

        # Add / Edit Lecture, Classwork & Assignment
    with st.expander("📘 Add / Edit Lecture, Classwork & Assignment", expanded=True):
        week = st.selectbox("Select Week", [f"Week {i}" for i in range(1, 16)])
        lectures_df = st.session_state["lectures_df"]

        if week in lectures_df["Week"].values:
            row_idx = lectures_df[lectures_df["Week"] == week].index[0]
        else:
            new_row = {"Week": week, "Topic": "", "Brief": "", "Classwork": "", "Assignment": "", "PDF_File": ""}
            lectures_df = pd.concat([lectures_df, pd.DataFrame([new_row])], ignore_index=True)
            row_idx = lectures_df[lectures_df["Week"] == week].index[0]
            st.session_state["lectures_df"] = lectures_df

        # Existing text fields
        topic = st.text_input("Topic", value=lectures_df.at[row_idx, "Topic"], key=f"topic_{week}")
        brief = st.text_area("Brief Description", value=lectures_df.at[row_idx, "Brief"], key=f"brief_{week}")
        classwork = st.text_area("Classwork", value=lectures_df.at[row_idx, "Classwork"], key=f"classwork_{week}")
        assignment = st.text_area("Assignment", value=lectures_df.at[row_idx, "Assignment"], key=f"assignment_{week}")

        # 🎯 FIXED: PDF Upload with proper error handling
        st.markdown("**Upload PDF Files (Optional)**")
        
        # Create PDF directory for this course
        pdf_dir = os.path.join("pdfs", course_code)
        os.makedirs(pdf_dir, exist_ok=True)
        
        # PDF Upload
        lecture_pdf = st.file_uploader("Lecture PDF", type=["pdf"], key=f"pdf_{week}")
        
        # 🎯 FIXED: Safe PDF existence check
        current_pdf = lectures_df.at[row_idx, "PDF_File"]
        
        # Check if current_pdf exists and is a valid string path
        pdf_exists = False
        pdf_path_to_use = ""
        
        if current_pdf and isinstance(current_pdf, str) and current_pdf.strip():
            pdf_path_to_use = current_pdf
            try:
                pdf_exists = os.path.exists(current_pdf)
            except (TypeError, OSError) as e:
                st.warning(f"⚠️ Error checking PDF path: {e}")
                pdf_exists = False
        
        # Display current PDF if it exists
        if pdf_exists:
            st.info(f"📎 Current PDF: {os.path.basename(pdf_path_to_use)}")
            
            # Show PDF download button
            try:
                with open(pdf_path_to_use, "rb") as pdf_file:
                    st.download_button(
                        label="📥 Download Current PDF",
                        data=pdf_file,
                        file_name=os.path.basename(pdf_path_to_use),
                        mime="application/pdf",
                        key=f"download_{week}"
                    )
            except Exception as e:
                st.error(f"❌ Error reading PDF file: {e}")
            
            # Option to remove PDF
            if st.button("🗑️ Remove PDF", key=f"remove_{week}"):
                try:
                    if os.path.exists(pdf_path_to_use):
                        os.remove(pdf_path_to_use)
                    lectures_df.at[row_idx, "PDF_File"] = ""
                    st.session_state["lectures_df"] = lectures_df
                    st.success("✅ PDF removed successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error removing PDF: {e}")

        # Handle new PDF upload
        if lecture_pdf is not None:
            # Save PDF to file system
            pdf_filename = f"{course_code}_{week.replace(' ', '')}_{lecture_pdf.name}"
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            
            try:
                with open(pdf_path, "wb") as f:
                    f.write(lecture_pdf.getbuffer())
                
                # Update DataFrame with PDF path
                lectures_df.at[row_idx, "PDF_File"] = pdf_path
                st.session_state["lectures_df"] = lectures_df
                st.success(f"✅ PDF uploaded successfully: {lecture_pdf.name}")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error saving PDF: {e}")

        # Update the DataFrame with text fields
        lectures_df.at[row_idx, "Topic"] = topic
        lectures_df.at[row_idx, "Brief"] = brief
        lectures_df.at[row_idx, "Classwork"] = classwork
        lectures_df.at[row_idx, "Assignment"] = assignment

        # Save button for all changes
        if st.button("💾 Save Changes", key=f"save_{week}"):
            try:
                # Save to CSV
                lectures_df.to_csv(LECTURE_FILE, index=False)
                st.session_state["lectures_df"] = lectures_df
                st.success("✅ All changes saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving changes: {e}")
            
    
    # 🕒 Attendance Control (Admin)
    # -------------------------------
    st.subheader("🎛 Attendance Control")

    selected_week = st.selectbox(
        "Select Week", 
        [f"Week {i}" for i in range(1, 16)], 
        key=f"{course_code}_week_select"
    )

    # Get current status from persistent storage
    current_status = get_attendance_status(course_code, selected_week)
    is_currently_open = current_status.get("is_open", False)

    # Display current status
    if is_currently_open:
        st.success(f"✅ Attendance is CURRENTLY OPEN for {course_code} - {selected_week}")
    else:
        st.warning(f"🚫 Attendance is CURRENTLY CLOSED for {course_code} - {selected_week}")

    # Use buttons for attendance control
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔓 OPEN Attendance", use_container_width=True, type="primary"):
            success = set_attendance_status(course_code, selected_week, True, datetime.now())
            if success:
                st.success(f"✅ Attendance OPENED for {course_code} - {selected_week}")
                st.rerun()
            else:
                st.error("❌ Failed to open attendance")

    with col2:
        if st.button("🔒 CLOSE Attendance", use_container_width=True, type="secondary"):
            success = set_attendance_status(course_code, selected_week, False)
            if success:
                st.warning(f"🚫 Attendance CLOSED for {course_code} - {selected_week}")
                st.rerun()
            else:
                st.error("❌ Failed to close attendance")

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

    # 🎯 ENHANCED ATTENDANCE VIEWING
    # -------------------------------
    st.header("📊 Attendance Records")
    
    # Create tabs for different viewing options
    tab1, tab2, tab3 = st.tabs([
        "👥 Student Details", 
        "📈 Weekly Summary", 
        "📋 Complete History"
    ])
    
    with tab1:
        st.subheader("Student Attendance Details")
        view_week = st.selectbox(
            "Select Week to View", 
            [f"Week {i}" for i in range(1, 16)], 
            key=f"{course_code}_view_week"
        )
        view_student_attendance_details(course_code, view_week)
    
    with tab2:
        st.subheader("Weekly Attendance Summary")
        show_attendance_summary(course_code)
    
    with tab3:
        view_all_students_attendance(course_code)

    # 🌐 GLOBAL OVERVIEW
    # -------------------------------
    st.header("🌐 Global Attendance Overview")

    if st.button("🔄 Refresh Global Overview", type="secondary"):
        global_df = get_all_courses_attendance()
        
        if not global_df.empty:
            st.dataframe(global_df, use_container_width=True)
            
            # Show some metrics
            total_all_courses = global_df["Total Students"].sum()
            st.metric("Total Attendance Across All Courses", total_all_courses)
        else:
            st.info("No attendance data found for any course.")

    # --------------------------------------
    # CLASSWORK & SEMINAR RECORDS (unchanged)
    # --------------------------------------
    for file, label in [
        (CLASSWORK_FILE, "Classwork Submissions"),
        (SEMINAR_FILE, "Seminar Submissions")
    ]:
        st.divider()
        st.markdown(f"### {label}")

        if os.path.exists(file):
            try:
                df = pd.read_csv(file)
                st.dataframe(df, use_container_width=True)

                col1, col2 = st.columns([2, 1])

                with col1:
                    st.download_button(
                        label=f"⬇️ Download {label} CSV",
                        data=df.to_csv(index=False).encode(),
                        file_name=os.path.basename(file),
                        mime="text/csv",
                        key=f"{label}_download"
                    )

                with col2:
                    if st.button(f"🗑️ Delete {label}", key=f"{label}_delete"):
                        os.remove(file)
                        st.warning(f"⚠️ {label} deleted successfully.")
                        st.rerun()

            except Exception as e:
                st.error(f"Failed to read {label}: {e}")
        else:
            st.info(f"No {label.lower()} yet.")

       # 📋 Classwork Submissions Viewing
    # -------------------------------
    st.header("📝 Classwork Submissions")
    
    if os.path.exists(CLASSWORK_FILE):
        try:
            classwork_df = pd.read_csv(CLASSWORK_FILE)
            
            if not classwork_df.empty:
                # Filter options
                col1, col2 = st.columns(2)
                with col1:
                    view_week = st.selectbox(
                        "View submissions for week:",
                        ["All Weeks"] + [f"Week {i}" for i in range(1, 16)],
                        key="classwork_view_week"
                    )
                
                with col2:
                    search_student = st.text_input("🔍 Search student:", placeholder="Name or Matric...")
                
                # Filter data
                filtered_df = classwork_df.copy()
                if view_week != "All Weeks":
                    filtered_df = filtered_df[filtered_df['Week'] == view_week]
                
                if search_student:
                    filtered_df = filtered_df[
                        filtered_df['Name'].str.contains(search_student, case=False, na=False) |
                        filtered_df['Matric'].str.contains(search_student, case=False, na=False)
                    ]
                
                if not filtered_df.empty:
                    st.dataframe(filtered_df, use_container_width=True)
                    
                    # Download option
                    csv_data = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Classwork Submissions",
                        data=csv_data,
                        file_name=f"classwork_{course_code}_submissions.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    # View individual answers
                    st.subheader("📖 View Detailed Answers")
                    selected_index = st.selectbox(
                        "Select submission to view answers:",
                        range(len(filtered_df)),
                        format_func=lambda x: f"{filtered_df.iloc[x]['Name']} - {filtered_df.iloc[x]['Matric']} - {filtered_df.iloc[x]['Week']}"
                    )
                    
                    if selected_index is not None:
                        submission = filtered_df.iloc[selected_index]
                        st.write(f"**Student:** {submission['Name']} ({submission['Matric']})")
                        st.write(f"**Week:** {submission['Week']}")
                        st.write(f"**Submitted:** {submission['Timestamp']}")
                        
                        # Parse and display answers
                        try:
                            answers = json.loads(submission['Answers'])
                            st.write("**Answers:**")
                            for i, answer in enumerate(answers):
                                st.write(f"**Q{i+1}:** {answer}")
                                st.divider()
                        except:
                            st.write("**Answers:** Unable to parse answers")
                else:
                    st.info("No classwork submissions found matching your criteria.")
            else:
                st.info("No classwork submissions yet.")
                
        except Exception as e:
            st.error(f"Error loading classwork submissions: {e}")
    else:
        st.info("No classwork submissions file found yet.")
    # -------------------------
    # View & Grade Uploaded Files
    # -------------------------
    st.divider()
    st.subheader("📂 View Student Submissions & Grade Them")
    with st.expander("Expand to view and grade student submissions", expanded=True):
        upload_types = ["assignment", "drawing", "seminar"]
        for upload_type in upload_types:
            st.markdown(f"### 📄 {upload_type.capitalize()} Uploads")
            upload_dir = os.path.join(base_dir, course_code, upload_type)
            if not os.path.exists(upload_dir):
                st.info(f"No {upload_type} uploaded yet.")
                continue

            files = sorted([f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))])
            if not files:
                st.info(f"No {upload_type} uploaded yet.")
                continue

            for file in files:
                file_path = os.path.join(upload_dir, file)
                unique_key = f"{course_code}_{upload_type}_{file}"
                st.write(f"📎 **{file}**")

                try:
                    with open(file_path, "rb") as fh:
                        st.download_button(
                            label=f"⬇️ Download {file}",
                            data=fh,
                            file_name=file,
                            mime="application/octet-stream",
                            key=f"{unique_key}_download"
                        )
                except Exception:
                    st.warning("⚠️ Cannot open file for download.")

                score = st.number_input(f"Enter score for {file}", min_value=0, max_value=100, value=0, key=f"{unique_key}_score")
                if st.button(f"💾 Save Score ({file})", key=f"{unique_key}_save"):
                    try:
                        parts = file.rsplit(".", 1)[0].split("_")
                        if len(parts) < 3:
                            st.warning(f"Invalid filename format: {file}. Expected Name_Matric_Week.ext")
                            continue

                        student_name = parts[0].strip().title()
                        matric = parts[1].strip().upper()
                        week = parts[2].strip().title()

                        os.makedirs(scores_dir, exist_ok=True)
                        score_file = os.path.join(scores_dir, f"{course_code.lower()}_scores.csv")
                        required_columns = ["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Total", "Grade"]

                        if os.path.exists(score_file):
                            df_scores = pd.read_csv(score_file)
                        else:
                            df_scores = pd.DataFrame(columns=required_columns)

                        for col in required_columns:
                            if col not in df_scores.columns:
                                df_scores[col] = 0 if col in ["Assignment", "Test", "Practical", "Exam", "Total"] else ""

                        # Save the single score to Assignment field by default (legacy behavior)
                        # If you prefer another default mapping for upload scoring, change here.
                        df_scores.loc[
                            (df_scores["StudentName"].astype(str).str.lower() == student_name.lower()) &
                            (df_scores["MatricNo"].astype(str).str.lower() == matric.lower()) &
                            (df_scores["Week"].astype(str).str.lower() == week.lower()),
                            "Assignment"
                        ] = score

                        # If no existing row, add one
                        if not ((df_scores["StudentName"].astype(str).str.lower() == student_name.lower()) &
                                (df_scores["MatricNo"].astype(str).str.lower() == matric.lower()) &
                                (df_scores["Week"].astype(str).str.lower() == week.lower())).any():
                            new_row = {
                                "StudentName": student_name,
                                "MatricNo": matric,
                                "Week": week,
                                "Assignment": score,
                                "Test": 0,
                                "Practical": 0,
                                "Exam": 0,
                                "Total": 0,
                                "Grade": ""
                            }
                            df_scores = pd.concat([df_scores, pd.DataFrame([new_row])], ignore_index=True)

                        # Compute Total & Grade using weights:
                        # Assignment: 20%, Test: 20%, Practical: 10%, Exam: 50%
                        try:
                            df_scores["Total"] = (
                                df_scores.get("Assignment", 0).fillna(0).astype(float) * 0.20 +
                                df_scores.get("Test", 0).fillna(0).astype(float) * 0.20 +
                                df_scores.get("Practical", 0).fillna(0).astype(float) * 0.10 +
                                df_scores.get("Exam", 0).fillna(0).astype(float) * 0.50
                            ).round(1)
                        except Exception:
                            df_scores["Total"] = 0

                        # Grade scheme
                        def compute_grade(total):
                            try:
                                t = float(total)
                            except Exception:
                                return ""
                            if t >= 70: return "A"
                            if t >= 60: return "B"
                            if t >= 50: return "C"
                            if t >= 45: return "D"
                            if t >= 40: return "E"
                            return "F"

                        df_scores["Grade"] = df_scores["Total"].apply(compute_grade)

                        df_scores.to_csv(score_file, index=False)
                        st.success(f"✅ Score saved for {student_name} ({matric}) - {week}")
                    except Exception as e:
                        st.error(f"❌ Failed to save score file: {e}")

    # -------------------------
    # Grading — Manual Entry & CSV Upload
    # -------------------------
    st.divider()
    st.subheader("🧮 Grading — Manual Entry & CSV Upload")

    score_file = os.path.join(scores_dir, f"{course_code.lower()}_scores.csv")
    os.makedirs(scores_dir, exist_ok=True)

    # Option: Upload CSV with columns: StudentName, MatricNo, Week, Assignment, Test, Practical, Exam
    st.markdown("**Option A — Upload scores CSV** (columns: StudentName, MatricNo, Week, Assignment, Test, Practical, Exam)")
    uploaded_scores_csv = st.file_uploader("Upload scores CSV (optional)", type=["csv"], key=f"{course_code}_scores_csv")

    if uploaded_scores_csv is not None:
        try:
            uploaded_df = pd.read_csv(uploaded_scores_csv)
            # Ensure columns exist
            for col in ["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam"]:
                if col not in uploaded_df.columns:
                    uploaded_df[col] = 0
            # Compute totals and grades for uploaded rows
            uploaded_df["Total"] = (
                uploaded_df["Assignment"].fillna(0).astype(float) * 0.20 +
                uploaded_df["Test"].fillna(0).astype(float) * 0.20 +
                uploaded_df["Practical"].fillna(0).astype(float) * 0.10 +
                uploaded_df["Exam"].fillna(0).astype(float) * 0.50
            ).round(1)
            def compute_grade_scalar(t):
                try:
                    t = float(t)
                except Exception:
                    return ""
                if t >= 70: return "A"
                if t >= 60: return "B"
                if t >= 50: return "C"
                if t >= 45: return "D"
                if t >= 40: return "E"
                return "F"
            uploaded_df["Grade"] = uploaded_df["Total"].apply(compute_grade_scalar)

            # Merge with existing score file if present
            if os.path.exists(score_file):
                existing_df = pd.read_csv(score_file)
            else:
                existing_df = pd.DataFrame(columns=["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Total", "Grade"])

            # For each uploaded row, update or append
            for _, r in uploaded_df.iterrows():
                mask = (
                    (existing_df["StudentName"].astype(str).str.lower() == str(r["StudentName"]).lower()) &
                    (existing_df["MatricNo"].astype(str).str.lower() == str(r["MatricNo"]).lower()) &
                    (existing_df["Week"].astype(str).str.lower() == str(r["Week"]).lower())
                )
                if mask.any():
                    existing_df.loc[mask, ["Assignment", "Test", "Practical", "Exam", "Total", "Grade"]] = [
                        r["Assignment"], r["Test"], r["Practical"], r["Exam"], r["Total"], r["Grade"]
                    ]
                else:
                    new_row = {
                        "StudentName": r["StudentName"],
                        "MatricNo": r["MatricNo"],
                        "Week": r["Week"],
                        "Assignment": r["Assignment"],
                        "Test": r["Test"],
                        "Practical": r["Practical"],
                        "Exam": r["Exam"],
                        "Total": r["Total"],
                        "Grade": r["Grade"]
                    }
                    existing_df = pd.concat([existing_df, pd.DataFrame([new_row])], ignore_index=True)

            existing_df.to_csv(score_file, index=False)
            st.success("✅ Uploaded scores processed and saved.")
            st.dataframe(existing_df, use_container_width=True)

        except Exception as e:
            st.error(f"Failed to process uploaded CSV: {e}")

    st.markdown("---")
    # Option: Manual entry
    st.markdown("**Option B — Manual entry (per student & week)**")
    # Load existing scores or create template
    if os.path.exists(score_file):
        try:
            scores_df = pd.read_csv(score_file)
        except Exception:
            scores_df = pd.DataFrame(columns=["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Total", "Grade"])
    else:
        scores_df = pd.DataFrame(columns=["StudentName", "MatricNo", "Week", "Assignment", "Test", "Practical", "Exam", "Total", "Grade"])

    # Inputs for manual entry
    m_name = st.text_input("Student Name (manual)", key=f"{course_code}_manual_name")
    m_matric = st.text_input("Matric Number (manual)", key=f"{course_code}_manual_matric")
    m_week = st.selectbox("Week (manual)", lectures_df["Week"].tolist() if not lectures_df.empty else [f"Week {i}" for i in range(1, 16)], key=f"{course_code}_manual_week")
    m_assignment = st.number_input("Assignment score (0-100)", min_value=0, max_value=100, value=0, key=f"{course_code}_manual_assignment")
    m_test = st.number_input("Test score (0-100)", min_value=0, max_value=100, value=0, key=f"{course_code}_manual_test")
    m_practical = st.number_input("Practical score (0-100)", min_value=0, max_value=100, value=0, key=f"{course_code}_manual_practical")
    m_exam = st.number_input("Exam score (0-100)", min_value=0, max_value=100, value=0, key=f"{course_code}_manual_exam")

    if st.button("💾 Save Manual Score"):
        if not m_name or not m_matric:
            st.warning("Please provide student name and matric number.")
        else:
            try:
                # compute total and grade
                total = round(m_assignment * 0.20 + m_test * 0.20 + m_practical * 0.10 + m_exam * 0.50, 1)
                def compute_grade_value(t):
                    if t >= 70: return "A"
                    if t >= 60: return "B"
                    if t >= 50: return "C"
                    if t >= 45: return "D"
                    if t >= 40: return "E"
                    return "F"
                grade = compute_grade_value(total)

                mask = (
                    (scores_df["StudentName"].astype(str).str.lower() == m_name.lower()) &
                    (scores_df["MatricNo"].astype(str).str.lower() == m_matric.lower()) &
                    (scores_df["Week"].astype(str).str.lower() == m_week.lower())
                )

                if mask.any():
                    scores_df.loc[mask, ["Assignment", "Test", "Practical", "Exam", "Total", "Grade"]] = [
                        m_assignment, m_test, m_practical, m_exam, total, grade
                    ]
                else:
                    new_row = {
                        "StudentName": m_name.title(),
                        "MatricNo": m_matric.upper(),
                        "Week": m_week,
                        "Assignment": m_assignment,
                        "Test": m_test,
                        "Practical": m_practical,
                        "Exam": m_exam,
                        "Total": total,
                        "Grade": grade
                    }
                    scores_df = pd.concat([scores_df, pd.DataFrame([new_row])], ignore_index=True)

                scores_df.to_csv(score_file, index=False)
                st.success(f"✅ Manual score saved for {m_name} ({m_matric}) - {m_week}")
            except Exception as e:
                st.error(f"Failed to save manual score: {e}")

    # Show scores preview
    if not scores_df.empty:
        st.markdown("### Current Scores Preview")
        st.dataframe(scores_df.sort_values(["StudentName", "Week"]), use_container_width=True)
        st.download_button("⬇️ Download Scores CSV", data=scores_df.to_csv(index=False).encode(), file_name=os.path.basename(score_file), mime="text/csv")

    # -------------------------
    # Reset All Scores (danger)
    # -------------------------
    st.markdown("---")
    st.warning("Reset all scores will permanently delete the scores CSV for this course.")
    if st.button("🧹 Reset All Scores for this Course (Irreversible)"):
        try:
            if os.path.exists(score_file):
                os.remove(score_file)
                st.success("✅ Scores file removed.")
                try:
                    st.cache_data.clear()
                except Exception:
                    pass
            else:
                st.info("No scores file to remove.")
        except Exception as e:
            st.error(f"Failed to reset scores: {e}")

        # -------------------------
    # Video upload & management - FIXED VERSION
    # -------------------------
    st.divider()
    st.subheader("🎥 Upload & Manage Video Lectures")

    # Create video directory with proper structure
    base_dir = "data"
    video_dir = os.path.join(base_dir, course_code, "videos")
    os.makedirs(video_dir, exist_ok=True)

    # Video upload section
    st.markdown("### 📤 Upload New Video")
    uploaded_video = st.file_uploader(
        "Upload Lecture Video (MP4, MOV, AVI, MKV)", 
        type=["mp4", "mov", "avi", "mkv"], 
        key=f"{course_code}_video_upload"
    )
    
    if uploaded_video is not None:
        # Display video info
        file_size = uploaded_video.size / (1024 * 1024)  # Convert to MB
        st.write(f"**File:** {uploaded_video.name}")
        st.write(f"**Size:** {file_size:.2f} MB")
        st.write(f"**Type:** {uploaded_video.type}")
        
        # Check file size (Streamlit has ~200MB limit by default)
        if file_size > 500:  # 500MB limit
            st.error("❌ File too large! Please upload videos under 500MB.")
        else:
            try:
                # Generate safe filename
                original_name = uploaded_video.name
                safe_name = "".join(c for c in original_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                
                save_path = os.path.join(video_dir, safe_name)
                
                # Handle duplicate files
                base_name, ext = os.path.splitext(safe_name)
                counter = 1
                while os.path.exists(save_path):
                    save_path = os.path.join(video_dir, f"{base_name}_{counter}{ext}")
                    counter += 1
                
                # Save the file with progress
                with st.spinner(f"Uploading {safe_name}... This may take a moment for large files."):
                    with open(save_path, "wb") as f:
                        f.write(uploaded_video.getbuffer())
                
                st.success(f"✅ Video uploaded successfully: {os.path.basename(save_path)}")
                
                # Clear the uploader after successful upload
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to save video: {str(e)}")
                st.info("💡 **Troubleshooting tips:**")
                st.info("- Try compressing the video file")
                st.info("- Check available disk space")
                st.info("- Try a different video format")

    # Display existing videos
    st.markdown("### 📚 Existing Lecture Videos")
    
    video_files = []
    if os.path.exists(video_dir):
        video_files = sorted([f for f in os.listdir(video_dir) 
                            if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])
    
    if video_files:
        st.write(f"Found {len(video_files)} video(s)")
        
        for i, video in enumerate(video_files):
            video_path = os.path.join(video_dir, video)
            
            with st.expander(f"🎬 {video}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    try:
                        # Display video with controls
                        st.video(video_path)
                        
                        # Show video info
                        file_size = os.path.getsize(video_path) / (1024 * 1024)
                        st.caption(f"Size: {file_size:.2f} MB")
                        
                    except Exception as e:
                        st.error(f"❌ Cannot preview video: {str(e)}")
                        st.info("The video file might be corrupted or in an unsupported format.")
                
                with col2:
                    # Download button
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
                    
                    # Delete button
                    if st.button("🗑️ Delete", key=f"delete_{i}"):
                        try:
                            os.remove(video_path)
                            st.success(f"✅ Video deleted: {video}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Failed to delete: {str(e)}")
    else:
        st.info("No videos uploaded yet. Use the uploader above to add lecture videos.")

    # -------------------------------------
# ✅ Attendance Columns Check
# -------------------------------------
    if st.button("Check Attendance Columns"):
        file_path = get_file(course_code, "attendance_form")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            st.write(df.columns)
        else:
            st.warning("Attendance file not found!")

# -------------------------------------
    # 🎛 Classwork Control
    # -------------------------------
    st.subheader("🎛 Classwork Control")

    classwork_week = st.selectbox(
        "Select Week for Classwork", 
        [f"Week {i}" for i in range(1, 16)], 
        key=f"{course_code}_classwork_week"
    )

    # Get current classwork status
    current_classwork_status = get_classwork_status(course_code, classwork_week)
    is_classwork_open = current_classwork_status.get("is_open", False)

    # Display current status
    if is_classwork_open:
        st.success(f"✅ Classwork is CURRENTLY OPEN for {course_code} - {classwork_week}")
    else:
        st.warning(f"🚫 Classwork is CURRENTLY CLOSED for {course_code} - {classwork_week}")

    # Classwork control buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔓 OPEN Classwork", use_container_width=True, type="primary"):
            success = set_classwork_status(course_code, classwork_week, True, datetime.now())
            if success:
                st.success(f"✅ Classwork OPENED for {course_code} - {classwork_week}")
                st.rerun()
            else:
                st.error("❌ Failed to open classwork")

    with col2:
        if st.button("🔒 CLOSE Classwork", use_container_width=True, type="secondary"):
            success = set_classwork_status(course_code, classwork_week, False)
            if success:
                st.warning(f"🚫 Classwork CLOSED for {course_code} - {classwork_week}")
                st.rerun()
            else:
                st.error("❌ Failed to close classwork")

    # Auto-close functionality for classwork
    if is_classwork_open and current_classwork_status.get("open_time"):
        try:
            open_time = datetime.fromisoformat(current_classwork_status["open_time"])
            elapsed = (datetime.now() - open_time).total_seconds()
            remaining = max(0, 1200 - elapsed)  # 20 minutes in seconds
            
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
    
    
# 📁 Delete attendance record option
    attendance_folder = os.path.join("data", "attendance")
    os.makedirs(attendance_folder, exist_ok=True)
    attendance_file = os.path.join(attendance_folder, f"{course_code}_{selected_week}.csv")

    if os.path.exists(attendance_file):
        st.info(f"📂 Found record: {attendance_file}")
        if st.button(f"🗑 Delete Attendance Record for {course_code} - {selected_week}", key=f"del_{selected_course}_{selected_week}"):
            os.remove(attendance_file)
            st.success(f"✅ Deleted attendance record for {course_code} - {selected_week}")
        else:
            st.info(f"No attendance record yet for {course_code} - {selected_week}")


        ATTENDANCE_FOLDER = "attendance_records"

# Ensure folder exists
        os.makedirs(ATTENDANCE_FOLDER, exist_ok=True)

# List existing attendance files
        attendance_files = [f for f in os.listdir(ATTENDANCE_FOLDER) if f.endswith(".csv")]

        st.subheader("🗑️ Delete Weekly Attendance Record")
        base_folder = "attendance_records"
        if os.path.exists(base_folder):
            all_files = []
            for root, _, files in os.walk(base_folder):
                for f in files:
                    if f.endswith(".csv"):
                        all_files.append(os.path.join(root, f))

            if all_files:
                selected = st.selectbox("Select attendance file to delete:", all_files)
                if st.button("Delete Selected File"):
                    os.remove(selected)
                    st.success(f"✅ Deleted: {selected}")
            else:
                st.info("No attendance files found.")

 # ------------------------
    # 📋 STATUS SUMMARY
    # ------------------------
            if not df_status.empty:
                st.dataframe(df_status)

            st.markdown(f"---\n*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

# 🚪 SHOW VIEW BASED ON ROLE
# ===============================================================
if st.session_state["role"] == "Admin":
    admin_view(course_code)
elif st.session_state["role"] == "Student":
    student_view(course_code)
else:
    st.warning("Please select your role from the sidebar to continue.")





































































































































































































