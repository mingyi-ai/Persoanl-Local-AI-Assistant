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
    title: str = Field(description="The exact job title from the posting")
    company: str = Field(description="The company name", default="Not specified")
    location: str = Field(description="The job location, including if remote", default="Not specified")
    required_skills: List[str] = Field(description="List of required technical skills, technologies, and competencies")
    preferred_skills: List[str] = Field(description="List of preferred/nice-to-have skills and qualifications")
    experience_level: str = Field(description="Required years of experience or level (e.g., Entry, Mid, Senior)")
    education: str = Field(description="Required education level and field of study")
    job_type: str = Field(description="Employment type (e.g., Full-time, Contract, Part-time, Remote)")
    compensation: str = Field(description="Salary range and benefits information", default="Not specified")
    responsibilities: List[str] = Field(description="Key job responsibilities and duties", default_factory=list)
    requirements: List[str] = Field(description="General job requirements beyond skills", default_factory=list)
    benefits: List[str] = Field(description="List of benefits and perks", default_factory=list)
    department: str = Field(description="Department or team within the company", default="Not specified")
    level: str = Field(description="Job level or seniority (e.g., Junior, Senior, Lead, Manager)", default="Not specified")

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
            template="""Analyze the following job description and extract key information in a structured format. Follow these guidelines:

            1. Required Fields (must be filled):
              - title: Extract the exact job title
              - required_skills: List all explicitly required technical skills, tools, and technologies
              - preferred_skills: List any skills marked as "preferred", "nice-to-have", or "plus"
              - experience_level: Years of experience or level requirement
              - education: Required education level and field

            2. Additional Fields (use "Not specified" if not found):
              - company: Extract company name if present
              - location: Include full location details, note if remote/hybrid
              - job_type: Specify employment type (Full-time, Contract, etc.)
              - compensation: Extract any salary ranges and compensation details
              - level: Job level/seniority (e.g., Junior, Senior, Lead)
              - department: Department or team name
              
            3. Detailed Sections (leave as empty lists if not found):
              - responsibilities: Key duties and responsibilities
              - requirements: Non-skill requirements (e.g., clearances, certifications)
              - benefits: Company benefits and perks
              
            Job Description:
            {description}
            
            {format_instructions}
            
            Instructions:
            1. Extract information EXACTLY as written in the job posting
            2. Do not make assumptions or add information not in the text
            3. Use "Not specified" for missing optional fields
            4. Use empty lists [] for missing list fields
            5. All skills should be specific (e.g., "Python", "React", not "programming")
            6. Keep lists concise - use key phrases, not full sentences
            7. The response must be valid JSON and include all fields

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
