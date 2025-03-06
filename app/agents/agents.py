import asyncio
import json
from typing import Dict
import os
from app.core.config import settings
from app.models.models import Language
from app.utils.logger import setup_logger
from openai import OpenAI # type: ignore


logger = setup_logger("agent", "agent.log")
client = OpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def extractor(requested_keys, message: str) -> Dict:
    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            prompt = f"Extract the following keys: {requested_keys} from this text: '{message}' and return them in JSON format. If a value is missing, set it to None."

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a smart key-value pair extractor. Always return a JSON object with the requested keys."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )

            content = response.choices[0].message.content

            if not content:
                print("Content is empty")
                return {}

            if isinstance(content, dict):
                return content

            if isinstance(content, str):
                content = content.strip()

            try:
                return json.loads(content)
            except json.JSONDecodeError:
                try:
                    content = content.replace("'", '"')
                    return json.loads(content)
                except json.JSONDecodeError:
                    print(f"Failed to parse message {message} with type: {type(content)} as JSON")
                    raise  # Re-raise to trigger retry

        except Exception as e:
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                print(f"Attempt {attempt + 1} failed. Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Double the delay for next retry
            else:
                print(f"All {max_retries} attempts failed. Final error: {str(e)}")
                return {}

    return {}

async def create_appointment_dialog_agent(message, conversation_history, appointment_details) -> Dict:
    dialogue_template = f"""
You are an assistant for managing medical appointment scheduling conversations.
Your goal is to guide the conversation to collect all necessary information for booking an appointment.

Required appointment information:
- Procedure type
- Date
- Time
- Clinic name
- Doctor specialty

Current conversation state:
{conversation_history}

Current appointment details collected:
{appointment_details}

What should be the next question or response to move the conversation forward?
Respond with a clear next step that maintains a natural conversation flow.

If switching from English to Spanish or vice versa, maintain consistent tone and information collection.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": dialogue_template},
                {"role": "user", "content": message}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content

        return content

    except Exception as e:
        print(f"{str(e)}")

async def intent_agent(message: str) -> Dict:
    template = f"""
Identify the primary intent of the user's message.
Possible intents:
- schedule_appointment: User wants to book a new appointment
- cancel_appointment: User wants to cancel an existing appointment
- reschedule_appointment: User wants to change an existing appointment
- inquire_doctors: User is asking about available doctors
- inquire_services: User is asking about available medical services
- provide_information: User is providing information for their appointment
- confirm: User is confirming something
- deny: User is declining something
- greeting: User is greeting the system
- farewell: User is ending the conversation
- help: User needs assistance with using the system
- other: None of the above

User message: {message}

Respond with only the intent label.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an intent classification agent. Respond with just the intent."},
                {"role": "user", "content": template}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content

        return content

    except Exception as e:
        print(f"{str(e)}")

async def response_agent(message, conversation_history, appointment_details, user_intent, language: str = 'en', ) -> str:
    template = f"""
You are a warm and professional medical assistant that helps clinics schedule, reschedule, and edit doctor appointments. Keep responses clear, concise, and friendly while ensuring accuracy in appointment details. If needed, ask relevant follow-up questions to confirm details before proceeding.

Language preference: {language}

Task: Generate a natural, conversational response based on the conversation history, current appointment details, and user intent.

Conversation history:
{conversation_history}

Current appointment details:
{appointment_details}

User intent: {user_intent}

**Response guidelines:**
1. Acknowledge the user's input in a friendly and helpful tone.
2. If appointment details are missing, ask the user for clarification in a natural way.
3. Ensure the response flows well within the context of the conversation.
4. The response must be generated in {language} (English or Spanish).
5. Be concise, clear, and professional.
6. If the user's name appears in the conversation history, personalize the response by addressing them by name.

**Your response:**
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": template},
                {"role": "user", "content": message}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content

        return content

    except Exception as e:
        print(f"{str(e)}")

async def translate_agent(text: str, source_language: Language, target_language: Language) -> str:
    """Translate text between English and Spanish"""
    if source_language == target_language:
        return text

    template = f"""
    Translate the following text from {source_language.value} to {target_language.value}:

    {text}

    Provide only the translated text without any additional explanations.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                # {"role": "system", "content": "You are a smart key-value pair extractor. Always return a JSON object with the requested keys."},
                {"role": "user", "content": template}
            ],
            temperature=0.3
        )

        content = response.choices[0].message.content

        return content

    except Exception as e:
        print(f"{str(e)}")


async def generate_generic_response(message: str, conversation_history: list) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a warm and professional medical assistant that helps clinics schedule, reschedule, edit and manage doctor appointments. "
                               f"Keep responses clear, concise, and friendly while ensuring accuracy in appointment details. "
                               f"Use the conversation history to maintain context and provide relevant responses. "
                               f"If needed, ask relevant follow-up questions to confirm appointment details before proceeding. "
                               "ensure users confirm inputs before proceeding."
                               f"Conversation History: {conversation_history}"
                },
                {"role": "user", "content": message}
            ],
            temperature=0.7
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"An error occurred: {e}")
        return "Sorry, there was an error processing your request."