"""UI components for the job tracker page."""
from typing import Dict, Any, Optional, List
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime

from core.ui.forms import (
    JobPostingForm, ApplicationForm, 
    ApplicationStatusForm
)
from core.ui.displays import display_applications_table, display_status_history
from core.ui.base import show_validation_errors, show_operation_result
from core.file_utils import save_uploaded_file, get_file_hash

def render_add_job_posting_section(
    db: Session,
    job_posting_controller,
    application_controller,
    prefill_data: Optional[Dict[str, Any]] = None
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
            date_posted=job_posting_data["date_posted"].isoformat() if job_posting_data["date_posted"] else None,
            type=job_posting_data["type"],
            seniority=job_posting_data["seniority"],
            tags=job_posting_data["tags"],
            skills=job_posting_data["skills"],
            industry=job_posting_data["industry"]
        )
        
        if not show_operation_result(jp_result, f"Job Posting '{job_posting_data['title']}' created with ID: {jp_result.get('job_posting_id')}"):
            return False

        # Handle file uploads - save files directly as paths in simplified schema
        resume_file_path = None
        cover_letter_file_path = None
        
        if application_data["resume"]:
            resume_file_path = save_uploaded_file(application_data["resume"])

        if application_data["cover_letter_file"]:
            cover_letter_file_path = save_uploaded_file(application_data["cover_letter_file"])

        # Create application with file paths instead of file IDs
        app_result = application_controller.create_application(
            db=db,
            job_posting_id=jp_result["job_posting_id"],
            resume_file_path=resume_file_path,
            cover_letter_file_path=cover_letter_file_path,
            cover_letter_text=application_data["cover_letter_text"],
            submission_method=application_data["submission_method"],
            additional_questions=application_data["additional_questions"],
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
        # Show AI parsing status if prefill data is available
        if prefill_data:
            with st.container():
                st.success("🤖 AI Analysis Complete - Review and edit the prefilled data below")
                
                # Show skills summary if available
                if "skills" in prefill_data and prefill_data["skills"]:
                    with st.expander("📊 AI-Parsed Skills Summary", expanded=False):
                        skills_list = prefill_data["skills"].split(', ') if prefill_data["skills"] else []
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if skills_list:
                                st.write("**Skills:**")
                                for skill in skills_list:
                                    st.write(f"• {skill}")
                        
                        with col2:
                            if "tags" in prefill_data and prefill_data["tags"]:
                                st.write("**Tags:**")
                                tags_list = prefill_data["tags"].split(', ') if prefill_data["tags"] else []
                                for tag in tags_list:
                                    st.write(f"• {tag}")
        
        with st.form("add_job_posting_form", clear_on_submit=True):
            st.subheader("1. Job Posting Details")
            job_posting_data = JobPostingForm.render("new_jp", prefill_data=prefill_data)

            st.subheader("2. Initial Application Details")
            application_data = ApplicationForm.render("new_app")
            
            st.subheader("3. Initial Status")
            status_data = ApplicationStatusForm.render(
                "initial",
                prefill_data={"source_text": "AI-Assisted Entry" if prefill_data else "Manual Entry"}
            )
            
            submitted_add_form = st.form_submit_button("Add Job Posting and Application")
            
            if submitted_add_form:
                if handle_form_submission(job_posting_data, application_data, status_data):
                    st.session_state.show_add_job_posting_form = False
                    st.rerun()
    else:
        if prefill_data:
            st.info("🤖 AI analysis completed! Click the button above to review and create a job posting with the parsed data.")
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

    # # Display Job Posting Details
    # with st.expander("Job Posting Details", expanded=True):
    #     # For now, just display job posting details without editing capability
    #     # TODO: Add update_job_posting method to controller and enable editing
        
    #     st.write(f"**Job Posting ID:** {app_details['job_posting_id']}")
    #     st.write(f"**Title:** {app_details.get('job_title', 'N/A')}")
    #     st.write(f"**Company:** {app_details.get('job_company', 'N/A')}")
    #     st.write(f"**Location:** {app_details.get('job_location', 'N/A')}")
    #     st.write(f"**Type:** {app_details.get('job_type', 'N/A')}")
    #     st.write(f"**Seniority:** {app_details.get('job_seniority', 'N/A')}")
    #     st.write(f"**Source URL:** {app_details.get('job_source_url', 'N/A')}")
    #     st.write(f"**Date Posted:** {app_details.get('job_date_posted', 'N/A')}")
    #     st.write(f"**Tags:** {app_details.get('job_tags', 'N/A')}")
    #     st.write(f"**Skills:** {app_details.get('job_skills', 'N/A')}")
    #     st.write(f"**Industry:** {app_details.get('job_industry', 'N/A')}")
        
    #     if app_details.get('job_description'):
    #         st.write("**Job Description:**")
    #         st.text_area("Job Description", value=app_details['job_description'], height=200, disabled=True, key=f"job_desc_{selected_app_id}", label_visibility="collapsed")
        
    #     st.info("💡 Job posting editing will be available in a future update.")
    
    # Display Application Details
    with st.expander("Application Details", expanded=True):
        with st.form(key=f"edit_application_record_{selected_app_id}"):
            st.write(f"**Application ID:** {selected_app_id}")
            
            application_data = ApplicationForm.render(
                "edit_app",
                prefill_data={
                    "submission_method": app_details.get('submission_method'),
                    "cover_letter_text": app_details.get('cover_letter_text', ''),
                    "additional_questions": app_details.get('additional_questions', ''),
                    "notes": app_details.get('application_notes', '')
                }
            )
            
            # File Upload Section (simplified schema - no file selection from existing files)
            st.markdown("**File Management**")
            
            # Show current file paths if they exist
            current_resume = app_details.get('resume_file_path')
            current_cover_letter = app_details.get('cover_letter_file_path')
            
            if current_resume:
                st.info(f"📄 Current Resume: {current_resume}")
            if current_cover_letter:
                st.info(f"📄 Current Cover Letter: {current_cover_letter}")
            
            # File upload fields for replacing existing files
            new_resume = st.file_uploader(
                "Upload New Resume (will replace current if uploaded)",
                type=["pdf", "docx", "txt"],
                key=f"new_resume_{selected_app_id}"
            )
            
            new_cover_letter = st.file_uploader(
                "Upload New Cover Letter File (will replace current if uploaded)",
                type=["pdf", "docx", "txt"],
                key=f"new_cover_letter_{selected_app_id}"
            )
            
            if st.form_submit_button("Save Application Changes"):
                # Handle file uploads
                resume_file_path = current_resume  # Keep existing by default
                cover_letter_file_path = current_cover_letter  # Keep existing by default
                
                if new_resume:
                    resume_file_path = save_uploaded_file(new_resume)
                
                if new_cover_letter:
                    cover_letter_file_path = save_uploaded_file(new_cover_letter)
                
                result = application_controller.update_application(
                    db=db,
                    application_id=selected_app_id,
                    resume_file_path=resume_file_path,
                    cover_letter_file_path=cover_letter_file_path,
                    cover_letter_text=application_data["cover_letter_text"],
                    submission_method=application_data["submission_method"],
                    additional_questions=application_data["additional_questions"],
                    notes=application_data["notes"]
                )
                show_operation_result(result, "Application details updated!")
                if result["success"]:
                    st.rerun()

    # Status History and Logging
    # with st.expander("Status History & Logging"):
    #     st.write("**Current Status History:**")
    #     display_status_history(app_details.get('status_history', []))
        
    #     with st.form(key=f"log_status_{selected_app_id}"):
    #         status_data = ApplicationStatusForm.render("new_status")
            
    #         if st.form_submit_button("Log New Status"):
    #             result = application_controller.update_application_status(
    #                 db=db,
    #                 application_id=selected_app_id,
    #                 status=status_data["status"],
    #                 source_text=status_data["source_text"]
    #             )
    #             show_operation_result(result, f"Status '{status_data['status']}' logged.")
    #             if result["success"]:
    #                 st.rerun()

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
