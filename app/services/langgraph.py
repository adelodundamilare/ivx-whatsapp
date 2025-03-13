
import asyncio
import json
import os
import re
from typing import Dict, List, TypedDict
from app.agents.agents import extractor, intent_agent
from app.handler.greet import GreetingHandler
from app.handler.procedure_collector import ProcedureCollector
from app.models.models import ClinicState, Message
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.helpers import get_message_history, invoke_ai, send_response
from app.utils.logger import setup_logger
from app.utils.state_manager import StateManager
from langgraph.graph import StateGraph, START, END # type: ignore
from datetime import datetime, timedelta
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder # type: ignore
import openai
import json
from app.core.config import settings

openai.api_key = settings.OPENAI_API_KEY

logger = setup_logger("langgraph", "langgraph.log")

# llm = ChatOpenAI(model="gpt-4", temperature=0.5)


# LANGUAGES = {
#     "en": {"booked": "✅ Your appointment has been booked!", "updated": "✏️ Your appointment has been updated!", "canceled": "❌ Your appointment has been canceled!", "not_understood": "🤖 I didn't understand your request. Please try again!", "greeting": "👋 Hello! How can I assist you today?", "thanks": "🙏 You're welcome! Let me know if you need anything else."},
#     "es": {"booked": "✅ ¡Tu cita ha sido reservada!", "updated": "✏️ ¡Tu cita ha sido actualizada!", "canceled": "❌ ¡Tu cita ha sido cancelada!", "not_understood": "🤖 No entendí tu solicitud. ¡Por favor, intenta de nuevo!", "greeting": "👋 ¡Hola! ¿En qué puedo ayudarte hoy?", "thanks": "🙏 ¡De nada! Avísame si necesitas algo más."}
# }

# class AssistantState(BaseModel):
#     user_input: str
#     intent: str = "unknown"
#     data: dict = {}
#     language: str = "en"
#     message: str = ""

# class MedicalAssistant:
#     def __init__(self, message: Message):
#         self.message = message
#         self.whatsapp_service = WhatsAppBusinessAPI(message)
#         self.bubble_client = BubbleApiClient()
#         self.build_graph()

#     def build_graph(self):
#         self.graph = Graph()
#         self.graph.add_node("detect_intent", self.intent_task)
#         self.graph.add_node("handle_intent", self.process_intent_task)
#         self.graph.add_edge("detect_intent", "handle_intent")
#         self.graph.set_entry_point("detect_intent")

#     async def intent_task(self, state: AssistantState):
#         response = await llm.ainvoke(state.user_input)
#         try:
#             parsed_response = json.loads(response.content) if isinstance(response.content, str) else {}
#         except json.JSONDecodeError:
#             parsed_response = {}
#         return AssistantState(
#             user_input=state.user_input,
#             intent=parsed_response.get("intent", "unknown"),
#             data=parsed_response.get("data", {}),
#             language=state.language
#         )

#     async def process_intent_task(self, state: AssistantState):
#         extracted_data = state.data
#         language = state.language

#         if state.intent == "greeting":
#             state.message = LANGUAGES[language]["greeting"]
#         elif state.intent == "thanks":
#             state.message = LANGUAGES[language]["thanks"]
#         elif state.intent == "book":
#             await self.bubble_client.book_appointment(extracted_data)
#             state.message = LANGUAGES[language]["booked"]
#         elif state.intent == "edit":
#             await self.bubble_client.edit_appointment(extracted_data)
#             state.message = LANGUAGES[language]["updated"]
#         elif state.intent == "cancel":
#             await self.bubble_client.cancel_appointment(extracted_data)
#             state.message = LANGUAGES[language]["canceled"]
#         elif state.intent == "retrieve":
#             result = await self.bubble_client.get_appointment(extracted_data)
#             state.message = result.get("details", LANGUAGES[language]["not_understood"])
#         else:
#             state.message = LANGUAGES[language]["not_understood"]

#         await self.whatsapp_service.send_text_message(state.message)

#         return AssistantState(
#             user_input=state.user_input,
#             intent=state.intent,
#             data=state.data,
#             language=state.language,
#             message=state.message
#         )

#     async def chat(self, user_input: str, language: str = "en"):
#         state = AssistantState(user_input=user_input, language=language)
#         graph_executor = self.graph.compile()
#         print(state, 'state')
#         async for output in graph_executor.astream(state):
#             state = AssistantState(**output)
#         # await self.whatsapp_service.send_text_message(state.message)






# class BubbleDB:
#     def __init__(self):
#         self.doctors = {
#             "Dr. Smith": {"specialties": ["checkup"], "location": "Downtown", "phone": "whatsapp:+1234567890"},
#             "Dr. Jones": {"specialties": ["surgery"], "location": "Downtown", "phone": "whatsapp:+1234567891"},
#             "Dr. Brown": {"specialties": ["dental"], "location": "Uptown", "phone": "whatsapp:+1234567892"}
#         }
#         self.appointments = []  # {"clinic_phone": "", "patient_name": "", "procedure": "", "doctor": "", "datetime": "", "clinic_location": ""}
#         self.doctor_preferences = {}  # Dynamic mapping if needed

#     def save_appointment(self, appointment):
#         self.appointments.append(appointment)
#         return True

#     def get_doctors_by_location(self, location):
#         return [name for name, info in self.doctors.items()]  # Return all doctors for now (refine later)

#     def find_appointment(self, clinic_phone):
#         return next((appt for appt in self.appointments if appt["clinic_phone"] == clinic_phone), None)

#     def update_appointment(self, clinic_phone, new_details):
#         for i, appt in enumerate(self.appointments):
#             if appt["clinic_phone"] == clinic_phone:
#                 self.appointments[i].update(new_details)
#                 return True
#         return False

#     def cancel_appointment(self, clinic_phone):
#         for i, appt in enumerate(self.appointments):
#             if appt["clinic_phone"] == clinic_phone:
#                 del self.appointments[i]
#                 return True
#         return False

# class ClinicState(TypedDict):
#     user_input: str
#     intent: str
#     intent_confidence: float
#     appointment: dict
#     messages: Annotated[List[dict], operator.add]
#     needs_clarification: bool
#     conversation_step: str
#     clinic_phone: str
#     clinic_info: dict  # {"name": str, "clinic": str}
#     doctor_index: int
#     clarification_attempts: int

# class ClinicAssistant:
#     def __init__(self, message: Message):
#         self.db = BubbleDB()
#         self.user_states = {}
#         self.message = message
#         self.whatsapp_service = WhatsAppBusinessAPI(message)
#         self.graph = self._build_graph()

#     def _get_safe_state(self, state: ClinicState, key: str, default=None):
#         return state.get(key, default) if state else default

#     def _get_clinic_info(self, state: ClinicState, key: str, default: str = "") -> str:
#         return state.get("clinic_info", {}).get(key, default)

#     async def _call_openai(self, prompt: str, system_msg: str = "You're a professional, friendly AI assistant (AIA) helping clinics connect with doctors for patient bookings.") -> str:
#         try:
#             response = openai_service.create_agent_completion(
#                 messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
#             )
#             logger.info(f"OpenAI response: {response}")
#             return response
#         except Exception as e:
#             logger.error(f"OpenAI error: {str(e)}")
#             return f"Error: {str(e)}"

#     async def _send_whatsapp_message(self, to_phone: str, message: str) -> bool:
#         await self.whatsapp_service.send_text_message(message=message, to_number=to_phone)

#     # Node Methods
#     async def greet(self, state: ClinicState) -> ClinicState:
#         messages = self._get_safe_state(state, "messages", [])
#         user_input = self._get_safe_state(state, "user_input", "").lower()
#         clinic_name = self._get_clinic_info(state, "name")
#         clinic_location = self._get_clinic_info(state, "clinic")

#         if not messages:
#             if not clinic_name or not clinic_location:
#                 if user_input and user_input not in ["hi", "hey", "hello", "just checking this out"]:
#                     prompt = f"Extract clinic staff name and clinic location from: '{user_input}'. " \
#                              f"Return JSON: {{'name': '...', 'clinic': '...'}}, leave clinic empty if unclear."
#                     try:
#                         details = json.loads(await self._call_openai(prompt))
#                         extracted_name = details.get("name", "").strip()
#                         extracted_clinic = details.get("clinic", "").strip()

#                         if not extracted_name and not extracted_clinic:
#                             prompt = "I couldn't understand your input. Please provide your name and your clinic's location so I can assist you."
#                             response = await self._call_openai(prompt)
#                             return {
#                                 "messages": [{"role": "assistant", "content": response}],
#                                 "needs_clarification": True,
#                                 "conversation_step": "greet"
#                             }
#                         elif not extracted_clinic:
#                             prompt = f"I got your name as {extracted_name}, but couldn't determine your clinic's location. Please provide your clinic's location."
#                             response = await self._call_openai(prompt)
#                             return {
#                                 "messages": [{"role": "assistant", "content": response}],
#                                 "needs_clarification": True,
#                                 "conversation_step": "greet",
#                                 "clinic_info": {"name": extracted_name, "clinic": ""}
#                             }
#                         elif not extracted_name:
#                             prompt = f"I got your clinic location as {extracted_clinic}, but couldn't determine your name. Please provide your name."
#                             response = await self._call_openai(prompt)
#                             return {
#                                 "messages": [{"role": "assistant", "content": response}],
#                                 "needs_clarification": True,
#                                 "conversation_step": "greet",
#                                 "clinic_info": {"name": "", "clinic": extracted_clinic}
#                             }

#                         state["clinic_info"] = {"name": extracted_name, "clinic": extracted_clinic}
#                         prompt = f"Hello {extracted_name}! I'm AIA, your assistant to connect {extracted_clinic} with doctors for patient bookings. How can I assist you today?"
#                         response = await self._call_openai(prompt)
#                         return {
#                             "messages": [{"role": "assistant", "content": response}],
#                             "needs_clarification": False,
#                             "conversation_step": "greet",
#                             "clinic_info": state["clinic_info"]
#                         }
#                     except json.JSONDecodeError:
#                         prompt = "I couldn't process your input. Please provide your name and your clinic's location so I can assist you."
#                         response = await self._call_openai(prompt)
#                         return {
#                             "messages": [{"role": "assistant", "content": response}],
#                             "needs_clarification": True,
#                             "conversation_step": "greet"
#                         }
#                 else:
#                     prompt = "Hello! I'm AIA, your assistant to help clinics connect with doctors for patient bookings. Please provide your name and your clinic's location."
#                     response = await self._call_openai(prompt)
#                     return {
#                         "messages": [{"role": "assistant", "content": response}],
#                         "needs_clarification": True,
#                         "conversation_step": "greet"
#                     }

#             prompt = f"Hello {clinic_name}! I'm AIA, your assistant to connect {clinic_location} with doctors for patient bookings. How can I assist you today?"
#             response = await self._call_openai(prompt)
#             return {
#                 "messages": [{"role": "assistant", "content": response}],
#                 "needs_clarification": False,
#                 "conversation_step": "greet"
#             }
#         return state

#     async def classify_intent(self, state: ClinicState) -> ClinicState:
#         user_input = self._get_safe_state(state, "user_input", "")
#         clinic_name = self._get_clinic_info(state, "name")
#         clinic_location = self._get_clinic_info(state, "clinic")

#         if not clinic_name or not clinic_location:
#             prompt = "The clinic staff hasn't provided their name or location yet. Politely ask them to provide their name and clinic location."
#             response = await self._call_openai(prompt)
#             return {
#                 "messages": [{"role": "assistant", "content": response}],
#                 "needs_clarification": True,
#                 "conversation_step": "classify",
#                 "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
#             }

#         prompt = f"Classify the intent of: '{user_input}' and determine if clarification is needed. " \
#                  f"Options: book_doctor, edit_appointment, cancel_appointment, check_appointment_status. " \
#                  f"Return valid JSON: {{'intent': '...', 'confidence': 0.0-1.0, 'needs_clarification': true/false}}. " \
#                  f"If the input is vague (e.g., 'hi', 'just checking'), set confidence low and request clarification. " \
#                  f"Recognize 'i have an appointment i want to terminate' as 'cancel_appointment'."
#         try:
#             result = json.loads(await self._call_openai(prompt))
#             intent = result.get("intent", "book_doctor")
#             confidence = result.get("confidence", 0.0)
#             needs_clarification = result.get("needs_clarification", confidence < 0.75)
#             if confidence < 0.75 or needs_clarification:
#                 prompt = f"Clinic input was unclear: '{user_input}'. Ask for clarification politely based on intent '{intent}'."
#                 response = await self._call_openai(prompt)
#                 return {
#                     "messages": [{"role": "assistant", "content": response}],
#                     "intent": intent,
#                     "intent_confidence": confidence,
#                     "needs_clarification": True,
#                     "conversation_step": "classify",
#                     "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
#                 }
#             return {
#                 "intent": intent,
#                 "intent_confidence": confidence,
#                 "needs_clarification": needs_clarification,
#                 "conversation_step": "classify",
#                 "clarification_attempts": 0
#             }
#         except json.JSONDecodeError as e:
#             logger.error(f"JSON parsing failed: {e}")
#             return {
#                 "messages": [{"role": "assistant", "content": "I'm having trouble understanding. Please clarify your request."}],
#                 "needs_clarification": True,
#                 "conversation_step": "classify",
#                 "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
#             }

#     async def create_appointment(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         clinic_location = self._get_clinic_info(state, "clinic")
#         clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)

#         if not clinic_name or not clinic_location:
#             try:
#                 prompt = f"Extract clinic staff name and location from: '{state['user_input']}'. Return JSON: {{'name': '...', 'clinic': '...'}}, leave clinic empty if unclear."
#                 details = json.loads(await self._call_openai(prompt))
#                 state["clinic_info"] = {"name": details.get("name", ""), "clinic": details.get("clinic", "")}
#                 if not details.get("name"):
#                     prompt = "I couldn't get your name. Could you please provide it so I can assist with patient bookings?"
#                     response = await self._call_openai(prompt)
#                     return {
#                         "messages": [{"role": "assistant", "content": response}],
#                         "needs_clarification": True,
#                         "conversation_step": "create_appointment",
#                         "clarification_attempts": clarification_attempts + 1
#                     }
#             except json.JSONDecodeError:
#                 prompt = "I couldn't identify your info. Please provide your name and clinic location."
#                 response = await self._call_openai(prompt)
#                 return {
#                     "messages": [{"role": "assistant", "content": response}],
#                     "needs_clarification": True,
#                     "conversation_step": "create_appointment",
#                     "clarification_attempts": clarification_attempts + 1
#                 }

#         appointment = self._get_safe_state(state, "appointment", {})
#         if not appointment.get("procedure") or not appointment.get("patient_name"):
#             prompt = f"Ask {clinic_name} staff from {clinic_location} for the patient's name and the procedure (e.g., checkup, surgery, dental) they need a doctor for."
#             response = await self._call_openai(prompt)
#             return {
#                 "messages": [{"role": "assistant", "content": response}],
#                 "needs_clarification": True,
#                 "conversation_step": "create_appointment",
#                 "clarification_attempts": clarification_attempts + 1
#             }

#         try:
#             prompt = f"Extract patient name and procedure from: '{state['user_input']}'. Return JSON: {{'patient_name': '...', 'procedure': '...'}}, default procedure to 'checkup' if unclear."
#             details = json.loads(await self._call_openai(prompt))
#             procedure = details.get("procedure", "checkup")
#             patient_name = details.get("patient_name", "")
#             if not patient_name:
#                 prompt = "I couldn't get the patient's name. Could you please provide it?"
#                 response = await self._call_openai(prompt)
#                 return {
#                     "messages": [{"role": "assistant", "content": response}],
#                     "needs_clarification": True,
#                     "conversation_step": "create_appointment",
#                     "clarification_attempts": clarification_attempts + 1
#                 }
#             state["appointment"]["procedure"] = procedure
#             state["appointment"]["patient_name"] = patient_name
#             return {"appointment": state["appointment"], "needs_clarification": False, "conversation_step": "create_appointment"}
#         except json.JSONDecodeError:
#             prompt = "I couldn't identify the procedure or patient name. Please specify (e.g., 'checkup for John Doe')."
#             response = await self._call_openai(prompt)
#             return {
#                 "messages": [{"role": "assistant", "content": response}],
#                 "needs_clarification": True,
#                 "conversation_step": "create_appointment",
#                 "clarification_attempts": clarification_attempts + 1
#             }

#     async def collect_edit(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         existing_appt = self.db.find_appointment(state["clinic_phone"])
#         if not existing_appt:
#             prompt = f"Inform {clinic_name} staff that no patient appointment exists to edit and suggest booking one."
#             response = await self._call_openai(prompt)
#             return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "collect_edit"}

#         prompt = f"Ask {clinic_name} staff what they'd like to change about the patient's appointment: " \
#                  f"{existing_appt['procedure']} for {existing_appt['patient_name']} with {existing_appt['doctor']} at {existing_appt['clinic_location']} on {existing_appt['datetime']} " \
#                  f"(e.g., procedure, date/time, or doctor)."
#         response = await self._call_openai(prompt)
#         return {
#             "messages": [{"role": "assistant", "content": response}],
#             "needs_clarification": True,
#             "conversation_step": "collect_edit",
#             "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
#         }

#     async def process_edit(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         clinic_location = self._get_clinic_info(state, "clinic")
#         existing_appt = self.db.find_appointment(state["clinic_phone"])
#         if not existing_appt:
#             return {"messages": [{"role": "assistant", "content": "No patient appointment found to edit."}], "conversation_step": "process_edit"}

#         try:
#             prompt = f"Extract changes from: '{state['user_input']}' for appointment: {json.dumps(existing_appt)}. " \
#                      f"Return JSON: {{'procedure': '...', 'datetime': '...', 'doctor': '...'}}, use existing values if not specified."
#             changes = json.loads(await self._call_openai(prompt))
#             new_procedure = changes.get("procedure", existing_appt["procedure"])
#             new_datetime = changes.get("datetime", existing_appt["datetime"])
#             new_doctor = changes.get("doctor", existing_appt["doctor"])

#             self.db.update_appointment(state["clinic_phone"], {"procedure": new_procedure, "datetime": new_datetime, "doctor": new_doctor})
#             prompt = f"Confirm to {clinic_name} staff that the patient's appointment is updated to {new_procedure} " \
#                      f"for {existing_appt['patient_name']} with {new_doctor} at {clinic_location} on {new_datetime}."
#             response = await self._call_openai(prompt)
#             await self._send_whatsapp_message(self.db.doctors[new_doctor]["phone"], response)
#             return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "process_edit"}
#         except json.JSONDecodeError:
#             return {
#                 "messages": [{"role": "assistant", "content": "I couldn't understand the changes. Please specify (e.g., procedure, date/time, doctor)."}],
#                 "needs_clarification": True,
#                 "conversation_step": "process_edit",
#                 "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
#             }

#     async def cancel_appointment(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         existing_appt = self.db.find_appointment(state["clinic_phone"])
#         if not existing_appt:
#             prompt = f"Inform {clinic_name} staff that no patient appointment exists to cancel."
#             response = await self._call_openai(prompt)
#             return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "cancel_appointment"}

#         prompt = f"Ask {clinic_name} staff to confirm cancellation of the patient's {existing_appt['procedure']} " \
#                  f"for {existing_appt['patient_name']} with {existing_appt['doctor']} at {existing_appt['clinic_location']} on {existing_appt['datetime']} (yes/no)."
#         response = await self._call_openai(prompt)
#         return {
#             "messages": [{"role": "assistant", "content": response}],
#             "needs_clarification": True,
#             "conversation_step": "cancel_appointment",
#             "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
#         }

#     async def process_cancel(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         existing_appt = self.db.find_appointment(state["clinic_phone"])
#         if not existing_appt:
#             return {"messages": [{"role": "assistant", "content": "No patient appointment found to cancel."}], "conversation_step": "process_cancel"}

#         try:
#             prompt = f"Determine if '{state['user_input']}' indicates confirmation (yes) or not (no). Return JSON: {{'confirmed': true/false}}."
#             result = json.loads(await self._call_openai(prompt))
#             confirmed = result.get("confirmed", False)
#         except json.JSONDecodeError:
#             return {
#                 "messages": [{"role": "assistant", "content": "Please respond with 'yes' or 'no' to confirm."}],
#                 "needs_clarification": True,
#                 "conversation_step": "process_cancel",
#                 "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
#             }

#         if confirmed:
#             self.db.cancel_appointment(state["clinic_phone"])
#             prompt = f"Confirm to {clinic_name} staff that the patient's appointment with {existing_appt['doctor']} " \
#                      f"at {existing_appt['clinic_location']} on {existing_appt['datetime']} for {existing_appt['patient_name']} has been cancelled."
#             response = await self._call_openai(prompt)
#             await self._send_whatsapp_message(self.db.doctors[existing_appt["doctor"]]["phone"], response)
#             return {"messages": [{"role": "assistant", "content": response}], "appointment": {}, "conversation_step": "process_cancel"}
#         return {"messages": [{"role": "assistant", "content": "Cancellation aborted. How else can I assist with patient bookings?"}], "conversation_step": "process_cancel"}

#     async def check_appointment_status(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         clinic_location = self._get_clinic_info(state, "clinic")
#         existing_appt = self.db.find_appointment(state["clinic_phone"])
#         if not existing_appt:
#             prompt = f"Inform {clinic_name} staff that no patient appointment is currently scheduled at {clinic_location}."
#         else:
#             prompt = f"Report to {clinic_name} staff the status of the patient's appointment: " \
#                      f"{existing_appt['procedure']} for {existing_appt['patient_name']} with {existing_appt['doctor']} at {clinic_location} on {existing_appt['datetime']}."
#         response = await self._call_openai(prompt)
#         return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "check_appointment_status"}

#     async def initiate_doctor_search(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         clinic_location = self._get_clinic_info(state, "clinic")
#         appointment = self._get_safe_state(state, "appointment", {})
#         prompt = f"Thank {clinic_name} staff from {clinic_location} for providing the procedure ({appointment.get('procedure', '')}) " \
#                  f"for patient {appointment.get('patient_name', '')} and inform them that you'll look for an available doctor and get back to them."
#         response = await self._call_openai(prompt)
#         return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "initiate_doctor_search", "doctor_index": 0}

#     async def prompt_doctors(self, state: ClinicState) -> ClinicState:
#         clinic_location = self._get_clinic_info(state, "clinic")
#         appointment = self._get_safe_state(state, "appointment", {})
#         doctors = self.db.get_doctors_by_location(clinic_location)
#         doctor_index = self._get_safe_state(state, "doctor_index", 0)
#         if doctor_index >= len(doctors):
#             prompt = f"Inform the clinic staff that no doctors are currently available for {appointment.get('procedure', '')} " \
#                      f"at {clinic_location} and suggest contacting the clinic directly or trying another procedure."
#             response = await self._call_openai(prompt)
#             return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "prompt_doctors"}

#         doctor = doctors[doctor_index]
#         prompt = f"Ask {doctor} if they're available for a {appointment.get('procedure', '')} at {clinic_location} " \
#                  f"on {appointment.get('datetime', (datetime.now() + timedelta(days=2)).strftime('%A, %B %d at 2:00 PM'))} for patient {appointment.get('patient_name', '')}. Request a yes/no response."
#         doctor_response = await self._call_openai(prompt)
#         await self._send_whatsapp_message(self.db.doctors[doctor]["phone"], doctor_response)

#         accepted = random.choice([True, False])
#         if accepted:
#             state["appointment"]["doctor"] = doctor
#             state["appointment"]["datetime"] = appointment.get("datetime", (datetime.now() + timedelta(days=2)).strftime("%A, %B %d at 2:00 PM"))
#             return {"appointment": state["appointment"], "conversation_step": "prompt_doctors"}
#         return {"doctor_index": doctor_index + 1, "conversation_step": "prompt_doctors"}

#     async def propose_doctor(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         appointment = self._get_safe_state(state, "appointment", {})
#         prompt = f"Propose to {clinic_name} staff that {appointment.get('doctor', '')} is available " \
#                  f"for a {appointment.get('procedure', '')} for patient {appointment.get('patient_name', '')} at {self._get_clinic_info(state, 'clinic')} " \
#                  f"on {appointment.get('datetime', '')}. Ask for confirmation (yes/no)."
#         response = await self._call_openai(prompt)
#         return {"messages": [{"role": "assistant", "content": response}], "needs_clarification": True, "conversation_step": "propose_doctor"}

#     async def confirm_appointment(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         clinic_location = self._get_clinic_info(state, "clinic")
#         appointment = self._get_safe_state(state, "appointment", {})
#         try:
#             prompt = f"Determine if '{state['user_input']}' indicates acceptance (yes) or rejection (no). Return JSON: {{'accepted': true/false}}."
#             result = json.loads(await self._call_openai(prompt))
#             accepted = result.get("accepted", False)
#         except json.JSONDecodeError:
#             return {
#                 "messages": [{"role": "assistant", "content": "Please respond with 'yes' or 'no' to confirm."}],
#                 "needs_clarification": True,
#                 "conversation_step": "confirm_appointment",
#                 "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
#             }

#         if accepted:
#             self.db.save_appointment({"clinic_phone": state["clinic_phone"], **appointment, "clinic_location": clinic_location})
#             prompt = f"Confirm to {clinic_name} staff that the {appointment.get('procedure', '')} for {appointment.get('patient_name', '')} " \
#                      f"with {appointment.get('doctor', '')} at {clinic_location} on {appointment.get('datetime', '')} is scheduled. " \
#                      f"Notify them a reminder will be sent 1 day before."
#             response = await self._call_openai(prompt)
#             await self._send_whatsapp_message(self.db.doctors[appointment["doctor"]]["phone"], response)
#             asyncio.create_task(self._schedule_reminder(state["clinic_phone"], appointment, clinic_location))
#             return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "confirm_appointment"}
#         prompt = "Inform the clinic staff that you'll look for another available doctor and proceed."
#         response = await self._call_openai(prompt)
#         return {"messages": [{"role": "assistant", "content": response}], "doctor_index": self._get_safe_state(state, "doctor_index", 0) + 1, "conversation_step": "prompt_doctors"}

#     async def wrap_up(self, state: ClinicState) -> ClinicState:
#         clinic_name = self._get_clinic_info(state, "name")
#         prompt = f"Ask {clinic_name} staff if there's anything else they need help with for patient bookings before ending the session."
#         response = await self._call_openai(prompt)
#         logger.info(f"Wrap up response: {response}")
#         return {
#             "messages": [{"role": "assistant", "content": response}],
#             "needs_clarification": False,
#             "conversation_step": "wrap_up"
#         }

#     async def handle_error(self, state: ClinicState) -> ClinicState:
#         prompt = "An error occurred. Apologize politely to the clinic staff and inform them that the process couldn't be completed. Suggest trying again later or contacting support if the issue persists."
#         response = await self._call_openai(prompt)
#         logger.info(f"Error node reached: {state}")
#         return {
#             "messages": [{"role": "assistant", "content": response}],
#             "needs_clarification": False,
#             "conversation_step": "error"
#         }

#     async def _schedule_reminder(self, clinic_phone: str, appointment: dict, clinic_location: str):
#         wait_time = (datetime.strptime(appointment["datetime"], "%A, %B %d at 2:00 PM") - timedelta(days=1) - datetime.now()).total_seconds()
#         if wait_time > 0:
#             await asyncio.sleep(wait_time)
#             prompt = f"Remind {self._get_clinic_info(self.user_states.get(clinic_phone, {}), 'name')} staff and {appointment['doctor']} " \
#                      f"about the {appointment['procedure']} for {appointment['patient_name']} at {clinic_location} on {appointment['datetime']}."
#             response = await self._call_openai(prompt)
#             await self._send_whatsapp_message(clinic_phone, response)
#             await self._send_whatsapp_message(self.db.doctors[appointment["doctor"]]["phone"], response)

#     # Routing Methods
#     def _route_after_greet(self, state: ClinicState) -> str:
#         needs_clarification = self._get_safe_state(state, "needs_clarification", False)
#         user_input = self._get_safe_state(state, "user_input", "")
#         clinic_name = self._get_clinic_info(state, "name")
#         clinic_location = self._get_clinic_info(state, "clinic")

#         logger.info(f"Routing after greet: needs_clarification={needs_clarification}, user_input='{user_input}', clinic_info={{'name': '{clinic_name}', 'clinic': '{clinic_location}'}}")

#         if needs_clarification:
#             logger.info("Ending graph to wait for clinic info")
#             return END

#         logger.info("Proceeding to classify intent with clinic info")
#         return "classify"

#     def _route_after_classify(self, state: ClinicState) -> str:
#         if self._get_safe_state(state, "needs_clarification", False) and self._get_safe_state(state, "clarification_attempts", 0) < 3:
#             return "create_appointment" if self._get_safe_state(state, "intent") == "book_doctor" else self._get_safe_state(state, "intent", "error")
#         intent = self._get_safe_state(state, "intent", "book_doctor")
#         return {
#             "book_doctor": "create_appointment",
#             "edit_appointment": "collect_edit",
#             "cancel_appointment": "cancel_appointment",
#             "check_appointment_status": "check_appointment_status"
#         }.get(intent, "error")

#     def _route_after_create_appointment(self, state: ClinicState) -> str:
#         clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
#         if self._get_safe_state(state, "needs_clarification", False) and clarification_attempts >= 3:
#             return "error"
#         return "initiate_doctor_search" if not self._get_safe_state(state, "needs_clarification", False) else "create_appointment"

#     def _route_after_collect_edit(self, state: ClinicState) -> str:
#         clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
#         if self._get_safe_state(state, "needs_clarification", False) and clarification_attempts >= 3:
#             return "error"
#         return "process_edit" if not self._get_safe_state(state, "needs_clarification", False) else "collect_edit"

#     def _route_after_process_edit(self, state: ClinicState) -> str:
#         return "wrap_up"

#     def _route_after_cancel_appointment(self, state: ClinicState) -> str:
#         clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
#         if self._get_safe_state(state, "needs_clarification", False) and clarification_attempts >= 3:
#             return "error"
#         return "process_cancel" if not self._get_safe_state(state, "needs_clarification", False) else "cancel_appointment"

#     def _route_after_process_cancel(self, state: ClinicState) -> str:
#         return "wrap_up"

#     def _route_after_check_appointment_status(self, state: ClinicState) -> str:
#         return "wrap_up"

#     def _route_after_initiate(self, state: ClinicState) -> str:
#         return "prompt_doctors"

#     def _route_after_prompt(self, state: ClinicState) -> str:
#         return "propose_doctor" if self._get_safe_state(state, "appointment", {}).get("doctor") else "prompt_doctors"

#     def _route_after_propose(self, state: ClinicState) -> str:
#         clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
#         if self._get_safe_state(state, "needs_clarification", False) and clarification_attempts >= 3:
#             return "error"
#         return "confirm_appointment" if self._get_safe_state(state, "needs_clarification", False) else "prompt_doctors"

#     def _route_after_confirm(self, state: ClinicState) -> str:
#         return "wrap_up" if not self._get_safe_state(state, "needs_clarification", False) else "confirm_appointment"

#     def _route_after_action(self, state: ClinicState) -> str:
#         clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
#         needs_clarification = self._get_safe_state(state, "needs_clarification", False)
#         conversation_step = self._get_safe_state(state, "conversation_step", "")

#         logger.info(f"Routing after action: step={conversation_step}, needs_clarification={needs_clarification}, attempts={clarification_attempts}")

#         if conversation_step == "error":
#             logger.info("Exiting graph from error node")
#             return END

#         if needs_clarification and clarification_attempts >= 3:
#             logger.info("Routing to error due to max clarification attempts")
#             return "error"

#         if needs_clarification:
#             logger.info("Routing back to create_appointment for clarification")
#             return "create_appointment"

#         logger.info("No clarification needed, ending graph")
#         return END

#     def _build_graph(self) -> StateGraph:
#         workflow = StateGraph(ClinicState)
#         workflow.add_node("greet", self.greet)
#         workflow.add_node("classify", self.classify_intent)
#         workflow.add_node("create_appointment", self.create_appointment)
#         workflow.add_node("collect_edit", self.collect_edit)
#         workflow.add_node("process_edit", self.process_edit)
#         workflow.add_node("cancel_appointment", self.cancel_appointment)
#         workflow.add_node("process_cancel", self.process_cancel)
#         workflow.add_node("check_appointment_status", self.check_appointment_status)
#         workflow.add_node("initiate_doctor_search", self.initiate_doctor_search)
#         workflow.add_node("prompt_doctors", self.prompt_doctors)
#         workflow.add_node("propose_doctor", self.propose_doctor)
#         workflow.add_node("confirm_appointment", self.confirm_appointment)
#         workflow.add_node("wrap_up", self.wrap_up)
#         workflow.add_node("error", self.handle_error)

#         workflow.set_entry_point("greet")
#         workflow.add_conditional_edges("greet", self._route_after_greet)
#         workflow.add_conditional_edges("classify", self._route_after_classify)
#         workflow.add_conditional_edges("create_appointment", self._route_after_create_appointment)
#         workflow.add_conditional_edges("collect_edit", self._route_after_collect_edit)
#         workflow.add_conditional_edges("process_edit", self._route_after_process_edit)
#         workflow.add_conditional_edges("cancel_appointment", self._route_after_cancel_appointment)
#         workflow.add_conditional_edges("process_cancel", self._route_after_process_cancel)
#         workflow.add_conditional_edges("check_appointment_status", self._route_after_check_appointment_status)
#         workflow.add_conditional_edges("initiate_doctor_search", self._route_after_initiate)
#         workflow.add_conditional_edges("prompt_doctors", self._route_after_prompt)
#         workflow.add_conditional_edges("propose_doctor", self._route_after_propose)
#         workflow.add_conditional_edges("confirm_appointment", self._route_after_confirm)
#         workflow.add_conditional_edges("wrap_up", self._route_after_action)
#         workflow.add_conditional_edges("error", self._route_after_action)

#         return workflow.compile()

#     async def process_message(self, user_input: str, clinic_phone: str) -> str:
#         state = self.user_states.get(clinic_phone, ClinicState(
#             user_input="", intent="", intent_confidence=0.0, appointment={}, messages=[],
#             needs_clarification=False, conversation_step="", clinic_phone=clinic_phone,
#             clinic_info={}, doctor_index=0, clarification_attempts=0
#         ))
#         state["user_input"] = user_input
#         state["needs_clarification"] = False

#         final_response = None
#         node_outputs = []

#         async for output in self.graph.astream(state):
#             logger.info(f"Node output: {output}")
#             node_name = list(output.keys())[0]
#             node_data = output[node_name]
#             node_outputs.append((node_name, node_data))

#             state["intent"] = node_data.get("intent", state["intent"])
#             state["intent_confidence"] = node_data.get("intent_confidence", state["intent_confidence"])
#             state["appointment"] = node_data.get("appointment", state["appointment"])
#             state["clinic_info"] = node_data.get("clinic_info", state["clinic_info"])
#             state["doctor_index"] = node_data.get("doctor_index", state["doctor_index"])
#             state["needs_clarification"] = node_data.get("needs_clarification", state["needs_clarification"])
#             state["conversation_step"] = node_data.get("conversation_step", state["conversation_step"])
#             state["clarification_attempts"] = node_data.get("clarification_attempts", state["clarification_attempts"])

#             if "messages" in node_data and node_data["messages"]:
#                 state["messages"] = node_data["messages"]
#                 final_response = node_data["messages"][-1]["content"]

#         logger.info(f"Processed nodes: {[name for name, _ in node_outputs]}")
#         self.user_states[clinic_phone] = state

#         return final_response or "Something went wrong. Please try again."





















# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel, Field
# from typing import Dict, Optional
# from langchain.chat_models import ChatOpenAI # type: ignore
# from langchain.tools import StructuredTool # type: ignore
# from langchain.prompts import ChatPromptTemplate # type: ignore
# from langchain.agents import AgentType, initialize_agent # type: ignore
# from langchain.memory import ConversationBufferMemory # type: ignore
# import json
# from langgraph.graph import StateGraph, END # type: ignore
# import langgraph.pregel as pg


# llm = ChatOpenAI(temperature=0)

# clinics_db = {
#     "clinic1": {"name": "City Clinic", "preferred_doctors": ["doctor1", "doctor2"], "contact_info": "clinic1@email.com"},
#     "clinic2": {"name": "Downtown Med", "preferred_doctors": ["doctor3", "doctor1"], "contact_info": "clinic2@email.com"},
# }
# doctors_db = {
#     "doctor1": {"name": "Dr. Smith", "specialization": "Cardiology", "availability": True, "contact_info": "doctor1@email.com"},
#     "doctor2": {"name": "Dr. Jones", "specialization": "Neurology", "availability": False, "contact_info": "doctor2@email.com"},
#     "doctor3": {"name": "Dr. Williams", "specialization": "Cardiology", "availability": True, "contact_info": "doctor3@email.com"},
# }
# appointments_db = {
#     "appt1001": {"clinic_id": "clinic1", "doctor_id": "doctor1", "procedure": "Cardiology Consultation", "date": "2023-11-10", "time": "10:00", "status": "Scheduled", "patient_name": "Patient A"},
#     "appt1002": {"clinic_id": "clinic2", "doctor_id": "doctor3", "procedure": "Neurology Check-up", "date": "2023-11-12", "time": "14:00", "status": "Confirmed", "patient_name": "Patient B"},
# }

# def get_clinic_info(clinic_id):
#     return clinics_db.get(clinic_id)
# def get_doctor_info(doctor_id):
#     return doctors_db.get(doctor_id)
# def update_doctor_availability(doctor_id, availability):
#     if doctor_id in doctors_db:
#         doctors_db[doctor_id]["availability"] = availability
#         return True
#     return False
# def get_appointment_details(appointment_identifier: str) -> str:
#     appointment = appointments_db.get(appointment_identifier)
#     if appointment:
#         return f"Appointment ID: {appointment_identifier}, Procedure: {appointment['procedure']}, Date: {appointment['date']}, Time: {appointment['time']}, Status: {appointment['status']}, Patient: {appointment['patient_name']}"
#     return f"Appointment with ID {appointment_identifier} not found."
# def update_appointment(appointment_identifier: str, updates: str) -> str:
#     if appointment_identifier in appointments_db:
#         try:
#             updates_dict = dict(item.split(": ") for item in updates.split(", "))
#             appointments_db[appointment_identifier].update(updates_dict)
#             return f"Appointment {appointment_identifier} updated successfully with: {updates}"
#         except Exception as e:
#             return f"Error updating appointment {appointment_identifier}. Invalid updates format. Error: {e}"
#     return f"Appointment with ID {appointment_identifier} not found."
# def cancel_appointment(appointment_identifier: str) -> str:
#     if appointment_identifier in appointments_db:
#         appointments_db[appointment_identifier]["status"] = "Cancelled"
#         return f"Appointment {appointment_identifier} cancelled."
#     return f"Appointment with ID {appointment_identifier} not found."
# def search_doctor_specialization(specialization: str) -> str:
#     doctors = [doc for doc_id, doc in doctors_db.items() if doc["specialization"].lower() == specialization.lower() and doc["availability"]]
#     if doctors:
#         return f"Found available doctors with specialization {specialization}: {', '.join([d['name'] for d in doctors])}"
#     return f"No available doctors found with specialization {specialization} right now."

# class AppointmentIdentifier(BaseModel):
#     appointment_identifier: str = Field(..., description="The identifier for the appointment")
# class AppointmentUpdates(BaseModel):
#     appointment_identifier: str = Field(..., description="The identifier for the appointment to update")
#     updates: str = Field(..., description="Updates in 'key: value, key: value' format")
# class Specialization(BaseModel):
#     specialization: str = Field(..., description="The doctor's specialization to search for")

# get_appointment_details_tool = StructuredTool.from_function(func=get_appointment_details, name="get_appointment_details", description="Fetch appointment details", args_schema=AppointmentIdentifier)
# update_appointment_tool = StructuredTool.from_function(func=update_appointment, name="update_appointment", description="Update appointment details", args_schema=AppointmentUpdates)
# cancel_appointment_tool = StructuredTool.from_function(func=cancel_appointment, name="cancel_appointment", description="Cancel appointment", args_schema=AppointmentIdentifier)
# search_doctor_specialization_tool = StructuredTool.from_function(func=search_doctor_specialization, name="search_doctor_specialization", description="Search doctors by specialization", args_schema=Specialization) # Corrected args_schema
# tools = [get_appointment_details_tool, update_appointment_tool, cancel_appointment_tool, search_doctor_specialization_tool]

# class IntentAgent:
#     def __init__(self):
#         self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
#         self.prompt = ChatPromptTemplate.from_messages([("system", """You classify user intent:"""), MessagesPlaceholder(variable_name="chat_history"), ("user", "{input}"), MessagesPlaceholder(variable_name="agent_scratchpad")])
#         self.llm = llm
#         self.tools = []
#         self.agent_chain = initialize_agent(tools=self.tools, llm=self.llm, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, prompt=self.prompt, memory=self.memory, verbose=False)
#     def identify_intent(self, message):
#         intent = self.agent_chain.run(input=message)
#         return intent
# intent_agent = IntentAgent()

# class DataExtractionAgent:
#     def __init__(self):
#         self.llm = llm
#     def extract_appointment_id(self, message):
#         prompt = ChatPromptTemplate.from_messages([("system", "Extract Appointment ID. Respond 'NONE' if not found."), ("human", "{message}")])
#         chain = prompt | self.llm
#         appointment_id = chain.invoke({"message": message}).content.strip()
#         return appointment_id
#     def extract_update_details(self, message):
#         prompt = ChatPromptTemplate.from_messages([("system", """Extract appointment update details as JSON. Respond '{}' if not found."""), ("human", "{message}")])
#         chain = prompt | self.llm
#         update_details_json_str = chain.invoke({"message": message}).content.strip()
#         try:
#             return json.loads(update_details_json_str)
#         except json.JSONDecodeError:
#             return {}
# data_extraction_agent = DataExtractionAgent()

# class GraphState(TypedDict):
#     clinic_id: str
#     user_message: str
#     chat_history: list
#     intent: Optional[str] = None
#     procedure_details: Optional[str] = None
#     proposed_doctor_id: Optional[str] = None
#     pending_intent: Optional[str] = None
#     pending_appointment_id: Optional[str] = None
#     response: Optional[str] = None

# def identify_intent_node(state: GraphState):
#     intent = intent_agent.identify_intent(state.user_message)
#     return {"intent": intent}
# def greet_node(state: GraphState):
#     return {"response": "Hello! How can I help you today?"}
# def ask_procedure_info_node(state: GraphState):
#     return {"response": "Okay, I can help with bookings. What procedure are you looking for?"}
# def extract_procedure_info_node(state: GraphState):
#     return {"procedure_details": "Cardiology Consultation"}
# def search_doctor_node(state: GraphState):
#     specialization = state.procedure_details
#     doctor_search_result = search_doctor_specialization_tool.run(Specialization(specialization=specialization)) # Use Specialization BaseModel
#     return {"doctor_search_result": doctor_search_result}
# def propose_doctor_node(state: GraphState):
#     proposed_doctor_id = "doctor1"
#     return {"proposed_doctor_id": proposed_doctor_id, "response": f"Proposing Dr. Smith (doctor1). Do you confirm?"}
# def confirm_appointment_node(state: GraphState):
#     doctor_agent = DoctorAgent("doctor1")
#     booking_confirmation = doctor_agent.confirm_appointment(f"{state.procedure_details} for Clinic {state.clinic_id}")
#     return {"response": f"{booking_confirmation}. Appointment scheduled and confirmed."}
# def handle_unknown_intent_node(state: GraphState):
#     return {"response": "Sorry, I didn't understand that. How can I help?"}

# def route_based_on_intent(state):
#     intent = state.intent
#     intent_map = { # Define intent_map here for clarity
#         "Greet": "greet",
#         "BookAppointment": "ask_procedure_info",
#         "ProvideProcedureInfo": "extract_procedure_info",
#         "ConfirmDoctor": "confirm_appointment",
#         "Unknown": "handle_unknown_intent",
#     }
#     return intent_map.get(state.intent, "handle_unknown_intent") # Default to unknown if intent not in map

# # def route_based_on_intent(state):
# #     intent = state.intent
# #     if intent == "Greet":
# #         return "greet"
# #     elif intent == "BookAppointment":
# #         return "ask_procedure_info"
# #     elif intent == "ProvideProcedureInfo":
# #         return "extract_procedure_info"
# #     elif intent == "ConfirmDoctor":
# #         return "confirm_appointment"
# #     elif intent == "Unknown":
# #         return "handle_unknown_intent"
# #     else:
# #         return "handle_unknown_intent"

# class DoctorAgent:
#     def __init__(self, doctor_id):
#         self.doctor_id = doctor_id
#         self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
#         self.prompt = ChatPromptTemplate.from_messages([("system", "AI assistant for Dr. {doctor_name}."), MessagesPlaceholder(variable_name="chat_history"), ("user", "{input}"), MessagesPlaceholder(variable_name="agent_scratchpad")])
#         self.llm = llm
#         self.tools = []
#         doctor_info = get_doctor_info(self.doctor_id)
#         doctor_name = doctor_info["name"] if doctor_info else "Unknown Doctor"
#         self.agent_chain = initialize_agent(tools=self.tools, llm=self.llm, agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION, prompt=self.prompt.partial(doctor_name=doctor_name, doctor_id=self.doctor_id), memory=self.memory, verbose=False)
#     def send_message(self, message):
#         return self.agent_chain.run(input=message.format(doctor_id=self.doctor_id, doctor_name=get_doctor_info(self.doctor_id)["name"] if get_doctor_info(self.doctor_id) else "Unknown Doctor"))
#     def check_availability(self, procedure_details):
#         doctor_info = get_doctor_info(self.doctor_id)
#         if doctor_info and doctor_info["availability"]:
#             return f"Dr. {doctor_info['name']} is available for {procedure_details}."
#         return f"Dr. {doctor_info['name']} is not available right now."
#     def confirm_appointment(self, appointment_details):
#         doctor_info = get_doctor_info(self.doctor_id)
#         if doctor_info and doctor_info["availability"]:
#             update_doctor_availability(self.doctor_id, False)
#             return f"Booking confirmed with Dr. {doctor_info['name']} for {appointment_details}."
#         return f"Sorry, Dr. {doctor_info['name']} is no longer available."

# builder = StateGraph(GraphState)
# builder.add_node("identify_intent", identify_intent_node)
# builder.add_node("greet", greet_node)
# builder.add_node("ask_procedure_info", ask_procedure_info_node)
# builder.add_node("extract_procedure_info", extract_procedure_info_node)
# builder.add_node("search_doctor", search_doctor_node)
# builder.add_node("propose_doctor", propose_doctor_node)
# builder.add_node("confirm_appointment", confirm_appointment_node)
# builder.add_node("handle_unknown_intent", handle_unknown_intent_node)

# builder.add_edge(START, "identify_intent")
# builder.add_edge("identify_intent", route_based_on_intent)
# builder.add_edge("greet", END)
# builder.add_edge("ask_procedure_info", END)
# builder.add_edge("extract_procedure_info", "search_doctor")
# builder.add_edge("search_doctor", "propose_doctor")
# builder.add_edge("propose_doctor", "confirm_appointment")
# builder.add_edge("confirm_appointment", END)
# builder.add_edge("handle_unknown_intent", END)

# workflow = builder.compile()

# def process_message(clinic_id: str, message: str) -> str:
#     inputs = {"clinic_id": clinic_id, "user_message": message, "chat_history": []}
#     result = workflow.invoke(inputs)
#     for output in result.values():
#         if isinstance(output, dict) and "response" in output:
#             response_message = output.get("response", "Default response")
#             return {"clinic_id": clinic_id, "response": response_message}
#     return {"clinic_id": clinic_id, "response": "Workflow executed, no specific response generated."}




from langgraph.graph import StateGraph, END # type: ignore
from typing import TypedDict
import asyncio
from datetime import datetime, timedelta
import logging
import json
import os
import re

state_manager = StateManager()

valid_intents = {
    "create_appointment": "create_appointment",
    "cancel_appointment": "cancel_appointment",
    "check_appointment_status": "check_appointment_status",
    "greet": "greet"
}
# memory = ConversationBufferMemory()
class ClinicAssistant:
    def __init__(self, message: Message):
        self.message = message
        self.whatsapp_service = WhatsAppBusinessAPI(message)
        self.state_manager = StateManager()
        self.graph = self._build_graph()
    @property
    def state(self):
        return self.state_manager.get_state(self.message.phone_number)

    def _update_state(self, data: Dict):
        self.state_manager.update_state(self.message.phone_number, data)

    async def greet(self, _: ClinicState) -> ClinicState:
        print('calling greet kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        handler = GreetingHandler(intent="greet", message=self.message)
        return await handler.process()

    async def intro(self, _) -> ClinicState:
        print('calling intro kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        handler = GreetingHandler(intent="greet",message=self.message)
        return await handler.general_response()

    async def create_appointment(self, _: ClinicState) -> ClinicState:
        print('calling create_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        handler = ProcedureCollector(intent="create_appointment", message=self.message)
        return await handler.process()

    async def classify_intent(self, _: ClinicState) -> ClinicState:
        print('calling classify_intent kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        state = self.state
        print(state, 'classify_intent state kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')

        clinic_phone = state.get("clinic_phone", "")
        user_input = state.get("user_input", "")

        if not state.get("clinic_name", "") or not state.get("full_name", ""):
            return "greet"

        if state.get("needs_clarification") and state.get("intent") != "other":
            return state.get("intent")

        prompt = f"""
Identify the primary intent of the user's message.

Use the conversation history to maintain context and determine the intent.

Possible intents:
- create_appointment: User wants to book a new appointment
- cancel_appointment: User wants to cancel an existing appointment
- edit_appointment: User wants to change or update an existing appointment
- greet: User is greeting the system
- other: None of the above

User message: {user_input}

Respond with only the intent label.
"""
        intent = await invoke_ai(prompt, clinic_phone)
        print(intent, 'classify_intent intent kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')

        if intent in valid_intents:
            return self._update_state({
                "intent": intent,
                "needs_clarification": False
            })

        return self._update_state({ "needs_clarification": True })

    async def prompt_doctors(self, state: ClinicState) -> ClinicState:
        print('calling prompt_doctors kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        clinic_phone = state.get("clinic_phone", "")
        full_name = state.get("full_name", "")
        clinic_name = state.get("clinic_name", "")
        patient_name = state.get("patient_name", "")
        procedure = state.get("procedure", "")
        doctor_index = state.get("doctor_index", 0)

        # doctors = await self.db.get_doctors_by_location(clinic_name)
        doctors = []
        if doctor_index >= len(doctors):
            prompt = f"Inform {full_name} at {clinic_name} that no doctors are available for {procedure}, and suggest trying a different procedure or contacting support."
            response = await invoke_ai(prompt, clinic_phone)
            await send_response(clinic_phone, response, message=self.message)
            return {}

        doctor = doctors[doctor_index]
        datetime_slot = (datetime.now() + timedelta(days=2)).strftime("%A, %B %d at 2:00 PM")
        prompt = f"Propose to {full_name} at {clinic_name} that {doctor} is available for {procedure} for {patient_name} on {datetime_slot}. Ask for confirmation (yes/no)."
        response = await invoke_ai(prompt, clinic_phone)
        await send_response(clinic_phone, response, message=self.message)
        return {
            "doctor": doctor,
            "datetime": datetime_slot,
            "doctor_index": doctor_index + 1,
            "needs_clarification": True
        }

    async def confirm_appointment(self, state: ClinicState) -> ClinicState:
        print('calling confirm_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        clinic_phone = state.get("clinic_phone", "")
        user_input = state.get("user_input", "")
        name = state.get("name", "")
        clinic_location = state.get("clinic_location", "")

        if state.get("needs_clarification", True):
            # history
            intent_data = await intent_agent(message=user_input)
            accepted = intent_data.get("entities", {}).get("confirmation", user_input.lower()) == "yes"

            if accepted:
                appointment = {
                    "clinic_phone": clinic_phone,
                    "patient_name": state.get("patient_name", ""),
                    "procedure": state.get("procedure", ""),
                    "doctor": state.get("doctor", ""),
                    "datetime": state.get("datetime", ""),
                    "clinic_location": clinic_location
                }
                await self.db.save_appointment(appointment)
                message =f"New booking: {state['procedure']} for {state['patient_name']} on {state['datetime']}."
                to_number = self.db.doctors[state["doctor"]]["phone"]
                await self.whatsapp_service.send_text_message(to_number, message)
                asyncio.create_task(self.db.schedule_reminder(clinic_phone, appointment, clinic_location))
                prompt = f"Confirm to {name} at {clinic_location} that {state['procedure']} for {state['patient_name']} with {state['doctor']} on {state['datetime']} is booked. Mention a reminder will be sent 1 day before, and ask if they need help with anything else."
                response = await invoke_ai(prompt, clinic_phone)
                await send_response(clinic_phone, response, message=self.message)
                return {"appointment": appointment, "needs_clarification": False}
            else:
                prompt = f"Let {name} at {clinic_location} know you'll look for another doctor for {state['patient_name']}'s {state['procedure']}, and ask if they have a preferred date."
                response = await invoke_ai(prompt, clinic_phone)
                await send_response(clinic_phone, response, message=self.message)
                return {"needs_clarification": False}

        prompt = "Please respond with 'yes' or 'no' to confirm the booking."
        response = await invoke_ai(prompt, clinic_phone)
        await send_response(clinic_phone, response, message=self.message)
        return {"needs_clarification": True}

    async def cancel_appointment(self, state: ClinicState) -> ClinicState:
        print('calling cancel_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        clinic_phone = state.get("clinic_phone", "")
        name = state.get("name", "")
        clinic_location = state.get("clinic_location", "")

        appointment = await self.db.find_appointment(clinic_phone)
        if not appointment:
            prompt = f"Inform {name} at {clinic_location} that no appointments were found to cancel, and ask if they'd like to book one instead."
            response = await invoke_ai(prompt, clinic_phone)
            await send_response(clinic_phone, response, message=self.message)
            return {}

        prompt = f"Ask {name} at {clinic_location} to confirm cancellation of the appointment: {appointment['procedure']} for {appointment['patient_name']} with {appointment['doctor']} on {appointment['datetime']} (yes/no), and offer to help with something else if they decline."
        response = await invoke_ai(prompt, clinic_phone)
        await send_response(clinic_phone, response, message=self.message)
        return {
            "appointment": appointment,
            "needs_clarification": True
        }

    async def process_cancel(self, state: ClinicState) -> ClinicState:
        print('calling process_cancel kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        clinic_phone = state.get("clinic_phone", "")
        user_input = state.get("user_input", "")
        name = state.get("name", "")
        clinic_location = state.get("clinic_location", "")

        if state.get("needs_clarification", True):
            intent_data = await intent_agent(message=user_input)
            confirmed = intent_data.get("entities", {}).get("confirmation", user_input.lower()) == "yes"

            if confirmed:
                await self.db.cancel_appointment(clinic_phone)
                prompt = f"Let {name} at {clinic_location} know the appointment for {state['appointment']['patient_name']} has been cancelled, and ask if they need help with anything else."
                response = await invoke_ai(prompt, clinic_phone)
                await send_response(clinic_phone, response, message=self.message)
                return {"appointment": {}, "needs_clarification": False}
            else:
                prompt = f"Inform {name} at {clinic_location} that the cancellation was aborted, and ask how else they'd like to proceed."
                response = await invoke_ai(prompt, clinic_phone)
                await send_response(clinic_phone, response, message=self.message)
                return {"needs_clarification": False}

        prompt = "Please respond with 'yes' or 'no' to confirm the cancellation."
        response = await invoke_ai(prompt, clinic_phone)
        await send_response(clinic_phone, response, message=self.message)
        return {"needs_clarification": True}

    async def check_appointment_status(self, state: ClinicState) -> ClinicState:
        print('calling check_appointment_status kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        clinic_phone = state.get("clinic_phone", "")
        name = state.get("name", "")
        clinic_location = state.get("clinic_location", "")

        appointment = await self.db.find_appointment(clinic_phone)

        if not appointment:
            prompt = f"Tell {name} at {clinic_location} that no appointments are scheduled, and ask if they'd like to book one."
        else:
            prompt = f"Inform {name} at {clinic_location} about their appointment: {appointment['procedure']} for {appointment['patient_name']} with {appointment['doctor']} on {appointment['datetime']}, and ask if they need help with anything else."
        response = await invoke_ai(prompt, clinic_phone)
        await send_response(clinic_phone, response, message=self.message)
        return {"appointment": appointment}

    async def wrap_up(self, _) -> ClinicState:
        print('calling wrap_up kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        state = self.state
        clinic_phone = state.get("clinic_phone", "")
        name = state.get("name", "")
        clinic_location = state.get("clinic_location", "")

        prompt = f"Thank {name} from {clinic_location} for the conversation, and ask if there's anything else they need help with before ending the session."
        response = await invoke_ai(prompt, clinic_phone)
        await send_response(clinic_phone, response, message=self.message)
        return {"needs_clarification": True}

    # Routing Functions
    def _route_after_greet(self, _: ClinicState) -> str:
        print('calling _route_after_greet kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        state = self.state
        if state.get("needs_clarification", False):
            return END
        return END

    def _route_after_classify(self, _: ClinicState) -> str:
        print('calling _route_after_classify kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        state = self.state
        # print(state, '_route_after_classify state yyyyyyyyyyyyyyyyyyyy')

        if not state.get("clinic_name", "") or not state.get("full_name", ""):
            return "greet"

        if state.get("needs_clarification") and state.get("intent") != "other":
            return state.get("intent")

        intent = state.get("intent")
        print(intent, 'intent yyyyyyyyyyyyyyyyyyyy')

        return valid_intents.get(intent, "intro")

    def _route_after_create_appointment(self, _: ClinicState) -> str:
        print('calling _route_after_create_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        state = self.state
        if state.get("needs_clarification"):
            return END
        return "wrap_up"

    def _route_after_prompt_doctors(self, state: ClinicState) -> str:
        print('calling _route_after_prompt_doctors kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        if state.get("needs_clarification"):
            return "confirm_appointment"
        return "prompt_doctors"

    def _route_after_confirm_appointment(self, state: ClinicState) -> str:
        print('calling _route_after_confirm_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        if state.get("needs_clarification"):
            return "confirm_appointment"
        return "wrap_up"

    def _route_after_cancel_appointment(self, state: ClinicState) -> str:
        print('calling _route_after_cancel_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        if state.get("needs_clarification"):
            return "process_cancel"
        return "cancel_appointment"

    def _route_after_process_cancel(self, state: ClinicState) -> str:
        print('calling _route_after_process_cancel kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        return "wrap_up"

    def _route_after_check_appointment_status(self, state: ClinicState) -> str:
        print('calling _route_after_process_cancel kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        return "wrap_up"

    def _route_after_wrap_up(self, state: ClinicState) -> str:
        print('calling _route_after_wrap_up kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        if state.get("needs_clarification"):
            return END
        return "wrap_up"

    def _route_after_intro(self, state: ClinicState) -> str:
        print('calling _route_after_intro kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        if state.get("needs_clarification"):
            return END
        return "intro"

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ClinicState)
        workflow.add_node("greet", self.greet)
        workflow.add_node("classify_intent", self.classify_intent)
        workflow.add_node("create_appointment", self.create_appointment)
        workflow.add_node("prompt_doctors", self.prompt_doctors)
        workflow.add_node("confirm_appointment", self.confirm_appointment)
        workflow.add_node("cancel_appointment", self.cancel_appointment)
        workflow.add_node("process_cancel", self.process_cancel)
        workflow.add_node("check_appointment_status", self.check_appointment_status)
        workflow.add_node("wrap_up", self.wrap_up)
        workflow.add_node("intro", self.intro)

        workflow.set_entry_point("classify_intent")
        workflow.add_conditional_edges("greet", self._route_after_greet)
        workflow.add_conditional_edges("classify_intent", self._route_after_classify)
        workflow.add_conditional_edges("create_appointment", self._route_after_create_appointment)
        workflow.add_conditional_edges("prompt_doctors", self._route_after_prompt_doctors)
        workflow.add_conditional_edges("confirm_appointment", self._route_after_confirm_appointment)
        workflow.add_conditional_edges("cancel_appointment", self._route_after_cancel_appointment)
        workflow.add_conditional_edges("process_cancel", self._route_after_process_cancel)
        workflow.add_conditional_edges("check_appointment_status", self._route_after_check_appointment_status)
        workflow.add_conditional_edges("wrap_up", self._route_after_wrap_up)
        # workflow.add_conditional_edges("intro", "classify_intent")

        return workflow.compile()

    async def process_message(self, clinic_phone: str, user_input: str) -> str:
        state = state_manager.get_state(clinic_phone)
        state["user_input"] = user_input
        state["clinic_phone"] = clinic_phone
        state["needs_clarification"] = False

        # history = get_message_history(clinic_phone)
        # history.add_user_message(user_input)  # Use synchronous add for simplicity
        # logger.info(f"Added user message to history for {clinic_phone}: {user_input}")

        final_response = None
        async for output in self.graph.astream(
            state,
            config={"configurable": {"session_id": clinic_phone}}
        ):
            logger.info(f"Node output: {output}")
            # node_name = list(output.keys())[0]
            # node_data = output[node_name]

            # Update state with node output
            # state.update(node_data)
            # state_manager.update_state(clinic_phone, state)

            # Capture the last response from the history
            # messages = history.messages  # Use synchronous messages attribute
            # if messages and messages[-1].type == "ai":
            #     final_response = messages[-1].content
        # Handle final response from the last node
        # if "final_response" in output:
        #     final_response = output["final_response"]

        return final_response or "Something went wrong. Please try again."
