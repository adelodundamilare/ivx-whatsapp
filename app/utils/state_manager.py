from datetime import datetime
from typing import Dict, Optional
from app.models.models import ConversationState, Intent

class StateManager:
    def __init__(self):
        self.conversation_state: Dict[str, ConversationState] = {}
        self.business_phone_number: Optional[str] = None
        self.conversations: Dict[str, ConversationState] = {
            'phone_number': '',
            'current_intent': Intent.UNKNOWN,
            'collected_data': {},
            'missing_fields': [],
            'last_interaction': datetime.now(),
            'confirmation_pending': False,
            'modification_pending':  False,
            'context': {},
            'interaction_count': 0,
            'last_error': None,
        }
        self.appointment_data = {
            "current_step": ""
        }
        self.user_phone_number = ''

    # def set_conversation_state(self, value: ConversationState):
    #     self.conversation_state = value

    # def get_conversation_state(self):
    #     return self.conversation_state

    def get_state(self, phone_number: str) -> bool:
        if phone_number in self.conversation_state:
            return self.conversation_state[phone_number]
        return False

    def get_is_processing(self, phone_number: str) -> bool:
        if phone_number in self.conversation_state:
            return self.conversation_state[phone_number].is_processing
        return False

    def set_is_processing(self, phone_number: str, value: bool):
        if phone_number in self.conversation_state:
            self.conversation_state[phone_number].is_processing = value

    def set_user_phone_number(self, phone_number: str):
        self.user_phone_number = phone_number

    def get_user_phone_number(self) -> str:
        return self.user_phone_number

# Create a single instance
state_manager = StateManager()
# def get_state_manager():
#     return state_manager


def get_current_step() -> str:
    return state_manager.appointment_data['current_step']

def set_current_step(val:str) -> str:
    state_manager.appointment_data['current_step'] = val

def is_current_step(val: str) -> bool:
    return val == get_current_step()
