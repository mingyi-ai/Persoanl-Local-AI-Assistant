"""Form classes for the job tracker UI."""
from datetime import datetime
from typing import Optional, Dict, Any, List
import streamlit as st
from ..database import schemas
from .base import show_validation_warnings

class BaseForm:
    """Base class for form handling with standardized prefill interface."""
    
    @staticmethod
    def validate_required(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, str]:
        """Validate required fields in the form data."""
        errors = {}
        for field in required_fields:
            if not data.get(field):
                errors[field] = f"{field.replace('_', ' ').title()} is required"
        return errors
    
    @staticmethod
    def _get_prefill_value(prefill_data: Optional[Dict[str, Any]], field: str, default: Any = ""):
        """Safely extract prefill value with fallback to default."""
        if not prefill_data:
            return default
        return prefill_data.get(field, default)
    
    @staticmethod
    def _validate_prefill_data(prefill_data: Optional[Dict[str, Any]], expected_fields: List[str]) -> Dict[str, str]:
        """Validate prefill data and return warnings for invalid fields."""
        warnings = {}
        if not prefill_data:
            return warnings
        
        # Known legacy fields that can be safely ignored
        legacy_fields = {'parsed_metadata', 'id', 'created_at', 'updated_at'}
            
        for field, value in prefill_data.items():
            if field not in expected_fields and field not in legacy_fields:
                warnings[field] = f"Unexpected field '{field}' in prefill data"
            elif value is None:
                warnings[field] = f"Field '{field}' has null value in prefill data"
                
        return warnings

class JobPostingForm(BaseForm):
    """Form for job posting details with standardized prefill support."""
    
    EXPECTED_FIELDS = ["title", "company", "location", "type", "seniority", "description", "source_url", "date_posted", "tags", "skills", "industry"]
    
    @classmethod
    def render(cls, key_prefix: str = "", prefill_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render the job posting form fields with prefill support."""
        # Validate prefill data and show warnings if needed
        if prefill_data:
            warnings = cls._validate_prefill_data(prefill_data, cls.EXPECTED_FIELDS)
            show_validation_warnings(warnings)
        
        data = {}
        
        data["title"] = st.text_input(
            "Job Title*",
            value=cls._get_prefill_value(prefill_data, "title"),
            key=f"{key_prefix}_title",
            help="AI-parsed" if prefill_data and "title" in prefill_data else None
        )
        
        data["company"] = st.text_input(
            "Company*",
            value=cls._get_prefill_value(prefill_data, "company"),
            key=f"{key_prefix}_company",
            help="AI-parsed" if prefill_data and "company" in prefill_data else None
        )
        
        data["location"] = st.text_input(
            "Location",
            value=cls._get_prefill_value(prefill_data, "location"),
            key=f"{key_prefix}_location",
            help="AI-parsed" if prefill_data and "location" in prefill_data else None
        )

        data["type"] = st.selectbox(
            "Job Type",
            options=["Full-time", "Part-time", "Contract", "Temporary", "Internship", "Freelance", "Other"],
            # options=list(schemas.JobType),  # schemas.JobType to do later
            index=0,  # Default to first option
            key=f"{key_prefix}_type",
            help="AI-suggested" if prefill_data and "type" in prefill_data else None
        )

        data["seniority"] = st.selectbox(
            "Seniority Level",
            # options=list(schemas.SeniorityLevel), # schemas.SeniorityLevel to do later
            options=["Entry", "Mid-Senior", "Director", "Executive", "Intern", "Other"], 
            index=0,  # Default to first option
            key=f"{key_prefix}_seniority",
            help="AI-suggested" if prefill_data and "seniority" in prefill_data else None
        )
        
        data["description"] = st.text_area(
            "Job Description (paste here)*",
            value=cls._get_prefill_value(prefill_data, "description"),
            height=200,
            key=f"{key_prefix}_description",
            help="AI-parsed" if prefill_data and "description" in prefill_data else None
        )
        
        data["source_url"] = st.text_input(
            "Job Source URL",
            value=cls._get_prefill_value(prefill_data, "source_url"),
            key=f"{key_prefix}_source_url",
            help="AI-parsed" if prefill_data and "source_url" in prefill_data else None
        )
        
        # Handle date parsing more gracefully
        date_posted_str = cls._get_prefill_value(prefill_data, "date_posted")
        date_posted_val = None
        if date_posted_str:
            try:
                if isinstance(date_posted_str, str):
                    date_posted_val = datetime.strptime(date_posted_str, "%Y-%m-%d").date()
                elif hasattr(date_posted_str, 'date'):
                    date_posted_val = date_posted_str.date()
                else:
                    date_posted_val = date_posted_str
            except (ValueError, TypeError):
                st.warning(f"Invalid date format in prefill data: {date_posted_str}")
                date_posted_val = None
            
        data["date_posted"] = st.date_input(
            "Date Posted (if known)",
            value=date_posted_val,
            key=f"{key_prefix}_date_posted",
            help="AI-parsed" if prefill_data and "date_posted" in prefill_data else None
        )

        data["tags"] = st.text_input(
            "Tags (comma-separated, Optional)",
            value=cls._get_prefill_value(prefill_data, "tags"),
            key=f"{key_prefix}_tags",
            help="AI-suggested" if prefill_data and "tags" in prefill_data else None
        )

        data["skills"] = st.text_input(
            "Skills (comma-separated, Optional)",
            value=cls._get_prefill_value(prefill_data, "skills"),
            key=f"{key_prefix}_skills",
            help="AI-suggested" if prefill_data and "skills" in prefill_data else None
        )

        data["industry"] = st.text_input(
            "Industry (Optional)",
            value=cls._get_prefill_value(prefill_data, "industry"),
            key=f"{key_prefix}_industry",
            help="AI-suggested" if prefill_data and "industry" in prefill_data else None
        )

        return data

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate the job posting form data."""
        required_fields = ["title", "company", "description"]
        return cls.validate_required(data, required_fields)

class ApplicationForm(BaseForm):
    """Form for application details with standardized prefill support."""
    
    EXPECTED_FIELDS = ["submission_method", "date_submitted", "cover_letter_text", "additional_questions", "notes"]
    
    @classmethod
    def render(cls, key_prefix: str = "", prefill_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render the application form fields with prefill support."""
        # Validate prefill data and show warnings if needed
        if prefill_data:
            warnings = cls._validate_prefill_data(prefill_data, cls.EXPECTED_FIELDS)
            show_validation_warnings(warnings)
        
        data = {}
        
        # Handle submission method with prefill
        submission_method_options = list(schemas.SubmissionMethod) + [None]
        prefill_submission = cls._get_prefill_value(prefill_data, "submission_method")
        
        # Find index for prefilled value
        submission_index = 0
        if prefill_submission and prefill_submission in submission_method_options:
            submission_index = submission_method_options.index(prefill_submission)
        
        data["submission_method"] = st.selectbox(
            "Submission Method",
            options=submission_method_options,
            index=submission_index,
            key=f"{key_prefix}_submission_method",
            help="AI-suggested" if prefill_data and "submission_method" in prefill_data else None
        )

        # Handle date with prefill
        prefill_date = cls._get_prefill_value(prefill_data, "date_submitted")
        date_value = datetime.now().date()
        
        if prefill_date:
            try:
                if isinstance(prefill_date, str):
                    date_value = datetime.strptime(prefill_date, "%Y-%m-%d").date()
                elif hasattr(prefill_date, 'date'):
                    date_value = prefill_date.date()
                else:
                    date_value = prefill_date
            except (ValueError, TypeError):
                st.warning(f"Invalid date format in prefill data: {prefill_date}")
                date_value = datetime.now().date()
        
        data["date_submitted"] = st.date_input(
            "Submission Date",
            value=date_value,
            key=f"{key_prefix}_date_submitted",
            help="AI-suggested" if prefill_data and "date_submitted" in prefill_data else None
        )
        
        data["resume"] = st.file_uploader(
            "Upload Resume (Optional)",
            type=["pdf", "docx", "txt"],
            key=f"{key_prefix}_resume"
        )
        
        data["cover_letter_text"] = st.text_area(
            "Cover Letter (Optional)",
            value=cls._get_prefill_value(prefill_data, "cover_letter"),
            height=150,
            key=f"{key_prefix}_cover_letter_text",
            help="Paste your cover letter here or upload a file below"
        )

        data["cover_letter_file"] = st.file_uploader(
            "Upload Cover Letter File (Optional)",
            type=["pdf", "docx", "txt"],
            key=f"{key_prefix}_cover_letter_file"
        )

        data["additional_questions"] = st.text_area(
            "Additional Questions (JSON format, Optional)",
            value=cls._get_prefill_value(prefill_data, "additional_questions"),
            height=75,
            key=f"{key_prefix}_additional_questions",
            help="AI-generated" if prefill_data and "additional_questions" in prefill_data else None
        )
        
        data["notes"] = st.text_area(
            "Notes (Optional)",
            value=cls._get_prefill_value(prefill_data, "notes"),
            height=75,
            key=f"{key_prefix}_notes",
            help="AI-generated" if prefill_data and "notes" in prefill_data else None
        )
    

        return data

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate the application form data."""
        # No required fields for application form
        return {}

class ApplicationStatusForm(BaseForm):
    """Form for application status updates with standardized prefill support."""
    
    EXPECTED_FIELDS = ["status", "source_text"]
    
    @classmethod
    def render(cls, key_prefix: str = "", prefill_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render the status form fields with prefill support."""
        # Validate prefill data and show warnings if needed
        if prefill_data:
            warnings = cls._validate_prefill_data(prefill_data, cls.EXPECTED_FIELDS)
            show_validation_warnings(warnings)
        
        data = {}
        
        # Handle status with prefill
        status_options = ['submitted', 'viewed', 'screening', 'interview', 'assessment', 'offer', 'rejected', 'withdrawn', 'other']
        prefill_status = cls._get_prefill_value(prefill_data, "status")
        
        status_index = 0
        if prefill_status and prefill_status in status_options:
            status_index = status_options.index(prefill_status)
        
        data["status"] = st.selectbox(
            "Status",
            options=status_options,
            index=status_index,
            key=f"{key_prefix}_status",
            help="AI-detected" if prefill_data and "status" in prefill_data else None
        )
        
        data["source_text"] = st.text_area(
            "Source/Notes (e.g., email content, call summary)",
            value=cls._get_prefill_value(prefill_data, "source_text"),
            height=75,
            key=f"{key_prefix}_source_text",
            help="AI-extracted" if prefill_data and "source_text" in prefill_data else None
        )

        return data

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> Dict[str, str]:
        """Validate the status form data."""
        required_fields = ["status"]
        return cls.validate_required(data, required_fields)

class FileSelectionForm(BaseForm):
    """Form for selecting files from existing ones with standardized interface."""
    
    @classmethod
    def render(cls, key_prefix: str = "", available_files: Dict[int, str] = None, current_file_id: Optional[int] = None, prefill_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Render the file selection form fields with prefill support."""
        if available_files is None:
            available_files = {0: "None"}
        
        # Use prefill_data if provided, otherwise use current_file_id
        target_file_id = current_file_id
        if prefill_data and f"{key_prefix}_file_id" in prefill_data:
            target_file_id = prefill_data.get(f"{key_prefix}_file_id")
        
        file_keys = list(available_files.keys())
        try:
            file_index = file_keys.index(target_file_id if target_file_id in file_keys else 0)
        except ValueError:
            file_index = file_keys.index(0)
            
        selected_id = st.selectbox(
            f"Select {key_prefix.replace('_', ' ').title()}",
            options=file_keys,
            format_func=lambda x: available_files[x],
            index=file_index,
            key=f"{key_prefix}_file_select",
            help="AI-suggested" if prefill_data and f"{key_prefix}_file_id" in prefill_data else None
        )
        
        return {"file_id": selected_id if selected_id != 0 else None}
