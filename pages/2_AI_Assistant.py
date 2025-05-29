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

from core.file_utils import save_uploaded_file, COVER_LETTERS_DIR, save_cover_letter, get_file_hash
from core.ai_tools import extract_text_from_pdf, score_resume_job_description, generate_cover_letter, analyze_job_description_with_ollama 
from core.db import add_file, get_files_by_type, add_job_posting, add_application, log_application_status, add_or_update_parsed_metadata # Added add_or_update_parsed_metadata

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

# Job description input for saving application
if 'ai_job_description_input' not in st.session_state: # Stores JD for current AI operations
    st.session_state.ai_job_description_input = ""

# Initialize values for job title and company text inputs
if 'ai_job_title_save' not in st.session_state:
    st.session_state.ai_job_title_save = ""
if 'ai_company_name_save' not in st.session_state:
    st.session_state.ai_company_name_save = ""

# New session state for job description analysis results
if 'show_analysis_results' not in st.session_state:
    st.session_state.show_analysis_results = False
if 'ai_generated_tags' not in st.session_state:
    st.session_state.ai_generated_tags = []
if 'ai_generated_tech_stacks' not in st.session_state:
    st.session_state.ai_generated_tech_stacks = []
if 'selected_tags' not in st.session_state: # For multiselect interaction
    st.session_state.selected_tags = []
if 'selected_tech_stacks' not in st.session_state: # For multiselect interaction
    st.session_state.selected_tech_stacks = []
# Confirmed tags/stacks are what get saved
if 'confirmed_tags' not in st.session_state:
    st.session_state.confirmed_tags = []
if 'confirmed_tech_stacks' not in st.session_state:
    st.session_state.confirmed_tech_stacks = []


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
            _final_processed_response_for_display_and_history = ""
            # Variables to manage the first <think> block processing
            _thinking_active = False
            _think_start_time = 0.0
            _first_think_block_processed = False
            _text_before_first_think = ""
            _thinking_duration_msg = "" # Stores "⏳ Thinking... (took Xs)\\n\\n"
            
            raw_cumulative_response_from_model = "" # Holds the latest full raw response

            try:
                for token_chunk, current_raw_cumulative in stream_ollama_response(context, st.session_state.ai_selected_model_name):
                    # Handle potential error message from the stream_ollama_response generator itself
                    if isinstance(token_chunk, str) and "API error:" in token_chunk and current_raw_cumulative == token_chunk:
                        message_placeholder.error(token_chunk)
                        _final_processed_response_for_display_and_history = token_chunk
                        break  # Stop processing on API error

                    raw_cumulative_response_from_model = current_raw_cumulative
                    current_display_text = ""

                    if not _first_think_block_processed:
                        think_start_tag = "<think>"
                        think_end_tag = "</think>"
                        
                        start_idx = raw_cumulative_response_from_model.find(think_start_tag)
                        
                        if start_idx != -1: # <think> tag is present
                            if not _thinking_active: # First time encountering <think> for this block
                                _thinking_active = True
                                _think_start_time = time.time()
                                _text_before_first_think = raw_cumulative_response_from_model[:start_idx]
                            
                            end_idx = raw_cumulative_response_from_model.find(think_end_tag, start_idx + len(think_start_tag))
                            
                            if end_idx != -1: # </think> tag also present, completing the block
                                duration = time.time() - _think_start_time
                                _thinking_duration_msg = f"⏳ Thinking... (took {duration:.1f}s)\\n\\n"
                                
                                content_after_first_think = raw_cumulative_response_from_model[end_idx + len(think_end_tag):]
                                current_display_text = _text_before_first_think + _thinking_duration_msg + content_after_first_think
                                
                                _first_think_block_processed = True
                                _thinking_active = False 
                            else: # <think> present, but </think> not yet
                                current_display_text = _text_before_first_think + "⏳ Thinking..."
                        else: # No <think> tag encountered yet in the response
                            current_display_text = raw_cumulative_response_from_model
                    else: # First <think> block already processed
                        # Reconstruct display using the raw response and the stored thinking message
                        s_idx_raw = raw_cumulative_response_from_model.find("<think>")
                        e_idx_raw = -1
                        if s_idx_raw != -1:
                            e_idx_raw = raw_cumulative_response_from_model.find("</think>", s_idx_raw + len("<think>"))
                        
                        if s_idx_raw != -1 and e_idx_raw != -1: # First think block still identifiable in raw
                            text_before_current_raw_think = raw_cumulative_response_from_model[:s_idx_raw]
                            text_after_current_raw_think = raw_cumulative_response_from_model[e_idx_raw + len("</think>"):]
                            current_display_text = text_before_current_raw_think + _thinking_duration_msg + text_after_current_raw_think
                        else:
                            # Fallback if the original think block structure is lost in the raw stream,
                            # though this shouldn't happen if the model is consistent.
                            # This implies we append new raw data to the previously formed message.
                            # For simplicity, we assume the transformation can be reapplied if tags are present.
                            # If not, it defaults to showing the raw response from this point.
                            current_display_text = raw_cumulative_response_from_model


                    message_placeholder.markdown(current_display_text + "▌")
                    _final_processed_response_for_display_and_history = current_display_text
                
                # Loop finished
                if _final_processed_response_for_display_and_history:
                    message_placeholder.markdown(_final_processed_response_for_display_and_history)
                    # Add the processed response to chat history
                    st.session_state.chat_messages.append({"role": "assistant", "content": _final_processed_response_for_display_and_history})
                elif not ("API error:" in _final_processed_response_for_display_and_history): # Avoid double error message if API error already handled
                    message_placeholder.error("Failed to generate a response. Please try again.")
                    st.session_state.chat_messages.append({"role": "assistant", "content": "Failed to generate a response."})

            except Exception as e:
                error_msg = f"Error during AI response processing: {str(e)}"
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
# Remove the old AI action buttons and related UI elements

# Placeholder for new AI tools/features that will be driven by chat prompts
st.info("Use the chat interface above to interact with the AI for tasks like resume analysis, cover letter generation, and more.")

# Section for saving application details that might be populated via chat interaction
st.subheader("Save Application Details")
st.caption("If the AI helped you draft application details, you can save them here. You can also analyze the job description for tags and tech stacks.") # Updated caption

ai_job_title_input = st.text_input("Job Title (can be extracted by AI):", value=st.session_state.ai_job_title_save, key="ai_job_title_save_widget")
ai_company_name_input = st.text_input("Company Name (can be extracted by AI):", value=st.session_state.ai_company_name_save, key="ai_company_name_save_widget")
# Job description is already in session state if needed for saving
st.session_state.ai_job_description_input = st.text_area(
    "Job Description (can be extracted or summarized by AI):", 
    value=st.session_state.ai_job_description_input, 
    height=150, 
    key="ai_job_desc_save"
)

# --- Job Description Analysis Section ---
col1_jd_analysis, col2_jd_analysis = st.columns(2)
with col1_jd_analysis:
    analyze_jd_button = st.button("Analyze Job Description for Tags/Tech", key="analyze_jd_btn")

if analyze_jd_button and st.session_state.ai_job_description_input:
    if st.session_state.ai_llm_instance and st.session_state.ai_selected_model_name:
        with st.spinner("Analyzing job description... This may take a moment."):
            analysis_results = analyze_job_description_with_ollama(
                st.session_state.ai_job_description_input,
                st.session_state.ai_selected_model_name
            )
        if analysis_results and (analysis_results.get("tags") or analysis_results.get("tech_stacks")):
            st.session_state.ai_generated_tags = analysis_results.get("tags", [])
            st.session_state.ai_generated_tech_stacks = analysis_results.get("tech_stacks", [])
            # Initialize selected with all generated, user can deselect
            st.session_state.selected_tags = st.session_state.ai_generated_tags[:]
            st.session_state.selected_tech_stacks = st.session_state.ai_generated_tech_stacks[:]
            st.session_state.show_analysis_results = True
            st.success("Job description analyzed. Review and confirm below.")
            st.rerun() # Rerun to show the modal-like section
        else:
            st.error("Failed to analyze job description or no tags/tech stacks found.")
            st.session_state.show_analysis_results = False
    else:
        st.warning("Please select an AI model from the sidebar to analyze the job description.")
elif analyze_jd_button:
    st.warning("Please enter a job description above to analyze.")

if st.session_state.show_analysis_results:
    with st.expander("Confirm Extracted Tags and Tech Stacks", expanded=True):
        st.markdown("#### Review and Modify AI Suggestions")

        # Tags selection
        st.markdown("**Suggested Tags:**")
        # Use a temporary variable for multiselect to manage its state correctly during interaction
        current_selected_tags = st.multiselect(
            "Select relevant tags:",
            options=list(set(st.session_state.ai_generated_tags + st.session_state.selected_tags)), # Show all, including manually added
            default=st.session_state.selected_tags,
            key="multiselect_tags"
        )
        st.session_state.selected_tags = current_selected_tags
        
        custom_tag_input = st.text_input("Add custom tag:", key="custom_tag_input")
        if st.button("Add Tag", key="add_custom_tag_btn"):
            if custom_tag_input and custom_tag_input not in st.session_state.selected_tags:
                st.session_state.selected_tags.append(custom_tag_input)
                # No need to clear custom_tag_input here, text_input handles its own state unless we force rerun
                st.rerun() # Rerun to update multiselect and clear input if desired (or manage input clear manually)
            elif custom_tag_input in st.session_state.selected_tags:
                st.toast(f"Tag '{custom_tag_input}' already selected.")
            else:
                st.toast("Tag cannot be empty.")

        st.divider()

        # Tech Stacks selection
        st.markdown("**Suggested Tech Stacks:**")
        current_selected_tech_stacks = st.multiselect(
            "Select relevant tech stacks:",
            options=list(set(st.session_state.ai_generated_tech_stacks + st.session_state.selected_tech_stacks)),
            default=st.session_state.selected_tech_stacks,
            key="multiselect_tech_stacks"
        )
        st.session_state.selected_tech_stacks = current_selected_tech_stacks

        custom_tech_stack_input = st.text_input("Add custom tech stack:", key="custom_tech_stack_input")
        if st.button("Add Tech Stack", key="add_custom_tech_stack_btn"):
            if custom_tech_stack_input and custom_tech_stack_input not in st.session_state.selected_tech_stacks:
                st.session_state.selected_tech_stacks.append(custom_tech_stack_input)
                st.rerun()
            elif custom_tech_stack_input in st.session_state.selected_tech_stacks:
                st.toast(f"Tech stack '{custom_tech_stack_input}' already selected.")
            else:
                st.toast("Tech stack cannot be empty.")
        
        st.divider()

        # Confirmation and Cancel buttons
        col_confirm, col_cancel = st.columns(2)
        with col_confirm:
            if st.button("Confirm Selections", key="confirm_analysis_btn"):
                st.session_state.confirmed_tags = st.session_state.selected_tags[:]
                st.session_state.confirmed_tech_stacks = st.session_state.selected_tech_stacks[:]
                st.session_state.show_analysis_results = False
                st.success("Tags and tech stacks confirmed. They will be saved with the application.")
                st.rerun()
        with col_cancel:
            if st.button("Cancel Analysis", key="cancel_analysis_btn"):
                # Reset selections to what was last confirmed or to generated if nothing confirmed yet
                # Or simply hide and keep current selections for next time.
                # For now, just hide.
                st.session_state.show_analysis_results = False
                st.info("Analysis confirmation cancelled.")
                st.rerun()

# Display confirmed tags/stacks if any, before save button
if st.session_state.get('confirmed_tags') or st.session_state.get('confirmed_tech_stacks'):
    st.markdown("---")
    if st.session_state.get('confirmed_tags'):
        st.markdown(f"**Confirmed Tags:** {", ".join(st.session_state.confirmed_tags)}")
    if st.session_state.get('confirmed_tech_stacks'):
        st.markdown(f"**Confirmed Tech Stacks:** {", ".join(st.session_state.confirmed_tech_stacks)}")
    st.markdown("---")

# Enable save if job title is present
save_app_button_ai = st.button("Save Application to Tracker", key="ai_save_app_btn_new", disabled=not ai_job_title_input)

if save_app_button_ai:
    if not ai_job_title_input or not ai_company_name_input: # Require title and company for job posting
        st.error("Job Title and Company Name are required to save the application.")
    else:
        # 1. Add Job Posting
        job_posting_id = add_job_posting(
            title=ai_job_title_input,
            company=ai_company_name_input,
            description=st.session_state.ai_job_description_input
        )

        if not job_posting_id:
            st.error("Failed to create or retrieve job posting entry.")
        else:
            # Cover letter and resume are now handled differently (e.g., via chat commands or specific tools)
            # For saving an application, we might need a way to select/link files if they were generated or uploaded.
            # This part needs to be re-thought based on new AI tool workflows.
            # For now, we'll assume resume_file_id might still be relevant if a resume was selected in the sidebar.
            cover_letter_file_id_ai = None # Placeholder - will be set if a CL is generated and saved by a new tool
            current_resume_file_id = st.session_state.get('ai_resume_id') # From sidebar selection

            app_id_ai = add_application(
                job_posting_id=job_posting_id,
                resume_file_id=current_resume_file_id, 
                cover_letter_file_id=cover_letter_file_id_ai, # This will likely be None for now
                submission_method=None, 
                notes="Application details potentially drafted with AI Assistant. Specific files (e.g., cover letter) may need to be linked manually or via new AI tools."
            )
            if app_id_ai:
                st.success(f"Application for '{st.session_state.ai_job_title_save}' saved with ID: {app_id_ai}. View/edit in Job Tracker.") # Use session state value for display
                log_application_status(app_id_ai, "Draft", "Application created via AI Assistant")
                
                # Save confirmed tags and tech stacks to parsed_metadata
                if st.session_state.get('confirmed_tags') or st.session_state.get('confirmed_tech_stacks'):
                    tags_json = json.dumps(st.session_state.get('confirmed_tags', []))
                    tech_stacks_json = json.dumps(st.session_state.get('confirmed_tech_stacks', []))
                    
                    metadata_id = add_or_update_parsed_metadata(
                        job_posting_id=job_posting_id,
                        tags=tags_json,
                        tech_stacks=tech_stacks_json
                        # Seniority and industry can be added later if extracted
                    )
                    if metadata_id:
                        st.info("Associated tags and tech stacks saved.")
                    else:
                        st.warning("Could not save tags and tech stacks for this job posting.")

                # Clear inputs and analysis data after saving
                st.session_state.ai_job_description_input = ""
                st.session_state.ai_job_title_save = "" # Now this should work
                st.session_state.ai_company_name_save = "" # And this
                st.session_state.confirmed_tags = []
                st.session_state.confirmed_tech_stacks = []
                st.session_state.selected_tags = []
                st.session_state.selected_tech_stacks = []
                st.session_state.ai_generated_tags = []
                st.session_state.ai_generated_tech_stacks = []
                st.session_state.show_analysis_results = False
                
                st.rerun() 
            else:
                st.error("Failed to save application to database via AI Assistant page.")
