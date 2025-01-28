#!/usr/bin/env python3

# standard imports
import os
import sys

from datetime import datetime as dt

# third party imports
import click

# first party imports
from utilities import DataCleaner
from utilities import QueryManager
from utilities import Query
from utilities import QuerySplitter
from utilities.semaphore import ThreadManager


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
    help="timeout after which the request aborts automatically",
    show_default=True,
    type=int,
)
@click.option(
    "-k",
    "--kwargs",
    default=None,
    help="parameters for the query; supported keys: target, params\ntarget > specifies a target behind the api endpoint\nparams > sets specific parameters for the query; supported parameters are: 'query', 'dedup', 'partial_response', 'step', 'max_source_resolution', 'engine', 'analyze'",
)
@click.option("-p", "--storage-path", default=None, help="Storage path the store the query results")
@click.option(
    "-b",
    "--threshold",
    default=None,
    help="Threshold to split queries due to efficiency and resource optimization",
    type=int,
)
# option for max long term storage
def main(
    api_endpoint: str = None,
    cert: str = None,
    timeout: int = 30,
    kwargs: dict = None,
    storage_path: str = None,
    threshold: int = None,
):
    start = dt.now()
    if api_endpoint is None:
        print("Please parse a value to the flag --api-endpoint.")
        sys.exit(os.EX_USAGE)

    if kwargs is None:
        kwargs = {}

    tm = ThreadManager(12)
    qm = QueryManager(cert=cert, timeout=timeout, storage_path=storage_path, threshold=threshold, thread_manager=tm)

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
    print(f"Downloading data lastet: {(end - start)} seconds.")

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
                dc.clear_query_results(path=paths[0], step=3600)
                continue

            dc.clear_query_results(path=paths[0], step=60)

    end = dt.now()
    print(f"Cleaning data lastet: {(end - start)} seconds.")


if __name__ == "__main__":
    main()
    print("finished…")
