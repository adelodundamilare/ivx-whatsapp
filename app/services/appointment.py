
from typing import Dict, List
from xml.sax import ErrorHandler
from app.models.appointment import AppointmentCreate
from app.utils.logger import setup_logger
from app.utils.validator import AppointmentError, DataValidator
import httpx
from datetime import datetime, timedelta
import json
from app.models.whatsapp import BusinessHours

logger = setup_logger("apointment_api", "whatsapp.log")

class AppointmentService:
    def __init__(self, bubble_api_key: str):
        self.bubble_api_key = bubble_api_key
        self.error_handler = ErrorHandler()

    async def create_appointment(self, data: AppointmentCreate) -> Dict:
        try:
            # Sanitize inputs
            sanitized_data = {
                'clinic_name': DataValidator.sanitize_input(data.clinic_name),
                'clinic_address': DataValidator.sanitize_input(data.clinic_address),
                'patient_name': DataValidator.sanitize_input(data.patient_name),
                'medical_notes': DataValidator.sanitize_input(data.medical_notes) if data.medical_notes else None
            }

            # Create appointment in Bubble.io
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://your-bubble-app.bubbleapps.io/api/1.1/obj/appointment",
                    headers={"Authorization": f"Bearer {self.bubble_api_key}"},
                    json={**data.dict(), **sanitized_data}
                )

                if response.status_code != 200:
                    raise AppointmentError("Failed to create appointment")

                appointment_data = response.json()

                # Create notification preferences
                await self._create_notification_preferences(
                    appointment_id=appointment_data['id'],
                    phone=data.patient_phone
                )

                return appointment_data

        except Exception as e:
            self.error_handler.log_error(e, {'data': data.dict()})
            raise

    async def get_available_slots(self, date: datetime) -> List[datetime]:
        """Get available appointment slots for a given date"""
        try:
            # Get all appointments for the date
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://your-bubble-app.bubbleapps.io/api/1.1/obj/appointment",
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

                # Generate available slots
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

# class AppointmentService:
#     def __init__(self, bubble_api_key: str, twilio_client=None):
#         self.bubble_api_key = bubble_api_key
#         self.twilio_client = twilio_client
#         self.notification_queue: Dict[str, List[DoctorNotification]] = {}

#     async def edit_appointment(self, edit_request: AppointmentEdit) -> dict:
#         try:
#             current_appointment = await self._get_appointment(edit_request.appointment_id)
#             if not current_appointment:
#                 raise HTTPException(status_code=404, detail="Appointment not found")

#             update_data = {}
#             if edit_request.new_date:
#                 update_data["date"] = edit_request.new_date.isoformat()
#             if edit_request.new_doctor_id:
#                 update_data["doctor"] = edit_request.new_doctor_id
#             if edit_request.new_procedure_type:
#                 update_data["procedure_type"] = edit_request.new_procedure_type

#             async with httpx.AsyncClient() as client:
#                 response = await client.patch(
#                     f"https://your-bubble-app.bubbleapps.io/api/1.1/obj/appointment/{edit_request.appointment_id}",
#                     headers={"Authorization": f"Bearer {self.bubble_api_key}"},
#                     json=update_data
#                 )

#                 if response.status_code != 200:
#                     raise HTTPException(status_code=500, detail="Failed to update appointment")

#             await self._create_modification_record(
#                 appointment_id=edit_request.appointment_id,
#                 changes=update_data,
#                 reason=edit_request.reason
#             )

#             await self._notify_about_changes(
#                 appointment_id=edit_request.appointment_id,
#                 changes=update_data
#             )

#             return {"status": "success", "message": "Appointment updated successfully"}

#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Error updating appointment: {str(e)}")

#     async def cancel_appointment(self, appointment_id: str, reason: str) -> dict:
#         try:
#             async with httpx.AsyncClient() as client:
#                 response = await client.patch(
#                     f"https://your-bubble-app.bubbleapps.io/api/1.1/obj/appointment/{appointment_id}",
#                     headers={"Authorization": f"Bearer {self.bubble_api_key}"},
#                     json={"status": AppointmentStatus.CANCELED, "cancellation_reason": reason}
#                 )

#                 if response.status_code != 200:
#                     raise HTTPException(status_code=500, detail="Failed to cancel appointment")

#             await self._notify_cancellation(appointment_id, reason)

#             return {"status": "success", "message": "Appointment canceled successfully"}

#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Error canceling appointment: {str(e)}")

#     async def start_doctor_notification_sequence(self, appointment_id: str) -> None:
#         try:
#             appointment = await self._get_appointment(appointment_id)
#             if not appointment:
#                 raise HTTPException(status_code=404, detail="Appointment not found")

#             matched_doctors = await self._get_matched_doctors(
#                 procedure_type=appointment["procedure_type"],
#                 appointment_date=appointment["date"]
#             )

#             notification_queue = []
#             for idx, doctor in enumerate(matched_doctors):
#                 expiry_time = datetime.now() + timedelta(minutes=30 if idx == 0 else 60)
#                 notification = DoctorNotification(
#                     doctor_id=doctor["id"],
#                     appointment_id=appointment_id,
#                     notification_type=doctor["preferred_notification"],
#                     priority=NotificationPriority.HIGH if idx == 0 else NotificationPriority.MEDIUM,
#                     expiry=expiry_time,
#                     response_needed=True
#                 )
#                 notification_queue.append(notification)

#             self.notification_queue[appointment_id] = notification_queue

#             await self._process_notification_queue(appointment_id)

#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Error starting notification sequence: {str(e)}")

#     async def handle_doctor_response(self, doctor_id: str, appointment_id: str, accepted: bool) -> dict:
#         try:
#             if accepted:
#                 async with httpx.AsyncClient() as client:
#                     response = await client.patch(
#                         f"https://your-bubble-app.bubbleapps.io/api/1.1/obj/appointment/{appointment_id}",
#                         headers={"Authorization": f"Bearer {self.bubble_api_key}"},
#                         json={
#                             "status": AppointmentStatus.DOCTOR_ASSIGNED,
#                             "assigned_doctor": doctor_id
#                         }
#                     )

#                     if response.status_code != 200:
#                         raise HTTPException(status_code=500, detail="Failed to update appointment")

#                 self.notification_queue.pop(appointment_id, None)

#                 await self._notify_clinic_about_doctor(appointment_id, doctor_id)

#             else:
#                 await self._process_notification_queue(appointment_id)

#             return {"status": "success", "message": "Doctor response processed successfully"}

#         except Exception as e:
#             raise HTTPException(status_code=500, detail=f"Error processing doctor response: {str(e)}")

#     async def _process_notification_queue(self, appointment_id: str) -> None:
#         if appointment_id not in self.notification_queue or not self.notification_queue[appointment_id]:
#             return

#         current_notification = self.notification_queue[appointment_id][0]

#         if current_notification.notification_type == NotificationPreference.SMS:
#             await self._send_sms_notification(current_notification)
#         elif current_notification.notification_type == NotificationPreference.EMAIL:
#             await self._send_email_notification(current_notification)
#         elif current_notification.notification_type == NotificationPreference.WHATSAPP:
#             await self._send_whatsapp_notification(current_notification)

#         asyncio.create_task(self._check_notification_expiry(appointment_id, current_notification))

#     async def _check_notification_expiry(self, appointment_id: str, notification: DoctorNotification) -> None:
#         await asyncio.sleep((notification.expiry - datetime.now()).total_seconds())

#         if (appointment_id in self.notification_queue and
#             self.notification_queue[appointment_id] and
#             self.notification_queue[appointment_id][0].doctor_id == notification.doctor_id):

#             self.notification_queue[appointment_id].pop(0)
#             await self._process_notification_queue(appointment_id)

#     async def _notify_clinic_about_doctor(self, appointment_id: str, doctor_id: str) -> None:
#         appointment = await self._get_appointment(appointment_id)
#         doctor = await self._get_doctor(doctor_id)

#         message = (
#             f"Good news! Dr. {doctor['name']} has confirmed availability for your "
#             f"appointment on {appointment['date']}. You will receive detailed "
#             f"instructions shortly."
#         )

#         clinic_notification = {
#             "type": "DOCTOR_CONFIRMED",
#             "appointment_id": appointment_id,
#             "doctor_id": doctor_id,
#             "message": message
#         }

#         await self._send_clinic_notification(clinic_notification)

#     async def _create_modification_record(self, appointment_id: str, changes: dict, reason: str) -> None:
#         modification_data = {
#             "appointment": appointment_id,
#             "changes": json.dumps(changes),
#             "reason": reason,
#             "modified_at": datetime.now().isoformat(),
#             "modification_type": "edit"
#         }

#         async with httpx.AsyncClient() as client:
#             await client.post(
#                 "https://your-bubble-app.bubbleapps.io/api/1.1/obj/appointment_modification",
#                 headers={"Authorization": f"Bearer {self.bubble_api_key}"},
#                 json=modification_data
#             )