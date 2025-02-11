"""
Module: query_management

This module provides classes and methods for managing and executing queries, handling query results, and managing query queues. It includes functionality for splitting queries, executing them, and storing the results.

Classes:
    QueryExecutor:
        Executes a given query and handles the result. Can split the query if the result exceeds a maximum threshold.

    Query:
        Represents a query with parameters such as base URL, start and end times, and additional keyword arguments. Provides methods to initialize, execute, and set request parameters.

    QueryManager:
        Manages multiple query queues, creates query objects, and sets up environments for query execution.

    QueryObject:
        Represents a single query object within a query queue. Responsible for creating its environment and executing the query.

    QueryQueue:
        Manages a queue of query objects. Creates the environment for the queue and schedules the execution of queries.

    QuerySplitter:
        Provides methods to split queries based on a threshold or a separator.

Functions:
    None

Usage:
    This module is intended to be used for managing and executing large sets of queries, particularly in environments where queries need to be split and executed in parallel. It handles the complexities of query execution, result handling, and error management.

Dependencies:
    - copy
    - json
    - os
    - uuid
    - datetime
    - requests
    - utilities.Calc
    - utilities.errors
    - utilities.data_filter
    - utilities.response_messages
    - utilities.semaphore
    - utilities.helper.ResponseDummy
"""

from __future__ import annotations

import copy
import json
import os
import uuid

from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz

import requests

from utilities import Calc
from utilities import errors
from utilities import data_filter
from utilities import response_messages
from utilities import semaphore
from utilities.helper import ResponseDummy

# TODO add META information to query -> QueryGroup

calc = Calc()


class QueryExecutor:
    """
    A class to manage and execute queries, handle their results, and split queries if necessary.

    Attributes:
        path (str): The file path where query results will be saved.
        query (Query): The current query being executed.
        chunk (int): The chunk number for splitting query results.

    Methods:
        __init__(path: str):
            Initializes the QueryExecutor with a given file path.

        execute_query(query: Query):
            Executes a given query and handles the result.

        reset():
            Resets the query and chunk attributes to their initial state.
    """

    def __init__(self, path: str):
        self.query = None
        self.path = path
        self.chunk = 0

    def execute_query(self, query: Query):
        """
        Executes the given query and handles the result.

        Args:
            query (Query): The query object to be executed.

        Returns:
            None
        """
        self.query = query
        result = query.execute()
        self.__handle_query_result(result=result)

    def reset(self):
        """
        Resets the query and chunk attributes to their initial states.

        This method sets the `query` attribute to None and the `chunk` attribute to 0.
        """
        self.query = None
        self.chunk = 0

    def __handle_query_result(self, result: dict):
        if result["status"] == "success":
            for index, value in enumerate(result["data"]["result"]):
                value["values"] = data_filter.remove_state_from_timestamp_value(value["values"])
                result["data"]["result"][index] = value

            filename = os.path.join(self.path, f"data{self.chunk}.json")

            with open(file=filename, mode="w", encoding="utf-8") as f:
                f.write(json.dumps(result, indent=4))
        elif result == response_messages.MESSAGE_EXCEEDED_MAXIMUM:
            query1, query2 = self.__split_request_by_half(self.query)

            self.execute_query(query=query1)
            self.chunk += 1
            self.execute_query(query=query2)
            self.chunk += 1

        return

    def __split_request_by_half(self, query: Query) -> tuple[Query, Query]:
        start_tt = float(query.global_start)
        end_tt = float(query.global_end)

        time_difference = end_tt - start_tt
        half = time_difference / 2
        mid = end_tt - half

        query1 = copy.deepcopy(query)
        query2 = copy.deepcopy(query)

        query1.global_start = mid
        query2.global_end = mid

        return (query1, query2)


class Query(object):
    """
    A class to manage and execute queries with specified parameters.

    Attributes:
        base_url (str): The base URL for the query.
        global_start (str): The start time for the query.
        global_end (str): The end time for the query.
        kwargs (dict): Additional keyword arguments for the query.
        path (str): The path for the query.
        cert (str): The certificate for the query.
        params (dict): The parameters for the query.
        target (str): The target for the query.
        timeout (int): The timeout for the query.

    Methods:
        initialize():
            Initializes the query parameters.
        execute():
            Executes the query and returns the result.
        set_request_parameters(cert: str = None, timeout: int = None):
            Sets the request parameters for the query.
        set_start(start: str):
            Sets the start time for the query.
        set_end(end: str):
            Sets the end time for the query.
    """

    def __init__(
        self,
        base_url: str = None,
        start: str = None,
        end: str = None,
        kwargs: dict = None,
    ):  # TODO set standard format for start / end -> str | float
        self.path = None

        self.base_url = base_url
        self.global_start = start
        self.global_end = end

        # maybe apply kwargs as kwargs
        self.kwargs = {} if kwargs is None else kwargs

        self.cert = None
        self.params = None
        self.target = None
        self.timeout = None

        self.initialize()

    def initialize(self):
        """
        Initializes the query management by setting the global start and end timestamps.

        This method ensures that the `global_end` and `global_start` attributes have valid values.
        If `global_end` is None, it sets it to the current timestamp.
        If `global_start` is None, it calculates the timestamp for five years ago and sets it.
        Finally, it applies additional request data through the `__parse_request_data` method.
        """
        now = dt.now(tz.utc)

        self.global_end = str(now.timestamp()) if self.global_end is None else self.global_end  # ensures end has value

        if self.global_start is None:  # ensures start has value
            self.global_start = calc.calculate_max_past(now, calc.max_long_term)
            self.global_start = str(self.global_start)

        # apply kwargs values
        self.__parse_request_data()

    def execute(self):
        """
        Executes a request and parses the result.

        This method sends a request using the __execute_request method,
        then parses the response using the __parse_request_result method,
        and returns the parsed result.

        Returns:
            The parsed result of the request.
        """
        response = self.__execute_request()
        result = self.__parse_request_result(response=response)

        return result

    def set_request_parameters(self, cert: str = None, timeout: int = None):
        """
        Sets the request parameters for the query management.

        Args:
            cert (str, optional): The certificate to be used for the request. Defaults to None.
            timeout (int, optional): The timeout duration for the request in seconds. Defaults to None.
        """
        self.cert = cert
        self.timeout = timeout

    # TODO set property
    def set_start(self, start: str):
        """
        Sets the start parameter for the query.

        Args:
            start (str): The start time or date to be set.

        Returns:
            None
        """
        self.global_start = start

        if self.params is None:
            return

        self.params["start"] = start

    # TODO set property
    def set_end(self, end: str):
        """
        Sets the end parameter for the query.

        Args:
            end (str): The end time or date to set for the query.

        Returns:
            None
        """
        self.global_end = end

        if self.params is None:
            return

        self.params["end"] = end

    def __execute_request(self) -> requests.Response:
        base_url = self.base_url
        cert = self.cert
        params = self.params
        target = self.target
        timeout = self.timeout

        url = base_url + target

        for _ in range(3):
            try:
                print(f"starting request… [{dt.fromtimestamp(float(params['start']))}]")  # TODO remove print statements
                res = requests.get(url=url, cert=cert, params=params, timeout=timeout)
                print(f"request finished [{dt.fromtimestamp(float(params['start']))}]")
            except requests.ConnectTimeout as e:
                print("requests.ConnectTimeout:", e)
                continue
            except requests.exceptions.ReadTimeout as e:
                print("requests.exceptions.ReadTimeout:", e)
                return ResponseDummy(response_messages.MESSAGE_EXCEEDED_MAXIMUM)
            except requests.exceptions.SSLError as e:
                print("requests.exceptions.SSLError:", e)
                continue
            except requests.exceptions.ConnectionError as e:
                print("requests.exceptions.ConnectionError:", e)
                continue
            except requests.exceptions.ChunkedEncodingError as e:
                print("requests.exceptions.ChunkedEncodingError:", e)
                return ResponseDummy(response_messages.MESSAGE_EXCEEDED_MAXIMUM)
            except Exception as e:
                raise e
            else:
                return res

        print("safety catch invoked")
        return ResponseDummy(response_messages.EMPTY_RESULTS)

    def __parse_request_result(self, response: requests.Response):
        if response is None:
            return response_messages.EMPTY_RESULTS

        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            # LOGGING
            print("=" * 50)
            print(response.text)
            print("=" * 50)
            return response_messages.EMPTY_RESULTS
        except Exception as e:
            print(f"Exception occured: {e.args}, {e.__traceback__.__str__}")
            return response_messages.EMPTY_RESULTS

        try:
            if data["status"] == "error" and data["errorType"] != "bad_data":
                return response_messages.EMPTY_RESULTS
        except KeyError:
            return response_messages.EMPTY_RESULTS
        else:
            return data

    def __parse_request_data(self):
        start = self.global_start
        end = self.global_end

        valid_query_parameters = (
            "query",
            "dedup",
            "partial_response",
            "step",
            "max_source_resolution",
            "engine",
            "analyze",
        )

        if "target" in self.kwargs:
            target = self.kwargs["target"]
        else:
            target = "query_range"

        params = {
            "query": "ALERTS",
            "dedup": "true",
            "partial_response": "false",
            "start": start,
            "end": end,
            "step": "60",
            "max_source_resolution": "0s",
            "engine": "thanos",
            "analyze": "false",
        }

        if "params" in self.kwargs:  # TODO consider using filters
            for parameter_key in self.kwargs["params"].keys():
                if parameter_key in valid_query_parameters:
                    params[parameter_key] = self.kwargs["params"][parameter_key]

        self.params = params
        self.target = target


class QueryManager:
    """
    Manages query queues and their associated operations.

    Attributes:
        cert (str): Certificate for authentication.
        timeout (int): Timeout duration for queries.
        directory_path (str): Path to store query data.
        threshold (int): Threshold value for query processing.
        thread_manager (semaphore.ThreadManager): Manager for handling threads.
        queues (dict[str, QueryQueue]): Dictionary of query queues managed by this instance.

    Methods:
        add_query_queue() -> int:
            Adds a new query queue and returns its UUID.

        create_query_objects(query_queue_uuid: str, query: Query, separator: int):
            Splits a query into multiple query objects and adds them to the specified query queue.

        create_environments():
            Creates environments for all query queues with query objects.
    """

    def __init__(
        self,
        cert: str = None,
        timeout: int = None,
        directory_path: str = None,
        threshold: int = None,
        thread_manager: semaphore.ThreadManager = None,
    ):
        self.cert = cert
        self.timeout = timeout
        self.treshold = threshold
        self.thread_manager = thread_manager

        self.queues: dict[str, QueryQueue] = {}
        self.directory_path = "data" if directory_path is None else directory_path

    def add_query_queue(self) -> int:
        """
        Adds a new query queue to the query manager.

        This method generates a new UUID for the query queue, creates a new
        QueryQueue instance, and adds it to the manager's queue dictionary.

        Returns:
            int: The UUID of the newly created query queue.
        """
        query_queue_uuid = uuid.uuid4().hex
        query_queue = QueryQueue(query_manager=self)
        self.queues[query_queue_uuid] = query_queue

        return query_queue_uuid

    def create_query_objects(self, query_queue_uuid: str, query: Query, separator: int):
        """
        Creates query objects from a given query and adds them to the specified query queue.

        Args:
            query_queue_uuid (str): The UUID of the query queue to which the query objects will be added.
            query (Query): The query to be split into query objects.
            separator (int): The separator used to split the query into multiple query objects.

        Raises:
            errors.InvalidQueryQueueError: If the provided query queue UUID does not exist in the QueryManager.

        """
        query_objects = QuerySplitter.split_by_separator(QuerySplitter(), query=query, separator=separator)
        query_queue = self.queues.get(query_queue_uuid, None)

        if query_queue is None:
            raise errors.InvalidQueryQueueError(
                f"The provided QueryQueue object doesn't exist inside this QueryManager.\nquery_queue_uuid: {query_queue_uuid}"
            )

        for key, value in query_objects.items():
            query_object = QueryObject(query_queue=query_queue, query=value, nr=key)
            query_queue.add_query_object(query_object=query_object)

    def create_environments(self):
        """
        Creates environments for each queue in the queues dictionary.

        This method iterates over the values in the `queues` dictionary. For each queue,
        if the queue has query objects, it calls the `create_query_queue_environment`
        method on the queue, passing the `directory_path` as an argument.

        Returns:
            None
        """
        for queue in self.queues.values():
            if len(queue.query_objects) == 0:
                continue
            queue.create_query_queue_environemt(self.directory_path)


# TODO add visual feedback


class QueryObject(object):
    """
    A class to manage and execute queries within a specified environment.

    Attributes:
        query_queue (QueryQueue): The queue that holds the query.
        query (Query): The query to be executed.
        object_nr (int): The identifier number for the query object.
        path (str): The file path where the query object environment is created.

    Methods:
        create_query_object_environment(path: str):
            Creates a directory for the query object environment at the specified path.

        execute_query():
            Executes the query using the parameters from the query queue's manager.
    """

    def __init__(self, query_queue: QueryQueue, query: Query, nr: int):
        self.query_queue = query_queue
        self.query = query
        self.object_nr = nr
        self.path = None

    def create_query_object_environment(self, path: str):
        """
        Creates a query object environment by ensuring the specified path exists and
        creating a subdirectory for the query object.

        Args:
            path (str): The base directory path where the query object environment
                        should be created.

        Raises:
            OSError: If the directory creation fails.
        """
        if not os.path.exists(path=path):
            os.makedirs(name=path)

        self.path = os.path.join(path, f"group{self.object_nr}")
        os.mkdir(self.path)

    def execute_query(self):
        """
        Executes the query with the specified parameters.

        This method retrieves the certificate and timeout from the query manager,
        sets the request parameters for the query, and then executes the query
        using a QueryExecutor instance.

        Attributes:
            cert (str): The certificate used for the query.
            path (str): The path where the query will be executed.
            timeout (int): The timeout value for the query.

        Raises:
            Exception: If the query execution fails.
        """
        cert = self.query_queue.query_manager.cert
        path = self.path
        timeout = self.query_queue.query_manager.timeout
        self.query.set_request_parameters(cert=cert, timeout=timeout)
        qe = QueryExecutor(path=path)
        qe.execute_query(self.query)


class QueryQueue(object):
    """
    A class to manage a queue of query objects and their execution.

    Attributes:
        query_manager (QueryManager): An instance of QueryManager to manage query execution.
        query_objects (list[QueryObject]): A list to store query objects.
        path (str): The path where the query queue environment is created.

    Methods:
        create_query_queue_environemt(path: str):
            Creates a directory environment for the query queue at the specified path.

        add_query_object(query_object: QueryObject):
            Adds a query object to the queue.

        schedule_queries() -> list[str]:
            Schedules the execution of all query objects in the queue and returns a list of thread UUIDs.
    """

    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager
        self.query_objects: list[QueryObject] = []
        self.path = None

    def create_query_queue_environemt(self, path: str):
        """
        Creates a query queue environment at the specified path.

        This method performs the following steps:
        1. Checks if the specified path exists. If not, it creates the directory.
        2. Generates a unique identifier (UUID) for the query queue.
        3. Constructs the full path for the query queue using the base path and the UUID.
        4. Creates the directory for the query queue.
        5. Iterates over the query objects and calls their `create_query_object_environment` method to set up their environments.

        Args:
            path (str): The base directory path where the query queue environment will be created.
        """
        if not os.path.exists(path=path):
            os.makedirs(name=path)

        queue_uuid = uuid.uuid4().hex

        self.path = os.path.join(path, queue_uuid)

        os.mkdir(self.path)

        for query_object in self.query_objects:
            query_object.create_query_object_environment(self.path)

    def add_query_object(self, query_object: QueryObject):
        """
        Adds a QueryObject to the list of query objects.

        Args:
            query_object (QueryObject): The query object to be added to the list.
        """
        self.query_objects.append(query_object)

    def schedule_queries(self) -> list[str]:
        """
        Schedules the execution of queries by creating a new thread for each query object.

        Returns:
            list[str]: A list of thread UUIDs corresponding to the scheduled queries.
        """
        out = []

        for query_object in self.query_objects:
            thread_uuid = self.query_manager.thread_manager.add_thread(query_object.execute_query)
            out.append(thread_uuid)

        return out


class QuerySplitter(object):
    """
    A utility class for splitting queries based on specified thresholds or separators.

    Methods
    -------
    split_by_treshold(query: Query, threshold: int = None) -> list[Query | None, Query | None]:
        Splits a query into two parts based on a given threshold in days. If no threshold is provided, returns the original query and None.

    split_by_separator(query: Query, separator: int):
        Splits a query into multiple parts based on a given time separator in seconds.
    """

    def __init__(self):
        pass

    def split_by_treshold(self, query: Query, threshold: int = None) -> list[Query | None, Query | None]:
        """
        Splits a given query into two separate queries based on a specified threshold.

        Args:
            query (Query): The original query to be split.
            threshold (int, optional): The threshold in days to split the query. If not provided, the query will not be split.

        Returns:
            list[Query | None, Query | None]: A list containing two queries. The first query covers the period from the threshold to the end date,
                                              and the second query covers the period from the start date to the threshold. If the threshold is not
                                              provided or the split is not possible, one of the queries will be None.
        """
        queries = []

        if not threshold:
            queries.extend([query, None])
            return queries

        now = dt.now(tz.utc)

        base_url = query.base_url
        start = query.global_start
        end = query.global_end
        kwargs = query.kwargs

        if start is None:
            start = calc.calculate_max_past(now, calc.max_long_term)
            start = str(start)

        end = str(now.timestamp()) if end is None else end

        split = str((now - td(days=threshold)).timestamp())

        flt_start = float(start)
        flt_split = float(split)
        flt_end = float(end)

        if flt_end > flt_split > flt_start:
            queries.append(Query(base_url=base_url, start=split, end=end, kwargs=kwargs))

            params = {
                "step": "3600",
                "max_source_resolution": "1h",
            }  # for 2nd query

            kwargs = copy.deepcopy(kwargs)
            if "params" in kwargs.keys():
                kwargs["params"].update(params)
            else:
                kwargs["params"] = params

            queries.append(Query(base_url=base_url, start=start, end=split, kwargs=kwargs))
        else:
            if split > end:
                queries.extend([None, query])
            elif start > split:
                queries.extend([query, None])
            else:
                print(f"Unexpected split: start {start}, split {split}, end {end}")

        return queries

    def split_by_separator(self, query: Query, separator: int):
        """
        Splits a given query into multiple sub-queries based on a specified time separator.

        Args:
            query (Query): The query object to be split.
            separator (int): The time interval in seconds to split the query by.

        Returns:
            dict: A dictionary where the keys are integers representing the sub-query index,
                  and the values are the sub-query objects.
        """
        query_objects = {}

        start = dt.fromtimestamp(float(query.global_start))
        global_end = dt.fromtimestamp(float(query.global_end))
        step = td(seconds=separator)
        objects_counter = 0

        end = start + step
        while end < global_end:
            query_copy = self.__create_query_copy(query=query, start=start, end=end)
            query_objects[objects_counter] = query_copy

            start = end
            end = start + step
            objects_counter += 1

        diff = global_end - end
        end = end + diff

        query_copy = self.__create_query_copy(query=query, start=start, end=end)
        query_objects[objects_counter] = query_copy

        return query_objects

    def __create_query_copy(self, query: Query, start: dt, end: dt) -> Query:
        query_copy = copy.deepcopy(query)
        query_copy.set_start(start=start.timestamp())
        query_copy.set_end(end=end.timestamp())

        return query_copy
