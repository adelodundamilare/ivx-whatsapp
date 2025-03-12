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
        self.procedure_type = self.state.get("procedure_type", "")
        self.date = self.state.get("date", "")
        self.time = self.state.get("time", "")
        self.patient_name = self.state.get("patient_name", "")
        self.location = self.state.get("location", "")
        self.patient_gender = self.state.get("patient_gender", "")
        self.additional_note = self.state.get("additional_note", "")
        self.confirmation_status = self.state.get("confirmation_status", "")
        self.clarification_attempts = self.state.get("clarification_attempts", 0)

        self.collector = DataCollector(self.clinic_phone, self.user_input)
        self.required_fields = ["procedure_type", "patient_gender", "location", "patient_name", "date", "time"]
        self.optional_fields = ["additional_note"]

    async def process(self):
        if self.confirmation_status == "PENDING":
            return await self._handle_confirmation_response()

        if self._has_missing_required_fields():
            await self._collect_missing_fields()

            if self._has_missing_required_fields():
                await self._create_clarification_state()
                return self.collector.update_state({
                    "needs_clarification": True
                })

        if self.confirmation_status != "CONFIRMED":
            await self._request_confirmation()
            return self.collector.update_state({
                "needs_clarification": True,
                "confirmation_status": "PENDING"
            })

        await self._handle_confirmed_procedure()
        return self.collector.update_state({
            "needs_clarification": False,
            "confirmation_status": "COMPLETED",
            "intent": None
        })

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
        print('collecting missing fields', missing_fields)
        if not missing_fields:
            return

        all_fields = self.required_fields + self.optional_fields
        extracted_data = await self.collector.extract_entities(all_fields)

        update_data = {}
        for field, value in extracted_data.items():
            update_data[field] = value
            if field == "procedure_type":
                self.procedure_type = value
            elif field == "patient_name":
                self.patient_name = value
            elif field == "patient_gender":
                self.patient_gender = value
            elif field == "date":
                self.date = value
            elif field == "time":
                self.time = value
            elif field == "location":
                self.location = value
            elif field == "additional_note":
                self.additional_note = value

        if update_data:
            self.collector.update_state(update_data)

    async def _create_clarification_state(self) -> Dict[str, Any]:
        """Request missing information from user"""
        missing_fields = self._get_missing_fields()
        if not missing_fields:
            return

        print(missing_fields, 'missing_fieldssssssssssssssssssssssssss')

        prompt = f"Respond warmly to this user message - {self.user_input} - as AIA, an assistant helping clinics connect with doctors. Then, ask for their {missing_fields} in a friendly, conversational way."
        response = await invoke_ai(prompt, self.clinic_phone)
        await send_response(self.clinic_phone, response,  message=self.message)

    async def _request_clarification(self) -> None:
        missing_fields = self._get_missing_fields()

        if missing_fields:
            missing_display = [field.replace('_', ' ') for field in missing_fields]
            fields_text = ", ".join(missing_display[:-1]) + (" and " if len(missing_display) > 1 else "") + missing_display[-1] if missing_display else ""

            prompt = f"Politely ask the user to provide their {fields_text} for the procedure. Be conversational and friendly."
        else:
            await self._request_confirmation()
            return

        response = await self._invoke_ai(prompt, self.clinic_phone)
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

        response = await self._invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)

    async def _handle_confirmation_response(self) -> Dict[str, Any]:
        confirmation_check = await self.collector.extract_entity("confirmation")
        change_request = await self.collector.extract_entity("change_request")

        if confirmation_check and confirmation_check.lower() in ["yes", "confirm", "correct", "good", "right"]:
            self.confirmation_status = "CONFIRMED"
            self.collector.update_state({"confirmation_status": "CONFIRMED"})
            return await self.process()

        elif change_request or (self.user_input and not confirmation_check):
            # User wants to change something, or didn't explicitly confirm
            # Extract all fields again to see if they provided updated values
            all_fields = self.required_fields + self.optional_fields
            updated_data = await self.collector.extract_entities(all_fields)

            if updated_data:
                update_data = {}
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

                await self._request_confirmation()
                update_data = {
                    **update_data,
                    "needs_clarification": True,
                    "intent": self.intent,
                    "confirmation_status": "PENDING",
                    # "procedure_type": self.procedure_type,
                    # "date": self.date,
                    # "time": self.time,
                    # "additional_note": self.additional_note
                }
                self.collector.update_state(update_data)
                return update_data
            else:
                prompt = "Ask the user which specific detail they would like to change (procedure type, date, time, or additional note)."
                response = await self._invoke_ai(prompt, self.clinic_phone)
                await self._send_response(self.clinic_phone, response)
                update_data = {
                    "needs_clarification": True,
                    "confirmation_status": "PENDING",
                    # "procedure_type": self.procedure_type,
                    # "intent": self.intent,
                    # "date": self.date,
                    # "time": self.time,
                    # "additional_note": self.additional_note
                }
                self.collector.update_state(update_data)
                return update_data

        prompt = "Politely ask the user to confirm if the details are correct or specify what they would like to change."
        response = await self._invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)
        update_data = {
            "needs_clarification": True,
            "confirmation_status": "PENDING",
        }
        self.collector.update_state(update_data)
        return update_data

    async def _handle_confirmed_procedure(self) -> None:
        procedure_data = {
            "procedure_type": self.procedure_type,
            "date": self.date,
            "time": self.time,
            "additional_note": self.additional_note,
            "clinic_phone": self.clinic_phone,
            "full_name": self.full_name,
            "clinic_name": self.clinic_name
        }

        result = await bubble_client.create_appointment(procedure_data)
        print(result, 'bubble result')

        # if it's successful, update user

        # Thank the user and inform them about next steps
        prompt = f"Thank the user for confirming the procedure details. Let them know you'll now look for available doctors for their {self.procedure_type} on {self.date} at {self.time}."
        response = await self._invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)

    async def _invoke_ai(self, prompt: str, phone: str) -> str:
        """Invoke AI to generate response"""
        # This would be implemented by the parent class
        return await invoke_ai(prompt, phone)

    async def _send_response(self, phone: str, message: str) -> None:
        """Send response to user"""
        # This would be implemented by the parent class
        await send_response(phone, message, message=self.message)