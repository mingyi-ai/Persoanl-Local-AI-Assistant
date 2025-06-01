"""Main page UI components for the reorganized job application tracker."""
from typing import Dict, Any, Optional, List
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session

from core.ui.forms import JobPostingForm, ApplicationForm, ApplicationStatusForm
from core.ui.displays import display_applications_table, display_status_history
from core.ui.base import show_validation_errors, show_operation_result
from core.ui.job_tracker_ui import render_application_management_section
from core.ui.form_handlers import CombinedFormHandler, ApplicationStatusFormHandler, JobPostingFormHandler, ApplicationFormHandler
from core.ui.form_renderers import ReusableFormRenderer
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
                        "source_url": getattr(result, 'source_url', ''),
                        "type": getattr(result, 'type', ''),
                        "seniority": getattr(result, 'seniority', ''),
                        "tags": getattr(result, 'tags', ''),
                        "skills": getattr(result, 'skills', ''),
                        "industry": getattr(result, 'industry', ''),
                        "date_posted": getattr(result, 'date_posted', '')
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
                        if result.skills:
                            st.write("**Skills:**")
                            skills_list = result.skills.split(', ')
                            for skill in skills_list[:3]:  # Show first 3
                                st.write(f"• {skill}")
                            if len(skills_list) > 3:
                                st.write(f"• ... and {len(skills_list) - 3} more")
                    
                    st.success("✅ Analysis complete! Use the 'Add New Job Posting' tab below to create an entry with this data.")
                else:
                    st.error("Failed to analyze job description. Please try again.")


def render_add_job_posting_tab(
    db: Session,
    job_tracker_controller,
    langchain_backend
) -> None:
    """Render the add new job posting tab."""
    # AI Analysis section at the top
    render_ai_job_description_analyzer(langchain_backend)
    
    st.divider()
     # Job posting form section
    st.subheader("📝 Create Job Posting & Application")
    
    # Get prefill data from AI analysis if available
    prefill_data = st.session_state.get("analysis_result", {})
    
    # Show AI parsing status if prefill data is available
    if prefill_data:
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
            # Use the centralized form handler
            combined_handler = CombinedFormHandler(db, job_tracker_controller)
            success = combined_handler.create_job_posting_and_application(
                job_posting_data, application_data, status_data
            )
            if success:
                st.rerun()


def render_application_status_tab(
    db: Session,
    applications_df: pd.DataFrame,
    job_tracker_controller
) -> None:
    """Render the application status update tab using reusable forms."""
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
        # Get application details
        app_result = job_tracker_controller.get_application_details(db, selected_app_id)
        app_details = app_result.get("details", {}) if app_result["success"] else {}
        
        # 1. Application Status Form on top with confirm button
        with st.expander("📊 Status History & Update", expanded=True):
            st.write("**Current Status History:**")
            if app_details.get('status_history'):
                display_status_history(app_details['status_history'])
            else:
                st.info("No status history available yet.")
            
            st.divider()
            st.markdown("**Log New Status Update:**")
            
            # Status form with confirm button
            with st.form(key=f"main_status_form_{selected_app_id}"):
                status_data = ApplicationStatusForm.render(f"main_status_{selected_app_id}")
                
                if st.form_submit_button("✅ Confirm Status Update", type="primary"):
                    status_handler = ApplicationStatusFormHandler(db, job_tracker_controller)
                    result = status_handler.update_status(selected_app_id, status_data)
                    status_handler.show_result(result, f"Status updated to '{status_data['status']}'")
                    if result["success"]:
                        st.rerun()
        
        st.divider()
        
        # 2. Job Posting Form with update button
        with st.expander("💼 Job Posting Details", expanded=False):
            with st.form(key=f"main_job_posting_form_{selected_app_id}"):
                st.markdown("**Update Job Posting Information:**")
                job_posting_data = ReusableFormRenderer.render_job_posting_details(
                    app_details, 
                    mode="edit", 
                    key_prefix=f"main_jp_{selected_app_id}",
                    selected_app_id=selected_app_id
                )
                
                if st.form_submit_button("🔄 Update Job Posting", type="secondary"):
                    jp_handler = JobPostingFormHandler(db, job_tracker_controller)
                    result = jp_handler.update_job_posting(app_details['job_posting_id'], job_posting_data)
                    jp_handler.show_result(result, "Job posting details updated!")
                    if result["success"]:
                        st.rerun()
        
        # 3. Application Form with update button
        with st.expander("📋 Application Details", expanded=False):
            with st.form(key=f"main_application_form_{selected_app_id}"):
                st.markdown("**Update Application Information:**")
                application_data = ReusableFormRenderer.render_application_details(
                    app_details, 
                    mode="edit", 
                    key_prefix=f"main_app_{selected_app_id}",
                    selected_app_id=selected_app_id
                )
                
                if st.form_submit_button("🔄 Update Application", type="secondary"):
                    app_handler = ApplicationFormHandler(db, job_tracker_controller)
                    result = app_handler.update_application(
                        selected_app_id, 
                        application_data,
                        new_resume=application_data.get("new_resume"),
                        new_cover_letter=application_data.get("new_cover_letter"),
                        current_resume_path=application_data.get("current_resume_path"),
                        current_cover_letter_path=application_data.get("current_cover_letter_path")
                    )
                    app_handler.show_result(result, "Application details updated!")
                    if result["success"]:
                        st.rerun()


def render_main_action_tabs(
    db: Session,
    applications_df: pd.DataFrame,
    job_tracker_controller,
    langchain_backend
) -> None:
    """Render the main action tabs section."""
    st.header("⚡ Actions")
    
    # Create main action tabs
    tab1, tab2 = st.tabs(["🔄 Update Application Status", "➕ Add New Job Posting"])
    
    with tab1:
        render_application_status_tab(
            db, applications_df, job_tracker_controller
        )
    
    with tab2:
        render_add_job_posting_tab(
            db, job_tracker_controller, langchain_backend
        )
