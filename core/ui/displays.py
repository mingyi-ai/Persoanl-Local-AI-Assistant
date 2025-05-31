"""Common UI components for displaying job application data."""
from typing import Dict, List, Any
import pandas as pd
import streamlit as st

def display_applications_table(df: pd.DataFrame, display_columns: List[str]):
    """Display a table of job applications."""
    if not df.empty:
        st.info(f"Displaying {len(df)} application(s).")
        st.dataframe(df[display_columns], use_container_width=True, hide_index=True)
    else:
        st.info("No applications found.")

def display_status_history(status_history: List[Dict[str, Any]]):
    """Display status history in a table."""
    if status_history:
        status_df = pd.DataFrame(status_history)
        # Use the correct column names based on our simplified schema
        display_columns = []
        if 'created_at' in status_df.columns:
            display_columns.append('created_at')
        elif 'timestamp' in status_df.columns:
            display_columns.append('timestamp')
        
        if 'status' in status_df.columns:
            display_columns.append('status')
        
        if 'source_text' in status_df.columns:
            display_columns.append('source_text')
            
        if display_columns:
            st.dataframe(status_df[display_columns], hide_index=True)
        else:
            st.caption("Status history data format not recognized.")
    else:
        st.caption("No status history recorded.")
