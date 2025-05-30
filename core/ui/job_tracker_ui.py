"""UI components for the job tracker page."""
from typing import Dict, Any, Optional, List
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime

from core.ui.forms import (
    JobPostingForm, ApplicationForm, 
    ApplicationStatusForm, FileSelectionForm
)
from core.ui.displays import display_applications_table, display_status_history
from core.ui.base import show_validation_errors, show_operation_result
from core.file_utils import save_uploaded_file, get_file_hash

def render_add_job_posting_section(
    db: Session,
    job_posting_controller,
    application_controller
) -> None:
    """Render the section for adding a new job posting and application."""
    st.header("Add New Job Posting & Application")

    if st.button("Show Add Job Posting Form", key="toggle_add_jp_form"):
        st.session_state.show_add_job_posting_form = not st.session_state.show_add_job_posting_form

    def handle_form_submission(
        job_posting_data: Dict[str, Any],
        application_data: Dict[str, Any],
        status_data: Dict[str, Any]
    ) -> bool:
        """Handle the form submission and return whether it was successful."""
        # Validate job posting data
        jp_errors = JobPostingForm.validate(job_posting_data)
        if show_validation_errors(jp_errors):
            return False

        # Create job posting
        jp_result = job_posting_controller.create_job_posting(
            db=db,
            title=job_posting_data["title"],
            company=job_posting_data["company"],
            description=job_posting_data["description"],
            location=job_posting_data["location"],
            source_url=job_posting_data["source_url"],
            date_posted=job_posting_data["date_posted"].isoformat() if job_posting_data["date_posted"] else None
        )
        
        if not show_operation_result(jp_result, f"Job Posting '{job_posting_data['title']}' created with ID: {jp_result.get('job_posting_id')}"):
            return False

        # Handle file uploads
        resume_file_id = None
        cover_letter_file_id = None
        
        if application_data["resume"]:
            saved_resume_path = save_uploaded_file(application_data["resume"])
            if saved_resume_path:
                file_hash = get_file_hash(saved_resume_path)
                resume_result = application_controller.create_file(
                    db=db,
                    file_type="resume",
                    file_path=saved_resume_path,
                    file_hash=file_hash,
                    original_name=application_data["resume"].name
                )
                if resume_result["success"]:
                    resume_file_id = resume_result["file_id"]

        if application_data["cover_letter"]:
            saved_cl_path = save_uploaded_file(application_data["cover_letter"])
            if saved_cl_path:
                file_hash = get_file_hash(saved_cl_path)
                cl_result = application_controller.create_file(
                    db=db,
                    file_type="cover_letter",
                    file_path=saved_cl_path,
                    file_hash=file_hash,
                    original_name=application_data["cover_letter"].name
                )
                if cl_result["success"]:
                    cover_letter_file_id = cl_result["file_id"]

        # Create application
        app_result = application_controller.create_application(
            db=db,
            job_posting_id=jp_result["job_posting_id"],
            resume_file_id=resume_file_id,
            cover_letter_file_id=cover_letter_file_id,
            submission_method=application_data["submission_method"],
            notes=application_data["notes"],
            date_submitted=application_data["date_submitted"].isoformat()
        )

        if not show_operation_result(app_result, "Application created successfully"):
            return False

        # Log initial status
        status_result = application_controller.update_application_status(
            db=db,
            application_id=app_result["application_id"],
            status=status_data["status"],
            source_text=status_data["source_text"]
        )
        
        return show_operation_result(status_result, "Initial status logged successfully")

    if st.session_state.get("show_add_job_posting_form", False):
        with st.form("add_job_posting_form", clear_on_submit=True):
            st.subheader("1. Job Posting Details")
            job_posting_data = JobPostingForm.render("new_jp")
            
            st.subheader("2. Initial Application Details")
            application_data = ApplicationForm.render("new_app")
            
            st.subheader("3. Initial Status")
            status_data = ApplicationStatusForm.render(
                "initial",
                prefill_data={"source_text": "Manual Entry"}
            )
            
            submitted_add_form = st.form_submit_button("Add Job Posting and Application")
            
            if submitted_add_form:
                if handle_form_submission(job_posting_data, application_data, status_data):
                    st.session_state.show_add_job_posting_form = False
                    st.rerun()
    else:
        st.caption("Click the button above to show the form for adding a new job posting and application.")

def render_application_management_section(
    db: Session,
    selected_app_id: int,
    application_controller,
    job_posting_controller
) -> None:
    """Render the section for managing an existing application."""
    st.subheader(f"Managing Application ID: {selected_app_id}")
    # Fetch full details for the selected application
    result = application_controller.get_application_details(db, selected_app_id)
    app_details = result.get("details") if result.get("success") else None

    if not app_details:
        st.error(f"Could not retrieve details for Application ID {selected_app_id}")
        return

    # Display Job Posting Details
    with st.expander("Job Posting Details", expanded=True):
        # Form for editing job posting details
        with st.form(key=f"edit_job_posting_{app_details['job_posting_id']}"):
            st.write(f"**Job Posting ID:** {app_details['job_posting_id']}")
            job_posting_data = JobPostingForm.render(
                "edit_jp",
                prefill_data={
                    "title": app_details.get('job_title', ''),
                    "company": app_details.get('job_company', ''),
                    "location": app_details.get('job_location', ''),
                    "description": app_details.get('job_description', ''),
                    "source_url": app_details.get('job_source_url', ''),
                    "date_posted": app_details.get('job_date_posted', '')
                }
            )

            if st.form_submit_button("Save Job Posting Changes"):
                result = job_posting_controller.create_job_posting(
                    db=db,
                    **job_posting_data
                )
                show_operation_result(result, "Job posting details updated!")
                if result["success"]:
                    st.rerun()
    
    # Display Application Details
    with st.expander("Application Details", expanded=True):
        with st.form(key=f"edit_application_record_{selected_app_id}"):
            st.write(f"**Application ID:** {selected_app_id}")
            
            application_data = ApplicationForm.render(
                "edit_app",
                prefill_data={
                    "submission_method": app_details.get('submission_method'),
                    "notes": app_details.get('application_notes', '')
                }
            )
            
            # File Selection
            st.markdown("**Attached Files**")
            resume_result = application_controller.list_files_by_type(db, "resume")
            available_resumes = {0: "None"}
            if resume_result["success"]:
                for res_file in resume_result["files"]:
                    available_resumes[res_file['id']] = res_file['original_name']
            
            resume_data = FileSelectionForm.render(
                "resume",
                available_files=available_resumes,
                current_file_id=app_details.get('resume_file_id')
            )
            
            cl_result = application_controller.list_files_by_type(db, "cover_letter")
            available_cls = {0: "None"}
            if cl_result["success"]:
                for cl_file in cl_result["files"]:
                    available_cls[cl_file['id']] = cl_file['original_name']
            
            cl_data = FileSelectionForm.render(
                "cover_letter",
                available_files=available_cls,
                current_file_id=app_details.get('cover_letter_file_id')
            )
            
            if st.form_submit_button("Save Application Changes"):
                result = application_controller.create_application(
                    db=db,
                    job_posting_id=app_details['job_posting_id'],
                    resume_file_id=resume_data["file_id"],
                    cover_letter_file_id=cl_data["file_id"],
                    submission_method=application_data["submission_method"],
                    notes=application_data["notes"]
                )
                show_operation_result(result, "Application details updated!")
                if result["success"]:
                    st.rerun()

    # Status History and Logging
    with st.expander("Status History & Logging"):
        st.write("**Current Status History:**")
        display_status_history(app_details.get('status_history', []))
        
        with st.form(key=f"log_status_{selected_app_id}"):
            status_data = ApplicationStatusForm.render("new_status")
            
            if st.form_submit_button("Log New Status"):
                result = application_controller.update_application_status(
                    db=db,
                    application_id=selected_app_id,
                    status=status_data["status"],
                    source_text=status_data["source_text"]
                )
                show_operation_result(result, f"Status '{status_data['status']}' logged.")
                if result["success"]:
                    st.rerun()

def filter_applications(df: pd.DataFrame, search_term: str = None, status_filter: str = None) -> pd.DataFrame:
    """Filter applications based on search term and status."""
    filtered_df = df.copy()
    
    if search_term:
        search_conditions = (
            filtered_df["job_title"].astype(str).str.contains(search_term, case=False, na=False) |
            filtered_df["job_company"].astype(str).str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[search_conditions]

    if status_filter and status_filter != "All":
        filtered_df = filtered_df[filtered_df["current_status"] == status_filter]
        
    return filtered_df
