from app.models.models import Intent, Message
from app.services import database
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.state_manager import StateManager

class OnboardingFlow:
    def __init__(self, message: Message):
        self.message = message
        self.state_manager = StateManager()
        self.state = StateManager().get_state(self.message.phone_number)
        self.whatsapp_service = WhatsAppBusinessAPI(message)

    async def process(self):
        # fetch if is first time user ==> user's with language not set
        # if first time user, introduce bot
        # present language options and ask user to select
        # after language is selected, collect clinic data and that'll be all
        # to change language, ask them to type help

        # if not first time user, fetch clinic data
        # prom
        clinic_data = await self.fetch_clinic_data()

        if clinic_data:
            return clinic_data

        await self.register_new_clinic()

    async def fetch_clinic_data(self):
        # first find data in local storage or redis

        if self.state.clinic_data:
            return self.state.clinic_data

        try:
            res = await database.find_clinic_by_phone(self.message.phone_number)
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

        print(self.state, 'state data >>>>>>>>>>>>')

        await self.whatsapp_service.send_text_message(message="""
Welcome to IVX AIA! 🎉

We're excited to have you on board! IVX AIA is your intelligent AI assistant, designed to streamline doctor appointment bookings for your clinic. Our goal is to make scheduling effortless, ensuring patients get the care they need while saving your team valuable time.

To get started, please tell us your name and your clinic name; e.g (Name: Franca Gold, Clinic Name: Bob Specialist)
""")

    def save_data_to_db(self, clinic):
        pass