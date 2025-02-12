from datetime import datetime, timedelta
from typing import Dict

from pydantic import ValidationError
from app.models.whatsapp import ConversationState
from app.models.appointment import Appointment
from app.repository.whatsapp import WhatsAppRepository
from app.utils.validator import DataValidator


async def process_message(
    user_id: str,
    message: str,
    current_state: ConversationState,
    repository: WhatsAppRepository
) -> str:
    if current_state == ConversationState.WELCOME:
        repository.user_states[user_id] = ConversationState.SERVICE_MENU
        return """Welcome to IVX Anesthesia Services! 👋

How can I assist you today?
1. Schedule an appointment
2. View doctor profiles
3. FAQ
4. Speak to a human agent"""

    elif current_state == ConversationState.SERVICE_MENU:
        return await handle_menu_selection(user_id, message, repository)

    elif current_state == ConversationState.BOOK_APPOINTMENT:
        return await handle_booking_flow(user_id, message, repository)

    return "I'm sorry, I didn't understand that. Please try again."

async def handle_menu_selection(
    user_id: str,
    message: str,
    repository: WhatsAppRepository
) -> str:
    if message == "1":
        repository.user_states[user_id] = ConversationState.BOOK_APPOINTMENT
        return "Please enter your clinic name to begin booking:"
    elif message == "2":
        repository.user_states[user_id] = ConversationState.DOCTOR_INFO
        return "Our anesthesiologists:\n\nDr. Smith - Specializing in pediatric cases\nDr. Johnson - Expert in complex procedures\nDr. Williams - Certified in conscious sedation"
    elif message == "3":
        repository.user_states[user_id] = ConversationState.FAQ
        return "Common Questions:\n\n1. How long before my procedure should I fast?\n2. What's the recovery time?\n3. Is anesthesia safe?\n\nReply with a number for more details."
    elif message == "4":
        # Transfer to human agent logic here
        return "Connecting you with a customer service representative. Please wait a moment."
    else:
        return "Please select a valid option (1-4)"

async def handle_booking_flow(
    user_id: str,
    message: str,
    repository: WhatsAppRepository
) -> str:
    """Handle appointment booking flow"""
    current_appointment = repository.appointments.get(user_id)

    if not current_appointment:
        # Start new appointment
        repository.appointments[user_id] = Appointment(
            clinic_name=message,
            clinic_address="",
            appointment_date=datetime.now(),
            procedure_type="",
            patient_phone=user_id
        )
        repository.user_states[user_id] = ConversationState.COLLECT_CLINIC_INFO
        return "Please enter your clinic's address:"

    # Add more booking flow logic here
    return "Appointment booking in progress..."



class WhatsAppService:
    def __init__(self, ai_assistant, appointment_manager):
        self.ai_assistant = ai_assistant
        self.appointment_manager = appointment_manager
        self.conversation_states = {}

    async def handle_message(self, user_id: str, message: str) -> str:
        current_state = self.conversation_states.get(user_id, {})
        intent, entities = await self.ai_assistant.process_message(message)

        if intent == "create_appointment":
            return await self._handle_appointment_creation(user_id, message, current_state)
        elif intent == "edit_appointment":
            return await self._handle_appointment_modification(user_id, message, current_state)
        elif intent == "cancel_appointment":
            return await self._handle_appointment_cancellation(user_id, message, current_state)
        elif intent == "check_status":
            return await self._handle_status_check(user_id, message)
        # doctor_info, cost_info
        else:
            return await self._handle_general_inquiry(message)

    async def _handle_appointment_creation(self, user_id: str, message: str, state: Dict) -> str:
        if "step" not in state:
            self.conversation_states[user_id] = {"step": "clinic_name"}
            return "Let's schedule your appointment. What's the name of your dental clinic?"

        current_step = state["step"]

        if current_step == "clinic_name":
            state["clinic_name"] = message
            state["step"] = "procedure_type"
            self.conversation_states[user_id] = state
            return """What type of procedure is this for? Please select a number:
1. Wisdom Teeth Extraction
2. Dental Implants
3. Root Canal
4. Multiple Extractions
5. Pediatric Dental Work"""

        elif current_step == "procedure_type":
            procedure_map = {
                "1": "wisdom_teeth",
                "2": "dental_implants",
                "3": "root_canal",
                "4": "multiple_extractions",
                "5": "pediatric_dental"
            }
            state["procedure_type"] = procedure_map.get(message)
            if not state["procedure_type"]:
                return "Please select a valid option (1-5)"

            state["step"] = "preferred_date"
            self.conversation_states[user_id] = state
            return "What's your preferred date for the procedure? (Please use format DD/MM/YYYY)"

        elif current_step == "preferred_date":
            try:
                state["preferred_date"] = datetime.strptime(message, "%d/%m/%Y")
                state["step"] = "patient_name"
                self.conversation_states[user_id] = state
                return "What's the patient's full name?"
            except ValueError:
                return "Please enter a valid date in the format DD/MM/YYYY"

        elif current_step == "patient_name":
            state["patient_name"] = message
            state["step"] = "confirm"
            self.conversation_states[user_id] = state

            summary = f"""Please confirm your appointment details:
- Clinic: {state['clinic_name']}
- Procedure: {state['procedure_type']}
- Date: {state['preferred_date'].strftime('%d/%m/%Y')}
- Patient: {state['patient_name']}

Reply with:
1. Confirm
2. Make changes"""
            return summary

        elif current_step == "confirm":
            if message == "1":
                try:
                    appointment = await self.appointment_manager.create_appointment(
                        Appointment(
                            clinic_name=state['clinic_name'],
                            procedure_type=state['procedure_type'],
                            preferred_date=state['preferred_date'],
                            patient_name=state['patient_name'],
                            patient_phone=user_id
                        )
                    )

                    self.conversation_states.pop(user_id, None)

                    await self.appointment_manager.start_doctor_notification_sequence(
                        appointment['id']
                    )

                    return f"""Great! Your appointment has been scheduled.
Appointment ID: {appointment['id']}
We'll notify you once a doctor confirms the appointment.

You can check the status anytime by sending 'status {appointment['id']}'"""

                except Exception as e:
                    return f"Sorry, there was an error scheduling your appointment. Please try again."

            elif message == "2":
                self.conversation_states[user_id] = {"step": "clinic_name"}
                return "Let's start over. What's the name of your dental clinic?"

            else:
                return "Please reply with 1 to confirm or 2 to make changes."

    async def _handle_appointment_modification(self, user_id: str, message: str, state: Dict) -> str:
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

    async def _handle_status_check(self, user_id: str, message: str) -> str:
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

    async def _handle_general_inquiry(self, message: str) -> str:
        """Handle general inquiries and questions"""
        return """How can I help you today?
1. Schedule new appointment
2. Modify existing appointment
3. Check appointment status
4. Speak to a human agent"""






class WhatsAppHandler:
    def __init__(self, ai_assistant, appointment_manager):
        self.ai_assistant = ai_assistant
        self.appointment_manager = appointment_manager
        self.conversation_states: Dict[str, ConversationState] = {}
        self.error_handler = ErrorHandler()

    async def handle_message(self, user_id: str, message: str) -> str:
        try:
            message = DataValidator.sanitize_input(message)

            state = self.conversation_states.get(user_id)

            if state and (datetime.now() - state.last_update) > timedelta(minutes=15):
                state = None

            if not state:
                intent, entities = await self.ai_assistant.process_message(message)
                return await self._handle_initial_message(user_id, intent, entities)

            return await self._handle_conversation_step(user_id, message, state)

        except Exception as e:
            self.error_handler.log_error(e, {
                'user_id': user_id,
                'message': message
            })
            return "I'm having trouble processing your request. Please try again or type 'help' for assistance."

    async def _handle_initial_message(
        self,
        user_id: str,
        intent: str,
        entities: Dict
    ) -> str:
        try:
            if intent == "book_appointment":
                self.conversation_states[user_id] = ConversationState(
                    step="collect_clinic",
                    data=entities
                )
                return ("Let's schedule your appointment. "
                       "What's the name of your dental clinic?")

            elif intent == "check_availability":
                return await self._handle_availability_check(entities)

            elif intent == "reschedule":
                if "appointment_id" in entities:
                    return await self._start_reschedule_flow(
                        user_id,
                        entities["appointment_id"]
                    )
                return "Please provide your appointment ID to reschedule."

            elif intent == "cancel":
                if "appointment_id" in entities:
                    return await self._start_cancellation_flow(
                        user_id,
                        entities["appointment_id"]
                    )
                return "Please provide your appointment ID to cancel."

            else:
                return """How can I assist you today?
1. Schedule new appointment
2. Check doctor availability
3. Manage existing appointment
4. Speak to a human agent"""

        except Exception as e:
            self.error_handler.log_error(e, {
                'user_id': user_id,
                'intent': intent,
                'entities': entities
            })
            return "I'm sorry, I encountered an error. Please try again."

    async def _handle_conversation_step(
        self,
        user_id: str,
        message: str,
        state: ConversationState
    ) -> str:
        """Handle ongoing conversation steps"""
        try:
            state.last_update = datetime.now()

            if message.lower() == "cancel":
                self.conversation_states.pop(user_id, None)
                return "Operation canceled. How else can I help you?"

            if message.lower() == "help":
                return self._get_help_message(state.step)

            handler = getattr(self, f"_handle_{state.step}", None)
            if handler:
                response = await handler(user_id, message, state)
            else:
                response = "I'm sorry, something went wrong. Please start over."
                self.conversation_states.pop(user_id, None)

            return response

        except ValidationError as e:
            state.attempt_count += 1
            if state.attempt_count >= 3:
                self.conversation_states.pop(user_id, None)
                return ("I'm having trouble understanding your input. "
                       "Please start over or type 'help' for assistance.")
            return f"Invalid input: {e.message}. Please try again."

        except Exception as e:
            self.error_handler.log_error(e, {
                'user_id': user_id,
                'state': state.dict()
            })
            self.conversation_states.pop(user_id, None)
            return "An error occurred. Please start over."

    async def _handle_collect_clinic(
        self,
        user_id: str,
        message: str,
        state: ConversationState
    ) -> str:
        """Handle clinic name collection"""
        if not DataValidator.validate_name(message):
            raise ValidationError("Please provide a valid clinic name")

        state.data['clinic_name'] = message
        state.step = 'collect_procedure'
        self.conversation_states[user_id] = state

        return """What type of procedure is this for? Please select a number:
1. Wisdom Teeth Extraction
2. Dental Implants
3. Root Canal
4. Multiple Extractions
5. Pediatric Dental Work"""

    async def _handle_availability_check(self, entities: Dict) -> str:
        """Handle availability check requests"""
        try:
            date = entities.get('date', datetime.now().date())
            available_slots = await self.appointment_manager.get_available_slots(date)

            if not available_slots:
                return f"Sorry, no available slots found for {date.strftime('%Y-%m-%d')}."

            slots_text = "\n".join(
                slot.strftime("%I:%M %p") for slot in available_slots[:5]
            )

            return f"""Available slots for {date.strftime('%Y-%m-%d')}:
{slots_text}

Reply with 'book' followed by the time to schedule an appointment."""

        except Exception as e:
            self.error_handler.log_error(e, {'entities': entities})
            return "Sorry, I couldn't check availability right now. Please try again later."

    def _get_help_message(self, step: str) -> str:
        """Get context-aware help messages"""
        help_messages = {
            "collect_clinic": "Please provide the name of your dental clinic (minimum 3 characters"}