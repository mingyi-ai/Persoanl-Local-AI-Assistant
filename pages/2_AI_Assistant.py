# Placeholder for AI Assistant page
import streamlit as st
from pathlib import Path
import time
import subprocess # For Ollama CLI interaction
import json # For parsing Ollama responses
import requests # For direct Ollama API access (commented out code)
import re # For processing <think> tags
import traceback # For enhanced error reporting

# Import LangChain components
try:
    import langchain_community
    from langchain_community.llms import Ollama
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    st.warning("LangChain packages not found. Consider installing with: pip install langchain langchain-community langchain-core")

# Attempt to import OllamaLLM, fall back to Ollama if not found
try:
    from langchain_ollama.llms import OllamaLLM
    # Use OllamaLLM as preferred if available
except ImportError:
    try:
        if not LANGCHAIN_AVAILABLE:
            from langchain_community.llms import Ollama
        OllamaLLM = Ollama # Alias if new one not found
        st.warning("Consider upgrading to `langchain-ollama` for the latest Ollama integration. Using fallback `langchain_community.llms.Ollama`.")
    except ImportError:
        OllamaLLM = None # Placeholder if no Ollama integration is found
        st.error("Ollama LLM integration not found. Please install `langchain-ollama` or `langchain-community`.")

from core.file_utils import save_uploaded_file, COVER_LETTERS_DIR, save_cover_letter, get_file_hash
from core.ai_tools import (
    extract_text_from_pdf, 
    score_resume_job_description, 
    generate_cover_letter, 
    analyze_job_description_with_ollama,
    analyze_job_description_with_langchain,
    stream_langchain_response_with_think_processing
)
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
if 'ai_langchain_llm' not in st.session_state:  # New LangChain LLM instance
    st.session_state.ai_langchain_llm = None
if 'ai_ollama_not_found' not in st.session_state:
    st.session_state.ai_ollama_not_found = False
if 'use_langchain' not in st.session_state:  # Flag to enable LangChain processing
    st.session_state.use_langchain = LANGCHAIN_AVAILABLE
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

# Function to stream responses using LangChain (replacing direct Ollama API)
# Previous direct Ollama API implementation has been commented out
# def stream_ollama_response(prompt, model_name, ollama_base_url=OLLAMA_BASE_URL):
#     """Stream a response from Ollama API directly (replaced with LangChain)"""
#     api_url = f"{ollama_base_url}/api/generate"
#     payload = {
#         "model": model_name,
#         "prompt": prompt,
#         "stream": True
#     }
#     
#     try:
#         response = requests.post(api_url, json=payload, stream=True)
#         response.raise_for_status()
#         
#         accumulated_response = ""
#         for line in response.iter_lines():
#             if not line:
#                 continue
#             
#             try:
#                 json_response = json.loads(line)
#                 if 'response' in json_response:
#                     chunk = json_response['response']
#                     accumulated_response += chunk
#                     yield chunk, accumulated_response
#                 
#                 if json_response.get('done', False):
#                     break
#             except json.JSONDecodeError:
#                 print(f"Error decoding JSON: {line}")
#     except Exception as e:
#         print(f"Error with Ollama API: {e}")
#         yield f"API error: {str(e)}", f"API error: {str(e)}"

def stream_langchain_response(prompt, langchain_llm):
    """Stream a response using LangChain with <think> tag processing and verbose debug output"""
    print(f"DEBUG: Using LangChain streaming for prompt: {prompt[:100]}...")
    
    # Create a simple chain with verbose debugging
    prompt_template = PromptTemplate.from_template("{context}")
    chain = prompt_template | langchain_llm | StrOutputParser()
    
    # Stream the response and process it
    accumulated_response = ""
    print("DEBUG: Starting LangChain streaming response...")
    start_time = time.time()
    
    try:
        for chunk in chain.stream({"context": prompt}):
            if chunk:
                # Debug output with chunk preview
                chunk_preview = chunk[:50].replace('\n', ' ')
                print(f"DEBUG: LangChain chunk received ({len(chunk)} chars): '{chunk_preview}...'")
                
                accumulated_response += chunk
                yield chunk, accumulated_response
        
        elapsed_time = time.time() - start_time
        print(f"DEBUG: LangChain streaming complete in {elapsed_time:.2f}s. Total response length: {len(accumulated_response)}")
    except Exception as e:
        print(f"DEBUG ERROR: Exception during LangChain streaming: {type(e).__name__}: {str(e)}")
        # Re-raise to be handled by the caller
        raise

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
            context = "<think>I am a job search assistant specializing in career advice, resume building, and interview preparation. I'll think carefully about my response.</think>\n\n"
            context += "You are a helpful AI assistant specializing in job search advice, resume building, and interview preparation.\n\n"
            
            # Add last few messages for context
            for msg in st.session_state.chat_messages[-6:]:  # Last 6 messages (3 exchanges)
                if msg["role"] == "user":
                    context += f"Human: {msg['content']}\n"
                else:
                    context += f"Assistant: {msg['content']}\n"
            
            # Add the current query
            context += f"\nHuman: {user_query}\nAssistant:"
            
            # All processing now uses LangChain - direct Ollama API calls have been removed
            message_placeholder.info("Processing with LangChain...")
            _final_processed_response_for_display_and_history = ""
            
            print(f"DEBUG: Chat request with query: '{user_query}', using model: {st.session_state.ai_selected_model_name}")
            print(f"DEBUG: Starting chat response generation with LangChain")
            print(f"DEBUG: LangChain LLM type: {type(st.session_state.ai_langchain_llm).__name__}")
            print(f"DEBUG: Full context length: {len(context)} chars")
            
            try:
                if LANGCHAIN_AVAILABLE and st.session_state.ai_langchain_llm:
                    # Define a callback for UI updates
                    def update_ui(text, cursor=""):
                        message_placeholder.markdown(text + cursor)
                        
                    # Stream and process the response using the core function
                    print("DEBUG: Calling stream_langchain_response_with_think_processing")
                    print(f"DEBUG: Context preview: {context[:200]}...")
                    
                    # Create streaming chain directly for more control
                    stream = st.session_state.ai_langchain_llm.stream(context)
                    
                    # Measure processing time for debugging
                    process_start_time = time.time()
                    raw_response, display_response = stream_langchain_response_with_think_processing(
                        stream, 
                        response_callback=update_ui
                    )
                    process_time = time.time() - process_start_time
                    
                    print(f"DEBUG: Processing completed in {process_time:.2f}s")
                    print(f"DEBUG: Raw response length: {len(raw_response)}")
                    print(f"DEBUG: Display response length: {len(display_response)}")
                    
                    # Store the processed response
                    _final_processed_response_for_display_and_history = display_response
                    print(f"DEBUG: Response processing complete. Display length: {len(display_response)}")
                else:
                    error_msg = "LangChain processing is not available. Please enable LangChain in the sidebar."
                    message_placeholder.error(error_msg)
                    _final_processed_response_for_display_and_history = error_msg
            except Exception as e:
                error_msg = f"Error with LangChain processing: {str(e)}"
                print(f"DEBUG ERROR: {error_msg}")
                print(f"DEBUG ERROR TYPE: {type(e).__name__}")
                print(f"DEBUG ERROR DETAILS: {e}")
                import traceback
                print(f"DEBUG ERROR TRACEBACK: {traceback.format_exc()}")
                
                # Enhanced error message for UI
                message_placeholder.error(error_msg)
                _final_processed_response_for_display_and_history = f"I'm sorry, I encountered an error: {str(e)}"
                
            # Variables used by the <think> processing
            _thinking_active = False
            _first_think_block_processed = False
            raw_cumulative_response_from_model = "" # For compatibility with existing code

            # Direct streaming with Ollama API has been commented out
            # We're now exclusively using LangChain with stream_langchain_response_with_think_processing
            try:
                # No need for a streaming loop here, as we're using the callback-based streaming
                # in stream_langchain_response_with_think_processing
                
                # Log completion with detailed info
                print("DEBUG: Chat response generation complete")
                print(f"DEBUG: Final response length: {len(_final_processed_response_for_display_and_history)} chars")
                
                # Check for <think> tags in final response (shouldn't be any)
                if "<think>" in _final_processed_response_for_display_and_history:
                    print("DEBUG WARNING: <think> tag found in final response!")
                if "</think>" in _final_processed_response_for_display_and_history:
                    print("DEBUG WARNING: </think> tag found in final response!")
                
                # Final response is already stored in _final_processed_response_for_display_and_history
                # from the stream_langchain_response_with_think_processing function
                
                # Update UI and chat history with final response
                if _final_processed_response_for_display_and_history:
                    print("DEBUG: Updating UI with final response")
                    message_placeholder.markdown(_final_processed_response_for_display_and_history)
                    # Add the processed response to chat history
                    st.session_state.chat_messages.append({"role": "assistant", "content": _final_processed_response_for_display_and_history})
                    print("DEBUG: Response added to chat history")
                elif not ("API error:" in _final_processed_response_for_display_and_history): # Avoid double error message if API error already handled
                    print("DEBUG ERROR: Empty response received from LangChain")
                    message_placeholder.error("Failed to generate a response. Please try again.")
                    st.session_state.chat_messages.append({"role": "assistant", "content": "Failed to generate a response."})

            except Exception as e:
                error_msg = f"Error during AI response processing: {str(e)}"
                print(f"DEBUG ERROR: {error_msg}")
                print(f"DEBUG ERROR TYPE: {type(e).__name__}")
                import traceback
                print(f"DEBUG ERROR TRACEBACK: {traceback.format_exc()}")
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
        st.session_state.ai_langchain_llm = None
    else:
        available_models_ai = get_ollama_models_ai_page()
        if available_models_ai:
            default_model_ai = st.session_state.ai_selected_model_name
            if not default_model_ai or default_model_ai not in available_models_ai:
                # If no model selected, or selected model is not in the current list, default to the first one
                default_model_ai = available_models_ai[0]

            # default_model_ai is now guaranteed to be a model name that exists in available_models_ai.
            # So, we can directly find its index.
            select_box_idx = available_models_ai.index(default_model_ai)

            chosen_model_name_ai = st.selectbox(
                "Choose an AI model:",
                options=available_models_ai,
                index=select_box_idx, # Use the determined index
                key="ai_ollama_model_selector"
            )

            if st.session_state.ai_llm_instance is None or st.session_state.ai_selected_model_name != chosen_model_name_ai:
                with st.spinner(f"Initializing AI model: {chosen_model_name_ai}..."):
                    try:
                        # For direct Ollama API
                        st.session_state.ai_llm_instance = chosen_model_name_ai
                        
                        # For LangChain integration if available
                        if LANGCHAIN_AVAILABLE:
                            try:
                                print(f"DEBUG: Initializing LangChain with model {chosen_model_name_ai}")
                                # Create the LangChain LLM instance
                                st.session_state.ai_langchain_llm = Ollama(model=chosen_model_name_ai)
                                
                                # Test if it's working with a simple invoke
                                print("DEBUG: Testing LangChain LLM with a simple invoke")
                                test_start_time = time.time()
                                test_response = st.session_state.ai_langchain_llm.invoke("Test")
                                test_elapsed = time.time() - test_start_time
                                
                                print(f"DEBUG: LangChain test successful in {test_elapsed:.2f}s")
                                print(f"DEBUG: Test response length: {len(test_response)} chars")
                                st.success(f"LangChain integration enabled with {chosen_model_name_ai}")
                            except Exception as e:
                                print(f"DEBUG ERROR: LangChain initialization failed: {type(e).__name__}: {e}")
                                import traceback
                                print(f"DEBUG ERROR TRACEBACK: {traceback.format_exc()}")
                                st.warning(f"LangChain initialization failed: {e}")
                                st.session_state.ai_langchain_llm = None
                                st.session_state.use_langchain = False
                        
                        st.session_state.ai_selected_model_name = chosen_model_name_ai
                        
                        # Add a welcome message when model changes
                        if st.session_state.chat_messages:
                            st.session_state.chat_messages.append({
                                "role": "assistant", 
                                "content": f"I've switched to the {chosen_model_name_ai} model. How can I help you with your job search?"
                            })
                        
                        st.success(f"AI model {chosen_model_name_ai} initialized.")
                        st.rerun() # Force a rerun to ensure UI consistency after model selection and initialization
                    except Exception as e:
                        st.error(f"Failed to initialize model {chosen_model_name_ai}: {e}")
                        st.session_state.ai_llm_instance = None
                        st.session_state.ai_selected_model_name = None
            
            # LangChain checkbox toggle (only if LangChain is available and langchain_llm exists)
            if LANGCHAIN_AVAILABLE and st.session_state.ai_langchain_llm:
                prev_value = st.session_state.use_langchain
                st.session_state.use_langchain = st.checkbox(
                    "Use LangChain processing", 
                    value=st.session_state.use_langchain,
                    help="When enabled, uses LangChain for response handling with <think> tag processing"
                )
                
                # Debug information when toggle changes
                if prev_value != st.session_state.use_langchain:
                    new_state = "enabled" if st.session_state.use_langchain else "disabled"
                    print(f"DEBUG: LangChain processing {new_state} by user")
            else:
                # Debug why the LangChain toggle isn't shown
                if not LANGCHAIN_AVAILABLE:
                    print("DEBUG: LangChain toggle not shown because LangChain is not available")
                else:
                    print("DEBUG: LangChain toggle not shown because langchain_llm is not initialized")
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
            # Use LangChain if enabled and available
            print(f"DEBUG: Job description analysis - LangChain enabled: {LANGCHAIN_AVAILABLE and st.session_state.use_langchain}")
            
            if LANGCHAIN_AVAILABLE and st.session_state.use_langchain and st.session_state.ai_langchain_llm:
                print(f"DEBUG: Using LangChain for job description analysis (model: {st.session_state.ai_selected_model_name})")
                print(f"DEBUG: Job description length: {len(st.session_state.ai_job_description_input)} chars")
                
                # Measure processing time
                start_time = time.time()
                analysis_results, raw_response = analyze_job_description_with_langchain(
                    st.session_state.ai_langchain_llm,
                    st.session_state.ai_job_description_input
                )
                elapsed_time = time.time() - start_time
                
                print(f"DEBUG: LangChain job analysis completed in {elapsed_time:.2f}s")
                # Log the results summarily
                tags_count = len(analysis_results.get("tags", []))
                tech_stacks_count = len(analysis_results.get("tech_stacks", []))
                print(f"DEBUG: Analysis found {tags_count} tags and {tech_stacks_count} tech stacks")
                print(f"DEBUG: Raw response length: {len(raw_response)} chars")
            else:
                print("DEBUG: Using direct Ollama API for job description analysis (deprecated)")
                print("DEBUG: This code path will be fully removed in the future")
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
