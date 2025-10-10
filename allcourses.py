import streamlit as st
import pandas as pd
import os
import re
from datetime import datetime, date, timedelta
import streamlit as st



# Hide default Streamlit elements & GitHub link, then add custom footer
st.markdown("""
<style>
/* Hide Streamlit default UI */
footer {visibility: hidden;}
#MainMenu {visibility: hidden;}

/* Hide GitHub repo link/button */
a[href*="github.com"] {
    display: none !important;
}

/* Hide viewer badge */
.viewerBadge_container__1QSob,
.viewerBadge_link__1S137,
.viewerBadge_text__1JaDK {
    display: none !important;
}

/* Custom footer */
.custom-footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background-color: #f0f2f6;
    color: #333333;
    text-align: center;
    padding: 8px;
    font-size: 15px;
    font-weight: 500;
    border-top: 1px solid #cccccc;
}
</style>

<div class="custom-footer">
    Developed by <b>Mide</b> | © 2025 | 
    <a href="https://example.com" target="_blank" style="text-decoration:none; color:#1f77b4;">
        Visit our website
    </a>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# CONFIGURATION
# -----------------------------
COURSES = {
    "MCB 221 – General Microbiology": "MCB221",
    "BCH 201 – General Biochemistry": "BCH201",
    "BIO 203 – General Physiology": "BIO203"
}

MODULES_DIR = "modules"
os.makedirs(MODULES_DIR, exist_ok=True)

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
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

def save_file(course_code, name, week, uploaded_file, submission_type):
    folder = f"submissions/{course_code}/{submission_type}"
    os.makedirs(folder, exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    ext = uploaded_file.name.split('.')[-1]
    save_path = f"{folder}/{safe_name}_week{week}_{submission_type}.{ext}"
    with open(save_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    st.success(f"✅ {submission_type.capitalize()} uploaded successfully as {uploaded_file.name}")

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

# -----------------------------
# LAYOUT
# -----------------------------
st.set_page_config(page_title="Multi-Course Dashboard", page_icon="📚", layout="wide")
st.subheader("Department of Biological Sciences Sikiru Adetona College of Education Omu-Ijebu")
st.title("📚 Multi-Course Portal")
course = st.selectbox("Select Course:", list(COURSES.keys()))
course_code = COURSES[course]

mode = st.radio("Select Mode:", ["Student", "Teacher/Admin"])

# Initialize lectures for each course
default_topics = [f"Lecture Topic {i+1}" for i in range(12)]  # Replace with actual topics
lectures_df = init_lectures(course_code, default_topics)

import os
import pandas as pd
import streamlit as st
from datetime import datetime

# Example placeholder paths
MODULES_DIR = "modules"  # folder containing PDFs
valid_code = "BIO203-OK3"  # change each lecture

# -----------------------------
# STUDENT MODE
# -----------------------------
if mode == "Student":
    st.subheader(f"🎓 {course} Student Access")

    # Attendance form
    with st.form(f"{course_code}_attendance_form"):
        name = st.text_input("Full Name")
        matric = st.text_input("Matric Number")
        week = st.selectbox("Select Lecture Week", lectures_df["Week"].tolist())
        attendance_code = st.text_input("Enter Attendance Code (Ask your lecturer)")
        submit_attendance = st.form_submit_button("✅ Mark Attendance")

    # Attendance submission logic
    if submit_attendance:
        if not name.strip() or not matric.strip():
            st.warning("Please enter your full name and matric number.")
        elif not attendance_code.strip():
            st.warning("Please enter the attendance code for today.")
        else:
            start_time = datetime.strptime("10:00", "%H:%M").time()  # Start time
            end_time = datetime.strptime("12:00", "%H:%M").time()    # End time
            now = datetime.now().time()

            if not (start_time <= now <= end_time):
                st.error("⏰ Attendance can only be marked between 10:00 AM and 12:00 PM.")
            elif attendance_code != valid_code:
                st.error("❌ Invalid attendance code. Ask your lecturer for today’s code.")
            else:
                # Mark attendance and store attended week in session
                mark_attendance(course_code, name, matric, week)
                st.session_state["attended_week"] = week
                st.success(f"✅ Attendance recorded for {name} ({week}).")

    # --- Automatically show lecture info once attendance is successful ---
    if "attended_week" in st.session_state:
        week = st.session_state["attended_week"]
        lecture_row = lectures_df[lectures_df["Week"] == week]

        if lecture_row.empty:
            st.error(f"No lecture data found for {week}.")
        else:
            lecture_info = lecture_row.iloc[0]
            st.markdown("---")
            st.subheader(f"📖 {week}: {lecture_info['Topic']}")

            # Safely extract content
            brief = str(lecture_info["Brief"]) if pd.notnull(lecture_info["Brief"]) else ""
            assignment = str(lecture_info["Assignment"]) if pd.notnull(lecture_info["Assignment"]) else ""
            classwork_text = str(lecture_info["Classwork"]) if pd.notnull(lecture_info["Classwork"]) else ""

            # Display sections
            if brief.strip():
                st.write(f"**Lecture Brief:** {brief}")

            if classwork_text.strip():
                st.write(f"**Classwork:** {classwork_text}")

            if assignment.strip():
                st.write(f"**Assignment:** {assignment}")

            # Show attached lecture note if available
            pdf_path = os.path.join(MODULES_DIR, f"{course_code}_{week.replace(' ', '_')}.pdf")

            if os.path.exists(pdf_path):
                st.markdown("### 📘 Lecture Note")
                with open(pdf_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()
                st.download_button(
                    label="📥 Download Lecture PDF",
                    data=pdf_bytes,
                    file_name=f"{course_code}_{week}.pdf",
                    mime="application/pdf"
                )
            else:
                st.info("Lecture note not uploaded yet.")
                st.rerun()

    # Assignment upload
    st.divider()
    st.subheader("📄 Assignment Upload")
    uploaded_assignment = st.file_uploader(f"Upload Assignment for {week}", type=["pdf","docx","jpg","png"], key=f"{course_code}_assignment")
    if uploaded_assignment and st.button(f"Submit Assignment for {week}"):
        save_file(course_code, name, week, uploaded_assignment, "assignment")

    # Classwork
    if classwork_text.strip():
        st.divider()
        st.subheader("🧩 Classwork Questions")
        questions = [q.strip() for q in classwork_text.split(";") if q.strip()]
        with st.form(f"{course_code}_cw_form"):
            answers = [st.text_input(f"Q{i+1}: {q}") for i,q in enumerate(questions)]
            submit_cw = st.form_submit_button("Submit Answers", disabled=not is_classwork_open(course_code, week))
            if submit_cw: save_classwork(course_code, name, matric, week, answers)

    # Drawing Upload
    st.divider()
    st.subheader("🖌️ Drawing Upload")
    student_name = st.text_input("Enter your full name", key="student_name_input")
    uploaded_drawing = st.file_uploader(f"Upload Drawing for {week}", type=["jpg","jpeg","png","pdf"], key=f"{course_code}_drawing")
    if uploaded_drawing and st.button(f"Submit Drawing for {week}"):
        save_file(course_code, name, week, uploaded_drawing, "drawing")

    # Seminar Upload
    st.divider()
    st.subheader("🎤 Seminar Upload")
    uploaded_seminar = st.file_uploader("Upload Seminar PPT", type=["ppt","pptx"], key=f"{course_code}_seminar")
    if uploaded_seminar and st.button(f"Submit Seminar for {week}"):
        save_file(course_code, name, week, uploaded_seminar, "seminar")

# -----------------------------
# TEACHER/ADMIN MODE
# -----------------------------
if mode=="Teacher/Admin":
    st.subheader("🔐 Teacher/Admin Panel")
    password = st.text_input("Enter Admin Password", type="password")
    ADMIN_PASS = "bimpe2025class"

    if password == ADMIN_PASS:
        st.success(f"✅ Logged in as Admin for {course}")

        # Edit lecture briefs, assignments, classwork
        lecture_to_edit = st.selectbox("Select Lecture", lectures_df["Week"].unique())
        row_idx = lectures_df[lectures_df["Week"]==lecture_to_edit].index[0]
        brief = st.text_area("Lecture Brief", value=lectures_df.at[row_idx,"Brief"])
        assignment = st.text_area("Assignment", value=lectures_df.at[row_idx,"Assignment"])
        classwork = st.text_area("Classwork (Separate questions with ;)", value=lectures_df.at[row_idx,"Classwork"])
        if st.button("💾 Update Lecture"):
            lectures_df.at[row_idx,"Brief"]=brief
            lectures_df.at[row_idx,"Assignment"]=assignment
            lectures_df.at[row_idx,"Classwork"]=classwork
            lectures_df.to_csv(get_file(course_code,"lectures"),index=False)
            st.success(f"{lecture_to_edit} updated successfully!")

        # Upload lecture PDFs
        st.divider()
        st.subheader("📄 Upload Lecture PDF Module")
        pdf_file = st.file_uploader("Upload Lecture Module", type=["pdf"])
        if pdf_file:
            pdf_path = os.path.join(MODULES_DIR, f"{course_code}_{lecture_to_edit.replace(' ','_')}.pdf")
            with open(pdf_path,"wb") as f: f.write(pdf_file.getbuffer())
            st.success(f"✅ PDF uploaded for {lecture_to_edit}")

        # Open/Close classwork
        st.divider()
        st.subheader("📚 Classwork Control")
        week_to_control = st.selectbox("Select Week to Open/Close Classwork", lectures_df["Week"].unique(), key="cw_control")
        if st.button(f"Open Classwork for {week_to_control} (20 mins)"):
            open_classwork(course_code, week_to_control)
            st.success(f"Classwork for {week_to_control} is now open for 20 minutes.")
        close_classwork_after_20min(course_code)

        # View records
        st.divider()
        for file, label in [("attendance","Attendance Records"),
                            ("classwork_submissions","Classwork Submissions")]:
            csv_file = get_file(course_code,file)
            st.markdown(f"### {label}")
            if os.path.exists(csv_file):
                df = pd.read_csv(csv_file)
                st.dataframe(df)
                st.download_button(f"Download {label} CSV", df.to_csv(index=False).encode(), csv_file)
            else:
                st.info(f"No {label.lower()} yet.")
    else:
        if password: st.error("❌ Incorrect password")













