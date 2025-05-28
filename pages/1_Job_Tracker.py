# Job Tracker Page

import streamlit as st
import pandas as pd
from datetime import datetime, date
from pathlib import Path
from core.db import (add_job_application, get_all_applications, 
                     get_application_by_id, update_job_application, 
                     delete_job_application, get_all_resumes) # Added get_all_resumes

st.set_page_config(layout="wide", page_title="Job Tracker")
st.title("Job Application Tracker")

# --- Session State Initialization (specific to Job Tracker) ---
if 'editing_app_id_tracker' not in st.session_state:
    st.session_state.editing_app_id_tracker = None
if 'show_add_manual_form_tracker' not in st.session_state:
    st.session_state.show_add_manual_form_tracker = False
if 'custom_fields_input_tracker' not in st.session_state: # For manual add form
    st.session_state.custom_fields_input_tracker = {}
if 'clear_new_cf_inputs_manual_add_tracker' not in st.session_state:
    st.session_state.clear_new_cf_inputs_manual_add_tracker = False


# --- Function to refresh applications (from original Tab 2) ---
def refresh_apps_data():
    apps = get_all_applications()
    if apps:
        df_data = []
        for app in apps:
            app_row = {
                "ID": app['id'],
                "Job Title": app['job_title'],
                "Company": app['company'],
                "Resume Path": app.get('resume_file_path', 'N/A'),
                "Job Description": app.get('job_description', 'N/A'),
                "Cover Letter Path": app.get('cover_letter_path', 'N/A'),
                "Submission Date": app['submission_date'],
                "AI Score": app.get('ai_score', 'N/A'),
                "AI Reasoning": app.get('ai_reasoning', 'N/A'),
                "Outcome": app['outcome'],
                "Notes": app.get('notes', 'N/A')
            }
            if isinstance(app.get('custom_fields'), dict):
                for cf_key, cf_value in app['custom_fields'].items():
                    app_row[f"Custom: {cf_key}"] = cf_value
            df_data.append(app_row)
        
        df = pd.DataFrame(df_data)
        base_columns = [
            "ID", "Job Title", "Company", "Resume Path", "Job Description", 
            "Cover Letter Path", "Submission Date", "AI Score", "AI Reasoning", 
            "Outcome", "Notes"
        ]
        custom_field_columns = sorted([col for col in df.columns if col.startswith("Custom: ")])
        all_df_columns = base_columns + custom_field_columns
        df = df.reindex(columns=all_df_columns)

        if 'Submission Date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['Submission Date']):
             df['Submission Date'] = pd.to_datetime(df['Submission Date'])
        return df
    return pd.DataFrame()

applications_df = refresh_apps_data()

# --- Search and Filter (from original Tab 2 sidebar) ---
st.sidebar.header("Filter & Search Applications")
search_term = st.sidebar.text_input("Search by Job Title, Company, or Custom Fields", key="search_apps_tracker")

outcome_options = ["All"] + sorted(list(applications_df["Outcome"].unique())) if not applications_df.empty and "Outcome" in applications_df.columns else ["All", "pending", "interview", "rejected", "offer"]
selected_outcome = st.sidebar.selectbox("Filter by Outcome", options=outcome_options, key="filter_outcome_tracker")

filtered_df = applications_df.copy()
if search_term:
    search_conditions = (
        filtered_df["Job Title"].astype(str).str.contains(search_term, case=False, na=False) |
        filtered_df["Company"].astype(str).str.contains(search_term, case=False, na=False)
    )
    for col in filtered_df.columns:
        if col.startswith("Custom: "):
            search_conditions |= filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)
    filtered_df = filtered_df[search_conditions]

if selected_outcome != "All":
    filtered_df = filtered_df[filtered_df["Outcome"] == selected_outcome]

# --- Display Applications Table (from original Tab 2) ---
if not filtered_df.empty:
    st.info(f"Displaying {len(filtered_df)} of {len(applications_df)} applications.")
    display_columns = ["ID", "Job Title", "Company", "Submission Date", "AI Score", "Outcome"]
    custom_display_columns = [col for col in filtered_df.columns if col.startswith("Custom: ")]
    st.dataframe(filtered_df[display_columns + custom_display_columns], use_container_width=True, hide_index=True)
elif not applications_df.empty and (search_term or selected_outcome != "All"):
    st.warning("No applications match your current filter criteria.")
else:
    st.info("No applications found in the database. Add some manually below or via the AI Assistant page.")

st.divider()

# --- Actions: Edit, Delete (from original Tab 2 col_actions1) ---
st.header("Manage Application")
col_manage1, col_manage2 = st.columns([1,2]) # Adjust column ratio if needed

with col_manage1:
    st.subheader("Select Application")
    if not filtered_df.empty:
        app_ids = filtered_df["ID"].tolist()
        selected_app_id_to_manage = st.selectbox("Select Application ID to Manage", options=app_ids, key="app_id_manage_tracker", index=None, placeholder="Choose an application ID")
    else:
        selected_app_id_to_manage = None
        st.caption("No applications to select for management.")

    if selected_app_id_to_manage:
        if st.button("Delete Application", type="primary", key=f"delete_tracker_{selected_app_id_to_manage}"):
            if delete_job_application(selected_app_id_to_manage):
                st.success(f"Application ID {selected_app_id_to_manage} deleted.")
                st.rerun()
            else:
                st.error(f"Failed to delete application ID {selected_app_id_to_manage}.")

with col_manage2:
    if selected_app_id_to_manage:
        app_details_tuple = get_application_by_id(selected_app_id_to_manage)
        if app_details_tuple:
            app_details = app_details_tuple # It's a dict
            
            st.subheader(f"Edit Application ID: {app_details['id']}")
            with st.form(key=f"edit_form_{app_details['id']}"):
                edit_job_title = st.text_input("Job Title", value=app_details["job_title"], key=f"edit_title_tracker_{app_details['id']}")
                edit_company = st.text_input("Company", value=app_details.get("company", ""), key=f"edit_company_tracker_{app_details['id']}")
                
                current_sub_date = pd.to_datetime(app_details["submission_date"]).date() if app_details["submission_date"] else datetime.now().date()
                edit_submission_date = st.date_input("Submission Date", value=current_sub_date, key=f"edit_sub_date_tracker_{app_details['id']}")

                edit_job_description = st.text_area("Job Description", value=app_details.get("job_description", ""), height=150, key=f"edit_jd_tracker_{app_details['id']}")
                edit_outcome_options = ["pending", "interview", "rejected", "offer", "other"]
                current_outcome_index = edit_outcome_options.index(app_details["outcome"]) if app_details["outcome"] in edit_outcome_options else 0
                edit_outcome = st.selectbox("Outcome", options=edit_outcome_options, index=current_outcome_index, key=f"edit_outcome_tracker_{app_details['id']}")
                edit_notes = st.text_area("Notes", value=app_details.get("notes", ""), height=100, key=f"edit_notes_tracker_{app_details['id']}")
                
                # --- Custom Fields Editing ---
                st.markdown("##### Custom Fields")
                if f"edit_custom_fields_tracker_{app_details['id']}" not in st.session_state:
                    st.session_state[f"edit_custom_fields_tracker_{app_details['id']}"] = app_details.get('custom_fields', {}).copy()
                
                current_custom_fields_edit = st.session_state[f"edit_custom_fields_tracker_{app_details['id']}"]
                
                for cf_key, cf_value in list(current_custom_fields_edit.items()):
                    cols = st.columns([4,4,1])
                    new_key_val = cols[0].text_input(f"Key##edit_{app_details['id']}_{cf_key}", value=cf_key, key=f"edit_cf_key_tracker_{app_details['id']}_{cf_key}")
                    new_val_val = cols[1].text_input(f"Value##edit_{app_details['id']}_{cf_key}", value=cf_value, key=f"edit_cf_val_tracker_{app_details['id']}_{cf_key}")
                    if cols[2].form_submit_button(label="X", help="Remove field"): # Removed key
                        if cf_key in current_custom_fields_edit:
                            del current_custom_fields_edit[cf_key]
                        st.rerun()
                    
                    if new_key_val != cf_key: # Key changed
                        current_custom_fields_edit.pop(cf_key)
                        current_custom_fields_edit[new_key_val] = new_val_val
                        st.rerun()
                    elif new_val_val != cf_value: # Value changed
                        current_custom_fields_edit[cf_key] = new_val_val
                        # st.rerun() # Rerun if immediate reflection is needed

                new_cf_key_edit = st.text_input("New Custom Field Key", key=f"new_cf_key_edit_tracker_{app_details['id']}")
                new_cf_value_edit = st.text_input("New Custom Field Value", key=f"new_cf_value_edit_tracker_{app_details['id']}")
                if st.form_submit_button("Add Custom Field"): # Removed key
                    if new_cf_key_edit and new_cf_key_edit not in current_custom_fields_edit:
                        current_custom_fields_edit[new_cf_key_edit] = new_cf_value_edit
                        st.rerun()
                    elif new_cf_key_edit in current_custom_fields_edit:
                        st.warning(f"Custom field '{new_cf_key_edit}' already exists.")
                    else:
                        st.warning("Custom field key cannot be empty.")
                
                save_changes_button = st.form_submit_button("Save Changes")
                if save_changes_button:
                    updated = update_job_application(
                        application_id=app_details['id'],
                        job_title=edit_job_title,
                        company=edit_company,
                        job_description=edit_job_description,
                        outcome=edit_outcome,
                        notes=edit_notes,
                        resume_id=app_details.get("resume_id"), # Keep existing
                        cover_letter_path=app_details.get("cover_letter_path"), # Keep existing
                        submission_date=datetime.combine(edit_submission_date, datetime.min.time()),
                        custom_fields=current_custom_fields_edit
                    )
                    if updated:
                        st.success(f"Application ID {app_details['id']} updated successfully.")
                        del st.session_state[f"edit_custom_fields_tracker_{app_details['id']}"]
                        st.session_state.editing_app_id_tracker = None 
                        st.rerun()
                    else:
                        st.error(f"Failed to update application ID {app_details['id']}.")
        else:
            st.error(f"Could not retrieve details for Application ID {selected_app_id_to_manage}.")
    else:
        st.caption("Select an application from the dropdown above to view details or edit.")


st.divider()
# --- Manually Add New Application (from original Tab 2 col_actions2) ---
st.header("Manually Add New Application")

if st.button("Show Manual Add Form", key="toggle_manual_add_form_tracker"):
    st.session_state.show_add_manual_form_tracker = not st.session_state.show_add_manual_form_tracker
    if st.session_state.show_add_manual_form_tracker:
        # Initialize/Reset form fields
        st.session_state.manual_title_add_tracker = ""
        st.session_state.manual_company_add_tracker = ""
        st.session_state.manual_sub_date_add_tracker = datetime.now().date()
        st.session_state.manual_jd_add_tracker = ""
        st.session_state.manual_outcome_add_tracker = "pending"
        st.session_state.manual_notes_add_tracker = ""
        st.session_state.manual_resume_link_tracker = 0 
        st.session_state.manual_custom_fields_tracker = {}
        st.session_state.new_manual_cf_key_input_tracker = ""
        st.session_state.new_manual_cf_value_input_tracker = ""
        st.session_state.clear_new_cf_inputs_manual_add_tracker = True


if st.session_state.get("show_add_manual_form_tracker", False):
    manual_outcome_options = ["pending", "interview", "rejected", "offer", "other"]
    available_resumes = get_all_resumes()
    resume_options = {0: "None"}
    for res in available_resumes:
        resume_options[res['id']] = Path(res['file_path']).name
    
    # Ensure session state keys for the form are initialized
    form_keys_defaults = {
        "manual_title_add_tracker": "", "manual_company_add_tracker": "",
        "manual_sub_date_add_tracker": datetime.now().date(), "manual_jd_add_tracker": "",
        "manual_outcome_add_tracker": manual_outcome_options[0], "manual_notes_add_tracker": "",
        "manual_resume_link_tracker": 0, "manual_custom_fields_tracker": {},
        "new_manual_cf_key_input_tracker": "", "new_manual_cf_value_input_tracker": ""
    }
    for key, default in form_keys_defaults.items():
        if key not in st.session_state: st.session_state[key] = default
    
    if st.session_state.get("clear_new_cf_inputs_manual_add_tracker", False):
        st.session_state.new_manual_cf_key_input_tracker = ""
        st.session_state.new_manual_cf_value_input_tracker = ""
        st.session_state.clear_new_cf_inputs_manual_add_tracker = False

    with st.form("manual_add_form_tracker", clear_on_submit=False):
        manual_job_title = st.text_input("Job Title*", key="manual_title_add_tracker")
        manual_company = st.text_input("Company", key="manual_company_add_tracker")
        manual_submission_date = st.date_input("Submission Date", key="manual_sub_date_add_tracker")
        manual_job_description = st.text_area("Job Description", height=100, key="manual_jd_add_tracker")
        
        if st.session_state.manual_outcome_add_tracker not in manual_outcome_options:
            st.session_state.manual_outcome_add_tracker = manual_outcome_options[0]
        current_manual_outcome_index = manual_outcome_options.index(st.session_state.manual_outcome_add_tracker)
        manual_outcome = st.selectbox("Outcome", options=manual_outcome_options, 
                                      index=current_manual_outcome_index, 
                                      key="manual_outcome_add_tracker")
        
        manual_notes = st.text_area("Notes", height=75, key="manual_notes_add_tracker")
        
        # --- Custom Fields for Manual Add ---
        st.markdown("##### Custom Fields")
        current_manual_custom_fields = st.session_state.manual_custom_fields_tracker

        for cf_key, cf_value in list(current_manual_custom_fields.items()):
            cols = st.columns([4,4,1])
            new_key = cols[0].text_input(f"Key##manual_{cf_key}", value=cf_key, key=f"manual_cf_key_input_tracker_{cf_key}")
            new_val = cols[1].text_input(f"Value##manual_{cf_key}", value=cf_value, key=f"manual_cf_val_input_tracker_{cf_key}")
            if cols[2].form_submit_button(label="X", help="Remove field"): # Removed key
                if cf_key in current_manual_custom_fields:
                    del current_manual_custom_fields[cf_key]
                st.rerun()
            
            if new_key != cf_key: # Key changed
                current_manual_custom_fields.pop(cf_key)
                current_manual_custom_fields[new_key] = new_val
                st.rerun()
            elif new_val != cf_value: # Value changed
                current_manual_custom_fields[cf_key] = new_val
                # st.rerun() # Optional for immediate reflection

        cols_add_cf = st.columns([3,3,2]) # Adjusted for button label
        new_cf_key_manual = cols_add_cf[0].text_input("New Custom Field Key", key="new_manual_cf_key_input_tracker")
        new_cf_val_manual = cols_add_cf[1].text_input("New Custom Field Value", key="new_manual_cf_value_input_tracker")
        if cols_add_cf[2].form_submit_button("Add Custom Field"): # Removed key
            if new_cf_key_manual and new_cf_key_manual not in current_manual_custom_fields:
                current_manual_custom_fields[new_cf_key_manual] = new_cf_val_manual
                st.session_state.clear_new_cf_inputs_manual_add_tracker = True
                st.rerun()
            elif new_cf_key_manual in current_manual_custom_fields:
                st.warning(f"Custom field '{new_cf_key_manual}' already exists.")
            else:
                st.warning("Custom field key cannot be empty.")

        # Resume linking
        if st.session_state.manual_resume_link_tracker not in resume_options:
             st.session_state.manual_resume_link_tracker = 0
        current_manual_resume_id_index = list(resume_options.keys()).index(st.session_state.manual_resume_link_tracker)
        
        manual_resume_id_val = st.selectbox(
            "Link Resume (Optional)", 
            options=list(resume_options.keys()), 
            format_func=lambda x: resume_options[x],
            index=current_manual_resume_id_index,
            key="manual_resume_link_tracker"
        )

        submitted_manual = st.form_submit_button("Add Application")
        if submitted_manual:
            if not st.session_state.manual_title_add_tracker:
                st.error("Job Title is required for manual entry.")
            else:
                app_id = add_job_application(
                    job_title=st.session_state.manual_title_add_tracker,
                    company=st.session_state.manual_company_add_tracker,
                    resume_id=st.session_state.manual_resume_link_tracker if st.session_state.manual_resume_link_tracker != 0 else None,
                    job_description=st.session_state.manual_jd_add_tracker,
                    cover_letter_path=None, 
                    ai_score=None, 
                    ai_reasoning=None, 
                    outcome=st.session_state.manual_outcome_add_tracker,
                    notes=st.session_state.manual_notes_add_tracker,
                    submission_date=datetime.combine(st.session_state.manual_sub_date_add_tracker, datetime.min.time()),
                    custom_fields=st.session_state.manual_custom_fields_tracker.copy()
                )
                if app_id:
                    st.success(f"Manually added application for '{st.session_state.manual_title_add_tracker}' with ID: {app_id}")
                    st.session_state.show_add_manual_form_tracker = False 
                    st.rerun()
                else:
                    st.error("Failed to manually add application.")
else:
    st.caption("Click the button above to open the form for adding an application manually.")
