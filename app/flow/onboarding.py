from app.models.models import ConfirmIntent, Intent, Message
from app.services.bubble_client import bubble_client
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.state_manager import StateManager
from app.models.models import main_menu_options

class OnboardingFlow:
    def __init__(self, message: Message):
        self.message = message
        self.state_manager = StateManager()
        self.state = StateManager().get_state(self.message.phone_number)
        self.whatsapp_service = WhatsAppBusinessAPI(message)

    async def start(self):
        clinic_data = await self.fetch_clinic_data()

        if not clinic_data:
            await self.register_new_clinic()
            return

        await self.show_menu()

    async def show_menu(self):

        self.state_manager.update_state(
            self.message.phone_number,
            current_intent=Intent.REQUEST_MENU_OPTIONS
        )
        await self.whatsapp_service.send_text_message(message="""
Welcome to IVX AIA! 🎉

We're thrilled to have you here! IVX AIA is your intelligent AI assistant, designed to simplify doctor appointment scheduling for your clinic.

How can we assist you today?
""")

        await self.whatsapp_service.send_interactive_list(
            header_text="",
            body_text="Please select an option from this menu",
            button_text="View Options",
            sections=main_menu_options
        )


    async def fetch_clinic_data(self):
        # first find data in local storage or redis
        if self.state.confirm_intent == ConfirmIntent.REQUEST_CLINIC_DATA:
            print(self.state.message, 'confirm response...')
            return

        if self.state.clinic_data:
            return self.state.clinic_data

        try:
            res = await bubble_client.find_clinic_by_phone(self.message.phone_number)

            self.state_manager.update_state(
                self.message.phone_number,
                clinic_data=res
            )
            return res
        except Exception as e:
            print(e)
            return False

    async def register_new_clinic(self):
        new_clinic_data = await self.get_clinic_info()
        self.save_data_to_db(new_clinic_data)

    async def get_clinic_info(self):

        self.state = self.state_manager.update_state(
            self.message.phone_number,
            current_intent=Intent.REQUEST_CLINIC_DATA
        )

        await self.whatsapp_service.send_text_message(message="""Welcome to IVX AIA! 🎉, I'm your AI assistant (AIA), here to help with doctor appointment scheduling.""")
        await self.whatsapp_service.send_text_message(message="""To get started, please provide your name and clinic name in this format: **Name: [Your Name], Clinic Name: [Your Clinic Name]**  """)

    async def collect_clinic_data(self):
        pass

    def save_data_to_db(self, clinic):
        pass