"""Reusable form renderer components for display and edit modes."""
from typing import Dict, Any, Optional, Union
import streamlit as st

from .forms import JobPostingForm, ApplicationForm


class ReusableFormRenderer:
    """Reusable form renderer that can handle both display and edit modes."""
    
    @staticmethod
    def render_job_posting_details(app_details: Dict[str, Any], 
                                 mode: str = "display", 
                                 key_prefix: str = "job_posting",
                                 selected_app_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Render job posting details in either display or edit mode.
        
        Args:
            app_details: Dictionary containing job posting details
            mode: "display" or "edit"
            key_prefix: Prefix for form field keys
            selected_app_id: Application ID for unique keys
            
        Returns:
            Form data dict if in edit mode, None if in display mode
        """
        
        if mode == "display":
            return ReusableFormRenderer._render_job_posting_display(app_details, selected_app_id)
        elif mode == "edit":
            return ReusableFormRenderer._render_job_posting_edit(app_details, key_prefix)
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'display' or 'edit'")
    
    @staticmethod
    def _render_job_posting_display(app_details: Dict[str, Any], selected_app_id: Optional[int] = None) -> None:
        """Render job posting details in display mode (read-only)."""
        
        # Basic job posting information
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Job Posting ID:** {app_details['job_posting_id']}")
            st.write(f"**Title:** {app_details.get('job_title', 'N/A')}")
            st.write(f"**Company:** {app_details.get('job_company', 'N/A')}")
            st.write(f"**Location:** {app_details.get('job_location', 'N/A')}")
            st.write(f"**Type:** {app_details.get('job_type', 'N/A')}")
            st.write(f"**Seniority:** {app_details.get('job_seniority', 'N/A')}")
        
        with col2:
            if app_details.get('job_source_url'):
                st.write(f"**Source URL:** [{app_details['job_source_url']}]({app_details['job_source_url']})")
            else:
                st.write("**Source URL:** N/A")
            
            st.write(f"**Date Posted:** {app_details.get('job_date_posted', 'N/A')}")
            st.write(f"**Tags:** {app_details.get('job_tags', 'N/A')}")
            st.write(f"**Skills:** {app_details.get('job_skills', 'N/A')}")
            st.write(f"**Industry:** {app_details.get('job_industry', 'N/A')}")
        
        # Job description in a separate section
        if app_details.get('job_description'):
            st.write("**Job Description:**")
            description_key = f"job_desc_{selected_app_id}" if selected_app_id else "job_desc"
            st.text_area(
                "Job Description", 
                value=app_details['job_description'], 
                height=200, 
                disabled=True, 
                key=description_key, 
                label_visibility="collapsed"
            )
    
    @staticmethod
    def _render_job_posting_edit(app_details: Dict[str, Any], key_prefix: str) -> Dict[str, Any]:
        """Render job posting details in edit mode (form fields)."""
        
        # Convert app_details to prefill_data format for the form
        prefill_data = {
            "title": app_details.get('job_title', ''),
            "company": app_details.get('job_company', ''),
            "location": app_details.get('job_location', ''),
            "type": app_details.get('job_type', ''),
            "seniority": app_details.get('job_seniority', ''),
            "description": app_details.get('job_description', ''),
            "source_url": app_details.get('job_source_url', ''),
            "date_posted": app_details.get('job_date_posted', ''),
            "tags": app_details.get('job_tags', ''),
            "skills": app_details.get('job_skills', ''),
            "industry": app_details.get('job_industry', '')
        }
        
        return JobPostingForm.render(key_prefix, prefill_data=prefill_data)
    
    @staticmethod
    def render_application_details(app_details: Dict[str, Any], 
                                 mode: str = "display", 
                                 key_prefix: str = "application",
                                 selected_app_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Render application details in either display or edit mode.
        
        Args:
            app_details: Dictionary containing application details
            mode: "display" or "edit"
            key_prefix: Prefix for form field keys
            selected_app_id: Application ID for unique keys
            
        Returns:
            Form data dict if in edit mode, None if in display mode
        """
        
        if mode == "display":
            return ReusableFormRenderer._render_application_display(app_details, selected_app_id)
        elif mode == "edit":
            return ReusableFormRenderer._render_application_edit(app_details, key_prefix, selected_app_id)
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'display' or 'edit'")
    
    @staticmethod
    def _render_application_display(app_details: Dict[str, Any], selected_app_id: Optional[int] = None) -> None:
        """Render application details in display mode (read-only)."""
        
        st.write(f"**Application ID:** {selected_app_id if selected_app_id else app_details.get('id', 'N/A')}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Submission Method:** {app_details.get('submission_method', 'N/A')}")
            st.write(f"**Date Submitted:** {app_details.get('date_submitted', 'N/A')}")
        
        with col2:
            current_resume = app_details.get('resume_file_path')
            current_cover_letter = app_details.get('cover_letter_file_path')
            
            if current_resume:
                st.write(f"📄 **Resume:** {current_resume}")
            else:
                st.write("📄 **Resume:** None")
            
            if current_cover_letter:
                st.write(f"📄 **Cover Letter File:** {current_cover_letter}")
            else:
                st.write("📄 **Cover Letter File:** None")
        
        # Cover letter text
        if app_details.get('cover_letter_text'):
            st.write("**Cover Letter Text:**")
            cl_key = f"cover_letter_{selected_app_id}" if selected_app_id else "cover_letter"
            st.text_area(
                "Cover Letter Text", 
                value=app_details['cover_letter_text'], 
                height=100, 
                disabled=True, 
                key=cl_key, 
                label_visibility="collapsed"
            )
        
        # Additional questions and notes
        if app_details.get('additional_questions'):
            st.write("**Additional Questions:**")
            aq_key = f"additional_q_{selected_app_id}" if selected_app_id else "additional_q"
            st.text_area(
                "Additional Questions", 
                value=app_details['additional_questions'], 
                height=75, 
                disabled=True, 
                key=aq_key, 
                label_visibility="collapsed"
            )
        
        if app_details.get('application_notes'):
            st.write("**Notes:**")
            notes_key = f"app_notes_{selected_app_id}" if selected_app_id else "app_notes"
            st.text_area(
                "Notes", 
                value=app_details['application_notes'], 
                height=75, 
                disabled=True, 
                key=notes_key, 
                label_visibility="collapsed"
            )
    
    @staticmethod
    def _render_application_edit(app_details: Dict[str, Any], key_prefix: str, selected_app_id: Optional[int] = None) -> Dict[str, Any]:
        """Render application details in edit mode (form fields)."""
        
        # Convert app_details to prefill_data format for the form
        prefill_data = {
            "submission_method": app_details.get('submission_method', ''),
            "date_submitted": app_details.get('date_submitted', ''),
            "cover_letter_text": app_details.get('cover_letter_text', ''),
            "additional_questions": app_details.get('additional_questions', ''),
            "notes": app_details.get('application_notes', '')
        }
        
        # Render the standard application form
        application_data = ApplicationForm.render(key_prefix, prefill_data=prefill_data)
        
        # Add file management section for existing applications
        if selected_app_id:
            st.markdown("**File Management**")
            
            # Show current file paths
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
            
            # Add file information to application data
            application_data["new_resume"] = new_resume
            application_data["new_cover_letter"] = new_cover_letter
            application_data["current_resume_path"] = current_resume
            application_data["current_cover_letter_path"] = current_cover_letter
        
        return application_data
    
    @staticmethod
    def render_expandable_section(title: str, 
                                content_func, 
                                mode: str = "display", 
                                expanded: bool = True,
                                info_message: Optional[str] = None,
                                **kwargs) -> Any:
        """
        Render an expandable section with consistent styling.
        
        Args:
            title: Section title
            content_func: Function that renders the content
            mode: "display" or "edit"
            expanded: Whether section starts expanded
            info_message: Optional info message to show
            **kwargs: Additional arguments passed to content_func
            
        Returns:
            Result from content_func
        """
        
        with st.expander(title, expanded=expanded):
            result = content_func(mode=mode, **kwargs)
            
            if info_message and mode == "display":
                st.info(info_message)
            
            return result
