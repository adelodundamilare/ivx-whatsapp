from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ValidationError, field_validator
from app.utils.validator import DataValidator

class AppointmentStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELED = "canceled"
    RESCHEDULED = "rescheduled"
    DOCTOR_ASSIGNED = "doctor_assigned"

class Appointment(BaseModel):
    procedure_type: Optional[str] = None
    preferred_date: Optional[datetime] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    medical_notes: Optional[str] = None
    insurance_info: Optional[str] = None
    special_requirements: Optional[str] = None

    @field_validator('preferred_date')
    def validate_date(cls, v):
        if not DataValidator.validate_date(v):
            raise ValidationError("Invalid appointment date/time")
        return v

    @field_validator('patient_phone')
    def validate_phone(cls, v):
        if not DataValidator.validate_phone(v):
            raise ValidationError("Invalid phone number format")
        return v

class AppointmentEdit(BaseModel):
    appointment_id: str
    new_date: Optional[datetime] = None
    new_doctor_id: Optional[str] = None
    new_procedure_type: Optional[str] = None
    reason: Optional[str] = None

    # @field_validator('preferred_date')
    # def validate_date(cls, v):
    #     if not DataValidator.validate_date(v):
    #         raise ValidationError("Invalid appointment date/time")
    #     return v

    # @field_validator('patient_phone')
    # def validate_phone(cls, v):
    #     if not DataValidator.validate_phone(v):
    #         raise ValidationError("Invalid phone number format")
    #     return v

class AppointmentResponse(BaseModel):
    id: str
    status: str
    doctor_id: Optional[str] = None
    bubble_id: Optional[str] = None

