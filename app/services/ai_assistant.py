
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException
from datetime import datetime, timedelta
from app.models.whatsapp import DoctorProfile, ProcedureRequest, ProcedureType, Specialty
import app.services.ai_assistant as ai_assistant
import json
import httpx
import re


class AIAssistant:
    def __init__(self, openai_key: str, bubble_api_key: str):
        self.openai_key = openai_key
        self.bubble_api_key = bubble_api_key
        ai_assistant.api_key = openai_key

    async def process_message(self, message: str, context: Dict) -> Tuple[str, Dict]:
        system_prompt = """You are an AI assistant for an anesthesia services company.
        Analyze the user message and extract relevant information about appointments,
        procedures, and medical details. Respond with structured data when possible."""

        try:
            response = await ai_assistant.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.1
            )

            intent, entities = self._parse_ai_response(response.choices[0].message.content)
            return self._generate_response(intent, entities, context)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")

    def _parse_ai_response(self, response: str) -> Tuple[str, Dict]:
        intents = {
            r"schedule|book|appointment": "schedule_appointment",
            r"doctor|anesthesiologist": "doctor_info",
            r"procedure|treatment": "procedure_info",
            r"cost|price|fee": "cost_info"
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

    async def match_doctor(self, procedure_request: ProcedureRequest) -> Optional[DoctorProfile]:
        doctors = await self._get_doctors_from_bubble()

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

            if await self._check_doctor_availability(doctor.id, procedure_request.preferred_date):
                score += 3

            scored_doctors.append((doctor, score))

        scored_doctors.sort(key=lambda x: x[1], reverse=True)
        return scored_doctors[0][0] if scored_doctors else None

    async def _get_doctors_from_bubble(self) -> List[DoctorProfile]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://your-bubble-app.bubbleapps.io/api/1.1/obj/doctor",
                headers={"Authorization": f"Bearer {self.bubble_api_key}"}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch doctors")

            doctors = []
            for doc in response.json()["response"]["results"]:
                doctors.append(DoctorProfile(
                    id=doc["_id"],
                    name=doc["name"],
                    specialties=[Specialty(s) for s in doc["specialties"]],
                    years_experience=doc["years_experience"],
                    available_days=doc["available_days"],
                    procedures=[ProcedureType(p) for p in doc["procedures"]],
                    rating=doc["rating"]
                ))
            return doctors

    async def _check_doctor_availability(self, doctor_id: str, date: datetime) -> bool:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://your-bubble-app.bubbleapps.io/api/1.1/obj/appointment",
                headers={"Authorization": f"Bearer {self.bubble_api_key}"},
                params={
                    "constraints": json.dumps([
                        {"key": "doctor", "constraint_type": "equals", "value": doctor_id},
                        {"key": "date", "constraint_type": "equals", "value": date.isoformat()}
                    ])
                }
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to check availability")

            existing_appointments = response.json()["response"]["results"]
            return len(existing_appointments) == 0

    def _generate_response(self, intent: str, entities: Dict, context: Dict) -> Tuple[str, Dict]:
        if intent == "schedule_appointment":
            return self._handle_appointment_scheduling(entities, context)
        elif intent == "doctor_info":
            return self._handle_doctor_info(entities, context)
        elif intent == "procedure_info":
            return self._handle_procedure_info(entities, context)
        else:
            return ("I'm sorry, I didn't quite understand. Could you please specify if you'd like to "
                   "schedule an appointment, learn about our doctors, or get procedure information?"), context

    def _handle_appointment_scheduling(self, entities: Dict, context: Dict) -> Tuple[str, Dict]:
        context.update(entities)

        required_fields = ["procedure_type", "date", "clinic_name"]
        missing_fields = [field for field in required_fields if field not in context]

        if missing_fields:
            next_field = missing_fields[0]
            if next_field == "procedure_type":
                return ("What type of procedure is this for? (Options: Wisdom Teeth, Dental Implants, "
                       "Root Canal, Multiple Extractions, Pediatric Dental)"), context
            elif next_field == "date":
                return "What date would you prefer for the procedure?", context
            elif next_field == "clinic_name":
                return "Which dental clinic will the procedure be at?", context

        return ("Great! I'll help you schedule an appointment for a "
                f"{context['procedure_type']} procedure on {context['date']} "
                f"at {context['clinic_name']}. "
                "Would you like me to check doctor availability now?"), context

    def _handle_doctor_info(self, entities: Dict, context: Dict) -> Tuple[str, Dict]:
        if "doctor_name" in entities:
            return f"Let me fetch Dr. {entities['doctor_name']}'s profile and availability.", context
        return ("I can help you learn about our anesthesiologists. "
                "Would you like to know about their specialties, experience, or availability?"), context

    def _handle_procedure_info(self, entities: Dict, context: Dict) -> Tuple[str, Dict]:
        proc_type = entities.get("procedure_type")
        if proc_type:
            return f"Let me provide you with information about anesthesia for {proc_type}.", context
        return ("I can provide information about anesthesia for various dental procedures. "
                "Which procedure would you like to learn more about?"), context