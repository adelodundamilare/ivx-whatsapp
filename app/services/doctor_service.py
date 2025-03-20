from datetime import datetime
import traceback
from app.models.models import Message
from app.services.bubble_client import bubble_client
from app.services.whatsapp import WhatsAppBusinessAPI
from app.core.config import settings
from app.utils.doctor_state_manager import DoctorStateManager
from app.utils.helpers import invoke_doctor_ai
from app.utils.logger import setup_logger

logger = setup_logger("doctor_service", "doctor_service.log")

class DoctorService:
    def __init__(self):
        self.state_manager = DoctorStateManager()
        self.whatsapp_service = WhatsAppBusinessAPI(
            message=Message(
                phone_number="5214421728398",
                message_id='',
                content="",
                timestamp=datetime.now(),
                business_phone_number_id="551871334675111",
                type="text"),
            business_phone_number_id="551871334675111")

    async def process(self):
        try:
            appointments = await bubble_client.find_unassigned_appointments()
            if len(appointments) < 1:
                return

            appointment = appointments[0]

            # for now, let's work with the first guy...
            best_doctor = await bubble_client.find_best_doctor()
            # print(best_doctor, 'best_doctor')
            # message best doctor
            prompt = f"""
Hi {best_doctor.get('full_name', '')}, 😊

I'm IVX, an AI assistant helping clinics connect with the right doctors for their patients.

A clinic is requesting a patient booking for *{appointment.get('service_type')}* with booking code *{appointment.get('code')}*. Would you be available on *{appointment.get('date')}*?

Let me know if this works for you. ✅
"""

            phone = best_doctor.get('phone_number')
            # response = await invoke_doctor_ai(prompt, phone)

            # update state, db too...
            self.state_manager.update_state(phone, {"appointment": appointment, "doctor": best_doctor})
            print('phone number', best_doctor.get('phone_number'))
            await self.whatsapp_service.send_text_message(prompt, to_number=phone)
        except Exception as e:
            logger.error(f"Error in processing doctor request: {str(e)}")
            traceback.print_exc()