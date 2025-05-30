# AI Assistant Page
import streamlit as st
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from core.database.base import get_db
from core.controllers.job_posting_controller import JobPostingController
from core.controllers.application_controller import ApplicationController
from core.ui.forms import JobPostingForm, ApplicationForm
from core.ui.base import show_validation_errors, show_operation_result
from core.LLM_backends import LLMBackend, LlamaCppBackend, OllamaBackend, get_ollama_models
from core.langchain_tools import LangChainBackend

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

st.set_page_config(layout="wide", page_title="AI Assistant")
st.title("AI Job Description Assistant")

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
    # Try Ollama first, fallback to local model
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

# Get instances from session state
db: Session = st.session_state.db
job_posting_controller = st.session_state.job_posting_controller
application_controller = st.session_state.application_controller
langchain_backend = st.session_state.langchain_backend

def render_job_description_analyzer():
    """Render the job description analyzer section."""
    with st.expander("Job Description Analyzer", expanded=True):
        # Input area for job description
        job_description = st.text_area(
            "Paste job description here",
            height=200,
            key="job_description_input"
        )

        analyze_col, submit_col = st.columns([1, 1])

        with analyze_col:
            if st.button("Analyze Description", key="analyze_button"):
                if not job_description:
                    st.warning("Please paste a job description first.")
                    return

                with st.spinner("Analyzing job description..."):
                    result = langchain_backend.analyze_job_description(job_description)
                    
                    if result:
                        # Store analysis result in session state for form prefilling
                        st.session_state.analysis_result = {
                            "title": result.title,
                            "description": job_description,
                            "parsed_metadata": {
                                "required_skills": result.required_skills,
                                "preferred_skills": result.preferred_skills,
                                "experience_level": result.experience_level,
                                "education": result.education,
                                "job_type": result.job_type
                            }
                        }
                        st.success("Analysis complete! Review the results below.")
                    else:
                        st.error("Failed to analyze job description. Please try again.")
                        return

                st.divider()
                st.subheader("Analysis Results")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Basic Information**")
                    st.write(f"Title: {result.title}")
                    st.write(f"Job Type: {result.job_type}")
                    st.write(f"Experience Level: {result.experience_level}")
                    st.write(f"Required Education: {result.education}")

                with col2:
                    st.write("**Skills**")
                    st.write("Required Skills:")
                    for skill in result.required_skills:
                        st.write(f"- {skill}")
                    st.write("Preferred Skills:")
                    for skill in result.preferred_skills:
                        st.write(f"- {skill}")

def render_job_posting_form():
    """Render the job posting form with analyzed data."""
    if "analysis_result" not in st.session_state:
        st.info("Analyze a job description to create a job posting.")
        return

    with st.form("create_posting_form"):
        st.subheader("Create Job Posting")
        
        # Pre-fill form with analyzed data
        job_posting_data = JobPostingForm.render(
            "analyzed_jp",
            prefill_data=st.session_state.analysis_result
        )

        submitted = st.form_submit_button("Create Job Posting")
        
        if submitted:
            # Validate job posting data
            jp_errors = JobPostingForm.validate(job_posting_data)
            if show_validation_errors(jp_errors):
                return

            logger.debug(f"Creating job posting with data: {job_posting_data}")
            logger.debug(f"Parsed metadata: {st.session_state.analysis_result.get('parsed_metadata')}")

            # Create job posting with parsed metadata
            jp_result = job_posting_controller.create_job_posting(
                db=db,
                title=job_posting_data["title"],
                company=job_posting_data.get("company", ""),
                description=job_posting_data["description"],
                location=job_posting_data.get("location", ""),
                source_url=job_posting_data.get("source_url", ""),
                date_posted=job_posting_data["date_posted"].isoformat() if job_posting_data.get("date_posted") else None,
                parsed_metadata=st.session_state.analysis_result.get("parsed_metadata")
            )
            
            logger.debug(f"Job posting creation result: {jp_result}")
            
            if show_operation_result(jp_result, "Job posting created successfully!"):
                st.success("You can now find this job posting in the Job Tracker to create an application.")
                # Clear the analysis result to reset the form
                del st.session_state.analysis_result

# Page Layout
render_job_description_analyzer()
st.divider()
render_job_posting_form()