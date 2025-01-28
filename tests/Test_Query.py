import unittest
from datetime import datetime as dt
from datetime import timedelta as td

# from unittest.mock import MagicMock
from utilities import Query

API_ENDPOINT = "https://metrics-internal.qa-de-1.cloud.sap/api/v1/"


class TestQuery(unittest.TestCase):
    def test_get_alert_request_data(self):
        base_url = API_ENDPOINT
        now = dt.now()
        start = str(now.timestamp())
        end = str((now - td(hours=5)).timestamp())
        kwargs = {"params": {"step": "3600"}}
        query = Query(base_url=base_url, start=start, end=end, kwargs=kwargs)
        result = query.get_alert_request_data(start=start, end=end)
        target = "query_range"
        params = {
            "query": "ALERTS",
            "dedup": "true",
            "partial_response": "false",
            "start": start,
            "end": end,
            "step": "3600",
            "max_source_resolution": "0s",
            "engine": "thanos",
            "analyze": "false",
        }
        expected_result = {"target": target, "params": params}
        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
