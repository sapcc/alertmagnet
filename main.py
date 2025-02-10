#!/usr/bin/env python3

# standard imports
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
# TODO: add possible option for max long term storage, currently fixed at 5y
def main(
    api_endpoint: str = None,
    cert: str = None,
    timeout: int = 30,
    kwargs: dict = None,
    directory_path: str = None,
    threshold: int = None,
):
    start = dt.now()
    if kwargs is None:
        kwargs = {}

    tm = ThreadManager(12)
    qm = QueryManager(cert=cert, timeout=timeout, storage_path=directory_path, threshold=threshold, thread_manager=tm)

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
                dc.clear_query_results(path=paths[index], step=3600)
                continue

            dc.clear_query_results(path=paths[index], step=60)

    end = dt.now()
    print(f"Cleaning data lastet: {(end - start)} seconds.")


if __name__ == "__main__":
    main()
    print("finished…")
