
import traceback
from app.agents import agents
from app.flow.appointment import AppointmentFlow
from app.flow.menu import MenuFlow
from app.flow.onboarding import OnboardingFlow
from app.managers.appointment_dialog import DataType
from app.managers.clinic_dialog import ClinicDialog
from app.managers.conversation import ConversationManager
from app.models.models import Intent, Message
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.logger import setup_logger
from app.utils.state_manager import StateManager

logger = setup_logger("engine", "engine.log")

class AppointmentOrchestrator:
    def __init__(self, message: Message):
        self.message = message
        self.conversation_manager = ConversationManager()
        self.whatsapp_service = WhatsAppBusinessAPI(message)
        self.state_manager = StateManager()
        self.state = StateManager().get_state(self.message.phone_number)

    async def process_message(self):
        try:
            current_intent = await agents.intent_agent(self.message.content)
            print(current_intent,  'current_intent')

            # response = await agents.response_agent(
            #     message=self.message.content,
            #     user_intent=current_intent,
            #     conversation_history=self.state.conversation_history,
            #     appointment_details='',
            # )
            response = await agents.generate_generic_response(
                message=self.message.content,
                conversation_history=self.state.conversation_history
            )
            await self.whatsapp_service.send_text_message(response)
            return

            if current_intent == Intent.REQUEST_CLINIC_DATA:
                await ClinicDialog(self.message, DataType.CLINIC).collect_data()
                return

            if current_intent == Intent.CREATE_APPOINTMENT:
                await AppointmentFlow(self.message).start()
                return

            if current_intent == Intent.REQUEST_MENU_OPTIONS:
                await MenuFlow(self.message).handle_menu_select_response()
                return

            await OnboardingFlow(self.message).start()
        except Exception as e:
            logger.error(f"Error in message processing: {str(e)}")
            traceback.print_exc()

            await self.whatsapp_service.send_text_message("I apologize, but I'm having trouble processing your request. Please try again in a moment.")
        finally:
            self.state_manager.update_state(self.message.phone_number, is_processing=False)



    # async def process_message(self, message: Message):
    #     try:
    #         response = await self.conversation_manager.handle_conversation(
    #             message.phone_number,
    #             message.content
    #         )

    #         await self.send_response(message, response)

    #         state_manager.set_is_processing(message.phone_number, False)

    #     except Exception as e:
    #         logger.error(f"Error in message processing: {str(e)}")
    #         await self.send_response(
    #             message.phone_number,
    #             "I apologize, but I'm having trouble processing your request. Please try again in a moment."
    #         )

    # async def send_response(self, message: Message, response: str):
    #     try:
    #         whatsapp_service = WhatsAppBusinessAPI(message)
    #         await whatsapp_service.send_text_message(
    #             message=response
    #         )

    #         # buttons = [
    #         #     {
    #         #         "type": "reply",
    #         #         "reply": {
    #         #             "id": "BUTTON_1",
    #         #             "title": "Yes"
    #         #         }
    #         #     },
    #         #     {
    #         #         "type": "reply",
    #         #         "reply": {
    #         #             "id": "BUTTON_2",
    #         #             "title": "No"
    #         #         }
    #         #     }
    #         # ]
    #         # await whatsapp_service.send_buttons(
    #         #     to_number=message.phone_number,
    #         #     body_text="Body text here",
    #         #     header_text="Header Text",
    #         #     footer_text="Choose an option",
    #         #     buttons=buttons
    #         # )

    #         # sections = [
    #         #     {
    #         #         "title": "Products",
    #         #         "rows": [
    #         #             {
    #         #                 "id": "PRODUCT_1",
    #         #                 "title": "Product 1",
    #         #                 "description": "Description 1"
    #         #             },
    #         #             {
    #         #                 "id": "PRODUCT_2",
    #         #                 "title": "Product 2",
    #         #                 "description": "Description 2"
    #         #             }
    #         #         ]
    #         #     }
    #         # ]
    #         # await whatsapp_service.send_interactive_list(
    #         #     to_number=message.phone_number,
    #         #     header_text="Our Products",
    #         #     body_text="Please select a product",
    #         #     footer_text="Thank you for shopping with us",
    #         #     button_text="View Products",
    #         #     sections=sections
    #         # )
    #     except Exception as e:
    #         logger.error(f"Error sending message: {str(e)}")


    # async def send_response(self, message: Message, response: str) -> bool:
    #     try:
    #         whatsapp_service = WhatsAppBusinessAPI(message.business_phone_number_id)

    #         async with asyncio.timeout(30.0):
    #             await whatsapp_service.send_text_message(
    #                 to_number=message.phone_number,
    #                 message=response
    #             )

    #             try:
    #                 await whatsapp_service.mark_message_as_read(
    #                     message_id=message.message_id
    #                 )
    #             except Exception as e:
    #                 logger.warning(f"Failed to mark as read: {str(e)}")

    #         return True

    #     except Exception as e:
    #         logger.error(f"Failed to send message: {str(e)}")
    #         return False
