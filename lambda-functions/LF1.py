import json
import os
import boto3
from datetime import datetime, date

sqs = boto3.client("sqs")

QUEUE_URL = os.environ.get("SQS_QUEUE_URL", "").strip()

ALLOWED_LOCATIONS = {
    "new york", "manhattan", "brooklyn", "queens", "chicago",
    "los angeles", "san francisco", "boston", "seattle", "austin", "miami",
    "nyc", "new york city"
}

ALLOWED_CUISINES = {
    "indian", "chinese", "italian", "mexican", "japanese"
}

NYC_UMBRELLA = {"nyc", "new york city"}

SLOT_ORDER = [
    ("Location",   "Which city are you dining in? (e.g. Manhattan, Brooklyn, Chicago, Miami...)"),
    ("Cuisine",    "What cuisine would you like? (Indian/Chinese/Italian/Mexican/Japanese)"),
    ("DiningDate", "What date would you like to dine?"),
    ("DiningTime", "What time would you like to dine?"),
    ("NumPeople",  "How many people are in your party?"),
    ("Email",      "What email should I send the suggestions to?")
]


# ---------- Lex V2 Helpers ----------
def slot_value(slots, name):
    s = (slots or {}).get(name)
    if not s:
        return None
    v = s.get("value")
    if not v:
        return None
    return v.get("interpretedValue") or v.get("originalValue")


def close(intent_name, message, state="Fulfilled", session_attrs=None):
    return {
        "sessionState": {
            "sessionAttributes": session_attrs or {},
            "dialogAction": {"type": "Close"},
            "intent": {"name": intent_name, "state": state}
        },
        "messages": [{"contentType": "PlainText", "content": message}]
    }


def elicit_slot(intent_obj, slot_to_elicit, message, session_attrs=None):
    return {
        "sessionState": {
            "sessionAttributes": session_attrs or {},
            "dialogAction": {"type": "ElicitSlot", "slotToElicit": slot_to_elicit},
            "intent": intent_obj
        },
        "messages": [{"contentType": "PlainText", "content": message}]
    }


def delegate(intent_obj, session_attrs=None):
    return {
        "sessionState": {
            "sessionAttributes": session_attrs or {},
            "dialogAction": {"type": "Delegate"},
            "intent": intent_obj
        }
    }


# ---------- Location Normalization ----------
def normalize_location(location):
    if not location:
        return None
    loc = location.strip().lower()
    if loc in NYC_UMBRELLA:
        return "nyc"
    if loc in ALLOWED_LOCATIONS:
        return loc
    return None


# ---------- Validation ----------
def validate_inputs(location, cuisine, dining_date, num_people, email):
    # Location check
    if location:
        if normalize_location(location) is None:
            return ("Location",
                    f"Sorry, we cannot fulfill requests for {location.title()}. "
                    f"Please enter a valid location: New York, Manhattan, Brooklyn, Queens, Chicago, "
                    f"Los Angeles, San Francisco, Boston, Seattle, Austin, or Miami.")

    # Cuisine check
    if cuisine:
        if cuisine.strip().lower() not in ALLOWED_CUISINES:
            return ("Cuisine",
                    f"Sorry, we don't have {cuisine} restaurants. "
                    f"Please choose from: Indian, Chinese, Italian, Mexican, or Japanese.")

    # Date check — must not be in the past
    if dining_date:
        try:
            parsed_date = datetime.strptime(dining_date, "%Y-%m-%d").date()
            if parsed_date < date.today():
                return ("DiningDate",
                        f"Sorry, that date is in the past. Please enter a future date.")
        except ValueError:
            return ("DiningDate",
                    "Sorry, I didn't understand that date. Please enter a valid date (e.g. March 5th).")

    # NumPeople check
    if num_people:
        try:
            n = int(num_people)
            if n < 1 or n > 20:
                return ("NumPeople",
                        "Sorry, party size must be between 1 and 20. How many people are in your party?")
        except Exception:
            return ("NumPeople",
                    "Sorry, that doesn't look like a valid number. Please enter a number (e.g. 2).")

    # Email check
    if email and "@" not in email:
        return ("Email",
                "Sorry, that email looks invalid. Please enter a valid email address.")

    return None


def next_missing_slot(slots):
    for slot_name, prompt in SLOT_ORDER:
        if slot_value(slots, slot_name) is None:
            return slot_name, prompt
    return None, None


# ---------- Main Handler ----------
def lambda_handler(event, context):
    print("FULL EVENT:", json.dumps(event))

    session_state = event.get("sessionState", {}) or {}
    session_attrs = session_state.get("sessionAttributes") or {}

    intent_obj = session_state.get("intent", {}) or {}
    intent_name = intent_obj.get("name", "UnknownIntent")
    slots = intent_obj.get("slots") or {}

    source = event.get("invocationSource")
    print(f"Source: {source}, Intent: {intent_name}, Slots: {json.dumps(slots)}")

    if intent_name == "GreetingIntent":
        return close(intent_name, "Hi! I can recommend restaurants. Say 'restaurant suggestions' to begin.")

    if intent_name == "ThankYouIntent":
        return close(intent_name, "You're welcome! If you need restaurant suggestions, just ask.")

    if intent_name == "HelpingIntent":
        return close(
            intent_name,
            "I can suggest restaurants in cities like Manhattan, Chicago, Miami and more. "
            "Try: 'Find Italian in Manhattan on April 3rd at 8pm for 2 people, email test@example.com'."
        )

    if intent_name != "DiningSuggestionsIntent":
        return close(intent_name, "Try saying 'restaurant suggestions' to get dining recommendations.")

    location   = slot_value(slots, "Location")
    cuisine    = slot_value(slots, "Cuisine")
    diningDate = slot_value(slots, "DiningDate")
    diningTime = slot_value(slots, "DiningTime")
    numPeople  = slot_value(slots, "NumPeople")
    email      = slot_value(slots, "Email")

    print(f"Values — Location: {location}, Cuisine: {cuisine}, Date: {diningDate}, Time: {diningTime}, People: {numPeople}, Email: {email}")

    if source == "DialogCodeHook":
        violated = validate_inputs(location, cuisine, diningDate, numPeople, email)
        if violated:
            slot_name, msg = violated
            return elicit_slot(intent_obj, slot_name, msg, session_attrs)

        slot_to_ask, prompt = next_missing_slot(slots)
        if slot_to_ask:
            return elicit_slot(intent_obj, slot_to_ask, prompt, session_attrs)

        return delegate(intent_obj, session_attrs)

    if source == "FulfillmentCodeHook":
        if not QUEUE_URL:
            return close(intent_name, "Server misconfiguration: SQS_QUEUE_URL is missing.")

        conf_state = intent_obj.get("confirmationState")
        if conf_state == "Denied":
            return close(intent_name, "No worries — request cancelled. Feel free to start over.")

        normalized_location = normalize_location(location)

        payload = {
            "location": normalized_location,
            "cuisine": cuisine,
            "diningDate": diningDate,
            "diningTime": diningTime,
            "numPeople": numPeople,
            "email": email,
            "insertedAtTimestamp": datetime.utcnow().isoformat()
        }

        sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(payload))

        location_display = "NYC" if normalized_location == "nyc" else location.title()

        return close(
            intent_name,
            f"Perfect! I'll email {cuisine} restaurant suggestions in {location_display} "
            f"on {diningDate} at {diningTime} for {numPeople} people to {email} shortly!"
        )

    return close(intent_name, "Something went wrong. Please try again.")