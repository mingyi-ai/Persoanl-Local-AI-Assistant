import logging
from typing import Optional, List
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.llms import LlamaCpp as LangChainLlama
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from .LLM_backends import LLMBackend, LlamaCppBackend, OllamaBackend

logger = logging.getLogger(__name__)

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
