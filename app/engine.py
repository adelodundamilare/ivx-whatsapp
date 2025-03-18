
import traceback
from app.managers.conversation import ConversationManager
from app.models.models import Message
from app.services.bubble_client import bubble_client
from app.services.doctor_assitant import DoctorAssistant
from app.services.langgraph import ClinicAssistant
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.logger import setup_logger
from app.utils.state_manager import StateManager

logger = setup_logger("engine", "engine.log")
clinic_agents = {}

class AppointmentOrchestrator:
    def __init__(self, message: Message):
        self.message = message
        self.whatsapp_service = WhatsAppBusinessAPI(message)
        self.conversation_manager = ConversationManager()
        self.state_manager = StateManager()
        self.state = StateManager().get_state(self.message.phone_number)

    async def process_message(self):

        try:
            user_phone = self.message.phone_number

            try:
                is_doctor = await bubble_client.is_doctor(user_phone)

                if is_doctor:
                    assistant = DoctorAssistant(message=self.message)
                    return await assistant.process_message(phone=user_phone, user_input=self.message.content)
            except Exception as e:
                logger.error(f"Error in message processing: {str(e)}")

            clinic_assistant = ClinicAssistant(message=self.message)
            return await clinic_assistant.process_message(clinic_phone=user_phone, user_input=self.message.content)
        except Exception as e:
            logger.error(f"Error in message processing: {str(e)}")
            traceback.print_exc()

            await self.whatsapp_service.send_text_message("I apologize, but I'm having trouble processing your request. Please try again in a moment.")
        finally:
            self.state_manager.update_state(self.message.phone_number, {"is_processing":False})