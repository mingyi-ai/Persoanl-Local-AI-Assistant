# Job Tracker Page
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
from core.database.base import get_db
from core.database import job_tracker_utils as db_utils
from core.database import models, schemas
from core.database.crud import (
    create_file, create_job_posting, create_application,
    create_status_history, get_application, get_job_posting,
    get_file_by_hash
)
from core.file_utils import save_uploaded_file, get_file_hash 

st.set_page_config(layout="wide", page_title="Job Tracker")
st.title("Job Application Tracker")

# Initialize database session in Streamlit session state
if 'db' not in st.session_state:
    try:
        st.session_state.db = next(get_db())
    except StopIteration:
        st.error("Could not connect to database. Please try again.")
        st.stop()

# Get DB session from state
db: Session = st.session_state.db

# --- Session State Initialization (Adjust as needed for new schema) ---
if 'selected_app_id_tracker' not in st.session_state:
    st.session_state.selected_app_id_tracker = None
if 'show_add_job_posting_form' not in st.session_state:
    st.session_state.show_add_job_posting_form = False

# --- Function to refresh applications --- 
def refresh_applications_display_data(db: Session) -> pd.DataFrame:
    """Fetches applications with their latest status for display."""
    apps_data = db_utils.get_applications_with_latest_status(db)
    if apps_data:
        df = pd.DataFrame(apps_data)
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

# --- Search and Filter (Adjust for new DataFrame columns) ---
st.sidebar.header("Filter & Search Applications")
search_term = st.sidebar.text_input(
    "Search by Job Title, Company", 
    key="search_apps_tracker"
)

# Dynamically get status options from the displayed data or a predefined list
status_options = ["All"]
if not applications_display_df.empty and 'current_status' in applications_display_df.columns:
    unique_statuses = applications_display_df["current_status"].dropna().unique().tolist()
    status_options.extend(sorted(unique_statuses))
else: # Fallback if no applications or status column is missing
    status_options.extend(['submitted', 'interview', 'rejected', 'offer'])

selected_status_filter = st.sidebar.selectbox(
    "Filter by Status", 
    options=status_options, 
    key="filter_status_tracker"
)

filtered_display_df = applications_display_df.copy()

if search_term:
    # Adjust search logic for new column names (e.g., 'job_title', 'job_company')
    search_conditions = (
        filtered_display_df["job_title"].astype(str).str.contains(search_term, case=False, na=False) |
        filtered_display_df["job_company"].astype(str).str.contains(search_term, case=False, na=False)
    )
    # Add more fields to search if necessary
    filtered_display_df = filtered_display_df[search_conditions]

if selected_status_filter != "All":
    filtered_display_df = filtered_display_df[filtered_display_df["current_status"] == selected_status_filter]

# --- Display Applications Table ---
st.header("Current Applications")
if not filtered_display_df.empty:
    st.info(f"Displaying {len(filtered_display_df)} of {len(applications_display_df)} applications.")
    # Select and order columns for display from filtered_display_df
    # Example: display_columns = ['application_id', 'job_title', 'job_company', 'job_date_submitted', 'current_status']
    display_columns = [col for col in ['application_id', 'job_title', 'job_company', 'job_date_submitted', 'resume_name', 'cover_letter_name', 'submission_method', 'current_status', 'status_timestamp'] if col in filtered_display_df.columns]
    
    st.dataframe(filtered_display_df[display_columns], use_container_width=True, hide_index=True)

elif not applications_display_df.empty and (search_term or selected_status_filter != "All"):
    st.warning("No applications match your current filter criteria.")
else:
    st.info("No applications found. Use the 'Add New Job Posting & Application' section to add one.")

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
else:
    selected_app_id_for_management = None
    st.caption("No applications to select for management.")

if selected_app_id_for_management:
    st.subheader(f"Managing Application ID: {selected_app_id_for_management}")
    # Fetch full details for the selected application
    app_details = db_utils.get_full_application_details(db, selected_app_id_for_management)

    if app_details:
        # Display Job Posting Details (and allow editing)
        with st.expander("Job Posting Details", expanded=True):
            # Form for editing job posting details
            with st.form(key=f"edit_job_posting_{app_details['job_posting_id']}"):
                st.write(f"**Job Posting ID:** {app_details['job_posting_id']}")
                new_title = st.text_input("Job Title", value=app_details.get('job_title', ''))
                new_company = st.text_input("Company", value=app_details.get('job_company', ''))
                new_location = st.text_input("Location", value=app_details.get('job_location', ''))
                new_description = st.text_area("Description", value=app_details.get('job_description', ''), height=150)
                new_source_url = st.text_input("Source URL", value=app_details.get('job_source_url', ''))
                new_date_posted_str = app_details.get('job_date_posted', '')
                try:
                    new_date_posted_val = datetime.strptime(new_date_posted_str, "%Y-%m-%d").date() if new_date_posted_str else None
                except ValueError:
                    new_date_posted_val = None # Handle cases where date might be invalid or empty
                new_date_posted = st.date_input("Date Posted (YYYY-MM-DD)", value=new_date_posted_val)

                if st.form_submit_button("Save Job Posting Changes"):
                    # Update job posting using SQLAlchemy
                    job_posting = get_job_posting(db, app_details['job_posting_id'])
                    if job_posting:
                        job_posting.title = new_title
                        job_posting.company = new_company
                        job_posting.location = new_location
                        job_posting.description = new_description
                        job_posting.source_url = new_source_url
                        job_posting.date_posted = new_date_posted.isoformat() if new_date_posted else None
                        try:
                            db.commit()
                            st.success("Job posting details updated!")
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Failed to update job posting details: {str(e)}")
                    else:
                        st.error("Job posting not found!")
        
        # Display Application Specific Details (and allow editing)
        with st.expander("Application Details", expanded=True):
            with st.form(key=f"edit_application_record_{selected_app_id_for_management}"):
                st.write(f"**Application ID:** {selected_app_id_for_management}")
                submission_options = list(schemas.SubmissionMethod) + [None]
                current_submission_method = app_details.get('submission_method')
                try:
                    submission_index = submission_options.index(current_submission_method)
                except ValueError:
                    submission_index = submission_options.index(None)

                new_submission_method = st.selectbox("Submission Method", 
                                                     options=submission_options,
                                                     index=submission_index)
                new_app_notes = st.text_area("Application Notes", value=app_details.get('application_notes', ''), height=100)

                # Resume and Cover Letter Management
                st.markdown("**Attached Files**")
                current_resume_id = app_details.get('resume_file_id')
                current_cl_id = app_details.get('cover_letter_file_id')

                # Get available files using SQLAlchemy
                available_resumes = {0: "None"}
                for res_file in db_utils.get_files_by_type(db, schemas.FileType.RESUME):
                    available_resumes[res_file['id']] = res_file['original_name']
                
                available_cls = {0: "None"}
                for cl_file in db_utils.get_files_by_type(db, schemas.FileType.COVER_LETTER):
                    available_cls[cl_file['id']] = cl_file['original_name']
                
                resume_keys = list(available_resumes.keys())
                try:
                    resume_index = resume_keys.index(current_resume_id if current_resume_id in resume_keys else 0)
                except ValueError:
                    resume_index = resume_keys.index(0)

                selected_resume_id = st.selectbox("Link Resume", options=resume_keys, 
                                                    format_func=lambda x: available_resumes[x],
                                                    index=resume_index)
                
                cl_keys = list(available_cls.keys())
                try:
                    cl_index = cl_keys.index(current_cl_id if current_cl_id in cl_keys else 0)
                except ValueError:
                    cl_index = cl_keys.index(0)
                selected_cl_id = st.selectbox("Link Cover Letter", options=cl_keys, 
                                                format_func=lambda x: available_cls[x],
                                                index=cl_index) 

                if st.form_submit_button("Save Application Changes"):
                    # Update application using SQLAlchemy
                    application = get_application(db, selected_app_id_for_management)
                    if application:
                        application.resume_file_id = selected_resume_id if selected_resume_id != 0 else None
                        application.cover_letter_file_id = selected_cl_id if selected_cl_id != 0 else None
                        application.submission_method = new_submission_method
                        application.notes = new_app_notes
                        try:
                            db.commit()
                            st.success("Application details updated!")
                            st.rerun()
                        except Exception as e:
                            db.rollback()
                            st.error(f"Failed to update application details: {str(e)}")
                    else:
                        st.error("Application not found!")

        # Status History and Logging New Status
        with st.expander("Status History & Logging"): 
            st.write("**Current Status History:**")
            if app_details.get('status_history'):
                status_df = pd.DataFrame(app_details['status_history'])
                st.dataframe(status_df[['timestamp', 'status', 'source_text']], hide_index=True)
            else:
                st.caption("No status history recorded.")
            
            with st.form(key=f"log_status_{selected_app_id_for_management}"):
                new_status = st.selectbox("New Status", options=['submitted', 'viewed', 'screening', 'interview', 'assessment', 'offer', 'rejected', 'withdrawn', 'other'])
                new_status_source = st.text_area("Source/Notes for new status (e.g., email content, call summary)", height=75)
                if st.form_submit_button("Log New Status"):
                    if db_utils.log_application_status(
                        db,
                        application_id=selected_app_id_for_management,
                        status=new_status,
                        source_text=new_status_source
                    ):
                        st.success(f"Status '{new_status}' logged.")
                        st.rerun()
                    else:
                        st.error("Failed to log status.")
        
        # Delete Application Button
        if st.button("Delete This Entire Application Record", type="primary", key=f"delete_app_rec_{selected_app_id_for_management}"):
            # Get application instance
            application = get_application(db, selected_app_id_for_management)
            if application:
                try:
                    db.delete(application)  # This will cascade delete related records
                    db.commit()
                    st.success(f"Application record {selected_app_id_for_management} and its related history/contacts/emails deleted.")
                    st.session_state.selected_app_id_tracker = None
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    st.error(f"Failed to delete application record: {str(e)}")
            else:
                st.error(f"Application not found.")
    else:
        st.error(f"Could not retrieve details for Application ID {selected_app_id_for_management}.")
else:
    st.caption("Select an application from the table or dropdown to manage its details.")

st.divider()

# --- Add New Job Posting & Initial Application ---
st.header("Add New Job Posting & Application")

if st.button("Show Add Job Posting Form", key="toggle_add_jp_form"):
    st.session_state.show_add_job_posting_form = not st.session_state.show_add_job_posting_form

if st.session_state.get("show_add_job_posting_form", False):
    with st.form("add_job_posting_form", clear_on_submit=True):
        st.subheader("1. Job Posting Details")
        jp_title = st.text_input("Job Title*")
        jp_company = st.text_input("Company*")
        jp_location = st.text_input("Location")
        jp_description = st.text_area("Job Description (paste here)*", height=200)
        jp_source_url = st.text_input("Job Source URL")
        jp_date_posted = st.date_input("Date Posted (if known)", value=None)
        
        st.subheader("2. Initial Application Details")
        app_submission_method = st.selectbox("Submission Method", 
                                             options=list(schemas.SubmissionMethod) + [None], index=0)
        app_notes = st.text_area("Initial Application Notes", height=75)
        app_date_submitted = st.date_input("Submission Date", value=datetime.now().date())
        
        uploaded_resume = st.file_uploader("Upload Resume (Optional)", type=["pdf", "docx", "txt"])
        uploaded_cl = st.file_uploader("Upload Cover Letter (Optional)", type=["pdf", "docx", "txt"])

        initial_status = st.selectbox("Initial Status", 
                                      options=['submitted', 'draft', 'planned'], index=0)
        initial_status_source = st.text_input("Source for initial status (e.g., 'Manual Entry')", 
                                              value="Manual Entry")

        submitted_add_form = st.form_submit_button("Add Job Posting and Application")

        if submitted_add_form:
            if not jp_title or not jp_company or not jp_description:
                st.error("Job Title, Company, and Description are required for the job posting.")
            else:
                # 1. Add Job Posting using SQLAlchemy
                job_posting = db_utils.add_job_posting_with_details(
                    db, 
                    title=jp_title, 
                    company=jp_company, 
                    description=jp_description,
                    location=jp_location, 
                    source_url=jp_source_url,
                    date_posted=jp_date_posted.isoformat() if jp_date_posted else None
                )
                
                if job_posting:
                    st.success(f"Job Posting '{jp_title}' added with ID: {job_posting.id}")
                    resume_file = None
                    cover_letter_file = None
                    
                    # Process resume if uploaded
                    if uploaded_resume:
                        saved_resume_path = save_uploaded_file(uploaded_resume)
                        if saved_resume_path:
                            resume_hash = get_file_hash(saved_resume_path)
                            if resume_hash:
                                resume_file = create_file(
                                    db,
                                    schemas.FileCreate(
                                        original_name=uploaded_resume.name,
                                        stored_path=str(saved_resume_path),
                                        sha256=resume_hash,
                                        file_type=schemas.FileType.RESUME
                                    )
                                )
                                if resume_file:
                                    st.info(f"Resume '{uploaded_resume.name}' processed and added to DB.")
                                else:
                                    st.warning(f"Resume '{uploaded_resume.name}' saved but failed to add to DB.")
                            else:
                                st.warning(f"Could not hash saved resume: {saved_resume_path}")
                        else:
                            st.warning(f"Could not save uploaded resume: {uploaded_resume.name}")

                    # Process cover letter if uploaded
                    if uploaded_cl:
                        saved_cl_path = save_uploaded_file(uploaded_cl)
                        if saved_cl_path:
                            cl_hash = get_file_hash(saved_cl_path)
                            if cl_hash:
                                cover_letter_file = create_file(
                                    db,
                                    schemas.FileCreate(
                                        original_name=uploaded_cl.name,
                                        stored_path=str(saved_cl_path),
                                        sha256=cl_hash,
                                        file_type=schemas.FileType.COVER_LETTER
                                    )
                                )
                                if cover_letter_file:
                                    st.info(f"Cover Letter '{uploaded_cl.name}' processed and added to DB.")
                                else:
                                    st.warning(f"Cover Letter '{uploaded_cl.name}' saved but failed to add to DB.")
                            else:
                                st.warning(f"Could not hash saved cover letter: {saved_cl_path}")
                        else:
                            st.warning(f"Could not save uploaded cover letter: {uploaded_cl.name}")
                    
                    # 2. Add Application record using SQLAlchemy
                    application = db_utils.add_application_with_details(
                        db,
                        job_posting_id=job_posting.id,
                        resume_file_id=resume_file.id if resume_file else None,
                        cover_letter_file_id=cover_letter_file.id if cover_letter_file else None,
                        submission_method=app_submission_method,
                        notes=app_notes,
                        date_submitted=app_date_submitted.isoformat()
                    )
                    
                    if application:
                        st.success(f"Application record created with ID: {application.id}")
                        # 3. Log initial status
                        status_entry = db_utils.log_application_status(
                            db,
                            application_id=application.id,
                            status=initial_status,
                            source_text=initial_status_source
                        )
                        if status_entry:
                            st.info(f"Initial status '{initial_status}' logged.")
                            st.session_state.show_add_job_posting_form = False
                            st.rerun()
                        else:
                            st.error("Failed to log initial status.")
                    else:
                        st.error("Failed to create application record.")
                else:
                    st.error("Failed to add job posting. It might already exist (based on title, company, description). Check existing entries.")
else:
    st.caption("Click the button above to open the form for adding a new job posting and its initial application.")

st.divider()
