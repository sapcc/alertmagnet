"""
This module provides utilities for filtering alert data from JSON files.

Functions:
    filtering(path: str) -> dict:
        Main function to filter alert data. Reads data from a JSON file, filters it,
        and writes the filtered data back to a JSON file. Returns the filtered data.
"""

import json
import os


def __get_data(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path {path} does not exist.")

    file = os.path.join(path, "finalData.json")

    with open(file=file, mode="r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def __filter_data(data: list):
    out = {}
    for alert in data:
        if alert["metric"]["alertstate"] == "pending":
            continue

        cluster = alert["metric"]["cluster"]
        alert_name = alert["metric"]["alertname"]
        index_cluster = out.get(cluster, -1)
        index_alert = out.get(alert_name, -1)

        if index_cluster == -1:
            out[cluster] = {}

        if index_alert == -1:
            out[cluster][alert_name] = []

        out[cluster][alert_name].extend(alert["values"])

    return out


def __write_data(data: dict, path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path {path} does not exist.")

    file = os.path.join(path, "filteredData.json")

    with open(file=file, mode="w", encoding="utf-8") as f:
        f.write(json.dumps(data))


def filtering(path: str):
    """
    Filters data from the given file path.

    This function reads data from the specified file path, filters the data,
    writes the filtered data back to the file, and returns the filtered data.

    Args:
        path (str): The file path from which to read and write data.

    Returns:
        The filtered data.
    """
    data = __get_data(path)
    filtered_data = __filter_data(data)
    __write_data(filtered_data, path)

    return filtered_data
