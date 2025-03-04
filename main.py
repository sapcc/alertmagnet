#!/usr/bin/env python3

# standard imports
import atexit
import json
import logging
import logging.config
import logging.handlers
import os
import pathlib
import time

from datetime import datetime as dt
from threading import Thread

# first party imports
from analyzing import analyzer
from filtering import DataCleaner
from presenting.metrics import Exporter
from querying import QueryManager
from querying import Query
from querying import QuerySplitter
from querying.query_management import calc
from utilities import config
from utilities.semaphore import ThreadManager

logger = logging.getLogger("alertmagnet")

CONFIG: dict[str, str] = {}


def load_config():
    env = os.getenv("ALERTMAGNET_CONFIG_FILE", "-1")
    if env != "-1":
        print("Using config file from environment variable.")
        config_file = env
    else:
        print("Using default config file.")
        config_file = "config/settings.conf"

    CONFIG.update(config.load_config(config_file=config_file))


def setup_logging():
    file = pathlib.Path("config/logging.conf")
    with open(file=file, mode="r", encoding="utf-8") as f:
        log_config = json.load(f)

    if CONFIG["log_to_file"]:
        if not os.path.exists("logs"):
            os.makedirs("logs")
    else:
        log_config["handlers"].pop("jsonFile")
        log_config["handlers"].pop("logFile")
        log_config["handlers"]["queue_handler"]["handlers"].remove("jsonFile")
        log_config["handlers"]["queue_handler"]["handlers"].remove("logFile")

    logging.config.dictConfig(config=log_config)
    logging.getLogger().setLevel(CONFIG["log_level"])  # adjusting root logger instead of local one

    queue_handler = logging.getHandlerByName("queue_handler")

    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)

    logger.info("Logging setup completed.")


def do_analysis(
    api_endpoint: str = None,
    cert: str = None,
    timeout: int = None,
    kwargs: dict = None,
    directory_path: str = None,
    threshold: int = None,
    delay: float = None,
    cores: int = None,
    max_long_term_storage: str = None,
    **kkwargs  # additional unused keyword arguments for logging purposes
):
    start = dt.now()

    tm = ThreadManager(semaphore_count=cores, delay=delay)
    qm = QueryManager(cert=cert, timeout=timeout, directory_path=directory_path, threshold=threshold, thread_manager=tm)

    calc.set_max_long_term(max_long_term_storage)

    query = Query(base_url=api_endpoint)

    queries = QuerySplitter.split_by_treshold(QuerySplitter(), query=query, threshold=threshold)

    query_uuids = [qm.add_query_queue() for i in range(len(queries))]

    if not queries[0] is None:
        qm.create_query_objects(query_queue_uuid=query_uuids[0], query=queries[0], separator=60 * 60 * 24)

    if not queries[1] is None:
        qm.create_query_objects(query_queue_uuid=query_uuids[1], query=queries[1], separator=60 * 60 * 24 * 90)

    qm.create_environments()

    for query_uuid in query_uuids:
        if len(qm.queues[query_uuid].query_objects) == 0:
            continue
        qm.queues[query_uuid].schedule_queries()

    logger.info("Starting to download data.")
    tm.execute_all_threads()
    end = dt.now()
    logger.info("Downloading data lastet: %s seconds.", (end - start))

    start = dt.now()

    max_index = 2
    paths = [None for i in range(max_index)]
    dc = DataCleaner()

    for index in range(max_index):
        query_uuid = query_uuids[index]

        if not len(qm.queues[query_uuid].query_objects) == 0:
            queue = qm.queues[query_uuid]
            paths[index] = queue.path

        if not paths[index] is None:
            try:
                step = queries[index].kwargs["params"]["step"]
            except KeyError:
                step = 60

            dc.clear_query_results(path=paths[index], step=step)

    end = dt.now()
    logger.info("Cleaning data lastet: %s seconds.", (end - start))

    logger.info("Starting to analyze data.")
    start = dt.now()

    for path in paths:
        if path is None:
            continue
        analyzer.get_mean_duration_per_alertname(path=path)

    end = dt.now()
    logger.info("Analyzing data lastet: %s seconds.", (end - start))

    for index_path, path in enumerate(paths[0:1]):
        filtered_data = analyzer.group_alert_timeseries_per_cluster(path=path)
        start_tt = queries[index_path].global_start
        end_tt = queries[index_path].global_end
        correlated_data = analyzer.correlate_data(
            path=path,
            result=filtered_data,
            gap=60,
            cores=cores,
            start_tt=start_tt,
            end_tt=end_tt,
        )
        analyzer.create_alert_corrrelation_list(
            path=path, alerts=correlated_data["alert_index"], matrix=correlated_data["corrcoef_matrix"]
        )

    return paths


def main(
    api_endpoint: str = None,
    cert: str = None,
    timeout: int = None,
    kwargs: dict = None,
    directory_path: str = None,
    threshold: int = None,
    delay: float = None,
    cores: int = None,
    max_long_term_storage: str = None,
    prometheus_port: int = None,
    **kkwargs  # additional unused keyword arguments for logging purposes
):
    logger.debug("Starting main function with config: %s", CONFIG)

    if kwargs is None:
        kwargs = {}

    e = Exporter(prometheus_port=prometheus_port, paths=[])
    exporter_thread = Thread(target=e.start_server)
    exporter_thread.start()

    to_be_removed_directories = []

    while True:
        paths = do_analysis(
            api_endpoint=api_endpoint,
            cert=cert,
            timeout=timeout,
            kwargs=kwargs,
            directory_path=directory_path,
            threshold=threshold,
            delay=delay,
            cores=cores,
            max_long_term_storage=max_long_term_storage,
        )

        e.paths = paths[0:1]

        time.sleep(60 * 60 * 24)

        to_be_removed_directories.extend(paths)

        if len(to_be_removed_directories) > 2:
            for path in to_be_removed_directories[:-2]:
                if os.path.exists(path):
                    os.remove(path)

                to_be_removed_directories.remove(path)


if __name__ == "__main__":
    load_config()
    setup_logging()
    main(**CONFIG)
