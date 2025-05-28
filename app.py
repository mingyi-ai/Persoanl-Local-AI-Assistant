import streamlit as st
from pathlib import Path
import time
import pandas as pd # Make sure pandas is imported
from datetime import datetime, date # Ensure date is imported
import json # For custom fields
import logging # For logging
import subprocess # Added import for subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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

from core.db import (add_resume, get_all_resumes, add_job_application, 
                     get_all_applications, get_application_by_id, 
                     update_job_application, delete_job_application, init_db)
from core.file_utils import save_uploaded_file, COVER_LETTERS_DIR, save_cover_letter, get_file_hash # Added get_file_hash
from core.job_parser import extract_text_from_pdf, score_resume_job_description, generate_cover_letter # Corrected import to score_resume_job_description

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
if 'editing_app_id' not in st.session_state: # For tracking which app is being edited
    st.session_state.editing_app_id = None
if 'show_add_manual_form' not in st.session_state: # To toggle manual add form
    st.session_state.show_add_manual_form = False
if 'custom_fields_input' not in st.session_state:
    st.session_state.custom_fields_input = {}
if 'clear_new_cf_inputs_manual_add' not in st.session_state: # ADDED for clearing custom field inputs
    st.session_state.clear_new_cf_inputs_manual_add = False   # ADDED

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

# --- Define Tabs ---
tab1, tab2 = st.tabs(["Process New Application", "Track Applications"])

with tab1:
    st.header("Process a New Job Application")
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
                    index=available_models.index(default_selection) if default_selection in available_models else 0, # Ensure index is valid
                    key="ollama_model_selector_tab1" # Unique key for this selectbox
                )

                # Initialize or update LLM instance if needed
                if st.session_state.llm_instance is None or st.session_state.llm_instance.model != chosen_model_name:
                    with st.spinner(f"Initializing AI model: {chosen_model_name}..."):
                        try: # Add try-except for model initialization
                            # Added timeout to Ollama initialization and used updated class
                            st.session_state.llm_instance = OllamaLLM(model=chosen_model_name, timeout=120) 
                            st.session_state.selected_model_name = chosen_model_name # Update session state
                            st.success(f"AI model {chosen_model_name} initialized.")
                        except Exception as e:
                            st.error(f"Failed to initialize model {chosen_model_name}: {e}")
                            st.session_state.llm_instance = None
                            st.session_state.selected_model_name = None
                    
            else:
                st.warning("No Ollama models found or Ollama is not running. AI features will be disabled.")
                st.session_state.llm_instance = None # Disable AI features
                st.session_state.selected_model_name = None

    # --- Main Area for Job Description and Actions ---
    col1_tab1, col2_tab1 = st.columns(2)

    with col1_tab1:
        st.subheader("Job Details")
        job_title_input_tab1 = st.text_input("Job Title:", key="job_title_tab1")
        company_name_input_tab1 = st.text_input("Company Name:", key="company_name_tab1")
        job_desc_input_tab1 = st.text_area("Paste the full job description here:", height=250, key="job_desc_input_tab1")

        # Action Buttons
        st.markdown("##### AI Actions")
        # Disable AI-related buttons if no LLM instance is available
        ai_features_disabled_tab1 = st.session_state.llm_instance is None

        score_button_tab1 = st.button("1. Score Resume", disabled=ai_features_disabled_tab1, key="score_btn_tab1")
        generate_cl_button_tab1 = st.button("2. Generate Cover Letter", disabled=ai_features_disabled_tab1, key="generate_cl_btn_tab1")
        
        st.markdown("##### Application Management")
        save_app_button_tab1 = st.button("3. Save Application to Database", key="save_app_btn_tab1")

    # --- Processing Logic for Buttons in Tab 1---
    if score_button_tab1:
        current_job_desc_tab1 = job_desc_input_tab1
        st.session_state.raw_ai_response_score = "" 
        if not st.session_state.resume_text:
            st.error("Please upload a resume first (in the sidebar).")
        elif not current_job_desc_tab1:
            st.error("Please paste the job description.")
        elif st.session_state.llm_instance is None:
            st.error("AI model not available. Please select a model or check Ollama setup (in the sidebar).")
        else:
            with st.spinner(f"AI ({st.session_state.selected_model_name}) is scoring your resume..."):
                score, reasoning, raw_response = score_resume_job_description( # Corrected function call
                    st.session_state.llm_instance, 
                    st.session_state.resume_text, 
                    current_job_desc_tab1
                )
                st.session_state.raw_ai_response_score = raw_response or "No raw response captured."
                if score is not None and reasoning is not None:
                    st.session_state.ai_score = score
                    st.session_state.ai_reasoning = reasoning
                    st.success("Resume scored successfully!")
                else:
                    st.error("Failed to score resume. Check console/Ollama logs for errors.")
                    st.session_state.ai_score = None
                    st.session_state.ai_reasoning = "Error during scoring."
                st.session_state.job_description = current_job_desc_tab1 

    if generate_cl_button_tab1:
        current_job_desc_tab1 = job_desc_input_tab1
        current_company_name_tab1 = company_name_input_tab1
        current_job_title_tab1 = job_title_input_tab1
        st.session_state.raw_ai_response_cl = "" 
        if not st.session_state.resume_text:
            st.error("Please upload a resume first (in the sidebar).")
        elif not current_job_desc_tab1:
            st.error("Please paste the job description.")
        elif not current_company_name_tab1 or not current_job_title_tab1:
            st.error("Please enter Company Name and Job Title for the cover letter.")
        elif st.session_state.llm_instance is None:
            st.error("AI model not available. Please select a model or check Ollama setup (in the sidebar).")
        else:
            with st.spinner(f"AI ({st.session_state.selected_model_name}) is crafting your cover letter..."):
                cover_letter_text, raw_response = generate_cover_letter(
                    st.session_state.llm_instance,
                    st.session_state.resume_text,
                    current_job_desc_tab1,
                    current_company_name_tab1,
                    current_job_title_tab1
                )
                st.session_state.raw_ai_response_cl = raw_response or "No raw response captured."
                if cover_letter_text and "Error during AI" not in cover_letter_text :
                    st.session_state.cover_letter = cover_letter_text
                    st.success("Cover letter generated!")
                else:
                    st.error("Failed to generate cover letter. Check console/Ollama logs for errors.")
                    st.session_state.cover_letter = cover_letter_text 
                st.session_state.job_description = current_job_desc_tab1

    if save_app_button_tab1:
        current_job_desc_tab1 = job_desc_input_tab1
        current_job_title_tab1 = job_title_input_tab1 # Get from new input
        current_company_name_tab1 = company_name_input_tab1 # Get from new input

        if not current_job_title_tab1:
            st.error("Please enter a Job Title.")
        # resume_id is optional now, so we don't strictly need it.
        # job_description is also optional in the DB, but good to have for AI features.
        else:
            # Cover letter path would be handled if we save CL to a file. For now, it's text.
            # We'll store the text directly in cover_letter_text, and path can be None.
            # For a more robust system, generated cover letters should be saved to files.
            # For now, we pass None for cover_letter_path.
            
            app_id = add_job_application(
                job_title=current_job_title_tab1,
                company=current_company_name_tab1 if current_company_name_tab1 else None,
                resume_id=st.session_state.resume_id, # Can be None
                job_description=current_job_desc_tab1 if current_job_desc_tab1 else None,
                cover_letter_path=None, # Placeholder for now
                ai_score=st.session_state.ai_score,
                ai_reasoning=st.session_state.ai_reasoning if st.session_state.ai_reasoning else None,
                # outcome and notes will be default or None
            )
            if app_id:
                st.success(f"Application for '{current_job_title_tab1}' at '{current_company_name_tab1}' saved with ID: {app_id}")
                # Clear relevant session state for the next application
                st.session_state.job_description = ""
                st.session_state.ai_score = None
                st.session_state.ai_reasoning = ""
                st.session_state.cover_letter = ""
                st.session_state.raw_ai_response_score = ""
                st.session_state.raw_ai_response_cl = ""
                # Consider clearing job_title_input_tab1, company_name_input_tab1, job_desc_input_tab1
                # by managing their values in session state or using st.rerun() if appropriate.
                # For now, let them persist.
                st.rerun() 
            else:
                st.error("Failed to save application to database.")

    # --- Display Area for AI Output and Cover Letter in Tab 1 ---
    with col2_tab1:
        st.subheader("AI Analysis & Generated Content")
        if st.session_state.ai_score is not None:
            st.metric(label="Resume Match Score", value=f"{st.session_state.ai_score:.0f}/100")
        if st.session_state.ai_reasoning:
            with st.expander("Scoring Explanation", expanded=False):
                st.markdown(st.session_state.ai_reasoning)
        
        if st.session_state.cover_letter:
            st.subheader("Generated Cover Letter")
            st.text_area("Cover Letter Preview", value=st.session_state.cover_letter, height=300, key="cl_display_area_tab1", disabled=True)

        # Display Raw AI Responses
        if st.session_state.raw_ai_response_score:
            with st.expander("Raw AI Response (Scoring)", expanded=False):
                st.text_area("Raw Scoring Output", value=st.session_state.raw_ai_response_score, height=150, disabled=True, key="raw_score_output_tab1")
        
        if st.session_state.raw_ai_response_cl:
            with st.expander("Raw AI Response (Cover Letter)", expanded=False):
                st.text_area("Raw Cover Letter Output", value=st.session_state.raw_ai_response_cl, height=150, disabled=True, key="raw_cl_output_tab1")

    # --- Cover Letter Generation and Application Submission ---
    with st.expander("Generate Cover Letter & Submit Application", expanded=True):
        st.subheader("AI-Powered Cover Letter and Application Submission")
        st.write("Generate a cover letter using AI and submit your job application in one go.")
        
        # Job details inputs
        job_title_input = st.text_input("Job Title (for Cover Letter):", key="job_title_input")
        company_name_input = st.text_input("Company Name (for Cover Letter):", key="company_name_input")
        
        # --- Restructured Resume selection for Cover Letter ---
        st.write("Select Resume for Cover Letter Generation")
        available_resumes_cl = get_all_resumes()
        resume_options_cl = {0: "None"} # Default option
        for res in available_resumes_cl:
            resume_options_cl[res['id']] = Path(res['file_path']).name
        
        # --- Session state management for selected resume ---
        if 'selected_resume_id_for_cl' not in st.session_state:
            st.session_state.selected_resume_id_for_cl = 0 # Default to "None"
        if 'selected_resume_path_for_cl' not in st.session_state:
            st.session_state.selected_resume_path_for_cl = None

        # Resume selection logic
        if st.session_state.selected_resume_id_for_cl != 0 and st.session_state.selected_resume_id_for_cl in resume_options_cl:
            # Valid resume ID selected
            st.session_state.selected_resume_path_for_cl = next((res['file_path'] for res in available_resumes_cl if res['id'] == st.session_state.selected_resume_id_for_cl), None)
        else:
            # No valid resume selected, or "None" option
            st.session_state.selected_resume_path_for_cl = None

        # Resume selectbox for Cover Letter
        selected_resume_id_for_cl = st.selectbox(
            "Choose a resume for Cover Letter:",
            options=list(resume_options_cl.keys()),
            format_func=lambda x: resume_options_cl[x],
            index=list(resume_options_cl.keys()).index(st.session_state.selected_resume_id_for_cl),
            key="resume_select_cl"
        )

        # Update session state on resume selection change
        if selected_resume_id_for_cl != st.session_state.selected_resume_id_for_cl:
            st.session_state.selected_resume_id_for_cl = selected_resume_id_for_cl
            if selected_resume_id_for_cl == 0:
                st.session_state.selected_resume_path_for_cl = None
            else:
                st.session_state.selected_resume_path_for_cl = next((res['file_path'] for res in available_resumes_cl if res['id'] == selected_resume_id_for_cl), None)

        # --- End of Restructured Resume selection for Cover Letter ---

        # Job description input
        job_description_input = st.text_area("Job Description:", height=250, key="job_description_input_cl")

        # --- AI Model selection for Cover Letter ---
        st.write("AI Model for Cover Letter Generation")
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
                    "Choose an AI model for Cover Letter:",
                    options=available_models,
                    index=available_models.index(default_selection) if default_selection in available_models else 0, # Ensure index is valid
                    key="ollama_model_selector_cl" # Unique key for this selectbox
                )

                # Initialize or update LLM instance if needed
                if st.session_state.llm_instance is None or st.session_state.llm_instance.model != chosen_model_name:
                    with st.spinner(f"Initializing AI model: {chosen_model_name}..."):
                        try: # Add try-except for model initialization
                            # Added timeout to Ollama initialization and used updated class
                            st.session_state.llm_instance = OllamaLLM(model=chosen_model_name, timeout=120) 
                            st.session_state.selected_model_name = chosen_model_name # Update session state
                            st.success(f"AI model {chosen_model_name} initialized.")
                        except Exception as e:
                            st.error(f"Failed to initialize model {chosen_model_name}: {e}")
                            st.session_state.llm_instance = None
                            st.session_state.selected_model_name = None
                    
            else:
                st.warning("No Ollama models found or Ollama is not running. AI features will be disabled.")
                st.session_state.llm_instance = None # Disable AI features
                st.session_state.selected_model_name = None

        # --- End of AI Model selection for Cover Letter ---

        # Action button for generating cover letter
        if st.button("Generate Cover Letter", key="generate_cl_button"):
            if st.session_state.job_description_input and st.session_state.selected_resume_path_for_cl:
                with st.spinner("Generating Cover Letter..."):
                    try:
                        resume_text_for_cl = extract_text_from_pdf(st.session_state.selected_resume_path_for_cl)
                        if resume_text_for_cl:
                            cover_letter = generate_cover_letter(
                                st.session_state.ollama_model_select,
                                resume_text_for_cl,
                                st.session_state.job_description_input,
                                st.session_state.get('job_title_input', 'the position'), # Use job title if available
                                st.session_state.get('company_name_input', 'the company') # Use company name if available
                            )
                            st.session_state.generated_cover_letter = cover_letter
                            st.success("Cover letter generated!")
                        else:
                            st.error("Could not extract text from the selected resume for cover letter generation.")
                    except Exception as e:
                        st.error(f"Error generating cover letter: {e}")
            else:
                st.warning("Please provide a job description and select a resume first.")
            
        if st.session_state.get("generated_cover_letter"):
            st.subheader("Generated Cover Letter")
            st.text_area("Cover Letter", value=st.session_state.generated_cover_letter, height=300, key="cl_display_area")

            # Save Cover Letter and Add Application Button
            if st.button("Save Cover Letter & Add Application", key="save_cl_and_add_app_button"):
                if not st.session_state.get('job_title_input') or not st.session_state.get('company_name_input'):
                    st.error("Job Title and Company Name are required to save the application.")
                elif not st.session_state.selected_resume_id_for_cl:
                    st.error("A resume must be selected and processed to link with the application.")
                else:
                    with st.spinner("Saving application..."):
                        # 1. Save the cover letter to a file
                        cl_content = st.session_state.generated_cover_letter
                        job_title_for_filename = st.session_state.get('job_title_input', 'Job')
                        company_for_filename = st.session_state.get('company_name_input', 'Company')
                        filename_prefix = f"{job_title_for_filename}_{company_for_filename}"
                        
                        cover_letter_file_path = save_cover_letter(cl_content, filename_prefix)

                        if cover_letter_file_path:
                            st.info(f"Cover letter saved to: {cover_letter_file_path}")
                            # 2. Add job application to database
                            try:
                                app_id = add_job_application(
                                    job_title=st.session_state.job_title_input,
                                    company=st.session_state.company_name_input,
                                    resume_id=st.session_state.selected_resume_id_for_cl, # This should be the ID from the DB
                                    job_description=st.session_state.job_description_input,
                                    cover_letter_path=cover_letter_file_path,
                                    ai_score=st.session_state.get('resume_score'),
                                    ai_reasoning=st.session_state.get('score_reasoning'),
                                    outcome='pending', # Default outcome
                                    notes='Cover letter generated by AI.', # Default note
                                    submission_date=datetime.now(), # Current timestamp
                                    custom_fields={}
                                )
                                if app_id:
                                    st.success(f"Application for '{st.session_state.job_title_input}' at '{st.session_state.company_name_input}' added successfully with ID: {app_id}!")
                                    # Clear relevant session state after successful save
                                    st.session_state.job_description_input = ""
                                    st.session_state.generated_cover_letter = ""
                                    st.session_state.resume_score = None
                                    st.session_state.score_reasoning = ""
                                    st.session_state.job_title_input = ""
                                    st.session_state.company_name_input = ""
                                    # st.session_state.selected_resume_path_for_cl = None # Keep this if user might want to reuse for another CL
                                    # st.session_state.selected_resume_id_for_cl = None # Keep this for same reason
                                    st.rerun()
                                else:
                                    st.error("Failed to add application to the database.")
                            except Exception as e:
                                st.error(f"Error adding application to database: {e}")
                        else:
                            st.error("Failed to save cover letter. Application not added.")

# --- Tab 2: Track Applications ---
with tab2:
    st.header("Track Your Job Applications")

    # --- Function to refresh applications ---
    def refresh_apps_data():
        apps = get_all_applications()
        if apps:
            # Prepare data for DataFrame, including unpacking custom_fields
            df_data = []
            for app in apps:
                app_row = {
                    "ID": app['id'],
                    "Job Title": app['job_title'],
                    "Company": app['company'],
                    "Resume Path": app.get('resume_file_path', 'N/A'), # Use .get for safety
                    "Job Description": app.get('job_description', 'N/A'),
                    "Cover Letter Path": app.get('cover_letter_path', 'N/A'),
                    "Submission Date": app['submission_date'],
                    "AI Score": app.get('ai_score', 'N/A'),
                    "AI Reasoning": app.get('ai_reasoning', 'N/A'),
                    "Outcome": app['outcome'],
                    "Notes": app.get('notes', 'N/A')
                }
                # Add custom fields as separate columns for display if they exist
                if isinstance(app.get('custom_fields'), dict):
                    for cf_key, cf_value in app['custom_fields'].items():
                        app_row[f"Custom: {cf_key}"] = cf_value
                df_data.append(app_row)
            
            df = pd.DataFrame(df_data)
            # Dynamically create the list of columns for the DataFrame
            # Start with base columns, then add any custom field columns found
            base_columns = [
                "ID", "Job Title", "Company", "Resume Path", "Job Description", 
                "Cover Letter Path", "Submission Date", "AI Score", "AI Reasoning", 
                "Outcome", "Notes"
            ]
            custom_field_columns = sorted([col for col in df.columns if col.startswith("Custom: ")])
            all_df_columns = base_columns + custom_field_columns
            df = df.reindex(columns=all_df_columns) # Ensure consistent column order

            if 'Submission Date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['Submission Date']):
                 df['Submission Date'] = pd.to_datetime(df['Submission Date'])
            return df
        return pd.DataFrame()

    applications_df = refresh_apps_data()

    # --- Search and Filter ---
    st.sidebar.header("Filter & Search Applications")
    search_term = st.sidebar.text_input("Search by Job Title, Company, or Custom Fields", key="search_apps")
    
    outcome_options = ["All"] + sorted(list(applications_df["Outcome"].unique())) if not applications_df.empty and "Outcome" in applications_df.columns else ["All", "pending", "interview", "rejected", "offer"]
    selected_outcome = st.sidebar.selectbox("Filter by Outcome", options=outcome_options, key="filter_outcome")

    filtered_df = applications_df.copy()
    if search_term:
        # Search in standard text fields and also in custom field values (converted to string)
        search_conditions = (
            filtered_df["Job Title"].astype(str).str.contains(search_term, case=False, na=False) |
            filtered_df["Company"].astype(str).str.contains(search_term, case=False, na=False)
        )
        for col in filtered_df.columns:
            if col.startswith("Custom: "):
                search_conditions |= filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)
        filtered_df = filtered_df[search_conditions]

    if selected_outcome != "All":
        filtered_df = filtered_df[filtered_df["Outcome"] == selected_outcome]

    # --- Display Applications Table ---
    if not filtered_df.empty:
        st.info(f"Displaying {len(filtered_df)} of {len(applications_df)} applications.")
        # Dynamically select columns for display, including custom ones
        display_columns = ["ID", "Job Title", "Company", "Submission Date", "AI Score", "Outcome"]
        custom_display_columns = [col for col in filtered_df.columns if col.startswith("Custom: ")]
        st.dataframe(filtered_df[display_columns + custom_display_columns], use_container_width=True, hide_index=True)
    elif not applications_df.empty and search_term or selected_outcome != "All":
        st.warning("No applications match your current filter criteria.")
    else:
        st.info("No applications found in the database. Add some via the 'Process New Application' tab or manually below.")

    st.divider()

    # --- Actions: Add, Edit, Delete ---
    col_actions1, col_actions2 = st.columns(2)

    with col_actions1:
        st.subheader("Manage Selected Application")
        if not filtered_df.empty:
            app_ids = filtered_df["ID"].tolist()
            selected_app_id_to_manage = st.selectbox("Select Application ID to Manage", options=app_ids, key="app_id_manage", index=None, placeholder="Choose an application ID")
        else:
            selected_app_id_to_manage = None
            st.caption("No applications to select for management.")


        if selected_app_id_to_manage:
            # Fetch full details for the selected app
            app_details_tuple = get_application_by_id(selected_app_id_to_manage)
            
            if app_details_tuple:
                app_details = app_details_tuple # It's already a dict from db.py
                
                st.markdown(f"**Details for Application ID: {app_details['id']}**")
                st.markdown(f"**Job Title:** {app_details['job_title']}")
                st.markdown(f"**Company:** {app_details.get('company', 'N/A')}")
                st.markdown(f"**Submission Date:** {pd.to_datetime(app_details['submission_date']).strftime('%Y-%m-%d') if app_details['submission_date'] else 'N/A'}")
                st.markdown(f"**Outcome:** {app_details['outcome']}")
                if app_details.get('resume_file_path'):
                    st.markdown(f"**Resume:** {Path(app_details['resume_file_path']).name}")
                if app_details.get('ai_score') is not None:
                    st.markdown(f"**AI Score:** {app_details['ai_score']:.0f}/100")
                
                # Display Custom Fields
                if app_details.get('custom_fields'):
                    st.markdown("**Custom Fields:**")
                    for key, value in app_details['custom_fields'].items():
                        st.markdown(f"- **{key}:** {value}")

                with st.expander("View Full Details / Edit"):
                    edit_job_title = st.text_input("Job Title", value=app_details["job_title"], key=f"edit_title_{app_details['id']}")
                    edit_company = st.text_input("Company", value=app_details.get("company", ""), key=f"edit_company_{app_details['id']}")
                    
                    current_sub_date = pd.to_datetime(app_details["submission_date"]).date() if app_details["submission_date"] else datetime.now().date()
                    edit_submission_date = st.date_input("Submission Date", value=current_sub_date, key=f"edit_sub_date_{app_details['id']}")

                    edit_job_description = st.text_area("Job Description", value=app_details.get("job_description", ""), height=150, key=f"edit_jd_{app_details['id']}")
                    edit_outcome_options = ["pending", "interview", "rejected", "offer", "other"]
                    current_outcome_index = edit_outcome_options.index(app_details["outcome"]) if app_details["outcome"] in edit_outcome_options else 0
                    edit_outcome = st.selectbox("Outcome", options=edit_outcome_options, index=current_outcome_index, key=f"edit_outcome_{app_details['id']}")
                    edit_notes = st.text_area("Notes", value=app_details.get("notes", ""), height=100, key=f"edit_notes_{app_details['id']}")
                    
                    # --- Custom Fields Editing ---
                    st.markdown("**Custom Fields (Key:Value)**")
                    # Initialize session state for this app's custom fields if not present
                    if f"edit_custom_fields_{app_details['id']}" not in st.session_state:
                        st.session_state[f"edit_custom_fields_{app_details['id']}"] = app_details.get('custom_fields', {}).copy() # Use a copy
                    
                    current_custom_fields_edit = st.session_state[f"edit_custom_fields_{app_details['id']}"] # Renamed for clarity
                    
                    # Display existing custom fields for editing
                    if current_custom_fields_edit: # Use renamed variable
                        for cf_key, cf_value in list(current_custom_fields_edit.items()): # Iterate over a copy, use renamed variable
                            col1_cf, col2_cf, col3_cf = st.columns([3,3,1])
                            current_key = cf_key # Store current key for reliable deletion
                            with col1_cf:
                                new_key_val = st.text_input(f"Key##{current_key}", value=current_key, key=f"edit_cf_key_{app_details['id']}_{current_key}") # Unique key
                            with col2_cf:
                                new_val_val = st.text_input(f"Value##{current_key}", value=cf_value, key=f"edit_cf_val_{app_details['id']}_{current_key}") # Unique key
                            with col3_cf:
                                st.markdown("<br>", unsafe_allow_html=True) # Spacer for button alignment
                                # Ensure this part is within an st.form if using st.form_submit_button
                                # Label for form_submit_button must be unique.
                                if st.form_submit_button(label=f"X_edit_{app_details['id']}_{current_key}", help="Remove field"):
                                    if current_key in current_custom_fields_edit: # Use correct session state dict
                                        del current_custom_fields_edit[current_key] # Use correct session state dict
                                    st.rerun() # Rerun to reflect removal

                            # Handle key/value updates - this logic runs on every rerun if values in text_inputs change
                            # This logic needs to be carefully reviewed if it's intended to update live or on save.
                            # For now, focusing on the delete button fix.
                            # The following block seems to reference 'manual_custom_fields', which is incorrect here.
                            # It should operate on 'current_custom_fields_edit' or be part of the save logic.
                            # Temporarily commenting out the potentially problematic auto-update logic for keys/values here
                            # to avoid unintended side-effects with 'manual_custom_fields'.
                            # if current_key in st.session_state.manual_custom_fields: # BUG: Should be current_custom_fields_edit
                            #     if new_key_val != current_key: 
                            #         value_to_move = st.session_state.manual_custom_fields.pop(current_key)
                            #         st.session_state.manual_custom_fields[new_key_val] = new_val_val 
                            #         st.rerun() 
                            #     elif new_val_val != cf_value: 
                            #         st.session_state.manual_custom_fields[current_key] = new_val_val
                    
                    # Add new custom field
                    new_cf_key_edit = st.text_input("New Custom Field Key", key=f"new_cf_key_edit_{app_details['id']}")
                    new_cf_value_edit = st.text_input("New Custom Field Value", key=f"new_cf_value_edit_{app_details['id']}")
                    if st.button("Add Custom Field", key=f"add_cf_edit_{app_details['id']}"):
                        if new_cf_key_edit and new_cf_key_edit not in current_custom_fields_edit:
                            current_custom_fields_edit[new_cf_key_edit] = new_cf_value_edit
                            # Clear inputs after adding by rerunning or resetting specific input keys
                            st.rerun()
                        elif new_cf_key_edit in current_custom_fields_edit:
                            st.warning(f"Custom field '{new_cf_key_edit}' already exists. Its value was updated if you changed it above.")
                        else:
                            st.warning("Custom field key cannot be empty.")
                    # --- End Custom Fields Editing ---

                    if st.button("Save Changes", key=f"save_edit_{app_details['id']}"):
                        updated = update_job_application(
                            application_id=app_details['id'],
                            job_title=edit_job_title,
                            company=edit_company,
                            job_description=edit_job_description,
                            outcome=edit_outcome,
                            notes=edit_notes,
                            resume_id=app_details.get("resume_id"),
                            cover_letter_path=app_details.get("cover_letter_path"),
                            submission_date=datetime.combine(edit_submission_date, datetime.min.time()),
                            custom_fields=current_custom_fields_edit # Pass the edited custom fields
                        )
                        if updated:
                            st.success(f"Application ID {app_details['id']} updated successfully.")
                            del st.session_state[f"edit_custom_fields_{app_details['id']}"] # Clean up session state
                            st.session_state.editing_app_id = None 
                            st.rerun()
                        else:
                            st.error(f"Failed to update application ID {app_details['id']}.")
                
                if st.button("Delete Application", type="primary", key=f"delete_{app_details['id']}"):
                    if delete_job_application(app_details['id']):
                        st.success(f"Application ID {app_details['id']} deleted.")
                        st.rerun()
                    else:
                        st.error(f"Failed to delete application ID {app_details['id']}.")


    with col_actions2:
        st.subheader("Manually Add New Application")
        if st.button("Show Manual Add Form", key="toggle_manual_add_form"):
            current_visibility = st.session_state.get("show_add_manual_form", False)
            st.session_state.show_add_manual_form = not current_visibility
            if st.session_state.show_add_manual_form: # If form is being shown (just became true)
                # Initialize/Reset form fields to defaults for a fresh form
                st.session_state.manual_title_add = ""
                st.session_state.manual_company_add = ""
                st.session_state.manual_sub_date_add = datetime.now().date()
                st.session_state.manual_jd_add = ""
                st.session_state.manual_outcome_add = "pending" # Default value
                st.session_state.manual_notes_add = ""
                st.session_state.manual_resume_link = 0 
                st.session_state.manual_custom_fields = {} # Clear any previous custom fields
                # Initialize inputs for adding new custom fields
                st.session_state.new_manual_cf_key_input_main = ""
                st.session_state.new_manual_cf_value_input_main = ""

        if st.session_state.get("show_add_manual_form", False):
            # Define options needed within the scope where form is built
            manual_outcome_options = ["pending", "interview", "rejected", "offer", "other"]
            available_resumes = get_all_resumes()
            resume_options = {0: "None"}
            for res_idx, res_val in enumerate(available_resumes): # Changed variable names to avoid conflict
                resume_options[res_val['id']] = Path(res_val['file_path']).name

            # Ensure all session state keys for the form are initialized if they somehow got deleted
            if "manual_title_add" not in st.session_state: st.session_state.manual_title_add = ""
            if "manual_company_add" not in st.session_state: st.session_state.manual_company_add = ""
            if "manual_sub_date_add" not in st.session_state: st.session_state.manual_sub_date_add = datetime.now().date()
            if "manual_jd_add" not in st.session_state: st.session_state.manual_jd_add = ""
            if "manual_outcome_add" not in st.session_state: st.session_state.manual_outcome_add = manual_outcome_options[0]
            if "manual_notes_add" not in st.session_state: st.session_state.manual_notes_add = ""
            if "manual_resume_link" not in st.session_state: st.session_state.manual_resume_link = 0
            if 'manual_custom_fields' not in st.session_state: st.session_state.manual_custom_fields = {}
            
            # Initialize or clear new custom field inputs based on flag or if they don't exist
            if st.session_state.get("clear_new_cf_inputs_manual_add", False):
                st.session_state.new_manual_cf_key_input_main = ""
                st.session_state.new_manual_cf_value_input_main = ""
                st.session_state.clear_new_cf_inputs_manual_add = False # Reset the flag
            else:
                if 'new_manual_cf_key_input_main' not in st.session_state: 
                    st.session_state.new_manual_cf_key_input_main = ""
                if 'new_manual_cf_value_input_main' not in st.session_state: 
                    st.session_state.new_manual_cf_value_input_main = ""

            with st.form("manual_add_form", clear_on_submit=False): 
                manual_job_title = st.text_input("Job Title*", key="manual_title_add")
                manual_company = st.text_input("Company", key="manual_company_add")
                manual_submission_date = st.date_input("Submission Date", key="manual_sub_date_add")
                manual_job_description = st.text_area("Job Description", height=100, key="manual_jd_add")
                
                # Ensure the value in session state is valid for selectbox index calculation
                if st.session_state.manual_outcome_add not in manual_outcome_options:
                    st.session_state.manual_outcome_add = manual_outcome_options[0]
                current_manual_outcome_index = manual_outcome_options.index(st.session_state.manual_outcome_add)
                manual_outcome = st.selectbox("Outcome", options=manual_outcome_options, 
                                              index=current_manual_outcome_index, 
                                              key="manual_outcome_add")
                
                manual_notes = st.text_area("Notes", height=75, key="manual_notes_add")
                
                # --- Custom Fields for Manual Add ---
                st.markdown("**Custom Fields (Key:Value)**")
                # 'manual_custom_fields' is already initialized above

                # Display existing custom fields for the current manual entry
                for cf_key, cf_value in list(st.session_state.manual_custom_fields.items()):
                    col1_cf, col2_cf, col3_cf = st.columns([3,3,1])
                    current_key = cf_key 
                    with col1_cf:
                        # Use unique keys for these inputs to avoid conflicts if same cf_key is re-added after removal
                        new_key_val = st.text_input(f"Key##{current_key}", value=current_key, key=f"manual_cf_key_input_{current_key}")
                    with col2_cf:
                        new_val_val = st.text_input(f"Value##{current_key}", value=cf_value, key=f"manual_cf_val_input_{current_key}")
                    with col3_cf:
                        st.markdown("<br>", unsafe_allow_html=True) 
                        if st.form_submit_button(label=f"X_manual_{current_key}", help="Remove field"): # Unique label
                            if current_key in st.session_state.manual_custom_fields:
                                del st.session_state.manual_custom_fields[current_key]
                            st.rerun() 

                    # Handle key/value updates from their respective input boxes
                    if current_key in st.session_state.manual_custom_fields:
                        updated_key = st.session_state[f"manual_cf_key_input_{current_key}"]
                        updated_value = st.session_state[f"manual_cf_val_input_{current_key}"]
                        
                        if updated_key != current_key: # Key was changed
                            # Remove old key, add new key with (potentially new) value
                            st.session_state.manual_custom_fields.pop(current_key)
                            st.session_state.manual_custom_fields[updated_key] = updated_value
                            st.rerun() 
                        elif updated_value != cf_value: # Value was changed (key was not)
                            st.session_state.manual_custom_fields[current_key] = updated_value
                            # st.rerun() # Optional: rerun to see value update immediately, or let it update on next action

                col1_add_cf, col2_add_cf, col3_add_cf = st.columns([2,2,1])
                with col1_add_cf:
                    new_manual_cf_key = st.text_input("New Custom Field Key", key="new_manual_cf_key_input_main")
                with col2_add_cf:
                    new_manual_cf_value = st.text_input("New Custom Field Value", key="new_manual_cf_value_input_main")
                with col3_add_cf:
                    st.markdown("<br>", unsafe_allow_html=True) 
                    add_custom_field_button = st.form_submit_button("Add Custom Field")
                
                if add_custom_field_button:
                    # Use the values from the dedicated input boxes for new custom fields
                    actual_new_key = st.session_state.new_manual_cf_key_input_main
                    actual_new_value = st.session_state.new_manual_cf_value_input_main
                    if actual_new_key and actual_new_key not in st.session_state.manual_custom_fields:
                        st.session_state.manual_custom_fields[actual_new_key] = actual_new_value
                        st.session_state.clear_new_cf_inputs_manual_add = True # Set flag to clear inputs on next run
                        st.rerun() 
                    elif actual_new_key in st.session_state.manual_custom_fields:
                        st.warning(f"Custom field '{actual_new_key}' already exists for this entry.")
                    else:
                        st.warning("Custom field key cannot be empty.")
                # --- End Custom Fields for Manual Add ---

                # Resume linking (optional)
                # Ensure resume_options is up-to-date and st.session_state.manual_resume_link is valid
                if st.session_state.manual_resume_link not in resume_options:
                     st.session_state.manual_resume_link = 0 # Default to "None" if invalid
                current_manual_resume_id_index = list(resume_options.keys()).index(st.session_state.manual_resume_link)
                
                manual_resume_id_val = st.selectbox( # Renamed variable to avoid conflict
                    "Link Resume (Optional)", 
                    options=list(resume_options.keys()), 
                    format_func=lambda x: resume_options[x],
                    index=current_manual_resume_id_index,
                    key="manual_resume_link"
                )

                submitted_manual = st.form_submit_button("Add Application")
                if submitted_manual:
                    if not st.session_state.manual_title_add: # Check value from session state
                        st.error("Job Title is required for manual entry.")
                    else:
                        app_id = add_job_application(
                            job_title=st.session_state.manual_title_add,
                            company=st.session_state.manual_company_add,
                            resume_id=st.session_state.manual_resume_link if st.session_state.manual_resume_link != 0 else None,
                            job_description=st.session_state.manual_jd_add,
                            cover_letter_path=None, 
                            ai_score=None, 
                            ai_reasoning=None, 
                            outcome=st.session_state.manual_outcome_add,
                            notes=st.session_state.manual_notes_add,
                            submission_date=datetime.combine(st.session_state.manual_sub_date_add, datetime.min.time()),
                            custom_fields=st.session_state.manual_custom_fields.copy()
                        )
                        if app_id:
                            st.success(f"Manually added application for '{st.session_state.manual_title_add}' with ID: {app_id}")
                            st.session_state.show_add_manual_form = False 
                            # The form fields will be reset by the initialization logic 
                            # when show_add_manual_form is next set to True.
                            # No need to explicitly clear st.session_state.manual_title_add etc. here.
                            st.rerun()
                        else:
                            st.error("Failed to manually add application.")
        else:
            st.caption("Click the button above to open the form for adding an application manually.")
