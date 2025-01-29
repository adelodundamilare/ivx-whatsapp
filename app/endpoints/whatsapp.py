
from fastapi import APIRouter, BackgroundTasks, Depends
from app.models.whatsapp import AppointmentCreate, ConversationState, WhatsAppMessage
from app.repository.whatsapp import WhatsAppRepository, get_whatsapp_repository
from app.services import whatsapp as whatsapp_service
from app.utils.logger import setup_logger

logger = setup_logger("whatsapp_api", "whatsapp.log")

router = APIRouter()

@router.post("/webhook/whatsapp", status_code=200)
async def whatsapp_webhook(
    message: WhatsAppMessage,
    background_tasks: BackgroundTasks,
    repository: WhatsAppRepository = Depends(get_whatsapp_repository)
):
    try:
        """Handle incoming WhatsApp messages"""
        user_id = message.from_number
        current_state = repository.user_states.get(user_id, ConversationState.WELCOME)

        # Process message based on current state
        response_message = await whatsapp_service.process_message(user_id, message.message_text, current_state, repository)

        # Send response in background
        # background_tasks.add_task(
        #     repository.send_whatsapp_message,
        #     user_id,
        #     response_message
        # )
        await repository.send_whatsapp_message(user_id, response_message)

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise
