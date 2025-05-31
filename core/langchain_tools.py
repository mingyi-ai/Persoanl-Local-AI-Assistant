import logging
from typing import Optional, List
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.llms import LlamaCpp as LangChainLlama
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from .LLM_backends import LLMBackend, LlamaCppBackend, OllamaBackend

logger = logging.getLogger(__name__)

# Import form classes to get field definitions
try:
    from .ui.forms import JobPostingForm, ApplicationForm, ApplicationStatusForm
except ImportError:
    # Fallback if forms aren't available
    JobPostingForm = None
    ApplicationForm = None
    ApplicationStatusForm = None

# Pydantic models for structured output
class JobRequirements(BaseModel):
    title: str = Field(description="The exact job title from the posting")
    company: str = Field(description="The company name", default="Not specified")
    location: str = Field(description="The job location, including if remote", default="Not specified")
    description: str = Field(description="The full job description text")
    source_url: str = Field(description="URL where the job posting was found", default="")
    type: str = Field(description="Job type (Full-time, Part-time, Contract, etc.)", default="Full-time")
    seniority: str = Field(description="Seniority level (Entry, Mid-Senior, Director, etc.)", default="Mid-Senior")
    tags: str = Field(description="Comma-separated tags for categorization", default="")
    skills: str = Field(description="Comma-separated technical skills and requirements", default="")
    industry: str = Field(description="Industry or sector", default="")
    date_posted: str = Field(description="Date when job was posted (YYYY-MM-DD format)", default="")

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
            self.langchain_llm = OllamaLLM(
                model=self.base_backend.model_name,
                callbacks=[StreamingStdOutCallbackHandler()],
            )

    def _generate_analysis_prompt(self) -> str:
        """Generate a dynamic prompt based on available form fields."""
        if JobPostingForm is None:
            # Fallback prompt if forms aren't available
            return self._get_fallback_prompt()
        
        job_fields = JobPostingForm.EXPECTED_FIELDS
        
        # Map form fields to descriptions
        field_descriptions = {
            "title": "Extract the exact job title as written",
            "company": "Extract company name if present",
            "location": "Include full location details, note if remote/hybrid/on-site",
            "description": "Use the full original job description text",
            "source_url": "Extract any URLs mentioned in the posting",
            "type": "Job type: Full-time, Part-time, Contract, Temporary, Internship, Freelance, Other",
            "seniority": "Seniority level: Entry, Mid-Senior, Director, Executive, Intern, Other",
            "tags": "Generate relevant tags for categorization (comma-separated)",
            "skills": "Extract all technical skills, tools, and technologies mentioned (comma-separated)",
            "industry": "Identify the industry or business sector",
            "date_posted": "Extract posting date if mentioned (use YYYY-MM-DD format)"
        }
        
        # Generate field instructions
        field_instructions = []
        required_fields = ["title", "company", "description"]  # Based on JobPostingForm.validate()
        
        for field in job_fields:
            if field in field_descriptions:
                required_marker = " (REQUIRED)" if field in required_fields else " (Optional)"
                field_instructions.append(f"  - {field}{required_marker}: {field_descriptions[field]}")
        
        prompt = f"""Analyze the following job description and extract key information in a structured JSON format.

        FIELD EXTRACTION GUIDELINES:
        {chr(10).join(field_instructions)}

        EXTRACTION RULES:
        1. Extract information EXACTLY as written in the job posting
        2. Do not make assumptions or add information not in the text
        3. Use "Not specified" for missing optional string fields
        4. Use empty strings "" for missing optional fields
        5. For skills: extract specific technologies, tools, languages (e.g., "Python", "React", "AWS")
        6. For tags: generate 3-5 relevant categorization tags based on the role and industry
        7. For type/seniority: choose the closest match from the available options
        8. Keep extracted text concise but complete
        9. The response must be valid JSON with all fields included

        Job Description:
        {{description}}

        {{format_instructions}}

        /no_think
        """
        return prompt

    def _get_fallback_prompt(self) -> str:
        """Fallback prompt when forms are not available."""
        return """Analyze the following job description and extract key information in a structured format.

        Extract the following fields:
        - title: The exact job title
        - company: Company name
        - location: Job location
        - description: Full job description
        - source_url: Any URLs mentioned
        - type: Employment type (Full-time, Part-time, Contract, etc.)
        - seniority: Seniority level (Entry, Mid-Senior, Director, etc.)
        - tags: Relevant tags (comma-separated)
        - skills: Technical skills (comma-separated)
        - industry: Industry sector
        - date_posted: Posting date (YYYY-MM-DD)

        Job Description:
        {description}

        {format_instructions}

        /no_think
        """

    def analyze_job_description(self, description: str) -> Optional[JobRequirements]:
        """Analyze job description and return structured data"""
        if not self.langchain_llm:
            logger.error("LangChain LLM not initialized")
            return None

        parser = PydanticOutputParser(pydantic_object=JobRequirements)
        
        # Generate dynamic prompt based on form fields
        template = self._generate_analysis_prompt()
        
        prompt = PromptTemplate(
            template=template,
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
