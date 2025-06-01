import streamlit as st
import sys
import os

# Add the core directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'core'))

from core.services.llm_service import LlamaCppBackend, OllamaBackend, LLMService
from core.services.prompt_service import PromptService
from core.ui.streaming_ui import create_streaming_display

def main():
    st.set_page_config(page_title="Test Unified Streaming", layout="wide")
    
    st.title("🧪 Test Unified Streaming Architecture")
    st.markdown("This test verifies that both LlamaCpp and Ollama backends support streaming with the same UI.")
    
    # Backend selection
    backend_type = st.sidebar.selectbox(
        "Select Backend",
        ["LlamaCpp", "Ollama"],
        help="Choose between LlamaCpp (local) or Ollama (server)"
    )
    
    # Initialize the selected backend
    if backend_type == "LlamaCpp":
        if "llamacpp_backend" not in st.session_state:
            st.session_state.llamacpp_backend = LlamaCppBackend()
            if st.session_state.llamacpp_backend.initialize_model():
                st.session_state.llamacpp_prompt_service = PromptService(st.session_state.llamacpp_backend)
            else:
                st.session_state.llamacpp_prompt_service = None
        
        backend = st.session_state.llamacpp_backend
        prompt_service = st.session_state.llamacpp_prompt_service
        
        if not prompt_service:
            st.error("❌ Failed to initialize LlamaCpp model. Please check if the model file exists.")
            return
        else:
            st.success("✅ LlamaCpp Backend initialized successfully")
            
    else:  # Ollama
        # Get available Ollama models
        ollama_models = LLMService.get_ollama_models()
        
        if not ollama_models:
            st.error("❌ No Ollama models found. Please make sure Ollama is running.")
            st.markdown("**To start Ollama:**")
            st.code("ollama serve")
            st.markdown("**To pull a model:**")
            st.code("ollama pull llama3.2")
            return
        
        selected_model = st.sidebar.selectbox(
            "Select Ollama Model",
            ollama_models,
            help="Choose from available Ollama models"
        )
        
        if "ollama_backend" not in st.session_state or st.session_state.get("ollama_model") != selected_model:
            st.session_state.ollama_backend = OllamaBackend(selected_model)
            st.session_state.ollama_model = selected_model
            if st.session_state.ollama_backend.initialize_model():
                st.session_state.ollama_prompt_service = PromptService(st.session_state.ollama_backend)
            else:
                st.session_state.ollama_prompt_service = None
        
        backend = st.session_state.ollama_backend
        prompt_service = st.session_state.ollama_prompt_service
        
        if not prompt_service:
            st.error(f"❌ Failed to connect to Ollama model: {selected_model}")
            return
        else:
            st.success(f"✅ Ollama Backend initialized successfully with model: {selected_model}")
    
    # Show backend info
    model_info = backend.get_model_info()
    with st.expander("Backend Information", expanded=False):
        st.json(model_info)
    
    # Test streaming functionality
    st.subheader("🔄 Test Streaming Functionality")
    
    test_job_description = st.text_area(
        "Test Job Description:",
        value="""
Software Engineer - Full Stack Developer

We are looking for a talented Full Stack Developer to join our team. 

Requirements:
- 3+ years of experience with React and Node.js
- Experience with Python and Django
- Knowledge of AWS cloud services
- Strong understanding of databases (PostgreSQL, MongoDB)
- Experience with Docker and CI/CD pipelines

Location: San Francisco, CA (Remote friendly)
Company: TechCorp Inc.
Salary: $120k - $180k

Apply now to join our innovative team!
        """.strip(),
        height=200
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🚀 Test Streaming Analysis", key="test_streaming"):
            if test_job_description.strip():
                
                # Create separated UI component
                streaming_display = create_streaming_display(f"test_streaming_{backend_type.lower()}")
                container = streaming_display.initialize_container()
                
                # Get callback function from UI component
                update_callback = streaming_display.get_update_callback()
                
                # Test if backend supports streaming
                if hasattr(backend, 'generate_response_streaming'):
                    st.info(f"✅ {backend_type} backend supports streaming")
                    
                    # Call streaming analysis
                    with st.spinner("Analyzing job description with streaming..."):
                        result = prompt_service.analyze_job_description_streaming(
                            test_job_description,
                            update_callback=update_callback,
                            max_tokens=2000,
                            temperature=0.1
                        )
                    
                    if result:
                        st.success("✅ **Streaming Analysis Success!**")
                        st.divider()
                        
                        # Display parsed results
                        st.subheader("📊 Parsed Results")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Title:**", result.title or "Not specified")
                            st.write("**Company:**", getattr(result, 'company', 'Not specified'))
                            st.write("**Location:**", getattr(result, 'location', 'Not specified'))
                            st.write("**Type:**", getattr(result, 'type', 'Not specified'))
                        
                        with col2:
                            st.write("**Seniority:**", getattr(result, 'seniority', 'Not specified'))
                            st.write("**Industry:**", getattr(result, 'industry', 'Not specified'))
                            if hasattr(result, 'skills') and result.skills:
                                st.write("**Skills:**", result.skills[:100] + "..." if len(result.skills) > 100 else result.skills)
                    else:
                        st.warning("⚠️ Analysis failed or was cancelled")
                else:
                    st.error(f"❌ {backend_type} backend doesn't support streaming")
            else:
                st.warning("Please enter a job description")
    
    with col2:
        # Show cancel button only for LlamaCpp (as per requirement)
        if backend_type == "LlamaCpp":
            if st.button("⏹️ Cancel", key="cancel_generation"):
                if hasattr(backend, 'stop_generation'):
                    backend.stop_generation()
                    st.warning("🛑 Generation cancelled")
                else:
                    st.error("Backend doesn't support cancellation")
        else:
            st.info("💡 Cancel button only available for LlamaCpp backend")
    
    # Show streaming comparison
    st.divider()
    st.subheader("🔄 Streaming Backend Comparison")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🦙 LlamaCpp Backend**")
        st.markdown("""
        - ✅ Local model execution
        - ✅ Streaming support
        - ✅ Cancellation support
        - ✅ No internet required
        - ⚠️ Slower on CPU
        - ⚠️ Large model files
        """)
    
    with col2:
        st.markdown("**🦙 Ollama Backend**") 
        st.markdown("""
        - ✅ Server-based execution
        - ✅ Streaming support
        - ❌ No cancellation support
        - ✅ Faster responses
        - ⚠️ Requires Ollama server
        - ✅ Model management via CLI
        """)
    
    # Architecture benefits
    st.subheader("🏗️ Unified Architecture Benefits")
    st.markdown("""
    - **Shared UI Components**: Both backends use the same `StreamingDisplay` component
    - **Consistent Interface**: Same callback pattern for both backends
    - **Easy Switching**: Users can switch backends without changing workflow
    - **Conditional Features**: Cancel button only shown for backends that support it
    - **Clean Separation**: UI logic separated from service logic
    """)

if __name__ == "__main__":
    main()
