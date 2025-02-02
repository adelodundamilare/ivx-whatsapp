
from typing import Any, Dict
import json
from datetime import datetime
from app.utils.logger import setup_logger
from pydantic import ValidationError
from app.utils.validator import AppointmentError

logger = setup_logger("error_api", "error.log")


class ErrorHandler:
    @staticmethod
    def log_error(error: Exception, context: Dict[str, Any] = None) -> None:
        """Log error with context"""
        error_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat(),
            'context': context or {}
        }
        logger.error(json.dumps(error_data))

    @staticmethod
    def format_error_message(error: Exception) -> str:
        """Format error message for user display"""
        if isinstance(error, ValidationError):
            return f"Invalid input: {error.message}"
        elif isinstance(error, AppointmentError):
            return f"Appointment error: {str(error)}"
        else:
            return "An unexpected error occurred. Please try again."