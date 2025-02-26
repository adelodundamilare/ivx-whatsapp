
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union
from pydantic import BaseModel

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

    REQUEST_MENU_OPTIONS = "request_menu_options"
    REQUEST_CLINIC_DATA = "request_clinic_data"

class ConfirmIntent(str, Enum):
    REQUEST_CLINIC_DATA = "request_clinic_data"
    CONFIRM_DATA = "confirm_data"

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
    type: str
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

    clinic_data: Dict = {}
    appointment_data: Dict = {}
    confirm_intent: Optional[ConfirmIntent] = None #key would be passed in
    input_request: Optional[str] = None #key would be passed in
    is_processing: bool = False

class AppointmentData(BaseModel):
    patient_name: str
    procedure_type: str
    phone_number: str
    preferred_date: Optional[datetime]
    symptoms: Optional[str] = None
    insurance_info: Optional[str] = None
    special_requirements: Optional[str] = None

@dataclass
class ValidationResult:
    is_valid: bool
    errors: Dict[str, str]