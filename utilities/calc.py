from datetime import datetime as dt
from datetime import timedelta as td


def calculate_past_five_years_timestamp(start: dt) -> float:
    past = start - td(weeks=52 * 5) # assume that one year has 52 weeks
    return past.timestamp()
