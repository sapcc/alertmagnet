# pylint: disable=C0114, C0115, C0116
from datetime import timedelta as td
from unittest import TestCase

from utilities import Calc


class TestCalc(TestCase):
    def __init__(self, methodName="runTest"):
        self.calc = Calc()
        super().__init__(methodName)

    def test_parse_past_range_empty(self):
        expected_result = td(days=0)
        result = self.calc._Calc__parse_past_range("")  # pylint: disable=W0212

        self.assertEqual(result, expected_result)

    def test_parse_past_range_days(self):
        expected_result = td(days=5)
        result = self.calc._Calc__parse_past_range("5d")  # pylint: disable=W0212

        self.assertEqual(result, expected_result)

    def test_parse_past_range_years(self):
        expected_result = td(days=365)
        result = self.calc._Calc__parse_past_range("1y")  # pylint: disable=W0212

        self.assertEqual(result, expected_result)

    def test_parse_past_range_months(self):
        expected_result = td(days=28)
        result = self.calc._Calc__parse_past_range("1m")  # pylint: disable=W0212

        self.assertEqual(result, expected_result)

    def test_parse_past_range_weeks(self):
        expected_result = td(weeks=2)
        result = self.calc._Calc__parse_past_range("2w")  # pylint: disable=W0212

        self.assertEqual(result, expected_result)

    def test_parse_past_range_invalid(self):
        expected_result = td()
        result = self.calc._Calc__parse_past_range("invalid")  # pylint: disable=W0212

        self.assertEqual(result, expected_result)
