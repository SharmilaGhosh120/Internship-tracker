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
    cur.close()

# --- Main UI ---
initialize_database()

st.title("🌟 Ky'ra: Your Internship Journey Mentor")

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
        with st.spinner("Fetching your profile..."):
            student_data = fetch_student_data(email_input)
        if student_data:
            total_internships = len(student_data["internships"])
            st.sidebar.success(
                f"Hi {student_data['name']}! You have logged {total_internships} internship{'s' if total_internships > 1 else ''}! 🚀"
            )

    metrics = fetch_metrics()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Internships Completed", metrics.get("total_internships", 0))
    with col2:
        st.metric("MSMEs Supported", metrics.get("total_msmes", 0))
    with col3:
        st.metric("Certifications Issued", metrics.get("certifications_issued", 0))

    if choice == "Log Internship":
        st.header("🛠️ Log Internship")
        email = st.text_input("Student Email")
        company = st.text_input("Company Name")
        duration = st.text_input("Duration (e.g., 3 months)")
        feedback = st.text_area("Feedback")
        msme_digitalized = st.number_input("MSMEs Digitalized", min_value=0)
        if st.button("Submit Internship"):
            if email and company and duration:
                with st.spinner("Saving your internship..."):
                    success = log_internship(email, company, duration, feedback, msme_digitalized)
                if success:
                    st.success("Internship logged successfully!")
                    st.balloons()
            else:
                st.error("Please fill in all required fields.")

    if choice == "Generate Report":
        st.header("📄 Generate Report")
        with st.spinner("Generating your internship report..."):
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

    if choice == "Opportunities":
        st.header("🚀 Opportunities")
        st.info("More internship opportunities coming soon!")

    if choice == "Feedback":
        st.header("🗣️ Share Your Feedback")
        if student_data:
            st.subheader("Rate Your Experience")
            feedback_type = st.radio("Choose feedback method:", ["Star Rating", "Emoji Scale"])
            if feedback_type == "Star Rating":
                rating = st.slider("Rate your experience", 1, 5, 3)
                comments = st.text_area("Comments")
                if st.button("Submit Feedback"):
                    with st.spinner("Submitting feedback..."):
                        if log_feedback(student_data["student_id"], rating, comments):
                            st.success("Thanks for your feedback! 🌟")
            else:
                emoji_ratings = {"😊": 5, "🙂": 3, "😔": 1}
                emoji = st.selectbox("How do you feel?", list(emoji_ratings.keys()))
                comments = st.text_area("Comments (optional)")
                if st.button("Submit Emoji Feedback"):
                    with st.spinner("Submitting emoji feedback..."):
                        rating = emoji_ratings[emoji]
                        if log_feedback(student_data["student_id"], rating, comments):
                            st.success("Thanks for your emoji feedback! 🎉")

