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
    """Student dashboard view with PERSISTENT storage and scores viewing"""
    
    # Initialize persistent directories
    ensure_persistent_dirs()
    
    # Use persistent file paths
    LECTURE_FILE = get_persistent_path("lectures", course_code)
    CLASSWORK_FILE = get_persistent_path("classwork", course_code)
    SCORES_FILE = get_persistent_path("scores", course_code)
    
    # Initialize student identity in session state
    if "student_identity" not in st.session_state:
        st.session_state.student_identity = {"name": "", "matric": ""}
    
    # Get student identity from session state
    student_name = st.session_state.student_identity["name"]
    student_matric = st.session_state.student_identity["matric"]
    
    st.title(f"🎓 Student Dashboard - {course_code}")

    # Student Identity Section
    st.subheader("👤 Student Identity")
    with st.form("student_identity_form"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Full Name", 
                                   value=student_name,
                                   placeholder="Enter your full name")
        with col2:
            new_matric = st.text_input("Matric Number", 
                                     value=student_matric,
                                     placeholder="Enter your matric number")
        save_identity = st.form_submit_button("💾 Save Identity", use_container_width=True)
        
        if save_identity:
            if new_name.strip() and new_matric.strip():
                st.session_state.student_identity = {
                    "name": new_name.strip(), 
                    "matric": new_matric.strip()
                }
                st.success("✅ Identity saved successfully!")
                st.rerun()
            else:
                st.error("❌ Please enter both name and matric number.")
    
    # Display current identity
    if student_name and student_matric:
        st.success(f"**Logged in as:** {student_name} ({student_matric})")
    else:
        st.warning("⚠️ Please set your identity above to view your scores and submit work.")

    # ===============================================================
    # 📊 SCORES VIEWING SECTION
    # ===============================================================
    if student_name and student_matric:
        st.header("📊 My Scores & Grades")
        
        # Load scores from persistent storage
        scores_file = os.path.join(PERSISTENT_DATA_DIR, "scores", f"{course_code.lower()}_scores.csv")
        
        if os.path.exists(scores_file):
            try:
                scores_df = pd.read_csv(scores_file)
                
                # Filter for current student
                student_scores = scores_df[
                    (scores_df["StudentName"].astype(str).str.strip().str.lower() == student_name.lower()) &
                    (scores_df["MatricNo"].astype(str).str.strip().str.lower() == student_matric.lower())
                ]
                
                if not student_scores.empty:
                    # Display overall performance
                    st.subheader("🎯 Overall Performance")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        avg_assignment = student_scores["Assignment"].mean()
                        st.metric("Avg Assignment", f"{avg_assignment:.1f}%")
                    
                    with col2:
                        avg_test = student_scores["Test"].mean()
                        st.metric("Avg Test", f"{avg_test:.1f}%")
                    
                    with col3:
                        avg_practical = student_scores["Practical"].mean()
                        st.metric("Avg Practical", f"{avg_practical:.1f}%")
                    
                    with col4:
                        avg_exam = student_scores["Exam"].mean()
                        st.metric("Avg Exam", f"{avg_exam:.1f}%")
                    
                    # Overall average
                    overall_avg = student_scores["Total"].mean()
                    st.metric("📈 Overall Average", f"{overall_avg:.1f}%")
                    
                    # Grade distribution
                    st.subheader("📋 Detailed Scores by Week")
                    
                    # Create a clean display dataframe
                    display_columns = ["Week", "Assignment", "Test", "Practical", "Exam", "Total", "Grade"]
                    display_df = student_scores[display_columns].copy()
                    
                    # Format percentages
                    for col in ["Assignment", "Test", "Practical", "Exam", "Total"]:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                    
                    # Display the table
                    st.dataframe(display_df, use_container_width=True)
                    
                    # Weekly breakdown with expanders
                    st.subheader("📖 Weekly Breakdown")
                    
                    for _, row in student_scores.iterrows():
                        with st.expander(f"📅 {row['Week']} - Total: {row['Total']:.1f}% | Grade: {row['Grade']}", expanded=False):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**Scores:**")
                                st.write(f"📝 **Assignment:** {row['Assignment']:.1f}%")
                                st.write(f"📋 **Test:** {row['Test']:.1f}%")
                                st.write(f"🔧 **Practical:** {row['Practical']:.1f}%")
                                st.write(f"🎯 **Exam:** {row['Exam']:.1f}%")
                                st.write(f"📊 **Total:** {row['Total']:.1f}%")
                            
                            with col2:
                                st.markdown("**Grade Analysis:**")
                                grade = row['Grade']
                                if grade == "A":
                                    st.success(f"🎉 **Excellent!** Grade: {grade}")
                                elif grade == "B":
                                    st.info(f"👍 **Good Job!** Grade: {grade}")
                                elif grade == "C":
                                    st.warning(f"💪 **Satisfactory** Grade: {grade}")
                                elif grade == "D" or grade == "E":
                                    st.error(f"📚 **Needs Improvement** Grade: {grade}")
                                else:
                                    st.error(f"🚨 **Failed** Grade: {grade}")
                                
                                # Progress bars for visual representation
                                st.markdown("**Score Distribution:**")
                                st.progress(row['Assignment']/100, text=f"Assignment: {row['Assignment']:.1f}%")
                                st.progress(row['Test']/100, text=f"Test: {row['Test']:.1f}%")
                                st.progress(row['Practical']/100, text=f"Practical: {row['Practical']:.1f}%")
                                st.progress(row['Exam']/100, text=f"Exam: {row['Exam']:.1f}%")
                    
                    # Performance trends
                    st.subheader("📈 Performance Trends")
                    
                    # Create trend data
                    trend_df = student_scores.copy()
                    trend_df = trend_df.sort_values("Week")
                    
                    # Convert Week to numeric for plotting
                    trend_df["WeekNum"] = trend_df["Week"].str.extract('(\d+)').astype(int)
                    trend_df = trend_df.sort_values("WeekNum")
                    
                    # Create trend chart
                    chart_data = trend_df[["Week", "Assignment", "Test", "Practical", "Exam", "Total"]].set_index("Week")
                    
                    st.line_chart(chart_data, use_container_width=True)
                    
                    # Download scores option
                    csv_data = student_scores.to_csv(index=False)
                    st.download_button(
                        label="📥 Download My Scores (CSV)",
                        data=csv_data,
                        file_name=f"{course_code}_{student_name}_{student_matric}_scores.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                else:
                    st.info("📊 No scores recorded yet for your account. Scores will appear here once your lecturer grades your work.")
                    
            except Exception as e:
                st.error(f"❌ Error loading scores: {e}")
                st.info("If this error persists, please contact your lecturer.")
        else:
            st.info("📊 No scores file found yet. Your scores will appear here once your lecturer starts grading.")

    # ===============================================================
    # 🕒 ATTENDANCE SECTION
    # ===============================================================
    st.header("🕒 Mark Attendance")
    
    with st.form(f"{course_code}_attendance_form"):
        # Pre-fill with session state values
        name = st.text_input("Full Name", 
                           value=student_name,
                           key=f"{course_code}_student_name")
        matric = st.text_input("Matric Number", 
                             value=student_matric,
                             key=f"{course_code}_student_matric")
        week = st.selectbox(
            "Select Week",
            [f"Week {i}" for i in range(1, 16)],
            key=f"{course_code}_att_week"
        )
        submit_attendance = st.form_submit_button("✅ Mark Attendance", use_container_width=True)

    # Attendance validation
    if submit_attendance:
        if not name.strip() or not matric.strip():
            st.warning("Please enter your full name and matric number.")
            st.stop()

        # Save identity to session state
        st.session_state.student_identity = {"name": name.strip(), "matric": matric.strip()}
        student_name = name.strip()
        student_matric = matric.strip()
        
        # Check if attendance is open
        status_data = get_attendance_status(course_code, week)
        is_attendance_open = status_data.get("is_open", False)
        
        if not is_attendance_open:
            st.error("🚫 Attendance for this course is currently closed. Please wait for your lecturer to open it.")
            st.stop()

        # Prevent duplicate marking
        if has_marked_attendance(course_code, week, student_name, student_matric):
            st.info("✅ Attendance already marked for this week.")
            st.stop()

        # Mark attendance
        ok = mark_attendance_entry(course_code, student_name, student_matric, week)
        if ok:
            st.session_state["attended_week"] = str(week)
            st.success(f"🎉 Attendance recorded successfully for {course_code} - {week}.")
            st.balloons()
        else:
            st.error("⚠️ Failed to record attendance. Try again later.")

    # ===============================================================
    # 📖 LECTURE MATERIALS WITH PERSISTENT STORAGE
    # ===============================================================
    st.header(f"📚 {course_code} Lecture Materials")
    
    # Load lectures from persistent storage
    try:
        if os.path.exists(LECTURE_FILE):
            lectures_df = pd.read_csv(LECTURE_FILE)
        else:
            lectures_df = pd.DataFrame(columns=["Week", "Topic", "Brief", "Assignment", "Classwork", "PDF_File"])
        
        # Ensure columns exist
        for col in ["Week", "Topic", "Brief", "Assignment", "Classwork", "PDF_File"]:
            if col not in lectures_df.columns:
                lectures_df[col] = ""
        
        st.session_state["lectures_df"] = lectures_df
        
    except Exception as e:
        st.error(f"⚠️ Error loading lecture file: {e}")
        return

    if lectures_df.empty or lectures_df["Week"].isna().all():
        st.info("No lecture materials available yet. Check back later!")
        return

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
                
                # 🧩 Classwork Section
                classwork_text = str(row.get("Classwork", "") or "").strip()
                if classwork_text:
                    st.markdown("### 🧩 Classwork Questions")
        
                    # Split questions by semicolon
                    questions = [q.strip() for q in classwork_text.split(";") if q.strip()]
        
                    if questions:
                        # Check if classwork is open
                        classwork_status = is_classwork_open(course_code, week)
            
                        with st.form(f"cw_form_{week.replace(' ', '_')}"):
                            st.write("**Answer the following questions:**")
                
                            # Create answer inputs
                            answers = []
                            for i, question in enumerate(questions):
                                st.write(f"**Q{i+1}:** {question}")
                                answer = st.text_area(
                                    f"Your answer for Q{i+1}",
                                    placeholder=f"Type your answer for Q{i+1} here...",
                                    key=f"q{i}_{week.replace(' ', '_')}",
                                    height=100,
                                    disabled=not classwork_status
                                )
                                answers.append(answer)
                                if i < len(questions) - 1:
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
                                # Use session state identity
                                if not student_name or not student_matric:
                                    st.error("❌ Please set your identity first using the form above.")
                                elif any(not answer.strip() for answer in answers):
                                    st.error("❌ Please answer all questions before submitting.")
                                else:
                                    # Save classwork using session state identity
                                    success = save_classwork(student_name, student_matric, week, answers)
                                    if success:
                                        st.balloons()
                                        st.rerun()
                    else:
                        st.info("No classwork questions available for this week.")
                else:
                    st.info("No classwork assigned for this week yet.")

                # Assignment section
                if row["Assignment"] and str(row["Assignment"]).strip():
                    st.markdown(f"**Assignment:** {row['Assignment']}")
            
            with col2:
                # PERSISTENT PDF access
                pdf_file = row.get("PDF_File", "")
                # Convert to string if needed
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
    # 🎥 VIDEO LECTURES WITH PERSISTENT STORAGE
    # ===============================================================
    st.header("🎥 Video Lectures")
    
    # Use persistent video directory
    video_dir = get_persistent_path("video", course_code)
    video_files = []
    
    try:
        if os.path.exists(video_dir):
            video_files = sorted([f for f in os.listdir(video_dir) 
                                if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])
    except Exception as e:
        st.error(f"Error accessing video directory: {e}")
    
    if video_files:
        st.success(f"Found {len(video_files)} video lecture(s) available!")
        
        # Limit display for performance
        MAX_VIDEOS_TO_SHOW = 10
        if len(video_files) > MAX_VIDEOS_TO_SHOW:
            st.info(f"Showing first {MAX_VIDEOS_TO_SHOW} videos. Contact your lecturer for more.")
            video_files = video_files[:MAX_VIDEOS_TO_SHOW]
        
        for i, video in enumerate(video_files):
            video_path = get_persistent_path("video", course_code, video)
            
            with st.expander(f"🎬 {video}", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    try:
                        # Display video with start time to avoid loading entire video
                        st.video(video_path, start_time=0)
                        
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

    # ===============================================================
    # 📤 STUDENT SUBMISSIONS SECTION
    # ===============================================================
    st.header("📤 Submit Assignments")
    
    # Assignment submission
    st.subheader("📝 Assignment Submission")
    with st.form("assignment_upload_form"):
        assignment_week = st.selectbox(
            "Select Week for Assignment",
            [f"Week {i}" for i in range(1, 16)],
            key="assignment_week"
        )
        assignment_file = st.file_uploader(
            "Upload Assignment File", 
            type=["pdf", "doc", "docx", "txt", "zip"],
            key="assignment_upload"
        )
        submit_assignment = st.form_submit_button("📤 Submit Assignment", use_container_width=True)
        
        if submit_assignment:
            if not student_name or not student_matric:
                st.error("❌ Please set your identity first.")
            elif not assignment_file:
                st.error("❌ Please select a file to upload.")
            else:
                # Save assignment to persistent storage
                assignment_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, "assignment")
                os.makedirs(assignment_dir, exist_ok=True)
                
                # Generate safe filename
                safe_name = f"{student_name}_{student_matric}_{assignment_week}_{assignment_file.name}"
                safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                
                assignment_path = os.path.join(assignment_dir, safe_name)
                
                try:
                    with open(assignment_path, "wb") as f:
                        f.write(assignment_file.getbuffer())
                    st.success(f"✅ Assignment submitted successfully: {assignment_file.name}")
                except Exception as e:
                    st.error(f"❌ Error submitting assignment: {e}")

    # Drawing submission
    st.subheader("🎨 Drawing Submission")
    with st.form("drawing_upload_form"):
        drawing_week = st.selectbox(
            "Select Week for Drawing",
            [f"Week {i}" for i in range(1, 16)],
            key="drawing_week"
        )
        drawing_file = st.file_uploader(
            "Upload Drawing File", 
            type=["jpg", "jpeg", "png", "gif", "pdf"],
            key="drawing_upload"
        )
        submit_drawing = st.form_submit_button("📤 Submit Drawing", use_container_width=True)
        
        if submit_drawing:
            if not student_name or not student_matric:
                st.error("❌ Please set your identity first.")
            elif not drawing_file:
                st.error("❌ Please select a file to upload.")
            else:
                # Save drawing to persistent storage
                drawing_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, "drawing")
                os.makedirs(drawing_dir, exist_ok=True)
                
                # Generate safe filename
                safe_name = f"{student_name}_{student_matric}_{drawing_week}_{drawing_file.name}"
                safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                
                drawing_path = os.path.join(drawing_dir, safe_name)
                
                try:
                    with open(drawing_path, "wb") as f:
                        f.write(drawing_file.getbuffer())
                    st.success(f"✅ Drawing submitted successfully: {drawing_file.name}")
                except Exception as e:
                    st.error(f"❌ Error submitting drawing: {e}")

    # Seminar submission
    st.subheader("📊 Seminar Submission")
    with st.form("seminar_upload_form"):
        seminar_week = st.selectbox(
            "Select Week for Seminar",
            [f"Week {i}" for i in range(1, 16)],
            key="seminar_week"
        )
        seminar_file = st.file_uploader(
            "Upload Seminar File", 
            type=["pdf", "ppt", "pptx", "doc", "docx"],
            key="seminar_upload"
        )
        submit_seminar = st.form_submit_button("📤 Submit Seminar", use_container_width=True)
        
        if submit_seminar:
            if not student_name or not student_matric:
                st.error("❌ Please set your identity first.")
            elif not seminar_file:
                st.error("❌ Please select a file to upload.")
            else:
                # Save seminar to persistent storage
                seminar_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, "seminar")
                os.makedirs(seminar_dir, exist_ok=True)
                
                # Generate safe filename
                safe_name = f"{student_name}_{student_matric}_{seminar_week}_{seminar_file.name}"
                safe_name = "".join(c for c in safe_name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                
                seminar_path = os.path.join(seminar_dir, safe_name)
                
                try:
                    with open(seminar_path, "wb") as f:
                        f.write(seminar_file.getbuffer())
                    st.success(f"✅ Seminar submitted successfully: {seminar_file.name}")
                except Exception as e:
                    st.error(f"❌ Error submitting seminar: {e}")

    # ===============================================================
    # 📈 STUDENT PROGRESS VIEW
    # ===============================================================
    if student_name and student_matric:
        st.header("📈 My Progress")
        
        # Check if student has submitted any work
        # Check attendance
        attendance_count = 0
        for week_num in range(1, 16):
            week = f"Week {week_num}"
            if has_marked_attendance(course_code, week, student_name, student_matric):
                attendance_count += 1
        
        # Check classwork submissions
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
        
        # Display progress metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Weeks Attended", f"{attendance_count}/15")
        with col2:
            st.metric("Classwork Submitted", classwork_count)
        with col3:
            # Count file submissions
            submission_dirs = ["assignment", "drawing", "seminar"]
            file_count = 0
            for sub_dir in submission_dirs:
                full_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads", course_code, sub_dir)
                if os.path.exists(full_dir):
                    files = os.listdir(full_dir)
                    student_files = [f for f in files if student_name.lower() in f.lower() and student_matric.lower() in f.lower()]
                    file_count += len(student_files)
            st.metric("Files Submitted", file_count)
        
        # Show recent activity
        st.subheader("Recent Activity")
        if attendance_count == 0 and classwork_count == 0 and file_count == 0:
            st.info("No activity yet. Start by marking attendance or submitting assignments!")
        else:
            activities = []
            
            # Add attendance activities
            for week_num in range(1, 16):
                week = f"Week {week_num}"
                if has_marked_attendance(course_code, week, student_name, student_matric):
                    activities.append(f"✅ Attended {week}")
            
            # Add classwork activities
            if classwork_count > 0:
                activities.extend([f"📝 Submitted classwork for {row['Week']}" for _, row in student_submissions.iterrows()])
            
            # Show latest 5 activities
            if activities:
                st.write("**Latest activities:**")
                for activity in activities[-5:]:  # Show last 5 activities
                    st.write(f"- {activity}")
    
    else:
        st.info("Set your identity to view your progress and submission history.")

    # ===============================================================
    # 🆘 HELP SECTION
    # ===============================================================
    with st.expander("❓ Need Help?"):
        st.markdown("""
        **Common Issues & Solutions:**
        
        - **Can't see my scores?** Make sure you've set your identity correctly
        - **Scores not updated?** It may take time for lecturers to grade submissions
        - **Can't submit classwork?** Make sure your lecturer has opened classwork for the week
        - **PDF not downloading?** Try using a different browser or check your downloads folder
        - **Video not playing?** The file might be large - try downloading it instead
        
        **Contact your lecturer if you need further assistance.**
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
    # PERSISTENT STORAGE SETUP
    # -------------------------
def get_persistent_path(folder_type, course_code, filename=None):
    base_dir = "persistent_storage"
    os.makedirs(base_dir, exist_ok=True)

    if not course_code:
        # Defensive handling
        return None

    folder_path = os.path.join(base_dir, folder_type, course_code)
    os.makedirs(folder_path, exist_ok=True)

    if filename:
        return os.path.join(folder_path, filename)
    return folder_path

    ensure_persistent_dirs()

    pdf_dir = get_persistent_path("pdf", course_code)
    if not pdf_dir:
        st.error("⚠️ Invalid PDF directory. Make sure a valid course code is selected.")
        st.stop()
    os.makedirs(pdf_dir, exist_ok=True)


    if not course_code:
        st.error("⚠️ No course selected. Please select a course to manage.")
        st.stop()

    # ✅ Define all persistent files safely
    LECTURE_FILE = f"data/{course_code}_lecture.csv"
    CLASSWORK_FILE = f"data/{course_code}_classwork.csv"
    ATTENDANCE_FILE = f"data/{course_code}_attendance.csv"
    STUDENT_LIST_FILE = f"data/{course_code}_students.csv"

    
    # Base directories for student uploads
    base_dir = os.path.join(PERSISTENT_DATA_DIR, "student_uploads")
    scores_dir = os.path.join(PERSISTENT_DATA_DIR, "scores")
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(scores_dir, exist_ok=True)

    # -------------------------
    # Lecture Management
    # -------------------------
    st.header("📚 Lecture Management")

    # Load lectures CSV safely from persistent storage
    if os.path.exists(LECTURE_FILE):
        lectures_df = pd.read_csv(LECTURE_FILE)
        lectures_df.columns = lectures_df.columns.str.strip()
    else:
        lectures_df = pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment", "PDF_File"])

    # Ensure all required columns exist
    for col in ["Week", "Topic", "Brief", "Classwork", "Assignment", "PDF_File"]:
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

        # 🎯 PERSISTENT PDF Upload
        st.markdown("**Upload PDF Files (Permanent Storage)**")
        
        # Use persistent PDF directory
        pdf_dir = get_persistent_path("pdf", course_code)
        os.makedirs(pdf_dir, exist_ok=True)
        
        # PDF Upload
        lecture_pdf = st.file_uploader("Lecture PDF", type=["pdf"], key=f"pdf_{week}")
        
        # Get current PDF path safely
        current_pdf = lectures_df.at[row_idx, "PDF_File"]
        if not isinstance(current_pdf, str):
            current_pdf = str(current_pdf) if current_pdf is not None else ""
        current_pdf = current_pdf.strip()
        
        # Display current PDF if exists in persistent storage
        if current_pdf and os.path.exists(current_pdf):
            st.success(f"📎 Current PDF: {os.path.basename(current_pdf)}")
            
            try:
                with open(current_pdf, "rb") as pdf_file:
                    file_size = os.path.getsize(current_pdf) / (1024 * 1024)
                    st.download_button(
                        label=f"📥 Download Current PDF ({file_size:.1f}MB)",
                        data=pdf_file,
                        file_name=os.path.basename(current_pdf),
                        mime="application/pdf",
                        key=f"download_{week}"
                    )
            except Exception as e:
                st.error(f"❌ Error reading PDF: {e}")
            
            # Option to remove PDF
            if st.button("🗑️ Remove PDF", key=f"remove_{week}"):
                try:
                    if os.path.exists(current_pdf):
                        os.remove(current_pdf)
                    lectures_df.at[row_idx, "PDF_File"] = ""
                    st.session_state["lectures_df"] = lectures_df
                    lectures_df.to_csv(LECTURE_FILE, index=False)
                    st.success("✅ PDF removed successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error removing PDF: {e}")

        # Handle new PDF upload to PERSISTENT storage
        if lecture_pdf is not None:
            safe_name = "".join(c for c in lecture_pdf.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            safe_name = safe_name.replace(' ', '_')
            
            # Use persistent path
            pdf_filename = f"{course_code}_{week.replace(' ', '')}_{safe_name}"
            pdf_path = get_persistent_path("pdf", course_code, pdf_filename)
            
            try:
                with st.spinner("Uploading PDF to permanent storage..."):
                    with open(pdf_path, "wb") as f:
                        f.write(lecture_pdf.getbuffer())
                
                lectures_df.at[row_idx, "PDF_File"] = pdf_path
                st.session_state["lectures_df"] = lectures_df
                lectures_df.to_csv(LECTURE_FILE, index=False)
                
                st.success(f"✅ PDF saved permanently: {lecture_pdf.name}")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error saving PDF: {e}")

        # Update text fields
        lectures_df.at[row_idx, "Topic"] = topic
        lectures_df.at[row_idx, "Brief"] = brief
        lectures_df.at[row_idx, "Classwork"] = classwork
        lectures_df.at[row_idx, "Assignment"] = assignment

        # Save button
        if st.button("💾 Save Changes", key=f"save_{week}"):
            try:
                lectures_df.to_csv(LECTURE_FILE, index=False)
                st.session_state["lectures_df"] = lectures_df
                st.success("✅ All changes saved to permanent storage!")
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

    # 🎛 Classwork Control
    # -------------------------------
    st.header("🎛 Classwork Control")

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

    # 📝 Classwork Submissions Viewing
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

                        # Save the single score to Assignment field by default
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

                        # Compute Total & Grade using weights
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
    # PERSISTENT Video Upload & Management
    # -------------------------
    st.divider()
    st.subheader("🎥 Upload & Manage Video Lectures (Permanent Storage)")

    # Use persistent video directory
    video_dir = get_persistent_path("video", course_code)
    os.makedirs(video_dir, exist_ok=True)

    # Video upload section
    st.markdown("### 📤 Upload New Video")
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
            try:
                safe_name = "".join(c for c in uploaded_video.name if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
                safe_name = safe_name.replace(' ', '_')
                
                # Use persistent path
                save_path = get_persistent_path("video", course_code, safe_name)
                
                # Handle duplicates
                base_name, ext = os.path.splitext(safe_name)
                counter = 1
                while os.path.exists(save_path):
                    save_path = get_persistent_path("video", course_code, f"{base_name}_{counter}{ext}")
                    counter += 1
                
                with st.spinner("Uploading video to permanent storage..."):
                    chunk_size = 1024 * 1024
                    with open(save_path, "wb") as f:
                        chunk = uploaded_video.read(chunk_size)
                        while chunk:
                            f.write(chunk)
                            chunk = uploaded_video.read(chunk_size)
                
                st.success(f"✅ Video saved permanently: {os.path.basename(save_path)}")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to save video: {str(e)}")

    # Display existing videos from PERSISTENT storage
    st.markdown("### 📚 Permanent Video Library")
    
    video_files = []
    try:
        if os.path.exists(video_dir):
            video_files = sorted([f for f in os.listdir(video_dir) 
                                if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv'))])
    except Exception as e:
        st.error(f"Error accessing video directory: {e}")
    
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

    # -------------------------
    # Delete Attendance Records
    # -------------------------
    st.divider()
    st.subheader("🗑️ Delete Attendance Records")
    
    # Get all attendance files for this course
    attendance_files = []
    attendance_folder = get_persistent_path("attendance")
    if os.path.exists(attendance_folder):
        attendance_files = [f for f in os.listdir(attendance_folder) if f.startswith(f"attendance_{course_code}_")]
    
    if attendance_files:
        selected_file = st.selectbox("Select attendance file to delete:", attendance_files)
        if st.button("🗑️ Delete Selected Attendance File"):
            file_path = os.path.join(attendance_folder, selected_file)
            try:
                os.remove(file_path)
                st.success(f"✅ Deleted: {selected_file}")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Failed to delete: {e}")
    else:
        st.info("No attendance files found for this course.")

    # ------------------------
    # Backup Option
    # ------------------------
    st.divider()
    st.subheader("💾 Backup System")
    
    if st.button("📦 Create Data Backup"):
        if backup_persistent_data():
            st.success("✅ Backup created successfully!")
    
    st.markdown(f"---\n*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    
# 🚪 SHOW VIEW BASED ON ROLE
# ===============================================================
if st.session_state["role"] == "Admin":
    admin_view(course_code)
elif st.session_state["role"] == "Student":
    student_view(course_code)
else:
    st.warning("Please select your role from the sidebar to continue.")












































































































































































































