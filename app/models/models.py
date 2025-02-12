
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, field_validator


class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"

class Intent(str, Enum):
    CREATE_APPOINTMENT = "create_appointment"
    EDIT_APPOINTMENT = "edit_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    CHECK_AVAILABILITY = "check_availability"
    GET_INFO = "get_info"
    GREETING = "greeting"
    FAREWELL = "farewell"
    CONFIRM = "confirm"
    DENY = "deny"
    THANK = "thank"
    HELP = "help"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, value: str) -> Optional["Intent"]:
        """Case-insensitive lookup of Intent enum."""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        return None  # Or raise ValueError if you prefer

class Message(BaseModel):
    message_id: str
    phone_number: str
    type: MessageType
    content: Union[str, bytes]
    timestamp: datetime
    business_phone_number_id: str

class ConversationState(BaseModel):
    phone_number: Optional[str]=None
    current_intent: Optional[Intent] = None
    collected_data: Dict = {}
    missing_fields: List[str] = []
    last_interaction: Optional[datetime]=datetime.now()
    confirmation_pending: bool = False
    modification_pending: bool = False
    context: Optional[Dict] = {}
    interaction_count: Optional[int] = 0
    last_error: Optional[str] = None

class AppointmentData(BaseModel):
    patient_name: str
    procedure_type: str
    preferred_date: Optional[datetime]
    preferred_time: Optional[str]
    symptoms: Optional[str] = None
    insurance_info: Optional[str] = None
    special_requirements: Optional[str] = None
    phone_number: str

    @field_validator('preferred_date')
    def validate_date(cls, v):
        if v and v < datetime.now():
            raise ValueError("Appointment date cannot be in the past")
        return v

@dataclass
class ValidationResult:
    is_valid: bool
    errors: Dict[str, str]