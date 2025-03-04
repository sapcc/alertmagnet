"""This module contains some default messages for possible responses."""

MESSAGE_EXCEEDED_MAXIMUM = {
    "status": "error",
    "errorType": "bad_data",
    "error": "exceeded maximum resolution of 11,000 points per timeseries. Try decreasing the query resolution (?step=XX)",
}

EMPTY_RESULTS = {"status": "success", "data": {"resultType": "matrix", "result": []}}
