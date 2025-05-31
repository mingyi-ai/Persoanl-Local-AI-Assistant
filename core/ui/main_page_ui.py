"""Main page UI components for the reorganized job application tracker."""
from typing import Dict, Any, Optional, List
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from core.ui.forms import JobPostingForm, ApplicationForm, ApplicationStatusForm
from core.ui.displays import display_applications_table, display_status_history
from core.ui.base import show_validation_errors, show_operation_result
from core.ui.job_tracker_ui import render_application_management_section
from core.file_utils import save_uploaded_file


def render_database_display_section(
    applications_df: pd.DataFrame,
    display_columns: List[str]
) -> None:
    """Render the database display section with tabs."""
    st.header("📊 Application Database")
    
    # Create tabs for database display
    tab1, tab2 = st.tabs(["📋 Applications Table", "📈 Statistics (Reserved)"])
    
    with tab1:
        # Fixed height container for the dataframe
        with st.container(height=400):
            if not applications_df.empty:
                st.info(f"Displaying {len(applications_df)} application(s).")
                st.dataframe(
                    applications_df[display_columns], 
                    use_container_width=True, 
                    hide_index=True,
                    height=350
                )
            else:
                st.info("No applications found.")
    
    with tab2:
        st.info("📈 Statistics and analytics will be available in a future update.")
        st.caption("This section will include charts, trends, and summary statistics.")


def render_ai_job_description_analyzer(langchain_backend) -> None:
    """Render the AI job description analyzer section."""
    st.subheader("🤖 AI Job Description Analyzer")
    
    with st.expander("Job Description Analyzer", expanded=True):
        job_description = st.text_area(
            "Paste job description here",
            height=200,
            key="main_job_description_input"
        )

        if st.button("Analyze Description", key="main_analyze_button"):
            if not job_description:
                st.warning("Please paste a job description first.")
                return

            with st.spinner("Analyzing job description..."):
                result = langchain_backend.analyze_job_description(job_description)

                if result:
                    # Store analysis result for use in form prefilling
                    st.session_state.analysis_result = {
                        "title": result.title,
                        "company": getattr(result, 'company', ''),
                        "description": job_description,
                        "location": getattr(result, 'location', ''),
                        "parsed_metadata": {
                            "required_skills": result.required_skills,
                            "preferred_skills": result.preferred_skills
                        }
                    }
                    
                    # Display analysis preview
                    st.divider()
                    st.subheader("📋 Analysis Preview")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Basic Information**")
                        st.write(f"**Title:** {result.title}")
                        if hasattr(result, 'company') and result.company:
                            st.write(f"**Company:** {result.company}")
                        if hasattr(result, 'location') and result.location:
                            st.write(f"**Location:** {result.location}")
                    
                    with col2:
                        st.write("**Skills Analysis**")
                        if result.required_skills:
                            st.write("**Required Skills:**")
                            for skill in result.required_skills[:3]:  # Show first 3
                                st.write(f"• {skill}")
                            if len(result.required_skills) > 3:
                                st.write(f"• ... and {len(result.required_skills) - 3} more")
                    
                    st.success("✅ Analysis complete! Use the 'Add New Job Posting' tab below to create an entry with this data.")
                else:
                    st.error("Failed to analyze job description. Please try again.")


def render_add_job_posting_tab(
    db: Session,
    job_posting_controller,
    application_controller,
    langchain_backend
) -> None:
    """Render the add new job posting tab."""
    # AI Analysis section at the top
    render_ai_job_description_analyzer(langchain_backend)
    
    st.divider()
    
    # Job posting form section
    st.subheader("📝 Create Job Posting & Application")
    
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
        
        if not show_operation_result(jp_result, f"Job Posting '{job_posting_data['title']}' created"):
            return False

        # Handle file uploads
        resume_file_path = None
        cover_letter_file_path = None
        
        if application_data["resume"]:
            resume_file_path = save_uploaded_file(application_data["resume"])

        if application_data["cover_letter_file"]:
            cover_letter_file_path = save_uploaded_file(application_data["cover_letter_file"])

        # Create application
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
        
        success = show_operation_result(status_result, "Initial status logged successfully")
        if success:
            # Clear the analysis result after successful submission
            if "analysis_result" in st.session_state:
                del st.session_state.analysis_result
        
        return success

    # Get prefill data from AI analysis if available
    prefill_data = st.session_state.get("analysis_result", {})
    
    # Show AI parsing status if prefill data is available
    if prefill_data:
        st.success("🤖 AI Analysis Complete - Review and edit the prefilled data below")
        
        # Show parsed metadata summary if available
        if "parsed_metadata" in prefill_data:
            with st.expander("📊 AI-Parsed Metadata Summary", expanded=False):
                metadata = prefill_data["parsed_metadata"]
                col1, col2 = st.columns(2)
                
                with col1:
                    if "required_skills" in metadata and metadata["required_skills"]:
                        st.write("**Required Skills:**")
                        for skill in metadata["required_skills"]:
                            st.write(f"• {skill}")
                
                with col2:
                    if "preferred_skills" in metadata and metadata["preferred_skills"]:
                        st.write("**Preferred Skills:**")
                        for skill in metadata["preferred_skills"]:
                            st.write(f"• {skill}")

    with st.form("main_add_job_posting_form", clear_on_submit=True):
        st.markdown("#### 1. Job Posting Details")
        job_posting_data = JobPostingForm.render("main_new_jp", prefill_data=prefill_data)

        st.markdown("#### 2. Application Details")
        application_data = ApplicationForm.render("main_new_app")
        
        st.markdown("#### 3. Initial Status")
        status_data = ApplicationStatusForm.render(
            "main_initial",
            prefill_data={"source_text": "AI-Assisted Entry" if prefill_data else "Manual Entry"}
        )
        
        submitted_form = st.form_submit_button("Create Job Posting and Application", type="primary")
        
        if submitted_form:
            if handle_form_submission(job_posting_data, application_data, status_data):
                st.rerun()


def render_application_status_tab(
    db: Session,
    applications_df: pd.DataFrame,
    application_controller,
    job_posting_controller
) -> None:
    """Render the application status update tab."""
    st.subheader("🔄 Update Application Status")
    
    if applications_df.empty:
        st.info("No applications available. Create an application first using the 'Add New Job Posting' tab.")
        return
    
    # Application selection
    app_id_options = applications_df['application_id'].tolist()
    selected_app_id = st.selectbox(
        "Select Application to Update", 
        options=app_id_options,
        format_func=lambda x: f"ID {x}: {applications_df[applications_df['application_id']==x]['job_title'].iloc[0]} at {applications_df[applications_df['application_id']==x]['job_company'].iloc[0]}",
        key="main_app_selector",
        index=None,
        placeholder="Choose an application..."
    )
    
    if selected_app_id:
        # Get application details for status history
        app_result = application_controller.get_application_details(db, selected_app_id)
        app_details = app_result.get("details", {}) if app_result["success"] else {}
        
        # Status History and Logging - moved to top and expanded by default
        with st.expander("📊 Status History & Logging", expanded=True):
            st.write("**Current Status History:**")
            if app_details.get('status_history'):
                display_status_history(app_details['status_history'])
            else:
                st.info("No status history available yet.")
            
            st.divider()
            
            # Status update form
            st.markdown("**Log New Status Update:**")
            with st.form(key=f"main_log_status_{selected_app_id}"):
                col1, col2 = st.columns([1, 3])
                
                with col1:
                    new_status = st.selectbox(
                        "New Status",
                        options=['submitted', 'viewed', 'screening', 'interview', 'assessment', 'offer', 'rejected', 'withdrawn'],
                        key=f"main_new_status_select_{selected_app_id}"
                    )
                
                with col2:
                    status_notes = st.text_area(
                        "Status Notes/Details",
                        placeholder="Add detailed notes about this status update...",
                        height=100,
                        key=f"main_status_notes_{selected_app_id}",
                        label_visibility="collapsed"
                    )
                
                if st.form_submit_button("📝 Log Status Update", type="primary"):
                    result = application_controller.update_application_status(
                        db=db,
                        application_id=selected_app_id,
                        status=new_status,
                        source_text=status_notes or f"Status updated to {new_status}"
                    )
                    show_operation_result(result, f"Status updated to '{new_status}'")
                    if result["success"]:
                        st.rerun()
        
        st.divider()
        
        # Full application management section
        st.markdown("#### 📋 Application Management")
        render_application_management_section(
            db, selected_app_id, application_controller, job_posting_controller
        )


def render_main_action_tabs(
    db: Session,
    applications_df: pd.DataFrame,
    job_posting_controller,
    application_controller,
    langchain_backend
) -> None:
    """Render the main action tabs section."""
    st.header("⚡ Actions")
    
    # Create main action tabs
    tab1, tab2 = st.tabs(["🔄 Update Application Status", "➕ Add New Job Posting"])
    
    with tab1:
        render_application_status_tab(
            db, applications_df, application_controller, job_posting_controller
        )
    
    with tab2:
        render_add_job_posting_tab(
            db, job_posting_controller, application_controller, langchain_backend
        )
