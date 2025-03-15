from typing import Any, Dict, List
from app.models.models import ClinicState, Message
from app.services.bubble_client import bubble_client
from app.utils.collect_data import DataCollector
from app.utils.helpers import invoke_ai, send_response
from app.utils.state_manager import StateManager
from app.utils.logger import setup_logger


logger = setup_logger("greet_handler", "greet_handler.log")

class GreetingHandler:
    def __init__(self, intent: str, message: Message):
        self.state_manager = StateManager()
        self.state = self.state_manager.get_state(message.phone_number)
        self.message = message
        self.intent = intent
        self.clinic_phone = self.state.get("clinic_phone", "")
        self.user_input = self.state.get("user_input", "")
        self.full_name = self.state.get("full_name", "")
        self.clinic_name = self.state.get("clinic_name", "")
        self.collector = DataCollector(self.clinic_phone, self.user_input)
        self.required_fields = ["full_name", "clinic_name"]

    async def process(self) -> ClinicState:
        if self._has_missing_fields():
            await self._try_database_lookup()

            if self._has_missing_fields():
                await self._try_extract_from_input()

                if self._has_missing_fields():
                    await self._request_clarification()
                    return self.collector.update_state({"needs_clarification": True, "intent": self.intent})

        await self._send_greeting()
        return self.collector.update_state({"needs_clarification": False, "intent": None})

    def _has_missing_fields(self) -> bool:
        current_data = self._get_current_data()
        missing = self.collector.get_missing_fields(self.required_fields, current_data)
        return len(missing) > 0

    def _get_current_data(self) -> Dict[str, Any]:
        return {
            "full_name": self.full_name,
            "clinic_name": self.clinic_name
        }

    def _get_missing_fields(self) -> List[str]:
        current_data = self._get_current_data()
        return self.collector.get_missing_fields(self.required_fields, current_data)

    async def _try_database_lookup(self) -> None:
        missing_fields = self._get_missing_fields()
        if not missing_fields:
            return

        # Lookup in database
        # clinic_data = await bubble_client.find_clinic_by_phone(self.clinic_phone)
        clinic_data = {}  # Placeholder for database result

        # Update from database if available
        if clinic_data:
            update_data = {}
            for field in missing_fields:
                if field in clinic_data and self.collector._is_valid_value(clinic_data[field]):
                    update_data[field] = clinic_data[field]
                    if field == "full_name":
                        self.full_name = clinic_data[field]
                    elif field == "clinic_name":
                        self.clinic_name = clinic_data[field]

            # Update state with data from database
            if update_data:
                self.collector.update_state(update_data)

    async def _try_extract_from_input(self) -> None:
        missing_fields = self._get_missing_fields()
        if not missing_fields:
            return

        extracted_data = await self.collector.extract_entities(missing_fields)

        if extracted_data:
            update_data = {}
            for field, value in extracted_data.items():
                update_data[field] = value
                if field == "full_name":
                    self.full_name = value
                elif field == "clinic_name":
                    self.clinic_name = value

            self.collector.update_state(update_data)

            if not self._has_missing_fields():
                # @todo: confirm input and proceed when user is cool, handle reject
                await self._save_to_database()

    async def _save_to_database(self) -> None:
        """Save collected data to database"""
        logger.info('calling::: _save_to_database')
        await bubble_client.create_clinic(data={
            "full_name": self.full_name,
            "clinic_name": self.clinic_name,
            "phone_number": self.clinic_phone
        })

    async def _request_clarification(self) -> None:
        """Request missing information from user"""
        missing_fields = self._get_missing_fields()
        if not missing_fields:
            return

        missing_field = missing_fields[0]  # Ask for one field at a time
        field_display_name = missing_field.replace('_', ' ')

        prompt = f"Respond warmly to this user message - {self.user_input} - as IVX AI Assistant, an assistant that helps clinics connect with doctors. If appropriate, acknowledge the user's message first. Then, ask for their {field_display_name} in a friendly, conversational way."
        response = await invoke_ai(prompt, self.clinic_phone)
        await send_response(self.clinic_phone, response,  message=self.message)

    async def _send_greeting(self) -> None:
        """Send greeting message with collected information"""
        prompt = f"Respond warmly to the user's message: '{self.user_input}'. If appropriate, greet them using their name ({self.full_name}) and acknowledge the clinic they represent ({self.clinic_name}). Then, guide the conversation by asking how you can assist them today. Offer options such as booking, canceling, or checking appointments."
        response = await invoke_ai(prompt, self.clinic_phone)
        await send_response(clinic_phone=self.clinic_phone, response_message=response, message=self.message)

    async def general_response(self) -> None:
        prompt = (f"You are a warm and professional medical assistant that helps clinics schedule, reschedule, edit and manage doctor appointments. "
         f"Keep responses clear, concise, and friendly while ensuring accuracy in appointment details. "
         f"Use the conversation history to maintain context and provide relevant responses. "
         f"If needed, ask relevant follow-up questions to confirm appointment details before proceeding. "
         f"ensure users confirm inputs before proceeding.")
        response = await invoke_ai(prompt, self.clinic_phone)
        await send_response(clinic_phone=self.clinic_phone, response_message=response, message=self.message)
        return self.collector.update_state({"needs_clarification": True})
