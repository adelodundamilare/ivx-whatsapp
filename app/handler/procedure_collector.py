import random
import string
from typing import Any, Dict, List
from app.models.models import Message
from app.services.bubble_client import bubble_client
from app.utils import helpers
from app.utils.collect_data import DataCollector
from app.utils.helpers import invoke_ai, send_response
from app.utils.state_manager import StateManager


class ProcedureCollector:
    def __init__(self, intent: str, message: Message):
        self.message = message
        self.state_manager = StateManager()
        self.clinic_phone = self.state.get("clinic_phone", "")
        self.user_input = self.state.get("user_input", "")
        self.intent = intent
        self.full_name = self.state.get("full_name", "")
        self.clinic_name = self.state.get("clinic_name", "")

        self.collector = DataCollector(self.clinic_phone, self.user_input)
        self.required_fields = ["procedure_type", "patient_gender", "location", "patient_name", "patient_age_range", "date", "time"]
        self.optional_fields = ["additional_note"]

    @property
    def state(self):
        return self.state_manager.get_state(self.message.phone_number)

    async def process(self):
        if self.state.get("confirmation_status") == "PENDING":
            result = await self._handle_confirmation_response()
            return result

        if self._has_missing_required_fields():
            await self._collect_missing_fields()

            if self._has_missing_required_fields():
                await self._create_clarification_state()
                return self.collector.update_state({
                    "needs_clarification": True
                })

        if self.state.get("confirmation_status") != "CONFIRMED":
            await self._request_confirmation()
            return self._update_state_data(confirmation_status="PENDING",
                                           needs_clarification=True)

        await self._handle_confirmed_procedure()
        return self._update_state_data(needs_clarification=False, intent=None)

    def _has_missing_required_fields(self) -> bool:
        current_data = self._get_current_data()
        missing = self.collector.get_missing_fields(self.required_fields, current_data)
        return len(missing) > 0

    def _get_current_data(self) -> Dict[str, Any]:
        state = self.state

        current_data = {
            "procedure_type": state.get("procedure_type"),
            "patient_gender": state.get("patient_gender"),
            "date": state.get("date"),
            "time": state.get("time"),
            "patient_name": state.get("patient_name"),
            "location": state.get("location"),
            "additional_note": state.get("additional_note"),
            "patient_age_range": state.get("patient_age_range"),
        }

        return current_data

    def _get_missing_fields(self) -> List[str]:
        current_data = self._get_current_data()
        return self.collector.get_missing_fields(self.required_fields, current_data)

    async def _collect_missing_fields(self) -> None:
        missing_fields = self._get_missing_fields()
        if not missing_fields:
            return

        await self._extract_entities()

    async def _create_clarification_state(self) -> Dict[str, Any]:
        """Request missing information from user"""
        missing_fields = self._get_missing_fields()
        if not missing_fields:
            return

        print(missing_fields, 'missing_fieldssssssssssssssssssssssssss')

        if len(missing_fields) == 1:
            prompt = f"Respond to the user's message: {self.user_input} then ask to kindly provide the {missing_fields[0]} for the appointment? 😊"
        else:
            prompt = f"Respond to the user's message: {self.user_input} then ask to kindly provide the following information for the appointment? 😊: {', '.join(missing_fields)}"

        response = await invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)

    async def _request_clarification(self) -> None:
        missing_fields = self._get_missing_fields()

        if missing_fields:
            missing_display = [field.replace('_', ' ') for field in missing_fields]
            fields_text = ", ".join(missing_display[:-1]) + (" and " if len(missing_display) > 1 else "") + missing_display[-1] if missing_display else ""

            prompt = f"Politely ask the user to provide their {fields_text} for the procedure. Be conversational and friendly."
        else:
            await self._request_confirmation()
            return

        response = await invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)

    async def _request_confirmation(self) -> None:
        procedure_summary = f"""
Here is the appointment summary:

- 📅 Date: {self.state.get("date")}
- 🕒 Time: {self.state.get("time")}
- 🏥 Procedure Type: {self.state.get("procedure_type")}
- 👤 Patient Name: {self.state.get("patient_name")}
- 📍 Appointment Location: {self.state.get("location")}
- 📝 Patient Age: {self.state.get("patient_age_range")}
- ⚧️ Patient Gender: {self.state.get("patient_gender")}
- 📝 Additional Note: {self.state.get("additional_note")}

Could you kindly confirm if everything looks good or let me know what you'd like to update? 😊
"""

        prompt = f"Show the user a summary of the procedure details they provided: {procedure_summary}. Ask them to confirm if everything is correct, or specify what they'd like to change. Be conversational and friendly."

        response = await invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)

    async def _handle_confirmation_response(self):
        prompt =f"""
Based on the following user response, determine the intent:

Possible intents:
- CONFIRM: If the user confirms the appointment change.
- CHANGE_REQUEST: If the user requests a change or provides new details (e.g., update date or name)
- OTHER: If the response is unclear or unrelated.

User input: "{self.user_input}"

Respond with only the intent label.
"""

        intent = await invoke_ai(prompt, self.clinic_phone)
        print(intent, '_handle_confirmation_response confirm intent')

        if intent == 'CONFIRM':
            self.state["confirmation_status"] = "CONFIRMED"
            self._update_state_data(confirmation_status="CONFIRMED")
            return await self.process()

        if intent == 'CHANGE_REQUEST':
            await self._extract_entities()
            await self._request_confirmation()
            return self._update_state_data(confirmation_status="PENDING", needs_clarification=True, intent=self.intent)

        prompt = f"""
Here is the appointment summary:

- 📅 Date: {self.state.get("date")}
- 🕒 Time: {self.state.get("time")}
- 🏥 Procedure Type: {self.state.get("procedure_type")}
- 👤 Patient Name: {self.state.get("patient_name")}
- 📝 Patient Age: {self.state.get("patient_age_range")}
- 📍 Appointment Location: {self.state.get("location")}
- ⚧️ Patient Gender: {self.state.get("patient_gender")}
- 📝 Additional Note: {self.state.get("additional_note")}

Could you kindly confirm if everything looks good or let me know what you'd like to update? 😊
"""
        await self._send_response(self.clinic_phone, prompt)
        return self._update_state_data(confirmation_status="PENDING", needs_clarification=True)


    async def _handle_confirmed_procedure(self) -> None:
        booking_code = self._generate_booking_code()
        procedure_data = {
            "service_type": self.state.get("procedure_type"),
            "date": self.state.get("date"),
            "time": self.state.get("time"),
            "additional_note": self.state.get("additional_note"),
            "patient_name": self.state.get("patient_name"),
            "patient_gender": self.state.get("patient_gender"),
            "location": self.state.get("location"),
            "phone_number": self.state.get("clinic_phone"),
            "patient_age_range": self.state.get("patient_age_range"),
            "code": booking_code
        }

        try:
            result = await bubble_client.create_appointment(procedure_data)
            print(result, 'bubble result')
        except Exception as e:
            print(f"Error in _handle_confirmed_procedure: {str(e)}")
            return await self._send_response(self.clinic_phone, "An error occurred while scheduling the procedure. Please try again later.")

        prompt = f"Thank the user for confirming the procedure details. Let them know you'll now look for available doctors for their {self.state.get('procedure_type')} on {self.state.get('date')} at {self.state.get('time')} and there booking code - which they need to keep safe for future use -  is {booking_code} then ask if they have any other thing they'll need help with"
        response = await invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset the state to initial values"""
        print('calling _reset_state')
        reset_state = {
            "procedure_type": None,
            "date": None,
            "time": None,
            "additional_note": None,
            "patient_name": None,
            "patient_gender": None,
            "location": None,
            "patient_age_range": None,
            "confirmation_status": None,
            "needs_clarification": False,
            "intent": None
        }
        self.collector.update_state(reset_state)

    async def _send_response(self, phone: str, message: str) -> None:
        await send_response(phone, message, message=self.message)

    def _update_state_data(self,  **state_updates):
        state_update = dict(state_updates)
        return self.collector.update_state(state_update)

    async def _extract_entities(self):
        all_fields = self.required_fields + self.optional_fields
        updated_data = await self.collector.extract_entities(all_fields)
        print(updated_data, 'extracted data to be updated')

        if updated_data:
            update_data = dict(self.state)

            if "date" in updated_data:
                validated_date = helpers.validate_and_parse_date(updated_data["date"])
                if validated_date:
                    updated_data["date"] = validated_date
                # else:
                #     return {"error": f"Invalid date format: {updated_data['date']}"}

            if "time" in updated_data:
                validated_time = helpers.validate_and_parse_time(updated_data["time"])
                if validated_time:
                    updated_data["time"] = validated_time
                # else:
                #     return {"error": f"Invalid time format: {updated_data['time']}"}

            for field, value in updated_data.items():
                update_data[field] = value

            if update_data:
                self.collector.update_state(update_data)

            return update_data
        else:
            return dict(self.state)

    def _generate_booking_code(self):
        random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return 'IVX' + random_code