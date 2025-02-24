# import asyncio
# import json
# import traceback
# from typing import Dict
# from app.agents.base import BaseAgent
# import os
# from app.core.config import settings
# from app.models.models import Intent
# from openai import OpenAI # type: ignore


# client = OpenAI(api_key=settings.OPENAI_API_KEY)
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# class ExtractionAgent(BaseAgent):
#     async def process(self, message: str, intent: Intent) -> Dict:
#         max_retries = 3
#         retry_delay = 2  # seconds

#         for attempt in range(max_retries):
#             try:
#                 prompt = self._create_extraction_prompt(message, intent)
#                 response = client.chat.completions.create(
#                     model="gpt-3.5-turbo",
#                     messages=[
#                         {"role": "system", "content": "Extract the following information in JSON format"},
#                         {"role": "user", "content": prompt}
#                     ],
#                     temperature=0.3
#                 )

#                 content = response.choices[0].message.content

#                 if not content:
#                     print("Content is empty")
#                     return {}

#                 if isinstance(content, dict):
#                     return content

#                 if isinstance(content, str):
#                     content = content.strip()

#                 try:
#                     return json.loads(content)
#                 except json.JSONDecodeError:
#                     try:
#                         content = content.replace("'", '"')
#                         return json.loads(content)
#                     except json.JSONDecodeError:
#                         print(f"Failed to parse message {message} with type: {type(content)} as JSON")
#                         raise  # Re-raise to trigger retry

#             except Exception as e:
#                 if attempt < max_retries - 1:  # Don't sleep on the last attempt
#                     print(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
#                     await asyncio.sleep(retry_delay)
#                     retry_delay *= 2  # Double the delay for next retry
#                 else:
#                     print(f"All {max_retries} attempts failed. Final error: {str(e)}")
#                     return {}

#         return {}

#     def _create_extraction_prompt(self, message: str, intent: Intent) -> str:
#         base_prompt = f"Message: {message}\n\Request for the following information extract the response in JSON format."

#         if intent == Intent.CREATE_APPOINTMENT:
#             return f"""
#             {base_prompt}
#             - patient_name: The name of the patient
#             - procedure_type: Type of medical procedure or consultation needed
#             - preferred_date: Preferred appointment date
#             - symptoms: Any symptoms mentioned
#             - insurance_info: Any insurance information provided
#             - special_requirements: Any special needs or requirements mentioned
#             - phone_number: Contact number if provided
#             """

#         elif intent == Intent.EDIT_APPOINTMENT:
#             return f"""
#             {base_prompt}
#             Required fields:
#             - appointment_identifier: Any reference to existing appointment (date, id, etc.)

#             Fields that might be changed (extract only if mentioned):
#             - new_date: New requested date
#             - new_time: New requested time
#             - reason_for_change: Reason for modification
#             - special_requirements: Any new special requirements
#             """

#         elif intent == Intent.CANCEL_APPOINTMENT:
#             return f"""
#             {base_prompt}
#             Required fields:
#             - appointment_identifier: Any reference to identify the appointment

#             Optional fields:
#             - reason_for_cancellation: Reason for canceling
#             - reschedule_needed: Whether they want to reschedule (true/false)
#             - preferred_reschedule_date: If reschedule mentioned, preferred new date
#             """

#         elif intent == Intent.CHECK_AVAILABILITY:
#             return f"""
#             {base_prompt}
#             Required fields:
#             - procedure_type: Type of procedure or consultation they're asking about

#             Optional fields:
#             - preferred_dates: Any specific dates mentioned
#             - doctor_preference: If any specific doctor is mentioned
#             - urgency_level: Any indication of urgency in the request
#             """

#         elif intent == Intent.GET_INFO:
#             return f"""
#             {base_prompt}
#             Required fields:
#             - info_type: What kind of information they're requesting (procedures, doctors, location, hours, etc.)

#             Optional fields:
#             - specific_procedure: If asking about a specific procedure
#             - specific_doctor: If asking about a specific doctor
#             - insurance_question: Any insurance-related queries
#             - pricing_question: Any cost-related queries
#             """

#         elif intent == Intent.HELP:
#             return f"""
#             {base_prompt}
#             Required fields:
#             - help_category: Main category of help needed (appointments, procedures, navigation, etc.)

#             Optional fields:
#             - specific_issue: Specific problem or confusion mentioned
#             - current_step: What they're trying to do
#             - error_message: Any error or issue they're encountering
#             - attempted_actions: What they've already tried
#             """

#         elif intent in [Intent.GREETING, Intent.FAREWELL, Intent.THANK]:
#             return f"""
#             {base_prompt}
#             Fields:
#             - time_of_day: If specific time of day is mentioned (morning/afternoon/evening)
#             - user_name: If user introduces themselves
#             - previous_interaction: Any reference to previous conversations
#             - emotional_tone: Overall tone of the message
#             - additional_context: Any other relevant context provided
#             """

#         elif intent == Intent.CONFIRM or intent == Intent.DENY:
#             return f"""
#             {base_prompt}
#             Fields:
#             - response_to: What they are confirming/denying (if clear from context)
#             - additional_info: Any additional information provided
#             - next_steps_requested: Any questions about what happens next
#             - clarification_needed: Any points they need clarified
#             """

#         else:  # UNKNOWN or any other intent
#             return f"""
#             {base_prompt}
#             Fields:
#             - main_topic: Main subject of the message
#             - user_request: What the user seems to be asking for
#             - time_sensitive: Whether this appears to be time-sensitive (true/false)
#             - user_info: Any user information provided
#             - action_needed: Any specific action they're requesting
#             - emotional_tone: Overall tone of the message
#             """
