from datetime import datetime
import re


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