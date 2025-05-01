

from typing import Dict
from app.models.models import ClinicState, Message
from app.services.bubble_client import bubble_client
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.doctor_state_manager import DoctorStateManager
from app.utils.helpers import invoke_doctor_ai
from app.utils.logger import setup_logger
from langgraph.graph import StateGraph, END # type: ignore

state_manager = DoctorStateManager()
logger = setup_logger("clinic_assistant", "clinic_assistant.log")

valid_intents = {
    "create_appointment": "create_appointment",
    "edit_appointment": "edit_appointment",
    "cancel_appointment": "cancel_appointment",
    "check_appointment_status": "check_appointment_status",
    "greet": "greet",
}
# memory = ConversationBufferMemory()
class DoctorAssistant:
    def __init__(self, message: Message):
        self.message = message
        self.whatsapp_service = WhatsAppBusinessAPI(message)
        self.state_manager = DoctorStateManager()
        self.user_input = message.content
        self.doctor = self.state.get("doctor", {})
        self.graph = self._build_graph()
    @property
    def state(self):
        return self.state_manager.get_state(self.message.phone_number)

    def _update_state(self, data: Dict):
        self.state_manager.update_state(self.message.phone_number, data)

    # async def greet(self, _: ClinicState):
    #     print('calling greet kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
    #     handler = GreetingHandler(intent="greet", message=self.message)
    #     return await handler.process()

    # async def intro(self, _):
    #     print('calling intro kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
    #     handler = GreetingHandler(intent="greet",message=self.message)
    #     return await handler.general_response()

    async def pause(self, _):
        return

    async def classify_intent(self, _: ClinicState):
        print('calling doctor classify_intent kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        print(self.state, 'calling state classify_intent kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        phone = self.message.phone_number
        appointment = self.state.get("appointment", {})
        doctor = self.state.get("doctor", {})
        full_name = doctor.get("full_name")

        if not appointment or not doctor:
            prompt = f"We cannot process this request at the moment, please try again later."
            await self.whatsapp_service.send_text_message(prompt, phone)
            return


        prompt = f"""
Identify the primary intent of the user's message.

Use the conversation history to maintain context and determine the intent.

Possible intents:
- accept: User accept the invite
- decline: User rejects the invite
- other: Unknown


User message: {self.user_input}

Respond with only the intent label.
"""
        intent = await invoke_doctor_ai(prompt, phone)
        print(intent, 'doctor classify_intent intent kkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk')

        if intent == 'accept':
            prompt = f"Thank you, {full_name}, for accepting the invitation with booking code: {appointment.get('code')}. We look forward to working with you!"
            prompt_clinic = f"Your appointment with booking code: {appointment.get('code')} has been accepted."
            data = {"status": "accepted", "assigned_doctor": doctor.get("_id")}
            await bubble_client.update_appointment(id=appointment.get("_id"), data=data)
            await self.whatsapp_service.send_text_message(prompt, phone)
            await self.whatsapp_service.send_text_message(prompt_clinic, appointment.get("phone_number"))

        if intent == 'decline':
            prompt = f"Thank you, {full_name}, for letting us know. We understand your decision and hope to collaborate in the future."
            await self.whatsapp_service.send_text_message(prompt, phone)


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


    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ClinicState)
        # workflow.add_node("greet", self.greet)
        workflow.add_node("classify_intent", self.classify_intent)
        # workflow.add_node("create_appointment", self.create_appointment)
        # workflow.add_node("edit_appointment", self.edit_appointment)
        # workflow.add_node("cancel_appointment", self.cancel_appointment)
        # workflow.add_node("check_appointment_status", self.check_appointment_status)
        # workflow.add_node("prompt_doctors", self.prompt_doctors)
        # workflow.add_node("wrap_up", self.wrap_up)
        # workflow.add_node("intro", self.intro)
        workflow.add_node("pause", self.pause)

        workflow.set_entry_point("classify_intent")
        # workflow.add_conditional_edges("greet", self._route_after_greet)
        # workflow.add_conditional_edges("classify_intent", self._route_after_classify)
        # workflow.add_conditional_edges("create_appointment", self._route_after_create_appointment)
        # workflow.add_conditional_edges("edit_appointment", self._route_after_edit_appointment)
        # workflow.add_conditional_edges("cancel_appointment", self._route_after_cancel_appointment)
        # workflow.add_conditional_edges("prompt_doctors", self._route_after_prompt_doctors)
        # workflow.add_conditional_edges("check_appointment_status", self._route_after_check_appointment_status)
        # workflow.add_conditional_edges("wrap_up", self._route_after_wrap_up)
        # workflow.add_conditional_edges("intro", "classify_intent")

        return workflow.compile()

    async def process_message(self, phone: str, user_input: str) -> str:
        state = self.state_manager.get_state(phone)
        state["user_input"] = user_input
        state["phone"] = phone
        state["needs_clarification"] = False

        final_response = None
        async for output in self.graph.astream(
            state,
            config={"configurable": {"session_id": phone}}
        ):
            logger.info(f"Node output: {output}")

        return final_response or "Something went wrong. Please try again."
