from datetime import datetime, timedelta
from app.core.config import settings
from app.models.models import Message
from app.utils.state_manager import StateManager
import httpx # type: ignore
from app.utils.logger import setup_logger
from typing import Dict, List, Optional, Union, Tuple
import calendar

logger = setup_logger("whatsapp_api", "whatsapp.log")

class WhatsAppDatePicker:
    def __init__(self, whatsapp_api):
        self.whatsapp_api = whatsapp_api
        self.month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

    async def send_month_view(
        self,
        year: int,
        month: int,
        available_dates: List[datetime] = None,
        to_number: Optional[str] = None,
        header_text: str = "Select Date",
        body_text: Optional[str] = None,
        footer_text: Optional[str] = None
    ) -> Dict:
        """
        Send a calendar view for a specific month with navigation controls
        """
        to_number = to_number or self.whatsapp_api.to_number

        # Get month details
        month_name = self.month_names[month - 1]
        num_days = calendar.monthrange(year, month)[1]
        first_day_weekday = datetime(year, month, 1).weekday()

        # Create month navigation buttons
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        next_month = month + 1 if month < 12 else 1
        next_year = year if month < 12 else year + 1

        buttons = [
            {
                "type": "reply",
                "reply": {
                    "id": f"cal_prev_{prev_year}_{prev_month}",
                    "title": "◀️ Previous"
                }
            },
            {
                "type": "reply",
                "reply": {
                    "id": f"cal_next_{next_year}_{next_month}",
                    "title": "Next ▶️"
                }
            },
            {
                "type": "reply",
                "reply": {
                    "id": f"cal_today",
                    "title": "Today 📅"
                }
            }
        ]

        # Send the navigation buttons first
        await self.whatsapp_api.send_buttons(
            to_number=to_number,
            header_text=f"{month_name} {year}",
            body_text="Navigate to view other months",
            buttons=buttons[:3]  # Max 3 buttons allowed
        )

        # Build calendar grid representation as text
        # Add weekday headers
        weekdays = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        calendar_text = " ".join(weekdays) + "\n"

        # Add empty spaces for days before the 1st of the month
        calendar_text += "   " * first_day_weekday

        # Add calendar days
        available_dates_set = set()
        if available_dates:
            available_dates_set = {(d.year, d.month, d.day) for d in available_dates}

        day_count = 1
        for i in range(first_day_weekday, 7 * 6):  # 6 rows maximum
            if day_count > num_days:
                break

            # Mark available dates
            is_available = (year, month, day_count) in available_dates_set
            day_str = f"{day_count:2d}"

            if is_available:
                day_str = f"*{day_str}*"  # Bold for available dates

            calendar_text += day_str + " "

            # New line at end of week
            if (i + 1) % 7 == 0:
                calendar_text += "\n"

            day_count += 1

        # Send the calendar grid as a text message
        await self.whatsapp_api.send_text_message(
            message=f"📅 *{month_name} {year}*\n\n{calendar_text}\n\n*Bold dates* are available for selection.",
            to_number=to_number
        )

        # Create sections with available dates for this month
        if available_dates:
            this_month_dates = [d for d in available_dates if d.year == year and d.month == month]

            if this_month_dates:
                # Group by week for better organization
                weeks = {}
                for date in this_month_dates:
                    week_num = date.isocalendar()[1]
                    if week_num not in weeks:
                        weeks[week_num] = []
                    weeks[week_num].append(date)

                sections = []
                for week_num, dates in weeks.items():
                    rows = [
                        {
                            "id": f"date_{date.strftime('%Y%m%d')}",
                            "title": date.strftime("%A, %B %d"),  # e.g., "Monday, February 19"
                            "description": f"Select this date"
                        }
                        for date in dates
                    ]

                    sections.append({
                        "title": f"Week of {dates[0].strftime('%B %d')}",
                        "rows": rows
                    })

                # Send available dates as interactive list
                return await self.whatsapp_api.send_interactive_list(
                    to_number=to_number,
                    header_text=header_text or f"Available Dates - {month_name} {year}",
                    body_text=body_text or "Please select your preferred date:",
                    footer_text=footer_text or "* Dates shown are available for booking",
                    button_text="Select Date",
                    sections=sections
                )
            else:
                await self.whatsapp_api.send_text_message(
                    message="No available dates for this month. Please navigate to another month.",
                    to_number=to_number
                )
                return {"status": "no_dates_available"}

        return {"status": "calendar_sent"}

    async def handle_calendar_navigation(self, payload: Dict) -> Tuple[int, int]:
        button_id = payload.get("id", "")

        if button_id.startswith("cal_prev_") or button_id.startswith("cal_next_"):
            # Extract year and month from button ID
            parts = button_id.split("_")
            if len(parts) >= 3:
                year = int(parts[2])
                month = int(parts[3])
                return year, month

        elif button_id == "cal_today":
            today = datetime.now()
            return today.year, today.month

        # Default to current month if something goes wrong
        today = datetime.now()
        return today.year, today.month

    async def send_date_range_selector(
        self,
        start_date: datetime,
        end_date: datetime,
        to_number: Optional[str] = None,
        excluded_dates: List[datetime] = None,
        header_text: str = "Select Date Range",
        body_text: Optional[str] = None
    ) -> Dict:
        """
        Send an interface to select a date range
        Provides options for common ranges and custom selection
        """
        to_number = to_number or self.whatsapp_api.to_number

        # Calculate some common date ranges
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        next_two_weeks = today + timedelta(days=14)
        next_month = today + timedelta(days=30)

        # Create options for common date ranges
        sections = [
            {
                "title": "Common Date Ranges",
                "rows": [
                    {
                        "id": f"range_today",
                        "title": "Today",
                        "description": today.strftime("%A, %B %d")
                    },
                    {
                        "id": f"range_tomorrow",
                        "title": "Tomorrow",
                        "description": tomorrow.strftime("%A, %B %d")
                    },
                    {
                        "id": f"range_week",
                        "title": "Next 7 days",
                        "description": f"From {today.strftime('%b %d')} to {next_week.strftime('%b %d')}"
                    },
                    {
                        "id": f"range_twoweeks",
                        "title": "Next 14 days",
                        "description": f"From {today.strftime('%b %d')} to {next_two_weeks.strftime('%b %d')}"
                    },
                    {
                        "id": f"range_month",
                        "title": "Next 30 days",
                        "description": f"From {today.strftime('%b %d')} to {next_month.strftime('%b %d')}"
                    }
                ]
            },
            {
                "title": "Custom Selection",
                "rows": [
                    {
                        "id": "custom_start",
                        "title": "Select Start Date",
                        "description": "Choose your own date range start"
                    },
                    {
                        "id": "custom_end",
                        "title": "Select End Date",
                        "description": "Choose your own date range end"
                    }
                ]
            }
        ]

        return await self.whatsapp_api.send_interactive_list(
            to_number=to_number,
            header_text=header_text,
            body_text=body_text or "Please select your preferred date range:",
            footer_text="You can choose a common range or make a custom selection",
            button_text="View Options",
            sections=sections
        )


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
        self.base_url = f"https://graph.facebook.com/v18.0/{self.business_phone_number_id}"
        self.headers = {"Authorization": f"Bearer {settings.GRAPH_API_TOKEN}"}
        self.date_picker = WhatsAppDatePicker(self)

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

    async def send_date_picker(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        available_dates: List[datetime] = None,
        to_number: Optional[str] = None,
        header_text: Optional[str] = "",
        body_text: Optional[str] = None
    ) -> Dict:
        """
        Send enhanced date picker with month view
        """
        to_number = to_number or self.to_number

        # Use current month if not specified
        if not year or not month:
            today = datetime.now()
            year = year or today.year
            month = month or today.month

        return await self.date_picker.send_month_view(
            year=year,
            month=month,
            available_dates=available_dates,
            to_number=to_number,
            header_text=header_text,
            body_text=body_text
        )

    async def send_date_range_picker(
        self,
        start_date: datetime,
        end_date: datetime,
        to_number: Optional[str] = None,
        excluded_dates: List[datetime] = None,
        header_text: str = "Select Date Range"
    ) -> Dict:
        """
        Send date range picker
        """
        to_number = to_number or self.to_number

        return await self.date_picker.send_date_range_selector(
            start_date=start_date,
            end_date=end_date,
            to_number=to_number,
            excluded_dates=excluded_dates,
            header_text=header_text
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
            finally:
                if to_number:
                    self.state_manager.update_state(to_number, is_processing=False)

