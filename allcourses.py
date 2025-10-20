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

import os
import streamlit as st
import pandas as pd
import json
from datetime import datetime

# =============================================
# PERSISTENT STORAGE SETUP
# =============================================

# Define persistent data directory (survives reboots)
PERSISTENT_DATA_DIR = "persistent_data"
os.makedirs(PERSISTENT_DATA_DIR, exist_ok=True)

def ensure_persistent_dirs():
    """Create all necessary persistent directories"""
    directories = [
        PERSISTENT_DATA_DIR,
        os.path.join(PERSISTENT_DATA_DIR, "pdfs"),
        os.path.join(PERSISTENT_DATA_DIR, "videos"),
        os.path.join(PERSISTENT_DATA_DIR, "data"),
        os.path.join(PERSISTENT_DATA_DIR, "attendance"),
        os.path.join(PERSISTENT_DATA_DIR, "classwork"),
        os.path.join(PERSISTENT_DATA_DIR, "seminar"),
        os.path.join(PERSISTENT_DATA_DIR, "lectures")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
    
    return True

# Initialize persistent directories
ensure_persistent_dirs()

# Update all file paths to use persistent storage
def get_persistent_path(file_type, course_code="", filename=""):
    """Get persistent file paths that survive reboots"""
    base_dir = PERSISTENT_DATA_DIR
    
    if file_type == "pdf":
        return os.path.join(base_dir, "pdfs", course_code, filename) if filename else os.path.join(base_dir, "pdfs", course_code)
    elif file_type == "video":
        return os.path.join(base_dir, "videos", course_code, filename) if filename else os.path.join(base_dir, "videos", course_code)
    elif file_type == "attendance":
        return os.path.join(base_dir, "attendance", filename) if filename else os.path.join(base_dir, "attendance")
    elif file_type == "classwork":
        return os.path.join(base_dir, "classwork", f"{course_code}_classwork.csv")
    elif file_type == "seminar":
        return os.path.join(base_dir, "seminar", f"{course_code}_seminar.csv")
    elif file_type == "lectures":
        return os.path.join(base_dir, "lectures", f"{course_code}_lectures.csv")
    elif file_type == "attendance_status":
        return os.path.join(base_dir, "data", "attendance_status.json")
    else:
        return os.path.join(base_dir, "data", filename)

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
def get_pdf_directory(course_code):
    """Get the PDF directory for a course"""
    pdf_dir = os.path.join("pdfs", course_code)
    os.makedirs(pdf_dir, exist_ok=True)
    return pdf_dir

def safe_pdf_path_check(pdf_path):
    """Safely check if a PDF path exists and is valid"""
    if not pdf_path or not isinstance(pdf_path, str):
        return False, "Invalid path type"
    
    pdf_path = pdf_path.strip()
    if not pdf_path:
        return False, "Empty path"
    
    try:
        exists = os.path.exists(pdf_path)
        if exists:
            # Check if it's actually a file and readable
            if os.path.isfile(pdf_path):
                return True, "Valid PDF file"
            else:
                return False, "Path exists but is not a file"
        else:
            return False, "File not found at path"
    except Exception as e:
        return False, f"Error checking path: {e}"

def fix_pdf_paths(lectures_df, course_code):
    """Fix PDF paths in the dataframe"""
    pdf_dir = get_pdf_directory(course_code)
    
    for idx, row in lectures_df.iterrows():
        pdf_path = row.get("PDF_File", "")
        if pdf_path and isinstance(pdf_path, str) and pdf_path.strip():
            # Check if path needs fixing
            pdf_path = pdf_path.strip()
            
            # If it's a relative path, try to make it absolute
            if not os.path.isabs(pdf_path):
                # Try to find the file in the PDF directory
                filename = os.path.basename(pdf_path)
                possible_path = os.path.join(pdf_dir, filename)
                if os.path.exists(possible_path):
                    lectures_df.at[idx, "PDF_File"] = os.path.abspath(possible_path)
                    st.info(f"Fixed path for {row['Week']}: {filename}")
    return lectures_df
    
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

def get_persistent_path(file_type, course_code="", filename=""):
    """Get persistent file paths that survive reboots"""
    base_dir = PERSISTENT_DATA_DIR
    
    if file_type == "scores":
        return os.path.join(base_dir, "scores", f"{course_code.lower()}_scores.csv")
    # ... your other file type cases ...

def student_view(course_code):
    """Student dashboard with persistent storage, scores, classwork, attendance, and uploads."""
    # Initialize persistent directories
    ensure_persistent_dirs()
    
    # Paths
    LECTURE_PATH = get_persistent_path("lectures", course_code)
    CLASSWORK_FILE = get_persistent_path("classwork", course_code)
    SCORES_FILE = get_persistent_path("scores", course_code)
    
    # Initialize student identity
    if "student_identity" not in st.session_state:
        st.session_state.student_identity = {"name": "", "matric": ""}
    student_name = st.session_state.student_identity["name"]
    student_matric = st.session_state.student_identity["matric"]
    
    st.title(f"🎓 Student Dashboard - {course_code}")

    # -----------------------
    # Student Identity
    # -----------------------
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
                st.experimental_rerun()
            else:
                st.error("❌ Please enter both name and matric number.")

    if student_name and student_matric:
        st.success(f"**Logged in as:** {student_name} ({student_matric})")
    else:
        st.warning("⚠️ Set your identity to view your scores and submit work.")


    # ===============================================================
# 📚 Student Lecture View
# ===============================================================
    st.header(f"📖 {course_code} Lecture Materials")

# Ensure persistent directories exist
    ensure_persistent_dirs()

# Path to the lecture CSV (must match admin path)
    LECTURE_FILE = os.path.join(PERSISTENT_DATA_DIR, "lectures", course_code, f"{course_code}_lectures.csv")

# Load lectures
    try:
        if os.path.exists(LECTURE_FILE):
            lectures_df = pd.read_csv(LECTURE_FILE)
        else:
            lectures_df = pd.DataFrame(columns=["Week", "Topic", "Brief", "Assignment", "Classwork", "PDF_File"])
    
    # Ensure all columns exist
        for col in ["Week", "Topic", "Brief", "Assignment", "Classwork", "PDF_File"]:
            if col not in lectures_df.columns:
                lectures_df[col] = ""

    except Exception as e:
        st.error(f"⚠️ Error loading lecture file: {e}")
        lectures_df = pd.DataFrame()

    if lectures_df.empty or lectures_df["Week"].isna().all():
        st.info("No lecture materials available yet. Check back later!")
    else:
        for _, row in lectures_df.iterrows():
            if pd.isna(row["Week"]) or row["Week"] == "":
                continue
        
            with st.expander(f"📖 {row['Week']} - {row.get('Topic','No Topic')}"):
            # Lecture brief
                if row.get("Brief","").strip():
                    st.markdown(f"**Description:** {row['Brief']}")
            
            # Assignment
                if row.get("Assignment","").strip():
                    st.markdown(f"**Assignment:** {row['Assignment']}")
            
            # Classwork questions
                classwork_text = str(row.get("Classwork","")).strip()
                if classwork_text:
                    st.markdown("**Classwork Questions:**")
                    questions = [q.strip() for q in classwork_text.split(";") if q.strip()]
                    for i, question in enumerate(questions):
                        st.write(f"Q{i+1}: {question}")
            
            # PDF download
                pdf_file = row.get("PDF_File","").strip()
                if pdf_file and os.path.exists(pdf_file):
                    try:
                        with open(pdf_file, "rb") as pdf_file_obj:
                            file_size = os.path.getsize(pdf_file) / (1024*1024)
                            st.download_button(
                                label=f"📥 Download PDF ({file_size:.1f}MB)",
                                data=pdf_file_obj,
                                file_name=os.path.basename(pdf_file),
                                mime="application/pdf"
                        )
                    except Exception as e:
                        st.error(f"⚠️ Cannot load PDF: {e}")
                else:
                    st.info("No PDF available for this lecture.")

    # -----------------------
    # Scores & Grades
    # -----------------------
    if student_name and student_matric:
        st.header("📊 My Scores & Grades")
        scores_file = os.path.join(PERSISTENT_DATA_DIR, "scores", f"{course_code.lower()}_scores.csv")
        if os.path.exists(scores_file):
            try:
                scores_df = pd.read_csv(scores_file)
                student_scores = scores_df[
                    (scores_df["StudentName"].astype(str).str.strip().str.lower() == student_name.lower()) &
                    (scores_df["MatricNo"].astype(str).str.strip().str.lower() == student_matric.lower())
                ]
                if not student_scores.empty:
                    # Overall metrics
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("Avg Assignment", f"{student_scores['Assignment'].mean():.1f}%")
                    col2.metric("Avg Test", f"{student_scores['Test'].mean():.1f}%")
                    col3.metric("Avg Practical", f"{student_scores['Practical'].mean():.1f}%")
                    col4.metric("Avg Exam", f"{student_scores['Exam'].mean():.1f}%")
                    st.metric("📈 Overall Average", f"{student_scores['Total'].mean():.1f}%")
                    
                    # Detailed table
                    display_columns = ["Week", "Assignment", "Test", "Practical", "Exam", "Total", "Grade"]
                    display_df = student_scores[display_columns].copy()
                    for col in ["Assignment", "Test", "Practical", "Exam", "Total"]:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                    st.dataframe(display_df, use_container_width=True)
                    
                    # Weekly breakdown
                    st.subheader("📖 Weekly Breakdown")
                    for _, row in student_scores.iterrows():
                        with st.expander(f"📅 {row['Week']} - Total: {row['Total']:.1f}% | Grade: {row['Grade']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"📝 Assignment: {row['Assignment']:.1f}%")
                                st.write(f"📋 Test: {row['Test']:.1f}%")
                                st.write(f"🔧 Practical: {row['Practical']:.1f}%")
                                st.write(f"🎯 Exam: {row['Exam']:.1f}%")
                                st.write(f"📊 Total: {row['Total']:.1f}%")
                            with col2:
                                grade = row['Grade']
                                if grade == "A": st.success(f"🎉 Excellent! Grade: {grade}")
                                elif grade == "B": st.info(f"👍 Good Job! Grade: {grade}")
                                elif grade == "C": st.warning(f"💪 Satisfactory Grade: {grade}")
                                elif grade in ["D","E"]: st.error(f"📚 Needs Improvement Grade: {grade}")
                                else: st.error(f"🚨 Failed Grade: {grade}")
                    
                    # Performance trends
                    trend_df = student_scores.copy().sort_values("Week")
                    trend_df["WeekNum"] = trend_df["Week"].str.extract('(\d+)').astype(int)
                    trend_df = trend_df.sort_values("WeekNum")
                    chart_data = trend_df[["Week", "Assignment", "Test", "Practical", "Exam", "Total"]].set_index("Week")
                    st.line_chart(chart_data, use_container_width=True)
                    
                    # Download CSV
                    st.download_button(
                        "📥 Download My Scores (CSV)",
                        student_scores.to_csv(index=False),
                        file_name=f"{course_code}_{student_name}_{student_matric}_scores.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("📊 No scores recorded yet for your account.")
            except Exception as e:
                st.error(f"❌ Error loading scores: {e}")
        else:
            st.info("📊 No scores file found yet.")

    # -----------------------
    # Attendance
    # -----------------------
    st.header("🕒 Mark Attendance")
    with st.form(f"{course_code}_attendance_form"):
        name = st.text_input("Full Name", value=student_name, key=f"{course_code}_student_name")
        matric = st.text_input("Matric Number", value=student_matric, key=f"{course_code}_student_matric")
        week = st.selectbox("Select Week", [f"Week {i}" for i in range(1,16)], key=f"{course_code}_att_week")
        submit_attendance = st.form_submit_button("✅ Mark Attendance", use_container_width=True)
    if submit_attendance:
        if not name.strip() or not matric.strip():
            st.warning("Enter full name and matric number.")
        else:
            st.session_state.student_identity = {"name": name.strip(), "matric": matric.strip()}
            status_data = get_attendance_status(course_code, week)
            if not status_data.get("is_open", False):
                st.error("🚫 Attendance is closed for this week.")
            elif has_marked_attendance(course_code, week, name, matric):
                st.info("✅ Attendance already marked.")
            else:
                ok = mark_attendance_entry(course_code, name, matric, week)
                if ok:
                    st.success(f"🎉 Attendance recorded for {week}")
                    st.balloons()
    
    # -----------------------
    # Lecture Materials
    # -----------------------
    st.header("📚 Lecture Materials")
    lectures_df = pd.DataFrame()
    if os.path.exists(LECTURE_PATH):
        if os.path.isdir(LECTURE_PATH):
            csv_files = [f for f in os.listdir(LECTURE_PATH) if f.lower().endswith('.csv')]
            if csv_files:
                lectures_df = pd.read_csv(os.path.join(LECTURE_PATH, csv_files[0]))
        elif os.path.isfile(LECTURE_PATH):
            lectures_df = pd.read_csv(LECTURE_PATH)
    if not lectures_df.empty:
        for _, row in lectures_df.iterrows():
            with st.expander(f"📖 {row.get('Week','')} : {row.get('Topic','')}"):
                brief = row.get("Brief","")
                if pd.notna(brief) and brief.strip(): st.markdown(f"**Description:** {brief}")
                assignment = row.get("Assignment","")
                if pd.notna(assignment) and assignment.strip(): st.markdown(f"**Assignment:** {assignment}")
                classwork = row.get("Classwork","")
                if pd.notna(classwork) and classwork.strip(): st.markdown(f"**Classwork:** {classwork}")
                pdf_file = row.get("PDF_File","")
                if pd.notna(pdf_file) and pdf_file.strip() and os.path.exists(pdf_file):
                    with open(pdf_file,"rb") as f:
                        st.download_button(f"📥 Download PDF {os.path.basename(pdf_file)}", f.read(), os.path.basename(pdf_file), mime="application/pdf")
    else:
        st.info("No lecture materials uploaded yet.")
    
    # -----------------------
    # Video Lectures
    # -----------------------
    st.header("🎥 Video Lectures")
    video_dir = get_persistent_path("video", course_code)
    video_files = []
    if os.path.exists(video_dir):
        if os.path.isdir(video_dir):
            video_files = [f for f in sorted(os.listdir(video_dir)) if f.lower().endswith(('.mp4','.mov','.avi','.mkv'))]
    if video_files:
        for i, video in enumerate(video_files[:10]):  # limit first 10
            video_path = os.path.join(video_dir, video)
            with st.expander(f"🎬 {video}"):
                st.video(video_path)
                with open(video_path,"rb") as f:
                    st.download_button("📥 Download Video", f.read(), video, mime="video/mp4")
    else:
        st.info("No video lectures uploaded yet.")
    
    # -----------------------
    # Assignment Upload
    # -----------------------
    for upload_type, types, header in [("assignment", ["pdf","doc","docx","txt","zip"], "📝 Assignment Submission"),
                                      ("drawing", ["jpg","jpeg","png","gif","pdf"], "🎨 Drawing Submission"),
                                      ("seminar", ["pdf","ppt","pptx","doc","docx"], "📊 Seminar Submission")]:
        st.subheader(header)
        with st.form(f"{upload_type}_upload_form"):
            week = st.selectbox(f"Select Week for {header}", [f"Week {i}" for i in range(1,16)], key=f"{upload_type}_week")
            file = st.file_uploader(f"Upload {header} File", type=types, key=f"{upload_type}_file")
            submit = st.form_submit_button(f"📤 Submit {header}", use_container_width=True)
            if submit:
                if not student_name or not student_matric:
                    st.error("❌ Set your identity first.")
                elif not file:
                    st.error("❌ Please select a file.")
                else:
                    dir_path = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, upload_type)
                    os.makedirs(dir_path, exist_ok=True)
                    safe_name = f"{student_name}_{student_matric}_{week}_{file.name}".replace(" ","_")
                    file_path = os.path.join(dir_path, safe_name)
                    with open(file_path,"wb") as f:
                        f.write(file.getbuffer())
                    st.success(f"✅ {header} submitted: {file.name}")
    
    # -----------------------
    # Student Progress
    # -----------------------
    if student_name and student_matric:
        st.header("📈 My Progress")
        # Attendance
        attendance_count = sum(has_marked_attendance(course_code, f"Week {i}", student_name, student_matric) for i in range(1,16))
        # Classwork submissions
        classwork_count = 0
        if os.path.exists(CLASSWORK_FILE):
            try:
                classwork_df = pd.read_csv(CLASSWORK_FILE)
                student_submissions = classwork_df[
                    (classwork_df['Name'].str.lower() == student_name.lower()) & 
                    (classwork_df['Matric'].str.lower() == student_matric.lower())
                ]
                classwork_count = len(student_submissions)
            except:
                pass
        # File uploads
        file_count = 0
        for sub_dir in ["assignment","drawing","seminar"]:
            full_dir = os.path.join(PERSISTENT_DATA_DIR,"student_uploads",course_code,sub_dir)
            if os.path.exists(full_dir):
                files = os.listdir(full_dir)
                student_files = [f for f in files if student_name.lower() in f.lower() and student_matric.lower() in f.lower()]
                file_count += len(student_files)
        col1,col2,col3 = st.columns(3)
        col1.metric("Weeks Attended", f"{attendance_count}/15")
        col2.metric("Classwork Submitted", classwork_count)
        col3.metric("Files Submitted", file_count)
        
        st.subheader("Recent Activity")
        activities = []
        for i in range(1,16):
            if has_marked_attendance(course_code, f"Week {i}", student_name, student_matric):
                activities.append(f"✅ Attended Week {i}")
        if classwork_count>0:
            activities.extend([f"📝 Submitted classwork for {row['Week']}" for _, row in student_submissions.iterrows()])
        if activities:
            st.write("**Latest activities:**")
            for activity in activities[-5:]:
                st.write(f"- {activity}")
        else:
            st.info("No activity yet. Start by marking attendance or submitting assignments!")

    # -----------------------
    # Help
    # -----------------------
    with st.expander("❓ Need Help?"):
        st.markdown("""
        **Common Issues & Solutions:**
        - Can't see my scores? Set your identity correctly
        - Scores not updated? Lecturer may not have graded yet
        - Can't submit classwork? Lecturer may not have opened it
        - PDF/Video issues? Try different browser
        """)

    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")




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

import os

def get_persistent_path(folder_type, course_code, filename=None):
    """
    Returns a fully qualified path for storing course data or files.
    If filename is provided → returns full file path.
    If not → returns the folder path only.
    """
    base_dir = "persistent_storage"
    os.makedirs(base_dir, exist_ok=True)

    if not course_code:
        return None

    folder_path = os.path.join(base_dir, folder_type, course_code)
    os.makedirs(folder_path, exist_ok=True)

    if filename:
        # Return full path for a file
        return os.path.join(folder_path, filename)
    else:
        # Return folder path (for directories like PDFs)
        return folder_path

    
def admin_view(course_code):
    """Admin dashboard to manage lectures, scores, classwork, attendance, and student uploads."""
    ensure_persistent_dirs()
    
    # Paths
    LECTURE_PATH = get_persistent_path("lectures", course_code)
    SCORES_PATH = get_persistent_path("scores", course_code)
    CLASSWORK_FILE = get_persistent_path("classwork", course_code)
    VIDEO_PATH = get_persistent_path("video", course_code)
    
    st.title(f"👩‍🏫 Admin Dashboard - {course_code}")
    
    # -----------------------
    # ===============================================================
# 📚 Lecture Management (Admin)
# ===============================================================
    st.header(f"📝 Lecture Management - {course_code}")

    ensure_persistent_dirs()

# Persistent paths
    lecture_dir = os.path.join(PERSISTENT_DATA_DIR, "lectures", course_code)
    os.makedirs(lecture_dir, exist_ok=True)
    LECTURE_FILE = os.path.join(lecture_dir, f"{course_code}_lectures.csv")

# Load existing lectures
    if os.path.exists(LECTURE_FILE):
        lectures_df = pd.read_csv(LECTURE_FILE)
    else:
        lectures_df = pd.DataFrame(columns=["Week", "Topic", "Brief", "Assignment", "Classwork", "PDF_File"])

# Ensure all 15 weeks exist
    for i in range(1, 16):
        week_label = f"Week {i}"
        if week_label not in lectures_df['Week'].values:
            new_row = pd.DataFrame([{
                "Week": week_label,
                "Topic": "",
                "Brief": "",
                "Assignment": "",
                "Classwork": "",
                "PDF_File": ""
            }])
            lectures_df = pd.concat([lectures_df, new_row], ignore_index=True)

    lectures_df = lectures_df.sort_values("Week").reset_index(drop=True)

    edited_rows = []

# Editable form for each week
    for idx, row in lectures_df.iterrows():
        with st.expander(f"{row['Week']} - {row.get('Topic','No Topic')}"):
            topic = st.text_input("Topic", value=row.get("Topic",""), key=f"topic_{idx}")
            brief = st.text_area("Lecture Brief", value=row.get("Brief",""), height=150, key=f"brief_{idx}")
            assignment = st.text_area("Assignment", value=row.get("Assignment",""), height=100, key=f"assignment_{idx}")
            classwork = st.text_area(
                "Classwork Questions (separate with semicolon ;)",
                value=row.get("Classwork",""), height=100, key=f"classwork_{idx}"
        )

        # Optional PDF upload
            pdf_file = st.file_uploader("Upload PDF (Optional)", type=["pdf"], key=f"pdf_{idx}")
            pdf_path = row.get("PDF_File","")
            if pdf_file:
                pdf_dir = os.path.join(PERSISTENT_DATA_DIR, "lectures_pdf", course_code)
                os.makedirs(pdf_dir, exist_ok=True)
                safe_name = f"{row['Week']}_{pdf_file.name}".replace(" ","_")
                pdf_path = os.path.join(pdf_dir, safe_name)
                with open(pdf_path, "wb") as f:
                    f.write(pdf_file.getbuffer())
                st.success(f"✅ PDF saved for {row['Week']}")

            edited_rows.append({
                "Week": row["Week"],
                "Topic": topic,
                "Brief": brief,
                "Assignment": assignment,
                "Classwork": classwork,
                "PDF_File": pdf_path
        })

# Save all lectures
    if st.button("💾 Save All Lectures"):
        updated_df = pd.DataFrame(edited_rows)
        updated_df.to_csv(LECTURE_FILE, index=False)
        st.success("✅ All lecture details saved successfully!")

# ===============================================================
# 📤 Upload Lecture CSV
# ===============================================================
    st.subheader("Upload Lecture CSV / PDF / Materials")
    with st.form("upload_lecture_form"):
        lecture_file = st.file_uploader("Upload Lecture CSV", type=["csv"], key="lecture_csv")
        submit_lecture = st.form_submit_button("📤 Upload Lecture")
        if submit_lecture:
            if lecture_file:
                lecture_path = os.path.join(lecture_dir, lecture_file.name)
                with open(lecture_path, "wb") as f:
                    f.write(lecture_file.getbuffer())
                st.success(f"✅ Lecture CSV uploaded: {lecture_file.name}")
            else:
                st.error("❌ Select a CSV file to upload.")

# ===============================================================
# 📖 View Uploaded Lectures
# ===============================================================
    uploaded_lectures = pd.DataFrame()
    csv_files = [f for f in os.listdir(lecture_dir) if f.lower().endswith(".csv")]
    if csv_files:
        uploaded_lectures = pd.read_csv(os.path.join(lecture_dir, csv_files[0]))

    if not uploaded_lectures.empty:
        st.subheader("Uploaded Lectures")
        st.dataframe(uploaded_lectures, use_container_width=True)

    # -----------------------
    # Scores Management
    # -----------------------
    st.header("📊 Manage Scores")
    st.subheader("Upload/Update Student Scores CSV")
    with st.form("upload_scores_form"):
        scores_file = st.file_uploader("Upload Scores CSV", type=["csv"], key="scores_csv")
        submit_scores = st.form_submit_button("📤 Upload Scores")
        if submit_scores:
            if scores_file:
                scores_dir = os.path.join(PERSISTENT_DATA_DIR, "scores")
                os.makedirs(scores_dir, exist_ok=True)
                scores_path = os.path.join(scores_dir, f"{course_code.lower()}_scores.csv")
                with open(scores_path, "wb") as f:
                    f.write(scores_file.getbuffer())
                st.success(f"✅ Scores uploaded: {scores_file.name}")
            else:
                st.error("❌ Select a CSV file to upload.")

    # View scores
    scores_file_path = os.path.join(PERSISTENT_DATA_DIR, "scores", f"{course_code.lower()}_scores.csv")
    if os.path.exists(scores_file_path):
        st.subheader("Uploaded Scores")
        try:
            scores_df = pd.read_csv(scores_file_path)
            st.dataframe(scores_df, use_container_width=True)
        except Exception as e:
            st.error(f"❌ Error loading scores CSV: {e}")
    
    # -----------------------
    # Classwork Management
    # -----------------------
    st.header("🧩 Manage Classwork")
    st.subheader("Add/Edit Classwork Questions")
    with st.form("classwork_form"):
        week = st.selectbox("Week", [f"Week {i}" for i in range(1,16)])
        questions = st.text_area("Classwork Questions (separate by semicolon ;)", height=200)
        open_status = st.checkbox("Open classwork for students?", value=True)
        submit_cw = st.form_submit_button("📤 Save Classwork")
        if submit_cw:
            save_classwork_questions(course_code, week, questions, open_status)
            st.success(f"✅ Classwork saved for {week} (Open: {open_status})")
    
    # View classwork
    st.subheader("Current Classwork")
    try:
        cw_df = pd.read_csv(CLASSWORK_FILE) if os.path.exists(CLASSWORK_FILE) else pd.DataFrame()
        if not cw_df.empty:
            st.dataframe(cw_df, use_container_width=True)
        else:
            st.info("No classwork uploaded yet.")
    except:
        st.info("No classwork uploaded yet.")
    
    # -----------------------
    # Video Upload
    # -----------------------
    st.header("🎥 Upload Video Lectures")
    with st.form("video_form"):
        video_file = st.file_uploader("Upload Video", type=["mp4","mov","avi","mkv"], key="video_file")
        submit_video = st.form_submit_button("📤 Upload Video")
        if submit_video:
            if video_file:
                video_dir = os.path.join(PERSISTENT_DATA_DIR, "video", course_code)
                os.makedirs(video_dir, exist_ok=True)
                video_path = os.path.join(video_dir, video_file.name)
                with open(video_path, "wb") as f:
                    f.write(video_file.getbuffer())
                st.success(f"✅ Video uploaded: {video_file.name}")
            else:
                st.error("❌ Select a video file to upload.")

    # View uploaded videos
    st.subheader("Uploaded Video Lectures")
    if os.path.exists(VIDEO_PATH):
        videos = [f for f in os.listdir(VIDEO_PATH) if f.lower().endswith(('.mp4','.mov','.avi','.mkv'))]
        if videos:
            for video in videos[:10]:  # show first 10
                st.write(video)
        else:
            st.info("No videos uploaded yet.")
    
    # -----------------------
    # Student Submissions
    # -----------------------
    st.header("📤 View Student Submissions")
    submission_types = ["assignment","drawing","seminar"]
    for sub_type in submission_types:
        st.subheader(f"📂 {sub_type.capitalize()} Submissions")
        sub_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, sub_type)
        if os.path.exists(sub_dir):
            files = os.listdir(sub_dir)
            if files:
                for file in files:
                    file_path = os.path.join(sub_dir, file)
                    st.write(file)
                    with open(file_path,"rb") as f:
                        st.download_button("📥 Download", f.read(), file, key=f"{sub_type}_{file}")
            else:
                st.info(f"No {sub_type} submissions yet.")
        else:
            st.info(f"No {sub_type} submissions yet.")
    
    # -----------------------
    # Attendance Management
    # -----------------------
    st.header("🕒 Attendance")
    st.subheader("View Attendance Status")
    for i in range(1,16):
        week = f"Week {i}"
        status = get_attendance_status(course_code, week)
        st.write(f"{week}: {'Open' if status.get('is_open', False) else 'Closed'}")


    # -----------------------
# Manual Score Entry
# -----------------------
    st.header("✏️ Manual Score Entry / Update")
    st.subheader("Enter scores for students manually")

# Load existing scores
    scores_file_path = os.path.join(PERSISTENT_DATA_DIR, "scores", f"{course_code.lower()}_scores.csv")
    scores_df = pd.DataFrame()
    if os.path.exists(scores_file_path):
        try:
            scores_df = pd.read_csv(scores_file_path)
        except:
            st.error("❌ Could not load existing scores.")

# Form to add/update scores
    with st.form("manual_scores_form"):
        student_name = st.text_input("Student Name")
        student_matric = st.text_input("Matric Number")
        week = st.selectbox("Week", [f"Week {i}" for i in range(1,16)])
    
        assignment_score = st.number_input("Assignment (%)", min_value=0, max_value=100, step=1)
        test_score = st.number_input("Test (%)", min_value=0, max_value=100, step=1)
        practical_score = st.number_input("Practical (%)", min_value=0, max_value=100, step=1)
        exam_score = st.number_input("Exam (%)", min_value=0, max_value=100, step=1)
    
        submit_manual_score = st.form_submit_button("💾 Save Score")
    
        if submit_manual_score:
            if not student_name.strip() or not student_matric.strip():
                st.error("❌ Enter both student name and matric number.")
            else:
            # Calculate total and grade
                total = (assignment_score + test_score + practical_score + exam_score) / 4
                if total >= 70:
                    grade = "A"
                elif total >= 60:
                    grade = "B"
                elif total >= 50:
                    grade = "C"
                elif total >= 45:
                    grade = "D"
                elif total >= 40:
                    grade = "E"
                else:
                    grade = "F"
            
            # If student + week already exists, update row
                if not scores_df.empty:
                    mask = (
                        (scores_df["StudentName"].str.strip().str.lower() == student_name.strip().lower()) &
                        (scores_df["MatricNo"].str.strip().str.lower() == student_matric.strip().lower()) &
                        (scores_df["Week"].str.strip().str.lower() == week.strip().lower())
                )
                    if mask.any():
                        scores_df.loc[mask, ["Assignment","Test","Practical","Exam","Total","Grade"]] = [
                            assignment_score, test_score, practical_score, exam_score, total, grade
                    ]
                        st.success(f"✅ Scores updated for {student_name} ({week})")
                    else:
                    # Add new row
                        new_row = {
                            "StudentName": student_name.strip(),
                            "MatricNo": student_matric.strip(),
                            "Week": week,
                            "Assignment": assignment_score,
                            "Test": test_score,
                            "Practical": practical_score,
                            "Exam": exam_score,
                            "Total": total,
                            "Grade": grade
                    }
                        scores_df = pd.concat([scores_df, pd.DataFrame([new_row])], ignore_index=True)
                        st.success(f"✅ Scores added for {student_name} ({week})")
                else:
                # First entry
                    scores_df = pd.DataFrame([{
                        "StudentName": student_name.strip(),
                        "MatricNo": student_matric.strip(),
                        "Week": week,
                        "Assignment": assignment_score,
                        "Test": test_score,
                        "Practical": practical_score,
                        "Exam": exam_score,
                        "Total": total,
                        "Grade": grade
                    }])
                    st.success(f"✅ Scores added for {student_name} ({week})")
            
            # Save back to CSV
                os.makedirs(os.path.dirname(scores_file_path), exist_ok=True)
                scores_df.to_csv(scores_file_path, index=False)

    # -----------------------
    # Help Section
    # -----------------------
    with st.expander("❓ Admin Help"):
        st.markdown("""
        - Upload lectures, videos, classwork, and scores to make them visible to students.
        - Open classwork to allow submissions.
        - Check student uploads and download for grading.
        - Attendance open/close is controlled per week.
        """)

    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")


    
# 🚪 SHOW VIEW BASED ON ROLE
# ===============================================================
if st.session_state["role"] == "Admin":
    admin_view(course_code)
elif st.session_state["role"] == "Student":
    student_view(course_code)
else:
    st.warning("Please select your role from the sidebar to continue.")




















































































































































































































