
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from app.models.models import Message, MessageType
from app.utils.state_manager import state_manager
from app.engine import AppointmentOrchestrator
from app.core.config import settings
from datetime import datetime
import traceback
from app.utils.logger import setup_logger

logger = setup_logger("whatsapp_api", "whatsapp.log")
router = APIRouter()

orchestrator = AppointmentOrchestrator()

@router.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()

    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [{}])[0]
        message_text = messages.get("text", {}).get("body")
        message_id = messages.get("id")

        #todo: handle voice messages

        if messages.get("type") == "text":
            business_phone_number_id = value.get("metadata", {}).get("phone_number_id")
            from_number = messages.get("from")
            message_text = messages.get("text", {}).get("body")
            state_manager.set_user_phone_number(from_number)

            print(state_manager.get_state(from_number), 'start wwwwwwwwwwwwwwwwww')

            if state_manager.get_is_processing(from_number) == True:
                return {"status": "ok"}

            message = Message(
                message_id=message_id,
                phone_number=from_number,
                type=MessageType.TEXT,
                content=message_text,
                timestamp=datetime.now(),
                business_phone_number_id=business_phone_number_id
            )

            # await orchestrator.process_message(message)

            # state_manager.set_is_processing(from_number, False)
            background_tasks.add_task(_process_message_task, message)

        return {"status": "ok"}
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/webhook")
async def verify_webhook(request: Request):
    try:
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        if mode == "subscribe" and token == settings.WEBHOOK_VERIFY_TOKEN:
            logger.info("Webhook verified successfully!")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Forbidden")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _process_message_task(message):
    try:
        await orchestrator.process_message(message)
    except Exception as e:
        logger.error(f"Error in background task processing message {message.message_id}: {e}")
        traceback.print_exc()