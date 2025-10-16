import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, date, timedelta, time
from streamlit_autorefresh import st_autorefresh
import zipfile
import io

import os

MODULES_DIR = "modules"
UPLOAD_DIR = "student_uploads"

os.makedirs(MODULES_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

# Ensure all folders exist
for folder in [MODULES_DIR, LECTURE_DIR, UPLOAD_DIR, LOG_DIR, SEMINAR_DIR]:
    os.makedirs(folder, exist_ok=True)

# Save student files in a consistent structure
student_upload_path = os.path.join(UPLOAD_DIR, course_code)
os.makedirs(student_upload_path, exist_ok=True)

# Tracker CSV
TRACK_FILE = os.path.join(student_upload_path, "submission_tracker.csv")
if not os.path.exists(TRACK_FILE):
    pd.DataFrame(columns=["StudentName", "MatricNo", "Week", "Assignment", "Drawing", "Seminar"]).to_csv(TRACK_FILE, index=False)

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
import streamlit as st

def display_all_module_pdfs(course_code):
    """
    Lists all module PDFs for a course and provides download buttons.
    """
    # List all PDF files in MODULES_DIR that start with course_code
    pdf_files = [
        f for f in os.listdir(MODULES_DIR)
        if os.path.isfile(os.path.join(MODULES_DIR, f))
        and f.lower().endswith(".pdf")
        and f.startswith(course_code)
    ]

    if not pdf_files:
        st.info("No module PDFs uploaded yet for this course.")
        return

    st.subheader("📂 Available Module PDFs")
    for pdf_file in pdf_files:
        pdf_path = os.path.join(MODULES_DIR, pdf_file)
        week_name = pdf_file.replace(f"{course_code}_", "").replace("_module.pdf", "").replace("_", " ")
        try:
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label=f"📥 {week_name} Module PDF",
                    data=f.read(),
                    file_name=pdf_file,
                    mime="application/pdf",
                    key=f"{pdf_file}_dl"
                )
        except Exception as e:
            st.error(f"Could not load file {pdf_file}: {e}")


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


def view_and_download_files(course_code, week=None, upload_type=None):
    """
    Displays and allows downloading of uploaded files for a course.

    Args:
        course_code (str): The course code folder.
        week (str, optional): Filter files for a specific week. Defaults to None.
        upload_type (str, optional): Filter files by type ('assignment', 'drawing', 'seminar'). Defaults to None.
    """
    # Folder where files are stored
    UPLOAD_DIR = os.path.join("uploads", course_code)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    try:
        files = os.listdir(UPLOAD_DIR)
        if not files:
            st.info("No files uploaded yet for this course.")
            return

        # Optionally filter by week or type
        if week:
            files = [f for f in files if week.replace(" ", "_") in f]
        if upload_type:
            files = [f for f in files if upload_type.lower() in f.lower()]

        if not files:
            st.info("No files match the selected criteria.")
            return

        st.subheader("📂 Available Files for Download")
        for file in files:
            file_path = os.path.join(UPLOAD_DIR, file)
            with open(file_path, "rb") as f:
                st.download_button(
                    label=f"📥 Download {file}",
                    data=f.read(),
                    file_name=file,
                    mime=None,  # Streamlit will auto-detect
                    key=f"{course_code}_{file}_dl"
                )
    except Exception as e:
        st.error(f"⚠️ Error displaying files: {e}")


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
import os
import pandas as pd
import streamlit as st

def view_and_download_files(course_code):
    """
    Displays download buttons for files actually submitted by instructor/students
    using the submission tracker CSV.
    """
    # Tracker CSV path
    TRACK_FILE = os.path.join("uploads", course_code, "submission_tracker.csv")

    # Check if tracker exists
    if not os.path.exists(TRACK_FILE):
        st.info("No files have been uploaded yet for this course.")
        return

    tracker_df = pd.read_csv(TRACK_FILE)

    # Folder where files are saved
    UPLOAD_DIR = os.path.join("uploads", course_code)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    st.subheader("📂 Available Files for Download")

    any_files = False
    for _, row in tracker_df.iterrows():
        student_name = row.get("StudentName", "")
        matric_no = row.get("MatricNo", "")
        week = row.get("Week", "")
        for sub_type in ["Assignment", "Drawing", "Seminar"]:
            filename = row.get(sub_type, "")
            if filename and os.path.exists(os.path.join(UPLOAD_DIR, filename)):
                any_files = True
                file_path = os.path.join(UPLOAD_DIR, filename)
                with open(file_path, "rb") as f:
                    st.download_button(
                        label=f"📥 {sub_type}: {student_name} ({matric_no}) - {week}",
                        data=f.read(),
                        file_name=filename,
                        mime=None,
                        key=f"{filename}_dl"
                    )

    if not any_files:
        st.info("No files have been uploaded yet for this course.")

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



import os
import pandas as pd

def init_lectures(lecture_data, lecture_file):
    """
    Initialize lectures by saving the lecture_data to a CSV file.
    Ensures that the parent directory exists before saving (works locally and on deployment).
    
    Parameters:
    - lecture_data: dict or list of dicts containing lecture info
    - lecture_file: str, path to the CSV file to save
    """
    # Ensure the parent directory exists
    os.makedirs(os.path.dirname(lecture_file), exist_ok=True)
    
    # Convert the data to DataFrame and save
    pd.DataFrame(lecture_data).to_csv(lecture_file, index=False)
    
    print(f"Lecture data successfully saved to: {lecture_file}")


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
# -----------------------------
# ATTENDANCE + SUBMISSION HELPERS
# -----------------------------
def has_marked_attendance(course_code, week, name):
    """Return True if student already has attendance for the week."""
    ATTENDANCE_FILE = get_file(course_code, "attendance")
    if not os.path.exists(ATTENDANCE_FILE):
        return False
    df = pd.read_csv(ATTENDANCE_FILE)
    if "StudentName" not in df.columns or "Week" not in df.columns:
        return False
    return ((df["StudentName"].str.lower() == name.strip().lower()) & (df["Week"] == week)).any()

def mark_attendance_entry(course_code, name, matric, week):
    """Mark attendance (returns True on success, False if already marked)."""
    ATTENDANCE_FILE = get_file(course_code, "attendance")
    if not os.path.exists(ATTENDANCE_FILE):
        pd.DataFrame(columns=["StudentName", "Matric", "Week", "Status", "Timestamp"]).to_csv(ATTENDANCE_FILE, index=False)

    df = pd.read_csv(ATTENDANCE_FILE)
    if ((df["StudentName"].str.lower() == name.strip().lower()) & (df["Week"] == week)).any():
        return False
    new_row = {"StudentName": name.strip(), "Matric": matric.strip(), "Week": week, "Status": "Present", "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(ATTENDANCE_FILE, index=False)
    return True


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


MODULES_DIR = "modules"
os.makedirs(MODULES_DIR, exist_ok=True)

import os
import streamlit as st

# Ensure directories exist
os.makedirs("modules", exist_ok=True)
os.makedirs("student_uploads", exist_ok=True)

MODULES_DIR = "modules"
UPLOAD_DIR = "student_uploads"

# ------------------------------
# Single module PDF for a week
# ------------------------------
def display_module_pdf(course_code, week):
    """
    Display the module PDF for a specific course and week.
    """
    pdf_filename = f"{course_code}_{week.replace(' ','_')}_module.pdf"
    pdf_path = os.path.join(MODULES_DIR, pdf_filename)

    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            st.download_button(
                label=f"📥 Download {week} Module PDF",
                data=f.read(),
                file_name=pdf_filename,
                mime="application/pdf",
                key=f"{course_code}_{week}_pdf"
            )
    else:
        st.info("Module PDF not yet uploaded.")


# ------------------------------
# Display all module PDFs for a course
# ------------------------------
def display_all_module_pdfs(course_code):
    """
    Lists all module PDFs for a course and provides download buttons.
    """
    # Ensure MODULES_DIR exists
    os.makedirs(MODULES_DIR, exist_ok=True)

    # List all PDF files in MODULES_DIR that match the course code
    pdf_files = [
        f for f in os.listdir(MODULES_DIR)
        if os.path.isfile(os.path.join(MODULES_DIR, f))
        and f.lower().endswith(".pdf")
        and f.startswith(course_code)
    ]

    if not pdf_files:
        st.info("No module PDFs uploaded yet for this course.")
        return

    st.subheader("📂 Available Module PDFs")
    for pdf_file in pdf_files:
        pdf_path = os.path.join(MODULES_DIR, pdf_file)
        week_name = pdf_file.replace(f"{course_code}_", "").replace("_module.pdf", "").replace("_", " ")
        try:
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label=f"📥 {week_name} Module PDF",
                    data=f.read(),
                    file_name=pdf_file,
                    mime="application/pdf",
                    key=f"{pdf_file}_dl"
                )
        except Exception as e:
            st.error(f"Could not load file {pdf_file}: {e}")



def mark_attendance_entry(course_code, name, matric, week):
    """Marks attendance for a given student safely with auto-column creation."""
    try:
        file_path = get_file(course_code, "attendance")

        # ✅ Load or initialize attendance DataFrame
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
        else:
            df = pd.DataFrame(columns=["StudentName", "Matric", "Week", "Timestamp"])

        # ✅ Ensure required columns exist
        for col in ["StudentName", "Matric", "Week", "Timestamp"]:
            if col not in df.columns:
                df[col] = None

        # ✅ Standardize column names (in case older files used different headers)
        df.columns = [c.strip().title().replace(" ", "") for c in df.columns]

        # ✅ Check if student has already marked attendance for this week
        if ((df["Studentname"].str.lower() == name.strip().lower()) & 
            (df["Week"].astype(str) == str(week))).any():
            return False  # already marked

        # ✅ Record new attendance
        new_entry = {
            "StudentName": name.strip(),
            "Matric": matric.strip(),
            "Week": week,
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)

        # ✅ Save back to CSV
        df.to_csv(file_path, index=False)
        return True

    except Exception as e:
        st.error(f"⚠️ Error marking attendance: {e}")
        return False


def student_view():
    if st.session_state.get("role") == "Student":
        st.title("🎓 Student Dashboard")
        st.info("Welcome, Student! Access your lectures, upload assignments, and mark attendance here.")
        st.subheader("🎓 Student Login and Attendance")

        # Initialize safe variables
        submit_attendance = False
        ok = False

        # -------------------------------
        # 🕒 Attendance Form
        # -------------------------------
        course_code = st.selectbox("Select Course",  ["BIO113", "BIO306", "BIO203", "BCH201", "MCB221"])
        with st.form(f"{course_code}_attendance_form"):
            name = st.text_input("Full Name", key=f"{course_code}_student_name")
            matric = st.text_input("Matric Number", key=f"{course_code}_student_matric")

            # ✅ Ensure lectures_df is defined before use
            if "lectures_df" not in st.session_state or st.session_state["lectures_df"] is None:
                try:
                    lectures_df = pd.read_csv(get_file(course_code, "lectures"))
                    st.session_state["lectures_df"] = lectures_df
                except Exception as e:
                    st.error(f"⚠️ Unable to load lecture file for {course_code}: {e}")
                    st.stop()
            else:
                lectures_df = st.session_state["lectures_df"]

            # ✅ Safety check: make sure Week column exists
            if "Week" not in lectures_df.columns:
                st.error("⚠️ The lectures file is missing the 'Week' column. Please upload a valid lectures CSV.")
                st.stop()

            week = st.selectbox("Select Lecture Week", lectures_df["Week"].tolist(), key=f"{course_code}_att_week")
            attendance_code = st.text_input("Enter Attendance Code (Ask your lecturer)", key=f"{course_code}_att_code")
            submit_attendance = st.form_submit_button("✅ Mark Attendance", use_container_width=True)

        # -------------------------------
        # 🧾 Attendance Validation Logic
        # -------------------------------
        if submit_attendance:
            if not name.strip() or not matric.strip():
                st.warning("Please enter your full name and matric number.")
            elif not attendance_code.strip():
                st.warning("Please enter the attendance code for today.")
            else:
                COURSE_TIMINGS = {
                    "BIO203": {"valid_code": "BIO203-ZT7", "start": "13:00", "end": "22:00"},
                    "BCH201": {"valid_code": "BCH201-ZT8", "start": "13:00", "end": "22:00"},
                    "MCB221": {"valid_code": "MCB221-ZT9", "start": "10:00", "end": "10:32"},
                    "BIO113": {"valid_code": "BIO113-ZT1", "start": "07:00", "end": "22:00"},
                    "BIO306": {"valid_code": "BIO306-ZT2", "start": "14:00", "end": "22:00"},
                }

                if course_code not in COURSE_TIMINGS:
                    st.error(f"⚠️ No timing configured for {course_code}.")
                else:
                    start_time = datetime.strptime(COURSE_TIMINGS[course_code]["start"], "%H:%M").time()
                    end_time = datetime.strptime(COURSE_TIMINGS[course_code]["end"], "%H:%M").time()
                    valid_code = COURSE_TIMINGS[course_code]["valid_code"]

                    now_t = (datetime.utcnow() + timedelta(hours=1)).time()  # Nigeria timezone (UTC+1)

                    if not (start_time <= now_t <= end_time):
                        st.error(f"⏰ Attendance for {course_code} is only open between "
                                 f"{start_time.strftime('%I:%M %p')} and {end_time.strftime('%I:%M %p')}.")
                    elif attendance_code != valid_code:
                        st.error("❌ Invalid attendance code. Ask your lecturer for today’s code.")
                    elif has_marked_attendance(course_code, week, name):
                        st.info("✅ Attendance already marked. You can’t mark it again.")
                        st.session_state["attended_week"] = week
                    else:
                        ok = mark_attendance_entry(course_code, name, matric, week)
                        if ok:
                            st.success(f"✅ Attendance recorded for {name} ({week}).")
                            st.session_state["attended_week"] = week
                            

    # ---------------------------------------------
    # 📘 Lecture Briefs and Classwork
    # ---------------------------------------------
        st.divider()
        st.subheader("📘 Lecture Briefs and Classwork")
        st.markdown("Here you can view lecture summaries, slides, and classwork materials.")
    
    # Safely get lecture info
        if "attended_week" in st.session_state:
            st.warning("Please attend a lecture before accessing materials.")
            week = st.session_state["attended_week"]
            st.success(f"Access granted for {week}")

    # ✅ Ensure lectures_df is available
        try:
            if "lectures_df" not in st.session_state:
                file_path = get_file(course_code, "lectures")
                lectures_df = ensure_default_lectures_file(file_path)
                st.session_state["lectures_df"] = lectures_df
        
            else:
                lectures_df = st.session_state["lectures_df"]

    # ✅ Safety check
            if "Week" not in lectures_df.columns:
                st.warning(f"⚠️ No 'Week' column found in lecture data for {course_code}.")
                st.stop()

            if week not in lectures_df["Week"].values:
                st.warning(f"⚠️ No lecture found for {week}.")
                st.stop()

            else:
        # Convert to dict to safely use .get()
                lecture_info = lectures_df[lectures_df["Week"] == week].iloc[0].to_dict()   
        except Exception as e:
            st.error(f"⚠️ Could not load lecture data for {course_code}: {e}")
            st.stop()

    # ✅ Retrieve selected lecture safely
            lecture_info = lectures_df[lectures_df["Week"] == week].iloc[0]
            lectures_df = st.session_state.get("lectures_df", pd.read_csv(get_file(course_code, "lectures")))
            st.session_state["lectures_df"] = lectures_df


    # ✅ Display Topic
        try:
    # Topic and Brief
            st.subheader(f"📖 {week}: {lecture_info.get('Topic', 'No topic available')}")
            brief = str(lecture_info.get("Brief", "") or "").strip()
            if brief:
                st.write(f"**Lecture Brief:** {brief}")
            else:
                st.info("Lecture brief not yet available.")

    # Assignment
            assignment = str(lecture_info.get("Assignment", "") or "").strip()
            if assignment:
                st.subheader("📚 Assignment")
                st.markdown(f"**Assignment:** {assignment}")
            else:
                st.info("Assignment not released yet.")

    # PDF Viewer
            display_module_pdf(course_code, week)

    # Classwork
            classwork_text = str(lecture_info.get("Classwork", "") or "").strip()
            if classwork_text:
                st.markdown("### 🧩 Classwork Questions")
                questions = [q.strip() for q in classwork_text.split(";") if q.strip()]
                with st.form("cw_form"):
                    answers = [st.text_input(f"Q{i+1}: {q}") for i, q in enumerate(questions)]
                    submit_cw = st.form_submit_button(
                        "Submit Answers", 
                        disabled=not is_classwork_open(course_code, week)
            )
                    close_classwork_after_20min(course_code)
                    if submit_cw:
                        save_classwork(name, matric, week, answers)
            else:
                st.info("Classwork not yet released.")

    # PDF download section
            pdf_path = os.path.join(MODULES_DIR, f"{course_code}_{lecture_info.get('Week', '').replace(' ', '_')}.pdf")
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label=f"📥 Download {lecture_info.get('Week', 'Lecture')} Module PDF",
                        data=pdf_file.read(),
                        file_name=f"{course_code}_{lecture_info.get('Week', 'Lecture')}.pdf",
                        mime="application/pdf",
                        key=f"{course_code}_pdf_dl"
            )
            else:
                st.info("Lecture note not uploaded yet.")

        except Exception as e:
            st.error(f"⚠️ Error displaying lecture details: {e}")

            if os.path.dirname(LECTURE_FILE):
                os.makedirs(os.path.dirname(LECTURE_FILE), exist_ok=True)

    # ===============================================================

# -------------------------
# Student View
# -------------------------
        st.title("🎓 Student Dashboard — View Scores")
# Path to scores file
        courses = ["BIO113", "BIO306", "BIO203", "BCH201", "MCB221"]

# Student selects the course
        course_code = st.selectbox("Select Your Course", courses)
# Ask student for their matric number
        matric_no = st.text_input("Enter Your Matric Number").strip().upper()
        score_file = os.path.join("scores", f"{course_code.lower()}_scores.csv")

        if os.path.exists(score_file):
            df = pd.read_csv(score_file)
    
        if matric_no:
        # Filter scores for this student
            student_scores = df[df["MatricNo"].astype(str).str.upper() == matric_no]
        
            if not student_scores.empty:
                st.success(f"✅ Scores for Matric Number: {matric_no}")
            # Show scores table
                st.dataframe(student_scores, use_container_width=True)
            
            # Optionally, download
                st.download_button(
                    "⬇️ Download Your Scores as CSV",
                    student_scores.to_csv(index=False).encode(),
                    file_name=f"{matric_no}_scores.csv",
                    mime="text/csv"
            )
            else:
                st.info("No scores found for this matric number yet.")
        else:
            st.warning("Scores have not been uploaded for this course yet.")


 

# Folder where instructor uploads are stored
        UPLOAD_DIR = os.path.join("uploads", course_code)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        st.subheader("📂 Available Lecture Files")

# List all files in the folder
        uploaded_files = os.listdir(UPLOAD_DIR)

        if uploaded_files:
            for file in uploaded_files:
                file_path = os.path.join(UPLOAD_DIR, file)
        # Display a download button for each file
                with open(file_path, "rb") as f:
                    st.download_button(
                    label=f"📥 {file}",
                    data=f,
                    file_name=file,
                    mime=None  # Let Streamlit detect automatically
            )
        else:
            st.info("No lecture files have been uploaded yet.")

# ===============================================================
# 📄 ASSIGNMENT, DRAWING & SEMINAR UPLOADS (ONE-TIME SUBMISSION)
# ===============================================================

        st.divider()
        st.subheader("📄 Assignment, Drawing & Seminar Uploads")

# -----------------------------
# Ensure lectures_df exists
# -----------------------------
        if "lectures_df" not in st.session_state:
            if os.path.exists(LECTURE_FILE):
                st.session_state["lectures_df"] = pd.read_csv(LECTURE_FILE)
            else:
                st.session_state["lectures_df"] = pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment"])
        lectures_df = st.session_state["lectures_df"]

# Safe weeks list
        weeks = lectures_df["Week"].tolist() if "Week" in lectures_df.columns and not lectures_df.empty else ["Week 1"]

# -----------------------------
# Upload folder & tracker CSV
# -----------------------------
        UPLOAD_DIR = os.path.join("uploads", course_code)
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        TRACK_FILE = os.path.join(UPLOAD_DIR, "submission_tracker.csv")
        if os.path.exists(TRACK_FILE):
            tracker_df = pd.read_csv(TRACK_FILE)
        else:
            tracker_df = pd.DataFrame(columns=["StudentName", "MatricNo", "Week", "Assignment", "Drawing", "Seminar"])

# -----------------------------
# Student Info
# -----------------------------
        student_name = st.text_input("Full Name", key=f"{course_code}_name_input")
        matric_no = st.text_input("Matric Number", key=f"{course_code}_matric_input")
        selected_week = st.selectbox("Select Week", weeks, key=f"{course_code}_week_select")

        if student_name and matric_no:
    # Check if student-week exists
            existing = tracker_df[
                (tracker_df["StudentName"] == student_name) &
                (tracker_df["MatricNo"] == matric_no) &
                (tracker_df["Week"] == selected_week)
    ]
            if existing.empty:
                student_row = len(tracker_df)
                tracker_df.loc[student_row] = [student_name, matric_no, selected_week, "", "", ""]
            else:
                student_row = existing.index[0]

    # -----------------------------
    # Submission types
    # -----------------------------
            submission_info = {
                "Assignment": ["pdf", "docx", "jpg", "png"],
                "Drawing": ["pdf", "jpg", "png"],
                "Seminar": ["pdf", "pptx", "docx"]
    }

            for sub_type, allowed_types in submission_info.items():
                submitted_file = tracker_df.at[student_row, sub_type]
                key_suffix = f"{sub_type}_{matric_no}_{selected_week}"

                if submitted_file:
                    st.warning(f"You have already submitted your **{sub_type}** for {selected_week}.")
                else:
                    uploaded_file = st.file_uploader(f"Upload {sub_type}", type=allowed_types, key=key_suffix)
                    if uploaded_file:
                # Save file
                        extension = uploaded_file.name.split('.')[-1]
                        filename = f"{student_name}_{matric_no}_{selected_week}_{sub_type}.{extension}"
                        file_path = os.path.join(UPLOAD_DIR, filename)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                # Update tracker CSV
                        tracker_df.at[student_row, sub_type] = filename
                        tracker_df.to_csv(TRACK_FILE, index=False)

                # Optional: call existing logging function if available
                        if "log_submission" in globals():
                            log_submission(course_code, matric_no, student_name, selected_week, uploaded_file.name, sub_type)

                        st.success(f"✅ {sub_type} uploaded successfully!")


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



#--- Fixed & hardened admin_view function ---
def admin_view():
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
        st.success(f"✅ Logged in as Admin for {course_code}")

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

    # File uploader
        files = st.file_uploader("Upload files", accept_multiple_files=True)

# Check if any files were uploaded
        if not files:
            st.info("No files uploaded yet.")
        else:
            st.success(f"{len(files)} file(s) ready to be processed!")

    # -------------------------
    # Add / Edit Lecture, Classwork & Assignment
    # -------------------------
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

        # Input fields
            topic = st.text_input("Lecture Topic", value=topic_default)
            brief = st.text_area("Lecture Brief", value=brief_default)
            classwork = st.text_area("Classwork (separate questions with ;)", value=classwork_default)
            assignment = st.text_area("Assignment (separate questions with ;)", value=assignment_default)

        # PDF uploads
            st.markdown("**Upload PDF Files (Optional)**")
            lecture_pdf = st.file_uploader("Lecture PDF", type=["pdf"])
            classwork_pdf = st.file_uploader("Classwork PDF", type=["pdf"])
            assignment_pdf = st.file_uploader("Assignment PDF", type=["pdf"])

        # Save lecture & uploads
            if st.button(f"💾 Save Lecture / Classwork / Assignment ({week})", key=f"save_{week}"):
                lectures_df.loc[row_idx, ["Topic", "Brief", "Classwork", "Assignment"]] = [topic, brief, classwork, assignment]

    # Ensure the parent directory exists
                if os.path.dirname(LECTURE_FILE):
                    os.makedirs(os.path.dirname(LECTURE_FILE), exist_ok=True)


    # Save the CSV
            lectures_df.to_csv(LECTURE_FILE, index=False)

            st.session_state["lectures_df"] = lectures_df
            st.success(f"✅ Lecture, Classwork, and Assignment for {week} saved!")


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
    # Student Records (Attendance / Classwork / Seminar)
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
                    df = pd.read_csv(file)
                    st.dataframe(df, use_container_width=True)
                    st.download_button(
                    label=f"⬇️ Download {label} CSV",
                    data=df.to_csv(index=False).encode(),
                    file_name=os.path.basename(file),
                    mime="text/csv",
                    key=f"{label}_download"
            )
                else:
                    st.info(f"No {label.lower()} yet.")

    # -------------------------
    # View & Grade Uploaded Files (assignment/drawing/seminar)
    # -------------------------
                st.divider()
                st.subheader("📂 View Student Submissions & Grade Them")
                with st.expander("Expand to view and grade student submissions", expanded=True):
                    upload_types = ["assignment", "drawing", "seminar"]
                    for upload_type in upload_types:
                    st.markdown(f"### 📄 {upload_type.capitalize()} Uploads")
                    upload_dir = os.path.join(base_dir, course_code, upload_type)
                    if os.path.exists(upload_dir):
                        files = sorted([
                        f for f in os.listdir(upload_dir)
                        if os.path.isfile(os.path.join(upload_dir, f))
            ])
                        if not files:
                            st.info(f"No {upload_type} uploaded yet.")
                    else:
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

                                score = st.number_input(
                                    f"Enter score for {file}",
                                    min_value=0,
                                    max_value=100,
                                    key=f"{unique_key}_score"
                    )

                            if st.button(f"💾 Save Score ({file})", key=f"{unique_key}_save"):
                        # Parse filename format: Name_Matric_Week.ext
                                parts = file.rsplit(".", 1)[0].split("_")
                                student_name = parts[0].strip().title() if len(parts) > 0 else "Unknown"
                                matric = parts[1].strip().upper() if len(parts) > 1 else "Unknown"
                                week = parts[2].strip().title() if len(parts) > 2 else "Unknown"

                        # Score file path
                                score_file = os.path.join(scores_dir, f"{course_code.lower()}_scores.csv")
                        # Load or create scores DataFrame safely
                                score_file = os.path.join("scores", f"{course_code.lower()}_scores.csv")
                                required_columns = ["StudentName", "MatricNo", "Week", "ClassworkScore", "SeminarScore", "AssignmentScore", "TotalScore"]

                                if os.path.exists(score_file):
                                    df = pd.read_csv(score_file)
                            # Add missing columns if any
                                    for col in required_columns:
                                        if col not in df.columns:
                                            df[col] = 0 if "Score" in col else ""
                                else:
    # Create empty DataFrame with required columns
                                    df = pd.DataFrame(columns=required_columns)

                        # parse filename expected: Name_Matric_Week.ext
                                    parts = file.rsplit(".", 1)[0].split("_")

# Validate filename format
                                if len(parts) < 3:
                                    st.warning(f"Invalid filename format: {file}. Use Name_Matric_Week.ext")
                                continue  # Skip this file if format is wrong

# Extract student info
                                student_name = parts[0].strip().title()
                                matric = parts[1].strip().upper()
                                week = parts[2].strip().title()

# Map upload type to column
                                column_map = {"assignment": "AssignmentScore", "drawing": "ClassworkScore", "seminar": "SeminarScore"}
                                col = column_map.get(upload_type, "AssignmentScore")

                        # Locate existing record
                                existing_idx = df[
                                    (df["StudentName"].astype(str).str.lower() == student_name.lower()) &
                                    (df["MatricNo"].astype(str).str.lower() == matric.lower()) &
                                    (df["Week"].astype(str).str.lower() == week.lower())
                                    ].index

                                column_map = {
                                    "assignment": "AssignmentScore",
                                    "drawing": "ClassworkScore",
                                    "seminar": "SeminarScore"
                        }
                                col = column_map.get(upload_type, "AssignmentScore")

                                if len(existing_idx) > 0:
                                    df.loc[existing_idx, col] = score
                                else:
                                    new_row = {
                                        "StudentName": student_name,
                                        "MatricNo": matric,
                                        "Week": week,
                                        "ClassworkScore": 0,
                                        "SeminarScore": 0,
                                        "AssignmentScore": 0,
                                        "TotalScore": 0
                            }
                                    new_row[col] = score
                                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

                        # Compute total weighted score
                                    df["TotalScore"] = (
                                        df.get("ClassworkScore", 0).fillna(0).astype(float) * 0.3 +
                                        df.get("SeminarScore", 0).fillna(0).astype(float) * 0.2 +
                                        df.get("AssignmentScore", 0).fillna(0).astype(float) * 0.5
                                    ).round(1)

                            try:
                                df.to_csv(score_file, index=False)
                                st.success(f"✅ Score saved for {student_name} ({matric}) - {week}")
                            except Exception as e:
                                st.error(f"❌ Failed to save score file: {e}")
            else:
                st.info(f"No directory found for {upload_type}.")

    # -------------------------
    # Live Score Review / Manual Entry
    # -------------------------
       # ===============================================================
# 📄 ADMIN DASHBOARD — MANAGE & REVIEW SCORES
# ===============================================================
        st.divider()
        with st.expander("🧭 ADMIN DASHBOARD — Manage and Review Scores", expanded=True):
            st.header("📊 Review Graded Scores")

            review_paths = [
            os.path.join("student_uploads", f"{course_code}_scores.csv"),
            os.path.join("scores", f"{course_code.lower()}_scores.csv")
    ]

            scores_df = None
            for p in review_paths:
                if os.path.exists(p):
                    try:
                        scores_df = pd.read_csv(p)
                        break
                    except Exception:
                    continue

                if scores_df is None or scores_df.empty:
                    st.info("No graded scores yet. Once you grade a file, it will appear here.")
                else:
                    col1, col2 = st.columns(2)

                    with col1:
                    type_values = ["All"] + (
                sorted(scores_df["Type"].dropna().unique().tolist())
                if "Type" in scores_df.columns else []
            )
            type_filter = st.selectbox(
                "Filter by Upload Type",
                type_values,
                key=f"{course_code}_type_filter"
            )

        with col2:
            sort_order = st.radio(
                "Sort by Date",
                ["Newest First", "Oldest First"],
                key=f"{course_code}_sort_order"
            )

        filtered_df = scores_df.copy()
        if type_filter != "All" and "Type" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Type"] == type_filter]

        if "Date Graded" in filtered_df.columns:
            filtered_df = filtered_df.sort_values(
                "Date Graded", ascending=(sort_order == "Oldest First")
            )

        st.dataframe(filtered_df, use_container_width=True)
        st.download_button(
            label="⬇️ Download All Scores (CSV)",
            data=filtered_df.to_csv(index=False).encode(),
            file_name=f"{course_code}_graded_scores.csv",
            mime="text/csv",
            key=f"{course_code}_graded_scores_download"
        )


# ===============================================================
# 🧮 MANUAL SCORE ENTRY
# ===============================================================
        st.divider()
st.header("🧮 Manual Score Entry & Review")

# ✅ Ensure lectures_df is defined before using it
if "lectures_df" not in st.session_state:
    if os.path.exists(LECTURE_FILE):
        lectures_df = pd.read_csv(LECTURE_FILE)
        st.session_state["lectures_df"] = lectures_df
    else:
        # Create a default empty DataFrame if file doesn't exist
        lectures_df = pd.DataFrame(columns=["Week", "Topic", "Brief", "Classwork", "Assignment"])
        st.session_state["lectures_df"] = lectures_df
else:
    lectures_df = st.session_state["lectures_df"]

# 🧾 Input fields
name = st.text_input("Student Name", key="manual_name")
matric = st.text_input("Matric Number", key="manual_matric")

# ✅ Select week from lectures_df or fallback to “Week 1”
week = st.selectbox(
    "Select Week",
    lectures_df["Week"].tolist() if not lectures_df.empty else ["Week 1"],
    key="manual_week"
)

score = st.number_input("Enter Score (0–100)", 0, 100, 0, key="manual_score")
remarks = st.text_input("Remarks (optional)", key="manual_remarks")
score_type = st.radio(
    "Select Assessment Type",
    ["classwork", "seminar", "assignment"],
    key="manual_type"
)

# 💾 Save or update score
if st.button("💾 Save / Update Score", key="save_manual_score"):
    if not name or not matric:
        st.warning("Please enter student name and matric number.")
    else:
        try:
            if "record_score" in globals() and callable(record_score):
                record_score(course_code, score_type, name, matric, week, score, remarks)
            else:
                # Fallback: save directly to scores CSV
                scores_dir = "scores"
                os.makedirs(scores_dir, exist_ok=True)
                score_file = os.path.join(scores_dir, f"{course_code.lower()}_scores.csv")

                if os.path.exists(score_file):
                    df = pd.read_csv(score_file)
                else:
                    df = pd.DataFrame(columns=[
                        "StudentName", "MatricNo", "Week",
                        "ClassworkScore", "SeminarScore",
                        "AssignmentScore", "TotalScore"
                    ])

                # Find matching record
                mask = (
                    (df["StudentName"].astype(str).str.lower() == name.lower()) &
                    (df["MatricNo"].astype(str).str.lower() == matric.lower()) &
                    (df["Week"].astype(str).str.lower() == week.lower())
                )

                # Update or create new record
                if mask.any():
                    if score_type == "classwork":
                        df.loc[mask, "ClassworkScore"] = score
                    elif score_type == "seminar":
                        df.loc[mask, "SeminarScore"] = score
                    else:
                        df.loc[mask, "AssignmentScore"] = score
                else:
                    new_row = {
                        "StudentName": name.title(),
                        "MatricNo": matric.upper(),
                        "Week": week,
                        "ClassworkScore": 0,
                        "SeminarScore": 0,
                        "AssignmentScore": 0,
                        "TotalScore": 0
                    }
                    if score_type == "classwork":
                        new_row["ClassworkScore"] = score
                    elif score_type == "seminar":
                        new_row["SeminarScore"] = score
                    else:
                        new_row["AssignmentScore"] = score
                    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

                # Compute total score
                df["TotalScore"] = (
                    df.get("ClassworkScore", 0).fillna(0).astype(float) * 0.3 +
                    df.get("SeminarScore", 0).fillna(0).astype(float) * 0.2 +
                    df.get("AssignmentScore", 0).fillna(0).astype(float) * 0.5
                ).round(1)

                df.to_csv(score_file, index=False)

            st.cache_data.clear()
            st.success("✅ Score recorded successfully!")
        except Exception as e:
            st.error(f"Failed to record manual score: {e}")


# ===============================================================
# 📝 STUDENT GRADING SECTION
# ===============================================================
        st.header("📝 Grade Students for Session")

        score_dir = "scores"
        os.makedirs(score_dir, exist_ok=True)
        score_file = os.path.join(score_dir, f"{course_code.lower()}_scores.csv")

        columns = ["StudentName", "MatricNo", "Attendance", "Classwork", "Test", "Practical", "Exam", "TotalScore"]

        if os.path.exists(score_file):
            df = pd.read_csv(score_file)
            for col in columns:
                if col not in df.columns:
                    df[col] = 0
        else:
            df = pd.DataFrame(columns=columns)

        for idx, row in df.iterrows():
            st.markdown(f"### {row.get('StudentName', 'Unknown')} ({row.get('MatricNo', 'Unknown')})")
            attendance = st.number_input("Attendance (out of 5)", 0, 5, int(row.get("Attendance", 0)), key=f"{idx}_att")
            classwork = st.number_input("Classwork (out of 10)", 0, 10, int(row.get("Classwork", 0)), key=f"{idx}_cw")
            test = st.number_input("Test (out of 10)", 0, 10, int(row.get("Test", 0)), key=f"{idx}_test")
            practical = st.number_input("Practical (out of 5)", 0, 5, int(row.get("Practical", 0)), key=f"{idx}_prac")
            exam = st.number_input("Exam (out of 70)", 0, 70, int(row.get("Exam", 0)), key=f"{idx}_exam")

            df.at[idx, "Attendance"] = attendance
            df.at[idx, "Classwork"] = classwork
            df.at[idx, "Test"] = test
            df.at[idx, "Practical"] = practical
            df.at[idx, "Exam"] = exam
            df.at[idx, "TotalScore"] = attendance + classwork + test + practical + exam

        if st.button("💾 Save All Student Scores"):
            df.to_csv(score_file, index=False)
            st.success("✅ All scores saved successfully!")

        st.dataframe(df, use_container_width=True)


    # -------------------------
    # Review Student Scores (filtered)
    # -------------------------
    st.divider()
    st.header("📊 Review Student Scores")
    score_file_candidates = [
        os.path.join("scores", f"{course_code.lower()}_scores.csv"),
        os.path.join("student_uploads", f"{course_code}_scores.csv"),
        (get_file(course_code, "scores") if "get_file" in globals() and callable(get_file) else None)
    ]
    score_file = next((p for p in score_file_candidates if p and os.path.exists(p)), None)

    if score_file:
        try:
            scores_df = pd.read_csv(score_file)
            col1, col2 = st.columns(2)
            with col1:
                week_filter = st.selectbox("Filter by Week", ["All"] + sorted(scores_df["Week"].dropna().unique().tolist()) if "Week" in scores_df.columns else ["All"])
            with col2:
                type_filter = st.selectbox("Filter by Assessment Type", ["All"] + sorted(scores_df["Type"].dropna().unique().tolist()) if "Type" in scores_df.columns else ["All"])
            filtered_df = scores_df.copy()
            if week_filter != "All" and "Week" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Week"] == week_filter]
            if type_filter != "All" and "Type" in filtered_df.columns:
                filtered_df = filtered_df[filtered_df["Type"] == type_filter]
            st.dataframe(filtered_df, use_container_width=True)
            st.download_button("⬇️ Download Filtered Scores", filtered_df.to_csv(index=False).encode(), file_name=f"{course_code}_filtered_scores.csv")
        except Exception as e:
            st.error(f"Error reading scores file: {e}")
    else:
        st.info("🔒 No scores recorded yet.")

    # -------------------------
    # Video upload & management
    # -------------------------
    st.divider()
    st.subheader("🎥 Upload & Manage Video Lectures")
    video_dir = os.path.join("video_lectures", course_code)
    os.makedirs(video_dir, exist_ok=True)
    uploaded_video = st.file_uploader("Upload Lecture Video (MP4 only)", type=["mp4"], key=f"{course_code}_video_upload")
    if uploaded_video is not None:
        try:
            save_path = os.path.join(video_dir, uploaded_video.name)
            with open(save_path, "wb") as f:
                f.write(uploaded_video.read())
            st.success(f"✅ Video uploaded successfully: {uploaded_video.name}")
        except Exception as e:
            st.error(f"Failed to save uploaded video: {e}")

    # list existing videos
    video_files = sorted(os.listdir(video_dir)) if os.path.exists(video_dir) else []
    if video_files:
        st.markdown("### 📚 Uploaded Lecture Videos")
        for video in video_files:
            video_path = os.path.join(video_dir, video)
            try:
                st.video(video_path)
                with open(video_path, "rb") as vid_file:
                    st.download_button(label=f"⬇️ Download {video}", data=vid_file.read(), file_name=video, mime="video/mp4", key=f"{video}_download")
            except Exception:
                st.info(f"Cannot preview or download {video}.")
    else:
        st.info("No videos uploaded yet.")

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


# 🚪 SHOW VIEW BASED ON ROLE
# ===============================================================
if st.session_state["role"] == "Admin":
    admin_view()
elif st.session_state["role"] == "Student":
    student_view()
else:
    st.warning("Please select your role from the sidebar to continue.")












































