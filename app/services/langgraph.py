
import json
from app.models.models import Message
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.logger import setup_logger
from langgraph.graph import StateGraph, END # type: ignore
from typing import TypedDict, Annotated, List
import operator
from datetime import datetime, timedelta
import openai
import random
import asyncio
import json
from app.core.config import settings
from app.services.openai import openai_service

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






class BubbleDB:
    def __init__(self):
        self.doctors = {
            "Dr. Smith": {"specialties": ["checkup"], "location": "Downtown", "phone": "whatsapp:+1234567890"},
            "Dr. Jones": {"specialties": ["surgery"], "location": "Downtown", "phone": "whatsapp:+1234567891"},
            "Dr. Brown": {"specialties": ["dental"], "location": "Uptown", "phone": "whatsapp:+1234567892"}
        }
        self.appointments = []  # {"clinic_phone": "", "patient_name": "", "procedure": "", "doctor": "", "datetime": "", "clinic_location": ""}
        self.doctor_preferences = {}  # Dynamic mapping if needed

    def save_appointment(self, appointment):
        self.appointments.append(appointment)
        return True

    def get_doctors_by_location(self, location):
        return [name for name, info in self.doctors.items()]  # Return all doctors for now (refine later)

    def find_appointment(self, clinic_phone):
        return next((appt for appt in self.appointments if appt["clinic_phone"] == clinic_phone), None)

    def update_appointment(self, clinic_phone, new_details):
        for i, appt in enumerate(self.appointments):
            if appt["clinic_phone"] == clinic_phone:
                self.appointments[i].update(new_details)
                return True
        return False

    def cancel_appointment(self, clinic_phone):
        for i, appt in enumerate(self.appointments):
            if appt["clinic_phone"] == clinic_phone:
                del self.appointments[i]
                return True
        return False

class ClinicState(TypedDict):
    user_input: str
    intent: str
    intent_confidence: float
    appointment: dict
    messages: Annotated[List[dict], operator.add]
    needs_clarification: bool
    conversation_step: str
    clinic_phone: str
    clinic_info: dict  # {"name": str, "clinic": str}
    doctor_index: int
    clarification_attempts: int

class ClinicAssistant:
    def __init__(self, message: Message):
        self.db = BubbleDB()
        self.user_states = {}
        self.message = message
        self.whatsapp_service = WhatsAppBusinessAPI(message)
        self.graph = self._build_graph()

    def _get_safe_state(self, state: ClinicState, key: str, default=None):
        return state.get(key, default) if state else default

    def _get_clinic_info(self, state: ClinicState, key: str, default: str = "") -> str:
        return state.get("clinic_info", {}).get(key, default)

    async def _call_openai(self, prompt: str, system_msg: str = "You're a professional, friendly AI assistant (AIA) helping clinics connect with doctors for patient bookings.") -> str:
        try:
            response = openai_service.create_agent_completion(
                messages=[{"role": "system", "content": system_msg}, {"role": "user", "content": prompt}]
            )
            logger.info(f"OpenAI response: {response}")
            return response
        except Exception as e:
            logger.error(f"OpenAI error: {str(e)}")
            return f"Error: {str(e)}"

    async def _send_whatsapp_message(self, to_phone: str, message: str) -> bool:
        await self.whatsapp_service.send_text_message(message=message, to_number=to_phone)

    # Node Methods
    async def greet(self, state: ClinicState) -> ClinicState:
        messages = self._get_safe_state(state, "messages", [])
        user_input = self._get_safe_state(state, "user_input", "").lower()
        clinic_name = self._get_clinic_info(state, "name")
        clinic_location = self._get_clinic_info(state, "clinic")

        if not messages:
            if not clinic_name or not clinic_location:
                if user_input and user_input not in ["hi", "hey", "hello", "just checking this out"]:
                    prompt = f"Extract clinic staff name and clinic location from: '{user_input}'. " \
                             f"Return JSON: {{'name': '...', 'clinic': '...'}}, leave clinic empty if unclear."
                    try:
                        details = json.loads(await self._call_openai(prompt))
                        extracted_name = details.get("name", "").strip()
                        extracted_clinic = details.get("clinic", "").strip()

                        if not extracted_name and not extracted_clinic:
                            prompt = "I couldn’t understand your input. Please provide your name and your clinic’s location so I can assist you."
                            response = await self._call_openai(prompt)
                            return {
                                "messages": [{"role": "assistant", "content": response}],
                                "needs_clarification": True,
                                "conversation_step": "greet"
                            }
                        elif not extracted_clinic:
                            prompt = f"I got your name as {extracted_name}, but couldn’t determine your clinic’s location. Please provide your clinic’s location."
                            response = await self._call_openai(prompt)
                            return {
                                "messages": [{"role": "assistant", "content": response}],
                                "needs_clarification": True,
                                "conversation_step": "greet",
                                "clinic_info": {"name": extracted_name, "clinic": ""}
                            }
                        elif not extracted_name:
                            prompt = f"I got your clinic location as {extracted_clinic}, but couldn’t determine your name. Please provide your name."
                            response = await self._call_openai(prompt)
                            return {
                                "messages": [{"role": "assistant", "content": response}],
                                "needs_clarification": True,
                                "conversation_step": "greet",
                                "clinic_info": {"name": "", "clinic": extracted_clinic}
                            }

                        state["clinic_info"] = {"name": extracted_name, "clinic": extracted_clinic}
                        prompt = f"Hello {extracted_name}! I’m AIA, your assistant to connect {extracted_clinic} with doctors for patient bookings. How can I assist you today?"
                        response = await self._call_openai(prompt)
                        return {
                            "messages": [{"role": "assistant", "content": response}],
                            "needs_clarification": False,
                            "conversation_step": "greet",
                            "clinic_info": state["clinic_info"]
                        }
                    except json.JSONDecodeError:
                        prompt = "I couldn’t process your input. Please provide your name and your clinic’s location so I can assist you."
                        response = await self._call_openai(prompt)
                        return {
                            "messages": [{"role": "assistant", "content": response}],
                            "needs_clarification": True,
                            "conversation_step": "greet"
                        }
                else:
                    prompt = "Hello! I’m AIA, your assistant to help clinics connect with doctors for patient bookings. Please provide your name and your clinic’s location."
                    response = await self._call_openai(prompt)
                    return {
                        "messages": [{"role": "assistant", "content": response}],
                        "needs_clarification": True,
                        "conversation_step": "greet"
                    }

            prompt = f"Hello {clinic_name}! I’m AIA, your assistant to connect {clinic_location} with doctors for patient bookings. How can I assist you today?"
            response = await self._call_openai(prompt)
            return {
                "messages": [{"role": "assistant", "content": response}],
                "needs_clarification": False,
                "conversation_step": "greet"
            }
        return state

    async def classify_intent(self, state: ClinicState) -> ClinicState:
        user_input = self._get_safe_state(state, "user_input", "")
        clinic_name = self._get_clinic_info(state, "name")
        clinic_location = self._get_clinic_info(state, "clinic")

        if not clinic_name or not clinic_location:
            prompt = "The clinic staff hasn’t provided their name or location yet. Politely ask them to provide their name and clinic location."
            response = await self._call_openai(prompt)
            return {
                "messages": [{"role": "assistant", "content": response}],
                "needs_clarification": True,
                "conversation_step": "classify",
                "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
            }

        prompt = f"Classify the intent of: '{user_input}' and determine if clarification is needed. " \
                 f"Options: book_doctor, edit_appointment, cancel_appointment, check_status. " \
                 f"Return valid JSON: {{'intent': '...', 'confidence': 0.0-1.0, 'needs_clarification': true/false}}. " \
                 f"If the input is vague (e.g., 'hi', 'just checking'), set confidence low and request clarification. " \
                 f"Recognize 'i have an appointment i want to terminate' as 'cancel_appointment'."
        try:
            result = json.loads(await self._call_openai(prompt))
            intent = result.get("intent", "book_doctor")
            confidence = result.get("confidence", 0.0)
            needs_clarification = result.get("needs_clarification", confidence < 0.75)
            if confidence < 0.75 or needs_clarification:
                prompt = f"Clinic input was unclear: '{user_input}'. Ask for clarification politely based on intent '{intent}'."
                response = await self._call_openai(prompt)
                return {
                    "messages": [{"role": "assistant", "content": response}],
                    "intent": intent,
                    "intent_confidence": confidence,
                    "needs_clarification": True,
                    "conversation_step": "classify",
                    "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
                }
            return {
                "intent": intent,
                "intent_confidence": confidence,
                "needs_clarification": needs_clarification,
                "conversation_step": "classify",
                "clarification_attempts": 0
            }
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return {
                "messages": [{"role": "assistant", "content": "I’m having trouble understanding. Please clarify your request."}],
                "needs_clarification": True,
                "conversation_step": "classify",
                "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
            }

    async def collect_procedure(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        clinic_location = self._get_clinic_info(state, "clinic")
        clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)

        if not clinic_name or not clinic_location:
            try:
                prompt = f"Extract clinic staff name and location from: '{state['user_input']}'. Return JSON: {{'name': '...', 'clinic': '...'}}, leave clinic empty if unclear."
                details = json.loads(await self._call_openai(prompt))
                state["clinic_info"] = {"name": details.get("name", ""), "clinic": details.get("clinic", "")}
                if not details.get("name"):
                    prompt = "I couldn’t get your name. Could you please provide it so I can assist with patient bookings?"
                    response = await self._call_openai(prompt)
                    return {
                        "messages": [{"role": "assistant", "content": response}],
                        "needs_clarification": True,
                        "conversation_step": "collect_procedure",
                        "clarification_attempts": clarification_attempts + 1
                    }
            except json.JSONDecodeError:
                prompt = "I couldn’t identify your info. Please provide your name and clinic location."
                response = await self._call_openai(prompt)
                return {
                    "messages": [{"role": "assistant", "content": response}],
                    "needs_clarification": True,
                    "conversation_step": "collect_procedure",
                    "clarification_attempts": clarification_attempts + 1
                }

        appointment = self._get_safe_state(state, "appointment", {})
        if not appointment.get("procedure") or not appointment.get("patient_name"):
            prompt = f"Ask {clinic_name} staff from {clinic_location} for the patient’s name and the procedure (e.g., checkup, surgery, dental) they need a doctor for."
            response = await self._call_openai(prompt)
            return {
                "messages": [{"role": "assistant", "content": response}],
                "needs_clarification": True,
                "conversation_step": "collect_procedure",
                "clarification_attempts": clarification_attempts + 1
            }

        try:
            prompt = f"Extract patient name and procedure from: '{state['user_input']}'. Return JSON: {{'patient_name': '...', 'procedure': '...'}}, default procedure to 'checkup' if unclear."
            details = json.loads(await self._call_openai(prompt))
            procedure = details.get("procedure", "checkup")
            patient_name = details.get("patient_name", "")
            if not patient_name:
                prompt = "I couldn’t get the patient’s name. Could you please provide it?"
                response = await self._call_openai(prompt)
                return {
                    "messages": [{"role": "assistant", "content": response}],
                    "needs_clarification": True,
                    "conversation_step": "collect_procedure",
                    "clarification_attempts": clarification_attempts + 1
                }
            state["appointment"]["procedure"] = procedure
            state["appointment"]["patient_name"] = patient_name
            return {"appointment": state["appointment"], "needs_clarification": False, "conversation_step": "collect_procedure"}
        except json.JSONDecodeError:
            prompt = "I couldn’t identify the procedure or patient name. Please specify (e.g., 'checkup for John Doe')."
            response = await self._call_openai(prompt)
            return {
                "messages": [{"role": "assistant", "content": response}],
                "needs_clarification": True,
                "conversation_step": "collect_procedure",
                "clarification_attempts": clarification_attempts + 1
            }

    async def collect_edit(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        existing_appt = self.db.find_appointment(state["clinic_phone"])
        if not existing_appt:
            prompt = f"Inform {clinic_name} staff that no patient appointment exists to edit and suggest booking one."
            response = await self._call_openai(prompt)
            return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "collect_edit"}

        prompt = f"Ask {clinic_name} staff what they’d like to change about the patient’s appointment: " \
                 f"{existing_appt['procedure']} for {existing_appt['patient_name']} with {existing_appt['doctor']} at {existing_appt['clinic_location']} on {existing_appt['datetime']} " \
                 f"(e.g., procedure, date/time, or doctor)."
        response = await self._call_openai(prompt)
        return {
            "messages": [{"role": "assistant", "content": response}],
            "needs_clarification": True,
            "conversation_step": "collect_edit",
            "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
        }

    async def process_edit(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        clinic_location = self._get_clinic_info(state, "clinic")
        existing_appt = self.db.find_appointment(state["clinic_phone"])
        if not existing_appt:
            return {"messages": [{"role": "assistant", "content": "No patient appointment found to edit."}], "conversation_step": "process_edit"}

        try:
            prompt = f"Extract changes from: '{state['user_input']}' for appointment: {json.dumps(existing_appt)}. " \
                     f"Return JSON: {{'procedure': '...', 'datetime': '...', 'doctor': '...'}}, use existing values if not specified."
            changes = json.loads(await self._call_openai(prompt))
            new_procedure = changes.get("procedure", existing_appt["procedure"])
            new_datetime = changes.get("datetime", existing_appt["datetime"])
            new_doctor = changes.get("doctor", existing_appt["doctor"])

            self.db.update_appointment(state["clinic_phone"], {"procedure": new_procedure, "datetime": new_datetime, "doctor": new_doctor})
            prompt = f"Confirm to {clinic_name} staff that the patient’s appointment is updated to {new_procedure} " \
                     f"for {existing_appt['patient_name']} with {new_doctor} at {clinic_location} on {new_datetime}."
            response = await self._call_openai(prompt)
            await self._send_whatsapp_message(self.db.doctors[new_doctor]["phone"], response)
            return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "process_edit"}
        except json.JSONDecodeError:
            return {
                "messages": [{"role": "assistant", "content": "I couldn’t understand the changes. Please specify (e.g., procedure, date/time, doctor)."}],
                "needs_clarification": True,
                "conversation_step": "process_edit",
                "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
            }

    async def confirm_cancel(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        existing_appt = self.db.find_appointment(state["clinic_phone"])
        if not existing_appt:
            prompt = f"Inform {clinic_name} staff that no patient appointment exists to cancel."
            response = await self._call_openai(prompt)
            return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "confirm_cancel"}

        prompt = f"Ask {clinic_name} staff to confirm cancellation of the patient’s {existing_appt['procedure']} " \
                 f"for {existing_appt['patient_name']} with {existing_appt['doctor']} at {existing_appt['clinic_location']} on {existing_appt['datetime']} (yes/no)."
        response = await self._call_openai(prompt)
        return {
            "messages": [{"role": "assistant", "content": response}],
            "needs_clarification": True,
            "conversation_step": "confirm_cancel",
            "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
        }

    async def process_cancel(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        existing_appt = self.db.find_appointment(state["clinic_phone"])
        if not existing_appt:
            return {"messages": [{"role": "assistant", "content": "No patient appointment found to cancel."}], "conversation_step": "process_cancel"}

        try:
            prompt = f"Determine if '{state['user_input']}' indicates confirmation (yes) or not (no). Return JSON: {{'confirmed': true/false}}."
            result = json.loads(await self._call_openai(prompt))
            confirmed = result.get("confirmed", False)
        except json.JSONDecodeError:
            return {
                "messages": [{"role": "assistant", "content": "Please respond with 'yes' or 'no' to confirm."}],
                "needs_clarification": True,
                "conversation_step": "process_cancel",
                "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
            }

        if confirmed:
            self.db.cancel_appointment(state["clinic_phone"])
            prompt = f"Confirm to {clinic_name} staff that the patient’s appointment with {existing_appt['doctor']} " \
                     f"at {existing_appt['clinic_location']} on {existing_appt['datetime']} for {existing_appt['patient_name']} has been cancelled."
            response = await self._call_openai(prompt)
            await self._send_whatsapp_message(self.db.doctors[existing_appt["doctor"]]["phone"], response)
            return {"messages": [{"role": "assistant", "content": response}], "appointment": {}, "conversation_step": "process_cancel"}
        return {"messages": [{"role": "assistant", "content": "Cancellation aborted. How else can I assist with patient bookings?"}], "conversation_step": "process_cancel"}

    async def check_status(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        clinic_location = self._get_clinic_info(state, "clinic")
        existing_appt = self.db.find_appointment(state["clinic_phone"])
        if not existing_appt:
            prompt = f"Inform {clinic_name} staff that no patient appointment is currently scheduled at {clinic_location}."
        else:
            prompt = f"Report to {clinic_name} staff the status of the patient’s appointment: " \
                     f"{existing_appt['procedure']} for {existing_appt['patient_name']} with {existing_appt['doctor']} at {clinic_location} on {existing_appt['datetime']}."
        response = await self._call_openai(prompt)
        return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "check_status"}

    async def initiate_doctor_search(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        clinic_location = self._get_clinic_info(state, "clinic")
        appointment = self._get_safe_state(state, "appointment", {})
        prompt = f"Thank {clinic_name} staff from {clinic_location} for providing the procedure ({appointment.get('procedure', '')}) " \
                 f"for patient {appointment.get('patient_name', '')} and inform them that you’ll look for an available doctor and get back to them."
        response = await self._call_openai(prompt)
        return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "initiate_doctor_search", "doctor_index": 0}

    async def prompt_doctors(self, state: ClinicState) -> ClinicState:
        clinic_location = self._get_clinic_info(state, "clinic")
        appointment = self._get_safe_state(state, "appointment", {})
        doctors = self.db.get_doctors_by_location(clinic_location)
        doctor_index = self._get_safe_state(state, "doctor_index", 0)
        if doctor_index >= len(doctors):
            prompt = f"Inform the clinic staff that no doctors are currently available for {appointment.get('procedure', '')} " \
                     f"at {clinic_location} and suggest contacting the clinic directly or trying another procedure."
            response = await self._call_openai(prompt)
            return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "prompt_doctors"}

        doctor = doctors[doctor_index]
        prompt = f"Ask {doctor} if they’re available for a {appointment.get('procedure', '')} at {clinic_location} " \
                 f"on {appointment.get('datetime', (datetime.now() + timedelta(days=2)).strftime('%A, %B %d at 2:00 PM'))} for patient {appointment.get('patient_name', '')}. Request a yes/no response."
        doctor_response = await self._call_openai(prompt)
        await self._send_whatsapp_message(self.db.doctors[doctor]["phone"], doctor_response)

        accepted = random.choice([True, False])
        if accepted:
            state["appointment"]["doctor"] = doctor
            state["appointment"]["datetime"] = appointment.get("datetime", (datetime.now() + timedelta(days=2)).strftime("%A, %B %d at 2:00 PM"))
            return {"appointment": state["appointment"], "conversation_step": "prompt_doctors"}
        return {"doctor_index": doctor_index + 1, "conversation_step": "prompt_doctors"}

    async def propose_doctor(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        appointment = self._get_safe_state(state, "appointment", {})
        prompt = f"Propose to {clinic_name} staff that {appointment.get('doctor', '')} is available " \
                 f"for a {appointment.get('procedure', '')} for patient {appointment.get('patient_name', '')} at {self._get_clinic_info(state, 'clinic')} " \
                 f"on {appointment.get('datetime', '')}. Ask for confirmation (yes/no)."
        response = await self._call_openai(prompt)
        return {"messages": [{"role": "assistant", "content": response}], "needs_clarification": True, "conversation_step": "propose_doctor"}

    async def confirm_booking(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        clinic_location = self._get_clinic_info(state, "clinic")
        appointment = self._get_safe_state(state, "appointment", {})
        try:
            prompt = f"Determine if '{state['user_input']}' indicates acceptance (yes) or rejection (no). Return JSON: {{'accepted': true/false}}."
            result = json.loads(await self._call_openai(prompt))
            accepted = result.get("accepted", False)
        except json.JSONDecodeError:
            return {
                "messages": [{"role": "assistant", "content": "Please respond with 'yes' or 'no' to confirm."}],
                "needs_clarification": True,
                "conversation_step": "confirm_booking",
                "clarification_attempts": self._get_safe_state(state, "clarification_attempts", 0) + 1
            }

        if accepted:
            self.db.save_appointment({"clinic_phone": state["clinic_phone"], **appointment, "clinic_location": clinic_location})
            prompt = f"Confirm to {clinic_name} staff that the {appointment.get('procedure', '')} for {appointment.get('patient_name', '')} " \
                     f"with {appointment.get('doctor', '')} at {clinic_location} on {appointment.get('datetime', '')} is scheduled. " \
                     f"Notify them a reminder will be sent 1 day before."
            response = await self._call_openai(prompt)
            await self._send_whatsapp_message(self.db.doctors[appointment["doctor"]]["phone"], response)
            asyncio.create_task(self._schedule_reminder(state["clinic_phone"], appointment, clinic_location))
            return {"messages": [{"role": "assistant", "content": response}], "conversation_step": "confirm_booking"}
        prompt = "Inform the clinic staff that you’ll look for another available doctor and proceed."
        response = await self._call_openai(prompt)
        return {"messages": [{"role": "assistant", "content": response}], "doctor_index": self._get_safe_state(state, "doctor_index", 0) + 1, "conversation_step": "prompt_doctors"}

    async def wrap_up(self, state: ClinicState) -> ClinicState:
        clinic_name = self._get_clinic_info(state, "name")
        prompt = f"Ask {clinic_name} staff if there’s anything else they need help with for patient bookings before ending the session."
        response = await self._call_openai(prompt)
        logger.info(f"Wrap up response: {response}")
        return {
            "messages": [{"role": "assistant", "content": response}],
            "needs_clarification": False,
            "conversation_step": "wrap_up"
        }

    async def handle_error(self, state: ClinicState) -> ClinicState:
        prompt = "An error occurred. Apologize politely to the clinic staff and inform them that the process couldn’t be completed. Suggest trying again later or contacting support if the issue persists."
        response = await self._call_openai(prompt)
        logger.info(f"Error node reached: {state}")
        return {
            "messages": [{"role": "assistant", "content": response}],
            "needs_clarification": False,
            "conversation_step": "error"
        }

    async def _schedule_reminder(self, clinic_phone: str, appointment: dict, clinic_location: str):
        wait_time = (datetime.strptime(appointment["datetime"], "%A, %B %d at 2:00 PM") - timedelta(days=1) - datetime.now()).total_seconds()
        if wait_time > 0:
            await asyncio.sleep(wait_time)
            prompt = f"Remind {self._get_clinic_info(self.user_states.get(clinic_phone, {}), 'name')} staff and {appointment['doctor']} " \
                     f"about the {appointment['procedure']} for {appointment['patient_name']} at {clinic_location} on {appointment['datetime']}."
            response = await self._call_openai(prompt)
            await self._send_whatsapp_message(clinic_phone, response)
            await self._send_whatsapp_message(self.db.doctors[appointment["doctor"]]["phone"], response)

    # Routing Methods
    def _route_after_greet(self, state: ClinicState) -> str:
        needs_clarification = self._get_safe_state(state, "needs_clarification", False)
        user_input = self._get_safe_state(state, "user_input", "")
        clinic_name = self._get_clinic_info(state, "name")
        clinic_location = self._get_clinic_info(state, "clinic")

        logger.info(f"Routing after greet: needs_clarification={needs_clarification}, user_input='{user_input}', clinic_info={{'name': '{clinic_name}', 'clinic': '{clinic_location}'}}")

        if needs_clarification:
            logger.info("Ending graph to wait for clinic info")
            return END

        logger.info("Proceeding to classify intent with clinic info")
        return "classify"

    def _route_after_classify(self, state: ClinicState) -> str:
        if self._get_safe_state(state, "needs_clarification", False) and self._get_safe_state(state, "clarification_attempts", 0) < 3:
            return "collect_procedure" if self._get_safe_state(state, "intent") == "book_doctor" else self._get_safe_state(state, "intent", "error")
        intent = self._get_safe_state(state, "intent", "book_doctor")
        return {
            "book_doctor": "collect_procedure",
            "edit_appointment": "collect_edit",
            "cancel_appointment": "confirm_cancel",
            "check_status": "check_status"
        }.get(intent, "error")

    def _route_after_collect_procedure(self, state: ClinicState) -> str:
        clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
        if self._get_safe_state(state, "needs_clarification", False) and clarification_attempts >= 3:
            return "error"
        return "initiate_doctor_search" if not self._get_safe_state(state, "needs_clarification", False) else "collect_procedure"

    def _route_after_collect_edit(self, state: ClinicState) -> str:
        clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
        if self._get_safe_state(state, "needs_clarification", False) and clarification_attempts >= 3:
            return "error"
        return "process_edit" if not self._get_safe_state(state, "needs_clarification", False) else "collect_edit"

    def _route_after_process_edit(self, state: ClinicState) -> str:
        return "wrap_up"

    def _route_after_confirm_cancel(self, state: ClinicState) -> str:
        clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
        if self._get_safe_state(state, "needs_clarification", False) and clarification_attempts >= 3:
            return "error"
        return "process_cancel" if not self._get_safe_state(state, "needs_clarification", False) else "confirm_cancel"

    def _route_after_process_cancel(self, state: ClinicState) -> str:
        return "wrap_up"

    def _route_after_check_status(self, state: ClinicState) -> str:
        return "wrap_up"

    def _route_after_initiate(self, state: ClinicState) -> str:
        return "prompt_doctors"

    def _route_after_prompt(self, state: ClinicState) -> str:
        return "propose_doctor" if self._get_safe_state(state, "appointment", {}).get("doctor") else "prompt_doctors"

    def _route_after_propose(self, state: ClinicState) -> str:
        clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
        if self._get_safe_state(state, "needs_clarification", False) and clarification_attempts >= 3:
            return "error"
        return "confirm_booking" if self._get_safe_state(state, "needs_clarification", False) else "prompt_doctors"

    def _route_after_confirm(self, state: ClinicState) -> str:
        return "wrap_up" if not self._get_safe_state(state, "needs_clarification", False) else "confirm_booking"

    def _route_after_action(self, state: ClinicState) -> str:
        clarification_attempts = self._get_safe_state(state, "clarification_attempts", 0)
        needs_clarification = self._get_safe_state(state, "needs_clarification", False)
        conversation_step = self._get_safe_state(state, "conversation_step", "")

        logger.info(f"Routing after action: step={conversation_step}, needs_clarification={needs_clarification}, attempts={clarification_attempts}")

        if conversation_step == "error":
            logger.info("Exiting graph from error node")
            return END

        if needs_clarification and clarification_attempts >= 3:
            logger.info("Routing to error due to max clarification attempts")
            return "error"

        if needs_clarification:
            logger.info("Routing back to collect_procedure for clarification")
            return "collect_procedure"

        logger.info("No clarification needed, ending graph")
        return END

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ClinicState)
        workflow.add_node("greet", self.greet)
        workflow.add_node("classify", self.classify_intent)
        workflow.add_node("collect_procedure", self.collect_procedure)
        workflow.add_node("collect_edit", self.collect_edit)
        workflow.add_node("process_edit", self.process_edit)
        workflow.add_node("confirm_cancel", self.confirm_cancel)
        workflow.add_node("process_cancel", self.process_cancel)
        workflow.add_node("check_status", self.check_status)
        workflow.add_node("initiate_doctor_search", self.initiate_doctor_search)
        workflow.add_node("prompt_doctors", self.prompt_doctors)
        workflow.add_node("propose_doctor", self.propose_doctor)
        workflow.add_node("confirm_booking", self.confirm_booking)
        workflow.add_node("wrap_up", self.wrap_up)
        workflow.add_node("error", self.handle_error)

        workflow.set_entry_point("greet")
        workflow.add_conditional_edges("greet", self._route_after_greet)
        workflow.add_conditional_edges("classify", self._route_after_classify)
        workflow.add_conditional_edges("collect_procedure", self._route_after_collect_procedure)
        workflow.add_conditional_edges("collect_edit", self._route_after_collect_edit)
        workflow.add_conditional_edges("process_edit", self._route_after_process_edit)
        workflow.add_conditional_edges("confirm_cancel", self._route_after_confirm_cancel)
        workflow.add_conditional_edges("process_cancel", self._route_after_process_cancel)
        workflow.add_conditional_edges("check_status", self._route_after_check_status)
        workflow.add_conditional_edges("initiate_doctor_search", self._route_after_initiate)
        workflow.add_conditional_edges("prompt_doctors", self._route_after_prompt)
        workflow.add_conditional_edges("propose_doctor", self._route_after_propose)
        workflow.add_conditional_edges("confirm_booking", self._route_after_confirm)
        workflow.add_conditional_edges("wrap_up", self._route_after_action)
        workflow.add_conditional_edges("error", self._route_after_action)

        return workflow.compile()

    async def process_message(self, user_input: str, clinic_phone: str) -> str:
        state = self.user_states.get(clinic_phone, ClinicState(
            user_input="", intent="", intent_confidence=0.0, appointment={}, messages=[],
            needs_clarification=False, conversation_step="", clinic_phone=clinic_phone,
            clinic_info={}, doctor_index=0, clarification_attempts=0
        ))
        state["user_input"] = user_input
        state["needs_clarification"] = False

        final_response = None
        node_outputs = []

        async for output in self.graph.astream(state):
            logger.info(f"Node output: {output}")
            node_name = list(output.keys())[0]
            node_data = output[node_name]
            node_outputs.append((node_name, node_data))

            state["intent"] = node_data.get("intent", state["intent"])
            state["intent_confidence"] = node_data.get("intent_confidence", state["intent_confidence"])
            state["appointment"] = node_data.get("appointment", state["appointment"])
            state["clinic_info"] = node_data.get("clinic_info", state["clinic_info"])
            state["doctor_index"] = node_data.get("doctor_index", state["doctor_index"])
            state["needs_clarification"] = node_data.get("needs_clarification", state["needs_clarification"])
            state["conversation_step"] = node_data.get("conversation_step", state["conversation_step"])
            state["clarification_attempts"] = node_data.get("clarification_attempts", state["clarification_attempts"])

            if "messages" in node_data and node_data["messages"]:
                state["messages"] = node_data["messages"]
                final_response = node_data["messages"][-1]["content"]

        logger.info(f"Processed nodes: {[name for name, _ in node_outputs]}")
        self.user_states[clinic_phone] = state

        return final_response or "Something went wrong. Please try again."
