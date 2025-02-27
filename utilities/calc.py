import logging
import re

from datetime import datetime as dt
from datetime import timedelta as td

logger = logging.getLogger("alertmagnet")


class Calc:
    def __init__(self):
        self.max_long_term = None

    def set_max_long_term(self, max_long_term: str):
        self.max_long_term = max_long_term

    def calculate_max_past(self, end: dt, past_range: str) -> float:
        logger.debug("Calculating max past for %s and %s", end, past_range)
        delta = self.__parse_past_range(past_range)
        past = end - delta

        return past.timestamp()

    def __parse_past_range(self, past_range: str) -> td:
        match = re.match(r"(?:(\d+)y)?(?:(\d+)m)?(?:(\d+)w)?(?:(\d+)d)?", past_range)

        if not match:
            logger.error("Invalid past_range format: %s", past_range)
            raise ValueError(f"Invalid past_range format: {past_range}")

        years = int(match.group(1) or 0)
        months = int(match.group(2) or 0)
        weeks = int(match.group(3) or 0)
        days = int(match.group(4) or 0)

        total_days = years * 365 + months * 28 + weeks * 7 + days
        logger.debug("Total days: %d", total_days)

        return td(days=total_days)
