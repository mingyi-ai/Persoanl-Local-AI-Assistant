"""Base UI components and utilities."""
from typing import Dict, Any, Optional
import streamlit as st

def show_validation_errors(errors: Dict[str, str]):
    """Display validation errors."""
    if errors:
        error_text = "\n".join([f"• {error}" for error in errors.values()])
        st.error(error_text)
        return True
    return False

def show_operation_result(result: Dict[str, Any], success_message: Optional[str] = None):
    """Display the result of an operation."""
    if result.get("success"):
        st.success(success_message or "Operation completed successfully!")
        return True
    else:
        st.error(f"Operation failed: {result.get('message', 'Unknown error')}")
        return False
