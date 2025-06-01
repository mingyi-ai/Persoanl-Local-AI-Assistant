import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from core.database import Base, engine
from core.database.base import get_db
from core.controllers.job_tracker_controller import JobTrackerController
from core.services.prompt_service import PromptService
from core.services.llm_service import LLMService, OllamaBackend, LlamaCppBackend
from core.ui.job_tracker_ui import (
    render_database_display_section,
    render_main_action_tabs
)

# Initialize database by creating all tables (idempotent)
Base.metadata.create_all(bind=engine)

# --- Streamlit App Configuration ---
st.set_page_config(layout="wide", page_title="Job Application Assistant")

st.title("🎯 Job Application Assistant")
st.caption("Manage your job applications with AI assistance")

# --- Initialize Database and Controllers ---
@st.cache_resource
def initialize_controllers():
    """Initialize controllers and database connection."""
    try:
        db = next(get_db())
        job_tracker_controller = JobTrackerController()
        return db, job_tracker_controller
    except StopIteration:
        st.error("Could not connect to database. Please try again.")
        st.stop()

# --- Initialize AI Backend ---
@st.cache_resource
def initialize_ai_backend():
    """Initialize AI backend for job description analysis."""
    with st.spinner("Initializing AI model..."):
        available_models = LLMService.get_ollama_models()
        if available_models:
            llm_backend = OllamaBackend(available_models[0])
        else:
            llm_backend = LlamaCppBackend()
        
        if not llm_backend.initialize_model():
            st.error("Failed to initialize AI model. Please check logs.")
            st.stop()
        
        return PromptService(llm_backend)

# Initialize components
db, job_tracker_controller = initialize_controllers()
prompt_service = initialize_ai_backend()

# --- Data Fetching Function ---
def refresh_applications_display_data(db: Session) -> pd.DataFrame:
    """Fetches applications with their latest status for display."""
    result = job_tracker_controller.get_application_list(db)
    
    if not result.get("success", False):
        return pd.DataFrame()
    
    applications = result.get("applications", [])
    
    if not applications:
        return pd.DataFrame()
    
    # Transform the data for display
    display_data = []
    for app in applications:
        # Extract filename from file paths for display
        resume_name = ""
        cover_letter_name = ""
        
        if app.get('resume_file_path'):
            resume_name = app['resume_file_path'].split('/')[-1]
        
        if app.get('cover_letter_file_path'):
            cover_letter_name = app['cover_letter_file_path'].split('/')[-1]
        
        # Rename date_submitted to job_date_submitted for consistency
        app_data = {
            'application_id': app['application_id'],  # Fixed: use 'application_id' not 'id'
            'job_title': app['job_title'],
            'job_company': app['job_company'],
            'job_date_submitted': app.get('date_submitted', ''),
            'resume_name': resume_name,
            'cover_letter_name': cover_letter_name,
            'submission_method': app.get('submission_method', ''),
            'current_status': app.get('current_status', 'submitted'),
            'status_timestamp': app.get('status_timestamp', '')
        }
        display_data.append(app_data)
    
    return pd.DataFrame(display_data)

# --- Main UI Layout ---

# 1. Database Display Section (Fixed height)
applications_display_df = refresh_applications_display_data(db)
display_columns = [
    'application_id', 'job_title', 'job_company', 'job_date_submitted',
    'resume_name', 'cover_letter_name', 'submission_method',
    'current_status', 'status_timestamp'
]

render_database_display_section(applications_display_df, display_columns)

st.divider()

# 2. Main Action Tabs Section
render_main_action_tabs(
    db, 
    applications_display_df,
    job_tracker_controller, 
    prompt_service
)

# --- Footer ---
st.divider()
st.caption("💡 Tip: Use the application tabs above to manage your job applications and analyze job descriptions.")
