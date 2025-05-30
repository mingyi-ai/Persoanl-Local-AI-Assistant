import streamlit as st
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Literal
from pathlib import Path
import logging
import subprocess
import json
from llama_cpp import Llama
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODELS_DIR = Path("core/model")
DEFAULT_MODEL = "Qwen3-8B-Q4_K_M.gguf"
OLLAMA_BASE_URL = "http://localhost:11434"

# Helper function to get available Ollama models
def get_ollama_models():
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            return [model['name'] for model in models]
        return []
    except requests.RequestException:
        return []

# Abstract base class for LLM backends
class LLMBackend(ABC):
    @abstractmethod
    def initialize_model(self) -> bool:
        """Initialize the model. Return True if successful."""
        pass

    @abstractmethod
    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Generate a response from the model given a list of messages."""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the currently loaded model."""
        pass

class LlamaCppBackend(LLMBackend):
    def __init__(self, model_path: str = str(MODELS_DIR / DEFAULT_MODEL)):
        self.model_path = model_path
        logger.info(f"Initializing LlamaCpp backend with model: {model_path}")
        # Move model to session state
        if "llm_model" not in st.session_state:
            st.session_state.llm_model = None

    def initialize_model(self) -> bool:
        try:
            logger.info("Loading model...")
            # Initialize model in session state if not already loaded
            if st.session_state.llm_model is None:
                st.session_state.llm_model = Llama(
                    model_path=self.model_path,
                    n_gpu_layers=-1,  # Use all GPU layers
                    n_ctx=2048,      # Context size
                    verbose=True     # Enable verbose logging
                )
            logger.info("Model loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        if st.session_state.llm_model is None:
            logger.error("Model not initialized")
            return None

        try:
            logger.info("Generating response...")
            response = st.session_state.llm_model.create_chat_completion(
                messages=messages,
                max_tokens=kwargs.get('max_tokens', 100),
                temperature=kwargs.get('temperature', 0.7),
                top_p=kwargs.get('top_p', 0.95)
            )
            
            if response and 'choices' in response and response['choices']:
                return response['choices'][0]['message']['content'].strip()
            return None
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None

    def get_model_info(self) -> Dict[str, str]:
        return {
            "backend": "llama.cpp",
            "model_path": self.model_path,
            "status": "loaded" if st.session_state.get("llm_model") is not None else "not loaded"
        }

class OllamaBackend(LLMBackend):
    def __init__(self, model_name: str = ""):
        self.model_name = model_name
        logger.info(f"Initializing Ollama backend with model: {model_name}")

    def initialize_model(self) -> bool:
        try:
            # Test connection to Ollama
            response = requests.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                # Check if selected model exists
                models = [model['name'] for model in response.json().get('models', [])]
                if self.model_name in models:
                    logger.info("Ollama model verified successfully")
                    return True
                else:
                    logger.error(f"Model {self.model_name} not found in Ollama")
                    return False
            return False
        except requests.RequestException as e:
            logger.error(f"Error connecting to Ollama: {e}")
            return False

    def generate_response(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        if not self.model_name:
            logger.error("No model selected")
            return None

        try:
            logger.info("Generating response with Ollama...")
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "options": {
                        "temperature": kwargs.get('temperature', 0.7),
                        "top_p": kwargs.get('top_p', 0.95)
                    },
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                return response.json()['message']['content'].strip()
            return None
        except Exception as e:
            logger.error(f"Error generating response with Ollama: {e}")
            return None

    def get_model_info(self) -> Dict[str, str]:
        return {
            "backend": "ollama",
            "model": self.model_name,
            "status": "connected" if self.initialize_model() else "not connected"
        }

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
        st.title("🤖 LLM Test Interface")
        
        # Sidebar for model information and controls
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

        # Chat interface
        st.subheader("Chat")
        
        # Display chat messages
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        # Chat input
        model_ready = isinstance(self.backend, (OllamaBackend, LlamaCppBackend)) and self.backend.initialize_model()
        if not model_ready:
            st.error("Failed to initialize model. Please check logs.")
            return
            
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

        # Clear chat button
        if st.sidebar.button("Clear Chat", key="clear_chat_btn"):
            st.session_state.messages = []
            st.rerun()

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
    
    # Initialize chat interface
    chat_interface = ChatInterface(llm_backend)
    chat_interface.render()

if __name__ == "__main__":
    main()

