from datetime import datetime
from app.core.config import settings
import httpx # type: ignore
from app.utils.logger import setup_logger
from typing import Dict, List, Optional

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




class WhatsAppBusinessAPI:
    def __init__(self, business_phone_number_id: str):
        self.base_url = f"https://graph.facebook.com/v18.0/{business_phone_number_id}"
        self.headers = {"Authorization": f"Bearer {settings.GRAPH_API_TOKEN}"}

    async def send_text_message(self, to_number: str, message: str, reply_to_message_id: Optional[str] = None) -> Dict:
        """Send a simple text message"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "text": {"body": message}
        }

        # if reply_to_message_id:
        #     payload["context"] = {"message_id": reply_to_message_id}

        return await self._make_request("/messages", payload)

    async def send_template_message(
        self,
        to_number: str,
        template_name: str,
        language_code: str,
        components: List[Dict]
    ) -> Dict:
        """Send a template message"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                },
                "components": components
            }
        }

        return await self._make_request("/messages", payload)

    async def send_interactive_list(
        self,
        to_number: str,
        header_text: str,
        body_text: str,
        footer_text: str,
        button_text: str,
        sections: List[Dict]
    ) -> Dict:
        """Send an interactive list message"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {
                    "type": "text",
                    "text": header_text
                },
                "body": {
                    "text": body_text
                },
                "footer": {
                    "text": footer_text
                },
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }

        return await self._make_request("/messages", payload)

    async def send_location(
        self,
        to_number: str,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None
    ) -> Dict:
        """Send a location message"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "location",
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": name,
                "address": address
            }
        }

        return await self._make_request("/messages", payload)

    async def send_reaction(
        self,
        to_number: str,
        message_id: str,
        emoji: str
    ) -> Dict:
        """Send a reaction to a message"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "reaction",
            "reaction": {
                "message_id": message_id,
                "emoji": emoji
            }
        }

        return await self._make_request("/messages", payload)

    async def send_contact(
        self,
        to_number: str,
        contacts: List[Dict]
    ) -> Dict:
        """Send contact information"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "contacts",
            "contacts": contacts
        }

        return await self._make_request("/messages", payload)

    async def send_buttons(
        self,
        to_number: str,
        header_text: Optional[str],
        body_text: str,
        footer_text: Optional[str],
        buttons: List[Dict]
    ) -> Dict:
        """Send a message with buttons"""
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body_text
                },
                "action": {
                    "buttons": buttons
                }
            }
        }

        if header_text:
            payload["interactive"]["header"] = {"type": "text", "text": header_text}
        if footer_text:
            payload["interactive"]["footer"] = {"text": footer_text}

        return await self._make_request("/messages", payload)

    async def send_calendar_selection(
        self,
        to_number: str,
        start_date: datetime,
        available_dates: List[datetime],
        header_text: str = "Select Date",
        body_text: Optional[str] = None
    ) -> Dict:
        """
        Send a calendar-like date selection using list message
        Since WhatsApp doesn't have a native calendar, we create a scrollable list of dates
        """
        # Group dates by week
        weeks = []
        current_week = []

        for date in available_dates:
            if len(current_week) < 7:
                current_week.append(date)
            else:
                weeks.append(current_week)
                current_week = [date]

        if current_week:
            weeks.append(current_week)

        # Create sections for each week
        sections = []
        for i, week in enumerate(weeks):
            rows = [
                {
                    "id": f"date_{date.strftime('%Y%m%d')}",
                    "title": date.strftime("%A, %B %d"),  # e.g., "Monday, February 19"
                    "description": f"Select this date to book your appointment"
                }
                for date in week
            ]

            sections.append({
                "title": f"Week {i + 1}",
                "rows": rows
            })

        return await self.send_interactive_list(
            to_number=to_number,
            header_text=header_text,
            body_text=body_text or "Please select your preferred date:",
            footer_text="Scroll to see more dates",
            button_text="View Dates",
            sections=sections
        )

    async def send_time_slots(
        self,
        to_number: str,
        selected_date: datetime,
        available_slots: List[str]
    ) -> Dict:
        """
        Send available time slots for a selected date using buttons
        """
        # Create buttons for time slots (max 3 at a time)
        buttons = [
            {
                "type": "reply",
                "reply": {
                    "id": f"time_{slot.replace(':', '')}",
                    "title": slot
                }
            }
            for slot in available_slots[:3]  # WhatsApp limits to 3 buttons
        ]

        return await self.send_buttons(
            to_number=to_number,
            header_text=f"Available Times - {selected_date.strftime('%B %d, %Y')}",
            body_text="Please select your preferred time:",
            footer_text="Choose a time slot",
            buttons=buttons
        )

    async def mark_message_as_read(self, message_id: str) -> Dict:
        """Mark a message as read"""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }

        return await self._make_request("/messages", payload)

    async def _make_request(self, endpoint: str, payload: Dict) -> Dict:
        """Make HTTP request to WhatsApp API"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}{endpoint}",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                if response.status_code != 200:
                    logger.error(f"API request failed: {response.text}")
                    return {"error": response.text, "status_code": response.status_code}

                return response.json()
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                return {"error": str(e)}

# # Example usage
# async def main():
#     api = WhatsAppBusinessAPI(
#         business_phone_number_id=settings.BUSINESS_PHONE_NUMBER_ID,
#         api_token=settings.GRAPH_API_TOKEN
#     )

#     # Example: Send template message
#     template_components = [
#         {
#             "type": "body",
#             "parameters": [
#                 {
#                     "type": "text",
#                     "text": "John Doe"
#                 }
#             ]
#         }
#     ]

#     await api.send_template_message(
#         to_number="RECIPIENT_NUMBER",
#         template_name="hello_world",
#         language_code="en",
#         components=template_components
#     )

#     # Example: Send interactive list
#     sections = [
#         {
#             "title": "Products",
#             "rows": [
#                 {
#                     "id": "PRODUCT_1",
#                     "title": "Product 1",
#                     "description": "Description 1"
#                 },
#                 {
#                     "id": "PRODUCT_2",
#                     "title": "Product 2",
#                     "description": "Description 2"
#                 }
#             ]
#         }
#     ]

#     await api.send_interactive_list(
#         to_number="RECIPIENT_NUMBER",
#         header_text="Our Products",
#         body_text="Please select a product",
#         footer_text="Thank you for shopping with us",
#         button_text="View Products",
#         sections=sections
#     )

#     # Example: Send buttons
#     buttons = [
#         {
#             "type": "reply",
#             "reply": {
#                 "id": "BUTTON_1",
#                 "title": "Yes"
#             }
#         },
#         {
#             "type": "reply",
#             "reply": {
#                 "id": "BUTTON_2",
#                 "title": "No"
#             }
#         }
#     ]

#     await api.send_buttons(
#         to_number="RECIPIENT_NUMBER",
#         header_text="Confirmation",
#         body_text="Would you like to proceed?",
#         footer_text="Choose an option",
#         buttons=buttons
#     )


# # Example usage
# async def handle_appointment_booking():
#     api = WhatsAppBusinessAPI(
#         business_phone_number_id=settings.BUSINESS_PHONE_NUMBER_ID,
#         api_token=settings.GRAPH_API_TOKEN
#     )

#     # Generate available dates (next 14 days)
#     today = datetime.now()
#     available_dates = [
#         today + timedelta(days=x)
#         for x in range(14)
#         if (today + timedelta(days=x)).weekday() < 5  # Exclude weekends
#     ]

#     # Send calendar selection
#     await api.send_calendar_selection(
#         to_number="RECIPIENT_NUMBER",
#         start_date=today,
#         available_dates=available_dates,
#         header_text="Book Appointment",
#         body_text="Please select your preferred date:"
#     )

#     # Example time slots (would be sent after date selection)
#     time_slots = ["09:00", "10:00", "11:00"]
#     await api.send_time_slots(
#         to_number="RECIPIENT_NUMBER",
#         selected_date=available_dates[0],
#         available_slots=time_slots
#     )