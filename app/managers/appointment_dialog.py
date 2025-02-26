from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Callable, Optional, TypeVar, Generic, Union

from pydantic import BaseModel
import os
from app.agents import agents
from app.core.config import settings
from app.models.models import ConfirmIntent, DataType, Intent, Message
from app.services.bubble_client import bubble_client
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils import helpers
from app.utils.state_manager import StateManager
from openai import OpenAI # type: ignore
from app.models.models import main_menu_options


client = OpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

T = TypeVar('T')

class DataValidator(BaseModel):
    required_fields: List[str]
    validation_rules: Dict[str, Callable] = {}
    data_handler: Optional[Callable] = None
    field_prompts: Dict[str, str] = {}  # Added field prompts

# Define validation functions
def validate_date(date_str: str) -> bool:
    return helpers.validate_date(date_str)

def validate_time(time_str: str) -> bool:
    return helpers.validate_time(time_str) if hasattr(helpers, 'validate_time') else True

# Handler functions for different data types
async def handle_appointment_data(data: Dict[str, Any], phone_number: str) -> bool:
    data = {**data, "phone_number": phone_number, "status": "pending"}
    return await bubble_client.create_appointment(data)

DATA_CONFIGS = {
    DataType.APPOINTMENT: DataValidator(
        required_fields=["patient_name", "patient_gender", "patient_age_range", "date", "time", "service_type", "location"],
        validation_rules={
            "date": validate_date,
            # "time": validate_time
        },
        data_handler=handle_appointment_data,
        field_prompts={
            "patient_name": "Kindly input the patient's name",
            "patient_age_range": "What is the patient's age?",

            "date": "What date would you like to book? (DD-MM-YYYY)",
            "time": "What time would you prefer? (e.g. 14:00)",
            "patient_gender": "What is the patient's gender?",
            "service_type": "What type of service are you booking?",
            "location": "Which location would you like to have the appointment?"
        }
    )
}

@dataclass
class ValidationResult:
    invalid_fields: List[str]
    valid_fields: Dict[str, Any]

class AppointmentDialog(Generic[T]):
    def __init__(self, message: Message, data_type: DataType):
        self.message = message
        self.data_type = data_type
        self.state_manager = StateManager()
        self.whatsapp_service = WhatsAppBusinessAPI(message)
        self.state = self.state_manager.get_state(message.phone_number)
        self.config = DATA_CONFIGS[data_type]
        self.current_field_index = 0

        if not hasattr(self.state, f"{self.data_type.value}_data"):
            self.state_manager.update_state(
                self.message.phone_number,
                **{f"{self.data_type.value}_data": {}}
            )

    async def collect_data(self) -> Union[Dict[str, Any], ValidationResult]:
        if self.state.confirm_intent == ConfirmIntent.CONFIRM_DATA:
            await self._handle_confirm_response()
            return getattr(self.state, f"{self.data_type.value}_data", {})

        if self.state.input_request:
            await self._process_step_input()
            return

        await self.move_to_next_field()
        return self._validate_data(getattr(self.state, f"{self.data_type.value}_data", {}))

    async def _process_step_input(self) -> ValidationResult:
        field = self.state.input_request

        extracted_data = await agents.extractor([field], self.message.content)

        cleaned_data = self._clean_data(extracted_data)

        if field in cleaned_data:
            merged_data = self._merge_with_existing_data(cleaned_data)
            await self._handle_valid_data(merged_data)

            self.state_manager.update_state(
                self.message.phone_number,
                input_request=None
            )

            await self.move_to_next_field()
        else:
            await self._send_field_prompt(field, is_retry=True)

        data = getattr(self.state, f"{self.data_type.value}_data", {})
        return self._validate_data(data)

    async def _send_field_prompt(self, field: str, is_retry: bool = False):
        prompt = self.config.field_prompts.get(field)

        if field == "date":
            if is_retry:
                prompt = f"Please provide a valid future date. {prompt}"
                await self.whatsapp_service.send_text_message(prompt)
                return

        if field == "time":
            if is_retry:
                prompt = f"I couldn't understand that. {prompt}"
                await self.whatsapp_service.send_text_message(prompt)

            await self._send_time_slot()
            return


        if field == "patient_gender":
            if is_retry:
                prompt = f"I couldn't understand that. {prompt}"
                await self.whatsapp_service.send_text_message(prompt)

            await self._send_patient_gender_list()
            return

        if field == "location":
            if is_retry:
                prompt = f"I couldn't understand that. {prompt}"
                await self.whatsapp_service.send_text_message(prompt)

            await self._send_location_option()
            return

        if field == "service_type":
            if is_retry:
                prompt = f"I couldn't understand that. {prompt}"
                await self.whatsapp_service.send_text_message(prompt)

            await self._send_service_type_list()
            return

        if field == "patient_age_range":
            if is_retry:
                prompt = f"I couldn't understand that. {prompt}"
                await self.whatsapp_service.send_text_message(prompt)

            await self._send_patient_age_range_list()
            return

        if prompt is None:
            prompt = f"Please provide your {field.replace('_', ' ')}"

        if is_retry:
            prompt = f"I couldn't understand that. {prompt}"

        await self.whatsapp_service.send_text_message(prompt)

    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            k: v for k, v in data.items()
            if self._is_valid_value(v) and self._passes_validation_rules(k, v)
        }

    def _is_valid_value(self, value: Any) -> bool:
        if value is None or value == 'Not provided':
            return False
        if isinstance(value, str) and not value.strip():
            return False
        return True

    def _passes_validation_rules(self, key: str, value: Any) -> bool:
        validation_rule = self.config.validation_rules.get(key)
        return validation_rule(value) if validation_rule else True

    def _merge_with_existing_data(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        existing_data = getattr(self.state, f"{self.data_type.value}_data", {})
        return {**existing_data, **new_data}

    def _validate_data(self, data: Dict[str, Any]) -> ValidationResult:
        invalid_fields = [
            field for field in self.config.required_fields
            if field not in data
        ]
        valid_fields = {
            field: data[field]
            for field in self.config.required_fields
            if field in data
        }
        return ValidationResult(invalid_fields, valid_fields)

    async def _handle_valid_data(self, data: Dict[str, Any]):
        existing_data = getattr(self.state, f"{self.data_type.value}_data", {})
        updated_data = {**existing_data, **data}

        self.state_manager.update_state(
            self.message.phone_number,
            **{f"{self.data_type.value}_data": updated_data}
        )

    async def _confirm_input(self, data: Dict[str, Any]):
        await self._send_data_review(data)
        await self._send_confirmation_buttons(data)

    async def _send_data_review(self, data: Dict[str, Any]):
        formatted_data = self._format_data_for_display(data)
        await self.whatsapp_service.send_text_message(
            "Please review the information:\n\n"
            f"{formatted_data}"
        )

    async def _send_confirmation_buttons(self, data: Dict[str, Any]):
        buttons = self._create_buttons(data)

        for i in range(0, len(buttons), 3):
            print(f"Sending chunk *******************************: {chunk}")
            chunk = buttons[i:i + 3]
            await self.whatsapp_service.send_buttons(
                body_text="Select to update.",
                buttons=chunk
            )

    def _format_data_for_display(self, data: Dict[str, Any]) -> str:
        return "\n".join(
            f"• {key.replace('_', ' ').title()}: {value}"
            for key, value in data.items()
        )

    def _create_buttons(self, data: Dict[str, Any]) -> List[Dict]:
        # update_buttons = [
        #     {
        #         "type": "reply",
        #         "reply": {
        #             "id": f"UPDATE_{key.upper()}",
        #             "title": f"Update {key.replace('_', ' ').title()}"
        #         }
        #     }
        #     for key in data.keys()
        # ]
        update_buttons = []
        for i, key in enumerate(data.keys()):
            update_buttons.append({
                "type": "reply",
                "reply": {
                    "id": f"UPDATE_{i}",
                    "title": f"Update {key.replace('_', ' ').title()}"
                }
            })

        confirm_button = {
            "type": "reply",
            "reply": {
                "id": "CONFIRM_ALL",
                "title": "✓ Confirm All"
            }
        }

        print(update_buttons, 'update_buttons')

        return [*update_buttons, confirm_button]

    async def _handle_confirm_response(self):
        response = self.message.content

        if response == "CONFIRM_ALL":
            await self._handle_confirmation()
        elif response.startswith("UPDATE_"):
            num_id = response.replace("UPDATE_", "").lower()
            await self._handle_field_update(num_id)

    async def _handle_confirmation(self):
        data = getattr(self.state, f"{self.data_type.value}_data", {})

        if self.config.data_handler:
            success = await self.config.data_handler(data, self.message.phone_number)
        else:
            success = await bubble_client.create_clinic({**data, "phone_number": self.message.phone_number})

        # Clear confirmation intent after handling data
        self.state_manager.update_state(
            self.message.phone_number,
            confirm_intent=None,
            input_request=None
        )

        data_type_name = self.data_type.value.replace('_', ' ')
        if success:
            await self._handle_confirmation_success()
        else:
            await self.whatsapp_service.send_text_message(
                f"Sorry, we encountered an issue saving your {data_type_name} information. Please try again later."
            )

    async def _handle_field_update(self, num_id: str):
        existing_data = getattr(self.state, f"{self.data_type.value}_data", {})
        keys_list = list(existing_data.keys())
        field_to_update = keys_list[int(num_id)]
        updated_data = {k: v for k, v in existing_data.items() if k != field_to_update}

        self.state_manager.update_state(
            self.message.phone_number,
            confirm_intent=None,
            **{f"{self.data_type.value}_data": updated_data},
            input_request=field_to_update
        )

        await self._send_field_prompt(field_to_update)

    async def move_to_next_field(self) -> Optional[str]:
        data = getattr(self.state, f"{self.data_type.value}_data", {})

        for field in self.config.required_fields:
            if field not in data:
                self.state_manager.update_state(
                    self.message.phone_number,
                    input_request=field
                )
                await self._send_field_prompt(field)
                return field

        self.state_manager.update_state(
            self.message.phone_number,
            confirm_intent=ConfirmIntent.CONFIRM_DATA,
            input_request=None
        )

        # await self._confirm_input(data)

    def get_current_field(self) -> Optional[str]:
        """Get the current field being collected"""
        return self.state.input_request

    def get_collected_data(self) -> Dict[str, Any]:
        return getattr(self.state, f"{self.data_type.value}_data", {})

    def get_remaining_fields(self) -> List[str]:
        """Get list of fields that still need to be collected"""
        data = self.get_collected_data()
        return [field for field in self.config.required_fields if field not in data]

    def is_data_complete(self) -> bool:
        """Check if all required data has been collected"""
        return len(self.get_remaining_fields()) == 0

    def _send_service_type_list(self):
        service_types = [
            ("GENERAL_CONSULTATION", "General Consultation"),
            ("DENTAL_CHECKUP", "Dental Checkup"),
            ("EYE_EXAM", "Eye Exam"),
            ("PHYSICAL_THERAPY", "Physical Therapy"),
            ("PEDIATRIC_APPOINTMENT", "Pediatric Appointment"),
            ("DERMATOLOGY_APPOINTMENT", "Dermatology Appointment"),
            ("GYNECOLOGY_APPOINTMENT", "Gynecology Appointment"),
            # ("CARDIOLOGY_APPOINTMENT", "Cardiology Appointment"),
            # ("ORTHOPEDIC_APPOINTMENT", "Orthopedic Appointment"),
            # ("MENTAL_HEALTH_COUNSELING", "Mental Health Counseling")
        ]

        options = [
            {
                "title": "Select Option",
                "rows": [{"id": id_, "title": title} for id_, title in service_types]
            }
        ]

        return self.whatsapp_service.send_interactive_list(
            button_text="Select",
            body_text="Please select the type of appointment you are seeking:",
            header_text="",
            sections=options
        )

    def _send_patient_age_range_list(self):
        service_types = [
            ("LESS_THAN_18", "< 18"),
            ("18_TO_25", "18 to 25"),
            ("26_TO_35", "26 to 35"),
            ("36_TO_45", "36 to 45"),
            ("46_TO_55", "46 to 55"),
            ("OVER_55", "> 55")
        ]

        options = [
            {
                "title": "Select Option",
                "rows": [{"id": id_, "title": title} for id_, title in service_types]
            }
        ]

        return self.whatsapp_service.send_interactive_list(
            button_text="Select Option",
            body_text="Please select your patient's age group",
            header_text="",
            sections=options
        )

    def _send_patient_gender_list(self):
        service_types = [
            ("FEMALE", "Female"),
            ("MALE", "Male"),
            ("OTHER", "Other")
        ]

        options = [
            {
                "title": "Select Option",
                "rows": [{"id": id_, "title": title} for id_, title in service_types]
            }
        ]

        return self.whatsapp_service.send_interactive_list(
            button_text="Select Option",
            body_text="Please select your patient's gender",
            header_text="",
            sections=options
        )

    async def _send_date_list(self):

        today = datetime.now()
        available_dates = [
            today + timedelta(days=x)
            for x in range(14)
            if (today + timedelta(days=x)).weekday() < 5  # Exclude weekends
        ]

        # Send the enhanced date picker
        await self.whatsapp_service.send_date_picker(
            available_dates=available_dates,
            # header_text="Select Date",
            body_text="Please select a date from the calendar below:"
        )

    async def _send_time_slot(self):
        time_slots = ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00", "16:00"]

        await self.whatsapp_service.send_time_slots(
            available_slots=time_slots,
        )

    async def _send_location_option(self):
        await self.whatsapp_service.request_location_selection()

    async def _handle_confirmation_success(self):
        self.state_manager.update_state(
            self.message.phone_number,
            current_intent=Intent.REQUEST_MENU_OPTIONS
        )

        await self.whatsapp_service.send_text_message("Great! Your appointment has been successfully booked.")
        await self.whatsapp_service.send_text_message("We're now reaching out to the best doctors based on your preferences. You'll receive a confirmation soon.")

        await self.whatsapp_service.send_interactive_list(
            header_text="",
            body_text="If you need anything else, please select an option from the main menu",
            button_text="View Options",
            sections=main_menu_options
        )