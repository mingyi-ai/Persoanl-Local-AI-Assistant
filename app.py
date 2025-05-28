# Build a local job application assistant web app using Streamlit.

# Features:
# - Upload a resume PDF
# - Paste a job description
# - Compute a SHA256 hash of uploaded files, store in a /data/files/ folder with unique filename
# - Store job applications, resumes, cover letters, and metadata in SQLite
# - Use LangChain with Ollama (local LLM) to:
#   - Score how well a resume matches a job description
#   - Generate a personalized cover letter
# - Save each application with:
#   - Resume file path
#   - Cover letter text
#   - Job description
#   - Submission timestamp
#   - AI score and reasoning
# - Web interface should include:
#   - Sidebar resume uploader
#   - Text area to paste job description
#   - Buttons to score, generate cover letter, and save to DB
#   - Section to display AI score, explanation, and cover letter

# Use the following folder structure:
# - app.py (Streamlit app entry)
# - core/file_utils.py (for file hashing/saving)
# - core/job_parser.py (LangChain logic)
# - core/db.py (SQLite helpers)
# - data/files/ (for uploaded files)

# All functions should be robust, self-contained, and work for local, single-user use.
# Assume user is running this locally with access to Ollama and resume/job data.
