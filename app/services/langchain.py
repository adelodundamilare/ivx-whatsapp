# from app.agents import agents
# from app.models.models import Message
# from app.services.bubble_client import BubbleApiClient
# from app.services.whatsapp import WhatsAppBusinessAPI
# from langchain_openai import ChatOpenAI  # type: ignore
# from langchain.schema import SystemMessage # type: ignore
# import dateparser # type: ignore
# import json

# llm = ChatOpenAI(model="gpt-4", temperature=0.5)

# session_memory = {}

# def store_memory(user_id, key, value):
#     if user_id not in session_memory:
#         session_memory[user_id] = {}
#     session_memory[user_id][key] = value

# def get_memory(user_id, key):
#     return session_memory.get(user_id, {}).get(key, None)

# def extract_details(user_message):
#     """Extracts structured appointment details from user input."""

#     prompt = f"""
#     Extract structured data from the following user message regarding an appointment:

#     - Date (YYYY-MM-DD, or natural language like 'next Monday')
#     - Time (HH:MM AM/PM, or 'morning', 'afternoon')
#     - Location (clinic, hospital, etc.)
#     - Service (doctor specialty)

#     Example Response:
#     {{
#         "date": "2025-03-10",
#         "time": "14:00",
#         "location": "Greenwood Clinic",
#         "service": "Pediatrician"
#     }}

#     User Message: "{user_message}"
#     Extracted Data:
#     """

#     response = llm.invoke([SystemMessage(content=prompt)])

#     try:
#         extracted_data = json.loads(response.content)
#         # Parse natural language dates
#         if "date" in extracted_data:
#             parsed_date = dateparser.parse(extracted_data["date"])
#             if parsed_date:
#                 extracted_data["date"] = parsed_date.strftime("%Y-%m-%d")
#         return extracted_data
#     except:
#         return {}

# def detect_intent(user_message):
#     """Classifies user intent (greeting, booking, editing, etc.)."""

#     prompt = f"""
#     Classify the user's message into one of these intents:
#     - greeting
#     - gratitude
#     - general_inquiry
#     - book_appointment
#     - edit_appointment
#     - cancel_appointment
#     - get_appointment_details
#     - unknown

#     User Message: "{user_message}"
#     Intent:
#     """

#     response = llm.invoke([SystemMessage(content=prompt)])
#     return response.content.strip().lower()

# async def schedule_appointment(user_id):
#     """Finalizes appointment and stores in Bubble.io (Simulated)."""

#     appointment = {
#         "preferred_date": get_memory(user_id, "date"),
#         "preferred_time": get_memory(user_id, "time"),
#         "location": get_memory(user_id, "location"),
#         "service_type": get_memory(user_id, "service"),
#     }

#     if None in appointment.values():
#         return "Some details are missing. Let's confirm the missing ones."

#     await BubbleApiClient().create_appointment(appointment)

#     return f"📅 Appointment Confirmed!\n- Date: {appointment['date']}\n- Time: {appointment['time']}\n- Location: {appointment['location']}\n- Service: {appointment['service']}"

# def edit_appointment(user_id, field, new_value):
#     """Edits appointment details."""
#     if field not in ["date", "time", "location", "service"]:
#         return "Invalid field. You can edit date, time, location, or service."
#     store_memory(user_id, field, new_value)
#     return f"Your appointment {field} has been updated to {new_value}."

# def cancel_appointment(user_id):
#     """Cancels the user's appointment."""
#     session_memory.pop(user_id, None)
#     return "Your appointment has been canceled successfully."


# def send_notification(user_id, message):
#     """Simulated notification (FastAPI background task)."""
#     print(f"🔔 Sending Notification to {user_id}: {message}")

# async def orchestrator(message: Message):

#     intent = detect_intent(message)
#     user_id = message.phone_number
#     whatsapp_service = WhatsAppBusinessAPI(message)
#     conversation_history = get_memory(user_id, key='conversation_history') or []
#     store_memory(user_id, 'conversation_history', conversation_history.append({'user':message.content}))

#     if intent == "book_appointment":
#         extracted_data = extract_details(message)
#         for key, value in extracted_data.items():
#             store_memory(user_id, key, value)

#         if all(field in extracted_data for field in ["date", "time", "location", "service"]):
#             res = await schedule_appointment(user_id)
#             return await whatsapp_service.send_text_message(res)

#         # await whatsapp_service.send_text_message("Let's start your appointment booking. What date are you looking for?")

#     if intent == "edit_appointment":
#         return "What would you like to change? (date, time, location, service)"

#     if intent == "cancel_appointment":
#         return cancel_appointment(user_id)

#     if intent == "get_appointment_details":
#         return str(session_memory.get(user_id, "No appointment found."))

#     response = await agents.generate_generic_response(
#         message=message.content,
#         conversation_history=get_memory(user_id, key='conversation_history')
#     )
#     store_memory(user_id, 'conversation_history', conversation_history.append({'system':response}))
#     await whatsapp_service.send_text_message(response)

# Required installations:
# pip install langchain openai python-dateutil

from langchain.chat_models import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from datetime import datetime, timedelta
import os
import json
from typing import List, Dict, Optional
import asyncio
import random

os.environ["OPENAI_API_KEY"] = "your-api-key-here"

class BubbleDB:
    def __init__(self):
        self.clinics = {
            "clinic1": {"name": "Downtown Clinic", "procedures": ["checkup", "surgery"]},
            "clinic2": {"name": "Uptown Clinic", "procedures": ["checkup", "dental"]}
        }
        self.doctors = {
            "doc1": {"name": "Dr. Smith", "specialties": ["checkup"], "clinic": "clinic1"},
            "doc2": {"name": "Dr. Jones", "specialties": ["surgery"], "clinic": "clinic1"},
            "doc3": {"name": "Dr. Brown", "specialties": ["dental"], "clinic": "clinic2"}
        }
        self.appointments = []

    def save_appointment(self, appointment: Dict):
        self.appointments.append(appointment)
        return True

    def get_available_doctors(self, procedure: str, clinic_id: str) -> List[str]:
        return [did for did, doc in self.doctors.items()
                if procedure in doc["specialties"] and doc["clinic"] == clinic_id]

class Agent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.llm = ChatOpenAI(temperature=0.8, model_name="gpt-3.5-turbo")  # Balanced tone

    async def process(self, task: str, context: List[Dict] = []) -> Dict:
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=f"You are {self.name}, a {self.role}. Maintain a professional yet "
                                "approachable tone, like a helpful colleague. Be clear, concise, and "
                                "warm—avoid overly casual slang or humor unless it fits naturally. "
                                "Adapt your responses to the context and user’s input."),
            *self._convert_context(context),
            HumanMessage(content=f"Task: {task}")
        ])
        response = await self.llm.agenerate([prompt.messages])
        return {
            "agent": self.name,
            "response": response.generations[0][0].text,
            "timestamp": datetime.now().isoformat()
        }

    def _convert_context(self, context: List[Dict]) -> List:
        return [SystemMessage(content=f"Previously, {item['agent']} noted: {item['response']}")
                for item in context]

class IntentAgent(Agent):
    def __init__(self):
        super().__init__("IntentClassifier", "specialist in understanding user requests")
        self.intents = ["book_appointment", "edit_appointment", "cancel_appointment", "general_query"]

    async def classify(self, user_input: str, context: List[Dict]) -> Dict:
        task = f"Determine the user’s intent from: '{user_input}'. Options: " \
               f"{', '.join(self.intents)}. Return only the intent name."
        result = await self.process(task, context)
        return {
            "intent": result["response"].strip(),
            "confidence": random.uniform(0.9, 1.0)  # Simulated confidence
        }

class ClinicAssistant:
    def __init__(self):
        self.db = BubbleDB()
        self.intent_agent = IntentAgent()
        self.scheduler = Agent("Scheduler", "expert in managing appointments")
        self.matcher = Agent("Matcher", "specialist in doctor assignments")
        self.notifier = Agent("Notifier", "coordinator for doctor notifications")
        self.history = []
        self.appointment_data = {}

    async def collect_details(self, user_input: str, retry=False) -> str:
        context = self.history + [{"agent": "User", "response": user_input}]
        task = "Engage the user to gather appointment details (clinic, procedure, date, time). " \
              "Be professional and friendly, offering options like Downtown or Uptown Clinic if " \
              "appropriate. If details are missing, ask a clear follow-up question."
        if retry:
            task += " (The user didn’t provide enough last time—gently prompt for more.)"

        result = await self.scheduler.process(task, context)
        self.history.append(result)

        if any(q in result["response"].lower() for q in ["what", "which", "?"]):
            return result["response"]

        # Simulate parsing
        self.appointment_data = {
            "clinic": "clinic1" if "downtown" in user_input.lower() else "clinic2",
            "procedure": "checkup" if "check" in user_input.lower() else "dental",
            "datetime": (datetime.now() + timedelta(days=1)).strftime("%A, %B %d at 2:00 PM")
        }
        return await self.process_booking()

    async def process_booking(self) -> str:
        match_task = f"Identify an available doctor for a {self.appointment_data['procedure']} " \
                    f"at {self.db.clinics[self.appointment_data['clinic']]['name']}."
        match_result = await self.matcher.process(match_task, self.history)
        self.history.append(match_result)

        doctors = self.db.get_available_doctors(
            self.appointment_data["procedure"],
            self.appointment_data["clinic"]
        )
        if not doctors:
            task = "Inform the user no doctors are available and suggest alternatives " \
                  "(e.g., different procedure or clinic) in a helpful way."
            result = await self.scheduler.process(task, self.history)
            self.history.append(result)
            return result["response"]

        self.appointment_data["doctor"] = random.choice(doctors)

        notify_task = f"Notify {self.db.doctors[self.appointment_data['doctor']]['name']} of a " \
                     f"{self.appointment_data['procedure']} appointment on " \
                     f"{self.appointment_data['datetime']} at " \
                     f"{self.db.clinics[self.appointment_data['clinic']]['name']}."
        notify_result = await self.notifier.process(task, notify_task)
        self.history.append(notify_result)

        self.db.save_appointment(self.appointment_data)

        task = f"Confirm the booking for a {self.appointment_data['procedure']} with " \
               f"{self.db.doctors[self.appointment_data['doctor']]['name']} on " \
               f"{self.appointment_data['datetime']} and ask how else to assist."
        result = await self.scheduler.process(task, self.history)
        self.history.append(result)
        return result["response"]

    async def edit_appointment(self, user_input: str) -> str:
        task = f"Assist with modifying the appointment: {json.dumps(self.appointment_data)}. " \
               f"User request: '{user_input}'. Adjust details as needed and confirm changes."
        result = await self.scheduler.process(task, self.history)
        self.history.append(result)

        if any(x in result["response"].lower() for x in ["cancel", "delete", "remove"]):
            self.appointment_data = {}
            task = "Confirm the cancellation and offer further assistance."
            cancel_result = await self.scheduler.process(task, self.history)
            self.history.append(cancel_result)
            return cancel_result["response"]

        # Simulate a tweak
        if "next week" in user_input.lower():
            self.appointment_data["datetime"] = (datetime.now() + timedelta(days=7)).strftime("%A, %B %d at 2:00 PM")
        return result["response"]

    async def process_input(self, user_input: str) -> str:
        # Dynamic greeting on first interaction
        if not self.history:
            task = "Greet the user warmly and professionally, offering assistance with appointments."
            greeting = await self.scheduler.process(task, self.history)
            self.history.append(greeting)
            return greeting["response"]

        intent_result = await self.intent_agent.classify(user_input, self.history)
        self.history.append({"agent": "IntentClassifier", "response": intent_result["intent"]})
        intent = intent_result["intent"]

        if intent == "book_appointment":
            return await self.collect_details(user_input)
        elif intent == "edit_appointment":
            if not self.appointment_data:
                task = "Note there’s no appointment to edit and suggest booking one."
                result = await self.scheduler.process(task, self.history)
                self.history.append(result)
                return result["response"]
            return await self.edit_appointment(user_input)
        elif intent == "cancel_appointment":
            if not self.appointment_data:
                task = "Inform the user there’s no appointment to cancel and offer help."
                result = await self.scheduler.process(task, self.history)
                self.history.append(result)
                return result["response"]
            self.appointment_data = {}
            task = "Confirm the cancellation and ask how to assist next."
            result = await self.scheduler.process(task, self.history)
            self.history.append(result)
            return result["response"]
        elif intent == "general_query":
            task = f"Respond helpfully to the query: '{user_input}' in a professional manner."
            result = await self.scheduler.process(task, self.history)
            self.history.append(result)
            return result["response"]
        else:
            task = "Politely ask for clarification on the user’s request: '{user_input}'."
            result = await self.scheduler.process(task, self.history)
            self.history.append(result)
            return result["response"]

    def run(self):
        while True:
            user_input = input("\nYou: ")
            if user_input.lower() in ['quit', 'exit']:
                task = "Provide a professional farewell and end the session."
                farewell = asyncio.run(self.scheduler.process(task, self.history))
                print(f"Assistant: {farewell['response']}")
                break

            result = asyncio.run(self.process_input(user_input))
            print(f"Assistant: {result}")