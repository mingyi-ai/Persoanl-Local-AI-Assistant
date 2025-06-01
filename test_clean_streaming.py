#!/usr/bin/env python3
"""
Clean streaming test - Shows the final streaming output without debug elements.
Run with: streamlit run test_clean_streaming.py
"""

import streamlit as st
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.services.llm_service import LlamaCppBackend
from core.services.prompt_service import PromptService

st.set_page_config(page_title="Clean Streaming Test", layout="wide")

st.title("✨ Clean Streaming Output Test")
st.markdown("This demonstrates the cleaned-up streaming functionality without debug elements.")
st.markdown("---")

# Initialize session state
if "clean_backend" not in st.session_state:
    st.session_state.clean_backend = None
if "clean_prompt_service" not in st.session_state:
    st.session_state.clean_prompt_service = None

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
                    st.session_state.clean_backend = backend
                    st.session_state.clean_prompt_service = PromptService(backend)
                    st.sidebar.success("✅ Model loaded!")
                else:
                    st.sidebar.error("❌ Failed to load model")
    else:
        st.sidebar.warning("No .gguf files found in core/models/")
else:
    st.sidebar.error("core/models/ directory not found")

# Show current status
st.sidebar.markdown("### 📊 Status")
is_ready = st.session_state.clean_prompt_service is not None
st.sidebar.write(f"**Backend Ready:** {'✅' if is_ready else '❌'}")

# Main area
if st.session_state.clean_prompt_service:
    st.markdown("### 🤖 AI Job Description Analyzer")
    
    job_description = st.text_area(
        "Paste job description here:",
        value="""Senior Software Engineer - Backend
Company: TechStart Inc.
Location: Remote (US timezones)

We are looking for a Senior Backend Engineer to join our growing team. 

Requirements:
- 5+ years experience with Python and Django
- Experience with PostgreSQL and Redis
- Knowledge of AWS services (EC2, RDS, S3)
- Familiarity with Docker and Kubernetes
- Strong understanding of RESTful APIs
- Experience with microservices architecture

Nice to have:
- React.js knowledge
- DevOps experience
- Previous startup experience

Type: Full-time
Salary: $120k - $160k""",
        height=250
    )
    
    # Check if we're currently generating
    is_generating = st.session_state.get("clean_analysis_generating", False)
    
    # Create columns for buttons
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if not is_generating:
            if st.button("🔍 Analyze Description"):
                st.session_state.clean_analysis_generating = True
                st.rerun()
        else:
            st.info("🔄 Analyzing job description...")
    
    with col2:
        # Show cancel button when generating
        if is_generating:
            if st.button("⏹️ Cancel", type="secondary"):
                if hasattr(st.session_state.clean_backend, 'stop_generation'):
                    st.session_state.clean_backend.stop_generation()
                st.session_state.clean_analysis_generating = False
                st.warning("Analysis cancelled")
                st.rerun()
    
    # Handle generation when in generating state
    if is_generating:
        # Create streaming output container
        st.markdown("### 🔄 AI Analysis in Progress")
        response_container = st.empty()
        
        try:
            # Use streaming analysis
            result = st.session_state.clean_prompt_service.analyze_job_description(
                job_description,
                stream=True,
                response_container=response_container,
                max_tokens=1500,
                temperature=0.1
            )
            
            # Reset generating state
            st.session_state.clean_analysis_generating = False
            
            if result:
                # Clear streaming container and show results
                response_container.empty()
                
                # Display analysis preview
                st.divider()
                st.subheader("📋 Analysis Results")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Basic Information**")
                    st.write(f"**Title:** {result.title}")
                    if hasattr(result, 'company') and result.company:
                        st.write(f"**Company:** {result.company}")
                    if hasattr(result, 'location') and result.location:
                        st.write(f"**Location:** {result.location}")
                
                with col2:
                    st.write("**Skills Analysis**")
                    if result.skills:
                        st.write("**Skills:**")
                        skills_list = result.skills.split(', ')
                        for skill in skills_list[:5]:  # Show first 5
                            st.write(f"• {skill}")
                        if len(skills_list) > 5:
                            st.write(f"• ... and {len(skills_list) - 5} more")
                
                st.success("✅ Analysis complete!")
                
                # Show full parsed data
                with st.expander("📊 Full Parsed Data", expanded=False):
                    st.json({
                        "title": result.title,
                        "company": getattr(result, 'company', ''),
                        "location": getattr(result, 'location', ''),
                        "type": getattr(result, 'type', ''),
                        "seniority": getattr(result, 'seniority', ''),
                        "skills": getattr(result, 'skills', ''),
                        "tags": getattr(result, 'tags', ''),
                        "industry": getattr(result, 'industry', '')
                    })
            else:
                response_container.empty()
                st.error("Failed to analyze job description. Please try again.")
            
            st.rerun()
                
        except Exception as e:
            st.session_state.clean_analysis_generating = False
            response_container.empty()
            st.error(f"Error during analysis: {str(e)}")
            st.rerun()

else:
    st.info("👈 Please initialize a model in the sidebar to start testing")

# Footer
st.markdown("---")
st.caption("Clean streaming interface without debug elements")
