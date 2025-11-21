import datetime

def get_medication_prompt(user_text: str) -> str:
    today = datetime.date.today().isoformat()
    
    return f"""
    You are a backend API that converts unstructured text into a JSON array.
    You DO NOT talk. You ONLY return JSON.

    Current Date: {today}

    ### Interpretation Rules:
    - **Identify Medications:** Extract every distinct medication or nickname (e.g., "blue pill").
    - **Infer Standard Times (Crucial):** Map layman routines to 24-hour times:
       - "Morning"/"Breakfast" -> ["08:00"]
       - "Lunch"/"Afternoon" -> ["13:00"]
       - "Dinner"/"Evening" -> ["20:00"]
       - "Bedtime"/"Night" -> ["22:00"]
       - "Twice a day" -> ["09:00", "21:00"]
       - "Three times a day" -> ["09:00", "14:00", "21:00"]
    - **Durations:** Calculate 'end_date' (YYYY-MM-DD) if a duration is given (e.g., "for 7 days"). Otherwise, set to null.
    - **CRITICAL OUTPUT RULE:** Your output must start with '[' and end with ']'. No preamble.

    ### ONE-SHOT EXAMPLE (Follow this format exactly):
    Input: "Take 500mg Crocin twice daily for 3 days, and Aspirin every night."
    Output:
    [
      {{
        "name": "Crocin",
        "dosage": "500mg",
        "frequency": "twice daily",
        "alert_times": ["09:00", "21:00"],
        "end_date": "{ (datetime.date.today() + datetime.timedelta(days=3)).isoformat() }",
        "notes": null
      }},
      {{
        "name": "Aspirin",
        "dosage": null,
        "frequency": "every night",
        "alert_times": ["22:00"],
        "end_date": null,
        "notes": null
      }}
    ]

    ---
    
    ### REAL INPUT:
    "{user_text}"

    ### REAL OUTPUT (JSON Array ONLY):
    """