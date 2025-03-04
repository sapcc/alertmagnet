"""
This module provides a Prometheus exporter for alert metrics.

Classes:
    Exporter: A class to export alert metrics to Prometheus.

Functions:
    __init__(self, **kwargs): Initializes the Exporter with the given parameters.
    start_server(self): Starts the Prometheus HTTP server and updates metrics periodically.
    update_alertmagnet_important_true_metrics(self): Updates the 'alertmagnet_important_true' metric from JSON files.
    update_alertmagnet_correlation_coefficient_metrics(self): Updates the 'alertmagnet_correlation_coefficient' metric from JSON files.
"""

import json
import logging
import os


from prometheus_client import start_http_server
from prometheus_client.core import Gauge, Counter

logger = logging.getLogger("alertmagnet")


class Exporter(object):
    """
    A class to export Prometheus metrics for alert management.

    Attributes:
        port (int): The port on which the Prometheus exporter will run.
        paths (list): A list of paths to directories containing alert data files.
        metrics (dict): A dictionary of Prometheus Gauge metrics.
        last_changed (dict): A dictionary to track the last modification time of alert data files.

    Methods:
        start_server():
            Starts the Prometheus exporter server and periodically updates metrics.

        update_alertmagnet_important_true_metrics():
            Updates the 'alertmagnet_important_true' metric based on the data in 'alertMeanDurations.json' files.

        update_alertmagnet_correlation_coefficient_metrics():
            Updates the 'alertmagnet_correlation_coefficient' metric based on the data in 'correlating_alerts.json' files.
    """

    def __init__(self, **kwargs):
        self.port = kwargs["prometheus_port"]
        self.paths = kwargs["paths"]
        self.metrics = {
            "alertmagnet_important_true": Gauge(
                "alertmagnet_important_true",
                "Indicates whether an alert is important (1) or unimportant (0)",
                labelnames=["alertname"],
            ),
            "alertmagnet_correlation_coefficient": Gauge(
                "alertmagnet_correlation_coefficient",
                "Correlation coefficient of an alert",
                labelnames=["alertname", "correlating_alert"],
            ),
            "alertmagnet_analyzing_count": Counter(
                "alertmagnet_analyzing_count",
                "Number of alerts being analyzed",
            ),
        }
        self.last_changed = {
            "alertmagnet_important_true": 0,
            "alertmagnet_correlation_coefficient": 0,
        }

    def start_server(self):
        """
        Starts the Prometheus exporter server on the specified port and continuously updates metrics.

        This method initializes the Prometheus HTTP server on the port specified by `self.port`.
        It then enters an infinite loop where it logs the update process, updates specific metrics,
        and sleeps for 60 seconds before repeating the process.

        Metrics updated:
        - alertmagnet_important_true_metrics
        - alertmagnet_correlation_coefficient_metrics

        Logging:
        - Logs the start of the Prometheus exporter server.
        - Logs each update cycle of the metrics.

        Note:
        This method runs indefinitely and should be run in a separate thread or process to avoid blocking.
        """
        logger.info("Starting Prometheus exporter on port %s", self.port)
        start_http_server(self.port)
        self.update_metrics()

    def update_metrics(self):
        """
        Updates various metrics for the alert magnet system.

        This method logs the start of the metrics update process and then
        calls the following methods to update specific metrics:
        - update_alertmagnet_important_true_metrics: Updates metrics related to important true alerts.
        - update_alertmagnet_correlation_coefficient_metrics: Updates metrics related to correlation coefficients.
        """
        logger.info("Updating metrics")
        self.update_alertmagnet_important_true_metrics()
        self.update_alertmagnet_correlation_coefficient_metrics()

    def update_alertmagnet_important_true_metrics(self):
        """
        Updates the 'alertmagnet_important_true' metrics by reading the 'alertMeanDurations.json' file
        from each path in self.paths. If the file has been modified since the last update, it reads
        the JSON data and updates the corresponding metrics.

        Returns:
            None
        """
        for path in self.paths:
            file = os.path.join(path, "alertMeanDurations.json")

            if not os.path.isfile(path=file):
                return

            if os.path.getmtime(file) == self.last_changed["alertmagnet_important_true"]:
                return

            with open(file=file, mode="r", encoding="utf-8") as f:
                data = json.load(f)

            for alert, value in data.items():
                g = self.metrics["alertmagnet_important_true"]
                g.labels(alertname=alert).set(value)

    def update_alertmagnet_correlation_coefficient_metrics(self):
        """
        Updates the alertmagnet correlation coefficient metrics.

        This method iterates through the paths specified in `self.paths`, checks for the presence of
        a file named "correlating_alerts.json", and updates the correlation coefficient metrics if
        the file has been modified since the last update.

        The method performs the following steps:
        1. Constructs the file path for "correlating_alerts.json".
        2. Checks if the file exists. If not, the method returns.
        3. Compares the file's last modification time with the stored last change time for
           "alertmagnet_correlation_coefficient". If they are the same, the method returns early.
        4. Opens and reads the JSON data from the file.
        5. Iterates through the alerts and their corresponding correlation values.
        6. Updates the metrics for each alert and its correlating alerts using the provided values.

        Returns:
            None
        """
        for path in self.paths:
            file = os.path.join(path, "correlating_alerts.json")

            if not os.path.isfile(path=file):
                return

            if os.path.getmtime(file) == self.last_changed["alertmagnet_correlation_coefficient"]:
                return

            with open(file=file, mode="r", encoding="utf-8") as f:
                data = json.load(f)

            for alert, values in data.items():
                for correlating_alert, value in values.items():
                    g = self.metrics["alertmagnet_correlation_coefficient"]
                    g.labels(alertname=alert, correlating_alert=correlating_alert).set(value)

    def increase_alertmagnet_analyzing_count(self):
        """
        Increases the 'alertmagnet_analyzing_count' metric by 1.

        This method increments the 'alertmagnet_analyzing_count' metric by 1.

        Returns:
            None
        """
        self.metrics["alertmagnet_analyzing_count"].inc()
