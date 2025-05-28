import streamlit as st
from pathlib import Path
import os
from langchain_community.llms import Ollama # Ensure this import is present
import subprocess

from core.file_utils import save_uploaded_file, get_file_hash
from core.db import add_resume, add_job_application, get_all_applications, init_db
from core.job_parser import score_resume_job_description, generate_cover_letter, extract_text_from_pdf

# Initialize database (idempotent)
init_db()

# --- Streamlit App UI ---
st.set_page_config(layout="wide", page_title="Job Application Assistant")

st.title("Local Job Application Assistant")
st.caption("Upload your resume, paste a job description, and let AI help you!")

# --- Session State Initialization ---
if 'resume_text' not in st.session_state:
    st.session_state.resume_text = ""
if 'resume_file_path' not in st.session_state:
    st.session_state.resume_file_path = None
if 'resume_id' not in st.session_state:
    st.session_state.resume_id = None
if 'ai_score' not in st.session_state:
    st.session_state.ai_score = None
if 'ai_reasoning' not in st.session_state:
    st.session_state.ai_reasoning = ""
if 'cover_letter' not in st.session_state:
    st.session_state.cover_letter = ""
if 'job_description' not in st.session_state:
    st.session_state.job_description = ""
if 'raw_ai_response_score' not in st.session_state: # ADDED
    st.session_state.raw_ai_response_score = "" # ADDED
if 'raw_ai_response_cl' not in st.session_state: # ADDED
    st.session_state.raw_ai_response_cl = "" # ADDED
if 'selected_model_name' not in st.session_state: # Stores the name of the selected model
    st.session_state.selected_model_name = None
if 'llm_instance' not in st.session_state: # Stores the Ollama llm object
    st.session_state.llm_instance = None

# --- Helper function to get Ollama models ---
@st.cache_data(show_spinner=False) # Cache the list of models
def get_ollama_models():
    try:
        ollama_cmd_to_run = "ollama"
        print(f"DEBUG: Attempting to run: {ollama_cmd_to_run} list")
        result = subprocess.run([ollama_cmd_to_run, "list"], capture_output=True, text=True, check=True)
        
        print(f"DEBUG: Ollama list stdout (raw):\n--START STDOUT--\n{result.stdout}\n--END STDOUT--")
        print(f"DEBUG: Ollama list stderr (raw):\n--START STDERR--\n{result.stderr}\n--END STDERR--")

        stripped_stdout = result.stdout.strip()
        print(f"DEBUG: Ollama list stdout (stripped):\n--START STRIPPED STDOUT--\n{stripped_stdout}\n--END STRIPPED STDOUT--")

        lines = stripped_stdout.split('\n')
        print(f"DEBUG: Parsed lines list (length {len(lines)}): {lines}")

        models = []
        if len(lines) > 1:  # Expecting header + data lines
            print("DEBUG: Processing lines for models (skipping header)...")
            # Start from index 1 to skip the header line
            for i, line_content in enumerate(lines[1:], start=1):
                print(f"DEBUG:   Line {i} (original index in lines list): '{line_content}'")
                # Strip individual line just in case there are leading/trailing spaces on the line itself
                processed_line = line_content.strip()
                print(f"DEBUG:     Line {i} (stripped): '{processed_line}'")
                
                if not processed_line: # If the line is empty after stripping, skip it
                    print(f"DEBUG:     Line {i} is empty after strip, skipping.")
                    continue

                parts = processed_line.split() # Split by any whitespace
                print(f"DEBUG:     Line {i} parts from split: {parts}")
                
                if parts: # If split produced a non-empty list
                    models.append(parts[0])
                    print(f"DEBUG:       Appended model: {parts[0]}")
                else:
                    print(f"DEBUG:     Line {i} produced no parts after split.")
        else:
            print("DEBUG: Not enough lines to process for models (len(lines) <= 1). Output might be empty or header-only.")
        
        if not models and stripped_stdout: 
             print("DEBUG: Ollama list ran and produced output, but no models were successfully parsed from it.")
        elif not models:
             print("DEBUG: No models parsed, and stdout was empty or only whitespace.")
        else:
            print(f"DEBUG: Successfully parsed models: {models}")

        return models
    except FileNotFoundError:
        print(f"Ollama command ('{ollama_cmd_to_run}') not found. Ensure Ollama is installed and in PATH.")
        st.session_state.ollama_not_found = True 
        return []
    except subprocess.CalledProcessError as e:
        print(f"Ollama list command failed with error: {e}")
        print(f"Ollama list stdout (on error):\\n{e.stdout}")
        print(f"Ollama list stderr (on error):\\n{e.stderr}")
        # Don't set ollama_not_found = True here, as ollama might be running but 'list' failed
        return []
    except Exception as e:
        print(f"An unexpected error occurred while fetching Ollama models: {e}")
        return []

if 'ollama_not_found' not in st.session_state:
    st.session_state.ollama_not_found = False

# --- Sidebar for Resume Upload and Model Selection ---
with st.sidebar:
    st.header("Upload Your Resume")
    uploaded_resume = st.file_uploader("Choose a PDF file", type="pdf")

    if uploaded_resume is not None:
        # Save the uploaded file and get its path
        saved_path = save_uploaded_file(uploaded_resume)
        if saved_path:
            st.session_state.resume_file_path = saved_path
            st.success(f"Resume '{uploaded_resume.name}' uploaded and saved.")
            
            # Extract text from PDF for processing
            st.session_state.resume_text = extract_text_from_pdf(saved_path)
            if not st.session_state.resume_text:
                st.error("Could not extract text from the resume PDF.")
                st.session_state.resume_file_path = None
            else:
                # Add to DB and get ID
                file_hash = get_file_hash(saved_path)
                if file_hash:
                    resume_id = add_resume(saved_path, file_hash)
                    if resume_id:
                        st.session_state.resume_id = resume_id
                        st.info(f"Resume added to database with ID: {resume_id}")
                    else:
                        st.error("Failed to add resume to database.")
                else:
                    st.error("Failed to hash the resume file.")
        else:
            st.error("Failed to save the uploaded resume.")
            st.session_state.resume_file_path = None


    if st.session_state.resume_file_path:
        st.markdown(f"**Current Resume:** `{Path(st.session_state.resume_file_path).name}`")
    else:
        st.info("Please upload a resume to begin.")

    st.divider()
    st.header("AI Model Selection")

    if st.session_state.ollama_not_found:
        st.error("Ollama command not found. Please ensure Ollama is installed and in your PATH.")
        st.session_state.llm_instance = None # Ensure AI features are disabled
    else:
        available_models = get_ollama_models()
        if available_models:
            # Determine the model to be selected in the selectbox
            # Priority: 1. Current session's selected_model_name if valid, 2. First available model
            default_selection = st.session_state.selected_model_name
            if default_selection not in available_models:
                default_selection = available_models[0]

            chosen_model_name = st.selectbox(
                "Choose an AI model:",
                options=available_models,
                index=available_models.index(default_selection),
                key="ollama_model_selector"
            )

            # Initialize or update LLM instance if needed
            if st.session_state.llm_instance is None or st.session_state.llm_instance.model != chosen_model_name:
                with st.spinner(f"Initializing AI model: {chosen_model_name}..."):
                    st.session_state.llm_instance = Ollama(model=chosen_model_name)
                st.session_state.selected_model_name = chosen_model_name # Update session state
                # st.success(f"Model {chosen_model_name} ready.") # Optional: can be a bit noisy
        else:
            st.warning("No Ollama models found or Ollama is not running. AI features will be disabled.")
            st.session_state.llm_instance = None # Disable AI features
            st.session_state.selected_model_name = None


# --- Main Area for Job Description and Actions ---
col1, col2 = st.columns(2)

with col1:
    st.header("Job Description")
    job_desc_input = st.text_area("Paste the full job description here:", height=300, key="job_desc_input_key")
    # Update session state directly if using a key that persists across reruns,
    # or handle it via button actions if preferred.
    # For simplicity, we'll read from job_desc_input when buttons are pressed.

    st.header("Company & Role (for Cover Letter)")
    company_name = st.text_input("Company Name:")
    job_title = st.text_input("Job Title:")

    # Action Buttons
    st.markdown("### Actions")
    # Disable AI-related buttons if no LLM instance is available
    ai_features_disabled = st.session_state.llm_instance is None

    score_button = st.button("1. Score Resume vs. Job Description", disabled=ai_features_disabled)
    generate_cl_button = st.button("2. Generate Cover Letter", disabled=ai_features_disabled)
    save_app_button = st.button("3. Save Application to Database") # Save button is always enabled

# --- Processing Logic for Buttons ---
if score_button:
    current_job_desc = job_desc_input # Get current value from text_area
    st.session_state.raw_ai_response_score = "" # Clear previous raw response
    if not st.session_state.resume_text:
        st.error("Please upload a resume first.")
    elif not current_job_desc:
        st.error("Please paste the job description.")
    # llm_instance check is implicitly handled by button's disabled state, but good for robustness
    elif st.session_state.llm_instance is None:
        st.error("AI model not available. Please select a model or check Ollama setup.")
    else:
        with st.spinner(f"AI ({st.session_state.selected_model_name}) is scoring your resume..."):
            score, reasoning, raw_response = score_resume_job_description(st.session_state.llm_instance, st.session_state.resume_text, current_job_desc) # MODIFIED
            st.session_state.raw_ai_response_score = raw_response or "No raw response captured." # ADDED
            if score is not None and reasoning is not None:
                st.session_state.ai_score = score
                st.session_state.ai_reasoning = reasoning
                st.success("Resume scored successfully!")
            else:
                st.error("Failed to score resume. Check console/Ollama logs for errors.")
                st.session_state.ai_score = None
                st.session_state.ai_reasoning = "Error during scoring."
            st.session_state.job_description = current_job_desc # Save for display/saving app

if generate_cl_button:
    current_job_desc = job_desc_input
    st.session_state.raw_ai_response_cl = "" # Clear previous raw response
    if not st.session_state.resume_text:
        st.error("Please upload a resume first.")
    elif not current_job_desc:
        st.error("Please paste the job description.")
    elif not company_name or not job_title:
        st.error("Please enter Company Name and Job Title for the cover letter.")
    elif st.session_state.llm_instance is None:
        st.error("AI model not available. Please select a model or check Ollama setup.")
    else:
        with st.spinner(f"AI ({st.session_state.selected_model_name}) is crafting your cover letter..."):
            cover_letter_text, raw_response = generate_cover_letter( # MODIFIED
                st.session_state.llm_instance,
                st.session_state.resume_text,
                current_job_desc,
                company_name,
                job_title
            )
            st.session_state.raw_ai_response_cl = raw_response or "No raw response captured." # ADDED
            if cover_letter_text and "Error during AI" not in cover_letter_text :
                st.session_state.cover_letter = cover_letter_text
                st.success("Cover letter generated!")
            else:
                st.error("Failed to generate cover letter. Check console/Ollama logs for errors.")
                st.session_state.cover_letter = cover_letter_text # Store error message if any
            st.session_state.job_description = current_job_desc # Save for display/saving app


if save_app_button:
    # Use job_description from session state, which should be updated by score/CL actions
    # or directly from input if those weren't run.
    current_job_desc = job_desc_input if not st.session_state.job_description else st.session_state.job_description
    if not st.session_state.resume_id:
        st.error("No resume has been processed and saved. Please upload a resume first.")
    elif not current_job_desc: # Check current_job_desc from input
        st.error("Please provide a job description.")
    else:
        app_id = add_job_application(
            resume_id=st.session_state.resume_id,
            job_description=current_job_desc, # Use the most recent job description
            cover_letter_text=st.session_state.cover_letter if st.session_state.cover_letter else None,
            ai_score=st.session_state.ai_score if st.session_state.ai_score is not None else None,
            ai_reasoning=st.session_state.ai_reasoning if st.session_state.ai_reasoning else None
        )
        if app_id:
            st.success(f"Application saved to database with ID: {app_id}")
            # Clear relevant session state for the next application, except for resume and model
            st.session_state.job_description = ""
            st.session_state.ai_score = None
            st.session_state.ai_reasoning = ""
            st.session_state.cover_letter = ""
            # To clear the text_area, you might need to change its key or use st.rerun()
            # For now, we'll let it persist until the user changes it or a new score/CL is generated.
            st.rerun() 
        else:
            st.error("Failed to save application to database.")

# --- Display Area for AI Output and Cover Letter ---
with col2:
    st.header("AI Analysis & Cover Letter")
    if st.session_state.ai_score is not None: # Check if score exists
        st.metric(label="Resume Match Score", value=f"{st.session_state.ai_score:.0f}/100")
    if st.session_state.ai_reasoning: # Check if reasoning exists
        st.subheader("Scoring Explanation")
        st.markdown(st.session_state.ai_reasoning)
    
    if st.session_state.cover_letter: # Check if cover letter exists
        st.subheader("Generated Cover Letter")
        st.text_area("Cover Letter", value=st.session_state.cover_letter, height=400, key="cl_display_area", disabled=True)

    # Display Raw AI Responses
    if st.session_state.raw_ai_response_score: # ADDED
        with st.expander("Raw AI Response (Scoring)", expanded=False): # ADDED
            st.text_area("Raw Scoring Output", value=st.session_state.raw_ai_response_score, height=200, disabled=True, key="raw_score_output") # ADDED
    
    if st.session_state.raw_ai_response_cl: # ADDED
        with st.expander("Raw AI Response (Cover Letter)", expanded=False): # ADDED
            st.text_area("Raw Cover Letter Output", value=st.session_state.raw_ai_response_cl, height=200, disabled=True, key="raw_cl_output") # ADDED

# --- Display Saved Applications ---
st.divider()
st.header("Saved Applications")
applications = get_all_applications()
if applications:
    for app_idx, app_data in enumerate(applications):
        app_id, resume_path, job_desc, cl_text, timestamp, score, reasoning = app_data
        expander_title = f"ID: {app_id} - Submitted: {timestamp.split('.')[0]}"
        if score is not None:
            expander_title += f" - Score: {score:.0f}/100"
        else:
            expander_title += " - Score: N/A"

        with st.expander(expander_title):
            st.markdown(f"**Resume File:** `{Path(resume_path).name}`")
            st.markdown("**Job Description:**")
            st.text_area("JD", value=job_desc, height=150, disabled=True, key=f"jd_{app_id}_{app_idx}")
            if cl_text:
                st.markdown("**Cover Letter:**")
                st.text_area("CL", value=cl_text, height=200, disabled=True, key=f"cl_{app_id}_{app_idx}")
            if score is not None and reasoning:
                st.markdown("**AI Score & Reasoning:**")
                st.markdown(f"Score: {score:.0f}/100") # Ensure score is formatted if it exists
                st.markdown(f"Reasoning: {reasoning}")
            elif score is not None: # Only score, no reasoning
                 st.markdown(f"**AI Score:** {score:.0f}/100")
else:
    st.info("No applications saved yet.")
