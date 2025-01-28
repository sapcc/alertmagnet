from datetime import datetime as dt
from datetime import timedelta as td


def calculate_past_five_years_timestamp(start: dt) -> float:
    past = start - td(weeks=260)  # 260 = 52 * 5 | past 5 years
    return past.timestamp()
