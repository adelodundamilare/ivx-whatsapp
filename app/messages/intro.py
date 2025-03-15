from typing import Dict
from app.data.appointment import AppointmentHandler
from app.models.whatsapp import ConversationState
from app.utils.state_manager import state_manager

# INTRO OPTIONS
# 1. Schedule new appointment
# 2. Modify existing appointment
# 3. Check appointment status
# 4. Handle appointment cancellation
# 5. View doctor profiles
# 6. Handle procedure info
# 7. FAQ

async def handle_intro_response(message):
    if message == '1':
        return await handle_appointment_scheduling({})
    elif message == '2':
        return handle_appointment_modification()
    elif message == '3':
        return handle_status_check()
    elif message == '4':
        return handle_appointment_cancellation()
    elif message == '5':
        return handle_doctor_info()
    elif message == '6':
        return handle_procedure_info()

    return handle_intro()


async def handle_appointment_scheduling(message: str):
    state_manager.set_conversation_state(ConversationState.BOOK_APPOINTMENT)

    handler = AppointmentHandler(state_manager)
    return await handler.handle_appointment(message)

    # if is_current_step("service_type"):
    #     res = handle_service_type_input(message, data)
    #     if res:
    #         return res

    # if is_current_step("preferred_date"):
    #     if not DataValidator.validate_date(message):
    #         set_current_step("preferred_date")
    #         return "Please provide a valid future date in YYYY-MM-DD format."
    #     data["preferred_date"] = message

    # if is_current_step("patient_name"):
    #     if not DataValidator.validate_name(message):
    #         set_current_step("patient_name")
    #         return "Please enter a valid name."
    #     data["patient_name"] = message

    # if is_current_step("clinic_name"):
    #     if not DataValidator.validate_name(message):
    #         set_current_step("clinic_name")
    #         return "Please provide a valid clinic name"
    #     data["clinic_name"] = message

    # if is_current_step("summary"):
    #     if message == '1':
    #         # send request to backend...
    #         return f"""Great! I'll help you schedule an appointment for a *{data['service_type'].replace("_", " ").title()}* procedure on *{data['preferred_date']}* at *{data['clinic_name']}*. Would you like me to check doctor availability now?"""

    #     elif message == '2':
    #         del data["service_type"]
    #         del data["preferred_date"]
    #         del data["patient_name"]
    #         del data["clinic_name"]
    #         set_current_step("service_type")
    #         state_manager.set_conversation_state(ConversationState.BOOK_APPOINTMENT)
    #         return AppointmentPrompts.get_procedure_prompt()
    #     else:
    #         return "Please reply with 1 to confirm or 2 to make changes."

    # required_fields = ["service_type", "preferred_date", "patient_name", "clinic_name", "summary"]
    # missing_fields = [field for field in required_fields if field not in data]

    # if missing_fields:
    #     next_field = missing_fields[0]
    #     if next_field == "service_type":
    #         set_current_step("service_type")
    #         return AppointmentPrompts.get_procedure_prompt()
    #     if next_field == "preferred_date":
    #         set_current_step("preferred_date")
    #         return AppointmentPrompts.PREFERRED_DATE
    #     if next_field == "patient_name":
    #         set_current_step("patient_name")
    #         return AppointmentPrompts.PATIENT_NAME
    #     if next_field == "clinic_name":
    #         set_current_step("clinic_name")
    #         return AppointmentPrompts.CLINIC_NAME
    #     if next_field == "summary":
    #         set_current_step("summary")
    #         return AppointmentPrompts.SUMMARY(data)

    #     set_current_step("")


async def handle_appointment_modification(self, user_id: str, message: str, state: Dict) -> str:
    if "step" not in state:
        self.conversation_states[user_id] = {"step": "get_appointment_id"}
        return "Please provide the appointment ID you'd like to modify."

    current_step = state["step"]

    if current_step == "get_appointment_id":
        appointment = await self.appointment_manager._get_appointment(message)
        if not appointment or appointment['patient_phone'] != user_id:
            return "Sorry, I couldn't find that appointment. Please check the ID and try again."

        state["appointment_id"] = message
        state["step"] = "modification_type"
        self.conversation_states[user_id] = state
        return """What would you like to modify?
1. Date
2. Procedure type
3. Cancel appointment"""

    elif current_step == "modification_type":
        if message == "1":
            state["modification"] = "date"
            state["step"] = "new_date"
            self.conversation_states[user_id] = state
            return "What's the new preferred date? (Please use format DD/MM/YYYY)"

        elif message == "2":
            state["modification"] = "procedure"
            state["step"] = "new_procedure"
            self.conversation_states[user_id] = state
            return """Select the new procedure type:
1. Wisdom Teeth Extraction
2. Dental Implants
3. Root Canal
4. Multiple Extractions
5. Pediatric Dental Work"""

        elif message == "3":
            state["step"] = "confirm_cancellation"
            self.conversation_states[user_id] = state
            return "Please provide a reason for cancellation."


async def handle_status_check(self, user_id: str, message: str) -> str:
    appointment_id = message.replace("status", "").strip()

    try:
        appointment = await self.appointment_manager._get_appointment(appointment_id)
        if not appointment:
            return "Sorry, I couldn't find that appointment. Please check the ID and try again."

        status_messages = {
            "pending": "We're currently finding an available doctor.",
            "doctor_assigned": f"Dr. {appointment['doctor_name']} has been assigned to your case.",
            "confirmed": "Your appointment has been confirmed.",
            "canceled": "This appointment has been canceled.",
            "rescheduled": "This appointment has been rescheduled."
        }

        return f"""Appointment Status:
Date: {appointment['date'].strftime('%d/%m/%Y')}
Status: {status_messages.get(appointment['status'], 'Status unknown')}"""

    except Exception as e:
        return "Sorry, I couldn't retrieve the appointment status. Please try again later."


async def handle_appointment_cancellation(self, user_id: str, message: str, state: Dict) -> str:
    if "step" not in state:
        self.conversation_states[user_id] = {"step": "get_appointment_id"}
        return "Please provide the appointment ID you'd like to cancel."

    current_step = state["step"]

    if current_step == "get_appointment_id":
        appointment = await self.appointment_manager._get_appointment(message)
        if not appointment or appointment['patient_phone'] != user_id:
            return "Sorry, I couldn't find that appointment. Please check the ID and try again."

        state["appointment_id"] = message
        state["step"] = "confirm_cancellation"
        self.conversation_states[user_id] = state
        return "Please provide a reason for cancellation."

    elif current_step == "confirm_cancellation":
        try:
            await self.appointment_manager._cancel_appointment(
                state["appointment_id"],
                cancellation_reason=message
            )
            del self.conversation_states[user_id]
            return "Your appointment has been successfully canceled. We'll send you a confirmation message shortly."
        except Exception as e:
            return "Sorry, I couldn't cancel the appointment. Please try again later."


def handle_doctor_info(entities: Dict):
    if "doctor_name" in entities:
        return f"Let me fetch Dr. {entities['doctor_name']}'s profile and availability."
    return ("I can help you learn about our anesthesiologists. "
            "Would you like to know about their specialties, experience, or availability?")

def handle_procedure_info(entities: Dict):
    proc_type = entities.get("service_type")
    if proc_type:
        return f"Let me provide you with information about anesthesia for {proc_type}."
    return ("I can provide information about anesthesia for various dental procedures. "
            "Which procedure would you like to learn more about?")

def handle_intro():
    state_manager.set_conversation_state(ConversationState.WELCOME)
    return """Welcome to IVX Anesthesia Services! 👋

How can I help you today?
1. Schedule new appointment
2. Modify existing appointment
3. Check appointment status
4. Handle Appointment cancellation
5. View doctor profiles
6. Speak to an Agent
7. FAQ"""





# def handle_service_type_input(message: str, data: dict) -> str:
#     if not DataValidator.validate_service_type(message):
#         set_current_step("service_type")
#         return "Please select a valid procedure type (1-5)."

#     procedure = ProcedureType.from_input(message)

#     if procedure:
#         data["service_type"] = procedure.value
#         # Or if you want to store the enum itself:
#         # data["service_type"] = procedure
#     else:
#         set_current_step("service_type")
#         return "Invalid procedure type selected."