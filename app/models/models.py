
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict, Union
from pydantic import BaseModel

class Intent(str, Enum):
    CREATE_APPOINTMENT = "create_appointment"
    CHECK_STATUS = "check_status"
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
    REQUEST_ID = "request_id"
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
    current_intent: Optional[Intent] = None
    phone_number: Optional[str]=None
    collected_data: Dict = {}
    missing_fields: List[str] = []
    last_interaction: Optional[datetime]=datetime.now()
    confirmation_pending: bool = False
    modification_pending: bool = False
    context: Optional[Dict] = {}
    interaction_count: Optional[int] = 0
    last_error: Optional[str] = None

    clinic_data: Dict = {}
    conversation_history: List[Dict[str, str]] = []
    appointment_data: Dict = {}
    confirm_intent: Optional[ConfirmIntent] = None #key would be passed in
    input_request: Optional[str] = None #key would be passed in
    is_processing: bool = False

class AppointmentData(BaseModel):
    patient_name: str
    service_type: str
    phone_number: str
    preferred_date: Optional[datetime]
    symptoms: Optional[str] = None
    insurance_info: Optional[str] = None
    special_requirements: Optional[str] = None

    selected_doctor_id: Optional[str] = None
    notes: Optional[str] = None

    procedure_details: Optional[str] = None
    doctor_specialization: Optional[str] = None

class Doctor(BaseModel):
    id: str
    name: str
    specialties: List[str]
    available_times: List[Dict[str, Any]]
    clinic_id: str
    rating: Optional[float] = None

class DataType(Enum):
    CLINIC = "clinic"
    APPOINTMENT = "appointment"


@dataclass
class ValidationResult:
    invalid_fields: List[str]
    valid_fields: Dict[str, Any]

class ProcedureType(str, Enum):
    CONSULTATION = "consultation"
    SURGERY = "surgery"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    SPECIALIZED = "specialized"

class MessageType(str, Enum):
    TEXT = "text"
    OPTION = "option"
    DATE = "date"
    TIME = "time"
    CONFIRMATION = "confirmation"

class UMessage(BaseModel):
    text: str
    type: MessageType
    options: Optional[List[str]] = None
    sender: str  # "user" or "assistant"

class Language(str, Enum):
    ENGLISH = "english"
    SPANISH = "spanish"

main_menu_options = [
    {
        "title": "Menu Options",
        "rows": [
            {
                "id": "CREATE_APPOINTMENT",
                "title": "Create appointment"
            },
            {
                "id": "CHECK_APPOINTMENT_STATUS",
                "title": "Check Status"
            },
            {
                "id": "UPDATE_APPOINTMENT",
                "title": "Update appointment"
            },
            {
                "id": "CANCEL_APPOINTMENT",
                "title": "Cancel appointment"
            }
        ]
    }
]

class AppointmentState(TypedDict):
    clinic_info: Optional[Dict] = {'full_name': None, 'clinic_name': None, 'phone_number': None}
    procedure_info: Optional[Dict] = None
    doctor_preferences: Optional[List[str]] = None
    current_doctor_index: int = 0
    selected_doctor: Optional[Dict] = None
    appointment_confirmed: bool = False

    is_processing: bool = False
    history: List[Dict[str, str]] = []
    phone_number: Optional[str]=None
    collected_data: Dict = {}
    missing_fields: List[str] = []


class ClinicState(TypedDict):
    user_input: str
    full_name: str
    clinic_name: str
    patient_age_range: str
    doctor_index: int
    needs_clarification: bool
    intent: str
    clarification_attempts: int