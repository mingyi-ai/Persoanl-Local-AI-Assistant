# Job Tracker Page
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from core.database.base import get_db
from core.controllers.job_posting_controller import JobPostingController
from core.controllers.application_controller import ApplicationController
from core.ui.displays import display_applications_table
from core.ui.job_tracker_ui import (
    render_add_job_posting_section,
    render_application_management_section,
    filter_applications
)

st.set_page_config(layout="wide", page_title="Job Tracker")
st.title("Job Application Tracker")

# Initialize database session and controllers in Streamlit session state
if 'db' not in st.session_state:
    try:
        st.session_state.db = next(get_db())
        st.session_state.job_posting_controller = JobPostingController()
        st.session_state.application_controller = ApplicationController()
    except StopIteration:
        st.error("Could not connect to database. Please try again.")
        st.stop()

# Get DB session and controllers from state
db: Session = st.session_state.db
job_posting_controller = st.session_state.job_posting_controller
application_controller = st.session_state.application_controller

# --- Session State Initialization ---
if 'selected_app_id_tracker' not in st.session_state:
    st.session_state.selected_app_id_tracker = None
if 'show_add_job_posting_form' not in st.session_state:
    st.session_state.show_add_job_posting_form = False

# --- Function to refresh applications --- 
def refresh_applications_display_data(db: Session) -> pd.DataFrame:
    """Fetches applications with their latest status for display."""
    result = application_controller.get_application_list(db)
    if result["success"] and result["applications"]:
        df = pd.DataFrame(result["applications"])
        # Fill NA values for better display
        df['current_status'] = df['current_status'].fillna('No Status')
        df['status_timestamp'] = df['status_timestamp'].fillna('')
        df['resume_name'] = df['resume_name'].fillna('No Resume')
        df['cover_letter_name'] = df['cover_letter_name'].fillna('No Cover Letter')
        df['submission_method'] = df['submission_method'].fillna('Not Specified')
        df['job_location'] = df['job_location'].fillna('Not Specified')
        return df
    return pd.DataFrame() # Return empty DataFrame if no data

applications_display_df = refresh_applications_display_data(db)

# --- Search and Filter ---
st.sidebar.header("Filter & Search Applications")
search_term = st.sidebar.text_input(
    "Search by Job Title, Company", 
    key="search_apps_tracker"
)

# Get status options
status_options = ["All"]
if not applications_display_df.empty and 'current_status' in applications_display_df.columns:
    unique_statuses = applications_display_df["current_status"].dropna().unique().tolist()
    status_options.extend(sorted(unique_statuses))
else:
    status_options.extend(['submitted', 'interview', 'rejected', 'offer'])

selected_status_filter = st.sidebar.selectbox(
    "Filter by Status", 
    options=status_options, 
    key="filter_status_tracker"
)

# Apply filters
filtered_display_df = filter_applications(
    applications_display_df,
    search_term,
    selected_status_filter
)

# --- Display Applications Table ---
st.header("Current Applications")
display_columns = [
    'application_id', 'job_title', 'job_company', 'job_date_submitted',
    'resume_name', 'cover_letter_name', 'submission_method',
    'current_status', 'status_timestamp'
]
display_applications_table(filtered_display_df, display_columns)

st.divider()

# --- Manage Selected Application ---
st.header("Manage Application")

if not filtered_display_df.empty:
    app_id_options = filtered_display_df['application_id'].tolist()
    selected_app_id_for_management = st.selectbox(
        "Select Application ID to Manage", 
        options=app_id_options, 
        key="app_id_manage_tracker", 
        index=None, 
        placeholder="Choose an application ID"
    )

    if selected_app_id_for_management:
        render_application_management_section(
            db,
            selected_app_id_for_management,
            application_controller,
            job_posting_controller
        )
else:
    st.caption("No applications to select for management.")

st.divider()

# --- Add New Job Posting & Application ---
render_add_job_posting_section(db, job_posting_controller, application_controller)

st.divider()
