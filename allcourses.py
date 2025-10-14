import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, date, timedelta, time
from streamlit_autorefresh import st_autorefresh
import zipfile
import io

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

# ===============================================================
# 📁 HELPER FUNCTION
# ===============================================================
def get_file(course_code, filetype):
    """Return the file path for a given course and file type."""
    filename = f"{course_code}_{filetype}.csv"
    return os.path.join(LOG_DIR, filename)

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


# -----------------------------

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
        
UPLOADS_DIR = "student_uploads"  # Adjust if you already defined elsewhere
os.makedirs(UPLOADS_DIR, exist_ok=True)

def save_file(course_code, student_name, week, uploaded_file, folder_name):
    """Save uploaded file to the appropriate course and folder."""
    upload_dir = os.path.join(UPLOADS_DIR, course_code, folder_name)
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = student_name.replace(" ", "_")
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



# -----------------------------
# STUDENT MODE
# -----------------------------
def student_view():
    if st.session_state.get("role") == "Student":
        st.title("🎓 Student Dashboard")
        st.info("Welcome, Student! Access your lectures, upload assignments, and mark attendance here.")
        st.subheader("🎓 Student Login and Attendance")

    # Initialize safe variables
    submit_attendance = False
    ok = False

    with st.form(f"{course_code}_attendance_form"):
        name = st.text_input("Full Name", key=f"{course_code}_student_name")
        matric = st.text_input("Matric Number", key=f"{course_code}_student_matric")
        week = st.selectbox("Select Lecture Week", lectures_df["Week"].tolist(), key=f"{course_code}_week")
        attendance_code = st.text_input("Enter Attendance Code (Ask your lecturer)", key=f"{course_code}_att_code")
        submit_attendance = st.form_submit_button("✅ Mark Attendance")

    if submit_attendance:
        if not name.strip() or not matric.strip():
            st.warning("Please enter your full name and matric number.")
        elif not attendance_code.strip():
            st.warning("Please enter the attendance code for today.")
        else:
            COURSE_TIMINGS = {
                "BIO203": {"valid_code": "BIO203-ZT7", "start": "10:00", "end": "14:00"},
                "BCH201": {"valid_code": "BCH201-ZT8", "start": "14:00", "end": "16:00"},
                "MCB221": {"valid_code": "MCB221-ZT9", "start": "10:00", "end": "10:20"},
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
                    st.session_state["attended_week"] = week  # Grant access if already marked
                else:
                    ok = mark_attendance_entry(course_code, name, matric, week)
                    if ok:
                        st.success(f"✅ Attendance recorded for {name} ({week}).")
                        st.session_state["attended_week"] = week
                        st.experimental_rerun()  # 🔄 Auto-refresh to show lecture immediately

    # ---------------------------------------------
    # 📘 Lecture Briefs and Classwork
    # ---------------------------------------------
    st.divider()
    st.subheader("📘 Lecture Briefs and Classwork")
    st.markdown("Here you can view lecture summaries, slides, and classwork materials.")

    lecture_row = pd.DataFrame()  # Safe default

    if "attended_week" in st.session_state and not lectures_df.empty:
        week = st.session_state["attended_week"]
        st.success(f"Access granted for {week}")
        lecture_row = lectures_df[lectures_df["Week"] == week]
    else:
        st.warning("No lecture selected or attendance not recorded yet.")

    if not lecture_row.empty:
        lecture_info = lecture_row.iloc[0]
        st.divider()
        st.subheader(f"📖 {lecture_info.get('Week', 'Lecture')}: {lecture_info.get('Topic', 'No topic available')}")

        # 🧾 Lecture Brief
        brief = str(lecture_info.get("Brief", "")).strip() if pd.notnull(lecture_info.get("Brief", "")) else ""
        if brief:
            st.markdown(f"**Lecture Brief:** {brief}")
        else:
            st.info("Lecture brief not available yet.")

        # 🧩 Classwork Section
        classwork_text = str(lecture_info.get("Classwork", "")).strip() if pd.notnull(lecture_info.get("Classwork", "")) else ""
        if classwork_text:
            st.markdown("### 🧩 Classwork Questions")
            questions = [q.strip() for q in classwork_text.split(";") if q.strip()]
            with st.form("cw_form"):
                answers = [st.text_input(f"Q{i+1}: {q}") for i, q in enumerate(questions)]
                submit_cw = st.form_submit_button("Submit Answers", disabled=not is_classwork_open(course_code, week))
                if submit_cw:
                    save_classwork(name, matric, week, answers)
                    st.success("✅ Classwork submitted successfully.")
        else:
            st.info("Classwork not yet released.")

        # 📝 Assignment Section
        assignment = str(lecture_info.get("Assignment", "")).strip() if pd.notnull(lecture_info.get("Assignment", "")) else ""
        if assignment:
            st.subheader("📚 Assignment")
            st.markdown(f"**Assignment:** {assignment}")
        else:
            st.info("Assignment not released yet.")

        # 📥 Lecture PDF Section
        pdf_path = os.path.join(MODULES_DIR, f"{course_code}_{lecture_info.get('Week', '').replace(' ', '_')}.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
                st.download_button(
                    label=f"📥 Download {lecture_info.get('Week', 'Lecture')} Module PDF",
                    data=pdf_bytes,
                    file_name=f"{course_code}_{lecture_info.get('Week', 'Lecture')}.pdf",
                    mime="application/pdf"
            )
        else:
                st.info("Lecture note not uploaded yet.")


    # ---------------------------------------------
    # 📈 Student Continuous Assessment (CA) Summary
    # ---------------------------------------------
    st.divider()
    st.subheader("📈 Your Continuous Assessment (CA) Summary")

    scores_file = os.path.join("scores", f"{course_code.lower()}_scores.csv")
    if os.path.exists(scores_file):
        df_scores = pd.read_csv(scores_file)
        if 'name' in locals() and 'matric' in locals() and name.strip() and matric.strip():
            student_scores = df_scores[
                (df_scores["StudentName"].str.lower() == name.strip().lower()) &
                (df_scores["MatricNo"].str.lower() == matric.strip().lower())
            ] if ("StudentName" in df_scores.columns and "MatricNo" in df_scores.columns) else pd.DataFrame()

            if not student_scores.empty:
                cw_total = student_scores["ClassworkScore"].mean() if "ClassworkScore" in student_scores else 0
                sem_total = student_scores["SeminarScore"].mean() if "SeminarScore" in student_scores else 0
                ass_total = student_scores["AssignmentScore"].mean() if "AssignmentScore" in student_scores else 0
                total_CA = (cw_total * 0.3) + (sem_total * 0.2) + (ass_total * 0.5)

                st.dataframe(
                    student_scores[[col for col in ["Week", "ClassworkScore", "SeminarScore", "AssignmentScore", "TotalScore"] if col in student_scores.columns]],
                    use_container_width=True
                )

                st.markdown(f"""
                    <div style='background-color:#f0f9ff;padding:15px;border-radius:10px;margin-top:10px;'>
                        <h4>📘 <b>Performance Summary</b></h4>
                        <ul>
                            <li>🧩 Classwork Avg: <b>{cw_total:.1f}%</b> (30%)</li>
                            <li>🎤 Seminar Avg: <b>{sem_total:.1f}%</b> (20%)</li>
                            <li>📝 Assignment Avg: <b>{ass_total:.1f}%</b> (50%)</li>
                        </ul>
                        <h3>💯 Total Continuous Assessment (CA): <b>{total_CA:.1f}%</b></h3>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No scores found yet. Participate in classwork, seminar, or assignments.")
        else:
            st.info("Enter your name & matric above to see your CA summary (if available).")
    else:
        st.warning("📁 Scores file not yet available for this course.")

# ===============================================================
# 📄 ASSIGNMENT, DRAWING & SEMINAR UPLOADS (STUDENT SECTION)
# ===============================================================
if st.session_state.get("role") == "Student":

    st.divider()
    st.subheader("📄 Assignment, Drawing & Seminar Uploads")

    # =======================
    # ASSIGNMENT UPLOAD
    # =======================
    st.divider()
    st.subheader("📝 Assignment Upload")

    selected_week_a = st.selectbox(
        "Select Week for Assignment",
        lectures_df["Week"].tolist(),
        key="assignment_week_select"
    )
    matric_a = st.text_input("Matric Number", key="matric_a")
    student_name_a = st.text_input("Full Name", key="student_name_a")
    uploaded_assignment = st.file_uploader(
        f"Upload Assignment for {selected_week_a}",
        type=["pdf", "docx", "jpg", "png"],
        key=f"{course_code}_assignment"
    )

    if st.button(f"📤 Submit Assignment for {selected_week_a}", key="submit_assignment_btn"):
        if not matric_a or not student_name_a:
            st.warning("Please enter your name and matric number before submitting.")
        elif not uploaded_assignment:
            st.warning("Please upload your assignment file before submitting.")
        else:
            file_path = save_file(course_code, student_name_a, selected_week_a, uploaded_assignment, "assignment")
            log_submission(course_code, matric_a, student_name_a, selected_week_a, uploaded_assignment.name, "Assignment")
            st.success(f"✅ {student_name_a} ({matric_a}) — Assignment uploaded successfully!")

    # =======================
    # DRAWING UPLOAD
    # =======================
    st.divider()
    st.subheader("🎨 Drawing Upload")

    selected_week_d = st.selectbox("Select Week for Drawing", lectures_df["Week"].tolist(), key="drawing_week_select")
    matric_d = st.text_input("Matric Number", key="matric_d")
    student_name_d = st.text_input("Full Name", key="student_name_d")
    uploaded_drawing = st.file_uploader(
        f"Upload Drawing for {selected_week_d}",
        type=["pdf", "jpg", "png"],
        key=f"{course_code}_drawing"
    )

    if st.button(f"📤 Submit Drawing for {selected_week_d}", key="submit_drawing_btn"):
        if not matric_d or not student_name_d:
            st.warning("Please enter your name and matric number before submitting.")
        elif not uploaded_drawing:
            st.warning("Please upload your drawing file before submitting.")
        else:
            file_path = save_file(course_code, student_name_d, selected_week_d, uploaded_drawing, "drawing")
            log_submission(course_code, matric_d, student_name_d, selected_week_d, uploaded_drawing.name, "Drawing")
            st.success(f"✅ {student_name_d} ({matric_d}) — Drawing uploaded successfully!")

    # =======================
    # SEMINAR UPLOAD
    # =======================
    st.divider()
    st.subheader("🎤 Seminar Upload")

    selected_week_s = st.selectbox("Select Week for Seminar", lectures_df["Week"].tolist(), key="seminar_week_select")
    matric_s = st.text_input("Matric Number", key="matric_s")
    student_name_s = st.text_input("Full Name", key="student_name_s")
    uploaded_seminar = st.file_uploader(
        f"Upload Seminar File for {selected_week_s}",
        type=["pdf", "pptx", "docx"],
        key=f"{course_code}_seminar"
    )

    if st.button(f"📤 Submit Seminar for {selected_week_s}", key="submit_seminar_btn"):
        if not matric_s or not student_name_s:
            st.warning("Please enter your name and matric number before submitting.")
        elif not uploaded_seminar:
            st.warning("Please upload your seminar file before submitting.")
        else:
            file_path = save_file(course_code, student_name_s, selected_week_s, uploaded_seminar, "seminar")
            log_submission(course_code, matric_s, student_name_s, selected_week_s, uploaded_seminar.name, "Seminar")
            st.success(f"✅ {student_name_s} ({matric_s}) — Seminar uploaded successfully!")


# ---------------------------------------------------------
# 🎓 STUDENT SECTION: Watch Lecture Videos
# ---------------------------------------------------------
    st.divider()
    st.subheader("🎬 Watch Lecture Videos")

    video_dir = os.path.join("video_lectures", course_code)
    if os.path.exists(video_dir):
        video_files = sorted(os.listdir(video_dir))
        if video_files:
            selected_video = st.selectbox("Select a lecture to watch:", video_files)
            video_path = os.path.join(video_dir, selected_video)
            st.video(video_path)
        else:
            st.info("No lecture videos have been uploaded yet.")
    else:
        st.warning("📁 No video directory found for this course.")



def admin_view():
    if st.session_state.get("role") != "Admin":
        return  # Only proceed if Admin

    st.title("👩‍🏫 Admin Dashboard")
    st.success("Welcome, Admin! Manage lectures, attendance, and student uploads here.")
    st.subheader("🔐 Teacher / Admin Panel")

    ADMIN_PASS = "bimpe2025class"
    password = st.text_input("Enter Admin Password", type="password")

    if password != ADMIN_PASS:
        st.warning("Enter the correct admin password to continue.")
        return

    st.session_state["role"] = "Admin"
    st.success(f"✅ Logged in as Admin for {course_code}")
    
        # -------------------------------------
        # 📚 LECTURE MANAGEMENT
        # -------------------------------------
    st.header("📚 Lecture Management")
    lecture_to_edit = st.selectbox("Select Lecture", lectures_df["Week"].unique(), key="admin_select_lecture")
    row_idx = lectures_df[lectures_df["Week"] == lecture_to_edit].index[0]
    brief = st.text_area("Lecture Brief", value=lectures_df.at[row_idx, "Brief"], key="admin_brief")
    assignment = st.text_area("Assignment", value=lectures_df.at[row_idx, "Assignment"], key="admin_assignment")
    classwork = st.text_area("Classwork (Separate questions with ;)", 
    value=lectures_df.at[row_idx, "Classwork"], key="admin_classwork")

    if st.button("💾 Update Lecture", key="admin_update_lecture"):
        lectures_df.at[row_idx, "Brief"] = brief
        lectures_df.at[row_idx, "Assignment"] = assignment
        lectures_df.at[row_idx, "Classwork"] = classwork
        lectures_df.to_csv(get_file(course_code, "lectures"), index=False)
        st.success(f"{lecture_to_edit} updated successfully!")

       # -------------------------------------
# 📄 UPLOAD LECTURE PDF MODULE
# -------------------------------------
    st.header("📄 Upload Lecture PDF Module")
    pdf_file = st.file_uploader("Upload Lecture Module", type=["pdf"], key="admin_pdf_upload")

    if pdf_file:
        pdf_path = os.path.join(MODULES_DIR, f"{course_code}_{lecture_to_edit.replace(' ', '_')}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(pdf_file.getbuffer())
        st.success(f"✅ PDF uploaded for {lecture_to_edit}")

# -------------------------------------
# 🧩 CLASSWORK CONTROL
# -------------------------------------
    st.header("🧩 Classwork Control")
    week_to_control = st.selectbox("Select Week to Open/Close Classwork", lectures_df["Week"].unique(), key="admin_cw_control")

    if st.button(f"📖 Open Classwork for {week_to_control} (20 mins)", key="admin_open_cw"):
        open_classwork(course_code, week_to_control)
        st.success(f"✅ Classwork for {week_to_control} is now open for 20 minutes.")

    close_classwork_after_20min(course_code)

# -------------------------------------
# 📋 STUDENT RECORDS
# -------------------------------------
    st.header("📋 Student Records")

    base_dir = "student_uploads"
    records = {
        "Attendance Records": os.path.join(base_dir, f"{course_code}_attendance.csv"),
        "Classwork Submissions": os.path.join(base_dir, f"{course_code}_classwork.csv"),
        "Seminar Submissions": os.path.join(base_dir, f"{course_code}_seminar.csv")
}

    for label, file_path in records.items():
        st.divider()
        st.markdown(f"### {label}")

        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)
                if not df.empty:
                    st.dataframe(df, use_container_width=True)
                    st.download_button(
                        label=f"⬇️ Download {label}",
                        data=df.to_csv(index=False).encode("utf-8"),
                        file_name=os.path.basename(file_path),
                        mime="text/csv"
                )
                else:
                    st.info(f"{label} file is empty.")
            except Exception as e:
                st.error(f"⚠️ Error reading {label}: {e}")
        else:
            st.info(f"No {label.lower()} yet.")

# ===============================================================
# 🧑‍🏫 ADMIN SECTION — VIEW & MANAGE STUDENT SUBMISSIONS
# ===============================================================
    if st.session_state.get("role") == "Admin":
        st.divider()
        st.subheader("🗂️ Manage Student Submissions")

    # Automatically refresh submissions every 30 seconds
        st_autorefresh(interval=30 * 1000, key="auto_refresh")

    # Define the path to the submissions log
        log_file = f"submissions_{course_code}.csv"

        if os.path.exists(log_file):
            submissions_df = pd.read_csv(log_file)

            st.success(f"📦 Total Submissions: {len(submissions_df)}")
            selected_type = st.selectbox("Filter by Submission Type", ["All", "Assignment", "Drawing", "Seminar"])

        # Filter data
            if selected_type != "All":
                submissions_df = submissions_df[submissions_df["Submission Type"] == selected_type]

        # Display submissions
            st.dataframe(submissions_df)

        # Download option
            csv = submissions_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Submissions CSV", csv, file_name=f"{course_code}_submissions.csv")

        # Option to view or delete
            st.divider()
            st.subheader("🧾 Manage Files")

            selected_week = st.selectbox("Select Week to View Files", submissions_df["Week"].unique())
            selected_week_files = submissions_df[submissions_df["Week"] == selected_week]

            for idx, row in selected_week_files.iterrows():
                st.write(f"📘 **{row['Student Name']} ({row['Matric Number']})** — {row['Submission Type']}")
                file_path = os.path.join("uploads", course_code, row["Week"], row["File Name"])
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        st.download_button(f"⬇️ Download {row['File Name']}", f, file_name=row["File Name"], key=f"dl_{idx}")
                else:
                    st.info("No submissions found yet for this course.")
    
# ---------------------------------------------------------
# 🧑‍🏫 ADMIN DASHBOARD: View + Grade + Review Scores
# ---------------------------------------------------------
    if st.session_state.get("role") == "admin":
        st.subheader("📂 View Student Submissions & Grade Them")

        upload_types = ["assignment", "drawing", "seminar"]
        base_dir = "student_uploads"
        scores_dir = "scores"
        os.makedirs(scores_dir, exist_ok=True)

        for upload_type in upload_types:
            st.markdown(f"### 📄 {upload_type.capitalize()} Uploads")

            upload_dir = os.path.join(base_dir, course_code, upload_type)
        if os.path.exists(upload_dir):
            files = sorted(os.listdir(upload_dir))
            if files:
                for file in files:
                    file_path = os.path.join(upload_dir, file)
                    unique_key = f"{course_code}_{upload_type}_{file}"

                    st.write(f"📎 {file}")

                    # ✅ Download button
                    with open(file_path, "rb") as f:
                        st.download_button(
                            label=f"⬇️ Download {file}",
                            data=f,
                            file_name=file,
                            mime="application/octet-stream",
                            key=f"{unique_key}_download"
                        )

                    # ✅ Enter score
                    score = st.number_input(
                        f"Enter score for {file}",
                        0, 100,
                        key=f"{unique_key}_score"
                    )

                    # ✅ Save button
                    if st.button(f"💾 Save Score ({file})", key=f"{unique_key}_save"):
                        # --- Extract name, matric, and week from file name ---
                        # Expect filename pattern: Name_Matric_Week.extension
                        parts = file.split("_")
                        student_name = parts[0].strip().title() if len(parts) > 0 else "Unknown"
                        matric = parts[1].strip().upper() if len(parts) > 1 else "Unknown"
                        week = parts[2].split(".")[0].strip().title() if len(parts) > 2 else "Unknown"

                        score_file = os.path.join(scores_dir, f"{course_code.lower()}_scores.csv")

                        # --- Load or create dataframe ---
                        if os.path.exists(score_file):
                            df = pd.read_csv(score_file)
                        else:
                            df = pd.DataFrame(columns=[
                                "StudentName", "MatricNo", "Week",
                                "ClassworkScore", "SeminarScore", "AssignmentScore", "TotalScore"
                            ])

                        # --- Normalize headers ---
                        df.columns = df.columns.str.strip().str.title()

                        # --- Check if student-week entry exists ---
                        existing_idx = df[
                            (df["StudentName"].str.lower() == student_name.lower()) &
                            (df["MatricNo"].str.lower() == matric.lower()) &
                            (df["Week"].str.lower() == week.lower())
                        ].index

                        # --- Update appropriate column ---
                        column_map = {
                            "assignment": "AssignmentScore",
                            "drawing": "ClassworkScore",
                            "seminar": "SeminarScore"
                        }
                        col = column_map.get(upload_type, "AssignmentScore")

                        if not existing_idx.empty:
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

                        # --- Compute total automatically ---
                        df["TotalScore"] = (
                            df.get("ClassworkScore", 0) * 0.3 +
                            df.get("SeminarScore", 0) * 0.2 +
                            df.get("AssignmentScore", 0) * 0.5
                        ).round(1)

                        # --- Save ---
                        df.to_csv(score_file, index=False)
                        st.success(f"✅ Score saved for {student_name} ({matric}) - {week}")
            else:
                st.info(f"No {upload_type} uploaded yet.")
        else:
            st.info(f"No directory found for {upload_type}.")

    # -----------------------------------------------------
   # -----------------------------------------------------
# 📊 LIVE SCORE REVIEW TABLE (Admin-Only Section)
# -----------------------------------------------------
    if st.session_state.get("role") == "Admin":
        with st.expander("🧭 ADMIN DASHBOARD — Manage and Review Scores", expanded=True):

            st.header("📊 Review Graded Scores")

            base_dir = "student_uploads"
            log_file = os.path.join(base_dir, f"{course_code}_scores.csv")

            if os.path.exists(log_file):
                scores_df = pd.read_csv(log_file)

            # ✅ Filters for easier viewing
                col1, col2 = st.columns(2)
                with col1:
                    type_filter = st.selectbox(
                        "Filter by Upload Type",
                        ["All"] + sorted(scores_df["Type"].unique().tolist()),
                        key=f"{course_code}_type_filter"
                )
                with col2:
                    sort_order = st.radio(
                        "Sort by Date",
                        ["Newest First", "Oldest First"],
                        key=f"{course_code}_sort_order"
                )

                filtered_df = scores_df.copy()
                if type_filter != "All":
                    filtered_df = filtered_df[filtered_df["Type"] == type_filter]

                filtered_df = filtered_df.sort_values(
                    "Date Graded", ascending=(sort_order == "Oldest First")
            )

            # ✅ Display filtered table
                st.dataframe(filtered_df, use_container_width=True)

            ## ✅ Download option
                st.download_button(
                    label="⬇️ Download All Scores (CSV)",
                    data=filtered_df.to_csv(index=False).encode(),
                    file_name=f"{course_code}_graded_scores.csv",
                    mime="text/csv",
                    key=f"{course_code}_download_scores"
)

            else:
                st.info("No graded scores yet. Once you grade a file, it will appear here.")


        # -------------------------------------
        # 🧮 GRADING AND SCORE MANAGEMENT
        # -------------------------------------
        st.divider()
        st.header("🧮 Manual Score Entry & Review")

        name = st.text_input("Student Name", key="manual_name")
        matric = st.text_input("Matric Number", key="manual_matric")
        week = st.selectbox("Select Week", lectures_df["Week"].tolist(), key="manual_week")
        score = st.number_input("Enter Score (0–100)", 0, 100, 0, key="manual_score")
        remarks = st.text_input("Remarks (optional)", key="manual_remarks")
        score_type = st.radio(
            "Select Assessment Type", ["classwork", "seminar", "assignment"], key="manual_type"
        )

        if st.button("💾 Save / Update Score", key="save_manual_score"):
            if not name or not matric:
                st.warning("Please enter student name and matric number.")
            else:
                record_score(course_code, score_type, name, matric, week, score, remarks)
                st.cache_data.clear()
                st.success("✅ Score recorded successfully!")

        # -------------------------------------
        # 📊 Review Student Scores (All)
        # -------------------------------------
        st.divider()
        st.header("📊 Review Student Scores")
        score_file = get_file(course_code, "scores")

        if os.path.exists(score_file):
            scores_df = pd.read_csv(score_file)

            col1, col2 = st.columns(2)
            with col1:
                week_filter = st.selectbox(
                    "Filter by Week",
                    ["All"] + sorted(scores_df["Week"].unique().tolist())
                )
            with col2:
                type_filter = st.selectbox(
                    "Filter by Assessment Type",
                    ["All"] + sorted(scores_df["Type"].unique().tolist())
                )

            filtered_df = scores_df.copy()
            if week_filter != "All":
                filtered_df = filtered_df[filtered_df["Week"] == week_filter]
            if type_filter != "All":
                filtered_df = filtered_df[filtered_df["Type"] == type_filter]

            st.dataframe(filtered_df, use_container_width=True)

            st.download_button(
                "⬇️ Download Filtered Scores",
                filtered_df.to_csv(index=False).encode(),
                file_name=f"{course_code}_filtered_scores.csv",
                mime="text/csv"
            )
        else:
            st.info("🔒 No scores recorded yet.")

# ---------------------------------------------------------
# ---------------------------------------------------------
# 🎥 ADMIN: Upload & Manage Video Lectures
# ---------------------------------------------------------
if st.session_state.get("role") == "admin":
    st.subheader("🎥 Upload & Manage Video Lectures")

    video_dir = os.path.join("video_lectures", course_code)
    os.makedirs(video_dir, exist_ok=True)

    # Upload video file
    uploaded_video = st.file_uploader(
        "Upload Lecture Video (MP4 only)",
        type=["mp4"],
        key=f"{course_code}_video_upload"
    )

    if uploaded_video is not None:
        save_path = os.path.join(video_dir, uploaded_video.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_video.read())
        st.success(f"✅ Video uploaded successfully: {uploaded_video.name}")

    # ---------------------------------------------
    # 🎥 Display list of uploaded lecture videos
    # ---------------------------------------------
    video_files = []  # ✅ Always initialize

    if os.path.exists(video_dir):
        video_files = sorted(os.listdir(video_dir))

    if video_files:
        st.markdown("### 📚 Uploaded Lecture Videos")
        for video in video_files:
            video_path = os.path.join(video_dir, video)
            st.video(video_path)
            with open(video_path, "rb") as vid_file:
                st.download_button(
                    label=f"⬇️ Download {video}",
                    data=vid_file.read(),
                    file_name=video,
                    mime="video/mp4",
                    key=f"{video}_download"
                )
    else:
        st.info("No videos uploaded yet.")


# 🚪 SHOW VIEW BASED ON ROLE
# ===============================================================
if st.session_state["role"] == "Admin":
    admin_view()
elif st.session_state["role"] == "Student":
    student_view()
else:
    st.warning("Please select your role from the sidebar to continue.")
















