# Placeholder for AI Assistant page
import streamlit as st
from pathlib import Path
import time
import subprocess # For Ollama CLI interaction
import json # For parsing Ollama streaming responses
import requests # For direct Ollama API access

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

from core.db import add_file, get_files_by_type, add_job_posting, add_application, log_application_status # Updated imports
from core.file_utils import save_uploaded_file, COVER_LETTERS_DIR, save_cover_letter, get_file_hash
from core.ai_tools import extract_text_from_pdf, score_resume_job_description, generate_cover_letter # Ensure this path is correct relative to how Streamlit runs pages

st.set_page_config(layout="wide", page_title="AI Assistant")
st.title("AI Assistant")
st.caption("Leverage AI to score resumes, generate cover letters, chat about your job search, and streamline your application process.")

# --- Session State Initialization (specific to AI Assistant) ---
# Chat related - using simple dict structure for messages
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []  # List of dicts with 'role' and 'content'
# Ensure old chat history doesn't cause issues
if "chat_history" in st.session_state:
    # Clean up old format if it exists to avoid conflicts
    del st.session_state.chat_history

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
# Remove conversation chain to avoid LangChain deprecation warning
if 'conversation_chain' in st.session_state:
    del st.session_state.conversation_chain


# --- Helper function to get Ollama models (copied from app.py, consider moving to a utils file) ---
@st.cache_data(show_spinner=False)
def get_ollama_models_ai_page():
    try:
        ollama_cmd_to_run = "ollama"
        result = subprocess.run([ollama_cmd_to_run, "list"], capture_output=True, text=True, check=True)
        # Use splitlines() instead of split('\n') for better compatibility
        lines = result.stdout.strip().splitlines()
        print(f"DEBUG: Raw Ollama output: {result.stdout}")
        models = []
        if len(lines) > 1:
            for line_content in lines[1:]:
                processed_line = line_content.strip()
                if not processed_line: continue
                parts = processed_line.split()
                if parts: 
                    models.append(parts[0])
                    print(f"DEBUG: Found model: {parts[0]}")
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

# Define the Ollama base URL
OLLAMA_BASE_URL = "http://localhost:11434"

# Function to stream responses directly from Ollama API
def stream_ollama_response(prompt, model_name):
    """Stream a response from Ollama API with proper error handling"""
    # Prepare API endpoint and payload
    api_url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": True
    }
    
    try:
        # Use requests's streaming for efficient delivery
        with requests.post(api_url, json=payload, stream=True) as response:
            response.raise_for_status()  # Raise error for bad responses
            full_response = ""
            
            # Process each chunk as it arrives
            for line in response.iter_lines():
                if line:
                    try:
                        # Parse JSON from the line
                        chunk = json.loads(line.decode('utf-8'))
                        if 'response' in chunk:
                            token = chunk['response']
                            full_response += token
                            yield token, full_response
                        # Check for completion or error
                        if chunk.get('done', False):
                            break
                    except json.JSONDecodeError:
                        # Handle invalid JSON
                        continue
            
            return full_response
    except requests.RequestException as e:
        # Handle request errors
        error_msg = f"API error: {str(e)}"
        yield error_msg, error_msg
        return error_msg

# --- AI Chat Section ---
st.subheader("Chat with AI Job Assistant")

# Add welcome message if chat is empty
if not st.session_state.chat_messages:
    model_name = st.session_state.ai_selected_model_name or "AI assistant"
    welcome_msg = f"Hello! I'm your AI Job Assistant, powered by {model_name}. How can I help you today?"
    st.session_state.chat_messages.append({"role": "assistant", "content": welcome_msg})

# Display chat messages
for message in st.session_state.chat_messages:
    with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
        st.write(message["content"])

# Handle user input
if st.session_state.ai_llm_instance is None:
    st.info("Please select a model from the sidebar to enable the chat.")
else:
    # Get user input
    user_query = st.chat_input("Ask about job search, resume tips, or interview advice...")
    
    if user_query:
        # Add user message to chat history
        st.session_state.chat_messages.append({"role": "user", "content": user_query})
        
        # Display user message (already displayed by chat_input, but this ensures UI consistency)
        with st.chat_message("user", avatar="👤"):
            st.write(user_query)
        
        # Generate and display assistant response with streaming
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            
            # Build context from chat history
            context = "You are a helpful AI assistant specializing in job search advice, resume building, and interview preparation.\n\n"
            # Add last few messages for context
            for msg in st.session_state.chat_messages[-6:]:  # Last 6 messages (3 exchanges)
                if msg["role"] == "user":
                    context += f"Human: {msg['content']}\n"
                else:
                    context += f"Assistant: {msg['content']}\n"
            
            # Stream response
            full_response = ""
            try:
                for token, current_response in stream_ollama_response(context, st.session_state.ai_selected_model_name):
                    message_placeholder.markdown(current_response + "▌")
                    full_response = current_response
                
                # Final display without cursor
                if full_response:
                    message_placeholder.markdown(full_response)
                    # Add to chat history
                    st.session_state.chat_messages.append({"role": "assistant", "content": full_response})
                else:
                    message_placeholder.error("Failed to generate a response. Please try again.")
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                message_placeholder.error(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": f"I'm sorry, I encountered an error: {str(e)}"})
            
            # Force page refresh to update the chat UI
            st.rerun()

# Add a more prominent divider between chat and resume tools
st.divider()
st.subheader("Resume & Cover Letter Tools")
st.caption("Upload your resume, paste a job description, and use AI to score your resume and generate a cover letter.")
st.divider()

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
                    # Use add_file for resumes
                    resume_file_id_ai = add_file(
                        original_name=uploaded_resume_ai.name,
                        stored_path=str(saved_path_ai), # Ensure it's a string
                        sha256=file_hash_ai,
                        file_type='resume'
                    )
                    if resume_file_id_ai:
                        st.session_state.ai_resume_id = resume_file_id_ai # Store file_id as resume_id
                        st.info(f"New resume added to files with ID: {resume_file_id_ai}. This resume is now selected.")
                    else:
                        st.error("Failed to add new resume to database.")
                else:
                    st.error("Failed to hash the new resume file.")
        else:
            st.error("Failed to save the uploaded resume.")
            st.session_state.ai_resume_file_path = None

    st.subheader("Or Select Existing Resume")
    available_resumes_ai = get_files_by_type('resume') # Use get_files_by_type
    resume_options_ai = {0: "None (or use uploaded if available)"}
    for res_ai in available_resumes_ai:
        # Adjust to new structure: {'id': ..., 'original_name': ..., 'stored_path': ...}
        resume_options_ai[res_ai['id']] = Path(res_ai['stored_path']).name
    
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
            st.session_state.ai_resume_file_path = selected_resume_details['stored_path'] # Use stored_path
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
                        
                        # Add a welcome message when model changes
                        if st.session_state.chat_messages:
                            st.session_state.chat_messages.append({
                                "role": "assistant", 
                                "content": f"I've switched to the {chosen_model_name_ai} model. How can I help you with your job search?"
                            })
                        
                        st.success(f"AI model {chosen_model_name_ai} initialized.")
                    except Exception as e:
                        st.error(f"Failed to initialize model {chosen_model_name_ai}: {e}")
                        st.session_state.ai_llm_instance = None
                        st.session_state.ai_selected_model_name = None
        else:
            st.warning("No Ollama models found or Ollama is not running. AI features will be disabled.")
            st.session_state.ai_llm_instance = None
            st.session_state.ai_selected_model_name = None

# Add a divider between chat and resume tools
st.divider()

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
    if not ai_job_title_input or not ai_company_name_input: # Require title and company for job posting
        st.error("Job Title and Company Name are required to save the application.")
    else:
        # 1. Add Job Posting
        job_posting_id = add_job_posting(
            title=ai_job_title_input,
            company=ai_company_name_input,
            description=st.session_state.ai_job_description_input
            # Add other fields like location, source_url, date_posted if available from UI
        )

        if not job_posting_id:
            st.error("Failed to create or retrieve job posting entry.")
        else:
            # 2. Save cover letter to file if generated
            cover_letter_file_id_ai = None
            if st.session_state.ai_cover_letter_result:
                filename_prefix_ai = f"{ai_job_title_input}_{ai_company_name_input}".replace(" ", "_").replace("/", "_")
                # Assuming save_cover_letter now returns a path, and we need to add it to files table
                cl_path_str = save_cover_letter(st.session_state.ai_cover_letter_result, filename_prefix_ai)
                if cl_path_str:
                    cl_path = Path(cl_path_str)
                    cl_hash = get_file_hash(cl_path)
                    if cl_hash:
                        cover_letter_file_id_ai = add_file(
                            original_name=cl_path.name,
                            stored_path=str(cl_path),
                            sha256=cl_hash,
                            file_type='cover_letter'
                        )
                        if cover_letter_file_id_ai:
                            st.info(f"Generated cover letter saved to: {cl_path_str} (File ID: {cover_letter_file_id_ai})")
                        else:
                            st.warning("Cover letter saved to disk, but failed to add to files database.")
                    else:
                        st.warning("Could not hash the generated cover letter file.")
                else:
                    st.warning("Could not save the generated cover letter to a file.")

            # 3. Add Application
            # Ensure ai_resume_id is the file_id from the 'files' table
            current_resume_file_id = st.session_state.get('ai_resume_id')

            app_id_ai = add_application(
                job_posting_id=job_posting_id,
                resume_file_id=current_resume_file_id, 
                cover_letter_file_id=cover_letter_file_id_ai,
                submission_method=None, # Or add a UI element for this
                notes="Application created via AI Assistant." 
                # date_submitted is handled by add_application
            )
            if app_id_ai:
                st.success(f"Application for '{ai_job_title_input}' saved with ID: {app_id_ai}. View/edit in Job Tracker.")
                # Log initial status
                log_application_status(app_id_ai, "Draft", "Application created via AI Assistant")

                # Optionally, save AI score and reasoning to parsed_metadata or a similar table
                # This requires a function like add_or_update_parsed_metadata from core.db
                # For now, this step is omitted as it's not a direct part of add_application

                # Clear/reset relevant AI page session state for next use
                st.session_state.ai_job_description_input = ""
                st.session_state.ai_score_result = None
                st.session_state.ai_reasoning_result = ""
                st.session_state.ai_cover_letter_result = ""
                st.session_state.ai_raw_score_response = ""
                st.session_state.ai_raw_cl_response = ""
                # Consider clearing job title and company, or let them persist.
                # For now, they will clear on next rerun due to st.text_input behavior.
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
