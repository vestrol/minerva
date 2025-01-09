import streamlit as st
from datetime import date
import pandas as pd
import plotly.express as px
from google.cloud import firestore
from google.oauth2 import service_account
import json

key_dict = json.loads(st.secrets["textkey"])
creds = service_account.Credentials.from_service_account_info(key_dict)
db = firestore.Client(credentials=creds, project="minerva-aba90")

def get_mentors():
    mentors = db.collection('mentors').get()
    return [mentor.to_dict()['name'] for mentor in mentors]

def get_scholars(mentor):
    scholars = db.collection('scholars').where('mentor', '==', mentor).get()
    return [scholar.to_dict()['name'] for scholar in scholars]

def verify_password(mentor, password):
    mentor_doc = db.collection('mentors').where('name', '==', mentor).get()[0]
    hashed_password = mentor_doc.to_dict()['password']
    return password == hashed_password

def save_check_in(data):
    db.collection('check_ins').add(data)

def add_scholar_to_db(name, mentor):
    db.collection('scholars').add({"name": name, "mentor": mentor})
    st.success(f"Scholar '{name}' has been added successfully!")

def fetch_analytics(mentor=None, scholar=None, date_start=None, date_end=None):
    query = db.collection('check_ins')
    if mentor:
        query = query.where('mentor', '==', mentor)
    if scholar:
        query = query.where('scholar', '==', scholar)
    if date_start and date_end:
        query = query.where('date', '>=', date_start).where('date', '<=', date_end)
    results = query.get()
    return [doc.to_dict() for doc in results]

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Check-in Form", "Analytics"])

if page == "Check-in Form":
    st.title("Missed Check-in Form")

    mentors = get_mentors()
    selected_mentor = st.selectbox("Select Mentor", mentors)

    password = st.text_input("Password", type="password")

    check_in_date = st.date_input("Date of Check-in", value=date.today())
    date_str = check_in_date.strftime("%Y-%m-%d")
    scholars = get_scholars(selected_mentor)
    scholars.append("Add Scholar")  # Add option to Scholar list

    selected_scholar = st.selectbox("Select Scholar", scholars)

    if selected_scholar == "Add Scholar":
        new_scholar_name = st.text_input("Enter the name of the new Scholar")
        reason_options = ["Exams", "Travelling", "Unwell", "Postponed", "Other"]
        selected_reason = st.selectbox("Reason for Check-in not done", reason_options)
        other_reason = ""
        if selected_reason == "Other":
            other_reason = st.text_input("Specify other reason")
        if st.button("Submit"):
            if new_scholar_name.strip():
                add_scholar_to_db(new_scholar_name, selected_mentor)
            else:
                st.error("Please enter a valid Scholar name.")

            if verify_password(selected_mentor, password):
                data = {
                    "mentor": selected_mentor,
                    "scholar": new_scholar_name,
                    "date": date_str,
                    "reason": selected_reason,
                    "other_reason": other_reason
                }
                save_check_in(data)
                st.success("Check-in submitted successfully!")
            else:
                st.error("Invalid password. Please try again.")
    else:
        reason_options = ["Exams", "Travelling", "Unwell", "Postponed", "Other"]
        selected_reason = st.selectbox("Reason for Check-in not done", reason_options)
        other_reason = ""
        if selected_reason == "Other":
            other_reason = st.text_input("Specify other reason")

        if st.button("Submit"):
            if verify_password(selected_mentor, password):
                data = {
                    "mentor": selected_mentor,
                    "scholar": selected_scholar,
                    "date": date_str,
                    "reason": selected_reason,
                    "other_reason": other_reason
                }
                save_check_in(data)
                st.success("Check-in submitted successfully!")
            else:
                st.error("Invalid password. Please try again.")

elif page == "Analytics":
    st.title("Analytics")

    # Filters
    mentors = ["All"] + get_mentors()
    selected_mentor = st.sidebar.selectbox("Filter by Mentor", mentors)

    scholars = ["All"]
    if selected_mentor != "All":
        scholars += get_scholars(selected_mentor)
    selected_scholar = st.sidebar.selectbox("Filter by Scholar", scholars)

    date_start = st.sidebar.date_input("Start Date", value=None)
    date_end = st.sidebar.date_input("End Date", value=None)

    # Apply filters
    mentor_filter = None if selected_mentor == "All" else selected_mentor
    scholar_filter = None if selected_scholar == "All" else selected_scholar
    date_start_str = date_start.strftime("%Y-%m-%d") if date_start else None
    date_end_str = date_end.strftime("%Y-%m-%d") if date_end else None

    data = fetch_analytics(mentor=mentor_filter, scholar=scholar_filter, date_start=date_start_str, date_end=date_end_str)

    if data:
        df = pd.DataFrame(data)
        # st.dataframe(df)
        col = st.columns(3)
        # KPIs
        st.subheader("Key Performance Indicators")
        col[0].metric("Total Check-ins", len(df))
        col[1].metric("Unique Mentors", df['mentor'].nunique())
        col[2].metric("Unique Scholars", df['scholar'].nunique())

        # Interactive Visualizations
        if 'date' in df.columns:
            st.subheader("Check-ins Over Time")
            counts_by_date = df['date'].value_counts().reset_index()
            counts_by_date.columns = ['Date', 'Check-ins']
            fig = px.bar(counts_by_date, x='Date', y='Check-ins', title="Check-ins Over Time")
            st.plotly_chart(fig)

        if 'mentor' in df.columns:
            st.subheader("Check-ins by Mentor")
            counts_by_mentor = df['mentor'].value_counts().reset_index()
            counts_by_mentor.columns = ['Mentor', 'Check-ins']
            fig = px.bar(counts_by_mentor, x='Mentor', y='Check-ins', title="Check-ins by Mentor")
            st.plotly_chart(fig)

        if 'scholar' in df.columns:
            st.subheader("Check-ins by Scholar")
            counts_by_scholar = df['scholar'].value_counts().reset_index()
            counts_by_scholar.columns = ['Scholar', 'Check-ins']
            fig = px.bar(counts_by_scholar, x='Scholar', y='Check-ins', title="Check-ins by Scholar")
            st.plotly_chart(fig)

    else:
        st.info("No data found for the selected filters.")
