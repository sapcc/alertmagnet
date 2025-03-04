"""
This module provides functions to filter data, perform correlation analysis, and generate a list of correlating alerts.

Functions:
    filter_data(path: str) -> dict:
        Filters data from the given path and returns the filtered data as a dictionary.
        If the filtered data already exists in a file, it loads and returns the data from the file.

    correlate_data(path: str, result: dict, gap: int) -> dict:
        Performs correlation analysis on the filtered data and returns the correlation coefficient matrix and alert index.
        If the correlation data already exists in a file, it loads and returns the data from the file.

    create_alert_corrrelation_list(path: str, alerts: list, matrix: dict) -> dict:
        Creates a list of correlating alerts based on the correlation coefficient matrix and saves it to a file.
        Returns the alert correlation list as a dictionary.

    get_correlating_alerts(path: str, gap: int) -> list:
        Filters data, performs correlation analysis, and generates a list of correlating alerts.
        Returns the alert correlation list.
"""

import json
import logging
import os

from datetime import datetime as dt

from analyzing import filtering, CorrelationAnalyzer, get_mean_duration_per_alertname

logger = logging.getLogger("alertmagnet")


def group_alert_timeseries_per_cluster(path: str) -> dict:
    """
    Filters data from the given path and returns the result as a dictionary.

    If a file named "filteredData.json" exists in the specified path, the function
    reads and returns its contents. Otherwise, it performs the filtering process,
    logs the time taken, and returns the filtered data.

    Args:
        path (str): The path to the directory containing the data to be filtered.

    Returns:
        dict: The filtered data as a dictionary.
    """
    if os.path.exists(os.path.join(path, "filteredData.json")):
        with open(file=os.path.join(path, "filteredData.json"), mode="r", encoding="utf-8") as f:
            return json.load(f)

    logger.info("Starting filtering …")
    start = dt.now()
    result = filtering(path=path)
    end = dt.now()
    logger.info("Time taken: %s", end - start)

    return result


def correlate_data(path: str, result: dict, gap: int, cores: int, start_tt: float, end_tt: float) -> dict:
    """
    Calculate or load the correlation coefficient matrix for the given data.

    This function checks if a precomputed correlation coefficient matrix exists in the specified path.
    If it does not exist, it calculates the matrix using the provided data and saves it to a JSON file.
    If it exists, it loads the matrix from the JSON file.

    Args:
        path (str): The directory path where the correlation coefficient matrix JSON file is stored or will be saved.
        result (dict): The data for which the correlation coefficient matrix is to be calculated.
        gap (int): The gap parameter used in the correlation analysis.

    Returns:
        dict: A dictionary containing the alert index and the correlation coefficient matrix.
    """
    if not os.path.exists(os.path.join(path, "corrcoefficient_matrix.json")):
        logger.info("Starting correlation …")
        start = dt.now()
        ca = CorrelationAnalyzer(cores=cores, gap=gap)
        ca.calc_corrcoefficient_matrix(data=result, start=start_tt, end=end_tt)
        end = dt.now()
        logger.info("Time taken: %s", end - start)

        data = {"alert_index": ca.alerts, "corrcoef_matrix": ca.matrix}

        with open(file=os.path.join(path, "corrcoefficient_matrix.json"), mode="w", encoding="utf-8") as f:
            f.write(json.dumps(data))

        return data

    with open(file=os.path.join(path, "corrcoefficient_matrix.json"), mode="r", encoding="utf-8") as f:
        return json.load(f)


def create_alert_corrrelation_list(path: str, alerts: list, matrix: dict) -> dict:
    """
    Creates a dictionary of alert correlations and writes it to a JSON file.

    This function takes a list of alerts and a correlation matrix, and generates a dictionary
    where each alert is mapped to a list of other alerts that have a correlation value greater
    than 0.7. The resulting dictionary is then written to a JSON file at the specified path.

    Args:
        path (str): The file path where the JSON file will be saved.
        alerts (list): A list of alert names.
        matrix (dict): A dictionary representing the correlation matrix, where each key is an
                       index of an alert and the value is a list of correlation values with other alerts.

    Returns:
        dict: A dictionary where each key is an alert and the value is a list of correlated alerts.
    """
    alert_correlation = {}

    for index_alert, alert in enumerate(alerts):
        alert_correlation[alert] = {}
        for index_corr, corr in enumerate(matrix[index_alert]):
            if index_alert == index_corr:
                continue

            if corr >= 0.0:
                alert_correlation[alert][alerts[index_corr]] = corr

    with open(file=os.path.join(path, "correlating_alerts.json"), mode="w", encoding="utf-8") as f:
        f.write(json.dumps(alert_correlation))

    return alert_correlation


def get_correlating_alerts(path: str, gap: int, cores: int, start_tt: float, end_tt: float) -> list:
    """
    Analyzes alert data from a given file path and returns a list of correlating alerts.

    This function performs the following steps:
    1. Filters the data from the specified file path.
    2. Correlates the filtered data based on the provided gap.
    3. Creates a list of alert correlations using the correlated data.

    Args:
        path (str): The file path to the alert data.
        gap (int): The gap parameter used for correlating the data.

    Returns:
        list: A list of correlating alerts.
    """
    filtered_data = group_alert_timeseries_per_cluster(path=path)
    correlated_data = correlate_data(
        path=path, result=filtered_data, gap=gap, cores=cores, start_tt=start_tt, end_tt=end_tt
    )
    correlation_list = create_alert_corrrelation_list(
        path=path, alerts=correlated_data["alert_index"], matrix=correlated_data["corrcoef_matrix"]
    )

    return correlation_list


def get_alert_durations(path: str) -> dict:
    """
    Calculate the mean duration for each alert name from the data in the given file path.

    Args:
        path (str): The file path to the data source containing alert information.

    Returns:
        dict: A dictionary where the keys are alert names and the values are the mean durations of those alerts.
    """
    return get_mean_duration_per_alertname(path=path)
