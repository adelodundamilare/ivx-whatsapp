
import asyncio
from app.managers.conversation import ConversationManager
from app.models.models import Message
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.logger import setup_logger
from app.utils.state_manager import state_manager

logger = setup_logger("engine", "engine.log")
processing_message = False

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

            state_manager.set_is_processing(message.phone_number, False)

        except Exception as e:
            logger.error(f"Error in message processing: {str(e)}")
            await self.send_response(
                message.phone_number,
                "I apologize, but I'm having trouble processing your request. Please try again in a moment."
            )

    async def send_response(self, message: Message, response: str):
        try:
            whatsapp_service = WhatsAppBusinessAPI(message.business_phone_number_id)
            await whatsapp_service.send_text_message(
                to_number=message.phone_number,
                message=response
            )
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")


    async def send_response(self, message: Message, response: str) -> bool:
        try:
            whatsapp_service = WhatsAppBusinessAPI(message.business_phone_number_id)

            async with asyncio.timeout(30.0):
                await whatsapp_service.send_text_message(
                    to_number=message.phone_number,
                    message=response
                )

                try:
                    await whatsapp_service.mark_message_as_read(
                        message_id=message.message_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to mark as read: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False
