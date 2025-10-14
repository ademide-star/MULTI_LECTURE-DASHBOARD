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
def get_file(course_code, filename):
    return f"{course_code}_{filename}.csv"

def init_lectures(course_code, default_weeks):
    LECTURE_FILE = get_file(course_code, "lectures")
    if not os.path.exists(LECTURE_FILE):
        lecture_data = {
            "Week": [f"Week {i+1}" for i in range(len(default_weeks))],
            "Topic": default_weeks,
            "Brief": [""]*len(default_weeks),
            "Assignment": [""]*len(default_weeks),
            "Classwork": [""]*len(default_weeks)
        }
        pd.DataFrame(lecture_data).to_csv(LECTURE_FILE, index=False)
    df = pd.read_csv(LECTURE_FILE)
    # Fill NaN with empty string
    df["Brief"] = df["Brief"].fillna("")
    df["Assignment"] = df["Assignment"].fillna("")
    df["Classwork"] = df["Classwork"].fillna("")
    return df
    
def display_seminar_upload(name, matric):
    today = date.today()
    if today >= date(today.year,10,20):
        seminar_file = st.file_uploader("Upload Seminar PPT", type=["ppt","pptx"])
        if seminar_file:
            save_seminar(name, matric, seminar_file)
        st.info("Seminar presentations will hold in the **3rd week of November**.")
    else:
        st.warning("Seminar submissions will open mid-semester.")
        
def mark_attendance(course_code, name, matric, week):
    ATTENDANCE_FILE = get_file(course_code, "attendance")
    df = pd.read_csv(ATTENDANCE_FILE) if os.path.exists(ATTENDANCE_FILE) else pd.DataFrame(columns=["Timestamp","Matric Number","Name","Week"])
    if ((df["Matric Number"] == matric) & (df["Week"] == week)).any():
        st.warning(f"Attendance already marked for {week}.")
        return True
    df = pd.concat([df, pd.DataFrame([{
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Matric Number": matric, "Name": name, "Week": week
    }])], ignore_index=True)
    df.to_csv(ATTENDANCE_FILE, index=False)
    st.success(f"Attendance marked for {name} ({matric}) - {week}")
    return True

def save_classwork(course_code, name, matric, week, answers):
    CLASSWORK_FILE = get_file(course_code, "classwork_submissions")
    df = pd.read_csv(CLASSWORK_FILE) if os.path.exists(CLASSWORK_FILE) else pd.DataFrame(columns=["Timestamp","Matric Number","Name","Week","Answers"])
    if ((df["Matric Number"] == matric) & (df["Week"] == week)).any():
        st.warning("You’ve already submitted this classwork.")
        return False
    entry = {"Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
             "Matric Number": matric, "Name": name, "Week": week, "Answers": "; ".join(answers)}
    df = pd.concat([df, pd.DataFrame([entry])], ignore_index=True)
    df.to_csv(CLASSWORK_FILE, index=False)
    st.success("✅ Classwork submitted successfully!")
    return True

# PDF and seminar helpers
# -----------------------------
def display_module_pdf(week):
    pdf_path = f"{MODULES_DIR}/{week.replace(' ','_')}.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path,"rb") as f:
            st.download_button(label=f"📥 Download {week} Module PDF", data=f, file_name=f"{week}_module.pdf", mime="application/pdf")
    else:
        st.info("Lecture PDF module not yet uploaded.")
# -----------------------------
# CLASSWORK CONTROL
# -----------------------------
def is_classwork_open(course_code, week):
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork_status")
    if not os.path.exists(CLASSWORK_STATUS_FILE):
        return False
    df = pd.read_csv(CLASSWORK_STATUS_FILE)
    if week not in df["Week"].values:
        return False
    row = df[df["Week"] == week].iloc[0]
    return row["IsOpen"] == 1

def open_classwork(course_code, week):
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork_status")
    now = datetime.now()
    df = pd.read_csv(CLASSWORK_STATUS_FILE) if os.path.exists(CLASSWORK_STATUS_FILE) else pd.DataFrame(columns=["Week","IsOpen","OpenTime"])
    if week in df["Week"].values:
        df.loc[df["Week"]==week, ["IsOpen","OpenTime"]] = [1, now]
    else:
        df = pd.concat([df, pd.DataFrame([{"Week":week,"IsOpen":1,"OpenTime":now}])], ignore_index=True)
    df.to_csv(CLASSWORK_STATUS_FILE, index=False)

def close_classwork_after_20min(course_code):
    CLASSWORK_STATUS_FILE = get_file(course_code, "classwork_status")
    if not os.path.exists(CLASSWORK_STATUS_FILE):
        return
    df = pd.read_csv(CLASSWORK_STATUS_FILE)
    now = datetime.now()
    for idx, row in df.iterrows():
        if row["IsOpen"]==1 and pd.notnull(row["OpenTime"]):
            open_time = pd.to_datetime(row["OpenTime"])
            if (now - open_time).total_seconds() > 20*60:
                df.at[idx,"IsOpen"]=0
                df.at[idx,"OpenTime"]=None
    df.to_csv(CLASSWORK_STATUS_FILE,index=False)
    
def save_file(course_code, name, week, uploaded_file, file_type):
    # Create directory structure
    folder_path = os.path.join("submissions", course_code, file_type)
    os.makedirs(folder_path, exist_ok=True)
    # Save uploaded file
    file_path = os.path.join(folder_path, f"{name}_{week}_{uploaded_file.name}")
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    # Log upload in CSV
    csv_log = os.path.join("records", f"{course_code}_{file_type}_uploads.csv")
    log_df = pd.DataFrame([[datetime.now(), name, week, uploaded_file.name]], 
                          columns=["Timestamp", "Name", "Week", "File"])
    if os.path.exists(csv_log):
        old = pd.read_csv(csv_log)
        log_df = pd.concat([old, log_df], ignore_index=True)
    log_df.to_csv(csv_log, index=False)
    # Log record in CSV
    record_file = os.path.join("submissions", f"{course_code}_submissions.csv")
    record = pd.DataFrame([{
        "Name": name,
        "Week": week,
        "FileName": uploaded_file.name,
        "Type": file_type,
        "Path": file_path
    }])

    if os.path.exists(record_file):
        existing = pd.read_csv(record_file)
        updated = pd.concat([existing, record], ignore_index=True)
        updated.to_csv(record_file, index=False)
    else:
        record.to_csv(record_file, index=False)
        
def mark_attendance(course_code, name, matric, week):
    ATTENDANCE_FILE = get_file(course_code, "attendance")

    # Create file if it doesn't exist
    if not os.path.exists(ATTENDANCE_FILE):
        df = pd.DataFrame(columns=["StudentName", "Matric", "Week", "Status"])
        df.to_csv(ATTENDANCE_FILE, index=False)

    df = pd.read_csv(ATTENDANCE_FILE)

    # Check if attendance already exists
    if ((df["StudentName"].str.lower() == name.strip().lower()) & (df["Week"] == week)).any():
        return False  # Already marked

    # Record new attendance
    new_row = {"StudentName": name.strip(), "Matric": matric.strip(), "Week": week, "Status": "Present"}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(ATTENDANCE_FILE, index=False)
    return True

import os
import pandas as pd
from datetime import datetime

# ============================
# FILE HELPERS
# ============================
def get_score_file(course_code, score_type):
    folder_path = os.path.join("submissions", course_code)
    os.makedirs(folder_path, exist_ok=True)
    return os.path.join(folder_path, f"{score_type}_scores.csv")

# --- Record or Update Student Score ---
def record_score(course_code, score_type, name, matric, week, score, remarks=""):
    score_file = get_score_file(course_code, score_type)
    df = pd.read_csv(score_file) if os.path.exists(score_file) else pd.DataFrame(columns=["StudentName", "Matric", "Week", "Score", "Remarks"])

    # Check existing entry
    existing = (
        (df["Matric"].astype(str).str.lower() == matric.strip().lower()) &
        (df["Week"] == week)
    )
    if existing.any():
        df.loc[existing, ["Score", "Remarks"]] = [score, remarks]
    else:
        new_row = {
            "StudentName": name.strip(),
            "Matric": matric.strip(),
            "Week": week,
            "Score": score,
            "Remarks": remarks,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(score_file, index=False)
    st.success(f"✅ {score_type.capitalize()} score updated for {name} ({week})")

# --- Cached retrieval (auto-refreshable) ---
@st.cache_data(ttl=30)  # cache refreshes every 30 seconds
def get_student_scores(course_code, matric):
    score_types = ["classwork", "seminar", "assignment"]
    results = {}

    for stype in score_types:
        f = get_score_file(course_code, stype)
        if os.path.exists(f):
            df = pd.read_csv(f)
            df = df[df["Matric"].astype(str).str.lower() == matric.strip().lower()]
            results[stype] = df[["Week", "Score"]].to_dict("records")
        else:
            results[stype] = []

    return results

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
    with st.form(f"{course_code}_attendance_form"):
        name = st.text_input("Full Name", key=f"{course_code}_att_name")
        matric = st.text_input("Matric Number", key=f"{course_code}_att_matric")
        week = st.selectbox("Select Lecture Week", lectures_df["Week"].tolist(), key=f"{course_code}_att_week")
        attendance_code = st.text_input("Enter Attendance Code (Ask your lecturer)", key=f"{course_code}_att_code")
        submit_attendance = st.form_submit_button("✅ Mark Attendance", use_container_width=True)

    if submit_attendance:
        if not name.strip() or not matric.strip():
            st.warning("Please enter your full name and matric number.")
        elif not attendance_code.strip():
            st.warning("Please enter the attendance code for today.")
        else:
            COURSE_TIMINGS = {
                "BIO203": {"valid_code": "BIO203-ZT7", "start": "10:00", "end": "14:00"},
                "BCH201": {"valid_code": "BCH201-ZT8", "start": "13:00", "end": "16:00"},
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
                    st.session_state["attended_week"] = week
                else:
                    ok = mark_attendance_entry(course_code, name, matric, week)
                    if ok:
                        st.success(f"✅ Attendance recorded for {name} ({week}).")
                        st.session_state["attended_week"] = week
                        st.experimental_rerun()

    # ---------------------------------------------
    # 📘 Lecture Briefs and Classwork
    # ---------------------------------------------
    st.divider()
    st.subheader("📘 Lecture Briefs and Classwork")
    st.markdown("Here you can view lecture summaries, slides, and classwork materials.")

    lecture_row = pd.DataFrame()

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

        brief = str(lecture_info.get("Brief", "")).strip()
        if brief:
            st.markdown(f"**Lecture Brief:** {brief}")
        else:
            st.info("Lecture brief not available yet.")

        # 🧩 Classwork Section
        classwork_text = str(lecture_info.get("Classwork", "")).strip()
        if classwork_text:
            st.markdown("### 🧩 Classwork Questions")
            questions = [q.strip() for q in classwork_text.split(";") if q.strip()]
            with st.form(f"{course_code}_cw_form"):
                answers = [st.text_input(f"Q{i+1}: {q}", key=f"{course_code}_cw_q{i}") for i, q in enumerate(questions)]
                submit_cw = st.form_submit_button("Submit Answers", disabled=not is_classwork_open(course_code, week))
                if submit_cw:
                    save_classwork(name, matric, week, answers)
                    st.success("✅ Classwork submitted successfully.")
        else:
            st.info("Classwork not yet released.")

        # 📝 Assignment
        assignment = str(lecture_info.get("Assignment", "")).strip()
        if assignment:
            st.subheader("📚 Assignment")
            st.markdown(f"**Assignment:** {assignment}")
        else:
            st.info("Assignment not released yet.")

        # 📥 PDF Download
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

    # ---------------------------------------------
    # 📈 Continuous Assessment Summary
    # ---------------------------------------------
    st.divider()
    st.subheader("📈 Your Continuous Assessment (CA) Summary")

    scores_file = os.path.join("scores", f"{course_code.lower()}_scores.csv")
    if os.path.exists(scores_file):
        df_scores = pd.read_csv(scores_file)
        if name.strip() and matric.strip():
            student_scores = df_scores[
                (df_scores["StudentName"].str.lower() == name.strip().lower()) &
                (df_scores["MatricNo"].str.lower() == matric.strip().lower())
            ] if ("StudentName" in df_scores.columns and "MatricNo" in df_scores.columns) else pd.DataFrame()

            if not student_scores.empty:
                cw_total = student_scores.get("ClassworkScore", pd.Series([0])).mean()
                sem_total = student_scores.get("SeminarScore", pd.Series([0])).mean()
                ass_total = student_scores.get("AssignmentScore", pd.Series([0])).mean()
                total_CA = (cw_total * 0.3) + (sem_total * 0.2) + (ass_total * 0.5)

                st.dataframe(student_scores, use_container_width=True)
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
                st.info("No scores found yet.")
        else:
            st.info("Enter your name & matric above to see your CA summary.")
    else:
        st.warning("📁 Scores file not yet available for this course.")

    # ===============================================================
    # 📄 ASSIGNMENT, DRAWING & SEMINAR UPLOADS
    # ===============================================================
    st.divider()
    st.subheader("📄 Assignment, Drawing & Seminar Uploads")

    # 📝 Assignment
    selected_week_a = st.selectbox("Select Week for Assignment", lectures_df["Week"].tolist(), key=f"{course_code}_a_week")
    student_name_a = st.text_input("Full Name", key=f"{course_code}_a_name")
    matric_a = st.text_input("Matric Number", key=f"{course_code}_a_matric")
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
    selected_week_d = st.selectbox("Select Week for Drawing", lectures_df["Week"].tolist(), key=f"{course_code}_d_week")
    student_name_d = st.text_input("Full Name", key=f"{course_code}_d_name")
    matric_d = st.text_input("Matric Number", key=f"{course_code}_d_matric")
    uploaded_drawing = st.file_uploader("Upload Drawing", type=["pdf", "jpg", "png"], key=f"{course_code}_d_file")

    if st.button(f"📤 Submit Drawing", key=f"{course_code}_d_btn"):
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
    selected_week_s = st.selectbox("Select Week for Seminar", lectures_df["Week"].tolist(), key=f"{course_code}_s_week")
    student_name_s = st.text_input("Full Name", key=f"{course_code}_s_name")
    matric_s = st.text_input("Matric Number", key=f"{course_code}_s_matric")
    uploaded_seminar = st.file_uploader("Upload Seminar", type=["pdf", "pptx", "docx"], key=f"{course_code}_s_file")

    if st.button(f"📤 Submit Seminar", key=f"{course_code}_s_btn"):
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
    lecture_to_edit = st.selectbox("Select Lecture", lectures_df["Week"].unique(), key="Admin_select_lecture")
    row_idx = lectures_df[lectures_df["Week"] == lecture_to_edit].index[0]
    brief = st.text_area("Lecture Brief", value=lectures_df.at[row_idx, "Brief"], key="admin_brief")
    assignment = st.text_area("Assignment", value=lectures_df.at[row_idx, "Assignment"], key="Admin_assignment")
    classwork = st.text_area("Classwork (Separate questions with ;)", 
    value=lectures_df.at[row_idx, "Classwork"], key="Admin_classwork")

    if st.button("💾 Update Lecture", key="Admin_update_lecture"):
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

























