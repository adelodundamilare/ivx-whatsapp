import asyncio
import json
from app.models.models import Message
from app.services.whatsapp import WhatsAppBusinessAPI
from crewai import Agent, Crew, Task, Process
from langchain_openai import ChatOpenAI # type: ignore
from app.services.bubble_client import BubbleApiClient


llm = ChatOpenAI(model="gpt-4", temperature=0.5)

user_memory = {}

BUBBLE_API_URL = "https://your-bubble-app.com/api/1.1/obj/appointments"

# 🌍 Supported Languages
LANGUAGES = {
    "en": {"booked": "✅ Your appointment has been booked!", "updated": "✏️ Your appointment has been updated!", "canceled": "❌ Your appointment has been canceled!", "not_understood": "🤖 I didn't understand your request. Please try again!"},
    "es": {"booked": "✅ ¡Tu cita ha sido reservada!", "updated": "✏️ ¡Tu cita ha sido actualizada!", "canceled": "❌ ¡Tu cita ha sido cancelada!", "not_understood": "🤖 No entendí tu solicitud. ¡Por favor, intenta de nuevo!"}
}


class MedicalAssistant:
    def __init__(self, message: Message):
        """Initialize all agents, tasks, and the CrewAI system."""
        self.message = message
        self.whatsapp_service = WhatsAppBusinessAPI(message)
        self.init_agents()

    def init_agents(self):
        self.intent_agent = Agent(role="Intent Classification Specialist", goal="Accurately determine user intent from natural language inputs to facilitate appointment scheduling.", llm=llm, backstory="Expert in linguistic analysis and healthcare-related queries.")
        self.scheduling_agent = Agent(role="Appointment Scheduler", goal="Manage clinic appointment scheduling, modifications, and cancellations.", llm=llm, backstory="Specialist in coordinating appointments based on doctor availability and patient requests.")
        self.database_agent = Agent(role="Medical Database Manager", goal="Retrieve and update clinic and appointment records.", llm=llm, backstory="Ensures data consistency and accuracy in the appointment system.")
        self.notification_agent = Agent(role="Notification Coordinator", goal="Handle patient and doctor notifications regarding appointment status.", llm=llm, backstory="Responsible for ensuring timely updates on appointment confirmations, reschedules, and cancellations.")

    def create_intent_task(self, user_input):
        return Task(
            description="Analyze user input and classify the intent into booking, editing, canceling, or retrieving an appointment.",
            agent=self.intent_agent,
            expected_output="{'intent': 'book'|'edit'|'cancel'|'retrieve', 'data': {...}}"
        )

    def create_task_for_intent(self, intent, extracted_data):
        if intent == "book":
            return Task(
                description="Schedule an appointment based on user request and doctor availability.",
                agent=self.scheduling_agent,
                expected_output="{'status': 'success', 'message': 'Appointment booked successfully.'}"
            )
        elif intent == "edit":
            return Task(
                description="Update an existing appointment with new details.",
                agent=self.scheduling_agent,
                expected_output="{'status': 'success', 'message': 'Appointment updated successfully.'}"
            )
        elif intent == "cancel":
            return Task(
                description="Cancel a scheduled appointment.",
                agent=self.scheduling_agent,
                expected_output="{'status': 'success', 'message': 'Appointment canceled successfully.'}"
            )
        elif intent == "retrieve":
            return Task(
                description="Retrieve details of an existing appointment.",
                agent=self.database_agent,
                expected_output="{'status': 'success', 'appointment_details': {...}}"
            )
        return None

    # def init_tasks(self):
    #     """Define tasks that agents will perform based on user input"""
    #     self.intent_task = Task(
    #         description="Analyze user messages and classify the intent as either appointment scheduling, editing, cancellation, or general inquiry.",
    #         agent=self.intent_agent,
    #         expected_output="A JSON object containing the classified intent type and any relevant details: {'intent': 'schedule|edit|cancel|inquiry', 'details': {...}}"
    #     )

    #     self.scheduling_task = Task(
    #         description="Book, edit, or cancel appointments based on user requests and doctor availability.",
    #         agent=self.scheduling_agent,
    #         expected_output="A JSON object with the appointment details and status: {'status': 'booked|edited|cancelled', 'appointment': {...}}"
    #     )

    #     self.matching_task = Task(
    #         description="Identify the most appropriate doctor for the patient based on clinic preferences and requested procedures.",
    #         agent=self.doctor_matching_agent,
    #         expected_output="A JSON object with matched doctor information: {'doctor_id': '123', 'name': 'Dr. Smith', 'specialty': '...', 'availability': [...]}"
    #     )

    #     self.notification_task = Task(
    #         description="Send notifications to doctors in sequential order as per clinic preferences and handle their responses.",
    #         agent=self.notification_agent,
    #         expected_output="A JSON object with notification status: {'status': 'sent|accepted|rejected', 'doctor_id': '123', 'response': '...'}"
    #     )

    #     self.database_task = Task(
    #         description="Retrieve necessary clinic and doctor information from Bubble.io and store new appointment data.",
    #         agent=self.database_agent,
    #         expected_output="A JSON object with operation status: {'operation': 'read|write', 'status': 'success|error', 'data': {...}}"
    #     )

    #     self.translation_task = Task(
    #         description="Translate appointment-related conversations between English and Mexican Spanish when required.",
    #         agent=self.language_agent,
    #         expected_output="A JSON object with translated text: {'original': '...', 'translated': '...', 'source_lang': 'en|es', 'target_lang': 'en|es'}"
    #     )

    async def save_appointment_to_bubble(self, appointment_data):
        await BubbleApiClient().create_appointment(appointment_data)

    async def update_appointment_in_bubble(self, appointment_id, update_data):
        await BubbleApiClient().create_appointment(update_data)

    async def notify_doctor(self, doctor_id, appointment_details):
        """Sends a notification to the doctor and waits for their response."""
        await asyncio.sleep(2)  # Simulating async process
        print(f"📢 Doctor {doctor_id} notified: {appointment_details}")

        # Simulating doctor response (Accept or Reject)
        doctor_response = "accept"  # This should be received from an actual API call
        if doctor_response == "accept":
            await self.whatsapp_service.send_text_message(f"✅ Doctor {doctor_id} has accepted the appointment.")
            return {"status": "accepted"}
        else:
            await self.whatsapp_service.send_text_message(f"❌ Doctor {doctor_id} has rejected the appointment.")
            return {"status": "rejected"}

    def process_message(self):
        """Dynamically call only the required agents based on the request"""
        crew = Crew(agents=[self.intent_agent], tasks=[self.intent_task])
        intent_result = crew.kickoff()  # Get intent classification result

        if "schedule" in intent_result:
            tasks = [self.scheduling_task, self.matching_task, self.database_task, self.notification_task]
        elif "edit" in intent_result or "cancel" in intent_result:
            tasks = [self.scheduling_task, self.database_task, self.notification_task]
        elif "general inquiry" in intent_result:
            tasks = []  # No scheduling needed
        else:
            tasks = []

        # If translation is needed, add the language agent
        if "translate" in intent_result:
            tasks.append(self.translation_task)

        # Run the required tasks
        if tasks:
            crew = Crew(agents=[task.agent for task in tasks], tasks=tasks)
            crew.kickoff()

    async def chat(self, user_input: str, language: str = "en"):
        intent_crew = Crew(
            agents=[self.intent_agent],
            tasks=[self.create_intent_task(user_input)],
            process=Process.sequential
        )

        intent_result = intent_crew.kickoff(inputs={"user_input": user_input}) or {}

        intent = intent_result.get("intent", "unknown")
        extracted_data = intent_result.get("data", {})

        task = self.create_task_for_intent(intent, extracted_data)

        if task:
            crew = Crew(agents=[task.agent], tasks=[task], process=Process.sequential)
            response = crew.kickoff(inputs=extracted_data) or {}
            message = response.get("message", LANGUAGES[language]["not_understood"])
        else:
            message = LANGUAGES[language]["not_understood"]

        await self.whatsapp_service.send_text_message(message)

    # async def chat(self, user_input: str, language: str = "en"):

    #     # Step 1️⃣: Intent Extraction
    #     result = self.crew.kickoff(inputs={"user_input": user_input})
    #     print(result)
    #     orchestrator_data = result


    #     intent = orchestrator_data.get("intent", "unknown")
    #     extracted_data = orchestrator_data.get("data", {})

    #     print(intent, 'intent oooooooooooooo')
    #     print(extracted_data, 'extracted_data oooooooooooooo')

    #     # Step 2️⃣: Routing based on intent
    #     if intent == "book":
    #         save_result = await self.save_appointment_to_bubble(extracted_data)
    #         doctor_id = save_result.get("doctor_id")

    #         # Notify doctor and await response
    #         await self.notify_doctor(doctor_id, extracted_data)
    #         await self.whatsapp_service.send_text_message(LANGUAGES[language]["booked"])

    #     elif intent == "edit":
    #         appointment_id = extracted_data.get("appointment_id")
    #         update_data = extracted_data.get("updates", {})

    #         await self.update_appointment_in_bubble(appointment_id, update_data)
    #         await self.whatsapp_service.send_text_message(LANGUAGES[language]["updated"])

    #     elif intent == "cancel":
    #         appointment_id = extracted_data.get("appointment_id")

    #         await self.update_appointment_in_bubble(appointment_id, {"status": "canceled"})
    #         await self.whatsapp_service.send_text_message(LANGUAGES[language]["canceled"])

    #     elif intent == "retrieve":
    #         response = await self.database_task.execute(user_input)
    #         await self.whatsapp_service.send_text_message(response)

    #     # use general agent here
    #     await self.whatsapp_service.send_text_message(LANGUAGES[language]["not_understood"])