#!/usr/bin/env python3

# standard imports
import atexit
import json
import logging
import logging.config
import logging.handlers
import os
import pathlib

from datetime import datetime as dt

# first party imports
from utilities.config import load_config
from utilities import DataCleaner
from utilities import QueryManager
from utilities import Query
from utilities import QuerySplitter
from utilities.semaphore import ThreadManager
from utilities.query_management import calc

logger = logging.getLogger("alertmagnet")

CONFIG = load_config("config/config.cfg")


def setup_logging():
    file = pathlib.Path("config/logging.conf")
    with open(file=file, mode="r", encoding="utf-8") as f:
        config = json.load(f)

    if CONFIG["toggle_logging"]:
        if not os.path.exists("logs"):
            os.makedirs("logs")
    else:
        config["handlers"].pop("jsonFile")
        config["handlers"].pop("logFile")
        config["handlers"]["queue_handler"]["handlers"].remove("jsonFile")
        config["handlers"]["queue_handler"]["handlers"].remove("logFile")

    logging.config.dictConfig(config=config)
    logging.getLogger().setLevel(CONFIG["log_level"])  # adjusting root logger instead of local one

    queue_handler = logging.getHandlerByName("queue_handler")

    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)

    logger.info("Logging setup completed.")


def main(
    api_endpoint: str = None,
    cert: str = None,
    timeout: int = None,
    kwargs: dict = None,
    directory_path: str = None,
    threshold: int = None,
    delay: float = None,
    threads: int = None,
    max_long_term_storage: str = None,
    **kkwargs  # additional unused keyword arguments for logging purposes
):
    start = dt.now()
    if kwargs is None:
        kwargs = {}

    tm = ThreadManager(semaphore_count=threads, delay=delay)
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
            if index == 1:
                dc.clear_query_results(path=paths[index], step=3600)
                continue

            dc.clear_query_results(path=paths[index], step=60)

    end = dt.now()
    logger.info("Cleaning data lastet: %s seconds.", (end - start))


if __name__ == "__main__":
    setup_logging()
    main(**CONFIG)
