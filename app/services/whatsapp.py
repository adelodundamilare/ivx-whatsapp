import datetime
from app.models.whatsapp import AppointmentCreate, ConversationState
from app.repository.whatsapp import WhatsAppRepository


async def process_message(
    user_id: str,
    message: str,
    current_state: ConversationState,
    repository: WhatsAppRepository
) -> str:
    """Process incoming message based on conversation state"""
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
    """Handle main menu selection"""
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
        repository.appointments[user_id] = AppointmentCreate(
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