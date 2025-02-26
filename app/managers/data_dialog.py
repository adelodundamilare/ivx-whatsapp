
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

from pydantic import BaseModel
import os
from app.agents import agents
from app.core.config import settings
from app.models.models import ConfirmIntent, Message
from app.services.bubble_client import bubble_client
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

    async def collect_data(self, is_updating_input: bool = False):

        if self.state.confirm_intent == ConfirmIntent.CONFIRM_DATA:
            await self._handle_confirm_response()
            return

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
            await self._handle_invalid_fields(validation_result.invalid_fields, is_updating_input)
        else:
            self.state_manager.update_state(
                self.message.phone_number,
                confirm_intent=ConfirmIntent.CONFIRM_DATA
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

    async def _handle_invalid_fields(self, invalid_fields: List[str], is_updating_input: bool = False):
        field = invalid_fields[0]
        self.state_manager.update_state(
            self.message.phone_number,
            input_request=field
        )

        content = f"Apologies, but we were unable to capture your {field.replace('_', ' ').title()}. Please provide a valid input."

        if is_updating_input:
            content = f"Kindly input your {field.replace('_', ' ').title()}"

        await self.whatsapp_service.send_text_message(content)

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

    async def _handle_confirm_response(self):
        response = self.message.content

        if response == "CONFIRM_ALL":
            await self._handle_confirmation()
        elif response.startswith("UPDATE_"):
            field_to_update = response.replace("UPDATE_", "").lower()
            await self._handle_field_update(field_to_update)

    async def _handle_confirmation(self):
        # send result to bubble...
        data = getattr(self.state, f"{self.data_type.value}_data", {})
        data = { **data, "phone_number": self.message.phone_number }

        await bubble_client.create_clinic(data)

        await self.whatsapp_service.send_text_message(
            "Great! your data has been saved, feel free to send '/help' to change or update your clinic information."
        )
        # show menu prompt...

    async def _handle_field_update(self, field_to_update: str):
        invalid_field = [field_to_update]

        existing_data = getattr(self.state, f"{self.data_type.value}_data", {})
        updated_data = {k: v for k, v in existing_data.items() if k != field_to_update}

        self.state_manager.update_state(
            self.message.phone_number,
            confirm_intent=None,
            **{f"{self.data_type.value}_data": updated_data},
            input_request=invalid_field
        )
        await self.collect_data(is_updating_input=True)
