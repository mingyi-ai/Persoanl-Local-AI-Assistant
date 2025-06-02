import streamlit as st

# --- Streamlit App Configuration (MUST BE FIRST) ---
st.set_page_config(layout="wide", page_title="Job Application Assistant")

import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import logging # Added import for logging

from core.database import Base, engine
from core.database.base import get_db
from core.controllers.job_tracker_controller import JobTrackerController
from core.services.file_service import FileService
from core.ui.job_tracker_ui import (
    render_database_display_section,
    render_main_action_tabs
)
from core.ui.llm_setup import (
    render_complete_sidebar,
    initialize_llm_on_startup,
    get_current_prompt_service
)

# Initialize logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Ensure Data Directory Exists ---
# This must be done before database initialization to prevent file path errors
success, message = FileService.ensure_data_directory_exists()
if not success:
    st.error(f"Failed to initialize data directory: {message}")
    st.stop()
else:
    logger.info(message)

# Initialize database by creating all tables (idempotent)
Base.metadata.create_all(bind=engine)

# --- Check for Force Restart Flag ---
if st.session_state.get('force_restart_after_reset', False):
    # Clear the restart flag
    st.session_state.force_restart_after_reset = False
    
    # Force complete reinitialization by clearing all cached resources
    if hasattr(st, 'cache_resource'):
        st.cache_resource.clear()
    
    # Show restart message
    st.info("🔄 Application restarted successfully with fresh database connection.")
    logger.info("Application successfully restarted after database reset")

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
    # This function is now replaced by the LLM setup UI
    # Return None to let the sidebar handle initialization
    return None

# Initialize components
db, job_tracker_controller = initialize_controllers()

# Initialize LLM on startup automatically
initialize_llm_on_startup()

# Render LLM setup sidebar
render_complete_sidebar()

# Get current prompt service for the main app
prompt_service = get_current_prompt_service()

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

# --- Database Management Section (Moved to bottom of main page) ---
st.divider()
st.subheader("Database Management")

# Initialize session state flags if not already present
if 'show_reset_confirmation' not in st.session_state:
    st.session_state.show_reset_confirmation = False
if 'confirm_reset_db' not in st.session_state:
    st.session_state.confirm_reset_db = False

# If "⚠️ Reset Database" is clicked, set flag to show confirmation UI
if st.button("⚠️ Reset Database", key="reset_db_button_main"):
    st.session_state.show_reset_confirmation = True
    st.session_state.confirm_reset_db = False  # Ensure confirmation is reset if main button clicked again
    st.rerun() # Rerun to display the confirmation UI elements

# Display confirmation UI if show_reset_confirmation is true
if st.session_state.show_reset_confirmation:
    st.warning("This action will archive the current database and initialize a new, empty one. This cannot be undone.")
    
    # Use columns for a cleaner layout of confirmation buttons
    col1, col2, col_spacer = st.columns([1, 1, 5]) 
    with col1:
        if st.button("✅ Confirm Reset", key="confirm_reset_action"):
            st.session_state.confirm_reset_db = True       # Set flag to perform reset
            st.session_state.show_reset_confirmation = False # Hide confirmation UI
            st.rerun() # Rerun to process the actual reset action
    with col2:
        if st.button("❌ Cancel", key="cancel_reset_action"):
            st.session_state.confirm_reset_db = False      # Ensure reset is not performed
            st.session_state.show_reset_confirmation = False # Hide confirmation UI
            st.info("Database reset cancelled.")
            st.rerun() # Rerun to clear confirmation UI

# Perform reset if 'confirm_reset_db' is true
# This block is now evaluated independently after a rerun triggered by "Confirm Reset"
if st.session_state.get('confirm_reset_db', False):
    try:
        success, message = job_tracker_controller.reset_database()
        if success:
            st.success(f"Database reset successful: {message}")
            logger.info(f"Database reset successful: {message}")
            
            # CRITICAL: Force complete app restart after database reset
            
            # 1. Clear ALL cached resources and session state
            initialize_controllers.clear()
            if hasattr(initialize_ai_backend, 'clear'):
                initialize_ai_backend.clear()
            
            # 2. Clear ALL session state except the restart flag
            keys_to_keep = {'force_restart_after_reset'}
            keys_to_delete = [key for key in st.session_state.keys() if key not in keys_to_keep]
            for key in keys_to_delete:
                del st.session_state[key]
            
            # 3. Set restart flag and force immediate refresh
            st.session_state.force_restart_after_reset = True
            
            logger.info("Forcing complete application restart after database reset")
            
            # 4. Show restart message and force immediate rerun
            st.info("🔄 Restarting application with fresh database...")
            
            # Use JavaScript to force a complete page refresh for maximum reset
            st.markdown("""
            <script>
                setTimeout(function() {
                    window.location.reload();
                }, 1000);
            </script>
            """, unsafe_allow_html=True)
            
            # Also trigger Streamlit rerun as backup
            st.rerun() 
        else:
            st.error(f"Database reset failed: {message}")
            logger.error(f"Database reset failed: {message}")
    except Exception as e:
        st.error(f"An error occurred during database reset: {e}")
        logger.error(f"Error resetting database from main page UI: {e}", exc_info=True)
    finally:
        # CRITICAL: Always reset the confirmation flag after the attempt
        st.session_state.confirm_reset_db = False
        # No rerun here on failure, so user can see the error message.
        # If a rerun is desired even on failure, it might clear the error too quickly.
