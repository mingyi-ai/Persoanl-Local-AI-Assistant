# Placeholder for AI Assistant page
import streamlit as st
from pathlib import Path
import time
import subprocess # For Ollama CLI interaction

# Attempt to import OllamaLLM, fall back to Ollama if not found
try:
    from langchain_ollama.llms import OllamaLLM
except ImportError:
    try:
        from langchain_community.llms import Ollama
        OllamaLLM = Ollama # Alias if new one not found
        st.warning("Consider upgrading to `langchain-ollama` for the latest Ollama integration. Using fallback `langchain_community.llms.Ollama`.")
    except ImportError:
        OllamaLLM = None # Placeholder if no Ollama integration is found
        st.error("Ollama LLM integration not found. Please install `langchain-ollama` or `langchain-community`.")

from core.db import add_resume, get_all_resumes, add_job_application
from core.file_utils import save_uploaded_file, COVER_LETTERS_DIR, save_cover_letter, get_file_hash
from core.ai_tools import extract_text_from_pdf, score_resume_job_description, generate_cover_letter # Ensure this path is correct relative to how Streamlit runs pages

st.set_page_config(layout="wide", page_title="AI Assistant")
st.title("AI Assistant")
st.caption("Leverage AI to score resumes, generate cover letters, and streamline your application process.")

# --- Session State Initialization (specific to AI Assistant) ---
# Resume related
if 'ai_resume_text' not in st.session_state:
    st.session_state.ai_resume_text = ""
if 'ai_resume_file_path' not in st.session_state:
    st.session_state.ai_resume_file_path = None
if 'ai_resume_id' not in st.session_state: # ID of the resume selected/uploaded in this page
    st.session_state.ai_resume_id = None

# AI processing results
if 'ai_score_result' not in st.session_state:
    st.session_state.ai_score_result = None
if 'ai_reasoning_result' not in st.session_state:
    st.session_state.ai_reasoning_result = ""
if 'ai_cover_letter_result' not in st.session_state:
    st.session_state.ai_cover_letter_result = ""
if 'ai_job_description_input' not in st.session_state: # Stores JD for current AI operations
    st.session_state.ai_job_description_input = ""

# Raw AI responses for debugging/transparency
if 'ai_raw_score_response' not in st.session_state:
    st.session_state.ai_raw_score_response = ""
if 'ai_raw_cl_response' not in st.session_state:
    st.session_state.ai_raw_cl_response = ""

# Model selection and LLM instance (can be shared or page-specific)
# For now, keeping it page-specific to avoid conflicts if app.py also had one.
if 'ai_selected_model_name' not in st.session_state:
    st.session_state.ai_selected_model_name = None
if 'ai_llm_instance' not in st.session_state:
    st.session_state.ai_llm_instance = None
if 'ai_ollama_not_found' not in st.session_state:
    st.session_state.ai_ollama_not_found = False


# --- Helper function to get Ollama models (copied from app.py, consider moving to a utils file) ---
@st.cache_data(show_spinner=False)
def get_ollama_models_ai_page():
    try:
        ollama_cmd_to_run = "ollama"
        result = subprocess.run([ollama_cmd_to_run, "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        models = []
        if len(lines) > 1:
            for line_content in lines[1:]:
                processed_line = line_content.strip()
                if not processed_line: continue
                parts = processed_line.split()
                if parts: models.append(parts[0])
        return models
    except FileNotFoundError:
        st.session_state.ai_ollama_not_found = True 
        return []
    except subprocess.CalledProcessError as e:
        st.error(f"Ollama list command failed: {e.stderr}")
        return []
    except Exception as e:
        st.error(f"An unexpected error occurred while fetching Ollama models: {e}")
        return []

# --- Sidebar for Resume Upload/Selection and Model Selection ---
with st.sidebar:
    st.header("Resume for AI Processing")
    
    # Option 1: Upload a new resume
    st.subheader("Upload New Resume")
    uploaded_resume_ai = st.file_uploader("Choose a PDF file for AI tasks", type="pdf", key="ai_resume_uploader")

    if uploaded_resume_ai is not None:
        saved_path_ai = save_uploaded_file(uploaded_resume_ai) # Uses shared utility
        if saved_path_ai:
            st.session_state.ai_resume_file_path = saved_path_ai
            st.success(f"Resume \'{uploaded_resume_ai.name}\' uploaded.")
            
            st.session_state.ai_resume_text = extract_text_from_pdf(saved_path_ai)
            if not st.session_state.ai_resume_text:
                st.error("Could not extract text from the uploaded resume PDF.")
                st.session_state.ai_resume_file_path = None # Clear if extraction failed
            else:
                file_hash_ai = get_file_hash(saved_path_ai)
                if file_hash_ai:
                    resume_id_ai = add_resume(saved_path_ai, file_hash_ai) # Add to DB
                    if resume_id_ai:
                        st.session_state.ai_resume_id = resume_id_ai
                        st.info(f"New resume added to database with ID: {resume_id_ai}. This resume is now selected.")
                    else:
                        st.error("Failed to add new resume to database.")
                else:
                    st.error("Failed to hash the new resume file.")
        else:
            st.error("Failed to save the uploaded resume.")
            st.session_state.ai_resume_file_path = None

    st.subheader("Or Select Existing Resume")
    available_resumes_ai = get_all_resumes()
    resume_options_ai = {0: "None (or use uploaded if available)"}
    for res_ai in available_resumes_ai:
        resume_options_ai[res_ai['id']] = Path(res_ai['file_path']).name
    
    # Determine default selection for existing resumes
    # If a new one was just uploaded and processed, it takes precedence.
    # Otherwise, use what's in session state or default to "None".
    default_selected_resume_id = st.session_state.get('ai_resume_id', 0)
    if uploaded_resume_ai and st.session_state.ai_resume_id: # If new one just uploaded
         pass # ai_resume_id is already set
    
    selected_existing_resume_id = st.selectbox(
        "Choose an existing resume:",
        options=list(resume_options_ai.keys()),
        format_func=lambda x: resume_options_ai[x],
        index=list(resume_options_ai.keys()).index(default_selected_resume_id) if default_selected_resume_id in resume_options_ai else 0,
        key="ai_existing_resume_selector"
    )

    # Logic to handle selection of an existing resume
    if selected_existing_resume_id != 0 and selected_existing_resume_id != st.session_state.get('ai_resume_id_from_select'): # Check if selection changed
        st.session_state.ai_resume_id_from_select = selected_existing_resume_id # Track selection from this box
        selected_resume_details = next((r for r in available_resumes_ai if r['id'] == selected_existing_resume_id), None)
        if selected_resume_details:
            st.session_state.ai_resume_file_path = selected_resume_details['file_path']
            st.session_state.ai_resume_text = extract_text_from_pdf(st.session_state.ai_resume_file_path)
            st.session_state.ai_resume_id = selected_existing_resume_id # Update the main resume ID for AI tasks
            if not st.session_state.ai_resume_text:
                st.error(f"Could not extract text from selected resume: {Path(st.session_state.ai_resume_file_path).name}")
            else:
                st.info(f"Selected resume: {Path(st.session_state.ai_resume_file_path).name}")
        # If "None" is chosen or if a new resume was uploaded, this part is skipped or reset.
    elif selected_existing_resume_id == 0 and not uploaded_resume_ai : # If "None" is selected and no new upload pending
        if st.session_state.get('ai_resume_id_from_select') != 0: # if it was previously something else
            st.session_state.ai_resume_file_path = None
            st.session_state.ai_resume_text = ""
            st.session_state.ai_resume_id = None
            st.session_state.ai_resume_id_from_select = 0


    if st.session_state.ai_resume_file_path:
        st.markdown(f"**Active Resume for AI:** `{Path(st.session_state.ai_resume_file_path).name}` (ID: {st.session_state.ai_resume_id})")
    else:
        st.info("Please upload or select a resume for AI tasks.")

    st.divider()
    st.header("AI Model Selection")
    if st.session_state.ai_ollama_not_found:
        st.error("Ollama command not found. Ensure Ollama is installed and in PATH.")
        st.session_state.ai_llm_instance = None
    else:
        available_models_ai = get_ollama_models_ai_page()
        if available_models_ai:
            default_model_ai = st.session_state.ai_selected_model_name
            if default_model_ai not in available_models_ai:
                default_model_ai = available_models_ai[0]

            chosen_model_name_ai = st.selectbox(
                "Choose an AI model:",
                options=available_models_ai,
                index=available_models_ai.index(default_model_ai) if default_model_ai in available_models_ai else 0,
                key="ai_ollama_model_selector"
            )

            if st.session_state.ai_llm_instance is None or st.session_state.ai_llm_instance.model != chosen_model_name_ai:
                with st.spinner(f"Initializing AI model: {chosen_model_name_ai}..."):
                    try:
                        st.session_state.ai_llm_instance = OllamaLLM(model=chosen_model_name_ai, timeout=120)
                        st.session_state.ai_selected_model_name = chosen_model_name_ai
                        st.success(f"AI model {chosen_model_name_ai} initialized.")
                    except Exception as e:
                        st.error(f"Failed to initialize model {chosen_model_name_ai}: {e}")
                        st.session_state.ai_llm_instance = None
                        st.session_state.ai_selected_model_name = None
        else:
            st.warning("No Ollama models found or Ollama is not running. AI features will be disabled.")
            st.session_state.ai_llm_instance = None
            st.session_state.ai_selected_model_name = None

# --- Main Area for Job Description, AI Actions, and Output ---
col1_ai, col2_ai = st.columns(2)

with col1_ai:
    st.subheader("Job Details for AI Processing")
    ai_job_title_input = st.text_input("Job Title:", key="ai_job_title")
    ai_company_name_input = st.text_input("Company Name:", key="ai_company_name")
    # Use session state for job description to persist it across reruns if actions are taken
    st.session_state.ai_job_description_input = st.text_area(
        "Paste the full job description here:", 
        value=st.session_state.ai_job_description_input, 
        height=250, 
        key="ai_job_desc_input"
    )

    st.markdown("##### AI Actions")
    ai_features_disabled = st.session_state.ai_llm_instance is None or not st.session_state.ai_resume_text

    score_button_ai = st.button("1. Score Resume", disabled=ai_features_disabled, key="ai_score_btn")
    generate_cl_button_ai = st.button("2. Generate Cover Letter", disabled=ai_features_disabled, key="ai_generate_cl_btn")
    
    st.markdown("##### Save Application")
    # Enable save if job title is present, other fields are optional for saving from AI context
    save_app_button_ai = st.button("3. Save Application to Tracker", key="ai_save_app_btn", disabled=not ai_job_title_input)

# --- Processing Logic for AI Buttons ---
if score_button_ai:
    st.session_state.ai_raw_score_response = "" 
    if not st.session_state.ai_resume_text:
        st.error("Please upload or select a resume first (in the sidebar).")
    elif not st.session_state.ai_job_description_input: # Check the session state version
        st.error("Please paste the job description.")
    # LLM instance check is part of ai_features_disabled
    else:
        with st.spinner(f"AI ({st.session_state.ai_selected_model_name}) is scoring your resume..."):
            score, reasoning, raw_response = score_resume_job_description(
                st.session_state.ai_llm_instance, 
                st.session_state.ai_resume_text, 
                st.session_state.ai_job_description_input # Use session state version
            )
            st.session_state.ai_raw_score_response = raw_response or "No raw response captured."
            if score is not None and reasoning is not None:
                st.session_state.ai_score_result = score
                st.session_state.ai_reasoning_result = reasoning
                st.success("Resume scored successfully!")
            else:
                st.error("Failed to score resume. Check console/Ollama logs for errors.")
                st.session_state.ai_score_result = None
                st.session_state.ai_reasoning_result = "Error during scoring."

if generate_cl_button_ai:
    st.session_state.ai_raw_cl_response = ""
    if not st.session_state.ai_resume_text:
        st.error("Please upload or select a resume first (in the sidebar).")
    elif not st.session_state.ai_job_description_input:
        st.error("Please paste the job description.")
    elif not ai_company_name_input or not ai_job_title_input: # Check direct inputs for these
        st.error("Please enter Company Name and Job Title for the cover letter.")
    # LLM instance check is part of ai_features_disabled
    else:
        with st.spinner(f"AI ({st.session_state.ai_selected_model_name}) is crafting your cover letter..."):
            cover_letter_text, raw_response = generate_cover_letter(
                st.session_state.ai_llm_instance,
                st.session_state.ai_resume_text,
                st.session_state.ai_job_description_input, # Use session state version
                ai_company_name_input, # Use direct input
                ai_job_title_input     # Use direct input
            )
            st.session_state.ai_raw_cl_response = raw_response or "No raw response captured."
            if cover_letter_text and "Error during AI" not in cover_letter_text:
                st.session_state.ai_cover_letter_result = cover_letter_text
                st.success("Cover letter generated!")
            else:
                st.error("Failed to generate cover letter. Check console/Ollama logs for errors.")
                st.session_state.ai_cover_letter_result = cover_letter_text # Store even if error for inspection

if save_app_button_ai:
    if not ai_job_title_input: # Should be disabled, but double check
        st.error("Job Title is required to save the application.")
    else:
        # Save cover letter to file if generated
        cover_letter_file_path_ai = None
        if st.session_state.ai_cover_letter_result:
            filename_prefix_ai = f"{ai_job_title_input}_{ai_company_name_input}".replace(" ", "_").replace("/", "_")
            cover_letter_file_path_ai = save_cover_letter(st.session_state.ai_cover_letter_result, filename_prefix_ai)
            if cover_letter_file_path_ai:
                st.info(f"Generated cover letter saved to: {cover_letter_file_path_ai}")
            else:
                st.warning("Could not save the generated cover letter to a file, will save text to DB if possible.")

        app_id_ai = add_job_application(
            job_title=ai_job_title_input,
            company=ai_company_name_input if ai_company_name_input else None,
            resume_id=st.session_state.ai_resume_id, # From sidebar selection/upload
            job_description=st.session_state.ai_job_description_input if st.session_state.ai_job_description_input else None,
            cover_letter_text=st.session_state.ai_cover_letter_result if not cover_letter_file_path_ai else None, # Store text if not saved to file
            cover_letter_path=cover_letter_file_path_ai,
            ai_score=st.session_state.ai_score_result,
            ai_reasoning=st.session_state.ai_reasoning_result if st.session_state.ai_reasoning_result else None,
            # outcome and notes can be set to defaults or handled in Job Tracker
        )
        if app_id_ai:
            st.success(f"Application for \'{ai_job_title_input}\' saved with ID: {app_id_ai}. View/edit in Job Tracker.")
            # Clear/reset relevant AI page session state for next use
            st.session_state.ai_job_description_input = ""
            st.session_state.ai_score_result = None
            st.session_state.ai_reasoning_result = ""
            st.session_state.ai_cover_letter_result = ""
            st.session_state.ai_raw_score_response = ""
            st.session_state.ai_raw_cl_response = ""
            # Consider clearing job title and company, or let them persist for quick re-use.
            # For now, they will clear on next rerun due to st.text_input behavior without explicit session state backing for them.
            st.rerun() 
        else:
            st.error("Failed to save application to database via AI Assistant page.")


with col2_ai:
    st.subheader("AI Analysis & Generated Content")
    if st.session_state.ai_score_result is not None:
        st.metric(label="Resume Match Score", value=f"{st.session_state.ai_score_result:.0f}/100")
    if st.session_state.ai_reasoning_result:
        with st.expander("Scoring Explanation", expanded=False):
            st.markdown(st.session_state.ai_reasoning_result)
    
    if st.session_state.ai_cover_letter_result:
        st.subheader("Generated Cover Letter")
        st.text_area("Cover Letter Preview", value=st.session_state.ai_cover_letter_result, height=300, key="ai_cl_display_area", disabled=True)

    # Display Raw AI Responses
    if st.session_state.ai_raw_score_response:
        with st.expander("Raw AI Response (Scoring)", expanded=False):
            st.text_area("Raw Scoring Output", value=st.session_state.ai_raw_score_response, height=150, disabled=True, key="ai_raw_score_output")
    
    if st.session_state.ai_raw_cl_response:
        with st.expander("Raw AI Response (Cover Letter)", expanded=False):
            st.text_area("Raw Cover Letter Output", value=st.session_state.ai_raw_cl_response, height=150, disabled=True, key="ai_raw_cl_output")

# Note: The section "Generate Cover Letter & Submit Application" from original Tab 1's expander
# has been integrated into the main flow of this AI Assistant page.
# The AI Assistant page focuses on AI actions first, then saving the application.
