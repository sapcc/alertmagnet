#!/usr/bin/env python3

# standard imports
import atexit
import json
import logging
import logging.config
import logging.handlers
import pathlib

from datetime import datetime as dt

# third party imports
import click

# first party imports
from utilities import DataCleaner
from utilities import QueryManager
from utilities import Query
from utilities import QuerySplitter
from utilities.semaphore import ThreadManager
from utilities.query_management import calc

logger = logging.getLogger("alertmagnet")


def setup_logging():
    file = pathlib.Path("config/logging.conf")
    with open(file=file, mode="r", encoding="utf-8") as f:
        config = f.read()

    logging.config.dictConfig(json.loads(config))

    queue_handler = logging.getHandlerByName("queue_handler")

    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)

    logging.basicConfig(level="INFO")


@click.command()
@click.option("-a", "--api-endpoint", default=None, required=True, help="api endpoint to query against")
@click.option(
    "-c",
    "--cert",
    default=None,
    help="relative path to the certificate which is used to create the request",
)
@click.option(
    "-t",
    "--timeout",
    default=30,
    help="number of seconds the client will wait for the server to send a response",
    show_default=True,
    type=int,
)
@click.option(
    "-k",
    "--kwargs",
    default=None,
    help="parameters for the query; supported keys: target, params\ntarget > specifies a target behind the api endpoint\nparams > sets specific parameters for the query\n\tsupported parameters are:\n\t - 'query'\n\t - 'dedup'\n\t - 'partial_response'\n\t - 'step'\n\t - 'max_source_resolution'\n\t - 'engine'\n\t - 'analyze'",
)
@click.option("-p", "--directory-path", default=None, help="directory path in which the query results are stored")
@click.option(
    "-b",
    "--threshold",
    default=None,
    help="Threshold in days which specifies when the data are interpolated by Thanos\nThis helps splitting the queries due to efficiency and resource optimization",
    type=int,
)
@click.option(
    "-d",
    "--delay",
    default=0.25,
    help="Delay in seconds between each query execution",
    type=float,
)
@click.option(
    "-x",
    "--threads",
    default=12,
    help="Maximum number of threads to use for query execution",
    show_default=True,
    type=int,
)
@click.option(
    "-y",
    "--max-long-term-storage",
    default="1y",
    help="Maximum long term storage following the format <a>y, <b>m, <c>w, <d>d",
    show_default=True,
    type=str,
)
# TODO: add possible option for max long term storage, currently fixed at 5y
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
    main()
