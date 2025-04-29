
from typing import Dict
from app.handler.cancel_handler import CancelHandler
from app.handler.edit_handler import EditHandler
from app.handler.greet import GreetingHandler
from app.handler.procedure_collector import ProcedureCollector
from app.handler.status_handler import StatusHandler
from app.models.models import ClinicState, Message
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.helpers import invoke_ai, send_response
from app.utils.logger import setup_logger
from app.utils.state_manager import StateManager
from langgraph.graph import StateGraph, END # type: ignore
from datetime import datetime, timedelta
import openai
from app.core.config import settings

openai.api_key = settings.OPENAI_API_KEY

logger = setup_logger("clinic_assistant", "clinic_assistant.log")

# LANGUAGES = {
#     "en": {"booked": "✅ Your appointment has been booked!", "updated": "✏️ Your appointment has been updated!", "canceled": "❌ Your appointment has been canceled!", "not_understood": "🤖 I didn't understand your request. Please try again!", "greeting": "👋 Hello! How can I assist you today?", "thanks": "🙏 You're welcome! Let me know if you need anything else."},
#     "es": {"booked": "✅ ¡Tu cita ha sido reservada!", "updated": "✏️ ¡Tu cita ha sido actualizada!", "canceled": "❌ ¡Tu cita ha sido cancelada!", "not_understood": "🤖 No entendí tu solicitud. ¡Por favor, intenta de nuevo!", "greeting": "👋 ¡Hola! ¿En qué puedo ayudarte hoy?", "thanks": "🙏 ¡De nada! Avísame si necesitas algo más."}
# }


from langgraph.graph import StateGraph, END # type: ignore
from datetime import datetime, timedelta

state_manager = StateManager()

valid_intents = {
    "create_appointment": "create_appointment",
    "edit_appointment": "edit_appointment",
    "cancel_appointment": "cancel_appointment",
    "check_appointment_status": "check_appointment_status",
    "language_english": "language_english",
    "language_spanish": "language_spanish",
    "greet": "greet",
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

    async def pause(self, _) -> ClinicState:
        return

    async def create_appointment(self, _: ClinicState) -> ClinicState:
        print('calling create_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        handler = ProcedureCollector(intent="create_appointment", message=self.message)
        return await handler.process()

    async def edit_appointment(self, _: ClinicState) -> ClinicState:
        print('calling edit_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        handler = EditHandler(intent="edit_appointment", message=self.message)
        return await handler.process()

    async def cancel_appointment(self, _: ClinicState) -> ClinicState:
        print('calling cancel_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        handler = CancelHandler(intent="cancel_appointment", message=self.message)
        return await handler.process()

    async def check_appointment_status(self, _: ClinicState) -> ClinicState:
        print('calling check_appointment_status kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        handler = StatusHandler(intent="check_appointment_status", message=self.message)
        return await handler.process()

    async def classify_intent(self, _: ClinicState) -> ClinicState:
        print('calling classify_intent kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        state = self.state
        # print(state, 'classify_intent state kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')

        clinic_phone = state.get("clinic_phone", "")
        user_input = state.get("user_input", "")

        if not state.get("clinic_name", "") or not state.get("full_name", ""):
            return self._update_state({ "intent": "greet" })

        if state.get("needs_clarification") and state.get("intent") != "other":
            return self._update_state({ "intent": state.get("intent") })

        if state.get("confirmation_status") == "PENDING":
            return self._update_state({ "intent": state.get("intent") })

        prompt = f"""
Identify the primary intent of the user's message.

Use the conversation history to maintain context and determine the intent.

Possible intents:
- create_appointment: User wants to book a new appointment
- cancel_appointment: User wants to cancel an existing appointment
- edit_appointment: User wants to change or update an existing appointment
- check_appointment_status: User wants to check the status of an existing appointment
- language_english: User indicates preference for English language
- language_spanish: User indicates preference for Mexican Spanish language
- greet: User is greeting the system
- other: None of the above

User message: {user_input}

Respond with only the intent label.
"""
        intent = await invoke_ai(prompt, clinic_phone)
        print(intent, 'classify_intent intent kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')

        if intent == "language_english":
            return self._update_state({ "language": "english" })

        if intent == "language_spanish":
            return self._update_state({ "language": "spanish" })

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

        if not state.get("intent") or state.get("intent") == "other":
            return "wrap_up"

        if state.get("needs_clarification"):
            return state.get("intent")

        intent = state.get("intent")
        print(intent, 'intent yyyyyyyyyyyyyyyyyyyy')

        return valid_intents.get(intent, "intro")

    def _route_after_create_appointment(self, _: ClinicState) -> str:
        print('calling _route_after_create_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        state = self.state
        if state.get("needs_clarification"):
            return END
        return "pause"

    def _route_after_edit_appointment(self, _: ClinicState) -> str:
        print('calling _route_after_edit_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        state = self.state
        if state.get("needs_clarification"):
            return END
        return "pause"

    def _route_after_cancel_appointment(self, state: ClinicState) -> str:
        print('calling _route_after_cancel_appointment kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        if state.get("needs_clarification"):
            return END
        return "pause"

    def _route_after_prompt_doctors(self, state: ClinicState) -> str:
        print('calling _route_after_prompt_doctors kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        if state.get("needs_clarification"):
            return "confirm_appointment"
        return "prompt_doctors"

    def _route_after_check_appointment_status(self, state: ClinicState) -> str:
        print('calling _route_after_process_cancel kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        if state.get("needs_clarification"):
            return END
        return "pause"
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
        workflow.add_node("edit_appointment", self.edit_appointment)
        workflow.add_node("cancel_appointment", self.cancel_appointment)
        workflow.add_node("check_appointment_status", self.check_appointment_status)
        workflow.add_node("prompt_doctors", self.prompt_doctors)
        workflow.add_node("wrap_up", self.wrap_up)
        workflow.add_node("intro", self.intro)
        workflow.add_node("pause", self.pause)

        workflow.set_entry_point("classify_intent")
        workflow.add_conditional_edges("greet", self._route_after_greet)
        workflow.add_conditional_edges("classify_intent", self._route_after_classify)
        workflow.add_conditional_edges("create_appointment", self._route_after_create_appointment)
        workflow.add_conditional_edges("edit_appointment", self._route_after_edit_appointment)
        workflow.add_conditional_edges("cancel_appointment", self._route_after_cancel_appointment)
        workflow.add_conditional_edges("prompt_doctors", self._route_after_prompt_doctors)
        workflow.add_conditional_edges("check_appointment_status", self._route_after_check_appointment_status)
        workflow.add_conditional_edges("wrap_up", self._route_after_wrap_up)
        # workflow.add_conditional_edges("intro", "classify_intent")

        return workflow.compile()

    async def process_message(self, clinic_phone: str, user_input: str) -> str:
        state = state_manager.get_state(clinic_phone)
        state["user_input"] = user_input
        state["clinic_phone"] = clinic_phone
        state["needs_clarification"] = False

        final_response = None
        async for output in self.graph.astream(
            state,
            config={"configurable": {"session_id": clinic_phone}}
        ):
            logger.info(f"Node output: {output}")
            # state_manager.clear_state(clinic_phone)

        return final_response or "Something went wrong. Please try again."
