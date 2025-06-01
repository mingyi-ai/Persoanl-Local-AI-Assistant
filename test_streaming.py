#!/usr/bin/env python3
"""
Test script for the streaming LLM functionality.
This script tests the new streaming response feature with stop capability.
"""

import streamlit as st
from pathlib import Path
import sys

# Add the project root to the Python path
sys.path.append(str(Path(__file__).parent))

from core.services.llm_service import LlamaCppBackend, OllamaBackend
from core.services.prompt_service import PromptService

def test_streaming_functionality():
    """Test the streaming functionality with stop capability."""
    
    st.set_page_config(page_title="LLM Streaming Test", layout="wide")
    st.title("🧪 LLM Streaming Functionality Test")
    
    # Initialize session state
    if "test_backend" not in st.session_state:
        st.session_state.test_backend = None
    if "test_prompt_service" not in st.session_state:
        st.session_state.test_prompt_service = None
    
    # Backend selection
    st.sidebar.header("Backend Configuration")
    backend_type = st.sidebar.radio("Select Backend:", ["LlamaCpp", "Ollama"])
    
    if backend_type == "LlamaCpp":
        models_dir = Path("core/models")
        if models_dir.exists():
            gguf_files = [f.name for f in models_dir.iterdir() if f.suffix.lower() == '.gguf']
            if gguf_files:
                selected_model = st.sidebar.selectbox("Select Model:", gguf_files)
                if st.sidebar.button("Initialize LlamaCpp"):
                    with st.spinner("Initializing LlamaCpp..."):
                        backend = LlamaCppBackend(str(models_dir / selected_model))
                        if backend.initialize_model():
                            st.session_state.test_backend = backend
                            st.session_state.test_prompt_service = PromptService(backend)
                            st.sidebar.success("✅ LlamaCpp initialized!")
                        else:
                            st.sidebar.error("❌ Failed to initialize LlamaCpp")
            else:
                st.sidebar.warning("No .gguf models found in core/models/")
        else:
            st.sidebar.warning("Models directory not found")
    
    else:  # Ollama
        if st.sidebar.button("Initialize Ollama"):
            with st.spinner("Initializing Ollama..."):
                from core.services.llm_service import LLMService
                models = LLMService.get_ollama_models()
                if models:
                    backend = OllamaBackend(models[0])
                    if backend.initialize_model():
                        st.session_state.test_backend = backend
                        st.session_state.test_prompt_service = PromptService(backend)
                        st.sidebar.success(f"✅ Ollama initialized with {models[0]}!")
                    else:
                        st.sidebar.error("❌ Failed to initialize Ollama")
                else:
                    st.sidebar.error("❌ No Ollama models available")
    
    # Main testing area
    if st.session_state.test_prompt_service:
        st.header("🔍 Test Job Description Analysis")
        
        # Sample job description
        sample_job = st.text_area(
            "Job Description:",
            value="""Software Engineer - Python Backend
            
We are looking for a talented Python backend developer to join our team. 
You will be responsible for building scalable web applications using Django/Flask, 
working with PostgreSQL databases, and deploying applications using Docker and Kubernetes.

Requirements:
- 3+ years of Python experience
- Experience with Django or Flask
- Knowledge of SQL and database design
- Familiarity with cloud platforms (AWS, GCP)
- Understanding of REST APIs and microservices

Location: San Francisco, CA (Remote friendly)
Type: Full-time
Company: TechCorp Inc.
""",
            height=200
        )
        
        # Test buttons
        col1, col2 = st.columns([3, 1])
        
        is_generating = st.session_state.get("test_generating", False)
        
        with col1:
            if not is_generating:
                if st.button("🔍 Analyze (Streaming)", key="test_analyze"):
                    st.session_state.test_generating = True
                    st.rerun()
            else:
                st.info("🔄 Analyzing job description...")
        
        with col2:
            # Show cancel button only for LlamaCpp and when generating
            if (is_generating and 
                hasattr(st.session_state.test_backend, 'stop_generation')):
                
                if st.button("⏹️ Stop", key="test_stop", type="secondary"):
                    st.session_state.test_backend.stop_generation()
                    st.session_state.test_generating = False
                    st.warning("Analysis stopped by user")
                    st.rerun()
        
        # Handle generation
        if is_generating:
            response_container = st.empty()
            
            try:
                # Test streaming
                if hasattr(st.session_state.test_backend, 'generate_response_streaming'):
                    st.info("🔄 Using streaming generation...")
                    result = st.session_state.test_prompt_service.analyze_job_description(
                        sample_job,
                        stream=True,
                        response_container=response_container,
                        max_tokens=1000,
                        temperature=0.1
                    )
                else:
                    st.info("🔄 Using standard generation...")
                    result = st.session_state.test_prompt_service.analyze_job_description(sample_job)
                
                st.session_state.test_generating = False
                
                if result:
                    response_container.empty()
                    st.success("✅ Analysis completed!")
                    
                    # Display results
                    st.json({
                        "title": result.title,
                        "company": getattr(result, 'company', ''),
                        "location": getattr(result, 'location', ''),
                        "skills": getattr(result, 'skills', ''),
                        "type": getattr(result, 'type', ''),
                    })
                else:
                    response_container.empty()
                    st.error("❌ Analysis failed")
                
                st.rerun()
                
            except Exception as e:
                st.session_state.test_generating = False
                response_container.empty()
                st.error(f"❌ Error: {str(e)}")
                st.rerun()
    
    else:
        st.info("👆 Please initialize a backend in the sidebar to test streaming functionality")
    
    # Display backend info
    if st.session_state.test_backend:
        st.sidebar.divider()
        st.sidebar.header("Backend Info")
        model_info = st.session_state.test_backend.get_model_info()
        st.sidebar.json(model_info)

if __name__ == "__main__":
    test_streaming_functionality()
