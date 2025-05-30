"""Form classes for the job tracker UI."""
from datetime import datetime
from typing import Optional, Dict, Any, List
import streamlit as st
from ..database import schemas

class BaseForm:
    """Base class for form handling."""
    @staticmethod
    def validate_required(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, str]:
        """Validate required fields in the form data."""
        errors = {}
        for field in required_fields:
            if not data.get(field):
                errors[field] = f"{field.replace('_', ' ').title()} is required"
        return errors

class JobPostingForm(BaseForm):
    """Form for job posting details."""
    @classmethod
    def render(cls, key_prefix: str = "", prefill_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render the job posting form fields."""
        data = {}
        
        data["title"] = st.text_input(
            "Job Title*",
            value=prefill_data.get("title", "") if prefill_data else "",
            key=f"{key_prefix}_title"
        )
        
        data["company"] = st.text_input(
            "Company*",
            value=prefill_data.get("company", "") if prefill_data else "",
            key=f"{key_prefix}_company"
        )
        
        data["location"] = st.text_input(
            "Location",
            value=prefill_data.get("location", "") if prefill_data else "",
            key=f"{key_prefix}_location"
        )
        
        data["description"] = st.text_area(
            "Job Description (paste here)*",
            value=prefill_data.get("description", "") if prefill_data else "",
            height=200,
            key=f"{key_prefix}_description"
        )
        
        data["source_url"] = st.text_input(
            "Job Source URL",
            value=prefill_data.get("source_url", "") if prefill_data else "",
            key=f"{key_prefix}_source_url"
        )
        
        date_posted_str = prefill_data.get("date_posted", "") if prefill_data else ""
        try:
            date_posted_val = datetime.strptime(date_posted_str, "%Y-%m-%d").date() if date_posted_str else None
        except ValueError:
            date_posted_val = None
            
        data["date_posted"] = st.date_input(
            "Date Posted (if known)",
            value=date_posted_val,
            key=f"{key_prefix}_date_posted"
        )

        return data

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate the job posting form data."""
        required_fields = ["title", "company", "description"]
        return cls.validate_required(data, required_fields)

class ApplicationForm(BaseForm):
    """Form for application details."""
    @classmethod
    def render(cls, key_prefix: str = "", prefill_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render the application form fields."""
        data = {}
        
        data["submission_method"] = st.selectbox(
            "Submission Method",
            options=list(schemas.SubmissionMethod) + [None],
            index=0,
            key=f"{key_prefix}_submission_method"
        )
        
        data["notes"] = st.text_area(
            "Application Notes",
            value=prefill_data.get("notes", "") if prefill_data else "",
            height=75,
            key=f"{key_prefix}_notes"
        )
        
        data["date_submitted"] = st.date_input(
            "Submission Date",
            value=datetime.now().date(),
            key=f"{key_prefix}_date_submitted"
        )
        
        data["resume"] = st.file_uploader(
            "Upload Resume (Optional)",
            type=["pdf", "docx", "txt"],
            key=f"{key_prefix}_resume"
        )
        
        data["cover_letter"] = st.file_uploader(
            "Upload Cover Letter (Optional)",
            type=["pdf", "docx", "txt"],
            key=f"{key_prefix}_cover_letter"
        )

        return data

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate the application form data."""
        # No required fields for application form
        return {}

class ApplicationStatusForm(BaseForm):
    """Form for application status updates."""
    @classmethod
    def render(cls, key_prefix: str = "", prefill_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render the status form fields."""
        data = {}
        
        data["status"] = st.selectbox(
            "Status",
            options=['submitted', 'viewed', 'screening', 'interview', 'assessment', 'offer', 'rejected', 'withdrawn', 'other'],
            key=f"{key_prefix}_status"
        )
        
        data["source_text"] = st.text_area(
            "Source/Notes (e.g., email content, call summary)",
            value=prefill_data.get("source_text", "") if prefill_data else "",
            height=75,
            key=f"{key_prefix}_source_text"
        )

        return data

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate the status form data."""
        required_fields = ["status"]
        return cls.validate_required(data, required_fields)

class FileSelectionForm(BaseForm):
    """Form for selecting files from existing ones."""
    @classmethod
    def render(cls, key_prefix: str = "", available_files: Dict[int, str] = None, current_file_id: Optional[int] = None) -> Dict[str, Any]:
        """Render the file selection form fields."""
        if available_files is None:
            available_files = {0: "None"}
        
        file_keys = list(available_files.keys())
        try:
            file_index = file_keys.index(current_file_id if current_file_id in file_keys else 0)
        except ValueError:
            file_index = file_keys.index(0)
            
        selected_id = st.selectbox(
            f"Select {key_prefix.replace('_', ' ').title()}",
            options=file_keys,
            format_func=lambda x: available_files[x],
            index=file_index,
            key=f"{key_prefix}_file_select"
        )
        
        return {"file_id": selected_id if selected_id != 0 else None}
