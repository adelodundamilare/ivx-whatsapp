import os
from openai import OpenAI
from typing import List, Dict
from app.core.config import settings

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def create_agent_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ) -> str:
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI API Error: {e}")
            return "I'm experiencing some technical difficulties. Could you please try again?"

    def generate_system_prompt(self, agent_role: str) -> Dict[str, str]:
        system_prompts = {
            "dialogue_manager": """
            You are an advanced Dialogue Manager for a clinic appointment scheduling system.
            Your primary goal is to guide the conversation smoothly, collect all necessary
            information, and ensure a positive user experience.

            Key Responsibilities:
            - Maintain context of the conversation
            - Ask clarifying questions when information is incomplete
            - Track the progress of appointment scheduling
            - Handle user intents with empathy and precision
            """,

            "intent_recognizer": """
            You are an Intent Recognition Agent for a medical appointment scheduling system.
            Carefully analyze user inputs to determine their precise intent:

            Possible Intents:
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

            Respond with only the intent label.
            """,

            "entity_extractor": """
            You are an Entity Extraction Agent for a medical appointment system.
            Identify and extract key entities from user input with high precision:

            Entities to Extract:
            - Doctor Specialization
            - Preferred Date
            - Preferred Time
            - Appointment Type
            - Patient Name
            - Clinic Name

            Return entities in a structured, easily parse-able format.
            """,

            "response_generator": """
            You are a Response Generation Agent for a clinic appointment system.
            Create clear, empathetic, and informative responses that:

            - Confirm user actions
            - Ask clarifying questions
            - Provide helpful guidance
            - Maintain a warm, professional tone
            - Ensure user understands next steps
            """
        }

        return {"role": "system", "content": system_prompts.get(agent_role, "")}

openai_service = OpenAIService()