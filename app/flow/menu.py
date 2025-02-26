from app.models.models import ConfirmIntent, Intent, Message
from app.services.bubble_client import bubble_client
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
        print(response, 'response...')

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
        await self.whatsapp_service.send_text_message("Yo! we're creating this appointment")

    async def update_appointment(self):
        await self.whatsapp_service.send_text_message("Yo! we're updating this appointment")

    async def cancel_appointment(self):
        await self.whatsapp_service.send_text_message("Yo! we're cancelling this appointment")

    async def check_appointment_status(self):
        await self.whatsapp_service.send_text_message("Yo! we're to check this appointment status")

