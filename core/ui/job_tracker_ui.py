"""UI components for the job tracker page."""
from typing import Dict, Any, Optional, List
import streamlit as st
import pandas as pd
from sqlalchemy.orm import Session
from datetime import datetime

from core.ui.displays import display_applications_table, display_status_history
from core.ui.base import show_validation_errors, show_operation_result
from core.ui.form_renderers import ReusableFormRenderer
from core.services.file_service import FileService
from core.ui.forms import JobPostingForm, ApplicationForm, ApplicationStatusForm
from core.ui.form_handlers import CombinedFormHandler, ApplicationStatusFormHandler, JobPostingFormHandler, ApplicationFormHandler
from core.ui.streaming_ui import create_streaming_display

# Render the database display section with tabs for applications and statistics.
def render_database_display_section(
    applications_df: pd.DataFrame,
    display_columns: List[str]
) -> None:
    """Render the database display section with tabs."""
    st.header("📊 Application Database")
    
    # Create tabs for database display
    tab1, tab2 = st.tabs(["📋 Applications Table", "📈 Statistics (Reserved)"])
    
    with tab1:
        if not applications_df.empty:
            # Search Section
            st.subheader("🔍 Search Applications")
            
            # Create search bar with clear button
            search_col, clear_col = st.columns([4, 1])
            
            with search_col:
                search_term = st.text_input(
                    "Search applications",
                    placeholder="Type to search by job title, company, location, skills, tags...",
                    key="app_search",
                    label_visibility="collapsed",
                    help="Search across all application fields. Use multiple keywords for more specific results."
                )
            
            with clear_col:
                if st.button("🗑️ Clear", key="clear_search", help="Clear search", use_container_width=True):
                    st.session_state.app_search = ""
                    st.rerun()
            
            # Perform search
            if search_term:
                # Define searchable columns
                search_columns = ['job_title', 'job_company', 'job_location', 'job_skills', 'job_tags', 'job_description']
                
                # Convert search term to lowercase for case-insensitive search
                search_terms = search_term.lower().split()
                
                # Initialize result mask
                search_mask = pd.Series([False] * len(applications_df))
                
                # Search across all relevant columns
                for col in search_columns:
                    if col in applications_df.columns:
                        # Convert column to string and lowercase
                        col_text = applications_df[col].astype(str).str.lower()
                        
                        # Check if any search term is found in this column
                        for term in search_terms:
                            term_mask = col_text.str.contains(term, na=False, regex=False)
                            search_mask |= term_mask
                
                filtered_df = applications_df[search_mask].copy()
            else:
                filtered_df = applications_df.copy()
            
            # Display search results
            total_count = len(applications_df)
            filtered_count = len(filtered_df)
            
            if search_term:
                if filtered_count > 0:
                    if filtered_count == total_count:
                        st.info(f"✨ All {total_count} applications match '{search_term}'")
                    else:
                        st.success(f"🎯 Found {filtered_count} of {total_count} applications matching '{search_term}'")
                else:
                    st.warning(f"🔍 No matches for '{search_term}' - try different keywords or check spelling")
            else:
                st.info(f"📋 Displaying all {total_count} application(s) - start typing to search")
            
            # Fixed height container for the dataframe
            with st.container(height=400):
                if not filtered_df.empty:
                    st.dataframe(
                        filtered_df[display_columns], 
                        use_container_width=True, 
                        hide_index=True,
                        height=350,
                        column_config={
                            'application_id': st.column_config.NumberColumn('ID', width='small'),
                            'job_title': st.column_config.TextColumn('Job Title', width='medium'),
                            'job_company': st.column_config.TextColumn('Company', width='medium'),
                        }
                    )
                else:
                    if search_term:
                        st.info("💡 **No results found. Try:**\n- Using fewer or different keywords\n- Checking spelling\n- Using partial matches\n- Searching company names or job titles")
                    else:
                        st.info("No applications found.")
        else:
            st.info("No applications found.")
    
    with tab2:
        st.info("📈 Statistics and analytics will be available in a future update.")
        st.caption("This section will include charts, trends, and summary statistics.")


# Render the main action tabs for updating application status and adding new job postings.
def render_main_action_tabs(
    db: Session,
    applications_df: pd.DataFrame,
    job_tracker_controller,
    prompt_service
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
            db, job_tracker_controller, prompt_service
        )


# Main action, tab 1 - Render the application status update tab.
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


# Main action, tab 2 - Render the AI job description analyzer section.
def render_ai_job_description_analyzer(prompt_service) -> None:
    """Render the AI job description analyzer section."""
    from .streaming_ui import create_streaming_display
    
    st.subheader("🤖 AI Job Description Analyzer")
    
    # Check if AI service is available
    if not prompt_service:
        with st.expander("Job Description Analyzer", expanded=True):
            st.warning("⚠️ AI service not available. Please configure an LLM model in the sidebar.")
            st.text_area(
                "Paste job description here",
                height=200,
                key="main_job_description_input",
                disabled=True
            )
            st.button("Analyze Description", key="main_analyze_button", disabled=True)
        return
    
    with st.expander("Job Description Analyzer", expanded=True):
        job_description = st.text_area(
            "Paste job description here",
            height=200,
            key="main_job_description_input"
        )

        # Create columns for buttons
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if not st.session_state.get("ai_analysis_generating", False):
                analyze_clicked = st.button("🔍 Analyze Description", key="main_analyze_button")
            else:
                st.info("🔄 Analyzing job description...")
                analyze_clicked = False
        
        with col2:
            # Show cancel button only for LlamaCpp backend and when generating
            if (st.session_state.get("ai_analysis_generating", False) and 
                hasattr(prompt_service, 'base_backend') and 
                prompt_service.base_backend.__class__.__name__ == 'LlamaCppBackend'):
                
                if st.button("⏹️ Cancel", key="main_cancel_button", type="secondary"):
                    prompt_service.base_backend.stop_generation()
                    st.session_state.ai_analysis_generating = False
                    st.warning("Analysis cancelled by user")
                    st.rerun()

        # Initialize streaming display
        streaming_display = create_streaming_display("main_ai_analyzer")
        response_container = streaming_display.initialize_container()
        
        # Handle analysis trigger
        if analyze_clicked and job_description.strip():
            st.session_state.ai_analysis_generating = True
            st.session_state.ai_analysis_job_description = job_description
            st.rerun()
        elif analyze_clicked and not job_description.strip():
            st.warning("Please paste a job description first.")
        
        # Handle generation process (only if we're in generating state)
        if st.session_state.get("ai_analysis_generating", False):
            # Get the job description from session state
            analysis_job_description = st.session_state.get("ai_analysis_job_description", "")
            
            if not analysis_job_description:
                st.error("No job description found for analysis")
                st.session_state.ai_analysis_generating = False
                st.rerun()
                return
            
            try:
                # Determine if we should use streaming (both LlamaCpp and Ollama now support it)
                use_streaming = (hasattr(prompt_service, 'base_backend') and 
                               hasattr(prompt_service.base_backend, 'generate_response_streaming') and
                               hasattr(prompt_service, 'analyze_job_description_streaming'))
                
                if use_streaming:
                    # Use streaming with UI callback for both backends
                    update_callback = streaming_display.get_update_callback()
                    result = prompt_service.analyze_job_description_streaming(
                        analysis_job_description,
                        update_callback=update_callback,
                        max_tokens=2000,
                        temperature=0.1
                    )
                else:
                    # Use standard generation for backends that don't support streaming
                    streaming_display.show_processing("Processing job description...")
                    result = prompt_service.analyze_job_description(analysis_job_description)
                    
                    if result:
                        response_container.success("✅ Analysis completed successfully")
                    else:
                        response_container.error("❌ Analysis failed")
                
                # Reset generating state
                st.session_state.ai_analysis_generating = False
                
                # Store result for use in form prefilling
                if result:
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
                    
                    # Clear the streaming container and show results
                    response_container.empty()
                    
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
                    
                    st.success("✅ Analysis complete! Use the form below to create an entry with this data.")
                else:
                    streaming_display.show_error("Analysis failed or was cancelled")
                
                st.rerun()
                    
            except Exception as e:
                st.session_state.ai_analysis_generating = False
                streaming_display.show_error(f"Error during analysis: {str(e)}")
                st.rerun()

# Main action, tab 2 - Render the add new job posting section with AI analysis and form.
# Render the add new job posting tab with AI analysis and job posting form.
def render_add_job_posting_tab(
    db: Session,
    job_tracker_controller,
    prompt_service
) -> None:
    """Render the add new job posting tab."""
    # AI Analysis section at the top
    render_ai_job_description_analyzer(prompt_service)
    
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





def render_add_job_posting_section(
    db: Session,
    job_tracker_controller,
    prefill_data: Optional[Dict[str, Any]] = None
) -> None:
    """Render the section for adding a new job posting and application."""
    st.header("Add New Job Posting & Application")

    if st.button("Show Add Job Posting Form", key="toggle_add_jp_form"):
        st.session_state.show_add_job_posting_form = not st.session_state.show_add_job_posting_form

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
                # Use the centralized form handler
                combined_handler = CombinedFormHandler(db, job_tracker_controller)
                success = combined_handler.create_job_posting_and_application(
                    job_posting_data, application_data, status_data
                )
                if success:
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
    job_tracker_controller
) -> None:
    """Render the section for managing an existing application."""
    st.subheader(f"Managing Application ID: {selected_app_id}")
    # Fetch full details for the selected application
    result = job_tracker_controller.get_application_details(db, selected_app_id)
    app_details = result.get("details") if result.get("success") else None

    if not app_details:
        st.error(f"Could not retrieve details for Application ID {selected_app_id}")
        return

    # Display Job Posting Details using reusable form renderer
    ReusableFormRenderer.render_expandable_section(
        title="Job Posting Details",
        content_func=lambda mode, **kwargs: ReusableFormRenderer.render_job_posting_details(
            app_details, mode=mode, selected_app_id=selected_app_id, **kwargs
        ),
        mode="display",
        expanded=True,
        info_message="💡 Job posting editing will be available in a future update."
    )
    
    # Display Application Details using reusable form renderer and handlers
    with st.expander("Application Details", expanded=True):
        with st.form(key=f"edit_application_record_{selected_app_id}"):
            st.write(f"**Application ID:** {selected_app_id}")
            
            # Use the reusable form renderer for application editing
            application_data = ReusableFormRenderer.render_application_details(
                app_details, 
                mode="edit", 
                key_prefix="edit_app",
                selected_app_id=selected_app_id
            )
            
            if st.form_submit_button("Save Application Changes"):
                # Use the centralized application handler
                app_handler = ApplicationFormHandler(db, job_tracker_controller)
                result = app_handler.update_application(
                    application_id=selected_app_id,
                    application_data=application_data,
                    new_resume=application_data.get("new_resume"),
                    new_cover_letter=application_data.get("new_cover_letter"),
                    current_resume_path=application_data.get("current_resume_path"),
                    current_cover_letter_path=application_data.get("current_cover_letter_path")
                )
                app_handler.show_result(result, "Application details updated!")
                if result["success"]:
                    st.rerun()

