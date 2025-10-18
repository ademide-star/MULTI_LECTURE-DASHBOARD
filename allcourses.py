import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, date, timedelta, time
from streamlit_autorefresh import st_autorefresh
import zipfile
import io
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
import pandas as pd
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

# ===============================================================
# 📘 LECTURE INITIALIZATION
# ===============================================================
def init_lectures(course_code, default_weeks):
    """Create or load lectures CSV for a course. Returns DataFrame."""
    LECTURE_FILE = get_file(course_code, "lectures")
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

default_topics = [f"Lecture Topic {i+1}" for i in range(12)]
lectures_df = init_lectures(course_code, default_topics)

# -----------------------------
# --- Helper Function: View/Download Files ---
def init_lectures(course_code, topics):
    """Initialize lecture weeks dataframe."""
    df_path = os.path.join(LECTURE_DIR, f"{course_code}_lectures.csv")
    if os.path.exists(df_path):
        return pd.read_csv(df_path)
    else:
        df = pd.DataFrame({"Week": [f"Week {i+1}" for i in range(12)], "Topic": topics})
        df.to_csv(df_path, index=False)
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


def has_marked_attendance(course_code, week, name):
    """Check if student already marked attendance."""
    path = os.path.join(LOG_DIR, f"{course_code}_attendance.csv")
    if not os.path.exists(path):
        return False
    df = pd.read_csv(path)
    return ((df["Name"] == name) & (df["Week"] == week)).any()


def mark_attendance_entry(course_code, name, matric, week):
    """Mark student attendance and save persistently."""
    path = os.path.join(LOG_DIR, f"{course_code}_attendance.csv")
    data = {
        "Name": [name],
        "Matric": [matric],
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
def has_marked_attendance(course_code, week, name):
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


def save_file(course_code, name, week, uploaded_file, file_type):
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
        
def save_classwork(name, matric, week, answers):
    """Save classwork answers to a CSV file."""
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork_answers")
    if not os.path.exists(CLASSWORK_STATUS_FILE):
        pd.DataFrame(columns=["StudentName", "Matric", "Week", "Answers", "Timestamp"]).to_csv(CLASSWORK_STATUS_FILE, index=False)

    df = pd.read_csv(CLASSWORK_STATUS_FILE)
    answers_str = "; ".join([f"Q{i+1}: {ans.strip()}" for i, ans in enumerate(answers) if ans.strip()])
    new_row = {"StudentName": name.strip(), "Matric": matric.strip(), "Week": week, "Answers": answers_str, "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(CLASSWORK_FILE, index=False)
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


def mark_attendance_entry(course_code, name, matric, week):
    """Robust attendance marker — auto-fixes missing columns, duplicates, and broken files."""
    try:
        file_path = get_file(course_code, "attendance")
        if not file_path:
            raise ValueError("⚠️ Invalid attendance file path for this course.")

        # ✅ Ensure folder exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # ✅ Load file or create new one
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
            except Exception:
                # File exists but unreadable — recreate it cleanly
                df = pd.DataFrame(columns=["StudentName", "Matric", "Week", "Status", "Timestamp"])
        else:
            df = pd.DataFrame(columns=["StudentName", "Matric", "Week", "Status", "Timestamp"])

        # ✅ Normalize all column names (fixes case sensitivity)
        df.columns = [str(c).strip().title().replace(" ", "") for c in df.columns]

        # ✅ Ensure required columns exist
        required = ["StudentName", "Matric", "Week", "Status", "Timestamp"]
        for col in required:
            if col not in df.columns:
                df[col] = None

        # ✅ Remove duplicate/unnamed columns and fix index
        df = df.loc[:, ~df.columns.duplicated()]
        df = df.loc[:, ~df.columns.str.contains("^Unnamed", case=False, na=False)]
        df.reset_index(drop=True, inplace=True)

        # ✅ Convert to string (avoid dtype errors)
        for col in ["StudentName", "Matric", "Week"]:
            df[col] = df[col].astype(str).fillna("")

        # ✅ Check for duplicates
        already = df[
            (df["StudentName"].str.lower() == name.strip().lower()) &
            (df["Week"].astype(str) == str(week))
        ]
        if not already.empty:
            return False  # Already marked

        # ✅ Append new record
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
        st.error(f"⚠️ Error marking attendance: {e}")
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

# ---------------------- Student View ---------------------- #
def student_view():
    if st.session_state.get("role") != "Student":
        return

    st.title("🎓 Student Dashboard")
    st.info("Welcome, Student! Access your lectures, upload assignments, and mark attendance here.")
    st.subheader("🎓 Student Login and Attendance")

    submit_attendance = False

    # -------------------------------
    # 🕒 Attendance Form
    # -------------------------------
    course_code = st.selectbox("Select Course", ["MCB221", "BCH201", "BIO203", "BIO113", "BIO306"])
    with st.form(f"{course_code}_attendance_form"):
        name = st.text_input("Full Name", key=f"{course_code}_student_name")
        matric = st.text_input("Matric Number", key=f"{course_code}_student_matric")

        lectures_df = st.session_state.get("lectures_df") or load_lectures(course_code)

        if "Week" not in lectures_df.columns:
            st.error("⚠️ The lectures file is missing the 'Week' column.")
            st.stop()

        week = st.selectbox(
            "Select Lecture Week", 
            [str(w) for w in lectures_df["Week"].tolist()], 
            key=f"{course_code}_att_week"
        )
        attendance_code = st.text_input("Enter Attendance Code (Ask your lecturer)", key=f"{course_code}_att_code")
        submit_attendance = st.form_submit_button("✅ Mark Attendance", use_container_width=True)

    # -------------------------------
    # 🧾 Attendance Validation
    # -------------------------------
    if submit_attendance:
        if not name.strip() or not matric.strip():
            st.warning("Please enter your full name and matric number.")
        elif not attendance_code.strip():
            st.warning("Please enter the attendance code for today.")
        else:
            COURSE_TIMINGS = {
                "BIO203": {"valid_code": "BIO203-ZT7", "start": "01:00", "end": "22:00"},
                "BCH201": {"valid_code": "BCH201-ZT8", "start": "01:00", "end": "22:00"},
                "MCB221": {"valid_code": "MCB221-ZT9", "start": "01:00", "end": "22:20"},
                "BIO113": {"valid_code": "BIO113-ZT1", "start": "01:00", "end": "22:00"},
                "BIO306": {"valid_code": "BIO306-ZT2", "start": "01:00", "end": "22:00"},
            }

            if course_code not in COURSE_TIMINGS:
                st.error(f"⚠️ No timing configured for {course_code}.")
            else:
                start_time = datetime.strptime(COURSE_TIMINGS[course_code]["start"], "%H:%M").time()
                end_time = datetime.strptime(COURSE_TIMINGS[course_code]["end"], "%H:%M").time()
                valid_code = COURSE_TIMINGS[course_code]["valid_code"]

                now_t = (datetime.utcnow() + timedelta(hours=1)).time()  # UTC+1

                st.session_state["attended_week"] = str(week)  # store as string

                if not (start_time <= now_t <= end_time):
                    st.error(f"⏰ Attendance for {course_code} is only open between "
                             f"{start_time.strftime('%I:%M %p')} and {end_time.strftime('%I:%M %p')}.")
                elif attendance_code != valid_code:
                    st.error("❌ Invalid attendance code. Ask your lecturer for today’s code.")
                elif has_marked_attendance(course_code, week, name):
                    st.info("✅ Attendance already marked.")
                else:
                    ok = mark_attendance_entry(course_code, name, matric, week)
                    if ok:
                        st.success(f"✅ Attendance recorded for {name} ({week}).")

    # ---------------------------------------------
    # 📘 Lecture Briefs and Classwork
    # ---------------------------------------------
    st.divider()
    st.subheader("📘 Lecture Briefs and Classwork")

    if "attended_week" not in st.session_state:
        st.warning("Please attend a lecture before accessing materials.")
        return

    week = str(st.session_state["attended_week"])
    st.success(f"Access granted for {week}")

    lectures_df = st.session_state.get("lectures_df") or load_lectures(course_code)
    lecture_info = lectures_df.loc[lectures_df["Week"] == week].iloc[0].to_dict()

    # Topic & Brief
    st.subheader(f"📖 {week}: {lecture_info.get('Topic', 'No topic available')}")
    brief = clean_text(lecture_info.get("Brief"))
    if brief:
        st.write(f"**Lecture Brief:** {brief}")
    else:
        st.info("Lecture brief not yet available.")

    # Assignment
    assignment = clean_text(lecture_info.get("Assignment"))
    if assignment:
        st.subheader("📚 Assignment")
        st.markdown(f"**Assignment:** {assignment}")
    else:
        st.info("Assignment not yet released.")

    # ---------------------- Classwork Section ---------------------- #
    classwork_text = clean_text(lecture_info.get("Classwork"))
    if classwork_text:
        st.markdown("### 🧩 Classwork Questions")
        questions = [q.strip() for q in classwork_text.split(";") if q.strip()]

        remaining_sec = get_remaining_time(course_code, week)
        timer_placeholder = st.empty()
        progress_placeholder = st.empty()

        if remaining_sec > 0:
            st_autorefresh(interval=1000, key=f"{course_code}_{week}_cw_timer")

            minutes, seconds = divmod(remaining_sec, 60)
            timer_placeholder.info(f"⏱ Time remaining: {minutes:02d}:{seconds:02d} minutes")

            # Progress bar
            total_duration = 20 * 60
            progress = min(max((total_duration - remaining_sec) / total_duration, 0), 1)
            progress_placeholder.progress(progress)

            with st.form("cw_form"):
                answers_state_key = f"{course_code}_{week}_answers"
                if answers_state_key not in st.session_state:
                    st.session_state[answers_state_key] = [""] * len(questions)

                answers = []
                for i, q in enumerate(questions):
                    ans = st.text_input(f"Q{i+1}: {q}", value=st.session_state[answers_state_key][i], key=f"{answers_state_key}_{i}")
                    answers.append(ans)
                    st.session_state[answers_state_key][i] = ans

                submit_cw = st.form_submit_button(
                    "Submit Answers",
                    disabled=remaining_sec == 0 or not is_classwork_open(course_code, week)
                )
                if submit_cw:
                    save_classwork(name, matric, week, answers)
                    st.success("✅ Classwork submitted successfully!")
        else:
            timer_placeholder.info("⏳ Classwork not yet opened by Admin or time expired.")
            progress_placeholder.progress(1.0)

    # ---------------------- Lecture Materials (PDFs) ---------------------- #
    st.divider()
    st.subheader("📚 Lecture Materials")
    modules_dir = "modules"
    lecture_pdf_path = os.path.join(modules_dir, f"{course_code}_{week}_lecture.pdf")
    classwork_pdf_path = os.path.join(modules_dir, f"{course_code}_{week}_classwork.pdf")
    assignment_pdf_path = os.path.join(modules_dir, f"{course_code}_{week}_assignment.pdf")

    def show_pdf(file_path, label):
        if os.path.exists(file_path):
            st.markdown(f"**{label}**")
            with open(file_path, "rb") as pdf_file:
                st.download_button(
                    label=f"📥 Download {label}",
                    data=pdf_file.read(),
                    file_name=os.path.basename(file_path),
                    mime="application/pdf"
                )
            with open(file_path, "rb") as pdf_file:
                base64_pdf = base64.b64encode(pdf_file.read()).decode("utf-8")
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600px"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
        else:
            st.info(f"{label} not uploaded yet.")

    show_pdf(lecture_pdf_path, f"Lecture Note ({week})")
    show_pdf(classwork_pdf_path, f"Classwork ({week})")
    show_pdf(assignment_pdf_path, f"Assignment ({week})")


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
        else:
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

        # 🎬 Lecture Videos
        st.divider()
        st.subheader("🎬 Watch Lecture Videos")

        video_dir = os.path.join("video_lectures", course_code)
        if os.path.exists(video_dir):
            video_files = sorted(os.listdir(video_dir))
            if video_files:
                selected_video = st.selectbox("Select a lecture to watch:", video_files, key=f"{course_code}_video_select")
                st.video(os.path.join(video_dir, selected_video))
            else:
                st.info("No lecture videos uploaded yet.")
        else:
            st.warning("📁 No video directory found for this course.")

    # Ensure base directory exists
    base_dir = "uploads"
    os.makedirs(base_dir, exist_ok=True)


def admin_view(course_code):

    st.title("👩‍🏫 Admin Dashboard")
    st.subheader("🔐 Teacher / Admin Panel")

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
            new_row = {"Week": week, "Topic": "", "Brief": "", "Classwork": "", "Assignment": ""}
            lectures_df = pd.concat([lectures_df, pd.DataFrame([new_row])], ignore_index=True)
            row_idx = lectures_df[lectures_df["Week"] == week].index[0]
            st.session_state["lectures_df"] = lectures_df

         # Access existing/default values safely
        topic_default = lectures_df.at[row_idx, "Topic"]
        brief_default = lectures_df.at[row_idx, "Brief"]
        classwork_default = lectures_df.at[row_idx, "Classwork"]
        assignment_default = lectures_df.at[row_idx, "Assignment"]  
        
        topic = st.text_input("Lecture Topic", value=lectures_df.at[row_idx, "Topic"])
        brief = st.text_area("Lecture Brief", value=lectures_df.at[row_idx, "Brief"])
        classwork = st.text_area("Classwork (separate questions with ;)", value=lectures_df.at[row_idx, "Classwork"])
        assignment = st.text_area("Assignment (separate questions with ;)", value=lectures_df.at[row_idx, "Assignment"])

        st.markdown("**Upload PDF Files (Optional)**")
        lecture_pdf = st.file_uploader("Lecture PDF", type=["pdf"])
        classwork_pdf = st.file_uploader("Classwork PDF", type=["pdf"])
        assignment_pdf = st.file_uploader("Assignment PDF", type=["pdf"])

        if st.button(f"💾 Save Lecture / Classwork / Assignment ({week})", key=f"save_{week}"):
            lectures_df.loc[row_idx, ["Topic", "Brief", "Classwork", "Assignment"]] = [topic, brief, classwork, assignment]
            
            lectures_df.to_csv(LECTURE_FILE, index=False)
            st.session_state["lectures_df"] = lectures_df
            st.success(f"✅ Lecture, Classwork, and Assignment for {week} saved!")
            
            modules_dir = "modules"
            os.makedirs(modules_dir, exist_ok=True)
            # Save PDFs
            if lecture_pdf:
                lecture_pdf_path = os.path.join(modules_dir, f"{course_code}_{week}_lecture.pdf")
                with open(lecture_pdf_path, "wb") as f: f.write(lecture_pdf.getbuffer())
                st.success(f"✅ Lecture PDF uploaded for {week}")
            if classwork_pdf:
                classwork_pdf_path = os.path.join(modules_dir, f"{course_code}_{week}_classwork.pdf")
                with open(classwork_pdf_path, "wb") as f: f.write(classwork_pdf.getbuffer())
                st.success(f"✅ Classwork PDF uploaded for {week}")
            if assignment_pdf:
                assignment_pdf_path = os.path.join(modules_dir, f"{course_code}_{week}_assignment.pdf")
                with open(assignment_pdf_path, "wb") as f: f.write(assignment_pdf.getbuffer())
                st.success(f"✅ Assignment PDF uploaded for {week}")

            st.dataframe(lectures_df, use_container_width=True)

    # -------------------------
    # Student Records
    # -------------------------
    st.header("📋 Student Records")
    for file, label in [
        (ATTENDANCE_FILE, "Attendance Records"),
        (CLASSWORK_FILE, "Classwork Submissions"),
        (SEMINAR_FILE, "Seminar Submissions")
    ]:
        st.divider()
        st.markdown(f"### {label}")
        if os.path.exists(file):
            try:
                df = pd.read_csv(file)
                st.dataframe(df, use_container_width=True)
                st.download_button(
                    label=f"⬇️ Download {label} CSV",
                    data=df.to_csv(index=False).encode(),
                    file_name=os.path.basename(file),
                    mime="text/csv",
                    key=f"{label}_download"
                )
            except Exception as e:
                st.error(f"Failed to read {label}: {e}")
        else:
            st.info(f"No {label.lower()} yet.")

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
    # Video upload & management
    # -------------------------
    st.divider()
    st.subheader("🎥 Upload & Manage Video Lectures")

    video_dir = os.path.join(base_dir, course_code, "videos")
    os.makedirs(video_dir, exist_ok=True)

    uploaded_video = st.file_uploader("Upload Lecture Video (MP4 only)", type=["mp4"], key=f"{course_code}_video_upload")
    if uploaded_video:
        try:
            save_path = os.path.join(video_dir, uploaded_video.name)
            base_name, ext = os.path.splitext(uploaded_video.name)
            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join(video_dir, f"{base_name}_{counter}{ext}")
                counter += 1
            with open(save_path, "wb") as f:
                f.write(uploaded_video.read())
            st.success(f"✅ Video uploaded successfully: {os.path.basename(save_path)}")
        except Exception as e:
            st.error(f"Failed to save uploaded video: {e}")

    video_files = sorted(os.listdir(video_dir)) if os.path.exists(video_dir) else []
    if video_files:
        st.markdown("### 📚 Uploaded Lecture Videos")
        for video in video_files:
            video_path = os.path.join(video_dir, video)
            try:
                st.video(video_path)
                with open(video_path, "rb") as vid_file:
                    st.download_button(
                        label=f"⬇️ Download {video}",
                        data=vid_file.read(),
                        file_name=video,
                        mime="video/mp4"
                    )
            except Exception:
                st.info(f"Cannot preview or download {video}.")
    else:
        st.info("No videos uploaded yet.")

    if st.button("Check Attendance Columns"):
        file_path = get_file(course_code, "attendance_form")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            st.write(df.columns)
        else:
            st.warning("Attendance file not found!")
    # -------------------------------------
# 🧩 CLASSWORK CONTROL
# -------------------------------------
        st.header("🧩 Classwork Control")

        week_to_control = st.selectbox(
            "Select Week to Open/Close Classwork", 
            lectures_df["Week"].unique(), 
            key="admin_cw_control"
)

        if st.button(f"📖 Open Classwork for {week_to_control} (20 mins)", key="admin_open_cw"):
            open_classwork(course_code, week_to_control)
            st.success(f"✅ Classwork for {week_to_control} is now open for 20 minutes.")

        close_classwork_after_20min(course_code)
# Footer timestamp
        st.markdown(f"---\n*Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")



# 🚪 SHOW VIEW BASED ON ROLE
# ===============================================================
if st.session_state["role"] == "Admin":
    admin_view(course_code)
elif st.session_state["role"] == "Student":
    student_view()
else:
    st.warning("Please select your role from the sidebar to continue.")







































































