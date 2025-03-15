
from typing import Dict
from app.agents.base import BaseAgent
import os
from app.core.config import settings
from app.models.models import ConversationState, Intent
from app.utils import helpers
from openai import OpenAI # type: ignore


client = OpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class DialogAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.required_fields = {
            Intent.CREATE_APPOINTMENT: ["patient_name", "service_type", "preferred_date"]
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

    async def process(self, state: ConversationState, intent: Intent, extracted_data: Dict) -> str:
        # Remove any empty or None values from extracted data
        # extracted_data = {
        #     k: v for k, v in extracted_data.items()
        #     if v is not None and v != 'Not provided' and (
        #         not isinstance(v, str) or  # Keep non-string values
        #         (isinstance(v, str) and v.strip())  # Keep non-empty strings
        #     )
        # }
        extracted_data = {
            k: v for k, v in extracted_data.items()
            if v is not None and v != 'Not provided' and (
                not isinstance(v, str) or  # Keep non-string values
                (isinstance(v, str) and v.strip())  # Keep non-empty strings
            ) and (k != "patient_name" or "doe" not in v.lower()) # Check for "doe" in patient_name (case-insensitive)
        }

        # validate date parse_relative_date
        if extracted_data and extracted_data.get('preferred_date'):
            print(f"Extracted Data: {extracted_data} >>>>>>>>>>>>>")
            extracted_data['preferred_date'] = helpers.parse_relative_date(extracted_data['preferred_date'])

        # Update state with new data
        state.collected_data.update(extracted_data)
        state.collected_data.update({'phone_number': state.phone_number})


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
        # missing_fields = state.missing_fields

        # field_prompts = {
        #     "patient_name": "- **Your Name** (Full name)",
        #     "service_type": "- **Procedure Type** (e.g., General Consultation, Dental Cleaning, Blood Test)",
        #     "preferred_date": "- **Preferred Date** (YYYY-MM-DD or 'Next Available')",
        #     "symptoms": "- **Symptoms** (Briefly describe or type 'None')",
        #     "insurance_info": "- **Insurance Info** (Provider name, plan type, or 'Self-Pay')",
        #     "special_requirements": "- **Special Requirements** (e.g., Wheelchair Access, Language Preference, or 'None')",
        #     "phone_number": "- **Phone Number** (For confirmation)"
        # }

        # missing_prompt = "\n".join(field_prompts[field] for field in missing_fields if field in field_prompts)

        # return f'''I can help you book a medical appointment. Please provide: {missing_prompt}'''


    async def _generate_confirmation_message(self, state: ConversationState) -> str:
        # state.confirmation_pending = True

        summary_items = []
        for field, value in state.collected_data.items():
            formatted_field = field.replace('_', ' ').title()  # Removed the (field)
            formatted_value = value if value is not None else 'Not specified'
            summary_items.append(f"- {formatted_field}: {formatted_value}")

        # Join all items with newlines
        details = '\n'.join(summary_items)

        summary_message = f"""Please confirm your details:
{details}

Reply with:
1. Confirm
2. Deny"""

        return summary_message


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