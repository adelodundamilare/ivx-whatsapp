
from typing import Dict
from app.agents.base import BaseAgent
import os
from app.core.config import settings
from app.models.models import ConversationState, Intent
from app.utils.state_manager import state_manager
from openai import OpenAI # type: ignore


client = OpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class DialogAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.required_fields = {
            Intent.CREATE_APPOINTMENT: ["patient_name", "procedure_type", "preferred_date"]
        }
        # self.validation_rules = {
        #     # AppointmentField.PROCEDURE_TYPE: self._validate_procedure,
        #     AppointmentField.PREFERRED_DATE: DataValidator.validate_date,
        #     AppointmentField.PATIENT_NAME: DataValidator.validate_name,
        #     # AppointmentField.CLINIC_NAME: DataValidator.validate_name,
        #     # AppointmentField.SUMMARY: self._validate_summary
        # }
        # self.field_types = {
        #     Intent.CREATE_APPOINTMENT: {
        #         'date': 'date',
        #     }
        #     # Add more intents and their field types
        # }

    async def process(self, phone_number: str, intent: Intent, extracted_data: Dict) -> str:
        state = state_manager.conversation_state

        # validation_result = self._validate_data(intent, extracted_data)
        # if not validation_result.is_valid:
        #     state.validation_errors = validation_result.errors
        #     return await self._generate_validation_error_message(state)

        # Remove any empty or None values from extracted data
        extracted_data = {
            k: v for k, v in extracted_data.items()
            if v is not None and (
                not isinstance(v, str) or  # Keep non-string values
                (isinstance(v, str) and v.strip())  # Keep non-empty strings
            )
        }

        # Update state with new data
        state.collected_data.update(extracted_data)

        # Check missing fields
        required = self.required_fields.get(intent, [])
        state.missing_fields = [field for field in required if field not in state.collected_data]

        if state.missing_fields:
            return await self._generate_prompt_for_missing_fields(state)
        else:
            state.confirmation_pending = True
            return await self._generate_confirmation_message(state)

    async def _generate_prompt_for_missing_fields(self, state: ConversationState) -> str:
        prompt = f"Generate a friendly message asking for: {', '.join(state.missing_fields)}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly medical assistant"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content


    async def _generate_confirmation_message(self, state: ConversationState) -> str:
        # Create a summary of collected information
        state.confirmation_pending = True

        summary = "\n".join([f"{k}: {v}" for k, v in state.collected_data.items()])

        prompt = f"""
        Generate a friendly confirmation message for the following appointment details:
        {summary}

        The message should:
        1. Summarize the collected information
        2. Ask the user to confirm if everything is correct
        3. Inform them they can edit any information if needed
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly medical assistant. Keep responses concise but warm."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )

        # Store the state for future reference
        self.conversation_states[state.phone_number] = state

        return response.choices[0].message.content

    def generate_generic_response(self, message: str) -> str:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a warm and professional medical assistant that helps users schedule, reschedule, and edit doctor appointments. "
                        "Keep responses clear, concise, and friendly while ensuring accuracy in appointment details. "
                        "If needed, ask relevant follow-up questions to confirm appointment details before proceeding."
                    )
                },
                {"role": "user", "content": message}
            ],
            temperature=0.7
        )

        return response.choices[0].message.content


    # def _validate_data(self, intent: Intent, data: Dict) -> ValidationResult:
    #     errors = {}
    #     field_types = self.field_types.get(intent, {})

    #     for field, value in data.items():
    #         field_type = field_types.get(field)
    #         if field_type and field_type in self.validation_rules:
    #             validator = self.validation_rules[field_type]
    #             if not validator(value):
    #                 errors[field] = f"Invalid {field_type} format for {field}"

    #     return ValidationResult(
    #         is_valid=len(errors) == 0,
    #         errors=errors
    #     )


    # async def _generate_validation_error_message(self, state: ConversationState) -> str:
    #     error_messages = []
    #     for field, error in state.validation_errors.items():
    #         error_messages.append(f"- {error}")

    #     return (
    #         "I noticed some issues with the information provided:\n" +
    #         "\n".join(error_messages) +
    #         "\nPlease provide the correct information."
    #     )