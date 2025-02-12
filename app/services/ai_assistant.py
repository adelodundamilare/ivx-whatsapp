
from typing import Dict, Optional, Tuple
from fastapi import HTTPException
from app.models.whatsapp import ConversationState, DoctorProfile, ProcedureRequest, ProcedureType, Specialty
from app.core.config import settings
from app.services import database as database_service
from app.utils.state_manager import state_manager
from app.messages import intro
import re
import openai # type: ignore

client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
bubble_api_key=settings.BUBBLE_API_KEY

async def process_message(message: str):
    match state_manager.get_conversation_state():
        case ConversationState.WELCOME:
            return intro.handle_intro_response(message)
        case ConversationState.BOOK_APPOINTMENT | ConversationState.APPOINTMENT_PROCEDURE_TYPE | ConversationState.APPOINTMENT_DATE:
            return await intro.handle_appointment_scheduling(message)
        case _:
            return await _translate_response_with_ai(message)

async def _translate_response_with_ai(message: str, context: Dict) -> Tuple[str, Dict]:
    system_prompt = """You are an AI assistant for an anesthesia services company.
    Analyze the user message and extract relevant information about appointments,
    procedures, and medical details. Respond with structured data when possible."""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.1
        )

        intent, entities = _parse_ai_response(response.choices[0].message.content)
        return await _generate_response(intent, entities, context)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")


def _parse_ai_response(response: str) -> Tuple[str, Dict]:
    intents = {
        r"book|schedule|appoint": "schedule_appointment",
        r"cancel|reschedule": "modify_appointment",
        r"doctor|anesthesiologist": "doctor_info",
        r"procedure|treatment": "procedure_info",
        r"faq|question|help": "faq",
        r"status|check": "check_status",
        # r"confirm|verify": "confirm_appointment",
        # r"menu|options|services": "service_menu",
        # r"payment|pay|bill": "process_payment",
        # r"clinic|location|address": "collect_clinic_info",
        # r"time|date|when": "collect_datetime",
        # r"type|procedure|surgery": "collect_procedure",
        # r"doctor|provider|specialist": "match_doctor",
        # r"cost|price|fee": "cost_info",
    }

    intent = "unknown"
    for pattern, intent_name in intents.items():
        if re.search(pattern, response.lower()):
            intent = intent_name
            break

    entities = {}
    if "date" in response.lower():
        date_matches = re.findall(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', response)
        if date_matches:
            entities["date"] = date_matches[0]

    for proc in ProcedureType:
        if proc.value in response.lower():
            entities["procedure_type"] = proc

    return intent, entities

async def match_doctor(procedure_request: ProcedureRequest) -> Optional[DoctorProfile]:
    doctors = await database_service.get_doctors_from_bubble()

    scored_doctors = []
    for doctor in doctors:
        score = 0

        if procedure_request.procedure_type in doctor.procedures:
            score += 3

        if procedure_request.patient_age and procedure_request.patient_age < 18:
            if Specialty.PEDIATRIC in doctor.specialties:
                score += 2

        if procedure_request.complexity == "High" and doctor.years_experience > 5:
            score += 2

        if await database_service.check_doctor_availability(doctor.id, procedure_request.preferred_date):
            score += 3

        scored_doctors.append((doctor, score))

    scored_doctors.sort(key=lambda x: x[1], reverse=True)
    return scored_doctors[0][0] if scored_doctors else None


async def _generate_response(intent: str, entities: Dict) -> Tuple[str, Dict]:

    if intent == "schedule_appointment":
        return await intro.handle_appointment_scheduling(entities)
    elif intent == "doctor_info":
        return intro.handle_doctor_info(entities)
    elif intent == "procedure_info":
        return intro.handle_procedure_info(entities)
    # elif intent == "edit_appointment":
    #     return intro.handle_appointment_modification(user_id, message, current_state)
    # elif intent == "cancel_appointment":
    #     return intro.handle_appointment_cancellation(user_id, message, current_state)
    # elif intent == "check_status":
    #     return intro.handle_status_check(user_id, message)
    else:
        return intro.handle_intro()
        # return ("I'm sorry, I didn't quite understand. Could you please specify if you'd like to "
        #         "schedule an appointment, learn about our doctors, or get procedure information?"), context



