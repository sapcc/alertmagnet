"""
Module: correlation_analyzer

This module provides the CorrelationAnalyzer class, which is used to analyze correlations between alert samples over time. 
It includes methods to calculate correlation coefficient matrices, collect alert samples, and process data for correlation analysis.

Classes:
    CorrelationAnalyzer: A class to analyze correlations between alert samples.

Functions:
    calc_corrcoefficient_matrix(data: dict, start: float, end: float): Calculates the correlation coefficient matrix for the given data.
    get_time_samples(start: float, end: float, alert_key: str, alert_value: list, __store: dict): Collects time samples for a specific alert.
    collect_alert_samples(data: dict, start: float, end: float): Collects alert samples and processes them for correlation analysis.
    __sort_data(data: list): Sorts the given data based on the first element of each sublist.
    create_time_samples_per_time(data: list, start: float, end: float): Creates time samples for the given data within the specified time range.
    __create_coefficient_matrix(): Creates the correlation coefficient matrix.
    __calc_corrcoefficient_per_cluster(cluster_name: str): Calculates the correlation coefficient for a specific cluster.
    __calc_matrix_results(): Calculates the final results for the correlation matrix.
    get_data(path: str): Loads data from a specified file path.

"""

import json
import logging
import os
import time as t

from threading import BoundedSemaphore, Thread

import pandas as pd

logger = logging.getLogger("alertmagnet")


class CorrelationAnalyzer(object):
    """
    A class to analyze correlation coefficients between alert samples.

    Attributes:
        semaphore (BoundedSemaphore): A semaphore to limit the number of concurrent threads.
        gap (int): The time gap between samples.
        alerts (list): A list to store alert keys.
        matrix (list): A list to store the correlation coefficient matrix.
        data_matrix (dict): A dictionary to store the data matrix for each cluster.

    Methods:
        calc_corrcoefficient_matrix(data: dict, start: float, end: float):
            Calculates the correlation coefficient matrix for the given data within the specified time range.

        get_time_samples(start: float, end: float, alert_key: str, alert_value: list, __store: dict):
            Collects time samples for a specific alert within the specified time range and stores them in the provided dictionary.

        collect_alert_samples(data: dict, start: float, end: float):
            Collects alert samples from the given data within the specified time range and stores them in the data matrix.

        __sort_data(data: list):
            Sorts the given data based on the start time of each alert.

        create_time_samples_per_time(data: list, start: float, end: float):
            Creates time samples for the given data within the specified time range.

        __create_coefficient_matrix():
            Creates the initial correlation coefficient matrix and starts the calculation for each cluster.

        __calc_corrcoefficient_per_cluster(cluster_name: str):
            Calculates the correlation coefficient for each pair of alerts within the specified cluster.

        __calc_matrix_results():
            Calculates the final correlation coefficient results for the matrix.

        get_data(path: str):
            Loads and returns the data from the specified path.
    """

    def __init__(self, cores: int = 80, gap: int = 60):
        self.semaphore = BoundedSemaphore(cores)
        self.gap = gap

        self.alerts = []
        self.matrix = []
        self.data_matrix = {}

    def calc_corrcoefficient_matrix(self, data: dict, start: float, end: float):
        """
        Calculate the correlation coefficient matrix for the given data within the specified time range.

        This method collects alert samples from the provided data between the start and end times,
        creates a coefficient matrix, and calculates the matrix results.

        Args:
            data (dict): The input data containing alert samples.
            start (float): The start time for collecting alert samples.
            end (float): The end time for collecting alert samples.

        Returns:
            None
        """
        self.collect_alert_samples(data=data, start=start, end=end)
        self.__create_coefficient_matrix()
        self.__calc_matrix_results()

    def __get_time_samples(self, start: float, end: float, alert_key: str, alert_value: list, __store: dict):
        if not alert_key in self.alerts:
            self.alerts.append(alert_key)

        sorted_ranges = self.__sort_data(data=alert_value)
        samples = pd.DataFrame(self.__create_time_samples_per_time(data=sorted_ranges, start=start, end=end))

        __store[alert_key] = samples

    def collect_alert_samples(self, data: dict, start: float, end: float):
        print("Creating time samples")
        start_tt = t.time()

        for cluster_key, cluster_value in data.items():
            print(f"Processing cluster: {cluster_key}")
            __store = {}
            threads = []
            for alert_key, alert_value in cluster_value.items():
                threads.append(
                    Thread(target=self.__get_time_samples, args=(start, end, alert_key, alert_value, __store))
                )

            for thread in threads:
                with self.semaphore:
                    thread.start()

            for thread in threads:
                thread.join()

            self.data_matrix[cluster_key] = pd.concat(__store, axis=1)
            print(len(self.data_matrix[cluster_key].columns))

        end_tt = t.time()
        logger.info("Creating time samples took: %s", end_tt - start_tt)
        logger.info("Sorting alerts")
        self.alerts.sort()
        logger.info("Finished sorting alerts")

    def __sort_data(self, data: list):
        max_length = len(data)
        out = []

        while len(out) < max_length:
            min_value = data[0][0]
            min_index = 0
            for index, value in enumerate(data):
                if value[0] < min_value:
                    min_value = value[0]
                    min_index = index

            out.append(data[min_index])
            data.pop(min_index)

        return out

    def __create_time_samples_per_time(self, data: list, start: float, end: float):
        samples = []

        for time_pair in data:
            if start > end:
                break

            alert_start = time_pair[0]
            alert_duration = time_pair[1]

            if start <= alert_start:
                null_samples = (alert_start - start) // self.gap
                if start != alert_start and alert_start - null_samples * self.gap != start:
                    null_samples += 1

                for _ in range(int(null_samples)):
                    if not start + self.gap < end:
                        break

                    samples.append(0)
                    start += self.gap

            if alert_start + alert_duration * self.gap >= start:
                one_samples = ((alert_start + alert_duration) - start) // self.gap
                one_samples += 1
                for _ in range(int(one_samples)):
                    if not start + self.gap < end:
                        break

                    samples.append(1)
                    start += self.gap

        null_samples = (end - start) // self.gap
        null_samples += 1

        for _ in range(int(null_samples)):
            if not start + self.gap < end + self.gap:
                break

            samples.append(0)
            start += self.gap

        if end == start:
            samples.append(0)

        return samples

    def __create_coefficient_matrix(self):
        logger.info("Calculating correlation")

        start_tc = t.time()

        for _ in self.alerts:
            self.matrix.append([[0, 0] for _ in self.alerts])

        threads = []

        for cluster in self.data_matrix:
            threads.append(Thread(target=self.__calc_corrcoefficient_per_cluster, args=(cluster,)))

        for thread in threads:
            with self.semaphore:
                thread.start()

        for thread in threads:
            thread.join()

        end_tc = t.time()

        logger.info("Calculating correlation took: %s", end_tc - start_tc)

    def __calc_corrcoefficient_per_cluster(self, cluster_name: str):
        logger.info("Processing cluster: %s", cluster_name)
        cluster = self.data_matrix[cluster_name]
        indent = 1
        for alert_1 in cluster:
            for alert_2 in cluster[indent:]:
                res = cluster[alert_1].corr(cluster[alert_2])

                if str(res) == "nan":
                    res = 0

                self.matrix[self.alerts.index(alert_1[0])][self.alerts.index(alert_2[0])][0] += float(res)
                self.matrix[self.alerts.index(alert_1[0])][self.alerts.index(alert_2[0])][1] += 1

            indent += 1

        logger.info("Finished cluster: %s", cluster_name)

    def __calc_matrix_results(self):
        logger.info("Calculating matrix results")
        for index1, value1 in enumerate(self.matrix):
            for index2, value2 in enumerate(value1):
                if value2[1] == 0:
                    self.matrix[index1][index2] = 0
                    continue

                self.matrix[index1][index2] = value2[0] / value2[1]

        logger.info("Finished calculating matrix results")

    """def get_data(self, path: str):
        if not os.path.exists(path):
            logger.error("FileNotFoundError: Path %s does not exist.", path)
            raise FileNotFoundError(f"Path {path} does not exist.")

        file = os.path.join(path, "filteredData.json")

        with open(file=file, mode="r", encoding="utf-8") as f:
            data = json.load(f)

        return data"""
