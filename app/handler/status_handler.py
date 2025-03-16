from datetime import datetime
from app.models.models import Message
from app.services.bubble_client import bubble_client
from app.utils import helpers
from app.utils.collect_data import DataCollector
from app.utils.helpers import invoke_ai, send_response
from app.utils.state_manager import StateManager


class StatusHandler:
    def __init__(self, intent: str, message: Message):
        self.message = message
        self.state_manager = StateManager()
        self.clinic_phone = self.state.get("clinic_phone", "")
        self.user_input = self.message.content
        self.intent = intent

        self.collector = DataCollector(self.clinic_phone, self.user_input)

    @property
    def state(self):
        return self.state_manager.get_state(self.message.phone_number)

    async def process(self):
        if await self._is_valid_booking_code():
            appointment = await self._fetch_appointment()

            if appointment:
                return await self._show_appointment_status(appointment)

        if await self._request_appointment_fetch():
            return await self._fetch_latest_appointment()

        await self._request_booking_code()
        return self._update_state_expect_resp()

    async def _request_booking_code(self):
        prompt = "Politely ask the user to provide a valid booking code for the appointment whose status they want to check or confirm if they prefer we fetch some of their latest appointments. Be conversational and friendly."
        response = await invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)

    async def _fetch_appointment(self):
        booking_code = self.state.get("booking_code")

        try:
            appointment = await bubble_client.find_appointment_by_code(booking_code)
        except Exception as e:
            prompt = "Politely inform user we can't find an appointment with the provided booking code and suggest they try again."
            response = await invoke_ai(prompt, self.clinic_phone)
            await self._send_response(self.clinic_phone, response)
            return False

        if not appointment:
            prompt = "Politely inform user we can't find an appointment with the provided booking code and suggest they try again."
            response = await invoke_ai(prompt, self.clinic_phone)
            await self._send_response(self.clinic_phone, response)

        print(appointment, 'appointment')
        self._update_state_expect_resp(**{"appointment": appointment})
        return appointment

    async def _fetch_latest_appointment(self):

        try:
            appointments = await bubble_client.find_latest_appointments(self.clinic_phone)

            if not appointments:
                prompt = f"Inform {self.state.get('full_name', '')} that no appointments were found to cancel, and ask if they'd like to book one instead."
                response = await invoke_ai(prompt, self.clinic_phone)
                return await self._send_response(self.clinic_phone, response)

            result = "Your Upcoming Appointments:\n\nPlease copy the *Booking Code* of the appointment you'd like to cancel and paste it in your response. 😊\n\n"

            for i, data in enumerate(appointments, 1):
                result += f"Booking Code: {data.get('code')}\n"
                result += f"Patient Name: {data.get('patient_name')}\n"
                result += f"Service Type: {data.get('service_type')}\n"
                result += f"Appointment Date: {data.get('date')}\n"

                if i < len(appointments):
                    result += "\n━━━━━━━━━━━━━━━━━━━━\n"

            return await self._send_response(self.clinic_phone, result)
        except Exception as e:
            print(f"Error fetching latest appointments {str(e)}")
            prompt = "User is trying to access their appointment details, but we encountered a technical issue while retrieving the information. Politely apologize for the inconvenience, explain that we're experiencing a temporary problem with our booking system, and ask them to try again in a few minutes or contact the clinic directly."
            response = await invoke_ai(prompt, self.clinic_phone)
            return await self._send_response(self.clinic_phone, response)


    async def _request_appointment_fetch(self):
        prompt =f"""
Based on the following user response, determine the intent:

Possible intents:
- FETCH_ITEMS: If the user doesn't have a booking code handy and wants to fetching some of their latest appointments
- OTHER: If the response is unclear or unrelated.

User input: "{self.user_input}"

Respond with only the intent label.
"""
        intent = await invoke_ai(prompt, self.clinic_phone)
        print(intent, '_request_appointment_fetch intent')

        if intent == 'FETCH_ITEMS':
            return True

        return False

    async def _handle_valid_booking_code(self, booking_code: str):
        try:
            appointment = await self._fetch_appointment()
        except Exception as e:
            prompt = "Politely inform user we can't find an appointment with the provided booking code and suggest they try again."
            response = await invoke_ai(prompt, self.clinic_phone)
            return await self._send_response(self.clinic_phone, response)
        self._update_state_expect_resp(**{"appointment": appointment, "booking_code": booking_code})

    async def _is_valid_booking_code(self):
        booking_code = await self.collector.extract_entity("booking_code")
        if not booking_code:
            return False

        if not booking_code[:3].upper() == "IVX":
            return False

        self._update_state_expect_resp(**{"booking_code": booking_code})
        return True

    async def _show_appointment_status(self, appointment: dict):
        prompt = f"""
Here is the appointment status:

- 📅 Date: {appointment.get("date")}
- 🕒 Time: {appointment.get("time")}
- 🏥 Procedure Type: {appointment.get("service_type")}
- 👤 Patient Name: {appointment.get("patient_name")}
- 📝 Patient Age: {appointment.get("patient_age_range")}
- 📍 Appointment Location: {appointment.get("location")}
- ⚧️ Patient Gender: {appointment.get("patient_gender")}
- 📝 Additional Note: {appointment.get("additional_note")}
- 👤 Status: {appointment.get("status")}
"""
        response = await invoke_ai(prompt, self.clinic_phone)
        await self._send_response(self.clinic_phone, response)
        return self._update_state_simple(**{"needs_clarification": False, "intent": None})

    # UTILITIES

    async def _send_response(self, phone: str, message: str) -> None:
        await send_response(phone, message, message=self.message)

    def _update_state_expect_resp(self, **kwargs):
        update_data = {
            "intent": self.intent,
            "needs_clarification": True
        }

        if kwargs:
            update_data.update(kwargs)

        self.collector.update_state(update_data)

    def _update_state_simple(self, **kwargs):
        update_data = {}

        if kwargs:
            update_data.update(kwargs)

        self.collector.update_state(update_data)

