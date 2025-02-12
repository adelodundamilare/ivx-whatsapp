
from app.managers.conversation import ConversationManager
from app.models.models import Message
from app.services import whatsapp as whatsapp_service
from app.utils.logger import setup_logger


logger = setup_logger("engine", "engine.log")

class AppointmentOrchestrator:
    def __init__(self):
        self.conversation_manager = ConversationManager()


    async def process_message(self, message: Message):
        try:
            response = await self.conversation_manager.handle_conversation(
                message.phone_number,
                message.content
            )
            await self.send_response(message, response)

        except Exception as e:
            logger.error(f"Error in message processing: {str(e)}")
            await self.send_response(
                message.phone_number,
                "I apologize, but I'm having trouble processing your request. Please try again in a moment."
            )

    async def send_response(self, message: Message, response: str):
        try:
            await whatsapp_service.send_message(
                message.business_phone_number_id,
                message.phone_number,
                response,
                message.message_id
            )
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
