from datetime import datetime
import json
import os
from typing import Any, Dict, Optional
from app.models.models import AppointmentState, Intent

# class StateManager:
#     _instance = None

#     def __new__(cls):
#         if cls._instance is None:
#             cls._instance = super(StateManager, cls).__new__(cls)
#             cls._instance._initialize()
#         return cls._instance

#     def _initialize(self):
#         self.conversation_state: Dict[str, AppointmentState] = {}
#         self.business_phone_number: Optional[str] = None
#         self.user_phone_number: str = ""

#     def get_state(self, phone_number: str) -> AppointmentState:
#         if phone_number not in self.conversation_state:
#             self.conversation_state[phone_number] = AppointmentState()
#         return self.conversation_state[phone_number]

#     def update_state(self, phone_number: str, **updates):
#         state = self.get_state(phone_number)
#         # print(updates, state, "save state data ............")
#         for key, value in updates.items():
#             if hasattr(state, key):
#                 setattr(state, key, value)
#             else:
#                 setattr(state, key, value)
#         self.conversation_state[phone_number] = state
#         return state

#     def add_to_history(self, phone_number: str, role: str, content: str):
#         state = self.get_state(phone_number)
#         history = self.conversation_state[phone_number]["history"] or []
#         history.append({"role": role, "content": content})
#         self.conversation_state[phone_number]["history"] = history
#         return state

#     def clear_state(self, phone_number: str):
#         if phone_number in self.conversation_state:
#             del self.conversation_state[phone_number]
class StateManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    # def __init__(self, storage_file: str = "user_states.json"):
    #     self.storage_file = storage_file
    #     self.states: Dict[str, Dict[str, Any]] = self._load_states()

    def _initialize(self, storage_file: str = "user_states.json"):
        self.storage_file = storage_file
        self.states: Dict[str, Dict[str, Any]] = self._load_states()


    def _load_states(self) -> Dict[str, Dict[str, Any]]:
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, "r") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading states: {e}")
            return {}

    def _save_states(self):
        try:
            with open(self.storage_file, "w") as f:
                json.dump(self.states, f)
        except Exception as e:
            print(f"Error saving states: {e}")

    def get_state(self, clinic_phone: str) -> Dict[str, Any]:
        return self.states.get(clinic_phone, {
            "full_name": "",
            "clinic_name": "",
            "appointment": {
                "patient_gender": "",
                "service_type": "",
                "date": "",
                "time": "",
            },
            "doctor_index": 0,
            "history": [],
            "needs_clarification": False,
            "is_processing": False,
            "intent": "",
            "clarification_attempts": 0
        })

    def update_state(self, clinic_phone: str, updates: Dict[str, Any]):
        if clinic_phone not in self.states:
            self.states[clinic_phone] = self.get_state(clinic_phone)

        print(updates, "save state data ............")
        self.states[clinic_phone].update(updates)
        self._save_states()

    def clear_state(self, clinic_phone: str):
        if clinic_phone in self.states:
            del self.states[clinic_phone]
            self._save_states()