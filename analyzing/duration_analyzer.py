"""
This module provides functionality to analyze alert durations from JSON data.

Functions:
    __get_queried_data_from_json(path: str) -> dict:
        Reads JSON data from a file and returns it as a dictionary.
        Args:
            path (str): The directory path where the JSON file is located.
        Returns:
            dict: The JSON data loaded from the file.
        Raises:
            FileNotFoundError: If the JSON file does not exist.

    __calc_mean_duration_per_alertname(results: dict) -> dict:
        Calculates the mean duration for each alert name from the given results.
        Args:
            results (dict): The dictionary containing alert data.
        Returns:
            dict: A dictionary with alert names as keys and their mean durations as values.

    __write_calculated_data_to_json(data: dict, out: str):
        Writes the given data to a JSON file.
        Args:
            data (dict): The data to be written to the file.
            out (str): The output file path.

    get_mean_duration_per_alertname(path: str, out: str) -> dict:
        Main function to get the mean duration per alert name and write the results to a file.
        Args:
            path (str): The directory path where the input JSON file is located.
            out (str): The output file path where the results will be written.
        Returns:
            dict: A dictionary with alert names as keys and their mean durations as values.
"""

import json
import logging
import os

logger = logging.getLogger("alertmagnet")


def __get_queried_data_from_json(path: str):
    filename = os.path.join(path, "finalData.json")

    if not os.path.exists(filename):
        logger.error("FileNotFoundError: File %s does not exist.", filename)
        raise FileNotFoundError(f"File {filename} does not exist.")

    with open(file=filename, mode="r", encoding="utf-8") as f:
        results = json.load(f)

    return results


def __calc_mean_duration_per_alertname(results: dict):
    alerts = {}

    for result in results:
        if not result["metric"]["alertname"] in alerts:
            alerts[result["metric"]["alertname"]] = []

        for value_pair in result["values"]:
            alerts[result["metric"]["alertname"]].append(value_pair[1])

    for alertname, durations in alerts.items():
        mean = sum(durations) / len(durations)
        alerts[alertname] = mean

    return alerts


def __write_calculated_data_to_json(data: dict, path: str):
    out = os.path.join(path, "alertMeanDurations.json")

    with open(file=out, mode="w", encoding="utf-8") as f:
        f.write(json.dumps(data))


def get_mean_duration_per_alertname(path: str):
    """
    Calculate the mean duration per alert name from the data at the given path and write the results to the specified output file.

    Args:
        path (str): The file path to the input data.
        out (str): The file path to write the output data.

    Returns:
        dict: A dictionary containing the mean duration per alert name.
    """
    data = __get_queried_data_from_json(path=path)
    results = __calc_mean_duration_per_alertname(results=data)
    __write_calculated_data_to_json(data=results, path=path)

    return results
