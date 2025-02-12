from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict

from app.services import database
from app.utils.state_manager import get_current_step, set_current_step
from app.utils.validator import DataValidator

PROCEDURE_TYPE_OPTIONS: Dict[str, str] = {
    "1": "Wisdom Teeth",
    "2": "Dental Implants",
    "3": "Root Canal",
    "4": "Multiple Extractions",
    "5": "Pediatric Dental"
}

class AppointmentField(Enum):
    PROCEDURE_TYPE = "procedure_type"
    PREFERRED_DATE = "preferred_date"
    PATIENT_NAME = "patient_name"
    CLINIC_NAME = "clinic_name"
    SUMMARY = "summary"

class AppointmentPrompts:
    @staticmethod
    def get_procedure_prompt() -> str:
        prompt = "What type of procedure is this for?\n\n"
        return prompt + "\n".join(
            f"{key}. {value}"
            for key, value in PROCEDURE_TYPE_OPTIONS.items()
        )

    PREFERRED_DATE = "What date would you prefer for the procedure?"
    PATIENT_NAME = "Please enter the your name:"
    CLINIC_NAME = "Which dental clinic will the procedure be at?"

    @staticmethod
    def get_summary(data: Dict[str, str]) -> str:
        clinic_name = data.get('clinic_name', 'Not specified')
        procedure_type = data.get('procedure_type', 'Not specified')
        preferred_date = data.get('preferred_date', 'Not specified')
        patient_name = data.get('patient_name', 'Not specified')

        summary_message = f"""Please confirm your appointment details:
- Clinic: {clinic_name}
- Procedure: {procedure_type}
- Date: {preferred_date}
- Patient: {patient_name}

Reply with:
1. Confirm
2. Start over"""

        return summary_message

class AppointmentHandler:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.validators = {
            AppointmentField.PROCEDURE_TYPE: self._validate_procedure,
            AppointmentField.PREFERRED_DATE: DataValidator.validate_date,
            AppointmentField.PATIENT_NAME: DataValidator.validate_name,
            AppointmentField.CLINIC_NAME: DataValidator.validate_name,
            AppointmentField.SUMMARY: self._validate_summary
        }
        self.error_messages = {
            AppointmentField.PROCEDURE_TYPE: lambda: f"Please select a valid procedure type ({self._get_procedure_range()}).",
            AppointmentField.PREFERRED_DATE: lambda: "Please provide a valid future date in YYYY-MM-DD format.",
            AppointmentField.PATIENT_NAME: lambda: "Please enter a valid name.",
            AppointmentField.CLINIC_NAME: lambda: "Please provide a valid clinic name",
            AppointmentField.SUMMARY: lambda: "Please reply with 1 to confirm or 2 to make changes."
        }
        self.prompts = {
            AppointmentField.PROCEDURE_TYPE: AppointmentPrompts.get_procedure_prompt,
            AppointmentField.PREFERRED_DATE: lambda: AppointmentPrompts.PREFERRED_DATE,
            AppointmentField.PATIENT_NAME: lambda: AppointmentPrompts.PATIENT_NAME,
            AppointmentField.CLINIC_NAME: lambda: AppointmentPrompts.CLINIC_NAME,
            AppointmentField.SUMMARY: lambda data: AppointmentPrompts.get_summary(data)
        }

    def _get_procedure_range(self) -> str:
        numbers = sorted(map(int, PROCEDURE_TYPE_OPTIONS.keys()))
        return f"{numbers[0]}-{numbers[-1]}"

    def _validate_procedure(self, message: str) -> bool:
        return message in PROCEDURE_TYPE_OPTIONS

    def _validate_summary(self, message: str) -> bool:
        return message in {'1', '2'}

    async def _handle_summary_confirmation(self, message: str, data: Dict[str, str]) -> Optional[str]:
        if message == '1':
            return await self._process_appointment(data)
        elif message == '2':
            return self._reset_appointment(data)
        return None

    async def _process_appointment(self, data: Dict[str, str]) -> str:
        # Add backend service call here
        await database.create_appointment(data)
        return (
            f"Great! I'll help you schedule an appointment for a "
            f"*{data['procedure_type']}* procedure on *{data['preferred_date']}* "
            f"at *{data['clinic_name']}*. Would you like me to check doctor availability now?"
        )

    def _reset_appointment(self, data) -> str:
        del data["procedure_type"]
        del data["preferred_date"]
        del data["patient_name"]
        del data["clinic_name"]
        # set_current_step("procedure_type")
        # self.state_manager.reset_appointment_data()
        set_current_step(AppointmentField.PROCEDURE_TYPE.value)
        return AppointmentPrompts.get_procedure_prompt()

    async def handle_appointment(self, message: str) -> str:
        data = self.state_manager.appointment_data
        current_step = get_current_step()

        # Handle current step if exists
        if current_step:
            field = AppointmentField(current_step)
            if not self.validators[field](message):
                return self.error_messages[field]()

            if field == AppointmentField.PROCEDURE_TYPE:
                data[field.value] = PROCEDURE_TYPE_OPTIONS[message]
            elif field == AppointmentField.SUMMARY:
                return await self._handle_summary_confirmation(message, data)
            else:
                data[field.value] = message

        # Find and handle next step
        required_fields = [field.value for field in AppointmentField]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            next_field = AppointmentField(missing_fields[0])
            set_current_step(next_field.value)
            return self.prompts[next_field](data) if next_field == AppointmentField.SUMMARY else self.prompts[next_field]()

        return "Appointment process completed."