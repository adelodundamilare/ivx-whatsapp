import traceback
from typing import Dict
from app.models.models import AppointmentData, ConversationState, Intent
from datetime import datetime
from app.agents.base import VoiceAgent
from app.agents.intent import IntentAgent
from app.agents.extraction import ExtractionAgent
from app.agents.dialog import DialogAgent

from app.services import database
from app.utils.state_manager import state_manager
from app.utils.logger import setup_logger

logger = setup_logger("conversation_api", "conversation.log")

class ConversationManager:
    def __init__(self):
        self.voice_agent = VoiceAgent()
        self.intent_agent = IntentAgent()
        self.extraction_agent = ExtractionAgent()
        self.dialog_agent = DialogAgent()

    async def handle_conversation(self, phone_number: str, message: str) -> str:
        try:
            state = state_manager.conversation_state
            state.interaction_count += 1

            intent = await self.intent_agent.process(message)
            state.current_intent = intent
            state.phone_number = phone_number

            if state.confirmation_pending:
                state.current_intent = Intent.CREATE_APPOINTMENT

            if state.modification_pending:
                state.current_intent = Intent.EDIT_APPOINTMENT

            response = await self._handle_state_based_response(message)

            state.last_interaction = datetime.now()
            # state_manager.conversations[phone_number] = state

            return response

        except Exception as e:
            traceback.print_exc()
            logger.error(f"Error in conversation handling: {str(e)}")
            return "I apologize, but I'm having trouble processing your request. Please try again or contact our support team."

    async def _handle_state_based_response(self, message: str) -> str:

        try:
            state = state_manager.conversation_state

            if state.confirmation_pending:
                return await self._handle_confirmation(state, message)

            if state.modification_pending:
                return await self._handle_modification(state, message)

            if state.current_intent == Intent.CREATE_APPOINTMENT:
                return await self._handle_appointment_creation(state, message)

            if state.current_intent == Intent.EDIT_APPOINTMENT:
                return await self._handle_appointment_modification(state, message)

            # if state.current_intent == Intent.GREETING:
            #     return await self._handle_greeting(state, message)

            # Handle other intents... like cancel, status, doctor info, faq...
            return self.dialog_agent.generate_generic_response(message)

        except ValueError as e:
            state.last_error = str(e)
            traceback.print_exc()
            return f"I noticed an issue: {str(e)}. Could you please provide valid information?"

    async def _handle_appointment_creation(self, state: ConversationState, message: str) -> str:
        try:
            extracted_data = await self.extraction_agent.process(message, Intent.CREATE_APPOINTMENT)

            return await self.dialog_agent.process(
                phone_number=state.phone_number,
                intent=Intent.CREATE_APPOINTMENT,
                extracted_data=extracted_data
            )


        except ValueError as e:
            state.last_error = str(e)
            traceback.print_exc()
            return f"There seems to be an issue with the information provided: {str(e)}. Could you please provide valid information?"

    async def _handle_appointment_modification(self, state: ConversationState, message: str) -> str:
        try:
            extracted_data = await self.extraction_agent.process(message, Intent.EDIT_APPOINTMENT)

            return await self.dialog_agent.process(
                phone_number=state.phone_number,
                intent=Intent.EDIT_APPOINTMENT,
                extracted_data=extracted_data
            )

        except ValueError as e:
            state.last_error = str(e)
            return f"There seems to be an issue with modifying the appointment: {str(e)}. Could you please provide valid information?"

    async def _handle_greeting(self, state: ConversationState, message: str) -> str:
        try:
            extracted_data = await self.extraction_agent.process(message, Intent.EDIT_APPOINTMENT)

            intent = await self.intent_agent.process(message)
            state.current_intent = intent

        except ValueError as e:
            state.last_error = str(e)
            return f"There seems to be an issue with modifying the appointment: {str(e)}. Could you please provide valid information?"

    async def _handle_confirmation(self, state: ConversationState, message: str) -> str:

        if message == '1': #confirm
            result = await self._process_confirmed_action(state)
            state.confirmation_pending = False
            return result
        elif message == '2': # deny
            state.confirmation_pending = False
            return "I understand you don't want to proceed. What would you like to change?"
        else:
            return "I didn't quite catch that. Could you please confirm with '1' to confirm or '2' to deny/reject?"

    async def _process_confirmed_action(self, state: ConversationState) -> str:
        try:
            if state.current_intent == Intent.CREATE_APPOINTMENT:
                appointment_data = state.collected_data
                # assign a doctor...
                await database.create_appointment(appointment_data)
                # Send confirmation
                return f"Great! I've scheduled your appointment. We'll send you a confirmation message shortly."

            elif state.current_intent == Intent.EDIT_APPOINTMENT:
                # Process appointment modification
                # Save appointment to database
                return "I've updated your appointment with the new details. You'll receive a confirmation message shortly."

            elif state.current_intent == Intent.CANCEL_APPOINTMENT:
                # Process cancellation
                # Save appointment to database
                return "Your appointment has been cancelled. Would you like to reschedule?"

            else:
                return "I've processed your request. Is there anything else you need help with?"

        except ValueError as e:
            logger.error(f"Validation error in confirmed action: {str(e)}")
            return f"I'm sorry, but there seems to be an issue: {str(e)}. Could you please provide the correct information?"

        except Exception as e:
            logger.error(f"Error in processing confirmed action: {str(e)}")
            return "I'm having trouble processing your request. Please try again or contact our support team."


    async def _handle_modification(self, state: ConversationState, message: str) -> str:
        try:
            modified_data = await self.extraction_agent.process(message, state.current_intent)

            if not self._validate_modifications(modified_data):
                return "Some of the modifications aren't valid. Could you please check and try again?"

            state.collected_data.update(modified_data)
            state.modification_pending = False

            return await self._generate_confirmation_prompt(state)

        except Exception as e:
            logger.error(f"Error in modification handling: {str(e)}")
            return "I'm having trouble processing the modifications. Could you please try again?"


    @staticmethod
    def _validate_modifications(modified_data: Dict) -> bool:
        try:
            if 'preferred_date' in modified_data:
                date = datetime.strptime(modified_data['preferred_date'], '%Y-%m-%d')
                if date < datetime.now():
                    return False
            # Add more validation rules...
            return True
        except Exception:
            return False