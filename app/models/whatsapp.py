from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class ConversationState(BaseModel):
    step: str
    data: Dict[str, Any] = {}
    last_update: datetime = Field(default_factory=datetime.now)
    attempt_count: int = 0

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


# class AppointmentCreate(BaseModel):
#     clinic_name: str
#     clinic_address: str
#     procedure_type: str
#     preferred_date: datetime
#     patient_name: str
#     patient_phone: str
#     medical_notes: Optional[str] = None


class ProcedureType(str, Enum):
    WISDOM_TEETH = "wisdom_teeth"
    DENTAL_IMPLANTS = "dental_implants"
    ROOT_CANAL = "root_canal"
    MULTIPLE_EXTRACTIONS = "multiple_extractions"
    PEDIATRIC_DENTAL = "pediatric_dental"

class Specialty(str, Enum):
    GENERAL = "general"
    PEDIATRIC = "pediatric"
    COMPLEX_CASES = "complex_cases"
    SPECIAL_NEEDS = "special_needs"

class DoctorProfile(BaseModel):
    id: str
    name: str
    specialties: List[Specialty]
    years_experience: int
    available_days: List[str]
    procedures: List[ProcedureType]
    rating: float

class ProcedureRequest(BaseModel):
    procedure_type: ProcedureType
    patient_age: Optional[int]
    medical_conditions: Optional[List[str]]
    preferred_date: datetime
    duration_minutes: int
    complexity: str = Field(..., description="Low, Medium, High")

class MessageRequest(BaseModel):
    user_id: str
    message: str
    context: Optional[Dict] = {}

class MessageResponse(BaseModel):
    response: str
    updated_context: Dict

class NotificationPreference(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"

class NotificationPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DoctorNotification(BaseModel):
    doctor_id: str
    appointment_id: str
    notification_type: NotificationPreference
    priority: NotificationPriority
    expiry: datetime
    response_needed: bool

class CancellationRequest(BaseModel):
    reason: str = Field(..., description="Reason for cancellation")

class WhatsAppMessage(BaseModel):
    from_number: str
    message_text: str

class BusinessHours:
    START_HOUR = 9  # 9 AM
    END_HOUR = 17   # 5 PM
    WEEKEND_DAYS = (5, 6)  # Saturday and Sunday (0 = Monday)