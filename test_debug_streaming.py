#!/usr/bin/env python3
"""
Debug test for streaming functionality with enhanced UI debugging.

This script tests the enhanced streaming functionality with debug output
and cancel capability in the Job Description Analyzer.

Run with: streamlit run test_debug_streaming.py
"""

import streamlit as st
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.services.llm_service import LlamaCppBackend
from core.services.prompt_service import PromptService

st.set_page_config(page_title="Debug Streaming Test", layout="wide")

st.title("🐛 Debug Streaming Test")
st.markdown("---")

# Initialize session state
if "debug_backend" not in st.session_state:
    st.session_state.debug_backend = None
if "debug_prompt_service" not in st.session_state:
    st.session_state.debug_prompt_service = None

# Sidebar setup
st.sidebar.markdown("### 🔧 Setup")

# Model file selection
models_dir = Path("core/models")
if models_dir.exists():
    model_files = [f for f in models_dir.iterdir() if f.suffix == '.gguf']
    if model_files:
        selected_model = st.sidebar.selectbox(
            "Select Model:",
            options=[f.name for f in model_files],
            index=0
        )
        
        if st.sidebar.button("Initialize Model"):
            with st.spinner("Loading model..."):
                backend = LlamaCppBackend(str(models_dir / selected_model))
                if backend.initialize_model():
                    st.session_state.debug_backend = backend
                    st.session_state.debug_prompt_service = PromptService(backend)
                    st.sidebar.success("✅ Model loaded!")
                else:
                    st.sidebar.error("❌ Failed to load model")
    else:
        st.sidebar.warning("No .gguf files found in core/models/")
else:
    st.sidebar.error("core/models/ directory not found")

# Show session state info
st.sidebar.markdown("### 📊 Session State")
st.sidebar.write(f"**Stop Flag:** {st.session_state.get('llm_stop_generation', False)}")
st.sidebar.write(f"**Backend:** {'✅' if st.session_state.debug_backend else '❌'}")
st.sidebar.write(f"**Service:** {'✅' if st.session_state.debug_prompt_service else '❌'}")

# Reset button
if st.sidebar.button("🔄 Reset All"):
    for key in list(st.session_state.keys()):
        if key.startswith(('debug_', 'llm_')):
            del st.session_state[key]
    st.rerun()

# Main area
if st.session_state.debug_prompt_service:
    st.markdown("### 🤖 Streaming Test")
    
    test_job_description = st.text_area(
        "Test Job Description:",
        value="""Software Engineer
Company: TechCorp
Location: San Francisco, CA
Requirements: Python, JavaScript, React, Node.js
Experience: 3+ years
Type: Full-time""",
        height=150
    )
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🧪 Test Streaming Analysis"):
            st.session_state.test_running = True
            st.rerun()
    
    with col2:
        if st.session_state.get('test_running', False):
            if st.button("⏹️ Stop Test"):
                if hasattr(st.session_state.debug_backend, 'stop_generation'):
                    st.session_state.debug_backend.stop_generation()
                st.session_state.test_running = False
                st.warning("Test stopped!")
                st.rerun()
    
    # Run the test
    if st.session_state.get('test_running', False):
        st.markdown("### 🔄 Live Streaming Output")
        
        # Debug containers
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("**🤖 AI Generation Stream:**")
            response_container = st.empty()
        
        with col2:
            st.markdown("**📊 Debug Info:**")
            debug_info = st.empty()
        
        try:
            # Show debug info
            debug_info.info(f"""
**Backend:** {st.session_state.debug_backend.__class__.__name__}
**Stop Flag:** {st.session_state.get('llm_stop_generation', False)}
**Test Running:** {st.session_state.get('test_running', False)}
            """)
            
            # Run streaming analysis
            result = st.session_state.debug_prompt_service.analyze_job_description(
                test_job_description,
                stream=True,
                response_container=response_container,
                max_tokens=500,
                temperature=0.1
            )
            
            st.session_state.test_running = False
            
            if result:
                st.success("✅ Test completed successfully!")
                st.json({
                    "title": result.title,
                    "company": getattr(result, 'company', ''),
                    "location": getattr(result, 'location', ''),
                    "skills": getattr(result, 'skills', '')
                })
            else:
                st.error("❌ Test failed - no result returned")
                
        except Exception as e:
            st.session_state.test_running = False
            st.error(f"❌ Test error: {str(e)}")
        
        st.rerun()

else:
    st.info("👈 Please initialize a model in the sidebar to start testing")

# Footer
st.markdown("---")
st.caption("This is a debug test for the streaming functionality with enhanced UI debugging.")
