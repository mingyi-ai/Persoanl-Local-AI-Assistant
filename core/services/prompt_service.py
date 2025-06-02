import logging
from typing import Optional, List
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain_community.llms import LlamaCpp as LangChainLlama
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

from .llm_service import LLMBackend, LlamaCppBackend, OllamaBackend
from ..database.schemas import JobPostingBase

logger = logging.getLogger(__name__)

# Import form classes to get field definitions
try:
    from ..ui.forms import JobPostingForm, ApplicationForm, ApplicationStatusForm
except ImportError:
    # Fallback if forms aren't available
    JobPostingForm = None
    ApplicationForm = None
    ApplicationStatusForm = None

# Create a specialized schema for AI parsing without description field
class ParsedJobPostingData(BaseModel):
    """Parsed job posting data for AI analysis - excludes description field."""
    title: str
    company: str
    location: Optional[str] = None
    type: Optional[str] = None
    seniority: Optional[str] = None
    source_url: Optional[str] = None
    date_posted: Optional[str] = None
    tags: Optional[str] = None
    skills: Optional[str] = None
    industry: Optional[str] = None
    
    class Config:
        # Field descriptions for AI prompt generation
        json_schema_extra = {
            "properties": {
                "title": {"description": "The exact job title from the posting"},
                "company": {"description": "The company name"},
                "location": {"description": "The job location, including if remote"},
                "source_url": {"description": "URL where the job posting was found"},
                "type": {"description": "Job type (Full-time, Part-time, Contract, etc.)"},
                "seniority": {"description": "Seniority level (Entry, Mid-Senior, Director, etc.)"},
                "tags": {"description": "Comma-separated tags for categorization"},
                "skills": {"description": "Comma-separated technical skills and requirements"},
                "industry": {"description": "Industry or sector"},
                "date_posted": {"description": "Date when job was posted (YYYY-MM-DD format)"}
            }
        }

class PromptService:
    """Service for AI-powered job description analysis using LangChain."""
    
    def __init__(self, base_backend: LLMBackend):
        self.base_backend = base_backend
        self.langchain_llm = None
        self._initialize_langchain()

    def _initialize_langchain(self):
        """Initialize LangChain wrapper for the base backend."""
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
        
        # Map form fields to descriptions (excluding description field to avoid duplication)
        field_descriptions = {
            "title": "Extract the exact job title as written",
            "company": "Extract company name if present",
            "location": "Include full location details, note if remote/hybrid/on-site",
            "source_url": "Extract any URLs mentioned in the posting",
            "type": "Job type: Full-time, Part-time, Contract, Temporary, Internship, Freelance, Other",
            "seniority": "Seniority level: Entry, Mid-Senior, Director, Executive, Intern, Other",
            "tags": "Generate relevant tags for categorization (comma-separated)",
            "skills": "Extract all technical skills, tools, and technologies mentioned (comma-separated)",
            "industry": "Identify the industry or business sector",
            "date_posted": "Extract posting date if mentioned (use YYYY-MM-DD format)"
        }
        
        # Generate field instructions (excluding description field)
        field_instructions = []
        required_fields = ["title", "company"]  # Removed description from required fields since it won't be in the AI response
        
        for field in job_fields:
            if field in field_descriptions:  # Only include fields we want the AI to extract
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
        10. DO NOT include the original job description text in the response - only extract structured data

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
        - source_url: Any URLs mentioned
        - type: Employment type (Full-time, Part-time, Contract, etc.)
        - seniority: Seniority level (Entry, Mid-Senior, Director, etc.)
        - tags: Relevant tags (comma-separated)
        - skills: Technical skills (comma-separated)
        - industry: Industry sector
        - date_posted: Posting date (YYYY-MM-DD)

        IMPORTANT: Do not include the original job description text in the response.

        Job Description:
        {description}

        {format_instructions}

        /no_think
        """

    def analyze_job_description(self, description: str, **kwargs) -> Optional[ParsedJobPostingData]:
        """
        Analyze job description and return structured data.
        
        Args:
            description: Job description text
            **kwargs: Additional parameters including:
                - stream: Enable streaming response (default: False)
                - response_container: Streamlit container for live updates
        """
        if not self.langchain_llm:
            logger.error("LangChain LLM not initialized")
            return None

        parser = PydanticOutputParser(pydantic_object=ParsedJobPostingData)
        
        # Generate dynamic prompt based on form fields
        template = self._generate_analysis_prompt()
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["description"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        try:
            # Check if streaming is requested and backend supports it
            use_streaming = kwargs.get('stream', False)
            
            if use_streaming and hasattr(self.base_backend, 'generate_response_streaming'):
                # Delegate to streaming method if callback is provided
                update_callback = kwargs.get('update_callback')
                return self.analyze_job_description_streaming(
                    description, 
                    update_callback=update_callback, 
                    **kwargs
                )
            else:
                # Use the standard LangChain approach
                chain = prompt | self.langchain_llm
                result = chain.invoke({"description": description})
            
            # Handle None result from streaming (cancelled or failed)
            if result is None:
                logger.warning("Analysis result is None (possibly cancelled or failed)")
                return None
            
            # Parse the result using the helper method
            return self._parse_response(result, parser)
        except Exception as e:
            logger.error(f"Error analyzing job description: {e}")
            return None

    def analyze_job_description_streaming(self, description: str, update_callback: Optional[callable] = None, **kwargs) -> Optional[ParsedJobPostingData]:
        """
        Analyze job description with streaming support using callback pattern.
        
        Args:
            description: Job description text
            update_callback: Function to call with streaming updates (content, is_complete)
            **kwargs: Additional parameters
        """
        if not self.base_backend:
            logger.error("LLM backend not initialized")
            return None

        # Check if backend supports streaming
        if not hasattr(self.base_backend, 'generate_response_streaming'):
            logger.warning("Backend doesn't support streaming, falling back to regular generation")
            return self.analyze_job_description(description, **kwargs)

        parser = PydanticOutputParser(pydantic_object=ParsedJobPostingData)
        
        # Generate dynamic prompt based on form fields
        template = self._generate_analysis_prompt()
        
        prompt = PromptTemplate(
            template=template,
            input_variables=["description"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        formatted_prompt = prompt.format(description=description)
        messages = [{"role": "user", "content": formatted_prompt}]
        
        try:
            # Generate streaming response with callback
            result = self.base_backend.generate_response_streaming(
                messages=messages,
                update_callback=update_callback,
                max_tokens=kwargs.get('max_tokens', 2000),
                temperature=kwargs.get('temperature', 0.1),
                top_p=kwargs.get('top_p', 0.95)
            )
            
            if not result:
                logger.warning("No result from streaming generation")
                return None
            
            # Parse the final result
            return self._parse_response(result, parser)
            
        except Exception as e:
            logger.error(f"Error in streaming analysis: {e}")
            return None

    def _parse_response(self, result: str, parser) -> Optional[ParsedJobPostingData]:
        """Parse the response text into a ParsedJobPosting object."""
        try:
            import re
            # Only remove the first thinking tag pair
            cleaned_result = re.sub(r'<think>.*?</think>', '', result, count=1, flags=re.DOTALL)
            
            # Find the outermost JSON object using a more robust pattern
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

            json_content = find_json(cleaned_result)
            if json_content:
                parsed_result = parser.parse(json_content.strip())
                return parsed_result
            else:
                logger.warning("No valid JSON content found in response")
                return None
                
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None
