# 🎯 JobAssistant - AI-Powered Job Application Tracker

![Development Status](https://img.shields.io/badge/Status-Under%20Development-orange?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

> ⚠️ **Development Notice**: This project is actively under development. Features may change and some functionality is still being refined.

A Streamlit-based application that combines job application management with AI-powered job description analysis. JobAssistant helps you organize your job search while leveraging local AI models for intelligent parsing and insights.

## 🌟 Features

### Core Functionality
- **📋 Job Application Management** - Track job postings and applications with status history
- **🤖 AI Job Description Analysis** - Parse job descriptions and extract structured data using local LLMs
- **📄 File Management** - Upload and manage resumes and cover letters
- **📊 Application Analytics** - Track application status and trends


### AI Capabilities
- **Smart Job Parsing** - Extract job title, company, location, skills, and requirements
- **Skills Analysis** - Identify technical skills and qualifications
- **Form Auto-fill** - Populate job database with AI-parsed data
- **Dual Backend Support** - Choose between LlamaCpp (local GGUF files) or Ollama
- **Prompt Engineering** - Customizable AI prompts for better results 

### Data Management
- **SQLite Database** - Reliable local data storage with SQLAlchemy ORM
- **Database Archiving** - Backup and reset functionality


## 🚀 Quick Start

- **So far only tested on Apple Silicon Macs.**

### Installation

1. **Clone the repository:** download the code to your local machine.

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up AI Backend** (choose one option):

   **Option A: Local GGUF Models**
   - Download a GGUF model file (e.g., Qwen3-8B-Q4_K_M.gguf)
   - Place it in the `core/models/` directory
   - Recommended: [Qwen3-8B-GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF/resolve/main/Qwen3-8B-Q4_K_M.gguf)
   - Offline usage, custom models, more control with LlamaCpp.


   **Option B: Ollama**
   - Install [Ollama](https://ollama.com/docs/installation) and set up the Ollama service.
   -    ```bash
         # Download a compatible model (e.g., Qwen3)
         ollama pull qwen3:8b
         
         # Start Ollama service
         ollama serve
         ```
   - Requires Ollama service running and less control over models.

4. **Launch the application:**
   ```bash
   streamlit run app.py
   ```

## 🛠️ Development

### Architecture Overview

**Backend Architecture:**
- **MVC Pattern:** Controllers, Services, and Database layers
- **SQLAlchemy ORM:** Type-safe database operations
- **Pydantic Schemas:** Data validation and serialization
- **Dependency Injection:** Clean separation of concerns

**AI Integration:**
- **Abstract Backend Interface:** Pluggable AI backends
- **LangChain Integration:** LLM abstraction and tools

**Frontend Architecture:**
- **Vibe Coding** - Let AI do it.


## 📊 Project Status

### Current Status: **Under Development** 🚧

**Stable Features:**
- ✅ Job posting and application management
- ✅ SQLite database with full CRUD operations
- ✅ AI job description analysis (LlamaCpp & Ollama)
- ✅ Real-time streaming AI responses
- ✅ File upload and management
- ✅ Application status tracking
- ✅ Search and filtering
- ✅ Database backup and reset

**Knowon Issues:**
- ❗ Whenever start the app, if you directly switch to the second tab and click on a button, it will jump back to the first tab. Later clicks will work as expected. Will look into this session state issue later.

**In Progress:**
- 🔄 Enhanced AI prompt engineering
- 🔄 More AI features such as tailor CV and cover letter
- 🔄 Advanced analytics dashboard
- 🔄 UI improvements

**Planned Features:**
- Integration with job boards (LinkedIn, Indeed)
- Cover letter and resume generation, preferably fine-tune a small model for this
- Other AI capabilities like interview preparation, salary negotiation, etc.


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
