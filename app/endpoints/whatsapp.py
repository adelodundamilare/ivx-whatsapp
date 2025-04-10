
from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from app.models.models import Message
from app.services.doctor_service import DoctorService
from app.utils.state_manager import StateManager
from app.engine import AppointmentOrchestrator
from app.core.config import settings
from datetime import datetime
import traceback
from app.utils.logger import setup_logger

logger = setup_logger("whatsapp_api", "whatsapp.log")
router = APIRouter()


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
        from_number = messages.get("from")
        message_type = messages.get("type")

        business_phone_number_id = value.get("metadata", {}).get("phone_number_id")
        # print(business_phone_number_id, 'business_phone_number_id')
        if not message_type:
            return

        if message_type == "text":
            message_text = messages.get("text", {}).get("body")
        elif message_type == "button":
            message_text = messages.get("button", {}).get("text") #changed to .get("text")
        elif message_type == "location":
            location = messages.get("location", {})
            latitude = location.get("latitude")
            longitude = location.get("longitude")
            address = location.get("address")
            name = location.get("name")
            if latitude and longitude:
                # message_text = f"{latitude}, {longitude}"
                message_text = address
            else:
                message_text = "Location data missing."
        elif message_type == "audio":
            message_text = messages.get("audio", {}).get("id") #changed to .get("id")
        elif message_type == "interactive":
            interactive = messages.get("interactive", {})
            message_text = interactive.get("list_reply", {}).get("id") or interactive.get("button_reply", {}).get("id")
        else:
            # message_text = messages.get("text", {}).get("body")
            logger.warning(f"Unhandled message type: {message_type}")

        if not messages or not message_text or not message_type:
            return

        state = StateManager().get_state(from_number)

        if state.get('is_processing') == True:
            return {"status": "ok"}

        message = Message(
            message_id=message_id,
            phone_number=from_number,
            type=message_type,
            content=message_text,
            timestamp=datetime.now(),
            business_phone_number_id=business_phone_number_id
        )

        # await orchestrator.process_message(message)
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

@router.get("/get-doctor-approval")
async def get_doctor_approval(request: Request):
    try:
        doctor_service = DoctorService()
        await doctor_service.process()
        # CRON RUNS EVERY 5MINS
        # fetch all appointments with status None
        # fetch all available doctors...
        # match doctor to appointments depending on the set preference
        # message doctor via whatsapp api
        # handle doctor's response
        # if not doctor response in 15 minutes, send a reminder
        # if no response still after another 15mins cancel appointment, find another doctor and repeat.
        # if response is declined, find another doctor
        # if response is accepted, update appointment status and send a message to clinic...
        # RESPONSE IS ACCEPT OR DECLINE, DO NOTHING ELSE...
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/appointment-reminder")
async def appointment_reminder(request: Request):
    try:
        # CRON RUN ONCE EVERYDAY
        # fetch all accepted appointments
        # check if appointment date is less than 1 day
        # if less than 1 day, send a reminder to doctor and clinic...
        # DO NOTHING ELSE...
        print('yello!')
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def _process_message_task(message):
    try:
        await AppointmentOrchestrator(message).process_message()
    except Exception as e:
        logger.error(f"Error in background task processing message {message.message_id}: {e}")
        traceback.print_exc()
