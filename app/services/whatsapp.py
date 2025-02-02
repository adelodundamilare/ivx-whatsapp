
from typing import Dict

from fastapi import HTTPException
from app.models import whatsapp as whatsapp_model
from app.core.config import settings
from app.models.appointment import AppointmentCreate
import httpx


async def send_message(business_phone_number_id: str, from_number: str, messages: str) -> bool:
    message_text = messages.get("text", {}).get("body")

    async with httpx.AsyncClient() as client:
        reply_response = await client.post(
            f"https://graph.facebook.com/v18.0/{business_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.GRAPH_API_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": from_number,
                "text": {"body": f"Echo: {message_text}"},
                # "context": {"message_id": messages.get("id")},  # Reply to the original message
            },
        )
        if reply_response.status_code != 200:
            logger.error(f"Failed to send reply: {reply_response.text}")

        mark_read_response = await client.post(
            f"https://graph.facebook.com/v18.0/{business_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.GRAPH_API_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": messages.get("id"),
            },
        )
        if mark_read_response.status_code != 200:
            logger.error(f"Failed to mark message as read: {mark_read_response.text}")
