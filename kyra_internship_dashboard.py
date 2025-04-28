
# --- Imports ---
import streamlit as st
import sqlite3
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from reportlab.pdfgen import canvas
import tempfile
import base64
import io

# --- Streamlit Config ---
st.set_page_config(page_title="Ky'ra Internship Dashboard", layout="wide", initial_sidebar_state="expanded")
sns.set_style("whitegrid")

# --- Database Connection ---
@st.cache_resource
def get_connection():
    db_path = os.path.join(os.getcwd(), "internship_tracking.db")
    if "STREAMLIT_CLOUD" in os.environ:
        db_path = os.path.join("/tmp", "internship_tracking.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn

@st.cache_data
def initialize_database():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS internships (
            internship_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            company_name TEXT NOT NULL,
            duration TEXT NOT NULL,
            feedback TEXT,
            msme_digitalized INTEGER DEFAULT 0,
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            rating INTEGER,
            comments TEXT,
            FOREIGN KEY (student_id) REFERENCES students (student_id)
        )
    """)
    conn.commit()
    conn.close()

# --- Database Operations ---
def register_student(name, email):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR IGNORE INTO students (name, email) VALUES (?, ?)", (name, email))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Error registering student: {e}")
        return False

def log_internship(email, company, duration, feedback, msme_digitalized):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id FROM students WHERE email = ?", (email,))
        result = cur.fetchone()
        if result:
            student_id = result[0]
            cur.execute("""
                INSERT INTO internships (student_id, company_name, duration, feedback, msme_digitalized) 
                VALUES (?, ?, ?, ?, ?)
            """, (student_id, company, duration, feedback, msme_digitalized))
            conn.commit()
            conn.close()
            return True
        else:
            st.error("Student email not found.")
            return False
    except sqlite3.Error as e:
        st.error(f"Error logging internship: {e}")
        return False

def log_feedback(student_id, rating, comments):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO feedback (student_id, rating, comments) 
            VALUES (?, ?, ?)
        """, (student_id, rating, comments))
        conn.commit()
        conn.close()
        return True
    except sqlite3.Error as e:
        st.error(f"Error logging feedback: {e}")
        return False

def fetch_student_data(email):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id, name FROM students WHERE email = ?", (email,))
        student = cur.fetchone()
        if student:
            cur.execute("""
                SELECT company_name, duration, feedback, msme_digitalized 
                FROM internships WHERE student_id = ?
            """, (student[0],))
            internships = cur.fetchall()
            conn.close()
            return {"student_id": student[0], "name": student[1], "internships": internships}
        conn.close()
        return None
    except sqlite3.Error as e:
        st.error(f"Error fetching student data: {e}")
        return None

def fetch_reports():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT s.name, s.email, i.company_name, i.duration, i.feedback, i.msme_digitalized
            FROM students s
            JOIN internships i ON s.student_id = i.student_id
        """)
        data = cur.fetchall()
        conn.close()
        return data
    except sqlite3.Error as e:
        st.error(f"Error fetching reports: {e}")
        return []

def fetch_metrics():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM internships")
        total_internships = cur.fetchone()[0]
        cur.execute("SELECT SUM(msme_digitalized) FROM internships")
        total_msmes = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(DISTINCT student_id) FROM internships")
        certifications_issued = cur.fetchone()[0]
        conn.close()
        return {
            "total_internships": total_internships,
            "total_msmes": total_msmes,
            "certifications_issued": certifications_issued
        }
    except sqlite3.Error as e:
        st.error(f"Error fetching metrics: {e}")
        return {}

# --- Helper Functions ---
def generate_pdf_report(data):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf_path = tmp.name
    c = canvas.Canvas(pdf_path)
    c.setFont("Helvetica", 12)
    y = 800
    for row in data:
        text = f"Name: {row[0]}, Email: {row[1]}, Company: {row[2]}, Duration: {row[3]}, Feedback: {row[4]}, MSMEs Digitalized: {row[5]}"
        c.drawString(30, y, text)
        y -= 20
        if y < 40:
            c.showPage()
            y = 800
    c.save()
    return pdf_path

def plot_internship_progress(internships):
    if not internships:
        return None
    df = pd.DataFrame(internships, columns=["Company", "Duration", "Feedback", "MSMEs Digitalized"])
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.barplot(x=df.index, y=df["MSMEs Digitalized"], hue=df["Company"], ax=ax)
    ax.set_title("MSMEs Digitalized per Internship")
    ax.set_xlabel("Internship")
    ax.set_ylabel("MSMEs Digitalized")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode()

# --- Initialize Database ---
initialize_database()

# --- Streamlit UI ---
st.title("🌟 Ky'ra: Your Internship Journey Mentor")

# Welcome or Main Page
if "page" not in st.session_state:
    st.session_state.page = "Welcome"

if st.session_state.page == "Welcome":
    st.header("Welcome to Ky'ra! 🎉")
    st.write("""
        Ky'ra is your personal mentor to guide you through your internship journey:
        - **Register**: Create your profile.
        - **Log Internships**: Track your experiences.
        - **View Progress**: See your growth.
        - **Give Feedback**: Help improve Ky'ra!
    """)
    if st.button("Get Started"):
        st.session_state.page = "Main"

if st.session_state.page == "Main":
    st.sidebar.header("Your Journey")
    menu = ["Your Progress", "Log Internship", "Opportunities", "Feedback", "Generate Report"]
    choice = st.sidebar.selectbox("Navigate", menu)

    email_input = st.sidebar.text_input("Enter your email to personalize")
    student_data = None
    if email_input:
        student_data = fetch_student_data(email_input)
        if student_data:
            total_internships = len(student_data["internships"])
            message = (
                "You're just starting! Log your first internship!" if total_internships == 0 else
                f"Wow, {total_internships} internship{'s' if total_internships > 1 else ''}! Keep it up!"
            )
            st.sidebar.success(f"Hi {student_data['name']}! {message}")

    metrics = fetch_metrics()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Internships Completed", metrics.get("total_internships", 0))
    with col2:
        st.metric("MSMEs Supported", metrics.get("total_msmes", 0))
    with col3:
        st.metric("Certifications Issued", metrics.get("certifications_issued", 0))

    if choice == "Your Progress":
        st.header("📊 Your Progress")
        if student_data and student_data["internships"]:
            internships = student_data["internships"]
            total = len(internships)
            msmes = sum([int(i[3]) for i in internships])
            progress = min(total * 10, 100)
            st.progress(progress / 100)
            st.write(f"Internship Completion: {progress}%")
            if total >= 1:
                st.success("🎉 Badge: First Internship Completed!")
            if total >= 3:
                st.success("🚀 Badge: Internship Pro!")
            if msmes >= 5:
                st.success("🏆 Badge: Top Performer!")
            plot_data = plot_internship_progress(internships)
            if plot_data:
                st.image(f"data:image/png;base64,{plot_data}", caption="MSMEs Digitalized per Internship")
        else:
            st.info("No internships logged yet.")

    elif choice == "Log Internship":
        st.header("🛠️ Log Internship")
        email = st.text_input("Student Email")
        company = st.text_input("Company Name")
        duration = st.text_input("Duration (e.g., 3 months)")
        feedback = st.text_area("Feedback")
        msme_digitalized = st.number_input("MSMEs Digitalized", min_value=0)
        if st.button("Submit Internship"):
            if email and company and duration:
                if log_internship(email, company, duration, feedback, msme_digitalized):
                    st.success("Internship logged successfully!")
            else:
                st.error("Fill in all required fields.")

    elif choice == "Opportunities":
        st.header("🚀 Opportunities")
        st.write("Exciting internship opportunities coming soon!")

    elif choice == "Feedback":
        st.header("🗣️ Share Your Feedback")
        if student_data:
            st.subheader("Rate Your Experience")
            feedback_type = st.radio("Choose feedback method:", ["Star Rating", "Emoji Scale"])
            if feedback_type == "Star Rating":
                rating = st.slider("How was your experience today?", 1, 5, 3)
                comments = st.text_area("Comments")
                if st.button("Submit Feedback"):
                    if log_feedback(student_data["student_id"], rating, comments):
                        st.success("Thank you for your feedback!")
            else:
                emoji_ratings = {"😊": 5, "🙂": 3, "😔": 1}
                emoji = st.selectbox("How do you feel?", list(emoji_ratings.keys()))
                comments = st.text_area("Comments (optional)")
                if st.button("Submit Emoji Feedback"):
                    rating = emoji_ratings[emoji]
                    if log_feedback(student_data["student_id"], rating, comments):
                        st.success("Thanks for your feedback!")

    elif choice == "Generate Report":
        st.header("📄 Generate Report")
        report_data = fetch_reports()
        if report_data:
            pdf_path = generate_pdf_report(report_data)
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            b64_pdf = base64.b64encode(pdf_bytes).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="internship_report.pdf">📥 Download Report</a>'
            st.markdown(href, unsafe_allow_html=True)
        else:
            st.info("No report data available yet.")
