from datetime import datetime
from typing import Dict, Optional
from app.models.models import ConversationState, Intent

class StateManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.conversation_state: Dict[str, ConversationState] = {}
        self.business_phone_number: Optional[str] = None
        self.appointment_data = {"current_step": ""}
        self.user_phone_number: str = ""

    def get_state(self, phone_number: str) -> ConversationState:
        if phone_number not in self.conversation_state:
            self.conversation_state[phone_number] = ConversationState()
        return self.conversation_state[phone_number]

    def update_state(self, phone_number: str, **updates):
        state = self.get_state(phone_number)
        # print(updates, state, "save state data ............")
        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                setattr(state, key, value)
        self.conversation_state[phone_number] = state
        return state

    def clear_state(self, phone_number: str):
        if phone_number in self.conversation_state:
            del self.conversation_state[phone_number]

    def get_current_intent(self, phone_number: str) -> Intent:
        state = self.get_state(phone_number)
        return state.current_intent

    def set_current_intent(self, phone_number: str, intent: Intent):
        state = self.get_state(phone_number)
        state.current_intent = intent

    def set_user_phone_number(self, phone_number: str):
        self.user_phone_number = phone_number

    def get_current_step(self) -> str:
        return self.appointment_data["current_step"]

    def set_current_step(self, val: str):
        self.appointment_data["current_step"] = val

    def is_current_step(self, val: str) -> bool:
        return self.get_current_step() == val