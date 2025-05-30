import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from pathlib import Path
import requests
from llama_cpp import Llama
import streamlit as st
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.llms import LlamaCpp as LangChainLlama
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODELS_DIR = Path("core/models")
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

# Pydantic models for structured output
class JobRequirements(BaseModel):
    title: str = Field(description="The job title")
    required_skills: List[str] = Field(description="List of required technical skills")
    preferred_skills: List[str] = Field(description="List of preferred or optional skills")
    experience_level: str = Field(description="Required years of experience or level (e.g., Entry, Mid, Senior)")
    education: str = Field(description="Required education level")
    job_type: str = Field(description="Type of job (e.g., Full-time, Contract, Remote)")

class LangChainBackend:
    """Wrapper for LangChain functionality over existing backends"""
    def __init__(self, base_backend: LLMBackend):
        self.base_backend = base_backend
        self.langchain_llm = None
        self._initialize_langchain()

    def _initialize_langchain(self):
        # Common callback manager for all backends
        callback_manager = CallbackManager([StreamingStdOutCallbackHandler()])
        
        if isinstance(self.base_backend, LlamaCppBackend):
            self.langchain_llm = LangChainLlama(
                model_path=self.base_backend.model_path,
                n_gpu_layers=-1,
                n_ctx=2048,
                callback_manager=callback_manager,
                verbose=True,
            )
        elif isinstance(self.base_backend, OllamaBackend):
            from langchain.llms import Ollama
            self.langchain_llm = Ollama(
                model=self.base_backend.model_name,
                callback_manager=callback_manager,
            )

    def analyze_job_description(self, description: str) -> Optional[JobRequirements]:
        """Analyze job description and return structured data"""
        if not self.langchain_llm:
            logger.error("LangChain LLM not initialized")
            return None

        parser = PydanticOutputParser(pydantic_object=JobRequirements)
        prompt = PromptTemplate(
            template="""Analyze the following job description and extract key information in a structured format. Make sure to include all required fields: title, required_skills, preferred_skills, experience_level, education, and job_type.

            If certain information is not explicitly mentioned in the job description:
            - For experience_level: Use "Not specified" if not mentioned
            - For education: Use "Not specified" if not mentioned
            - For job_type: Use "Not specified" if not mentioned
            
            Job Description:
            {description}
            
            {format_instructions}
            
            Remember to include ALL fields in your response, using "Not specified" for missing information.
            The response must be valid JSON and include all required fields.

            /no_think
            """,
            input_variables=["description"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            # Use the new approach recommended by LangChain
            chain = prompt | self.langchain_llm
            result = chain.invoke({"description": description})
            
            # If result is a string (raw completion), clean and parse it
            if isinstance(result, str):
                import re
                # Only remove the first thinking tag pair
                result = re.sub(r'<think>.*?</think>', '', result, count=1, flags=re.DOTALL)
                
                # Find the outermost JSON object using a more robust pattern
                # This handles nested objects by counting braces
                def find_json(text):
                    stack = []
                    start = -1
                    for i, char in enumerate(text):
                        if char == '{':
                            if not stack:  # First opening brace
                                start = i
                            stack.append(char)
                        elif char == '}':
                            if stack and stack[-1] == '{':
                                stack.pop()
                                if not stack:  # Found matching outer braces
                                    return text[start:i+1]
                    return None

                json_content = find_json(result)
                if json_content:
                    result = json_content
                parsed_result = parser.parse(result.strip())
            else:
                # If result is already structured, convert it to JobRequirements
                parsed_result = JobRequirements(**result)
                
            return parsed_result
        except Exception as e:
            logger.error(f"Error analyzing job description: {e}")
            return None

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
