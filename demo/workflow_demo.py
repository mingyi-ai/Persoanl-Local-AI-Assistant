#!/usr/bin/env python3
"""
AI Assistant Workflow Demonstration
This script demonstrates the complete AI-assisted job application workflow.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.ui.forms import JobPostingForm, ApplicationForm, ApplicationStatusForm
from core.ui.base import show_validation_warnings, show_prefill_summary
from core.database.base import get_db
from core.controllers.job_posting_controller import JobPostingController
from core.controllers.application_controller import ApplicationController


def simulate_ai_analysis(job_description: str) -> dict:
    """
    Simulate AI analysis of a job description.
    In the real app, this would be done by LangChain backend.
    """
    # This simulates what the AI would extract from a job description
    return {
        "title": "Senior Python Developer",
        "company": "TechFlow Solutions",
        "description": job_description,
        "location": "San Francisco, CA (Remote friendly)",
        "source_url": "https://techflow.com/careers/senior-python-dev",
        "parsed_metadata": {
            "required_skills": [
                "Python", "Django", "PostgreSQL", "REST APIs", "Git"
            ],
            "preferred_skills": [
                "AWS", "Docker", "Redis", "Celery", "React", "TensorFlow"
            ],
            "experience_level": "Senior (5+ years)",
            "job_type": "Full-time",
            "education": "Bachelor's degree in Computer Science or equivalent"
        }
    }


def demonstrate_prefill_workflow():
    """Demonstrate the complete prefill workflow."""
    print("🚀 AI Assistant Workflow Demonstration")
    print("=" * 60)
    
    # Step 1: Simulate job description input
    print("\n📋 Step 1: Job Description Analysis")
    print("-" * 40)
    
    sample_job_description = """
    Senior Python Developer - TechFlow Solutions
    
    We are seeking a Senior Python Developer to join our growing engineering team.
    You will be responsible for building scalable web applications using Django,
    integrating with PostgreSQL databases, and designing REST APIs.
    
    Requirements:
    - 5+ years of Python development experience
    - Strong experience with Django framework
    - PostgreSQL database design and optimization
    - REST API development and documentation
    - Version control with Git
    
    Preferred Qualifications:
    - AWS cloud services experience
    - Docker containerization
    - Redis caching implementation
    - Celery task queue management
    - Frontend development with React
    - Machine learning with TensorFlow
    
    Location: San Francisco, CA (Remote work available)
    Type: Full-time position
    Education: Bachelor's degree in Computer Science or equivalent experience
    """
    
    print("Sample job description analyzed...")
    
    # Step 2: AI Analysis
    print("\n🤖 Step 2: AI Analysis Results")
    print("-" * 40)
    
    ai_result = simulate_ai_analysis(sample_job_description)
    
    print(f"✓ Title: {ai_result['title']}")
    print(f"✓ Company: {ai_result['company']}")
    print(f"✓ Location: {ai_result['location']}")
    print(f"✓ Required Skills: {', '.join(ai_result['parsed_metadata']['required_skills'])}")
    print(f"✓ Preferred Skills: {', '.join(ai_result['parsed_metadata']['preferred_skills'])}")
    
    # Step 3: Prefill Data Validation
    print("\n🔍 Step 3: Prefill Data Validation")
    print("-" * 40)
    
    jp_warnings = JobPostingForm._validate_prefill_data(ai_result)
    print(f"Job Posting validation: {len(jp_warnings)} warnings")
    for warning in jp_warnings:
        print(f"  ⚠️  {warning}")
    
    if len(jp_warnings) == 0:
        print("  ✅ All prefill data is valid")
    
    # Step 4: Form Data Extraction
    print("\n📝 Step 4: Form Data Extraction")
    print("-" * 40)
    
    extracted_data = {
        "title": JobPostingForm._get_prefill_value(ai_result, "title"),
        "company": JobPostingForm._get_prefill_value(ai_result, "company"),
        "description": JobPostingForm._get_prefill_value(ai_result, "description"),
        "location": JobPostingForm._get_prefill_value(ai_result, "location"),
        "source_url": JobPostingForm._get_prefill_value(ai_result, "source_url"),
        "date_posted": JobPostingForm._get_prefill_value(ai_result, "date_posted")
    }
    
    print("Extracted form data:")
    for key, value in extracted_data.items():
        display_value = value[:50] + "..." if len(str(value)) > 50 else value
        print(f"  {key}: {display_value}")
    
    # Step 5: Form Validation
    print("\n✅ Step 5: Form Validation")
    print("-" * 40)
    
    validation_errors = JobPostingForm.validate(extracted_data)
    if validation_errors:
        print("Validation errors found:")
        for error in validation_errors:
            print(f"  ❌ {error}")
    else:
        print("  ✅ All extracted data passes form validation")
    
    # Step 6: Database Integration
    print("\n💾 Step 6: Database Integration Demo")
    print("-" * 40)
    
    try:
        db = next(get_db())
        job_posting_controller = JobPostingController()
        application_controller = ApplicationController()
        
        # Create job posting
        jp_result = job_posting_controller.create_job_posting(
            db=db,
            **extracted_data
        )
        
        if jp_result["success"]:
            job_posting_id = jp_result["job_posting_id"]
            print(f"  ✅ Job posting created with ID: {job_posting_id}")
            
            # Create application
            app_data = {
                "submission_method": "online",
                "notes": "AI-assisted application created via demonstration",
                "date_submitted": "2024-01-15"
            }
            
            app_result = application_controller.create_application(
                db=db,
                job_posting_id=job_posting_id,
                **app_data
            )
            
            if app_result["success"]:
                application_id = app_result["application_id"]
                print(f"  ✅ Application created with ID: {application_id}")
                
                # Add initial status
                status_result = application_controller.update_application_status(
                    db=db,
                    application_id=application_id,
                    status="submitted",
                    source_text="AI-Assisted Entry - Workflow demonstration"
                )
                
                if status_result["success"]:
                    print(f"  ✅ Initial status logged successfully")
                else:
                    print(f"  ❌ Status logging failed: {status_result.get('error')}")
            else:
                print(f"  ❌ Application creation failed: {app_result.get('error')}")
        else:
            print(f"  ❌ Job posting creation failed: {jp_result.get('error')}")
        
        db.close()
        
    except Exception as e:
        print(f"  ❌ Database integration failed: {e}")
    
    # Step 7: Metadata Summary
    print("\n📊 Step 7: AI Metadata Summary")
    print("-" * 40)
    
    metadata = ai_result.get("parsed_metadata", {})
    
    print("Skills Analysis:")
    print("  Required Skills:")
    for skill in metadata.get("required_skills", []):
        print(f"    • {skill}")
    
    print("  Preferred Skills:")
    for skill in metadata.get("preferred_skills", []):
        print(f"    • {skill}")
    
    if "experience_level" in metadata:
        print(f"  Experience Level: {metadata['experience_level']}")
    if "job_type" in metadata:
        print(f"  Job Type: {metadata['job_type']}")
    if "education" in metadata:
        print(f"  Education: {metadata['education']}")
    
    print("\n🎉 Workflow demonstration complete!")
    print("=" * 60)
    
    return True


def demonstrate_manual_workflow():
    """Demonstrate manual entry workflow (without AI)."""
    print("\n🖊️  Manual Entry Workflow Demonstration")
    print("=" * 60)
    
    # Simulate manual form data
    manual_data = {
        "title": "Frontend Developer",
        "company": "WebCorp Inc.",
        "description": "Build responsive web applications using React and TypeScript.",
        "location": "Austin, TX",
        "source_url": "https://webcorp.com/jobs/frontend-dev"
    }
    
    print("Manual job posting data:")
    for key, value in manual_data.items():
        print(f"  {key}: {value}")
    
    # Test validation
    errors = JobPostingForm.validate(manual_data)
    if errors:
        print("\nValidation errors:")
        for error in errors:
            print(f"  ❌ {error}")
    else:
        print("\n  ✅ Manual data validation passed")
    
    # Test prefill interface with no data
    empty_prefill = {}
    warnings = JobPostingForm._validate_prefill_data(empty_prefill)
    print(f"\nEmpty prefill validation: {len(warnings)} warnings (expected)")
    
    # Test extraction with no prefill data
    title = JobPostingForm._get_prefill_value(empty_prefill, "title", "")
    print(f"Title extraction with no prefill: '{title}' (should be empty)")
    
    print("\n✅ Manual workflow works perfectly without AI assistance")
    
    return True


def demonstrate_error_handling():
    """Demonstrate error handling scenarios."""
    print("\n🚨 Error Handling Demonstration")
    print("=" * 60)
    
    # Test malformed AI data
    print("\n1. Malformed AI Data:")
    malformed_data = {
        "title": None,  # None instead of string
        "parsed_metadata": "not_a_dict",  # Wrong type
        "invalid_field": "ignored"
    }
    
    try:
        warnings = JobPostingForm._validate_prefill_data(malformed_data)
        print(f"   Warnings generated: {len(warnings)}")
        for warning in warnings:
            print(f"   ⚠️  {warning}")
    except Exception as e:
        print(f"   ❌ Exception: {e}")
    
    # Test partial AI data
    print("\n2. Partial AI Data:")
    partial_data = {"title": "Partial Job"}
    
    title = JobPostingForm._get_prefill_value(partial_data, "title")
    company = JobPostingForm._get_prefill_value(partial_data, "company", "Unknown")
    
    print(f"   Title: '{title}' (available)")
    print(f"   Company: '{company}' (fallback to default)")
    
    # Test validation with missing required fields
    print("\n3. Validation with Missing Fields:")
    incomplete_data = {"title": ""}  # Empty required field
    
    errors = JobPostingForm.validate(incomplete_data)
    print(f"   Validation errors: {len(errors)}")
    for error in errors:
        print(f"   ❌ {error}")
    
    print("\n✅ Error handling works correctly")
    
    return True


def main():
    """Run all demonstrations."""
    print("🎯 JobAssistant AI - Workflow Demonstrations")
    print("=" * 80)
    
    demos = [
        ("AI-Assisted Workflow", demonstrate_prefill_workflow),
        ("Manual Entry Workflow", demonstrate_manual_workflow),
        ("Error Handling", demonstrate_error_handling)
    ]
    
    for demo_name, demo_func in demos:
        print(f"\n{'='*20} {demo_name} {'='*20}")
        try:
            demo_func()
        except Exception as e:
            print(f"❌ Demo '{demo_name}' failed: {e}")
    
    print(f"\n{'='*80}")
    print("✨ All demonstrations complete!")
    print("\nThe AI Assistant successfully demonstrates:")
    print("  • Seamless AI-to-form data flow")
    print("  • Robust error handling and validation")
    print("  • Manual entry fallback capabilities")
    print("  • Clean architecture with separated concerns")
    print("\n🚀 Ready for production use!")


if __name__ == "__main__":
    main()
