\
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
# Assuming PyPDF2 is used for PDF parsing. Add to requirements if not already there.
# You might need to install it: pip install pypdf2
import PyPDF2
import requests # Added for direct Ollama API calls
import json # Added for parsing Ollama responses

OLLAMA_BASE_URL = "http://localhost:11434" # Define default base URL, can be overridden

def extract_text_from_pdf(pdf_file_path: str) -> str:
    """Extracts text from a PDF file."""
    try:
        with open(pdf_file_path, 'rb') as pdf_file:
            reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page_num in range(len(reader.pages)):
                text += reader.pages[page_num].extract_text() or ""
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_file_path}: {e}")
        return ""

def score_resume_job_description(llm: Ollama, resume_text: str, job_description: str) -> tuple[float | None, str | None, str | None]: # MODIFIED return type
    """Scores how well a resume matches a job description using LangChain and Ollama.
    Returns score, explanation, and raw AI response.
    """
    prompt_template = PromptTemplate(
        input_variables=["resume", "job_description"],
        template=(
            "Analyze the following resume and job description. "
            "Provide a score from 0 to 100 indicating how well the resume matches the job requirements. "
            "Also, provide a brief explanation for your score, highlighting key strengths and weaknesses of the resume in relation to the job description.\n\n"
            "Resume:\n{resume}\n\n"
            "Job Description:\n{job_description}\n\n"
            "Score (0-100): "
            "Explanation: "
        )
    )
    chain = LLMChain(llm=llm, prompt=prompt_template)
    raw_response_text = None # ADDED
    try:
        response = chain.invoke({"resume": resume_text, "job_description": job_description})
        raw_response_text = response.get('text', '') # ADDED: Get raw text
        print(f"DEBUG: Raw Ollama response (score_resume_job_description):\n{raw_response_text}") # ADDED: Print raw response

        # The output parsing here is highly dependent on the LLM's response format.
        # This is a basic attempt and might need significant refinement.
        text_response = raw_response_text.strip()
        
        # Try to parse score and explanation
        score_line = text_response.split('\n')[0]
        explanation_part = "".join(text_response.split('\n')[1:]).replace("Explanation:", "").strip()

        # Extract score (this is very brittle)
        score = None
        import re
        score_match = re.search(r"(\d+)", score_line)
        if score_match:
            score = float(score_match.group(1))
            if not (0 <= score <= 100):
                score = None # Invalid score range

        return score, explanation_part if explanation_part else "No explanation provided by AI.", raw_response_text # MODIFIED return

    except Exception as e:
        print(f"Error scoring resume: {e}")
        return None, f"Error during AI scoring: {e}", raw_response_text # MODIFIED return

def generate_cover_letter(llm: Ollama, resume_text: str, job_description: str, company_name: str, job_title: str) -> tuple[str | None, str | None]: # MODIFIED return type
    """Generates a personalized cover letter using LangChain and Ollama.
    Returns cover letter text and raw AI response.
    """
    prompt_template = PromptTemplate(
        input_variables=["resume", "job_description", "company_name", "job_title"],
        template=(
            "Based on the following resume and job description, write a personalized and compelling cover letter. "
            "The applicant is applying for the {job_title} position at {company_name}. "
            "The cover letter should highlight the most relevant skills and experiences from the resume that match the job requirements. "
            "It should be professional, concise, and enthusiastic.\n\n"
            "Resume:\n{resume}\n\n"
            "Job Description:\n{job_description}\n\n"
            "Cover Letter:"
        )
    )
    chain = LLMChain(llm=llm, prompt=prompt_template)
    raw_response_text = None # ADDED
    try:
        response = chain.invoke({
            "resume": resume_text, 
            "job_description": job_description,
            "company_name": company_name,
            "job_title": job_title
        })
        raw_response_text = response.get('text', '') # ADDED: Get raw text
        print(f"DEBUG: Raw Ollama response (generate_cover_letter):\n{raw_response_text}") # ADDED: Print raw response
        
        parsed_cover_letter = raw_response_text.strip()
        return parsed_cover_letter, raw_response_text # MODIFIED return
    except Exception as e:
        print(f"Error generating cover letter: {e}")
        return f"Error during AI cover letter generation: {e}", raw_response_text # MODIFIED return

def analyze_job_description_with_ollama(job_description_text: str, model_name: str, ollama_base_url: str = OLLAMA_BASE_URL) -> dict:
    """
    Analyzes a job description using a specified Ollama model to extract
    relevant tags and technology stacks.

    Args:
        job_description_text: The text of the job description.
        model_name: The name of the Ollama model to use (e.g., "llama3").
        ollama_base_url: The base URL for the Ollama API.

    Returns:
        A dictionary containing 'tags' (a list of strings) and 
        'tech_stacks' (a list of strings). Returns empty lists if parsing fails.
        Example: {"tags": ["python", "data analysis"], "tech_stacks": ["pandas", "scikit-learn"]}
    """
    api_url = f"{ollama_base_url}/api/generate"
    
    prompt = f"""
Analyze the following job description and extract key information.
Return the information as a valid JSON object with two keys: "tags" and "tech_stacks".
- "tags" should be a list of relevant keywords, skills, and concepts (e.g., "project management", "data analysis", "communication skills").
- "tech_stacks" should be a list of specific technologies, programming languages, frameworks, tools, and methodologies (e.g., "Python", "React", "AWS", "CI/CD", "Agile").

Keep the lists concise and relevant to the job description. If no relevant items are found for a category, provide an empty list.

Job Description:
---
{job_description_text}
---

JSON Output:
"""

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False, # We want the full response for JSON parsing
        "format": "json" # Request JSON output format from Ollama
    }

    try:
        response = requests.post(api_url, json=payload, timeout=120) # Increased timeout
        response.raise_for_status()
        
        response_data = response.json()
        
        # The 'response' field in Ollama's non-streaming JSON output contains the generated text.
        # This text itself should be the JSON string we asked for.
        generated_json_str = response_data.get("response", "{}")
        
        # Parse the JSON string generated by the LLM
        parsed_output = json.loads(generated_json_str)
        
        tags = parsed_output.get("tags", [])
        tech_stacks = parsed_output.get("tech_stacks", [])

        # Basic validation that we got lists
        if not isinstance(tags, list):
            print(f"Warning: 'tags' field was not a list. Received: {tags}")
            tags = []
        if not isinstance(tech_stacks, list):
            print(f"Warning: 'tech_stacks' field was not a list. Received: {tech_stacks}")
            tech_stacks = []
            
        return {"tags": tags, "tech_stacks": tech_stacks}

    except requests.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return {"tags": [], "tech_stacks": []}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response from LLM: {e}")
        print(f"Raw response content from LLM: {generated_json_str if 'generated_json_str' in locals() else 'N/A'}")
        return {"tags": [], "tech_stacks": []}
    except Exception as e:
        print(f"An unexpected error occurred in analyze_job_description_with_ollama: {e}")
        return {"tags": [], "tech_stacks": []}
