import re

from datetime import datetime as dt
from datetime import timedelta as td


class Calc:
    def __init__(self):
        pass

    def calculate_max_past(self, end: dt, past_range: str = "1y") -> float:
        delta = self.__parse_past_range(past_range)
        past = end - delta

        return past.timestamp()

    def __parse_past_range(self, past_range: str) -> td:
        match = re.match(r"(?:(\d+)y)?(?:(\d+)m)?(?:(\d+)w)?(?:(\d+)d)?", past_range)

        if not match:
            raise ValueError(f"Invalid past_range format: {past_range}")

        years = int(match.group(1) or 0)
        months = int(match.group(2) or 0)
        weeks = int(match.group(3) or 0)
        days = int(match.group(4) or 0)

        total_days = years * 365 + months * 28 + weeks * 7 + days

        return td(days=total_days)
