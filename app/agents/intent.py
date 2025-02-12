from app.agents.base import BaseAgent
import os
from app.core.config import settings
from app.models.models import Intent
from openai import OpenAI # type: ignore


client = OpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

class IntentAgent(BaseAgent):
    async def process(self, message: str) -> Intent:
        prompt = f"Classify the following message into one of these intents: {', '.join(Intent.__members__.keys())}. Message: {message}"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an intent classification agent. Respond with just the intent."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        return Intent.from_string(response.choices[0].message.content.strip().strip())

    async def get_confirmation_intent(self, message: str) -> Intent:
        try:
            prompt = """
            Is this message a confirmation (yes) or denial (no)? If unclear, respond with 'unknown'.
            Consider common variations like 'sure, thanks', 'okay, thanks', 'nope', 'yes thanks' etc.
            Respond with exactly one word: 'CONFIRM', 'DENY', or 'UNKNOWN'.
            """

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.3
            )

            result = response.choices[0].message.content.strip().upper()
            if result == 'CONFIRM':
                return Intent.CONFIRM
            elif result == 'DENY':
                return Intent.DENY
            else:
                return Intent.UNKNOWN

        except Exception as e:
            # logger.error(f"Error in confirmation intent analysis: {str(e)}")
            return Intent.UNKNOWN