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

# =========================================================
# ✅ UNIVERSAL HELPERS — ATTENDANCE, ASSIGNMENTS & SUBMISSIONS
# =========================================================
import os
import pandas as pd
from datetime import datetime
import streamlit as st

# ---------------------------------------------------------
# 🔧 Base Directories (created automatically)
# ---------------------------------------------------------
ATTENDANCE_DIR = "attendance"
UPLOADS_DIR = "uploads"
SCORES_DIR = "scores"
CLASSWORK_STATUS_DIR = "classwork_status"

for directory in [ATTENDANCE_DIR, UPLOADS_DIR, SCORES_DIR, CLASSWORK_STATUS_DIR]:
    os.makedirs(directory, exist_ok=True)


# =========================================================
# 📘 ATTENDANCE HELPERS
# =========================================================

def get_attendance_file(course_code):
    """Return full path for the attendance file of a course."""
    return os.path.join(ATTENDANCE_DIR, f"{course_code}_attendance.csv")


def has_marked_attendance(course_code, week, name, matric):
    """
    Check if a student (name + matric) has already marked attendance
    for a specific course and week.
    """
    try:
        file_path = get_attendance_file(course_code)
        if not os.path.exists(file_path):
            return False

        df = pd.read_csv(file_path)
        if df.empty:
            return False

        # Normalize comparison
        name = str(name).strip().lower()
        matric = str(matric).strip().lower()
        week = str(week).strip().lower()

        return (
            (df["Name"].astype(str).str.strip().str.lower() == name)
            & (df["Matric"].astype(str).str.strip().str.lower() == matric)
            & (df["Week"].astype(str).str.strip().str.lower() == week)
        ).any()
    except Exception as e:
        st.error(f"⚠️ Error checking attendance: {e}")
        return False


def mark_attendance_entry(course_code, name, matric, week):
    """
    Record or append a new attendance entry for a student.
    This function is shared between student and admin boards.
    """
    try:
        file_path = get_attendance_file(course_code)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_data = {
            "Name": [str(name).strip()],
            "Matric": [str(matric).strip()],
            "Week": [str(week).strip()],
            "Timestamp": [timestamp]
        }

        new_df = pd.DataFrame(new_data)

        if os.path.exists(file_path):
            existing_df = pd.read_csv(file_path)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        combined_df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Error recording attendance: {e}")
        return False


def load_attendance_records(course_code):
    """Load all attendance entries for a given course."""
    try:
        file_path = get_attendance_file(course_code)
        if os.path.exists(file_path):
            return pd.read_csv(file_path)
        return pd.DataFrame(columns=["Name", "Matric", "Week", "Timestamp"])
    except Exception as e:
        st.error(f"⚠️ Error loading attendance records: {e}")
        return pd.DataFrame(columns=["Name", "Matric", "Week", "Timestamp"])


# =========================================================
# 📂 FILE UPLOAD & SUBMISSION HELPERS
# =========================================================

def save_file(course_code, student_name, week, uploaded_file, category):
    """
    Save uploaded files (assignment, drawing, seminar) into organized folders.
    """
    try:
        safe_name = f"{student_name.replace(' ', '_')}_{week}_{uploaded_file.name}"
        save_dir = os.path.join(UPLOADS_DIR, category, course_code)
        os.makedirs(save_dir, exist_ok=True)

        file_path = os.path.join(save_dir, safe_name)

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return file_path
    except Exception as e:
        st.error(f"⚠️ Error saving file: {e}")
        return None


def log_submission(course_code, matric, name, week, filename, submission_type):
    """
    Log student uploads for tracking by admin.
    """
    try:
        log_file = os.path.join(UPLOADS_DIR, "submissions_log.csv")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_log = pd.DataFrame([{
            "Course": course_code,
            "Matric": matric,
            "Name": name,
            "Week": week,
            "FileName": filename,
            "Type": submission_type,
            "Timestamp": timestamp
        }])

        if os.path.exists(log_file):
            df = pd.read_csv(log_file)
            df = pd.concat([df, new_log], ignore_index=True)
        else:
            df = new_log

        df.to_csv(log_file, index=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Error logging submission: {e}")
        return False


# =========================================================
# 🧩 CLASSWORK HELPERS
# =========================================================

def save_classwork(student_name, matric, week, answers):
    """
    Save classwork responses from students.
    """
    try:
        file_path = os.path.join(CLASSWORK_STATUS_DIR, f"classwork_responses.csv")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_row = pd.DataFrame([{
            "Name": student_name,
            "Matric": matric,
            "Week": week,
            "Answers": "; ".join(answers),
            "Timestamp": timestamp
        }])

        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            df = pd.concat([df, new_row], ignore_index=True)
        else:
            df = new_row

        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Error saving classwork: {e}")
        return False


def load_classwork_status(course_code, week):
    """
    Load classwork status for a given course and week.
    """
    try:
        file_path = os.path.join(CLASSWORK_STATUS_DIR, f"{course_code}_classwork_status.csv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            record = df[(df["Course"] == course_code) & (df["Week"] == week)]
            if not record.empty:
                return record.iloc[0].to_dict()
        return {"Open": False}
    except Exception:
        return {"Open": False}


# =========================================================
# 🧾 SCORES MANAGEMENT HELPERS
# =========================================================

def load_scores(course_code):
    """Load student scores for a given course."""
    try:
        score_file = os.path.join(SCORES_DIR, f"{course_code.lower()}_scores.csv")
        if os.path.exists(score_file):
            return pd.read_csv(score_file)
        return pd.DataFrame(columns=["MatricNo", "Name", "Score"])
    except Exception as e:
        st.error(f"⚠️ Error loading scores: {e}")
        return pd.DataFrame(columns=["MatricNo", "Name", "Score"])


def save_scores(course_code, scores_df):
    """Save scores after updates."""
    try:
        score_file = os.path.join(SCORES_DIR, f"{course_code.lower()}_scores.csv")
        scores_df.to_csv(score_file, index=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Error saving scores: {e}")
        return False

# ===============================================================
# 📘 UNIVERSAL HELPERS (ADMIN + STUDENT)
# ===============================================================

import os
import pandas as pd
from datetime import datetime
import streamlit as st

# ✅ Main directory for logs
LOG_DIR = "attendance"
os.makedirs(LOG_DIR, exist_ok=True)


# ✅ Utility: ensure CSV exists with columns
def ensure_csv_exists(path, columns):
    """Create an empty CSV if missing to avoid FileNotFound errors."""
    if not os.path.exists(path):
        df = pd.DataFrame(columns=columns)
        df.to_csv(path, index=False)


# ✅ Check if student already marked attendance
def has_marked_attendance(course_code, week, name, matric):
    """Check if student has already marked attendance."""
    try:
        attendance_file = os.path.join(LOG_DIR, f"{course_code}_attendance.csv")
        ensure_csv_exists(attendance_file, ["Name", "Matric", "Week", "Timestamp"])

        df = pd.read_csv(attendance_file)
        df["Name"] = df["Name"].astype(str).str.strip().str.lower()
        df["Matric"] = df["Matric"].astype(str).str.strip().str.lower()
        df["Week"] = df["Week"].astype(str).str.strip().str.lower()

        name_clean = name.strip().lower()
        matric_clean = matric.strip().lower()
        week_clean = week.strip().lower()

        existing = df[
            (df["Name"] == name_clean)
            & (df["Matric"] == matric_clean)
            & (df["Week"] == week_clean)
        ]
        return len(existing) > 0
    except Exception as e:
        st.error(f"⚠️ Error checking attendance: {e}")
        return True


# ✅ Mark attendance
def mark_attendance_entry(course_code, name, matric, week):
    """Record a student's attendance persistently."""
    try:
        attendance_file = os.path.join(LOG_DIR, f"{course_code}_attendance.csv")
        ensure_csv_exists(attendance_file, ["Name", "Matric", "Week", "Timestamp"])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = pd.DataFrame({
            "Name": [name.strip()],
            "Matric": [matric.strip()],
            "Week": [week],
            "Timestamp": [timestamp],
        })

        df = pd.read_csv(attendance_file)
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(attendance_file, index=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Error recording attendance: {e}")
        return False


# ✅ Check if student submitted assignment/classwork
def has_submitted(course_code, week, matric, submission_type):
    """Check if student already submitted an assignment/classwork."""
    try:
        file_path = os.path.join(LOG_DIR, f"{submission_type}_{course_code}_{week.replace(' ', '')}.csv")
        ensure_csv_exists(file_path, ["Name", "Matric", "Week", "FileName", "Timestamp"])

        df = pd.read_csv(file_path)
        df["Matric"] = df["Matric"].astype(str).str.strip().str.lower()
        matric_clean = matric.strip().lower()

        return matric_clean in df["Matric"].values
    except Exception as e:
        st.error(f"⚠️ Error checking submission: {e}")
        return False


# ✅ Record submission
def record_submission(course_code, name, matric, week, submission_type, file_name):
    """Save student submission persistently."""
    try:
        file_path = os.path.join(LOG_DIR, f"{submission_type}_{course_code}_{week.replace(' ', '')}.csv")
        ensure_csv_exists(file_path, ["Name", "Matric", "Week", "FileName", "Timestamp"])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row = pd.DataFrame({
            "Name": [name.strip()],
            "Matric": [matric.strip()],
            "Week": [week],
            "FileName": [file_name],
            "Timestamp": [timestamp],
        })

        df = pd.read_csv(file_path)
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(file_path, index=False)
        return True
    except Exception as e:
        st.error(f"⚠️ Error recording submission: {e}")
        return False


# ===============================================================
# 🧑‍🏫 ADMIN DASHBOARD VIEWER
# ===============================================================

def admin_attendance_view():
    """Allow admin to view all attendance and submissions."""
    st.subheader("🗂️ Attendance & Submission Records")

    csv_files = [f for f in os.listdir(LOG_DIR) if f.endswith(".csv")]

    if not csv_files:
        st.warning("⚠️ No attendance or submission records found yet.")
        return

    course_files = {}
    for file in csv_files:
        parts = file.replace(".csv", "").split("_")
        if len(parts) < 2:
            continue
        course_code = parts[1]
        course_files.setdefault(course_code, []).append(file)

    selected_course = st.selectbox("📘 Select Course", sorted(course_files.keys()))

    for file in sorted(course_files[selected_course]):
        file_path = os.path.join(LOG_DIR, file)
        df = pd.read_csv(file_path)

        if df.empty:
            continue

        file_type = (
            "Attendance"
            if "attendance" in file
            else "Assignment"
            if "assignment" in file
            else "Classwork"
            if "classwork" in file
            else "Unknown"
        )

        st.markdown(f"### 🗓️ {file_type}: `{file.replace('.csv', '')}`")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label=f"⬇️ Download {file_type} CSV",
            data=csv,
            file_name=file,
            mime="text/csv",
        )

        st.divider()



import os
import pandas as pd
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import streamlit as st

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


                               
# ===============================================================
# 🎓 STUDENT VIEW DASHBOARD
# ===============================================================
def student_view(course_code):
    if st.session_state.get("role") != "Student":
        return

    # ✅ Always ensure required folders exist first
    ensure_directories()

    st.title("🎓 Student Dashboard")
    st.info("Welcome! Access your lectures, upload assignments, and mark attendance here.")

    # 🎓 COURSE SELECTION
    course_code = st.selectbox(
        "Select Course",
        ["MCB221", "BCH201", "BIO203", "BIO113", "BIO306"]
    )

    # ===============================================================
    # 📘 LOAD LECTURES
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
                    columns=["Week", "Topic", "Brief", "Assignment", "Classwork"]
                )
                lectures_df.to_csv(LECTURE_FILE, index=False)
            else:
                lectures_df = pd.read_csv(LECTURE_FILE)

        # Ensure essential columns exist
        for col in ["Week", "Topic", "Brief", "Assignment", "Classwork"]:
            if col not in lectures_df.columns:
                lectures_df[col] = ""

        st.session_state["lectures_df"] = lectures_df

    except Exception as e:
        st.error(f"⚠️ Error loading lecture file: {e}")
        return


# 🕒 ATTENDANCE FORM
    # -------------------------------
    with st.form(f"{course_code}_attendance_form"):
        name = st.text_input("Full Name", key=f"{course_code}_student_name")
        matric = st.text_input("Matric Number", key=f"{course_code}_student_matric")
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

        # Get status from persistent storage
        status_data = get_attendance_status(course_code, week)
        is_attendance_open = status_data.get("is_open", False)
        
        # Debug information
        st.write("---")
        st.subheader("🔍 Debug Information")
        st.write(f"**Course:** `{course_code}`")
        st.write(f"**Week:** `{week}`")
        st.write(f"**Status from JSON:** `{status_data}`")
        st.write(f"**Attendance Open:** `{is_attendance_open}`")
        
        # Show all status for debugging
        all_status = get_all_attendance_status()
        st.write("**All status in JSON file:**")
        if all_status:
            for key, value in all_status.items():
                st.write(f"- `{key}`: `{value}`")
        else:
            st.write("No status found in JSON file")
        st.write("---")
        
        if not is_attendance_open:
            st.error("🚫 Attendance for this course is currently closed. Please wait for your lecturer to open it.")
            st.stop()

        # Prevent duplicate marking
        if has_marked_attendance(course_code, week, name, matric):
            st.info("✅ Attendance already marked for this week.")
            st.stop()

        # Mark attendance
        ok = mark_attendance_entry(course_code, name, matric, week)
        if ok:
            st.session_state["attended_week"] = str(week)
            st.success(f"🎉 Attendance recorded successfully for {course_code} - {week}.")
        else:
            st.error("⚠️ Failed to record attendance. Try again later.")
        
    # ---------------------------------------------
    # 📘 Lecture Briefs and Classwork
    # ---------------------------------------------
    st.divider()
    st.subheader("📘 Lecture Briefs and Classwork")
    attended_week = st.session_state.get("attended_week")

    week = str(st.session_state.get("attended_week", ""))
    st.success(f"Access granted for Week {week}")

    lectures_df = st.session_state["lectures_df"] if "lectures_df" in st.session_state else load_lectures(course_code)

    # ---------------------------------------------
# 📖 Topic & Lecture Brief
# ---------------------------------------------
    if lectures_df is None or lectures_df.empty or "Week" not in lectures_df.columns:
        st.warning("⚠️ No lecture data found for this course.")
        return

# Ensure week is always a string
    week = str(week)

# Initialize lecture_row safely
    lecture_row = pd.DataFrame()

# Match lecture by week (avoid type mismatches)
    if not lectures_df.empty and "Week" in lectures_df.columns:
        lecture_row = lectures_df.loc[lectures_df["Week"].astype(str) == week]

# Convert to dict if found
    if not lecture_row.empty:
        lecture_info = lecture_row.squeeze().to_dict()
    else:
        lecture_info = {}
        st.info(f"No lecture content found for {week}.")


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

    
# ===============================================================
# 🧩 STUDENT CLASSWORK DISPLAY (FULLY FIXED VERSION)
# ===============================================================

# Retrieve classwork text from lecture_info
   
    classwork_text = str(clean_text(lecture_info.get("Classwork", "")) or "").strip()

# Debugging helper (optional)
# st.write("DEBUG: Classwork value =", classwork_text)

    if classwork_text:
        st.markdown("### 🧩 Classwork Questions")
        questions = [q.strip() for q in classwork_text.split(";") if q.strip()]

    # ✅ Load classwork status file
        CLASSWORK_STATUS_FILE = os.path.join("classwork_status", f"{course_code}_classwork_status.csv")
        os.makedirs(os.path.dirname(CLASSWORK_STATUS_FILE), exist_ok=True)

        is_open = False
        if os.path.exists(CLASSWORK_STATUS_FILE):
            df_status = pd.read_csv(CLASSWORK_STATUS_FILE)
            if ((df_status["Course"] == course_code) & (df_status["Week"] == week) & (df_status["Open"] == True)).any():
                is_open = True

    # ✅ Check if classwork is open
        if not is_open:
            st.info("⏳ Classwork not yet opened by Admin.")
        else:
        # Remaining time
            end_key = f"{course_code}_{week}_cw_end"
            end_time = st.session_state.get(end_key)
            if not end_time:
                end_time = datetime.now() + timedelta(minutes=20)
                st.session_state[end_key] = end_time

            remaining_sec = int((end_time - datetime.now()).total_seconds())

            if remaining_sec > 0:
            # Auto-refresh every second
                st_autorefresh(interval=1000, key=f"{course_code}_{week}_cw_timer")

                minutes, seconds = divmod(remaining_sec, 60)
                st.info(f"⏱ Time remaining: {minutes:02d}:{seconds:02d}")

            # Progress bar
                total_duration = 20 * 60
                progress = min(max((total_duration - remaining_sec) / total_duration, 0), 1)
                st.progress(progress)

            # 📝 Classwork form
                with st.form(f"classwork_form_{course_code}_{week}"):
                    answers = [st.text_input(f"Q{i+1}: {q}") for i, q in enumerate(questions)]
                    submit_btn = st.form_submit_button("Submit Answers")

                    if submit_btn:
                        save_classwork(name, matric, week, answers)
                        st.success("✅ Classwork submitted successfully!")

            else:
                st.warning("⏰ Time's up! Classwork is closed.")
                st.progress(1.0)
    else:
        st.info("📚 No classwork uploaded for this lecture.")


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
        # Download button
            with open(file_path, "rb") as pdf_file:
                st.download_button(
                    label=f"📥 Download {label}",
                    data=pdf_file.read(),
                    file_name=os.path.basename(file_path),
                    mime="application/pdf"
            )
       
        else:
            st.info(f"{label} not uploaded yet.")

# Display all PDFs
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

# Base attendance folder (where week-by-week files are stored)
    attendance_folder = os.path.join("data", "attendance")
    os.makedirs(attendance_folder, exist_ok=True)

# ATTENDANCE RECORDS
    st.subheader("🕒 Attendance Records (Week by Week)")

    attendance_files = [
        f for f in os.listdir(attendance_folder) if f.endswith(".csv")
]

    if attendance_files:
        selected_file = st.selectbox(
            "Select Attendance Week File to View/Delete",
            sorted(attendance_files),
            key="select_attendance_file"
    )

        selected_path = os.path.join(attendance_folder, selected_file)

        try:
            df = pd.read_csv(selected_path)
            st.dataframe(df, use_container_width=True)

            col1, col2 = st.columns([2, 1])

            with col1:
                st.download_button(
                    label=f"⬇️ Download {selected_file}",
                    data=df.to_csv(index=False).encode(),
                    file_name=selected_file,
                    mime="text/csv",
                    key=f"download_{selected_file}"
            )

            with col2:
                if st.button(f"🗑️ Delete {selected_file}", key=f"delete_{selected_file}"):
                    os.remove(selected_path)
                    st.warning(f"⚠️ {selected_file} deleted successfully.")
                    st.experimental_rerun()

        except Exception as e:
            st.error(f"Error reading {selected_file}: {e}")

    else:
        st.info("No attendance files found yet.")

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
                        st.experimental_rerun()

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
# ===============================================================
# 🧩 ADMIN CLASSWORK CONTROL (FULLY FIXED VERSION)
# ===============================================================

    st.header("🧩 Classwork Control")

# Load lectures for the selected course
    if "lectures_df" in st.session_state and not st.session_state["lectures_df"].empty:
        lectures_df = st.session_state["lectures_df"]
    else:
        lectures_df = load_lectures(course_code)

    if lectures_df.empty:
        st.info("No lectures found for this course.")
    else:
    # Select week to control
        week_options = lectures_df["Week"].unique().tolist()
        week_to_control = st.selectbox(
            "Select Week to Open/Close Classwork",
            week_options,
            key=f"{course_code}_admin_cw_week"
    )

    # ✅ Build the file path correctly
        CLASSWORK_STATUS_DIR = "classwork_status"
        os.makedirs(CLASSWORK_STATUS_DIR, exist_ok=True)
        CLASSWORK_STATUS_FILE = os.path.join(CLASSWORK_STATUS_DIR, f"{course_code}_classwork_status.csv")

    # ✅ Load or create the status CSV
        if os.path.exists(CLASSWORK_STATUS_FILE):
            df_status = pd.read_csv(CLASSWORK_STATUS_FILE)
        else:
            df_status = pd.DataFrame(columns=["Course", "Week", "Open"])

        st.markdown(f"### Managing Classwork for **{course_code}** – Week **{week_to_control}**")

    # ------------------------
    # 📖 OPEN CLASSWORK BUTTON
    # ------------------------
        if st.button(f"📖 Open Classwork for {week_to_control} (20 mins)", key=f"open_cw_{course_code}"):
        # Ensure entry exists or update existing
            if ((df_status["Course"] == course_code) & (df_status["Week"] == week_to_control)).any():
                df_status.loc[
                    (df_status["Course"] == course_code) & (df_status["Week"] == week_to_control),
                    "Open"
                ] = True
            else:
                df_status = pd.concat([df_status, pd.DataFrame([{
                    "Course": course_code,
                    "Week": week_to_control,
                    "Open": True
                }])], ignore_index=True)

        # ✅ Save safely
            df_status.to_csv(CLASSWORK_STATUS_FILE, index=False)

        # Set timer (20 minutes)
            st.session_state[f"{course_code}_{week_to_control}_cw_end"] = datetime.now() + timedelta(minutes=20)
            st.success(f"✅ Classwork for Week {week_to_control} is now OPEN for 20 minutes!")

    # ------------------------
    # ⏹ CLOSE CLASSWORK BUTTON
    # ------------------------
        if st.button(f"⏹ Close Classwork for {week_to_control}", key=f"close_cw_{course_code}"):
            if ((df_status["Course"] == course_code) & (df_status["Week"] == week_to_control)).any():
                df_status.loc[
                    (df_status["Course"] == course_code) & (df_status["Week"] == week_to_control),
                    "Open"
                ] = False
                df_status.to_csv(CLASSWORK_STATUS_FILE, index=False)

        # Expire timer
            st.session_state[f"{course_code}_{week_to_control}_cw_end"] = datetime.now()
            st.warning(f"⚠️ Classwork for Week {week_to_control} is now CLOSED!")




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

    # Debug information
    with st.expander("🔍 Persistent Storage Debug Info"):
        st.write("All attendance status in JSON file:")
        all_status = get_all_attendance_status()
        if all_status:
            for key, value in all_status.items():
                st.write(f"- `{key}`: `{value}`")
        else:
            st.write("No attendance status found in JSON file")
        
        st.write(f"Current course: `{course_code}`")
        st.write(f"Current week: `{selected_week}`")
        st.write(f"Current status: `{current_status}`")

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











































































































































































