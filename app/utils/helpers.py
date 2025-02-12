import calendar
from datetime import datetime, timedelta
import re
from dateutil.relativedelta import relativedelta # type: ignore


def parse_relative_date(date_expression):
    date_expression = date_expression.lower().strip()
    current_date = datetime.now()

    try:
        for fmt in ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%Y/%m/%d']:
            try:
                return datetime.strptime(date_expression, fmt)
            except ValueError:
                continue
    except ValueError:
        pass

    if date_expression == 'today':
        return current_date
    elif date_expression == 'tomorrow':
        return current_date + timedelta(days=1)
    elif date_expression == 'yesterday':
        return current_date - timedelta(days=1)

    month_pattern = r'(?:(\d+)(?:st|nd|rd|th))?\s*(next|last)\s+month'
    month_match = re.match(month_pattern, date_expression)
    if month_match:
        day, direction = month_match.groups()

        if direction == 'next':
            new_date = current_date + relativedelta(months=1)
        else:
            new_date = current_date - relativedelta(months=1)

        if day:
            day = int(day)
            max_day = calendar.monthrange(new_date.year, new_date.month)[1]
            day = min(day, max_day)
            return new_date.replace(day=day)

        return new_date

    days = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6
    }

    pattern = r'(next|last)?\s*(\w+)(?:\s+(next|last)\s+week)?'
    match = re.match(pattern, date_expression)

    if not match:
        raise ValueError(f"Unable to parse date expression: {date_expression}")

    prefix, day, week_modifier = match.groups()

    if day not in days:
        raise ValueError(f"Invalid day of week: {day}")

    target_day = days[day]
    current_day = current_date.weekday()

    days_until = (target_day - current_day) % 7

    if prefix == 'last' or week_modifier == 'last':
        if days_until == 0:
            days_until = -7
        else:
            days_until = days_until - 7
    elif prefix == 'next' or week_modifier == 'next':
        if days_until == 0:
            days_until = 7
        else:
            days_until = days_until + 7
    else:
        if days_until == 0:
            days_until = 7

    return current_date + timedelta(days=days_until)

def format_date(date):
    return date.strftime("%Y-%m-%d")