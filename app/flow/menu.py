from app.flow.appointment import AppointmentFlow
from app.models.models import ConfirmIntent, Intent, Message
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.state_manager import StateManager

class MenuFlow:
    def __init__(self, message: Message):
        self.message = message
        self.state_manager = StateManager()
        self.state = StateManager().get_state(self.message.phone_number)
        self.whatsapp_service = WhatsAppBusinessAPI(message)

    async def handle_menu_select_response(self):
        response = self.message.content

        if response == "CREATE_APPOINTMENT":
            await self.create_appointment()
        elif response == "CHECK_APPOINTMENT_STATUS":
            await self.check_appointment_status()
        elif response == "UPDATE_APPOINTMENT":
            await self.update_appointment()
        elif response == "CANCEL_APPOINTMENT":
            await self.cancel_appointment()
        else:
            await self.whatsapp_service.send_text_message("Invalid option selected. Please try again.")

    async def create_appointment(self):
        self.state_manager.update_state(
            self.message.phone_number,
            current_intent=Intent.CREATE_APPOINTMENT
        )
        await AppointmentFlow(self.message).start()

    async def update_appointment(self):
        await self.whatsapp_service.send_text_message(
            "Please provide your appointment ID. 🔍\n\n"
            "This helps us quickly locate your booking."
        )

    async def cancel_appointment(self):
        await self.whatsapp_service.send_text_message(
            "Please provide your appointment ID. 🔍\n\n"
            "This helps us quickly locate your booking."
        )

    async def check_appointment_status(self):
        if self.state.confirm_intent == ConfirmIntent.REQUEST_ID:
            # validate id
            # show appointment data
            await self.whatsapp_service.send_text_message("You're appointment with ID {} is still processing".format(self.message.content))
            return

        self.state_manager.update_state(
            self.message.phone_number,
            current_intent=Intent.CHECK_STATUS,
            confirm_intent=ConfirmIntent.REQUEST_ID
        )
        await self.whatsapp_service.send_text_message(
            "To check your appointment status, please provide your appointment ID. 🔍\n\n"
            "This helps us quickly locate your booking."
        )