
from typing import Dict, List

from fastapi import HTTPException
from app.utils.logger import setup_logger
from app.utils.validator import AppointmentError
import httpx # type: ignore
from app.core.config import settings
from datetime import datetime, timedelta
from app.utils.logger import setup_logger
import json
from app.models.whatsapp import BusinessHours, DoctorProfile, ProcedureType, Specialty

logger = setup_logger("database_api", "database.log")

bubble_api_key=settings.BUBBLE_API_KEY
bubble_url=settings.BUBBLE_API_URL

async def create_appointment(data: Dict) -> Dict:
    try:

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{bubble_url}/appointments",
                headers={"Authorization": f"Bearer {bubble_api_key}"},
                json={**data.dict(), **data}
            )

            if response.status_code != 200:
                raise AppointmentError("Failed to create appointment")

            appointment_data = response.json()

            return appointment_data

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

async def get_available_slots(self, date: datetime) -> List[datetime]:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{bubble_url}/appointments",
                headers={"Authorization": f"Bearer {self.bubble_api_key}"},
                params={
                    "constraints": json.dumps([
                        {"key": "preferred_date", "constraint_type": "equals", "value": date.date().isoformat()}
                    ])
                }
            )

            if response.status_code != 200:
                raise AppointmentError("Failed to fetch appointments")

            booked_slots = [
                datetime.fromisoformat(appt['preferred_date'])
                for appt in response.json()['response']['results']
            ]

            available_slots = []
            current_slot = datetime.combine(date.date(), datetime.min.time().replace(hour=BusinessHours.START_HOUR))

            while current_slot.hour < BusinessHours.END_HOUR:
                if current_slot not in booked_slots:
                    available_slots.append(current_slot)
                current_slot += timedelta(minutes=30)

            return available_slots

    except Exception as e:
        self.error_handler.log_error(e, {'date': date.isoformat()})
        raise

async def _create_notification_preferences(self, appointment_id: str, phone: str) -> None:
    """Create notification preferences for appointment"""
    try:
        notification_data = {
            'appointment_id': appointment_id,
            'phone': phone,
            'email_enabled': True,
            'sms_enabled': True,
            'whatsapp_enabled': True,
            'reminder_frequency': 'daily'
        }

        async with httpx.AsyncClient() as client:
            await client.post(
                "https://your-bubble-app.bubbleapps.io/api/1.1/obj/notification_preferences",
                headers={"Authorization": f"Bearer {self.bubble_api_key}"},
                json=notification_data
            )

    except Exception as e:
        self.error_handler.log_error(e, {
            'appointment_id': appointment_id,
            'phone': phone
        })
        # Don't raise - this is a non-critical operation
        logger.warning(f"Failed to create notification preferences: {str(e)}")


async def get_doctors_from_bubble(self) -> List[DoctorProfile]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
                f"{bubble_url}/doctors",
            headers={"Authorization": f"Bearer {bubble_api_key}"}
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

async def check_doctor_availability(doctor_id: str, date: datetime) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://your-bubble-app.bubbleapps.io/api/1.1/obj/appointment",
            headers={"Authorization": f"Bearer {bubble_api_key}"},
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
