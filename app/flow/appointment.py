from app.managers.appointment_dialog import AppointmentDialog
from app.models.models import ConfirmIntent, DataType, Message
from app.services.whatsapp import WhatsAppBusinessAPI
from app.utils.state_manager import StateManager

class AppointmentFlow:
    def __init__(self, message: Message):
        self.message = message
        self.state_manager = StateManager()

        self.dialog_manager = AppointmentDialog(
            message,
            DataType.APPOINTMENT
        )
        self.state = self.state_manager.get_state(self.message.phone_number)
        self.whatsapp_service = WhatsAppBusinessAPI(message)

    async def start(self):
        if self.state.confirm_intent == ConfirmIntent.CONFIRM_DATA:
            await self.dialog_manager._handle_confirm_response()
            return

        if not self.state.input_request and not self.dialog_manager.get_collected_data():
            await self._start_fresh_flow()
            return

        validation_result = await self.dialog_manager._process_step_input()

        if not self.state.input_request and not validation_result.invalid_fields:
            if self.dialog_manager.is_data_complete():
                data = self.dialog_manager.get_collected_data()
                await self.dialog_manager._confirm_input(data)
                self.state_manager.update_state(
                    self.message.phone_number,
                    confirm_intent=ConfirmIntent.CONFIRM_DATA
                )
            else:
                await self.dialog_manager.move_to_next_field()

    async def _start_fresh_flow(self):
        await self.whatsapp_service.send_text_message("Awesome! Let's get your appointment booked!")
        await self.dialog_manager.move_to_next_field()

    async def restart(self):
        self.state_manager.update_state(
            self.message.phone_number,
            appointment_data={},
            input_request=None,
            confirm_intent=None
        )
        await self._start_fresh_flow()