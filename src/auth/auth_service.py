import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import datetime
import time
import re
from twilio.rest import Client  

class AuthService:
    def __init__(self):
        try:
            self.supabase = st.connection(
                "supabase",
                type=SupabaseConnection,
                ttl=None,
                url=st.secrets["SUPABASE_URL"],
                key=st.secrets["SUPABASE_KEY"],
                client_options={
                    "timeout": 30,  # 30 seconds timeout
                    "retries": 3,   # 3 retries
                }
            )

            self.twilio_sid = st.secrets.get("twilio", {}).get("ACCOUNT_SID")
            self.twilio_token = st.secrets.get("twilio", {}).get("AUTH_TOKEN")
            self.twilio_from_number = st.secrets.get("twilio", {}).get("WHATSAPP_FROM")
            
            if self.twilio_sid:
                self.twilio_client = Client(self.twilio_sid, self.twilio_token)
            else:
                self.twilio_client = None

        except Exception as e:
            st.error(f"Failed to initialize services: {str(e)}")
            raise e
        
        # Validate session on initialization
        if 'auth_token' in st.session_state:
            if not self.validate_session_token():
                self.sign_out()

    def validate_email(self, email):
        """Validate email format."""
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))

    def check_existing_user(self, email):
        """Check if user already exists."""
        try:
            result = self.supabase.table('users')\
                .select('id')\
                .eq('email', email)\
                .execute()
            return len(result.data) > 0
        except Exception:
            return False

    def sign_up(self, email, password, name):
        try:
            auth_response = self.supabase.client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "name": name
                    }
                }
            })
            
            if not auth_response.user:
                return False, "Failed to create user account"
            
            user_data = {
                'id': auth_response.user.id,
                'email': email,
                'name': name,
                'created_at': datetime.now().isoformat()
            }
            
            # Insert user data into users table
            self.supabase.table('users').insert(user_data).execute()
            
            return True, user_data
                
        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate" in error_msg or "already registered" in error_msg:
                return False, "Email already registered"
            return False, f"Sign up failed: {str(e)}"

    def sign_in(self, email, password):
        try:
          
            
            auth_response = self.supabase.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            
            if auth_response and auth_response.user:
                # Get user data
                user_data = self.get_user_data(auth_response.user.id)
                if not user_data:
                    return False, "User data not found"
                    
                # Store session info
                st.session_state.auth_token = auth_response.session.access_token
                st.session_state.user = user_data
                return True, user_data
                
            return False, "Invalid login response"
        except Exception as e:
            return False, str(e)
    
    def sign_out(self):
        """Sign out and clear all session data."""
        try:
            self.supabase.client.auth.sign_out()
            from auth.session_manager import SessionManager
            SessionManager.clear_session_state()
            return True, None
        except Exception as e:
            return False, str(e)
    
    def get_user(self):
        try:
            return self.supabase.client.auth.get_user()
        except Exception:
            return None

    def create_session(self, user_id, title=None):
        try:
            current_time = datetime.now()
            default_title = f"{current_time.strftime('%d-%m-%Y')} | {current_time.strftime('%H:%M:%S')}"
            
            session_data = {
                'user_id': user_id,
                'title': title or default_title,
                'created_at': current_time.isoformat()
            }
            result = self.supabase.table('chat_sessions').insert(session_data).execute()
            return True, result.data[0] if result.data else None
        except Exception as e:
            return False, str(e)

    def get_user_sessions(self, user_id):
        try:
            result = self.supabase.table('chat_sessions')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .execute()
            return True, result.data
        except Exception as e:
            st.error(f"Error fetching sessions: {str(e)}")
            return False, []

    def save_chat_message(self, session_id, content, role='user'):
        try:
            message_data = {
                'session_id': session_id,
                'content': content,
                'role': role,
                'created_at': datetime.now().isoformat()
            }
            result = self.supabase.table('chat_messages').insert(message_data).execute()
            return True, result.data[0] if result.data else None
        except Exception as e:
            return False, str(e)

    def get_session_messages(self, session_id):
        try:
            result = self.supabase.table('chat_messages')\
                .select('*')\
                .eq('session_id', session_id)\
                .order('created_at')\
                .execute()
            return True, result.data
        except Exception as e:
            return False, str(e)

    def delete_session(self, session_id):
        try:
            messages_delete = self.supabase.table('chat_messages')\
                .delete()\
                .eq('session_id', session_id)\
                .execute()

            session_delete = self.supabase.table('chat_sessions')\
                .delete()\
                .eq('id', session_id)\
                .execute()

            return True, None
        except Exception as e:
            st.error(f"Failed to delete session: {str(e)}")
            return False, str(e)
    
    def validate_session_token(self):
        """Validate existing session token on startup."""
        try:
            session = self.supabase.client.auth.get_session()
            if not session or not session.access_token:
                return None
                
            if session.access_token != st.session_state.get('auth_token'):
                return None
                
            user = self.supabase.client.auth.get_user()
            if not user or not user.user:
                return None
                
            return self.get_user_data(user.user.id)
        except Exception:
            return None
    
    def get_user_data(self, user_id):
        """Get user data from database."""
        try:
            response = self.supabase.table('users')\
                .select('*')\
                .eq('id', user_id)\
                .single()\
                .execute()
            return response.data if response else None
        except Exception:
            return None

  
    def _send_whatsapp_confirmation(self, patient_name, patient_phone, doctor_name, preferred_day):
        """
        Sends a WhatsApp confirmation message via Twilio (using the Sandbox).
        """
        if not self.twilio_client:
            st.error("Twilio service is not configured. Cannot send WhatsApp.")
            return

        # --- FIX: Clean the phone number ---
        phone_number_cleaned = (
            patient_phone.replace(" ", "")
            .replace("-", "")
            .replace("(", "")
            .replace(")", "")
        )
        # --- END FIX ---

        if not phone_number_cleaned.startswith("+"):
            st.error(f"Invalid phone number format for WhatsApp. Must be E.164 (+91...). You entered: {patient_phone}")
            return

        try:
          
            message_body = (
                f"Hi {patient_name}! Your appointment request with {doctor_name} "
                f"for {preferred_day} has been received. "
                "The clinic will contact you shortly to confirm."
                "\n- CuraMate"
            )

            message = self.twilio_client.messages.create(
                from_=self.twilio_from_number,
                body=message_body,
                to=f'whatsapp:{phone_number_cleaned}' # <-- Use cleaned number
            )

            print(f"WhatsApp message sent! SID: {message.sid}")

        except Exception as e:
            st.error(f"Twilio Error: Failed to send WhatsApp. {str(e)}")
            pass

    def save_appointment(self, user_id, doctor_id, doctor_name,hospital_name, patient_name, patient_email, patient_phone, preferred_city, preferred_day):
        """Saves a new appointment request to the database."""
        try:
            appointment_data = {
                "user_id": user_id,
                "doctor_id": doctor_id,
                "doctor_name": doctor_name,
                "hospital_name": hospital_name,
                "patient_name": patient_name,
                "patient_email": patient_email,
                "patient_phone": patient_phone,
                "preferred_city": preferred_city,
                "preferred_day": preferred_day,
                "status": "Pending", # Set default status
                "created_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table('appointments').insert(appointment_data).execute()
            
            if result.data:

            
                self._send_whatsapp_confirmation(
                    patient_name=patient_name,
                    patient_phone=patient_phone, 
                    doctor_name=doctor_name,
                    preferred_day=preferred_day
                )
                
                return True
            else:
                st.error(f"Supabase insert returned no data: {result.error.message if result.error else 'Unknown error'}")
                return False
        except Exception as e:
            st.error(f"Error saving appointment: {str(e)}")
            return False
        
    def get_user_appointments(self, user_id):
        """Get all appointments for a user, sorted by date."""
        try:
            result = self.supabase.table('appointments')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('preferred_day', desc=True)\
                .execute()
            return True, result.data
        except Exception as e:
            st.error(f"Error fetching appointments: {str(e)}")
            return False, []
        
    
   # --- *** THIS IS THE UPDATED FUNCTION *** ---
    def save_medication(self, user_id, med_data):
        """Saves a single medication record."""
        try:
            # Ensure med_data has the user_id
            med_data['user_id'] = user_id
            # Add created_at if not present
            if 'created_at' not in med_data:
                 med_data['created_at'] = datetime.now().isoformat()
                 
            # --- FIX ---
            # Use returning="minimal" to force an exception if RLS fails.
            # This stops the "silent failure"
            result = self.supabase.table('medications').insert(med_data, returning="minimal").execute()
            
            # If .execute() does not throw, it succeeded.
            return True, result.data
        
        except Exception as e:
            # The RLS error will be caught here and returned as False
            return False, str(e)

    def get_user_medications(self, user_id):
        """Fetches all active medications for a user."""
        try:
            result = self.supabase.table('medications')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .execute()
            return True, result.data
        except Exception as e:
            return False, []






























# import streamlit as st
# from st_supabase_connection import SupabaseConnection
# from datetime import datetime
# import time
# import re
# from twilio.rest import Client  

# class AuthService:
#     def __init__(self):
#         try:
#             self.supabase = st.connection(
#                 "supabase",
#                 type=SupabaseConnection,
#                 ttl=None,
#                 url=st.secrets["SUPABASE_URL"],
#                 key=st.secrets["SUPABASE_KEY"],
#                 client_options={
#                     "timeout": 30,  # 30 seconds timeout
#                     "retries": 3,   # 3 retries
#                 }
#             )

#             self.twilio_sid = st.secrets.get("twilio", {}).get("ACCOUNT_SID")
#             self.twilio_token = st.secrets.get("twilio", {}).get("AUTH_TOKEN")
#             self.twilio_from_number = st.secrets.get("twilio", {}).get("WHATSAPP_FROM")
            
#             if self.twilio_sid:
#                 self.twilio_client = Client(self.twilio_sid, self.twilio_token)
#             else:
#                 self.twilio_client = None

#         except Exception as e:
#             st.error(f"Failed to initialize services: {str(e)}")
#             raise e
        
#         # Validate session on initialization
#         if 'auth_token' in st.session_state:
#             if not self.validate_session_token():
#                 self.sign_out()

#     def validate_email(self, email):
#         """Validate email format."""
#         pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
#         return bool(re.match(pattern, email))

#     def check_existing_user(self, email):
#         """Check if user already exists."""
#         try:
#             result = self.supabase.table('users')\
#                 .select('id')\
#                 .eq('email', email)\
#                 .execute()
#             return len(result.data) > 0
#         except Exception:
#             return False

#     def sign_up(self, email, password, name):
#         try:
#             auth_response = self.supabase.client.auth.sign_up({
#                 "email": email,
#                 "password": password,
#                 "options": {
#                     "data": {
#                         "name": name
#                     }
#                 }
#             })
            
#             if not auth_response.user:
#                 return False, "Failed to create user account"
            
#             user_data = {
#                 'id': auth_response.user.id,
#                 'email': email,
#                 'name': name,
#                 'created_at': datetime.now().isoformat()
#             }
            
#             # Insert user data into users table
#             self.supabase.table('users').insert(user_data).execute()
            
#             return True, user_data
                
#         except Exception as e:
#             error_msg = str(e).lower()
#             if "duplicate" in error_msg or "already registered" in error_msg:
#                 return False, "Email already registered"
#             return False, f"Sign up failed: {str(e)}"

#     def sign_in(self, email, password):
#         try:
          
            
#             auth_response = self.supabase.client.auth.sign_in_with_password({
#                 "email": email,
#                 "password": password
#             })
            
#             if auth_response and auth_response.user:
#                 # Get user data
#                 user_data = self.get_user_data(auth_response.user.id)
#                 if not user_data:
#                     return False, "User data not found"
                    
#                 # Store session info
#                 st.session_state.auth_token = auth_response.session.access_token
#                 st.session_state.user = user_data
#                 return True, user_data
                
#             return False, "Invalid login response"
#         except Exception as e:
#             return False, str(e)
    
#     def sign_out(self):
#         """Sign out and clear all session data."""
#         try:
#             self.supabase.client.auth.sign_out()
#             from auth.session_manager import SessionManager
#             SessionManager.clear_session_state()
#             return True, None
#         except Exception as e:
#             return False, str(e)
    
#     def get_user(self):
#         try:
#             return self.supabase.client.auth.get_user()
#         except Exception:
#             return None

#     def create_session(self, user_id, title=None):
#         try:
#             current_time = datetime.now()
#             default_title = f"{current_time.strftime("%d-%m-%Y")} | {current_time.strftime("%H:%M:%S")}"
            
#             session_data = {
#                 'user_id': user_id,
#                 'title': title or default_title,
#                 'created_at': current_time.isoformat()
#             }
#             result = self.supabase.table('chat_sessions').insert(session_data).execute()
#             return True, result.data[0] if result.data else None
#         except Exception as e:
#             return False, str(e)

#     def get_user_sessions(self, user_id):
#         try:
#             result = self.supabase.table('chat_sessions')\
#                 .select('*')\
#                 .eq('user_id', user_id)\
#                 .order('created_at', desc=True)\
#                 .execute()
#             return True, result.data
#         except Exception as e:
#             st.error(f"Error fetching sessions: {str(e)}")
#             return False, []

#     def save_chat_message(self, session_id, content, role='user'):
#         try:
#             message_data = {
#                 'session_id': session_id,
#                 'content': content,
#                 'role': role,
#                 'created_at': datetime.now().isoformat()
#             }
#             result = self.supabase.table('chat_messages').insert(message_data).execute()
#             return True, result.data[0] if result.data else None
#         except Exception as e:
#             return False, str(e)

#     def get_session_messages(self, session_id):
#         try:
#             result = self.supabase.table('chat_messages')\
#                 .select('*')\
#                 .eq('session_id', session_id)\
#                 .order('created_at')\
#                 .execute()
#             return True, result.data
#         except Exception as e:
#             return False, str(e)

#     def delete_session(self, session_id):
#         try:
#             messages_delete = self.supabase.table('chat_messages')\
#                 .delete()\
#                 .eq('session_id', session_id)\
#                 .execute()

#             session_delete = self.supabase.table('chat_sessions')\
#                 .delete()\
#                 .eq('id', session_id)\
#                 .execute()

#             return True, None
#         except Exception as e:
#             st.error(f"Failed to delete session: {str(e)}")
#             return False, str(e)
    
#     def validate_session_token(self):
#         """Validate existing session token on startup."""
#         try:
#             session = self.supabase.client.auth.get_session()
#             if not session or not session.access_token:
#                 return None
                
#             if session.access_token != st.session_state.get('auth_token'):
#                 return None
                
#             user = self.supabase.client.auth.get_user()
#             if not user or not user.user:
#                 return None
                
#             return self.get_user_data(user.user.id)
#         except Exception:
#             return None
    
#     def get_user_data(self, user_id):
#         """Get user data from database."""
#         try:
#             response = self.supabase.table('users')\
#                 .select('*')\
#                 .eq('id', user_id)\
#                 .single()\
#                 .execute()
#             return response.data if response else None
#         except Exception:
#             return None

  
#     def _send_whatsapp_confirmation(self, patient_name, patient_phone, doctor_name, preferred_day):
#         """
#         Sends a WhatsApp confirmation message via Twilio (using the Sandbox).
#         """
#         if not self.twilio_client:
#             st.error("Twilio service is not configured. Cannot send WhatsApp.")
#             return

#         if not patient_phone.startswith("+"):
#             st.error(f"Invalid phone number format for WhatsApp. Must be E.164 (+91...). You entered: {patient_phone}")
#             return

#         try:
          
#             message_body = (
#                 f"Hi {patient_name}! Your appointment request with {doctor_name} "
#                 f"for {preferred_day} has been received. "
#                 "The clinic will contact you shortly to confirm."
#                 "\n- CuraMate"
#             )

#             message = self.twilio_client.messages.create(
#                 from_=self.twilio_from_number,
#                 body=message_body,
#                 to=f'whatsapp:{patient_phone}' # Send to the user's phone
#             )

#             print(f"WhatsApp message sent! SID: {message.sid}")

#         except Exception as e:
#             st.error(f"Twilio Error: Failed to send WhatsApp. {str(e)}")
#             pass

#     def save_appointment(self, user_id, doctor_id, doctor_name,hospital_name, patient_name, patient_email, patient_phone, preferred_city, preferred_day):
#         """Saves a new appointment request to the database."""
#         try:
#             appointment_data = {
#                 "user_id": user_id,
#                 "doctor_id": doctor_id,
#                 "doctor_name": doctor_name,
#                 "hospital_name": hospital_name,
#                 "patient_name": patient_name,
#                 "patient_email": patient_email,
#                 "patient_phone": patient_phone,
#                 "preferred_city": preferred_city,
#                 "preferred_day": preferred_day,
#                 "status": "Pending", # Set default status
#                 "created_at": datetime.now().isoformat()
#             }
            
#             result = self.supabase.table('appointments').insert(appointment_data).execute()
            
#             if result.data:

            
#                 self._send_whatsapp_confirmation(
#                     patient_name=patient_name,
#                     patient_phone=patient_phone, 
#                     doctor_name=doctor_name,
#                     preferred_day=preferred_day
#                 )
                
#                 return True
#             else:
#                 st.error(f"Supabase insert returned no data: {result.error.message if result.error else 'Unknown error'}")
#                 return False
#         except Exception as e:
#             st.error(f"Error saving appointment: {str(e)}")
#             return False
        
#     def get_user_appointments(self, user_id):
#         """Get all appointments for a user, sorted by date."""
#         try:
#             result = self.supabase.table('appointments')\
#                 .select('*')\
#                 .eq('user_id', user_id)\
#                 .order('preferred_day', desc=True)\
#                 .execute()
#             return True, result.data
#         except Exception as e:
#             st.error(f"Error fetching appointments: {str(e)}")
#             return False, []
        
    
#    # --- Add these two methods INSIDE the AuthService class ---

#     def save_medication(self, user_id, med_data):
#         """Saves a single medication record."""
#         try:
#             # Ensure med_data has the user_id
#             med_data['user_id'] = user_id
#             # Add created_at if not present
#             if 'created_at' not in med_data:
#                  med_data['created_at'] = datetime.now().isoformat()
                 
#             result = self.supabase.table('medications').insert(med_data).execute()
#             return True, result.data
#         except Exception as e:
#             return False, str(e)

#     def get_user_medications(self, user_id):
#         """Fetches all active medications for a user."""
#         try:
#             result = self.supabase.table('medications')\
#                 .select('*')\
#                 .eq('user_id', user_id)\
#                 .order('created_at', desc=True)\
#                 .execute()
#             return True, result.data
#         except Exception as e:
#             return False, []