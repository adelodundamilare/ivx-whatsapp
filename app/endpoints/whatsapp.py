
from typing import Dict
from fastapi import APIRouter,  HTTPException, Request
from app.services.ai_assistant import AIAssistant
from app.services.appointment import AppointmentService
from app.utils.logger import setup_logger
from app.core.config import settings
from app.services import whatsapp as whatsapp_service

logger = setup_logger("whatsapp_api", "whatsapp.log")

router = APIRouter()
user_contexts: Dict[str, Dict] = {}

ai_assistant = AIAssistant(openai_key=settings.OPENAI_API_KEY, bubble_api_key=settings.BUBBLE_API_KEY)
appointment_manager = AppointmentService(bubble_api_key=settings.BUBBLE_API_KEY)

@router.post("/webhook")
async def handle_webhook(request: Request):
    body = await request.json()
    # logger.info(f"Incoming webhook message: {json.dumps(body, indent=2)}")

    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [{}])[0]

        if messages.get("type") == "text":
            business_phone_number_id = value.get("metadata", {}).get("phone_number_id")

            from_number = messages.get("from")
            message_text = messages.get("text", {}).get("body")

            await whatsapp_service.send_message(
                business_phone_number_id,
                from_number,
                messages
            )

        return {"status": "ok"}
    except Exception as e:
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
