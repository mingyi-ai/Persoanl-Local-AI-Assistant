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
        st.dataframe(status_df[['timestamp', 'status', 'source_text']], hide_index=True)
    else:
        st.caption("No status history recorded.")
