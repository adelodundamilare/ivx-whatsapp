import json
import os
from typing import Any, Dict

class DoctorStateManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DoctorStateManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self, storage_file: str = "doctor_states.json"):
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