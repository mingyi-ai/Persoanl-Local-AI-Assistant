import streamlit as st
import logging
from typing import List, Dict, Optional, Literal
from core.LLM_backends import (
    LLMBackend, LlamaCppBackend, OllamaBackend, get_ollama_models
)
from core.langchain_tools import LangChainBackend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="Testing Interface")
st.title("🧪 Testing Interface")

st.info("💡 **Note:** This page is for testing AI models and functionality. The main application is on the home page.")

class JobAnalyzer:
    def __init__(self, langchain_backend: LangChainBackend):
        self.langchain_backend = langchain_backend

    def render(self):
        st.header("🎯 Job Description Analyzer")
        
        # Text area for job description
        job_description = st.text_area(
            "Paste job description here",
            height=200,
            key="job_description_input"
        )

        if st.button("Analyze", key="analyze_button"):
            if not job_description:
                st.warning("Please paste a job description first.")
                return

            with st.spinner("Analyzing job description..."):
                result = self.langchain_backend.analyze_job_description(job_description)
                
                if result:
                    # Display results in a structured way
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Basic Information")
                        st.write(f"**Title:** {result.title}")
                        st.write(f"**Job Type:** {result.job_type}")
                        st.write(f"**Experience:** {result.experience_level}")
                        st.write(f"**Education:** {result.education}")
                    
                    with col2:
                        st.subheader("Skills")
                        st.write("**Required Skills:**")
                        for skill in result.required_skills:
                            st.markdown(f"- {skill}")
                        
                        st.write("**Preferred Skills:**")
                        for skill in result.preferred_skills:
                            st.markdown(f"- {skill}")
                else:
                    st.error("Failed to analyze job description. Please try again.")

class ChatInterface:
    def __init__(self, backend: LLMBackend):
        self.backend = backend
        self.initialize_session_state()

    @staticmethod
    def initialize_session_state():
        if "messages" not in st.session_state:
            st.session_state.messages = []
        if "dev_mode" not in st.session_state:
            st.session_state.dev_mode = False

    def render(self):
        st.header("💬 Chat Interface")
        
        # Sidebar controls
        with st.sidebar:
            st.subheader("Model Information")
            model_info = self.backend.get_model_info()
            for key, value in model_info.items():
                st.text(f"{key}: {value}")
            
            # Only show generation parameters in dev mode and for LlamaCpp backend
            show_params = st.session_state.dev_mode and isinstance(self.backend, LlamaCppBackend)
            
            if show_params:
                st.subheader("Generation Parameters")
                temperature = st.slider("Temperature", 0.0, 2.0, 0.7, 0.1,
                                     help="Higher values make the output more random, lower values make it more focused and deterministic",
                                     key="temperature_slider")
                top_p = st.slider("Top P", 0.0, 1.0, 0.95, 0.05,
                                help="Controls diversity by selecting most probable tokens whose cumulative probability exceeds p",
                                key="top_p_slider")
                max_tokens = st.slider("Max Tokens", 16, 2048, 512, 16,
                                     help="Maximum number of tokens to generate",
                                     key="max_tokens_slider")
            else:
                # Default values when not in dev mode or using Ollama
                temperature = 0.7
                top_p = 0.95
                max_tokens = 512
            
            # Clear chat button
            if st.button("Clear Chat", key="clear_chat_btn"):
                st.session_state.messages = []
                st.rerun()

        # Create a fixed height container for the chat interface
        chat_container = st.container()
        
        with chat_container:
            # Chat messages area with fixed height
            st.markdown('<div style="height: 400px; overflow-y: auto;">', unsafe_allow_html=True)
            
            # Display chat messages
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Chat input area
            input_container = st.container()
            
            with input_container:
                # Check model status
                model_ready = isinstance(self.backend, (OllamaBackend, LlamaCppBackend)) and self.backend.initialize_model()
                if not model_ready:
                    st.error("Failed to initialize model. Please check logs.")
                    return
                
                # Chat input
                if prompt := st.chat_input("Type your message here..."):
                    # Add user message to chat history
                    user_msg = {"role": "user", "content": prompt}
                    st.session_state.messages.append(user_msg)
                    
                    # Display user message
                    with st.chat_message("user"):
                        st.write(prompt)
                    
                    # Generate and display assistant response
                    with st.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            response = self.backend.generate_response(
                                st.session_state.messages,
                                temperature=temperature,
                                top_p=top_p,
                                max_tokens=max_tokens
                            )
                            if response:
                                st.write(response)
                                # Add assistant message to chat history
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": response
                                })
                            else:
                                st.error("Failed to generate response. Please try again.")

# Main execution
def main():
    # Initialize dev mode in session state
    if "dev_mode" not in st.session_state:
        st.session_state.dev_mode = False
    
    if "current_backend" not in st.session_state:
        st.session_state.current_backend = None
        
    with st.sidebar:
        # Developer mode toggle at the top with a unique key
        st.session_state.dev_mode = st.checkbox(
            "Developer Mode",
            value=st.session_state.dev_mode,
            key="dev_mode_toggle"
        )
        
        if st.session_state.dev_mode:
            st.title("Model Selection")
            backend_type = st.radio(
                "Select Backend",
                ["Ollama", "LlamaCpp"],
                index=0,  # Default to Ollama
                help="Choose between Ollama (requires Ollama server running) or local LlamaCpp models",
                key="backend_select"
            )
        else:
            # In user mode, default to Ollama if available, fallback to LlamaCpp
            available_models = get_ollama_models()
            backend_type = "Ollama" if available_models else "LlamaCpp"
    
    # Initialize the appropriate backend
    if backend_type == "Ollama":
        available_models = get_ollama_models()
        if not available_models:
            st.sidebar.error("No Ollama models found. Make sure Ollama is running.")
            if st.session_state.dev_mode:
                return
            else:
                # Fallback to LlamaCpp in user mode
                llm_backend = LlamaCppBackend()
                with st.spinner("Initializing local model..."):
                    llm_backend.initialize_model()
        else:
            if st.session_state.dev_mode:
                selected_model = st.sidebar.selectbox(
                    "Select Ollama Model",
                    options=available_models,
                    index=0 if available_models else None,
                    key="ollama_model_select"
                )
            else:
                selected_model = available_models[0]
                st.sidebar.info(f"Using Ollama model: {selected_model}")
            
            if selected_model:
                llm_backend = OllamaBackend(selected_model)
                with st.spinner(f"Connecting to Ollama ({selected_model})..."):
                    if not llm_backend.initialize_model():
                        st.error("Failed to connect to Ollama. Please check if the service is running.")
                        return
            else:
                st.sidebar.error("Please select a model to continue")
                return
    else:
        # LlamaCpp backend
        llm_backend = LlamaCppBackend()
        with st.spinner("Loading local model..."):
            if not llm_backend.initialize_model():
                st.error("Failed to load local model. Please check if the model file exists.")
                return
    
    # Store the current backend in session state
    st.session_state.current_backend = llm_backend
    
    # Initialize LangChain backend wrapper
    langchain_backend = LangChainBackend(llm_backend)
    
    # Page title
    st.title("🤖 AI Assistant Test Interface")
    
    # Initialize and render job analyzer
    job_analyzer = JobAnalyzer(langchain_backend)
    job_analyzer.render()
    
    # Add some spacing
    st.markdown("---")
    
    # Initialize and render chat interface
    chat_interface = ChatInterface(llm_backend)
    chat_interface.render()

if __name__ == "__main__":
    main()

