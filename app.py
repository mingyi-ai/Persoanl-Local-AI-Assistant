import streamlit as st
from core.db import init_db

# Initialize database (idempotent)
init_db()

# --- Streamlit App UI ---
st.set_page_config(layout="wide", page_title="Job Application Assistant")

st.title("Welcome to the Job Application Assistant!")
st.caption("Navigate using the sidebar to access the Job Tracker or AI Assistant.")

st.info(
    """ 
    **Getting Started:**

    -   **Job Tracker:** Manage and track your job applications. You can manually add new applications,
        view existing ones, update their status, and add custom details.
        
    -   **AI Assistant:** Leverage AI to help with your job applications. 
        Upload or select a resume, provide a job description, and the AI can:
        -   Score your resume against the job description.
        -   Generate a tailored cover letter.
        You can then save the application details, along with AI-generated content, to the Job Tracker.

    Use the sidebar to navigate to the desired section.
    """
)

# Note: No explicit tab creation here. Streamlit handles page navigation
# when files are placed in the 'pages/' directory.

# Session state initializations that were global in the original app.py
# should now be handled within their respective pages (1_Job_Tracker.py, 2_AI_Assistant.py)
# or be truly global if needed by multiple pages and initialized here carefully.
# For this refactoring, most session states were moved to be page-specific.

# The get_ollama_models() helper function, if needed by multiple pages,
# could be moved to a utility file in `core/` and imported by each page.
# For now, a version of it is in 2_AI_Assistant.py.

# Sidebar content that was previously in app.py (like resume upload or model selection)
# has been moved to the relevant pages (primarily 2_AI_Assistant.py).
