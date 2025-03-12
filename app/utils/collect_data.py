from typing import Any, Dict, List, Optional
from app.agents import agents
from app.utils.state_manager import StateManager

class DataCollector:
    def __init__(self, clinic_phone: str, user_input: str):
        self.state_manager = StateManager()
        self.clinic_phone = clinic_phone
        self.user_input = user_input

    async def extract_entity(self, entity_key: str) -> Optional[str]:
        """Extract a single entity from user input"""
        extracted_data = await agents.extractor([entity_key], self.user_input)
        cleaned_data = self._clean_data(extracted_data)
        return cleaned_data.get(entity_key)

    async def extract_entities(self, requested_keys: List[str]) -> Dict[str, Any]:
        """Extract multiple entities from user input"""
        if not requested_keys:
            return {}

        extracted_data = await agents.extractor(requested_keys, self.user_input)
        cleaned_data = self._clean_data(extracted_data)
        return cleaned_data

    def _clean_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove invalid values from extracted data"""
        return {
            k: v for k, v in data.items()
            if self._is_valid_value(v)
        }

    def _is_valid_value(self, value: Any) -> bool:
        """Check if a value is valid"""
        if value is None or value == 'Not provided':
            return False
        if isinstance(value, str) and not value.strip():
            return False
        return True

    def update_state(self, data: Dict[str, Any]) -> None:
        if data:
            self.state_manager.update_state(self.clinic_phone, data)

    def get_missing_fields(self, required_fields: List[str], current_data: Dict[str, Any]) -> List[str]:
        """Get list of missing required fields"""
        return [field for field in required_fields if field not in current_data or not self._is_valid_value(current_data.get(field))]