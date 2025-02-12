from typing import Dict
from app.models.models import ConversationState, Message
from typing import Dict
from app.core.config import settings
from openai import OpenAI # type: ignore
# import whisper # type: ignore
import os


client = OpenAI(api_key=settings.OPENAI_API_KEY)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WHATSAPP_API_KEY = os.getenv("WHATSAPP_API_KEY")

# Initialize clients
# audio_model = whisper.load_model("base")

class BaseAgent:
    def __init__(self):
        self.conversation_states: Dict[str, ConversationState] = {}

    async def process(self, message: Message):
        raise NotImplementedError

# Voice Processing Agent
class VoiceAgent(BaseAgent):
    async def process(self, message: Message) -> str:
        # Convert voice note to text using Whisper
        return 'ello'
        result = audio_model.transcribe(message.content)
        return result["text"]


# Dialog Management Agent