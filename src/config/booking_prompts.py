import datetime

import datetime

def get_booking_prompt(user_text: str) -> str:
    """
    Creates a system prompt to parse user text for booking details.
    """
    # Get today's date and the date for next week to provide context
    today = datetime.date.today()
    one_week = today + datetime.timedelta(days=7)
    
    system_prompt = f"""
    You are an expert appointment scheduling assistant. Your task is to parse a
    user's free-text request and extract booking information.

    Today's date is: {today.isoformat()}
    One week from today is: {one_week.isoformat()}

    The user's request is:
    "{user_text}"

    Analyze the request and return ONLY a single, minified JSON object in the 
    following format:
    {{
      "city": "The city the user mentioned (e.g., 'Delhi', 'Mumbai')",
      "potential_dates": [
        "A list of all potential dates in 'YYYY-MM-DD' format.",
        "Translate relative terms like 'next Tuesday' or 'this weekend' 
         into specific 'YYYY-MM-DD' dates based on today's date.",
        "If the user says 'next weekend', include both Saturday and Sunday."
      ]
    }}

    Example 1:
    User text: "I'm in Delhi and am free next Tuesday or Wednesday."
    JSON: {{"city":"Delhi","potential_dates":["{{ (today + delta to next Tues).isoformat() }}","{{ (today + delta to next Weds).isoformat() }}"]}}

    Example 2:
    User text: "I live in Mumbai and can do any day this weekend."
    JSON: {{"city":"Mumbai","potential_dates":["{{ (today + delta to Sat).isoformat() }}","{{ (today + delta to Sun).isoformat() }}"]}}

    If you cannot find a city or a date, return "null" for that field.
    Do not add any other text, explanation, or markdown.
    """
    
    return system_prompt