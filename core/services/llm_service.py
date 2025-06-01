
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pathlib import Path
import requests
from llama_cpp import Llama
import streamlit as st
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODELS_DIR = Path("core/models")
DEFAULT_MODEL = "Qwen3-8B-Q4_K_M.gguf"
OLLAMA_BASE_URL = "http://localhost:11434"

class LLMService:
    """Service for managing LLM operations and backends."""
    
    @staticmethod
    def get_ollama_models():
        """Helper function to get available Ollama models."""
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
