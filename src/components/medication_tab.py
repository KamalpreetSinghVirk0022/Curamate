# components/medication_tab.py
import streamlit as st
from services.medication_service import parse_medication_schedule, create_medication_calendar

def show_medication_tab():
    st.title("💊 Smart Medication Schedule")
    st.markdown("Tell us what your doctor said, and we'll create your schedule.")

    # Use session state to store the AI's preview
    if 'parsed_meds' not in st.session_state:
        st.session_state.parsed_meds = None

    # Check for a success flag to show message and download button
    if st.session_state.get("med_save_success", False):
        st.balloons()
        st.success("All medications saved successfully!")
        
        # --- ADD THE DOWNLOAD BUTTON ON SUCCESS ---
        saved_meds = st.session_state.get("last_saved_meds", [])
        if saved_meds:
            ics_content = create_medication_calendar(saved_meds)
            st.download_button(
                label="📥 Add Schedule to Your Calendar",
                data=ics_content,
                file_name=f"Medication_Schedule.ics",
                mime="text/calendar"
            )
        
        # Reset the flags
        st.session_state.med_save_success = False
        st.session_state.parsed_meds = None
        st.session_state.last_saved_meds = None # Clear saved meds

    # --- Input Form ---
    with st.form("med_input_form"):
        med_instructions = st.text_area(
            "Doctor's Instructions",
            placeholder="e.g., Take Amoxicillin 500mg three times a day for 7 days, and continue Metformin after dinner."
        )
        submitted = st.form_submit_button("Generate Schedule")

    if submitted and med_instructions:
        with st.spinner("AI Pharmacist is analyzing instructions..."):
            # Save the parsed meds to session state
            st.session_state.parsed_meds = parse_medication_schedule(med_instructions)
            
            if not st.session_state.parsed_meds:
                st.error("Could not understand those instructions. Please try again.")
                
            # Rerun to exit the form and show the preview
            st.rerun()

    # --- Show the preview if it exists in session state ---
    if st.session_state.parsed_meds:
        st.success(f"Found {len(st.session_state.parsed_meds)} medication(s)! Please confirm.")
        
        # Show preview
        for med in st.session_state.parsed_meds:
            with st.expander(f"💊 {med.get('name')} ({med.get('dosage')})", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Frequency:** {med.get('frequency')}")
                    st.write(f"**Alert Times:** {', '.join(med.get('alert_times', []))}")
                with col2:
                    st.write(f"**End Date:** {med.get('end_date') or 'Ongoing'}")
                    st.write(f"**Notes:** {med.get('notes') or 'None'}")
        
        # --- Confirmation Buttons ---
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Confirm & Save Schedule", type="primary", use_container_width=True):
                save_count = 0
                for med in st.session_state.parsed_meds:
                    success, error_or_data = st.session_state.auth_service.save_medication(
                        st.session_state.user['id'], 
                        med
                    )
                    if success:
                        save_count += 1
                    else:
                        st.error(f"Failed to save {med.get('name')}: {error_or_data}")
                
                if save_count == len(st.session_state.parsed_meds):
                    # Set success flag
                    st.session_state.med_save_success = True
                    # Store meds for the download button
                    st.session_state.last_saved_meds = st.session_state.parsed_meds
                    st.session_state.parsed_meds = None # Clear the preview
                    st.rerun()
                else:
                    st.error(f"Only saved {save_count}/{len(st.session_state.parsed_meds)} medications.")

        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.parsed_meds = None
                st.rerun()
                
    st.markdown("---")
    st.subheader("Your Active Medications")
    show_active_medications()


def show_active_medications():
    if 'auth_service' not in st.session_state:
        st.info("Loading...")
        return
        
    success, result = st.session_state.auth_service.get_user_medications(st.session_state.user['id'])
    
    if not success:
        st.error(f"Error loading medications: {result}")
        return

    if result:
        for med in result:
            with st.container():
                st.markdown(
                    f"""
                    <div style="padding: 1rem; background-color: #1F2937; border-radius: 10px; margin-bottom: 10px; border: 1px solid #374151;">
                        <h4 style="margin:0; color: #64B5F6;">{med['name']} <span style="font-size:0.8em; color:#9CA3AF;">({med['dosage'] or 'N/A'})</span></h4>
                        <p style="margin: 5px 0 0 0; color: #D1D5DB;">⏰ {', '.join(med['alert_times'])}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
    else:
        st.info("No active medications found.")






































# # components/medication_tab.py
# import streamlit as st
# from services.medication_service import parse_medication_schedule

# def show_medication_tab():
#     st.title("💊 Smart Medication Schedule")
#     st.markdown("Tell us what your doctor said, and we'll create your schedule.")

#     # --- NEW: Use session state to store the AI's preview ---
#     if 'parsed_meds' not in st.session_state:
#         st.session_state.parsed_meds = None

#     # --- NEW: Check for a success flag ---
#     if st.session_state.get("med_save_success", False):
#         st.balloons()
#         st.success("All medications saved successfully!")
#         # Reset the flags
#         st.session_state.med_save_success = False
#         st.session_state.parsed_meds = None

#     # --- Input Form ---
#     with st.form("med_input_form"):
#         med_instructions = st.text_area(
#             "Doctor's Instructions",
#             placeholder="e.g., Take Amoxicillin 500mg three times a day for 7 days, and continue Metformin after dinner."
#         )
#         submitted = st.form_submit_button("Generate Schedule")

#     if submitted and med_instructions:
#         with st.spinner("AI Pharmacist is analyzing instructions..."):
#             # Save the parsed meds to session state
#             st.session_state.parsed_meds = parse_medication_schedule(med_instructions)
            
#             if not st.session_state.parsed_meds:
#                 st.error("Could not understand those instructions. Please try again.")
                
#             # --- FIX: We must rerun here to exit the form ---
#             # This is safe because we haven't saved anything yet
#             st.rerun()

#     # --- NEW: Show the preview if it exists in session state ---
#     if st.session_state.parsed_meds:
#         st.success(f"Found {len(st.session_state.parsed_meds)} medication(s)! Please confirm.")
        
#         # Show preview
#         for med in st.session_state.parsed_meds:
#             with st.expander(f"💊 {med.get('name')} ({med.get('dosage')})", expanded=True):
#                 col1, col2 = st.columns(2)
#                 with col1:
#                     st.write(f"**Frequency:** {med.get('frequency')}")
#                     st.write(f"**Alert Times:** {', '.join(med.get('alert_times', []))}")
#                 with col2:
#                     st.write(f"**End Date:** {med.get('end_date') or 'Ongoing'}")
#                     st.write(f"**Notes:** {med.get('notes') or 'None'}")
        
#         # --- NEW: Confirmation Buttons ---
#         col1, col2 = st.columns(2)
#         with col1:
#             if st.button("✅ Confirm & Save Schedule", type="primary", use_container_width=True):
#                 save_count = 0
#                 for med in st.session_state.parsed_meds:
#                     success, error_or_data = st.session_state.auth_service.save_medication(
#                         st.session_state.user['id'], 
#                         med
#                     )
#                     if success:
#                         save_count += 1
#                     else:
#                         st.error(f"Failed to save {med.get('name')}: {error_or_data}")
                
#                 if save_count == len(st.session_state.parsed_meds):
#                     # --- FIX: Set success flag and rerun ---
#                     st.session_state.med_save_success = True
#                     st.session_state.parsed_meds = None # Clear the preview
#                     st.rerun()
#                 else:
#                     st.error(f"Only saved {save_count}/{len(st.session_state.parsed_meds)} medications.")

#         with col2:
#             if st.button("Cancel", use_container_width=True):
#                 st.session_state.parsed_meds = None
#                 st.rerun()
                
#     st.markdown("---")
#     st.subheader("Your Active Medications")
#     show_active_medications()


# def show_active_medications():
#     if 'auth_service' not in st.session_state:
#         st.info("Loading...")
#         return
        
#     success, result = st.session_state.auth_service.get_user_medications(st.session_state.user['id'])
    
#     if not success:
#         st.error(f"Error loading medications: {result}")
#         return

#     if result:
#         for med in result:
#             with st.container():
#                 st.markdown(
#                     f"""
#                     <div style="padding: 1rem; background-color: #1F2937; border-radius: 10px; margin-bottom: 10px; border: 1px solid #374151;">
#                         <h4 style="margin:0; color: #64B5F6;">{med['name']} <span style="font-size:0.8em; color:#9CA3AF;">({med['dosage'] or 'N/A'})</span></h4>
#                         <p style="margin: 5px 0 0 0; color: #D1D5DB;">⏰ {', '.join(med['alert_times'])}</p>
#                     </div>
#                     """, 
#                     unsafe_allow_html=True
#                 )
#     else:
#         st.info("No active medications found.")






























# # components/medication_tab.py

# import streamlit as st
# from services.medication_service import parse_medication_schedule

# def show_medication_tab():
#     st.title("💊 Smart Medication Schedule")
#     st.markdown("Tell us what your doctor said, and we'll create your schedule.")

#     with st.form("med_input_form"):
#         med_instructions = st.text_area(
#             "Doctor's Instructions",
#             placeholder="e.g., Take Amoxicillin 500mg three times a day for 7 days, and continue Metformin after dinner."
#         )
#         submitted = st.form_submit_button("Generate Schedule")

#     if submitted and med_instructions:
#         with st.spinner("AI Pharmacist is analyzing instructions..."):
#             parsed_meds = parse_medication_schedule(med_instructions)
            
#             if parsed_meds:
#                 st.success(f"Found {len(parsed_meds)} medication(s)!")
                
#                 # Show preview and allow saving
#                 for i, med in enumerate(parsed_meds):
#                     # Use a custom key for each expander
#                     with st.expander(f"💊 {med.get('name')} ({med.get('dosage')})", expanded=True):
#                         col1, col2 = st.columns(2)
#                         with col1:
#                             st.write(f"**Frequency:** {med.get('frequency')}")
#                             st.write(f"**Alert Times:** {', '.join(med.get('alert_times', []))}")
#                         with col2:
#                             st.write(f"**End Date:** {med.get('end_date') or 'Ongoing'}")
#                             st.write(f"**Notes:** {med.get('notes') or 'None'}")
                
#                 if st.button("✅ Confirm & Save Schedule", type="primary"):
#                     save_count = 0
#                     for med in parsed_meds:
#                         success, _ = st.session_state.auth_service.save_medication(
#                             st.session_state.user['id'], 
#                             med
#                         )
#                         if success:
#                             save_count += 1
                    
#                     if save_count == len(parsed_meds):
#                         st.balloons()
#                         st.success("All medications saved successfully!")
#                         st.rerun()
#                     else:
#                         st.error(f"Only saved {save_count}/{len(parsed_meds)} medications. Please try again.")
#             else:
#                 st.error("Could not understand those instructions. Please try again.")

#     st.markdown("---")
#     st.subheader("Your Active Medications")
#     show_active_medications()

# def show_active_medications():
#     # Check for auth_service, which might not be init on first run
#     if 'auth_service' not in st.session_state:
#         st.info("Loading...")
#         return
        
#     success, meds = st.session_state.auth_service.get_user_medications(st.session_state.user['id'])
#     if success and meds:
#         for med in meds:
#             with st.container():
#                 st.markdown(
#                     f"""
#                     <div style="padding: 1rem; background-color: #1F2937; border-radius: 10px; margin-bottom: 10px; border: 1px solid #374151;">
#                         <h4 style="margin:0; color: #64B5F6;">{med['name']} <span style="font-size:0.8em; color:#9CA3AF;">({med['dosage'] or 'N/A'})</span></h4>
#                         <p style="margin: 5px 0 0 0; color: #D1D5DB;">⏰ {', '.join(med['alert_times'])}</p>
#                     </div>
#                     """, 
#                     unsafe_allow_html=True
#                 )
#     else:
#         st.info("No active medications found.")