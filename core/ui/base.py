"""Base UI components and utilities."""
from typing import Dict, Any, Optional, List
import streamlit as st

def show_validation_errors(errors: Dict[str, str]):
    """Display validation errors."""
    if errors:
        error_text = "\n".join([f"• {error}" for error in errors.values()])
        st.error(error_text)
        return True
    return False

def show_validation_warnings(warnings: Dict[str, str]):
    """Display validation warnings for prefill data."""
    if warnings:
        warning_text = "\n".join([f"• {warning}" for warning in warnings.values()])
        st.warning(f"⚠️ Prefill Data Issues:\n{warning_text}")
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

def show_ai_assistance_indicator(field_name: str, has_ai_data: bool = False):
    """Show a small indicator that a field was AI-assisted."""
    if has_ai_data:
        st.caption(f"🤖 {field_name} was AI-parsed - please review")

def show_prefill_summary(prefill_data: Dict[str, Any], title: str = "AI-Parsed Data Summary"):
    """Display a summary of prefilled data for user review."""
    if not prefill_data:
        return
        
    with st.expander(f"📊 {title}", expanded=False):
        cols = st.columns(2)
        col_idx = 0
        
        for key, value in prefill_data.items():
            if key == "parsed_metadata":
                continue  # Handle metadata separately
                
            with cols[col_idx % 2]:
                if isinstance(value, (list, tuple)):
                    st.write(f"**{key.replace('_', ' ').title()}:**")
                    for item in value:
                        st.write(f"• {item}")
                elif value:
                    st.write(f"**{key.replace('_', ' ').title()}:** {value}")
            col_idx += 1
