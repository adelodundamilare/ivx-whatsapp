from datetime import datetime, timedelta
from app.core.config import settings
from app.models.models import Message
from app.utils.state_manager import StateManager
import httpx # type: ignore
from app.utils.logger import setup_logger
from typing import Dict, List, Optional, Union, Tuple
import calendar

logger = setup_logger("whatsapp_api", "whatsapp.log")

class WhatsAppBusinessAPI:
    def __init__(self, message: Optional[Message] = None, business_phone_number_id: Optional[str] = None):
        # Allow initializing with either a Message object or a business_phone_number_id
        if message:
            self.message = message
            self.business_phone_number_id = message.business_phone_number_id
            self.to_number = message.phone_number
        elif business_phone_number_id:
            self.message = None
            self.business_phone_number_id = business_phone_number_id
            self.to_number = None
        else:
            raise ValueError("Either message or business_phone_number_id must be provided")

        self.state_manager = StateManager()
        self.state = self.state_manager.get_state(message.phone_number)
        self.base_url = f"https://graph.facebook.com/v18.0/{self.business_phone_number_id}"
        self.headers = {"Authorization": f"Bearer {settings.GRAPH_API_TOKEN}"}

    async def send_text_message(self, message: str, to_number: Optional[str] = None, reply_to_message_id: Optional[str] = None) -> Dict:
        """Send a simple text message"""
        to_number = to_number or self.to_number
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "text": {"body": message}
        }

        if reply_to_message_id:
            payload["context"] = {"message_id": reply_to_message_id}

        return await self._make_request("/messages", payload)

    async def send_template_message(
        self,
        template_name: str,
        language_code: str,
        components: List[Dict],
        to_number: Optional[str] = None
    ) -> Dict:
        """Send a template message"""
        to_number = to_number or self.to_number
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
        button_text: str,
        body_text: str,
        header_text: str,
        sections: List[Dict],
        footer_text: Optional[str] = None,
        to_number: Optional[str] = None,
    ) -> Dict:
        to_number = to_number or self.to_number

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
                "action": {
                    "button": button_text,
                    "sections": sections
                }
            }
        }

        if footer_text:
            payload["interactive"]["footer"] = {"text": footer_text}

        return await self._make_request("/messages", payload)

    async def send_location(
        self,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
        to_number: Optional[str] = None
    ) -> Dict:
        """Send a location message"""
        to_number = to_number or self.to_number
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "location",
            "location": {
                "latitude": latitude,
                "longitude": longitude
            }
        }

        if name:
            payload["location"]["name"] = name
        if address:
            payload["location"]["address"] = address

        return await self._make_request("/messages", payload)

    async def send_reaction(
        self,
        message_id: str,
        emoji: str,
        to_number: Optional[str] = None
    ) -> Dict:
        """Send a reaction to a message"""
        to_number = to_number or self.to_number
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
        contacts: List[Dict],
        to_number: Optional[str] = None
    ) -> Dict:
        """Send contact information"""
        to_number = to_number or self.to_number
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "contacts",
            "contacts": contacts
        }

        return await self._make_request("/messages", payload)

    async def send_buttons(
        self,
        buttons: List[Dict],
        body_text: str,
        to_number: Optional[str] = None,
        header_text: Optional[str] = None,
        footer_text: Optional[str] = None,
    ) -> Dict:
        """Send a message with buttons"""
        to_number = to_number or self.to_number
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body_text
                },
                # "header": {
                #     "type": "text",
                #     "text": "ooo"
                # },
                "action": {
                    "buttons": buttons
                }
            }
        }

        # if header_text:
        #     payload["interactive"]["header"] = {"type": "text", "text": header_text}
        if footer_text:
            payload["interactive"]["footer"] = {"text": footer_text}

        return await self._make_request("/messages", payload)

    async def send_calendar_selection(
        self,
        start_date: datetime,
        available_dates: List[datetime],
        to_number: Optional[str]=None,
        header_text: str = "Select Date",
        body_text: Optional[str] = None
    ) -> Dict:
        """Send calendar selection interface (original implementation)"""
        to_number = to_number or self.to_number
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
                    "id": f"{date.strftime('%Y%m%d')}",
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
        available_slots: List[str],
        to_number: Optional[str]=None,
    ) -> Dict:
        to_number = to_number or self.to_number

        if len(available_slots) <= 3:
            buttons = [
                {
                    "type": "reply",
                    "reply": {
                        "id": f"{slot.replace(':', '')}",
                        "title": slot
                    }
                }
                for slot in available_slots
            ]

            return await self.send_buttons(
                to_number=to_number,
                header_text=f"Available Times",
                body_text="Please select your preferred time:",
                footer_text="Choose a time slot",
                buttons=buttons
            )
        else:
            morning_slots = [s for s in available_slots if int(s.split(':')[0]) < 12]
            afternoon_slots = [s for s in available_slots if 12 <= int(s.split(':')[0]) < 17]
            evening_slots = [s for s in available_slots if int(s.split(':')[0]) >= 17]

            sections = []

            if morning_slots:
                sections.append({
                    "title": "Morning",
                    "rows": [
                        {
                            "id": f"{slot.replace(':', '')}",
                            "title": slot,
                            "description": "Morning appointment"
                        }
                        for slot in morning_slots
                    ]
                })

            if afternoon_slots:
                sections.append({
                    "title": "Afternoon",
                    "rows": [
                        {
                            "id": f"{slot.replace(':', '')}",
                            "title": slot,
                            "description": "Afternoon appointment"
                        }
                        for slot in afternoon_slots
                    ]
                })

            if evening_slots:
                sections.append({
                    "title": "Evening",
                    "rows": [
                        {
                            "id": f"{slot.replace(':', '')}",
                            "title": slot,
                            "description": "Evening appointment"
                        }
                        for slot in evening_slots
                    ]
                })

            return await self.send_interactive_list(
                to_number=to_number,
                header_text="",
                body_text="Please select your preferred time:",
                footer_text="Choose from available time slots",
                button_text="View Times",
                sections=sections
            )

    async def request_location_selection(
        self,
        to_number: Optional[str] = None
    ) -> Dict:
        to_number = to_number or self.to_number

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "interactive",
            "interactive": {
                "type": "location_request_message",
                "body": {
                    "text": "Please select your preferred location; you can either manually *enter an address* or *share your preferred current location*."
                },
                "action": {
                    "name": "send_location"
                }
            }
        }

        # Make the request to send the interactive message
        response = await self._make_request("/messages", payload)
        return response

    async def handle_location_selection_response(self, webhook_data: Dict) -> None:
        if (
            webhook_data.get("entry")
            and webhook_data["entry"][0].get("changes")
            and webhook_data["entry"][0]["changes"][0].get("value")
            and webhook_data["entry"][0]["changes"][0]["value"].get("messages")
        ):
            messages = webhook_data["entry"][0]["changes"][0]["value"]["messages"]

            for message in messages:
                if (
                    message.get("type") == "interactive"
                    and message.get("interactive", {}).get("button_reply", {}).get("id") == "select_location"
                ):
                    from_number = message.get("from")

                    instruction_payload = {
                        "messaging_product": "whatsapp",
                        "to": from_number,
                        "type": "text",
                        "text": {
                            "body": "Great! To share a location, please:\n\n1. Tap the attachment (📎) icon\n2. Select 'Location'\n3. Choose 'Send your current location' OR 'Send a different location' to select any place on the map"
                        }
                    }

                    await self._make_request("/messages", instruction_payload)

                # Handle the actual location message when received
                elif message.get("type") == "location":
                    # Process the location data
                    location_data = message.get("location", {})
                    latitude = location_data.get("latitude")
                    longitude = location_data.get("longitude")
                    name = location_data.get("name")
                    address = location_data.get("address")

                    # You can now do something with this location data
                    # For example, store it in a database or process it further

                    # Optionally send a confirmation message
                    from_number = message.get("from")

                    confirmation_message = f"Thank you for sharing your selected location!"
                    if name or address:
                        location_details = []
                        if name:
                            location_details.append(name)
                        if address:
                            location_details.append(address)
                        confirmation_message += f"\n\nLocation: {', '.join(location_details)}"
                    else:
                        confirmation_message += f"\n\nCoordinates: {latitude}, {longitude}"

                    confirmation_payload = {
                        "messaging_product": "whatsapp",
                        "to": from_number,
                        "type": "text",
                        "text": {
                            "body": confirmation_message
                        }
                    }

                    await self._make_request("/messages", confirmation_payload)

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
        to_number = payload.get("to")
        if to_number != '2348099868604':
            payload["text"]['body'] = 'We are actively developing, please check back'

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

                # self._update_conversation_state(payload)

                return response.json()
            except Exception as e:
                logger.error(f"Request failed: {str(e)}")
                return {"error": str(e)}
            finally:
                if to_number:
                    self.state_manager.update_state(to_number, is_processing=False)

    def _update_conversation_state(self, payload):
            phone_number = payload.get('to')
            conversation_history = self.state.conversation_history or []

            conversation_entry = {
                'user': self.message.content,
                'aia': payload.get('text', {}).get('body', ''),
                'timestamp': datetime.now().isoformat()
            }
            conversation_history.append(conversation_entry)
            conversation_history = conversation_history[-30:]  # Keep last 30 entries
            self.state_manager.update_state(phone_number, conversation_history=conversation_history)

