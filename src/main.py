import streamlit as st
import datetime
from auth.session_manager import SessionManager
from components.auth_pages import show_login_page
from components.sidebar import show_sidebar
from components.analysis_form import show_analysis_form
from components.booking_form import show_booking_form
from components.medication_tab import show_medication_tab # <-- ADDED IMPORT
from config.app_config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON
from streamlit_option_menu import option_menu

# --- Page Config (Must be first Streamlit command) ---
st.set_page_config(
    page_title="CuraMate - Health Insights Agent",
    page_icon="🩺",
    layout="wide"
)

# --- CSS Loader Function ---
def load_css(file_name):
    """Loads a local CSS file."""
    try:
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"CSS file '{file_name}' not found. Make sure 'style.css' is in the root directory.")

# --- Original Welcome Screen Function ---
def show_welcome_screen():
    st.markdown(
        f"""
        <div style='text-align: center; padding: 50px;'>
            <h1>{APP_ICON} {APP_NAME}</h1>
            <h3>{APP_DESCRIPTION}</h3>
            <p style='font-size: 1.2em; color: #D1D5DB;'>{APP_TAGLINE}</p>
            <p>Start by creating a new analysis session in the sidebar</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    col1, col2, col3 = st.columns([2, 3, 2])
    with col2:
        if st.button("➕ Create New Analysis Session", use_container_width=True, type="primary"):
            success, session = SessionManager.create_chat_session()
            if success:
                st.session_state.current_session = session
                st.rerun()
            else:
                st.error("Failed to create session")

# --- Updated Chat History (for Dark Theme) ---
def show_chat_history():
    success, messages = st.session_state.auth_service.get_session_messages(
        st.session_state.current_session['id']
    )
    
    if success:
        for msg in messages:
            if msg['role'] == 'user':
                # User message
                st.markdown(f"""
                <div style='padding: 1rem; border-radius: 8px; background-color: #374151; margin-bottom: 1rem; border: 1px solid #4B5563;'>
                    <b>You:</b><br><br>{msg['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                # Assistant message
                st.markdown(f"""
                <div style='padding: 1rem; border-radius: 8px; background-color: #1F2937; border: 1px solid #4B5563; margin-bottom: 1rem;'>
                    <b>CuraMate:</b><br>{msg['content']}
                </div>
                """, unsafe_allow_html=True)

# --- New Appointment List Function (Moved from Sidebar) ---
def show_appointment_list():
    """Fetches and displays upcoming and previous appointments."""
    
    if not (st.session_state.user and 'id' in st.session_state.user):
        st.info("Log in to see appointments.")
        return

    success, appointments = SessionManager.get_user_appointments()
    
    if not success:
        st.error("Failed to load appointments.")
        return

    if not appointments:
        st.info("You have no appointments scheduled.")
        return

    upcoming_appts = []
    previous_appts = []
    today = datetime.date.today()

    for appt in appointments:
        try:
            appt_date = datetime.datetime.strptime(appt['preferred_day'], '%Y-%m-%d').date()
            if appt_date >= today:
                upcoming_appts.append(appt)
            else:
                previous_appts.append(appt)
        except (ValueError, TypeError):
            previous_appts.append(appt)

    # --- Render Appointments in 2 Columns ---
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Upcoming")
        if not upcoming_appts:
            st.caption("No upcoming appointments.")
        
        for appt in sorted(upcoming_appts, key=lambda x: x['preferred_day']):
            with st.expander(f"**{appt['preferred_day']}** - {appt['doctor_name']}"):
                st.markdown(f"**Hospital:** {appt.get('hospital_name', 'N/A')}")
                st.markdown(f"**Status:** {appt.get('status', 'Pending')}")

    with col2:
        st.subheader("Previous")
        if not previous_appts:
            st.caption("No previous appointments.")
        
        for appt in previous_appts:
             with st.expander(f"**{appt['preferred_day']}** - {appt['doctor_name']}"):
                st.markdown(f"**Hospital:** {appt.get('hospital_name', 'N/A')}")
                st.markdown(f"**Status:** {appt.get('status', 'Completed')}")

# --- Main App Logic ---
def main():
    load_css("style.css") 
    SessionManager.init_session()

    # --- Authentication Gate ---
    if not SessionManager.is_authenticated():
        show_login_page()
        return

    # --- New Horizontal Navigation Bar ---
    with st.container():
        selected = option_menu(
            menu_title=None, # required
            options=["New Analysis", "Appointments", "Medications", "Profile"], # UPDATED
            icons=["clipboard-data-fill", "calendar2-check-fill", "capsule", "person-circle"], # UPDATED
            menu_icon="cast", # optional
            default_index=0,
            orientation="horizontal",
            styles={
                "container": {"padding": "0!important", "background-color": "#111827", "border-bottom": "2px solid #374151"},
                "icon": {"color": "white", "font-size": "20px"}, 
                "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#374151", "color": "#D1D5DB"},
                "nav-link-selected": {"background-color": "#3B82F6", "color": "white"},
            }
        )
    # --- End Navigation Bar ---

    # --- Sidebar (for Chat History only) ---
    show_sidebar()

    # --- Main Content Area (Controlled by Navigation) ---
    if selected == "New Analysis":
        if st.session_state.get('current_session'):
            st.title(f"Analysis Session: {st.session_state.current_session['title']}")
            show_chat_history()
            
            # Conditionally show booking form or analysis form
            if st.session_state.get('show_booking_form', False):
                show_booking_form()
            else:
                show_analysis_form()
        else:
            show_welcome_screen()

    elif selected == "Appointments":
        st.title("🗓️ Your Appointments")
        st.markdown("<hr class='styled-divider'>", unsafe_allow_html=True)
        show_appointment_list() # Call the function
        
    elif selected == "Medications": # <-- NEW TAB
        show_medication_tab()

    elif selected == "Profile":
        st.title("👤 Your Profile")
        st.markdown("<hr class='styled-divider'>", unsafe_allow_html=True)
        
        display_name = st.session_state.user.get('name', st.session_state.user.get('email'))
        st.subheader(f"Welcome, {display_name}")
        st.write(f"**Email:** {st.session_state.user.get('email')}")
        
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            SessionManager.logout()
            st.rerun()

if __name__ == "__main__":
    main()










































# import streamlit as st
# import datetime
# from auth.session_manager import SessionManager
# from components.auth_pages import show_login_page
# from components.sidebar import show_sidebar
# from components.analysis_form import show_analysis_form
# from components.booking_form import show_booking_form
# from config.app_config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON
# from streamlit_option_menu import option_menu
# from components.medication_tab import show_medication_tab # <-- ADD IMPORT

# # --- Page Config (Must be first Streamlit command) ---
# st.set_page_config(
#     page_title="CuraMate - Health Insights Agent",
#     page_icon="🩺",
#     layout="wide"
# )

# # --- CSS Loader Function ---
# def load_css(file_name):
#     """Loads a local CSS file."""
#     try:
#         with open(file_name) as f:
#             st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
#     except FileNotFoundError:
#         st.error(f"CSS file '{file_name}' not found. Make sure 'style.css' is in the root directory.")

# # --- Original Welcome Screen Function ---
# def show_welcome_screen():
#     st.markdown(
#         f"""
#         <div style='text-align: center; padding: 50px;'>
#             <h1>{APP_ICON} {APP_NAME}</h1>
#             <h3>{APP_DESCRIPTION}</h3>
#             <p style='font-size: 1.2em; color: #D1D5DB;'>{APP_TAGLINE}</p>
#             <p>Start by creating a new analysis session in the sidebar</p>
#         </div>
#         """,
#         unsafe_allow_html=True
#     )
    
#     col1, col2, col3 = st.columns([2, 3, 2])
#     with col2:
#         if st.button("➕ Create New Analysis Session", use_container_width=True, type="primary"):
#             success, session = SessionManager.create_chat_session()
#             if success:
#                 st.session_state.current_session = session
#                 st.rerun()
#             else:
#                 st.error("Failed to create session")

# # --- Updated Chat History (for Dark Theme) ---
# def show_chat_history():
#     success, messages = st.session_state.auth_service.get_session_messages(
#         st.session_state.current_session['id']
#     )
    
#     if success:
#         for msg in messages:
#             if msg['role'] == 'user':
#                 # User message
#                 st.markdown(f"""
#                 <div style='padding: 1rem; border-radius: 8px; background-color: #374151; margin-bottom: 1rem; border: 1px solid #4B5563;'>
#                     <b>You:</b><br><br>{msg['content']}
#                 </div>
#                 """, unsafe_allow_html=True)
#             else:
#                 # Assistant message
#                 st.markdown(f"""
#                 <div style='padding: 1rem; border-radius: 8px; background-color: #1F2937; border: 1px solid #4B5563; margin-bottom: 1rem;'>
#                     <b>CuraMate:</b><br>{msg['content']}
#                 </div>
#                 """, unsafe_allow_html=True)

# # --- New Appointment List Function (Moved from Sidebar) ---
# def show_appointment_list():
#     """Fetches and displays upcoming and previous appointments."""
    
#     if not (st.session_state.user and 'id' in st.session_state.user):
#         st.info("Log in to see appointments.")
#         return

#     success, appointments = SessionManager.get_user_appointments()
    
#     if not success:
#         st.error("Failed to load appointments.")
#         return

#     if not appointments:
#         st.info("You have no appointments scheduled.")
#         return

#     upcoming_appts = []
#     previous_appts = []
#     today = datetime.date.today()

#     for appt in appointments:
#         try:
#             appt_date = datetime.datetime.strptime(appt['preferred_day'], '%Y-%m-%d').date()
#             if appt_date >= today:
#                 upcoming_appts.append(appt)
#             else:
#                 previous_appts.append(appt)
#         except (ValueError, TypeError):
#             previous_appts.append(appt)

#     # --- Render Appointments in 2 Columns ---
#     col1, col2 = st.columns(2)
    
#     with col1:
#         st.subheader("Upcoming")
#         if not upcoming_appts:
#             st.caption("No upcoming appointments.")
        
#         for appt in sorted(upcoming_appts, key=lambda x: x['preferred_day']):
#             with st.expander(f"**{appt['preferred_day']}** - {appt['doctor_name']}"):
#                 st.markdown(f"**Hospital:** {appt.get('hospital_name', 'N/A')}")
#                 st.markdown(f"**Status:** {appt.get('status', 'Pending')}")

#     with col2:
#         st.subheader("Previous")
#         if not previous_appts:
#             st.caption("No previous appointments.")
        
#         for appt in previous_appts:
#              with st.expander(f"**{appt['preferred_day']}** - {appt['doctor_name']}"):
#                 st.markdown(f"**Hospital:** {appt.get('hospital_name', 'N/A')}")
#                 st.markdown(f"**Status:** {appt.get('status', 'Completed')}")

# # --- Main App Logic ---
# def main():
#     load_css("style.css") 
#     SessionManager.init_session()

#     # --- Authentication Gate ---
#     if not SessionManager.is_authenticated():
#         show_login_page()
#         return

#     # --- New Horizontal Navigation Bar ---
#     with st.container():
#         selected = option_menu(
#             menu_title=None, # required
#             options=["New Analysis", "Appointments", "Medications", "Profile"], 
#             icons=["clipboard-data-fill", "calendar2-check-fill", "capsule", "person-circle"],
#             default_index=0,
#             orientation="horizontal",
#             styles={
#                 "container": {"padding": "0!important", "background-color": "#70747b", "border-bottom": "2px solid #374151"},
#                 "icon": {"color": "white", "font-size": "20px"}, 
#                 "nav-link": {"font-size": "16px", "text-align": "center", "margin":"0px", "--hover-color": "#ACB3BF", "color": "#000000"},
#                 "nav-link-selected": {"background-color": "#3B82F6", "color": "white"},
#             }
#         )
#     # --- End Navigation Bar ---

#     # --- Sidebar (for Chat History only) ---
#     show_sidebar()

#     # --- Main Content Area (Controlled by Navigation) ---
#     if selected == "New Analysis":
#         if st.session_state.get('current_session'):
#             st.title(f"Analysis Session: {st.session_state.current_session['title']}")
#             show_chat_history()
            
#             # Conditionally show booking form or analysis form
#             if st.session_state.get('show_booking_form', False):
#                 show_booking_form()
#             else:
#                 show_analysis_form()
#         else:
#             show_welcome_screen()

#     elif selected == "Appointments":
#         st.title("🗓️ Your Appointments")
#         st.markdown("<hr class='styled-divider'>", unsafe_allow_html=True)
#         show_appointment_list() # Call the function
        
#     elif selected == "Medications":
#         show_medication_tab()
        

#     elif selected == "Profile":
#         st.title("👤 Your Profile")
#         st.markdown("<hr class='styled-divider'>", unsafe_allow_html=True)
        
#         display_name = st.session_state.user.get('name', st.session_state.user.get('email'))
#         st.subheader(f"Welcome, {display_name}")
#         st.write(f"**Email:** {st.session_state.user.get('email')}")
        
#         st.markdown("---")
#         if st.button("Logout", use_container_width=True):
#             SessionManager.logout()
#             st.rerun()

# if __name__ == "__main__":
#     main()




















# # import streamlit as st
# # from auth.session_manager import SessionManager
# # from components.auth_pages import show_login_page
# # from components.sidebar import show_sidebar
# # from components.analysis_form import show_analysis_form
# # from components.booking_form import show_booking_form
# # # from components.footer import show_footer
# # from config.app_config import APP_NAME, APP_TAGLINE, APP_DESCRIPTION, APP_ICON

# # # Must be the first Streamlit command
# # st.set_page_config(
# #     page_title="CuraMate",
# #     page_icon="🩺",
# #     layout="wide"
# # )


# # def load_css(file_name):
# #     """Loads a local CSS file."""
# #     try:
# #         with open(file_name) as f:
# #             st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
# #     except FileNotFoundError:
# #         st.error(f"CSS file '{file_name}' not found. Make sure it's in the same directory.")



# # # Initialize session state
# # SessionManager.init_session()

# # # Hide all Streamlit form-related elements
# # st.markdown("""
# #     <style>
# #         /* Hide form submission helper text */
# #         div[data-testid="InputInstructions"] > span:nth-child(1) {
# #             visibility: hidden;
# #         }
# #     </style>
# # """, unsafe_allow_html=True)

# # def show_welcome_screen():
# #     st.markdown(
# #         f"""
# #         <div style='text-align: center; padding: 50px;'>
# #             <h1>{APP_ICON} {APP_NAME}</h1>
# #             <h3>{APP_DESCRIPTION}</h3>
# #             <p style='font-size: 1.2em; color: #666;'>{APP_TAGLINE}</p>
# #             <p>Start by creating a new analysis session</p>
# #         </div>
# #         """,
# #         unsafe_allow_html=True
# #     )
    
# #     col1, col2, col3 = st.columns([2, 3, 2])
# #     with col2:
# #         if st.button("➕ Create New Analysis Session", use_container_width=True, type="primary"):
# #             success, session = SessionManager.create_chat_session()
# #             if success:
# #                 st.session_state.current_session = session
# #                 st.rerun()
# #             else:
# #                 st.error("Failed to create session")

# # def show_chat_history():
# #     success, messages = st.session_state.auth_service.get_session_messages(
# #         st.session_state.current_session['id']
# #     )
    
# #     if success:
# #         for msg in messages:
# #             if msg['role'] == 'user':
# #                 st.info(msg['content'])
# #             else:
# #                 st.success(msg['content'])

# # def show_user_greeting():
# #     if st.session_state.user:
# #         display_name = st.session_state.user.get('name') or st.session_state.user.get('email', '')
# #         st.markdown(f"""
# #             <div style='text-align: right; padding: 1rem; color: #64B5F6; font-size: 1.1em;'>
# #                 👋 Hi, {display_name}
# #             </div>
# #         """, unsafe_allow_html=True)




# # def main():

# #     load_css("style.css")
# #     SessionManager.init_session()

# #     if not SessionManager.is_authenticated():
# #         show_login_page()
# #         # show_footer()
# #         return

# #     # Show user greeting at the top
# #     show_user_greeting()
    
# #     # Show sidebar
# #     show_sidebar()

# #     # Main chat area
# #     if st.session_state.get('current_session'):
# #         st.title(f"📊 {st.session_state.current_session['title']}")
# #         show_chat_history()
        
# #         if st.session_state.get('show_booking_form', False):
# #             show_booking_form()
# #         else:
# #             show_analysis_form()
            
# #     else:
# #         show_welcome_screen()


# # if __name__ == "__main__":
# #     main()