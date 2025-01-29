
from typing import Dict

from fastapi import HTTPException
from app.models import whatsapp as whatsapp_model
from app.core.config import settings
import httpx


class WhatsAppRepository:
    def __init__(self):
        self.whatsapp_token = settings.WHATSAPP_TOKEN
        self.bubble_api_key = settings.BUBBLE_API_KEY
        self.bubble_api_url = settings.BUBBLE_API_URL
        self.user_states: Dict[str, whatsapp_model.ConversationState] = {}
        self.appointments: Dict[str, whatsapp_model.AppointmentCreate] = {}

    async def send_whatsapp_message(self, to_number: str, message: str):
        """Send message using WhatsApp Business API"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.whatsapp_token}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "text",
                "text": {"body": message}
            }
            response = await client.post(
                "https://graph.facebook.com/v17.0/FROM_PHONE_NUMBER_ID/messages",
                headers=headers,
                json=payload
            )
            # print(response, 'response')
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to send WhatsApp message")

    async def update_bubble_record(self, appointment: whatsapp_model.AppointmentCreate) -> str:
        """Create or update appointment in Bubble.io"""
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {self.bubble_api_key}",
                "Content-Type": "application/json"
            }
            payload = appointment.dict()
            response = await client.post(
                f"{self.bubble_api_url}/api/1.1/obj/appointment",
                headers=headers,
                json=payload
            )
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to update Bubble.io record")
            return response.json()["id"]

# Initialize
whatsapp_repository = WhatsAppRepository()

async def get_whatsapp_repository() -> WhatsAppRepository:
    return whatsapp_repository