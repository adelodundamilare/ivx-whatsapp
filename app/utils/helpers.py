from datetime import datetime
import re
from typing import Dict
from app.models.models import Message
from app.services.whatsapp import WhatsAppBusinessAPI
from langchain_core.runnables.history import RunnableWithMessageHistory # type: ignore
from langchain_community.chat_message_histories import ChatMessageHistory # type: ignore
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder # type: ignore
from langchain_openai import ChatOpenAI # type: ignore
import os

llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo", temperature=0.7)

response_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "You are AIA, a professional and friendly AI assistant helping clinics - the user - connect with doctors. Use the conversation history to maintain context. Respond conversationally to: '{input}'. Guide the user proactively with suggestions (e.g., 'Would you like to book an appointment?')."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ]
)
response_chain = response_prompt | llm

response_history: Dict[str, ChatMessageHistory] = {}
def get_message_history(clinic_phone: str) -> ChatMessageHistory:
    if clinic_phone not in response_history:
        response_history[clinic_phone] = ChatMessageHistory()
        print(f"Initialized new history for {clinic_phone}")
    res =  response_history[clinic_phone]
    # print(res, 'get_message_history oooooooooooooooooooooooooooooooooooooooooooo')
    return res

def get_response_runnable(clinic_phone: str) -> RunnableWithMessageHistory:
    return RunnableWithMessageHistory(
        runnable=response_chain,
        get_session_history=lambda session_id: get_message_history(session_id),
        input_messages_key="input",
        history_messages_key="chat_history",
    )

async def invoke_ai(prompt:str, clinic_phone:str):
    runnable = get_response_runnable(clinic_phone)
    response = await runnable.ainvoke(
        {"input": prompt},
        config={"configurable": {"session_id": clinic_phone}}
    )
    return response.content

async def send_response(clinic_phone: str, response_message: str, message: Message):
    history = get_message_history(clinic_phone)
    history.add_ai_message(response_message)
    whatsapp_service = WhatsAppBusinessAPI(message)
    await whatsapp_service.send_text_message(to_number=clinic_phone, message=response_message)

# def parse_relative_date(date_expression):
#     date_expression = date_expression.lower().strip()
#     current_date = datetime.now()

#     try:
#         for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%Y/%m/%d']:
#             try:
#                 return datetime.strptime(date_expression, fmt)
#             except ValueError:
#                 continue
#     except ValueError:
#         pass

#     if date_expression == 'today':
#         return current_date
#     elif date_expression == 'tomorrow':
#         return current_date + timedelta(days=1)
#     elif date_expression == 'yesterday':
#         return current_date - timedelta(days=1)

#     month_pattern = r'(?:(\d+)(?:st|nd|rd|th))?\s*(next|last)\s+month'
#     month_match = re.match(month_pattern, date_expression)
#     if month_match:
#         day, direction = month_match.groups()

#         if direction == 'next':
#             new_date = current_date + relativedelta(months=1)
#         else:
#             new_date = current_date - relativedelta(months=1)

#         if day:
#             day = int(day)
#             max_day = calendar.monthrange(new_date.year, new_date.month)[1]
#             day = min(day, max_day)
#             return new_date.replace(day=day)

#         return new_date

#     days = {
#         'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
#         'friday': 4, 'saturday': 5, 'sunday': 6
#     }

#     pattern = r'(next|last)?\s*(\w+)(?:\s+(next|last)\s+week)?'
#     match = re.match(pattern, date_expression)

#     if not match:
#         raise ValueError(f"Unable to parse date expression: {date_expression}")

#     prefix, day, week_modifier = match.groups()

#     if day not in days:
#         raise ValueError(f"Invalid day of week: {day}")

#     target_day = days[day]
#     current_day = current_date.weekday()

#     days_until = (target_day - current_day) % 7

#     if prefix == 'last' or week_modifier == 'last':
#         if days_until == 0:
#             days_until = -7
#         else:
#             days_until = days_until - 7
#     elif prefix == 'next' or week_modifier == 'next':
#         if days_until == 0:
#             days_until = 7
#         else:
#             days_until = days_until + 7
#     else:
#         if days_until == 0:
#             days_until = 7

#     return current_date + timedelta(days=days_until)

# def format_date(date):
#     return date.strftime("%Y-%m-%d")


def validate_date(date_str: str) -> bool:
    date_str = date_str.strip()

    date_pattern = r'^(0?[1-9]|[12][0-9]|3[01])[\/-](0?[1-9]|1[0-2])[\/-](20\d{2})$'
    if not re.match(date_pattern, date_str):
        # Try alternate format MM/DD/YYYY
        alternate_pattern = r'^(0?[1-9]|1[0-2])[\/-](0?[1-9]|[12][0-9]|3[01])[\/-](20\d{2})$'
        if not re.match(alternate_pattern, date_str):
            return False

    try:
        if '/' in date_str:
            day, month, year = map(int, date_str.split('/'))
        else:
            day, month, year = map(int, date_str.split('-'))

        input_date = datetime(year, month, day)

        current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return input_date >= current_date
    except ValueError:
        try:
            if '/' in date_str:
                month, day, year = map(int, date_str.split('/'))
            else:
                month, day, year = map(int, date_str.split('-'))

            input_date = datetime(year, month, day)

            current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return input_date >= current_date
        except ValueError:
            return False

def validate_time(time_str: str) -> bool:
    time_str = time_str.strip().upper()
    time_pattern_12h = r'^(0?[1-9]|1[0-2]):([0-5][0-9])\s*(AM|PM)$'
    time_pattern_24h = r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$'

    if re.match(time_pattern_12h, time_str) or re.match(time_pattern_24h, time_str):
        return True

    return False

