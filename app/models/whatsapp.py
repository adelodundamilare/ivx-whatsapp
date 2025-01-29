from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ConversationState(str, Enum):
    WELCOME = "welcome"
    SERVICE_MENU = "service_menu"
    BOOK_APPOINTMENT = "book_appointment"
    COLLECT_CLINIC_INFO = "collect_clinic_info"
    COLLECT_DATETIME = "collect_datetime"
    COLLECT_PROCEDURE = "collect_procedure"
    MATCH_DOCTOR = "match_doctor"
    CONFIRM_BOOKING = "confirm_booking"
    PROCESS_PAYMENT = "process_payment"
    DOCTOR_INFO = "doctor_info"
    FAQ = "faq"

class WhatsAppMessage(BaseModel):
    from_number: str = Field(..., description="Sender's WhatsApp number")
    message_text: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.now)

class AppointmentCreate(BaseModel):
    clinic_name: str
    clinic_address: str
    appointment_date: datetime
    procedure_type: str
    patient_phone: str
    notes: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: str
    status: str
    doctor_id: Optional[str] = None
    bubble_id: Optional[str] = None
