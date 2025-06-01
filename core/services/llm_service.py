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
        # Initialize stop flag for interrupting generation
        if "llm_stop_generation" not in st.session_state:
            st.session_state.llm_stop_generation = False

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

    def generate_response_streaming(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Generate response with streaming and interruption support."""
        if st.session_state.llm_model is None:
            logger.error("Model not initialized")
            return None

        # Reset stop flag
        st.session_state.llm_stop_generation = False
        
        try:
            logger.info("Generating streaming response...")
            full_response = ""
            
            # Get callback function for UI updates (if provided)
            update_callback = kwargs.get('update_callback')
            
            # Create streaming completion
            stream = st.session_state.llm_model.create_chat_completion(
                messages=messages,
                max_tokens=kwargs.get('max_tokens', 2000),
                temperature=kwargs.get('temperature', 0.1),
                top_p=kwargs.get('top_p', 0.95),
                stream=True
            )
            
            for chunk in stream:
                # Check if generation should be stopped
                if st.session_state.get("llm_stop_generation", False):
                    logger.info("Generation interrupted by user")
                    return full_response.strip() if full_response else None
                    
                if chunk and 'choices' in chunk and chunk['choices']:
                    delta = chunk['choices'][0].get('delta', {})
                    if 'content' in delta:
                        content = delta['content']
                        full_response += content
                        
                        # Call UI update callback if provided
                        if update_callback:
                            filtered_response = self._filter_thinking_process(full_response)
                            update_callback(filtered_response, is_complete=False)
                        
                        # Small delay to allow UI updates
                        import time
                        time.sleep(0.05)
            
            # Final callback with complete response
            if update_callback and full_response:
                filtered_response = self._filter_thinking_process(full_response)
                update_callback(filtered_response, is_complete=True)
            
            return full_response.strip() if full_response else None
            
        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            return None

    def _filter_thinking_process(self, text: str) -> str:
        """Remove thinking process tags from the response text."""
        import re
        # Remove <think>...</think> tags and their content
        filtered = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        return filtered.strip()

    def stop_generation(self):
        """Stop the current generation."""
        st.session_state.llm_stop_generation = True
        logger.info("Generation stop requested")

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

    def generate_response_streaming(self, messages: List[Dict[str, str]], **kwargs) -> Optional[str]:
        """Generate response with streaming support for Ollama."""
        if not self.model_name:
            logger.error("No model selected")
            return None

        try:
            logger.info("Generating streaming response with Ollama...")
            
            # Get callback function for UI updates (if provided)
            update_callback = kwargs.get('update_callback')
            
            # Make streaming request to Ollama
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": self.model_name,
                    "messages": messages,
                    "options": {
                        "temperature": kwargs.get('temperature', 0.7),
                        "top_p": kwargs.get('top_p', 0.95)
                    },
                    "stream": True  # Enable streaming
                },
                stream=True  # Enable streaming response
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code}")
                return None
            
            full_response = ""
            
            # Process streaming response line by line
            for line in response.iter_lines():
                if line:
                    try:
                        # Parse JSON from each line
                        chunk_data = json.loads(line.decode('utf-8'))
                        
                        # Extract content from the message
                        if 'message' in chunk_data and 'content' in chunk_data['message']:
                            content = chunk_data['message']['content']
                            full_response += content
                            
                            # Call UI update callback if provided
                            if update_callback:
                                update_callback(full_response, is_complete=False)
                            
                            # Small delay to allow UI updates
                            import time
                            time.sleep(0.02)  # Smaller delay for Ollama as it's usually faster
                        
                        # Check if this is the final chunk
                        if chunk_data.get('done', False):
                            break
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse JSON chunk: {e}")
                        continue
            
            # Final callback with complete response
            if update_callback and full_response:
                update_callback(full_response, is_complete=True)
            
            return full_response.strip() if full_response else None
            
        except Exception as e:
            logger.error(f"Error in Ollama streaming generation: {e}")
            return None

    def get_model_info(self) -> Dict[str, str]:
        return {
            "backend": "ollama",
            "model": self.model_name,
            "status": "connected" if self.initialize_model() else "not connected"
        }
