import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, date, timedelta
from streamlit_autorefresh import st_autorefresh
import zipfile
import io

# -----------------------------
# BASIC CONFIG + DIRECTORIES
# -----------------------------
st.set_page_config(page_title="Multi-Course Dashboard", page_icon="📚", layout="wide")
st_autorefresh(interval=30 * 1000, key="auto_refresh")

# Ensure required folders exist
for d in ["data", "submissions", "records", "scores", "modules"]:
    os.makedirs(d, exist_ok=True)

MODULES_DIR = "modules"

# -----------------------------
# STYLES / FOOTER
# -----------------------------
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

# -----------------------------
# COURSES
# -----------------------------
COURSES = {
    "MCB 221 – General Microbiology": "MCB221",
    "BCH 201 – General Biochemistry": "BCH201",
    "BIO 203 – General Physiology": "BIO203",
}

# -----------------------------
# FILE HELPERS
# -----------------------------
# --- Helper Function: View/Download Files ---
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
# LECTURES INITIALISATION
# -----------------------------
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
    # ensure columns exist and fillna
    for col in ["Brief", "Assignment", "Classwork"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")
    return df

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
# APP LAYOUT
# -----------------------------
st.subheader("Department of Biological Sciences, Sikiru Adetona College of Education Omu-Ijebu")
st.title("📚 Multi-Course Portal")

course = st.selectbox("Select Course:", list(COURSES.keys()))
course_code = COURSES[course]
mode = st.radio("Select Mode:", ["Student", "Teacher/Admin"]) 

# Load or init lectures for the selected course
default_topics = [f"Lecture Topic {i+1}" for i in range(12)]
lectures_df = init_lectures(course_code, default_topics)

# -----------------------------
# STUDENT MODE
# -----------------------------
if mode == "Student":
    st.subheader(f"🎓 {course} Student Access")

    with st.form(f"{course_code}_attendance_form"):
        name = st.text_input("Full Name")
        matric = st.text_input("Matric Number")
        week = st.selectbox("Select Lecture Week", lectures_df["Week"].tolist())
        attendance_code = st.text_input("Enter Attendance Code (Ask your lecturer)")
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
                "MCB221": {"valid_code": "MCB221-ZT9", "start": "10:00", "end": "14:00"},
            }

            if course_code not in COURSE_TIMINGS:
                st.error(f"⚠️ No timing configured for {course_code}.")
            else:
                start_time = datetime.strptime(COURSE_TIMINGS[course_code]["start"], "%H:%M").time()
                end_time = datetime.strptime(COURSE_TIMINGS[course_code]["end"], "%H:%M").time()
                valid_code = COURSE_TIMINGS[course_code]["valid_code"]
                now_t = datetime.now().time()

                if not (start_time <= now_t <= end_time):
                    st.error(f"⏰ Attendance for {course_code} is only open between "
                             f"{start_time.strftime('%I:%M %p')} and {end_time.strftime('%I:%M %p')}.")
                elif attendance_code != valid_code:
                    st.error("❌ Invalid attendance code. Ask your lecturer for today’s code.")
                elif has_marked_attendance(course_code, week, name):
                    st.info("✅ Attendance already marked. You can’t mark it again.")
                else:
                    ok = mark_attendance_entry(course_code, name, matric, week)
                    if ok:
                        st.success(f"✅ Attendance recorded for {name} ({week}).")
                    else:
                        st.error("Could not record attendance. Try again or contact your lecturer.")

    st.divider()
    st.subheader("📈 Your Continuous Assessment (CA) Summary")

    # Student CA summary (optional central scores file)
    scores_file = os.path.join("scores", f"{course_code}_scores.csv")
    if os.path.exists(scores_file):
        df_scores = pd.read_csv(scores_file)
        # try to protect against missing name/matric when not set
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

                st.dataframe(student_scores[[col for col in ["Week", "ClassworkScore", "SeminarScore", "AssignmentScore", "TotalScore"] if col in student_scores.columns]], use_container_width=True)
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

    # Show lecture info for selected week
    lecture_row = lectures_df[lectures_df["Week"] == (week if 'week' in locals() else lectures_df.iloc[0]['Week'])]
    if lecture_row.empty:
        st.error("No lecture data found for the selected week.")
    else:
        lecture_info = lecture_row.iloc[0]
        st.divider()
        st.subheader(f"📖 {lecture_info['Week']}: {lecture_info['Topic']}")

        brief = str(lecture_info["Brief"]) if pd.notnull(lecture_info["Brief"]) else ""
        assignment = str(lecture_info["Assignment"]) if pd.notnull(lecture_info["Brief"]) else ""
        classwork_text = str(lecture_info["Classwork"]) if pd.notnull(lecture_info["Classwork"]) else ""

        if brief.strip():
            st.markdown(f"**Lecture Brief:** {brief}")

        # Classwork Section
           
        if lecture_info["Classwork"].strip():
            st.markdown("### 🧩 Classwork Questions")
            questions = [q.strip() for q in lecture_info["Classwork"].split(";") if q.strip()]
            with st.form("cw_form"):
                answers = [st.text_input(f"Q{i+1}: {q}") for i,q in enumerate(questions)]
                submit_cw = st.form_submit_button("Submit Answers", disabled=not is_classwork_open(course_code, week))
                if submit_cw: save_classwork(name, matric, week, answers)
        else: st.info("Classwork not yet released.")

        if assignment.strip():
            st.subheader("📚 Assignment")
            st.markdown(f"**Assignment:** {assignment}")
        else:
            st.info("Assignment not released yet.")

        # Lecture PDF
        pdf_path = os.path.join(MODULES_DIR, f"{course_code}_{lecture_info['Week'].replace(' ', '_')}.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
            st.download_button(label=f"📥 Download {lecture_info['Week']} Module PDF", data=pdf_bytes, file_name=f"{course_code}_{lecture_info['Week']}.pdf", mime="application/pdf")
        else:
            st.info("Lecture note not uploaded yet.")

   # -----------------------------
# 📄 ASSIGNMENT UPLOAD
# -----------------------------
st.divider()
st.subheader("📄 Assignment Upload")

selected_week_a = st.selectbox("Select Week for Assignment", lectures_df["Week"].tolist(), key="assignment_week_select")
matric_a = st.text_input("Matric Number", key="matric_a")
student_name_a = st.text_input("Enter your full name", key="student_name_a")

uploaded_assignment = st.file_uploader(
    f"Upload Assignment for {selected_week_a}",
    type=["pdf", "docx", "jpg", "png"],
    key=f"{course_code}_assignment"
)

with st.form("assignment_form"):
    submit_assignment = st.form_submit_button(f"Submit Assignment for {selected_week_a}")

    if submit_assignment:
        if not matric_a or not student_name_a:
            st.warning("Please enter your name and matric number before submitting.")
        elif not uploaded_assignment:
            st.warning("Please upload a file before submitting.")
        else:
            file_path = save_file(course_code, student_name_a, selected_week_a, uploaded_assignment, "assignment")
            log_submission(course_code, matric_a, student_name_a, selected_week_a, uploaded_assignment.name, "Assignment")
            st.success(f"✅ {student_name_a} ({matric_a}) — Assignment uploaded successfully!")

# -----------------------------
# 🖌️ DRAWING UPLOAD
# -----------------------------
st.divider()
st.subheader("🖌️ Drawing Upload for Class Work")

selected_week_d = st.selectbox("Select Week for Drawing", lectures_df["Week"].tolist(), key="drawing_week_select")
matric_d = st.text_input("Matric Number", key="matric_d")
student_name_d = st.text_input("Enter your full name", key="student_name_d")

uploaded_drawing = st.file_uploader(
    f"Upload Drawing for {selected_week_d}",
    type=["jpg", "jpeg", "png", "pdf"],
    key=f"{course_code}_drawing"
)

with st.form("drawing_form"):
    submit_drawing = st.form_submit_button(f"Submit Drawing for {selected_week_d}")

    if submit_drawing:
        if not matric_d or not student_name_d:
            st.warning("Please enter your name and matric number before submitting.")
        elif not uploaded_drawing:
            st.warning("Please upload a file before submitting.")
        else:
            file_path = save_file(course_code, student_name_d, selected_week_d, uploaded_drawing, "drawing")
            log_submission(course_code, matric_d, student_name_d, selected_week_d, uploaded_drawing.name, "Drawing")
            st.success(f"✅ {student_name_d} ({matric_d}) — Drawing uploaded successfully!")

# -----------------------------
# 🎤 SEMINAR UPLOAD
# -----------------------------
st.divider()
st.subheader("🎤 Seminar Upload")

selected_week_s = st.selectbox("Select Week for Seminar", lectures_df["Week"].tolist(), key="seminar_week_select")
matric_s = st.text_input("Matric Number", key="matric_s")
student_name_s = st.text_input("Enter your full name", key="student_name_s")

uploaded_seminar = st.file_uploader(
    f"Upload Seminar PPT for {selected_week_s}",
    type=["ppt", "pptx"],
    key=f"{course_code}_seminar"
)

with st.form("seminar_form"):
    submit_seminar = st.form_submit_button(f"Submit Seminar for {selected_week_s}")

    if submit_seminar:
        if not matric_s or not student_name_s:
            st.warning("Please enter your name and matric number before submitting.")
        elif not uploaded_seminar:
            st.warning("Please upload a file before submitting.")
        else:
            file_path = save_file(course_code, student_name_s, selected_week_s, uploaded_seminar, "seminar")
            log_submission(course_code, matric_s, student_name_s, selected_week_s, uploaded_seminar.name, "Seminar")
            st.success(f"✅ {student_name_s} ({matric_s}) — Seminar uploaded successfully!")


# ====================================================
# 🔐 TEACHER / ADMIN DASHBOARD (FULL + SCORE VIEWER)
# ====================================================
import streamlit as st
import pandas as pd
import os

# -----------------------------
# 🧠 ADMIN / TEACHER MODE LOGIN
# -----------------------------
if mode == "Teacher/Admin":
    st.title("🎓 Instructor Dashboard")
    st.subheader("🔐 Teacher / Admin Panel")

    ADMIN_PASS = "bimpe2025class"
    password = st.text_input("Enter Admin Password", type="password")

    if password == ADMIN_PASS:
        st.session_state["role"] = "admin"
        st.success(f"✅ Logged in as Admin for {course}")

        # -------------------------------------
        # 📚 LECTURE MANAGEMENT
        # -------------------------------------
        st.header("📚 Lecture Management")
        lecture_to_edit = st.selectbox("Select Lecture", lectures_df["Week"].unique())
        row_idx = lectures_df[lectures_df["Week"] == lecture_to_edit].index[0]

        brief = st.text_area("Lecture Brief", value=lectures_df.at[row_idx, "Brief"])
        assignment = st.text_area("Assignment", value=lectures_df.at[row_idx, "Assignment"])
        classwork = st.text_area("Classwork (Separate questions with ;)", 
                                 value=lectures_df.at[row_idx, "Classwork"])

        if st.button("💾 Update Lecture"):
            lectures_df.at[row_idx, "Brief"] = brief
            lectures_df.at[row_idx, "Assignment"] = assignment
            lectures_df.at[row_idx, "Classwork"] = classwork
            lectures_df.to_csv(get_file(course_code, "lectures"), index=False)
            st.success(f"{lecture_to_edit} updated successfully!")

        # -------------------------------------
        # 📄 UPLOAD LECTURE PDF MODULE
        # -------------------------------------
        st.header("📄 Upload Lecture PDF Module")
        pdf_file = st.file_uploader("Upload Lecture Module", type=["pdf"])
        if pdf_file:
            pdf_path = os.path.join(MODULES_DIR, f"{course_code}_{lecture_to_edit.replace(' ', '_')}.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            st.success(f"✅ PDF uploaded for {lecture_to_edit}")

        # -------------------------------------
        # 🧩 CLASSWORK CONTROL
        # -------------------------------------
        st.header("🧩 Classwork Control")
        week_to_control = st.selectbox("Select Week to Open/Close Classwork", 
                                       lectures_df["Week"].unique(), key="cw_control")
        if st.button(f"📖 Open Classwork for {week_to_control} (20 mins)"):
            open_classwork(course_code, week_to_control)
            st.success(f"✅ Classwork for {week_to_control} is now open for 20 minutes.")

        close_classwork_after_20min(course_code)

        # -------------------------------------
        # 🗂️ VIEW RECORDS
        # -------------------------------------
        st.header("🗂️ View Records")
        for file, label in [("attendance", "Attendance Records"), 
                            ("classwork_submissions", "Classwork Submissions")]:
            csv_file = get_file(course_code, file)
            st.markdown(f"### {label}")
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                st.dataframe(df)
                st.download_button(f"⬇️ Download {label}", df.to_csv(index=False).encode(), csv_file)
            else:
                st.info(f"No {label.lower()} yet.")

        # -------------------------------------
        # 🧮 GRADING AND SCORE MANAGEMENT
        # -------------------------------------
        st.header("🧮 Grading and Score Management")
        name = st.text_input("Student Name")
        matric = st.text_input("Matric Number")
        week = st.selectbox("Select Week", lectures_df["Week"].tolist())
        score = st.number_input("Enter Score (0–100)", 0, 100, 0)
        remarks = st.text_input("Remarks (optional)")
        score_type = st.radio("Select Assessment Type", ["classwork", "seminar", "assignment"])
        
        if st.button("💾 Save / Update Score"):
            if not name or not matric:
                st.warning("Please enter student name and matric number.")
            else:
                record_score(course_code, score_type, name, matric, week, score, remarks)
                st.cache_data.clear()
                st.success("✅ Score recorded successfully!")

        if st.button("🔁 Refresh Scores Now"):
            st.cache_data.clear()
            st.rerun()

        # -------------------------------------
        # 📊 SCORE REVIEW TABLE (NEW FEATURE)
        # -------------------------------------
        st.header("📊 Review & Filter Student Scores")
        score_file = get_file(course_code, "scores")
        if os.path.exists(score_file):
            scores_df = pd.read_csv(score_file)

            # Filters
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                week_filter = st.selectbox("Filter by Week", ["All"] + sorted(scores_df["Week"].unique().tolist()))
            with filter_col2:
                type_filter = st.selectbox("Filter by Assessment Type", ["All"] + sorted(scores_df["Type"].unique().tolist()))

            # Apply filters
            filtered_df = scores_df.copy()
            if week_filter != "All":
                filtered_df = filtered_df[filtered_df["Week"] == week_filter]
            if type_filter != "All":
                filtered_df = filtered_df[filtered_df["Type"] == type_filter]

            # Display filtered table
            st.dataframe(filtered_df)

            # Download filtered scores
            st.download_button(
                "⬇️ Download Filtered Scores",
                filtered_df.to_csv(index=False).encode(),
                file_name=f"{course_code}_filtered_scores.csv",
                mime="text/csv"
            )
        else:
            st.info("No scores recorded yet.")

    else:
        if password:
            st.error("❌ Incorrect password")

else:
    st.info("🔒 Only admins can access this section.")

