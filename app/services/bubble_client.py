from datetime import datetime
import httpx # type: ignore
import json
from typing import Any, Dict, Optional
from fastapi import HTTPException
from app.core.config import settings
from app.utils.logger import setup_logger

DEFAULT_TIMEOUT = 30

logger = setup_logger("bubble_api", "bubble_api.log")

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


class BubbleApiClient:
    """Client for interacting with Bubble API"""

    def __init__(self):
        self.api_url = settings.BUBBLE_API_URL
        self.api_key = settings.BUBBLE_API_KEY
        self.headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                           params: Optional[Dict] = None, expected_status_codes: tuple = (200, 201)) -> Any:
        """Make a request to the Bubble API with error handling"""
        url = f"{self.api_url}/{endpoint}"

        try:
            async with httpx.AsyncClient() as client:
                if method.lower() == "get":
                    response = await client.get(
                        url,
                        headers=self.headers,
                        params=params,
                        timeout=DEFAULT_TIMEOUT
                    )
                elif method.lower() == "post":
                    json_data = json.dumps(data, cls=DateTimeEncoder) if data else None
                    response = await client.post(
                        url,
                        headers=self.headers,
                        content=json_data,
                        timeout=DEFAULT_TIMEOUT
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Handle response status
                if response.status_code not in expected_status_codes:
                    error_message = response.text or f"API request failed with status {response.status_code}"
                    logger.error(f"API Error: {error_message} for {method} {url}")

                    if response.status_code == 404:
                        raise HTTPException(status_code=404, detail="Resource not found")
                    else:
                        raise HTTPException(status_code=response.status_code, detail=error_message)

                # Return response data for successful requests
                return response.json() if response.content else True

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)} during {method} request to {url}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

    async def create_appointment(self, data: Dict) -> bool:
        """Create a new appointment"""
        try:
            print('sending data to bubble', data)
            result = await self._make_request("post", "appointments", data=data)
            return result
        except HTTPException as e:
            raise HTTPException(status_code=500, detail=f"Failed to create appointment: {e.detail}")
        except Exception as e:
            logger.error(f"Error in create_appointment: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error creating appointment: {str(e)}")

    async def update_appointment(self, id: str, data: Dict) -> bool:
        try:
            print('sending data to bubble', data)
            result = await self._make_request("PATCH", f"appointments/{id}", data=data)
            return result
        except HTTPException as e:
            raise HTTPException(status_code=500, detail=f"Failed to create appointment: {e.detail}")
        except Exception as e:
            logger.error(f"Error in create_appointment: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error creating appointment: {str(e)}")

    async def create_clinic(self, data: Dict) -> bool:
        """Create a new clinic"""
        return await self._make_request("post", "clinics", data=data)

    async def find_clinic_by_phone(self, phone_number: str) -> Dict:
        """Find a clinic by phone number"""
        constraints = [{
            'key': 'phone_number',
            'constraint_type': 'equals',
            'value': phone_number
        }]

        params = {'constraints': json.dumps(constraints)}
        response_data = await self._make_request("get", "clinics", params=params)

        results = response_data.get("response", {}).get("results", [])
        if not results:
            raise HTTPException(status_code=404, detail="Clinic not found")

        return results[0]

    async def find_appointment_by_code(self, booking_code: str) -> Dict:
        constraints = [{
            'key': 'code',
            'constraint_type': 'equals',
            'value': booking_code
        }]

        params = {'constraints': json.dumps(constraints)}
        response_data = await self._make_request("get", "appointments", params=params)

        results = response_data.get("response", {}).get("results", [])
        if not results:
            raise HTTPException(status_code=404, detail="Appointment not found")

        return results[0]

    async def find_latest_appointments(self, clinic_phone: str) -> Dict:
        constraints = [{
            'key': 'phone_number',
            'constraint_type': 'equals',
            'value': clinic_phone
        }]
        params = {
            'constraints': json.dumps(constraints),
            'limit': 10,
            'order_by': 'created_at',
            'order_direction': 'desc'
        }

        response_data = await self._make_request("get", "appointments", params=params)

        results = response_data.get("response", {}).get("results", [])
        if not results:
            raise HTTPException(status_code=404, detail="Appointment not found")

        return results


bubble_client = BubbleApiClient()