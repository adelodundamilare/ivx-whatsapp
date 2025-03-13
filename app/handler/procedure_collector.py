from typing import Any, Dict, List
from app.models.models import Message
from app.services.bubble_client import bubble_client
from app.utils.collect_data import DataCollector
from app.utils.helpers import invoke_ai, send_response
from app.utils.state_manager import StateManager


class ProcedureCollector:
    def __init__(self, intent: str, message: Message):
        self.message = message
        self.state_manager = StateManager()
        self.state = self.state_manager.get_state(message.phone_number)
        self.clinic_phone = self.state.get("clinic_phone", "")
        self.user_input = self.state.get("user_input", "")
        self.intent = intent
        self.full_name = self.state.get("full_name", "")
        self.clinic_name = self.state.get("clinic_name", "")

        self.appointment = self.state.get("appointment", {})
        self.procedure_type = self.appointment.get("procedure_type", "")
        self.date = self.appointment.get("date", "")
        self.time = self.appointment.get("time", "")
        self.patient_name = self.appointment.get("patient_name", "")
        self.location = self.appointment.get("location", "")
        self.patient_gender = self.appointment.get("patient_gender", "")
        self.additional_note = self.appointment.get("additional_note", "")
        self.confirmation_status = self.appointment.get("confirmation_status")
        self.clarification_attempts = self.state.get("clarification_attempts", 0)

        self.collector = DataCollector(self.clinic_phone, self.user_input)
        self.required_fields = ["procedure_type", "patient_gender", "location", "patient_name", "date", "time"]
        self.optional_fields = ["additional_note"]

    async def process(self):
        if self.confirmation_status == "PENDING":
            result = await self._handle_confirmation_response()
            return result

        if self._has_missing_required_fields():
            await self._collect_missing_fields()

            if self._has_missing_required_fields():
                await self._create_clarification_state()
                return self.collector.update_state({
                    "needs_clarification": True
                })

        if self.confirmation_status != "CONFIRMED":
            await self._request_confirmation()
            return self._update_state_data({"confirmation_status":"PENDING"},
                                           needs_clarification=True)

        await self._handle_confirmed_procedure()
        return self._update_state_data(needs_clarification=False, intent=None, appointment={})

    def _has_missing_required_fields(self) -> bool:
        current_data = self._get_current_data()
        missing = self.collector.get_missing_fields(self.required_fields, current_data)
        return len(missing) > 0

    def _get_current_data(self) -> Dict[str, Any]:
        return {
            "procedure_type": self.procedure_type,
            "patient_gender": self.patient_gender,
            "date": self.date,
            "time": self.time,
            "patient_name": self.patient_name,
            "location": self.location,
            "additional_note": self.additional_note
        }

    def _get_missing_fields(self) -> List[str]:
        current_data = self._get_current_data()
        return self.collector.get_missing_fields(self.required_fields, current_data)

    async def _collect_missing_fields(self) -> None:
        missing_fields = self._get_missing_fields()
        if not missing_fields:
            return

        await self._extract_entities()

        # all_fields = self.required_fields + self.optional_fields
        # extracted_data = await self.collector.extract_entities(all_fields)

        # update_data = dict(self.appointment)
        # for field, value in extracted_data.items():
        #     update_data[field] = value
        #     if field == "procedure_type":
        #         self.procedure_type = value
        #     elif field == "patient_name":
        #         self.patient_name = value
        #     elif field == "patient_gender":
        #         self.patient_gender = value
        #     elif field == "date":
        #         self.date = value
        #     elif field == "time":
        #         self.time = value
        #     elif field == "location":
        #         self.location = value
        #     elif field == "additional_note":
        #         self.additional_note = value

        # if extracted_data:
        #     self.collector.update_state({"appointment": update_data})

    async def _create_clarification_state(self) -> Dict[str, Any]:
        """Request missing information from user"""
        missing_fields = self._get_missing_fields()
        if not missing_fields:
            return

        print(missing_fields, 'missing_fieldssssssssssssssssssssssssss')

        if len(missing_fields) == 1:
            prompt = f"Could you kindly provide the {missing_fields[0]} for the appointment? 😊"
        else:
            prompt = f"Could you kindly provide the following information for the appointment? 😊: {', '.join(missing_fields)}"

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
        """Show summary and ask user to confirm details"""
        procedure_summary = (
            f"Procedure type: {self.procedure_type}\n"
            f"Date: {self.date}\n"
            f"Time: {self.time}"
        )

        if self.additional_note:
            procedure_summary += f"\nAdditional note: {self.additional_note}"

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
            self.confirmation_status = "CONFIRMED"
            self._update_state_data({"confirmation_status":"CONFIRMED"})
            return await self.process()

        if intent == 'CHANGE_REQUEST':
            update_data = await self._extract_entities()
            await self._request_confirmation()
            return self._update_state_data({**update_data, "confirmation_status":"PENDING"}, needs_clarification=True, intent=self.intent)

        prompt = f"""
Here is the appointment summary:

- 📅 Date: {self.date}
- 🕒 Time: {self.time}
- 🏥 Procedure Type: {self.procedure_type}
- 👤 Patient Name: {self.patient_name}
- 📍 Appointment Location: {self.location}
- ⚧️ Patient Gender: {self.patient_gender}
- 📝 Additional Note: {self.additional_note}

Could you kindly confirm if everything looks good or let me know what you'd like to update? 😊

"""
        await self._send_response(self.clinic_phone, prompt)
        return self._update_state_data({"confirmation_status":"PENDING"}, needs_clarification=True)


    async def _handle_confirmed_procedure(self) -> None:
        procedure_data = {
            "service_type": self.procedure_type,
            "date": self.date,
            "time": self.time,
            "additional_note": self.additional_note,
            "clinic_phone": self.clinic_phone,
            "full_name": self.full_name,
            "clinic_name": self.clinic_name
        }

        # result = await bubble_client.create_appointment(procedure_data)
        # print(result, 'bubble result')

        # if it's successful, update user

        # Thank the user and inform them about next steps
        prompt = f"Thank the user for confirming the procedure details. Let them know you'll now look for available doctors for their {self.procedure_type} on {self.date} at {self.time}."
        response = await invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)

    async def _send_response(self, phone: str, message: str) -> None:
        """Send response to user"""
        # This would be implemented by the parent class
        await send_response(phone, message, message=self.message)

    def _update_state_data(self, appointment_updates=None, **state_updates):
        state_update = dict(state_updates)  # Create a copy of state_updates

        if appointment_updates:
            updated_appointment = self.appointment.copy()

            for field, value in appointment_updates.items():
                updated_appointment[field] = value

            state_update["appointment"] = updated_appointment
        else:
            state_update["appointment"] = self.appointment.copy()

        return self.collector.update_state(state_update)

    async def _extract_entities(self):
        all_fields = self.required_fields + self.optional_fields
        updated_data = await self.collector.extract_entities(all_fields)
        print(updated_data, 'extracted data to be updated')

        if updated_data:
            update_data = dict(self.appointment)
            for field, value in updated_data.items():
                update_data[field] = value
                if field == "procedure_type":
                    self.procedure_type = value
                elif field == "date":
                    self.date = value
                elif field == "time":
                    self.time = value
                elif field == "additional_note":
                    self.additional_note = value

            if update_data:
                self.collector.update_state(update_data)

        return update_data