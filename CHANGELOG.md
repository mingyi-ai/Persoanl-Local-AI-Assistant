# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - Under Development

### Added
- Development status documentation
- Comprehensive testing framework setup

### Changed
- Updated README with development status badges
- Enhanced project documentation structure

## [0.3.0] - 2025-06-02

### Added
- AI prompt optimization for better performance
- Dedicated `ParsedJobPostingData` schema for AI responses
- Enhanced data flow from analyzer to job posting form
- Improved form field help text and user guidance

### Changed
- **BREAKING**: Removed redundant "description" field from AI prompts
- Modified prompt service to exclude original job description from AI processing
- Updated form handling to use original job description directly

### Performance
- Reduced AI processing overhead by eliminating duplicate data
- Improved response times for job description analysis

## [0.2.0] - 2025-06-01

### Added
- Comprehensive LLM streaming functionality
- Support for both LlamaCpp and Ollama backends
- LLM setup UI with backend initialization
- Module organization refactoring

### Changed
- Enhanced streaming UI components
- Improved error handling and user feedback
- Better separation of concerns in codebase

## [0.1.0] - 2025-05-XX

### Added
- Initial project setup
- Basic job application tracking functionality
- SQLite database with SQLAlchemy ORM
- File upload and management system
- Basic AI job description analysis
- Streamlit-based user interface

### Features
- Job posting and application management
- Status tracking and search functionality
- Resume and cover letter storage
- Database backup and reset capabilities

---

## Legend

- 🆕 **Added** - New features
- 🔄 **Changed** - Changes to existing functionality
- 🐛 **Fixed** - Bug fixes
- 🗑️ **Removed** - Removed features
- 🔧 **Technical** - Technical improvements
- ⚡ **Performance** - Performance improvements
- 🔒 **Security** - Security improvements
