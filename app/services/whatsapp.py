from app.core.config import settings
import httpx
from app.utils.logger import setup_logger

logger = setup_logger("whatsapp_api", "whatsapp.log")

async def send_message(business_phone_number_id: str, from_number: str, message_text: str, message_id: str) -> bool:

    async with httpx.AsyncClient() as client:
        reply_response = await client.post(
            f"https://graph.facebook.com/v18.0/{business_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.GRAPH_API_TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": from_number,
                "text": {"body": message_text},
                # "context": {"message_id": message_id},  # Reply to the original message
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
                "message_id": message_id,
            },
        )
        if mark_read_response.status_code != 200:
            logger.error(f"Failed to mark message as read: {mark_read_response.text}")
