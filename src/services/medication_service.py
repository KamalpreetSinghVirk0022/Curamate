# services/medication_service.py

import streamlit as st
import json
import re
import uuid
from config.medication_prompts import get_medication_prompt
from ics import Calendar, Event, DisplayAlarm
from ics.grammar.parse import ContentLine # <--- NEW IMPORT REQUIRED
from datetime import datetime, date, time, timedelta

def parse_medication_schedule(user_text: str):
    """
    Uses Groq to parse natural language medication instructions.
    """
    if 'analysis_agent' not in st.session_state:
        st.error("AI analysis agent is not initialized.")
        return None

    model_manager = st.session_state.analysis_agent.model_manager
    system_prompt = get_medication_prompt(user_text)

    result = model_manager.generate_analysis(
        data=user_text,
        system_prompt=system_prompt
    )

    if result["success"]:
        try:
            content = result["content"].strip()
            json_str = None
            
            # 1. Try to find JSON within markdown code fences
            json_match = re.search(r"```json\s*(\[.*\])\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)

            # 2. Try to find a raw JSON array
            json_match = re.search(r"(\[.*\])", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            st.error("AI response was in an invalid format. Please try again.")
            print(f"DEBUG: AI returned: {content}") 
            return None

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            return None
    
    st.error(f"AI analysis failed: {result.get('error')}")
    return None

def create_medication_calendar(med_list: list) -> str:
    """
    Creates a recurring .ics calendar file.
    """
    c = Calendar()
    
    for med in med_list:
        try:
            base_med_name = med.get("name", "Medication")
            dosage = med.get("dosage", "as prescribed")
            
            # 1. Set the end date (End of day)
            end_datetime = None
            if med.get("end_date"):
                d = datetime.strptime(med["end_date"], "%Y-%m-%d").date()
                end_datetime = datetime.combine(d, time(23, 59, 59))
            
            for alert_time_str in med.get("alert_times", []):
                # Parse time
                alert_time = datetime.strptime(alert_time_str, "%H:%M").time()
                display_time = alert_time.strftime("%I:%M %p")
                
                # Combine with today's date (Naive datetime = Floating time)
                start_datetime = datetime.combine(date.today(), alert_time)
                
                e = Event()
                e.name = f"💊 Take: {base_med_name} ({display_time})"
                e.description = f"Dosage: {dosage}"
                e.uid = f"{uuid.uuid4()}@curamate.app"
                e.begin = start_datetime
                e.duration = timedelta(minutes=15) 
                
                # --- FIX: Use ContentLine for RRULE ---
                # Instead of appending a string, we append a proper ContentLine object
                if end_datetime:
                    # Format: YYYYMMDDTHHMMSS
                    until_str = end_datetime.strftime("%Y%m%dT%H%M%S")
                    e.extra.append(ContentLine(name="RRULE", value=f"FREQ=DAILY;UNTIL={until_str}"))
                else:
                    e.extra.append(ContentLine(name="RRULE", value="FREQ=DAILY"))
                # ---------------------------------------
                
                # 30-minute reminder
                alarm = DisplayAlarm(trigger=timedelta(minutes=-30))
                e.alarms.append(alarm)
                
                c.events.add(e)
                
        except Exception as e:
            print(f"Error creating event for {med.get('name')}: {e}")

    return str(c)
