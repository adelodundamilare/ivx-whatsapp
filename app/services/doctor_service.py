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
    #     self.whatsapp_service = WhatsAppBusinessAPI(message=Message(), business_phone_number_id=settings.WHATSAPP_BUSINESS_PHONE_NUMBER_ID)

    async def init(self):
        try:
            appointments = await bubble_client.find_unassigned_appointments()
            if len(appointments) < 1:
                return

            # for now, let's work with the first guy...
            best_doctor = await bubble_client.find_unassigned_appointments()
            # message best doctor
            prompt = f"""
            Hi {best_doctor.get('first_name')}, 😊

            I'm IVX, an AI assistant helping clinics connect with the right doctors for their patients.

            A clinic is requesting a patient booking for *{appointments.get('service_type')}*. Would you be available on *{best_doctor.get('date')}*?

            Let me know if this works for you. ✅
            """

            phone = best_doctor.get('phone')
            response = await invoke_doctor_ai(prompt, phone)

            # update state, db too...
            self.state_manager.update_state(phone, {"appointment": appointments})
            await self.whatsapp_service.send_text_message(response)
        except Exception as e:
            logger.error(f"Error in message processing: {str(e)}")
            traceback.print_exc()