from datetime import datetime
from typing import Optional
import re


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
    def validate_date(date_str: str) -> bool:
        """Validate if date is within acceptable range and business hours"""
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if date < datetime.now():
                return False

            # if date.weekday() in BusinessHours.WEEKEND_DAYS:
            #     return False

            # if date.hour < BusinessHours.START_HOUR or date.hour >= BusinessHours.END_HOUR:
            #     return False

            return True
        except:
            return False

    @staticmethod
    def validate_name(name: str) -> bool:
        return bool(name and len(name.strip()) >= 3)

    @staticmethod
    def sanitize_input(text: str) -> str:
        sanitized = re.sub(r'[<>{}\\]', '', text)
        return sanitized.strip()
