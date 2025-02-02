from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import re

from app.models.whatsapp import BusinessHours


class ValidationError(Exception):
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(self.message)

class AppointmentError(Exception):
    pass



class DataValidator:
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        pattern = r'^\+?1?\d{9,15}$'
        return bool(re.match(pattern, phone))

    @staticmethod
    def validate_date(date: datetime) -> bool:
        """Validate if date is within acceptable range and business hours"""
        if date < datetime.now():
            return False

        if date.weekday() in BusinessHours.WEEKEND_DAYS:
            return False

        if date.hour < BusinessHours.START_HOUR or date.hour >= BusinessHours.END_HOUR:
            return False

        return True

    @staticmethod
    def validate_clinic_name(name: str) -> bool:
        """Validate clinic name"""
        return bool(name and len(name.strip()) >= 3)

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize input text"""
        # Remove any potential harmful characters
        sanitized = re.sub(r'[<>{}\\]', '', text)
        return sanitized.strip()
