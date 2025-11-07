import streamlit as st
from auth.session_manager import SessionManager
from config.app_config import ANALYSIS_DAILY_LIMIT
from streamlit_option_menu import option_menu # <-- 1. Import
import re # <-- 2. Import re for cleaning title

def show_sidebar():
    with st.sidebar:
        st.title(f"🩺 CuraMate")
        st.markdown(f"Welcome, {st.session_state.user.get('name', 'User')}!")
        
        # --- NEW SESSION BUTTON (Primary) ---
        if st.button("➕ New Analysis Session", use_container_width=True, type="primary"):
            if st.session_state.user and 'id' in st.session_state.user:
                success, session = SessionManager.create_chat_session()
                if success:
                    st.session_state.current_session = session
                    st.rerun()
                else:
                    st.error("Failed to create session")
            else:
                st.error("Please log in again")
                SessionManager.logout()
                st.rerun()

        # --- ANALYSIS LIMIT BOX (Unchanged) ---
        if 'analysis_count' not in st.session_state:
            st.session_state.analysis_count = 0
        
        remaining = ANALYSIS_DAILY_LIMIT - st.session_state.analysis_count
        st.markdown(
            f"""
            <div style='
                padding: 0.5rem;
                border-radius: 0.5rem;
                background: rgba(100, 181, 246, 0.1);
                margin: 0.5rem 0;
                text-align: center;
                font-size: 0.9em;
            '>
                <p style='margin: 0; color: #666;'>Daily Analysis Limit</p>
                <p style='
                    margin: 0.2rem 0 0 0;
                    color: {"#1976D2" if remaining > 3 else "#FF4B4B"};
                    font-weight: 500;
                '>
                    {remaining}/{ANALYSIS_DAILY_LIMIT} remaining
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        
        # --- RENDER THE NEW SESSION LIST ---
        show_session_list()
        
        # --- FOOTER & LOGOUT ---
        # This CSS trick pushes the logout button to the bottom
        st.markdown("""
            <style>
            .st-emotion-cache-16txtl3 {
                flex: 1;
            }
            .st-emotion-cache-h4xjwg {
                flex: 1;
            }
            </style>
        """, unsafe_allow_html=True)
        
        st.markdown("<div class='st-emotion-cache-16txtl3 st-emotion-cache-h4xjwg'></div>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            SessionManager.logout()
            st.rerun()


def show_session_list():
    """
    Renders the new, stylish session list using streamlit-option-menu.
    """
    if not (st.session_state.user and 'id' in st.session_state.user):
        return

    success, sessions = SessionManager.get_user_sessions()
    if not success:
        st.error("Failed to load sessions")
        return

    if not sessions:
        st.info("No previous sessions")
        return

    # --- NEW MENU LOGIC ---
    
    # 1. Prepare data for the menu
    session_titles = []
    session_map = {} # To map titles back to session objects
    
    for session in sessions:
        # Clean title: remove emojis, limit length
        title = re.sub(r'[^\w\s-]', '', session['title'])
        title = (title[:25] + '...') if len(title) > 25 else title
        session_titles.append(title)
        session_map[title] = session

    # 2. Find the index of the currently active session
    default_index = 0
    if st.session_state.get('current_session'):
        try:
            current_title = re.sub(r'[^\w\s-]', '', st.session_state.current_session['title'])
            current_title = (current_title[:25] + '...') if len(current_title) > 25 else current_title
            default_index = session_titles.index(current_title)
        except ValueError:
            default_index = 0 # Fallback if not found

    # 3. Render the navigation menu
    selected_title = option_menu(
        menu_title="Previous Sessions",
        options=session_titles,
        icons=['chat-text'] * len(session_titles), # Icon for each
        menu_icon="collection",
        default_index=default_index,
        orientation="vertical",
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"font-size": "16px"}, 
            "menu-title": {"font-size": "18px", "font-weight": "600", "margin-bottom": "10px"},
            "nav-link": {"font-size": "15px", "text-align": "left", "margin":"0px", "--hover-color": "#374151"},
        }
    )
    
    # 4. Handle session selection
    if selected_title and session_map[selected_title] != st.session_state.get('current_session'):
        st.session_state.current_session = session_map[selected_title]
        st.rerun()

    # --- NEW DELETE FUNCTIONALITY ---
    st.markdown("---")
    st.subheader("Manage Sessions")
    
    # Let user select a session to delete
    session_to_delete_title = st.selectbox(
        "Select a session to delete",
        options=[""] + session_titles,
        index=0
    )
    
    if session_to_delete_title:
        session_to_delete = session_map[session_to_delete_title]
        
        if st.button(f"Delete '{session_to_delete_title}'", type="primary", use_container_width=True):
            session_id = session_to_delete['id']
            current_session_id = st.session_state.get('current_session', {}).get('id')
            
            success, error = SessionManager.delete_session(session_id)
            if success:
                if current_session_id and current_session_id == session_id:
                    st.session_state.current_session = None
                st.rerun()
            else:
                st.error(f"Failed to delete: {error}")
























# import streamlit as st
# from auth.session_manager import SessionManager
# # from components.footer import show_footer
# from config.app_config import ANALYSIS_DAILY_LIMIT
# import datetime # <-- ADD THIS IMPORT

# def show_sidebar():
#     with st.sidebar:
#         st.title("💬 Chat Sessions")
        
#         if st.button("+ New Analysis Session", use_container_width=True):
#             if st.session_state.user and 'id' in st.session_state.user:
#                 success, session = SessionManager.create_chat_session()
#                 if success:
#                     st.session_state.current_session = session
#                     st.rerun()
#                 else:
#                     st.error("Failed to create session")
#             else:
#                 st.error("Please log in again")
#                 SessionManager.logout()
#                 st.rerun()

#         # Add analysis counter
#         if 'analysis_count' not in st.session_state:
#             st.session_state.analysis_count = 0
        
#         remaining = ANALYSIS_DAILY_LIMIT - st.session_state.analysis_count
#         st.markdown(
#             f"""
#             <div style='
#                 padding: 0.5rem;
#                 border-radius: 0.5rem;
#                 background: rgba(100, 181, 246, 0.1);
#                 margin: 0.5rem 0;
#                 text-align: center;
#                 font-size: 0.9em;
#             '>
#                 <p style='margin: 0; color: #666;'>Daily Analysis Limit</p>
#                 <p style='
#                     margin: 0.2rem 0 0 0;
#                     color: {"#1976D2" if remaining > 3 else "#FF4B4B"};
#                     font-weight: 500;
#                 '>
#                     {remaining}/{ANALYSIS_DAILY_LIMIT} remaining
#                 </p>
#             </div>
#             """,
#             unsafe_allow_html=True
#         )

#         st.markdown("---")
#         show_session_list()
        
#         # --- NEW APPOINTMENTS SECTION ---
#         # st.markdown("---")
#         # show_appointment_list()
        
#         # Logout button
#         st.markdown("---")
#         if st.button("Logout", use_container_width=True):
#             SessionManager.logout()
#             st.rerun()
        
       

# def show_session_list():
#     if st.session_state.user and 'id' in st.session_state.user:
#         success, sessions = SessionManager.get_user_sessions()
#         if success:
#             if sessions:
#                 st.subheader("Previous Sessions")
#                 render_session_list(sessions)
#             else:
#                 st.info("No previous sessions")

# def render_session_list(sessions):
#     # Store deletion state
#     if 'delete_confirmation' not in st.session_state:
#         st.session_state.delete_confirmation = None
    
#     for session in sessions:
#         render_session_item(session)

# def render_session_item(session):
#     if not session or not isinstance(session, dict) or 'id' not in session:
#         return
        
#     session_id = session['id']
#     current_session = st.session_state.get('current_session', {})
#     current_session_id = current_session.get('id') if isinstance(current_session, dict) else None
    
#     # Create container for each session
#     with st.container():
#         # Session title and delete button side by side
#         title_col, delete_col = st.columns([4, 1])
        
#         with title_col:
#             if st.button(f"📝 {session['title']}", key=f"session_{session_id}", use_container_width=True):
#                 st.session_state.current_session = session
#                 st.rerun()
        
#         with delete_col:
#             if st.button("🗑️", key=f"delete_{session_id}", help="Delete this session"):
#                 if st.session_state.delete_confirmation == session_id:
#                     st.session_state.delete_confirmation = None
#                 else:
#                     st.session_state.delete_confirmation = session_id
#                 st.rerun()
        
#         # Show confirmation below if this session is being deleted
#         if st.session_state.delete_confirmation == session_id:
#             st.warning("Delete above session?")
#             left_btn, right_btn = st.columns(2)
#             with left_btn:
#                 if st.button("Yes", key=f"confirm_delete_{session_id}", type="primary", use_container_width=True):
#                     handle_delete_confirmation(session_id, current_session_id)
#             with right_btn:
#                 if st.button("No", key=f"cancel_delete_{session_id}", use_container_width=True):
#                     st.session_state.delete_confirmation = None
#                     st.rerun()

# def handle_delete_confirmation(session_id, current_session_id):
#     if not session_id:
#         st.error("Invalid session")
#         return
        
#     success, error = SessionManager.delete_session(session_id)
#     if success:
#         st.session_state.delete_confirmation = None
#         # Clear current session if it was deleted
#         if current_session_id and current_session_id == session_id:
#             st.session_state.current_session = None
#         st.rerun()
#     else:
#         st.error(f"Failed to delete: {error}")

# # --- NEW FUNCTION TO SHOW APPOINTMENTS ---
# def show_appointment_list():
#     """Fetches and displays upcoming and previous appointments."""
#     st.title("🗓️ Appointments")
    
#     if not (st.session_state.user and 'id' in st.session_state.user):
#         st.info("Log in to see appointments.")
#         return

#     success, appointments = SessionManager.get_user_appointments()
    
#     if not success:
#         st.error("Failed to load appointments.")
#         return

#     if not appointments:
#         st.info("No appointments found.")
#         return

#     upcoming_appts = []
#     previous_appts = []
#     today = datetime.date.today()

#     for appt in appointments:
#         try:
#             # Assumes 'preferred_day' is saved as 'YYYY-MM-DD'
#             appt_date = datetime.datetime.strptime(appt['preferred_day'], '%Y-%m-%d').date()
#             if appt_date >= today:
#                 upcoming_appts.append(appt)
#             else:
#                 previous_appts.append(appt)
#         except (ValueError, TypeError):
#             # If date format is wrong or null, treat as previous
#             previous_appts.append(appt)

#     # --- Render Upcoming Appointments ---
#     st.subheader("Upcoming")
#     if not upcoming_appts:
#         st.caption("No upcoming appointments.")
    
#     # Sort upcoming appointments (earliest first)
#     for appt in sorted(upcoming_appts, key=lambda x: x['preferred_day']):
#         with st.expander(f"**{appt['preferred_day']}** - {appt['doctor_name']}"):
#             st.markdown(f"**Hospital:** {appt.get('hospital_name', 'N/A')}")
#             st.markdown(f"**Status:** {appt.get('status', 'Pending')}")
#             st.markdown(f"**Patient:** {appt.get('patient_name', 'N/A')}")

#     # --- Render Previous Appointments ---
#     st.subheader("Previous")
#     if not previous_appts:
#         st.caption("No previous appointments.")
    
#     # Already sorted by date descending from the SQL query
#     for appt in previous_appts:
#          with st.expander(f"**{appt['preferred_day']}** - {appt['doctor_name']}"):
#             st.markdown(f"**Hospital:** {appt.get('hospital_name', 'N/A')}")
#             st.markdown(f"**Status:** {appt.get('status', 'Completed')}") 
#             st.markdown(f"**Patient:** {appt.get('patient_name', 'N/A')}")

