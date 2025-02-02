
from typing import Dict
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from app.models.whatsapp import  CancellationRequest, MessageRequest, MessageResponse, ProcedureRequest, WhatsAppMessage
from app.models.appointment import  AppointmentCreate, AppointmentEdit
from app.services.ai_assistant import AIAssistant
from app.services.appointment import AppointmentService
from app.utils.logger import setup_logger
import httpx
from app.core.config import settings
from app.services import whatsapp as whatsapp_service
import json

logger = setup_logger("appointment_api", "appointment.log")

router = APIRouter()
user_contexts: Dict[str, Dict] = {}

ai_assistant = AIAssistant(openai_key=settings.OPENAI_API_KEY, bubble_api_key=settings.BUBBLE_API_KEY)
appointment_manager = AppointmentService(bubble_api_key=settings.BUBBLE_API_KEY)

@router.post("/process-message", response_model=MessageResponse)
async def process_message(request: MessageRequest):
    try:
        context = user_contexts.get(request.user_id, {})
        context.update(request.context)

        response, updated_context = await ai_assistant.process_message(
            request.message,
            context
        )

        user_contexts[request.user_id] = updated_context

        return MessageResponse(
            response=response,
            updated_context=updated_context
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

@router.post("/match-doctor")
async def match_doctor(procedure_request: ProcedureRequest):
    try:
        doctor = await ai_assistant.match_doctor(procedure_request)
        if doctor:
            return doctor
        raise HTTPException(status_code=404, detail="No suitable doctor found")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

@router.delete("/reset-context/{user_id}")
async def reset_context(user_id: str):
    try:
        if user_id in user_contexts:
            del user_contexts[user_id]
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise


@router.put("/appointments/{appointment_id}/edit")
async def edit_appointment(
    appointment_id: str,
    edit_request: AppointmentEdit,
    background_tasks: BackgroundTasks
):
    try:
        result = await appointment_manager.edit_appointment(
            AppointmentEdit(appointment_id=appointment_id, **edit_request.dict())
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: str,
    cancellation: CancellationRequest,
    background_tasks: BackgroundTasks
):
    try:
        result = await appointment_manager.cancel_appointment(
            appointment_id=appointment_id,
            reason=cancellation.reason
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/appointments/{appointment_id}/start-notifications")
async def start_notifications(
    appointment_id: str,
    background_tasks: BackgroundTasks
):
    """Start sequential doctor notification process"""
    try:
        background_tasks.add_task(
            appointment_manager.start_doctor_notification_sequence,
            appointment_id
        )
        return {"status": "success", "message": "Notification sequence initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/doctor-response/{appointment_id}")
async def process_doctor_response(
    appointment_id: str,
    doctor_id: str,
    accepted: bool,
    background_tasks: BackgroundTasks
):
    """Process doctor's response to appointment request"""
    try:
        result = await appointment_manager.handle_doctor_response(
            doctor_id=doctor_id,
            appointment_id=appointment_id,
            accepted=accepted
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/appointments/create")
async def create_appointment(
    appointment: AppointmentCreate,
    background_tasks: BackgroundTasks
):
    try:
        result = await appointment_manager.create_appointment(appointment)

        # Start doctor notification sequence in background
        # background_tasks.add_task(
        #     appointment_manager.start_doctor_notification_sequence,
        #     result['id']
        # )
        appointment_manager.start_doctor_notification_sequence(result['id'])

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))