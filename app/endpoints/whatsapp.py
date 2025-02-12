
from datetime import datetime
import traceback
from typing import Dict
from fastapi import APIRouter,  HTTPException, Request
from app.engine import AppointmentOrchestrator
from app.models.models import Message, MessageType
from app.services import ai_assistant
from app.utils.logger import setup_logger
from app.core.config import settings
from app.services import whatsapp as whatsapp_service
from app.utils.state_manager import state_manager

logger = setup_logger("whatsapp_api", "whatsapp.log")

router = APIRouter()
user_contexts: Dict[str, Dict] = {}
orchestrator = AppointmentOrchestrator()

@router.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.json()
    # logger.info(f"Incoming webhook message: {json.dumps(body, indent=2)}")

    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [{}])[0]
        message_text = messages.get("text", {}).get("body")
        message_id = messages.get("id")

        if messages.get("type") == "text":
            business_phone_number_id = value.get("metadata", {}).get("phone_number_id")

            from_number = messages.get("from")
            message_text = messages.get("text", {}).get("body")
            state_manager.set_user_phone_number(from_number)

            message = Message(
                message_id=message_id,
                phone_number=from_number,
                type=MessageType.TEXT,
                content=message_text,
                timestamp=datetime.now(),
                business_phone_number_id=business_phone_number_id
            )

            # Process the message here
            await orchestrator.process_message(message)
            # message_text = await ai_assistant.process_message(message_text)
            # await database.process_message(from_number, message_text, user_contexts)

            # await whatsapp_service.send_message(
            #     business_phone_number_id,
            #     from_number,
            #     message_text,
            #     message_id
            # )

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
