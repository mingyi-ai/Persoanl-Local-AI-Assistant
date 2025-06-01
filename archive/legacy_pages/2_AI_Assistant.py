# AI Assistant Page - Legacy Interface
import streamlit as st
from sqlalchemy.orm import Session
from core.database.base import get_db
from core.controllers.job_posting_controller import JobPostingController
from core.controllers.application_controller import ApplicationController
from core.ui.job_tracker_ui import render_add_job_posting_section
from core.langchain_tools import LangChainBackend
from core.LLM_backends import get_ollama_models, OllamaBackend, LlamaCppBackend

st.set_page_config(layout="wide", page_title="AI Assistant - Legacy")
st.title("🤖 AI Job Description Assistant (Legacy Interface)")

st.info("💡 **Note:** The main AI functionality has been moved to the home page. This page is kept for testing and legacy access.")

# Initialize database session and controllers in Streamlit session state
if 'db' not in st.session_state:
    try:
        st.session_state.db = next(get_db())
        st.session_state.job_posting_controller = JobPostingController()
        st.session_state.application_controller = ApplicationController()
    except StopIteration:
        st.error("Could not connect to database. Please try again.")
        st.stop()

# Initialize AI backend if not already initialized
if 'llm_backend' not in st.session_state:
    available_models = get_ollama_models()
    if available_models:
        st.session_state.llm_backend = OllamaBackend(available_models[0])
    else:
        st.session_state.llm_backend = LlamaCppBackend()

    with st.spinner("Initializing AI model..."):
        if not st.session_state.llm_backend.initialize_model():
            st.error("Failed to initialize AI model. Please check logs.")
            st.stop()
        st.session_state.langchain_backend = LangChainBackend(st.session_state.llm_backend)

# Initialize session state keys if not already set
if 'show_add_job_posting_form' not in st.session_state:
    st.session_state.show_add_job_posting_form = False

# Get instances from session state
db: Session = st.session_state.db
job_posting_controller = st.session_state.job_posting_controller
application_controller = st.session_state.application_controller
langchain_backend = st.session_state.langchain_backend

def render_job_description_analyzer():
    """Render the job description analyzer section."""
    with st.expander("Job Description Analyzer", expanded=True):
        job_description = st.text_area(
            "Paste job description here",
            height=200,
            key="job_description_input"
        )

        if st.button("Analyze Description", key="analyze_button"):
            if not job_description:
                st.warning("Please paste a job description first.")
                return

            with st.spinner("Analyzing job description..."):
                result = langchain_backend.analyze_job_description(job_description)

                # Update the parsed data to include only fields accepted by job_posting_controller
                if result:
                    # Create comprehensive prefill data with validation-friendly structure
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
                    
                    st.success("✅ Analysis complete! Scroll down to create a job posting with this data.")
                else:
                    st.error("Failed to analyze job description. Please try again.")

# Page Layout
render_job_description_analyzer()
st.divider()
render_add_job_posting_section(
    db=db,
    job_posting_controller=job_posting_controller,
    application_controller=application_controller,
    prefill_data=st.session_state.get("analysis_result", {})
)

st.divider()
st.caption("💡 This legacy interface will be maintained for testing. Use the main page for the improved experience.")