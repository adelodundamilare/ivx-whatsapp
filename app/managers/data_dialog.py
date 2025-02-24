
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel
import os
from app.agents import agents
from app.core.config import settings
from app.models.models import ConfirmIntent, Message
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils import helpers
from app.utils.state_manager import StateManager
from openai import OpenAI # type: ignore


client = OpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class DataType(Enum):
    CLINIC = "clinic"
    APPOINTMENT = "appointment"

class DataValidator(BaseModel):
    required_fields: List[str]
    validation_rules: Dict = {}

DATA_CONFIGS = {
    DataType.CLINIC: DataValidator(
        required_fields=["full_name", "clinic_name"],
        validation_rules={
            "full_name": lambda x: "doe" not in x.lower()
        }
    ),
    DataType.APPOINTMENT: DataValidator(
        required_fields=["date", "time", "service_type", "location"],
        validation_rules={
            "date": lambda x: helpers.validate_date(x)
        }
    ),
    # Add more configurations as needed
}

@dataclass
class ValidationResult:
    invalid_fields: List[str]
    valid_fields: Dict[str, any]

class DataDialogManager:
    def __init__(self, message: Message, data_type: DataType):
        self.message = message
        self.data_type = data_type
        self.state_manager = StateManager()
        self.whatsapp_service = WhatsAppBusinessAPI(message)
        self.state = self.state_manager.get_state(message.phone_number)
        self.config = DATA_CONFIGS[data_type]

    async def collect_data(self):
        requested_keys = (
            [self.state.input_request]
            if self.state.input_request
            else self.config.required_fields
        )

        extracted_data = await agents.extractor(requested_keys, self.message.content)
        cleaned_data = self._clean_data(extracted_data)
        merged_data = self._merge_with_existing_data(cleaned_data)

        validation_result = self._validate_data(merged_data)

        if validation_result.valid_fields:
            await self._handle_valid_data(merged_data)

        if validation_result.invalid_fields:
            await self._handle_invalid_fields(validation_result.invalid_fields)
        else:
            self.state_manager.update_state(
                self.message.phone_number,
                confirm_intent=f"CONFIRM_{self.data_type.value.upper()}"
            )
            await self._confirm_input(merged_data)

        return merged_data

    def _clean_data(self, data: Dict) -> Dict:
        return {
            k: v for k, v in data.items()
            if self._is_valid_value(v) and self._passes_validation_rules(k, v)
        }

    def _is_valid_value(self, value) -> bool:
        if value is None or value == 'Not provided':
            return False
        if isinstance(value, str) and not value.strip():
            return False
        return True

    def _passes_validation_rules(self, key: str, value) -> bool:
        validation_rule = self.config.validation_rules.get(key)
        return validation_rule(value) if validation_rule else True

    def _merge_with_existing_data(self, new_data: Dict) -> Dict:
        existing_data = getattr(self.state, f"{self.data_type.value}_data", {})
        print(self.state, 'state data')
        print(existing_data, 'existing_data')
        return {**existing_data, **new_data}

    def _validate_data(self, data: Dict) -> ValidationResult:
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

    async def _handle_invalid_fields(self, invalid_fields: List[str]):
        field = invalid_fields[0]
        self.state_manager.update_state(
            self.message.phone_number,
            input_request=field
        )
        await self.whatsapp_service.send_text_message(
            f'It looks like there\'s an issue with your {field.replace("_", " ").title()}, kindly re-enter it correctly.'
        )

    async def _handle_valid_data(self, data: Dict):
        existing_data = getattr(self.state, f"{self.data_type.value}_data", {})
        updated_data = {**existing_data, **data}

        self.state_manager.update_state(
            self.message.phone_number,
            **{f"{self.data_type.value}_data": updated_data}
        )

    async def _confirm_input(self, data: Dict):
        await self._send_data_review(data)
        await self._send_confirmation_buttons(data)

    async def _send_data_review(self, data: Dict):
        formatted_data = self._format_data_for_display(data)
        await self.whatsapp_service.send_text_message(
            "Please review the information:\n\n"
            f"{formatted_data}"
        )

    async def _send_confirmation_buttons(self, data: Dict):
        buttons = self._create_buttons(data)

        # Send buttons in chunks of 3 (WhatsApp limit)
        for i in range(0, len(buttons), 3):
            chunk = buttons[i:i + 3]
            header_text = "Is this information correct?" if i == 0 else "Additional fields:"
            await self.whatsapp_service.send_buttons(
                body_text=header_text,
                buttons=chunk
            )

    def _format_data_for_display(self, data: Dict) -> str:
        return "\n".join(
            f"• {key.replace('_', ' ').title()}: {value}"
            for key, value in data.items()
        )

    def _create_buttons(self, data: Dict) -> List[Dict]:
        update_buttons = [
            {
                "type": "reply",
                "reply": {
                    "id": f"UPDATE_{key.upper()}",
                    "title": f"Update {key.replace('_', ' ').title()}"
                }
            }
            for key in data.keys()
        ]

        confirm_button = {
            "type": "reply",
            "reply": {
                "id": "CONFIRM_ALL",
                "title": "✓ Confirm All"
            }
        }

        return [*update_buttons, confirm_button]

# class DialogClinicData(BaseAgent):
#     def __init__(self, message: Message):
#         super().__init__()
#         self.message = message
#         self.state_manager = StateManager()
#         self.whatsapp_service = WhatsAppBusinessAPI(self.message)
#         self.state = self.state_manager.get_state(self.message.phone_number)
#         self.required_fields = {
#             Intent.REQUEST_CLINIC_DATA: ["full_name", "clinic_name"]
#         }

#     async def parse_message_with_ai(self):
#         requested_keys = self.required_fields.get(Intent.REQUEST_CLINIC_DATA, [])

#         if self.state.input_request:
#             requested_keys = [self.state.input_request]

#         extracted_data = await agents.extractor(requested_keys, self.message.content)
#         extracted_data = self._clean_data(extracted_data)
#         extracted_data = {
#             **self.state.clinic_data,
#             **extracted_data
#         }

#         # Check if all required fields are present
#         invalid_fields = [
#             field for field in self.required_fields[Intent.REQUEST_CLINIC_DATA]
#             if field not in extracted_data
#         ]

#         valid_fields = {
#             field: extracted_data[field]
#             for field in self.required_fields[Intent.REQUEST_CLINIC_DATA]
#             if field in extracted_data
#         }

#         if valid_fields:
#             updated_clinic_data = {
#                 **self.state.clinic_data,
#                 **valid_fields
#             }
#             self.state_manager.update_state(
#                 self.message.phone_number,
#                 clinic_data=updated_clinic_data
#             )

#         if invalid_fields:
#             field = invalid_fields[0]
#             self.state_manager.update_state(self.message.phone_number, input_request=field)
#             await self.whatsapp_service.send_text_message(
#                 f'It looks like there\'s an issue with your {field.replace("_", " ").title()}. Please re-enter it correctly.'
#             )
#         else:
#             self.state_manager.update_state(self.message.phone_number, confirm_intent=ConfirmIntent.REQUEST_CLINIC_DATA)
#             await self._confirm_input(extracted_data)

#         return extracted_data

#     def _clean_data(self, data):
#         return {
#             k: v for k, v in data.items()
#             if v is not None and v != 'Not provided' and (
#                 not isinstance(v, str) or  # Keep non-string values
#                 (isinstance(v, str) and v.strip())  # Keep non-empty strings
#             ) and (k != "full_name" or "doe" not in v.lower())  # Check for placeholder name
#         }

#     async def _confirm_input(self, data):
#         formatted_data = "\n".join(f"• {key.replace('_', ' ').title()}: {value}"
#                               for key, value in data.items())

#         await self.whatsapp_service.send_text_message(
#             "Please review the information you've provided:\n\n"
#             f"{formatted_data}"
#         )

#         buttons = [
#             {
#                 "type": "reply",
#                 "reply": {
#                     "id": f"UPDATE_{key.upper()}",
#                     "title": f"Update {key.replace('_', ' ').title()}"
#                 }
#             }
#             for key in data.keys()
#         ]

#         buttons.append({
#             "type": "reply",
#             "reply": {
#                 "id": "CONFIRM_ALL",
#                 "title": "✓ Confirm All"
#             }
#         })

#         await self.whatsapp_service.send_buttons(
#             body_text="Is this information correct?",
#             # footer_text="Select an option to continue",
#             buttons=buttons[:3]
#         )

#         if len(buttons) > 3:
#             for i in range(3, len(buttons), 3):
#                 chunk = buttons[i:i + 3]
#                 await self.whatsapp_service.send_buttons(
#                     header_text="Additional fields:",
#                     buttons=chunk
#                 )

