import streamlit as st
import json
import re
from typing import List, Dict, Any, Tuple
from datetime import datetime

from config.booking_prompts import get_booking_prompt

from ics import Calendar, Event, DisplayAlarm
from datetime import datetime, timedelta

RISK_SPECIALTY_MAP = {
    "anemia": "Hematology", "polycythemia": "Hematology", "leukemia": "Hematology",
    "thrombocytopenia": "Hematology", "thrombocytosis": "Hematology",
    "hepatitis": "Hepatology", "cirrhosis": "Hepatology", "fatty liver disease": "Hepatology",
    "cholestasis": "Hepatology", "liver dysfunction": "Hepatology",
    "diabetes": "Endocrinology", "thyroid disorders": "Endocrinology", "metabolic syndrome": "Endocrinology",
    "hyperlipidemia": "Cardiology", "atherosclerosis": "Cardiology", "hypertension": "Cardiology",
    "kidney disease": "Nephrology", "renal": "Nephrology", "creatinine": "Nephrology"
}

def load_doctors(filepath="doctors.json") -> List[Dict[str, Any]]:
    """Loads the doctor JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("`doctors.json` file not found.")
        return []
    except json.JSONDecodeError:
        st.error("Error decoding `doctors.json`.")
        return []

def get_specialty_from_risks(health_risks: List[str]) -> str | None:
    """Finds the first matching specialty from a list of health risks."""
    if not health_risks:
        return None
        
    for risk in health_risks:
        risk_lower = risk.lower().strip()
        for keyword, specialty in RISK_SPECIALTY_MAP.items():
            if keyword in risk_lower:
                return specialty
    return None

def parse_booking_request(user_prompt: str) -> Dict[str, Any] | None:
    """
    Uses the ModelManager to parse the user's booking request.
    """
    try:
        # Get the model manager from the analysis agent in session state
        if 'analysis_agent' not in st.session_state:
            st.error("Analysis agent not found. Cannot parse request.")
            return None
        
        model_manager = st.session_state.analysis_agent.model_manager
        
        # Get the specialized system prompt
        system_prompt = get_booking_prompt(user_prompt)
        
        # Pass "user_prompt" as the data to be analyzed
        result = model_manager.generate_analysis(
            data=user_prompt,
            system_prompt=system_prompt
        )
        
        if not result["success"]:
            st.error(f"AI failed to parse your request: {result.get('error')}")
            return None
            
        # The AI should return a JSON string. We need to find it.
        json_match = re.search(r"\{.*\}", result["content"], re.DOTALL)
        if not json_match:
            st.error("AI returned an invalid format. Please try rephrasing.")
            return None
            
        parsed_json = json.loads(json_match.group(0))
        
        if not parsed_json.get("city") or not parsed_json.get("potential_dates"):
            st.error("Could not find a city or available date in your request. Please be more specific (e.g., 'Delhi, next Tuesday').")
            return None
            
        return parsed_json

    except Exception as e:
        st.error(f"Error parsing booking request: {e}")
        return None

def _parse_experience(exp_str: str) -> int:
    """Helper to convert '15 years' to 15."""
    match = re.search(r"\d+", exp_str)
    return int(match.group(0)) if match else 0

def rank_doctors(doctors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ranks doctors first by experience (descending), then by fee (ascending).
    """
    return sorted(
        doctors,
        key=lambda doc: (
            _parse_experience(doc.get("experience", "0")),  # Priority 1: Experience (High to Low)
            -doc.get("fee", float('inf'))                   # Priority 2: Fee (Low to High)
        ),
        reverse=True # Reverses the experience, so we negate the fee
    )

def find_and_book_appointment(
    specialty: str,
    parsed_request: Dict[str, Any],
    patient_details: Dict[str, Any],
    user_id: str
) -> Dict[str, Any]:
    """
    Orchestrates the new booking flow:
    1. Filters doctors by city and specialty
    2. Ranks them
    3. Finds the first available match
    4. Books the appointment
    """
    all_doctors = load_doctors()
    if not all_doctors:
        return {"success": False, "message": "Doctor database is empty."}
        
    city = parsed_request["city"]
    potential_dates = parsed_request["potential_dates"] # List of "YYYY-MM-DD"
    
    # 1. Filter by specialty and city
    filtered_doctors = [
        doc for doc in all_doctors
        if doc.get("Specialization", "").lower() == specialty.lower()
        and doc.get("city", "").lower() == city.lower()
    ]
    
    if not filtered_doctors:
        return {"success": False, "message": f"No {specialty} found in {city}."}
        
    # 2. Rank the doctors
    ranked_doctors = rank_doctors(filtered_doctors)
    
    # 3. Find first match
    for date_str in sorted(potential_dates): # Check earliest date first
        try:
            appt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            day_of_week = appt_date.strftime("%A").lower() # e.g., "monday"
        except ValueError:
            continue # Skip invalid dates from LLM

        for doctor in ranked_doctors:
            doc_days = doctor.get("working days", "").lower()
            
            # Check if the doctor works on that day
            if day_of_week in doc_days:
                # Found a match! Book it.
                booked = book_appointment(user_id, doctor, patient_details, date_str)
                if booked:
                    return {
                        "success": True,
                        "doctor_name": doctor["Name"],
                        "hospital": doctor["hospital/clinic"],
                        "date": date_str
                    }
                else:
                    # Booking failed at the DB level
                    return {"success": False, "message": "Found a doctor, but failed to save the appointment to the database."}
            
            # Handle "monday - friday"
            if "monday - friday" in doc_days and day_of_week not in ["saturday", "sunday"]:
                booked = book_appointment(user_id, doctor, patient_details, date_str)
                if booked:
                    return {
                        "success": True,
                        "doctor_name": doctor["Name"],
                        "hospital": doctor["hospital/clinic"],
                        "date": date_str
                    }
                else:
                    return {"success": False, "message": "Found a doctor, but failed to save the appointment to the database."}

    # If loop finishes with no match
    return {
        "success": False,
        "message": f"No {specialty} in {city} was available on your preferred dates.",
        "alternatives": ranked_doctors # Return ranked list
    }

def book_appointment(user_id: str, doctor: Dict[str, Any], patient_details: Dict[str, str], date_str: str) -> bool:
    """
    "Books" an appointment by saving it to the database via the AuthService.
    Returns True on success, False on failure.
    """
    try:
        success = st.session_state.auth_service.save_appointment(
            user_id=user_id,
            doctor_id=doctor.get("id"),
            doctor_name=doctor.get("Name"),
            hospital_name=doctor.get("hospital/clinic"), 
            patient_name=patient_details.get("name"),
            patient_email=patient_details.get("email"),
            patient_phone=patient_details.get("phone"),
            preferred_city=doctor.get("city"), # Use doctor's city
            preferred_day=date_str # Use the specific date
        )
        return success
    except Exception as e:
        st.error(f"Failed to call save_appointment: {e}")
        return False
    


def create_calendar_file(doctor_name: str, hospital: str, date_str: str) -> str:
    """
    Creates the content for an .ics calendar file.
    """
    try:
        
        final_doctor_name = doctor_name or "Doctor"
        final_hospital = hospital or "Clinic Appointment"
        
      
        appt_datetime = datetime.strptime(f"{date_str} 09:00", "%Y-%m-%d %H:%M")
        
        
        c = Calendar()
        e = Event()
        
        e.name = f"Appointment with {final_doctor_name}"
        e.location = final_hospital
        
        # Set a specific 1-hour time block
        e.begin = appt_datetime
        e.end = appt_datetime + timedelta(hours=1)
        
        
        alarm = DisplayAlarm(trigger=timedelta(days=-1))
        e.alarms.append(alarm)
        
        c.events.add(e)
        
        # Return the file content as a string
        return str(c)
        
    except Exception as e:
        print(f"Error creating .ics file: {e}")
        return ""

