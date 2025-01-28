from __future__ import annotations
import copy
import json
import os
import uuid

from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz

import requests

from utilities import calc
from utilities import errors
from utilities import data_filter
from utilities import response_messages
from utilities import semaphore
from utilities.helper import ResponseDummy

# TODO add META information to query -> QueryGroup


class QueryExecutor:
    def __init__(self, path: str):
        self.query = None
        self.path = path
        self.chunk = 0

    def execute_query(self, query: Query):
        self.query = query
        result = query.execute()
        self.__handle_query_result(result=result)

    def reset(self):
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
        now = dt.now(tz.utc)

        self.global_end = str(now.timestamp()) if self.global_end is None else self.global_end  # ensures end has value

        if self.global_start is None:  # ensures start has value
            self.global_start = calc.calculate_past_five_years_timestamp(now)
            self.global_start = str(self.global_start)

        # apply kwargs values
        self.__parse_request_data()

    def execute(self):
        response = self.__execute_request()
        result = self.__parse_request_result(response=response)

        return result

    def set_request_parameters(self, cert: str = None, timeout: int = None):
        self.cert = cert
        self.timeout = timeout

    # TODO set property
    def set_start(self, start: str):
        self.global_start = start

        if self.params is None:
            return

        self.params["start"] = start

    # TODO set property
    def set_end(self, end: str):
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
            except requests.ConnectTimeout:
                print("requests.ConnectTimeout")
                continue
            except requests.exceptions.ReadTimeout:
                print("requests.exceptions.ReadTimeout")
                return ResponseDummy(response_messages.MESSAGE_EXCEEDED_MAXIMUM)
            except requests.exceptions.SSLError:
                print("requests.exceptions.SSLError")
                continue
            except requests.exceptions.ConnectionError:
                print("requests.exceptions.ConnectionError")
                continue
            except requests.exceptions.ChunkedEncodingError:
                print("requests.exceptions.ChunkedEncodingError")
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
    def __init__(
        self,
        cert: str = None,
        timeout: int = None,
        storage_path: str = None,
        threshold: int = None,
        thread_manager: semaphore.ThreadManager = None,
    ):
        self.cert = cert
        self.timeout = timeout
        self.treshold = threshold
        self.thread_manager = thread_manager

        self.queues: dict[str, QueryQueue] = {}
        self.storage_path = "data" if storage_path is None else storage_path

    def add_query_queue(self) -> int:
        query_queue_uuid = uuid.uuid4().hex
        query_queue = QueryQueue(query_manager=self)
        self.queues[query_queue_uuid] = query_queue

        return query_queue_uuid

    def create_query_objects(self, query_queue_uuid: str, query: Query, separator: int):
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
        for queue in self.queues.values():
            if len(queue.query_objects) == 0:
                continue
            queue.create_query_queue_environemt(self.storage_path)


# TODO add visual feedback


class QueryObject(object):
    def __init__(self, query_queue: QueryQueue, query: Query, nr: int):
        self.query_queue = query_queue
        self.query = query
        self.object_nr = nr
        self.path = None

    def create_query_object_environment(self, path: str):
        if not os.path.exists(path=path):
            os.makedirs(name=path)

        self.path = os.path.join(path, f"group{self.object_nr}")
        os.mkdir(self.path)

    def execute_query(self):
        cert = self.query_queue.query_manager.cert
        path = self.path
        timeout = self.query_queue.query_manager.timeout
        self.query.set_request_parameters(cert=cert, timeout=timeout)
        qe = QueryExecutor(path=path)
        qe.execute_query(self.query)


class QueryQueue(object):
    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager
        self.query_objects: list[QueryObject] = []
        self.path = None

    def create_query_queue_environemt(self, path: str):
        if not os.path.exists(path=path):
            os.makedirs(name=path)

        queue_uuid = uuid.uuid4().hex

        self.path = os.path.join(path, queue_uuid)

        os.mkdir(self.path)

        for query_object in self.query_objects:
            query_object.create_query_object_environment(self.path)

    def add_query_object(self, query_object: QueryObject):
        self.query_objects.append(query_object)

    def schedule_queries(self) -> list[str]:
        out = []

        for query_object in self.query_objects:
            thread_uuid = self.query_manager.thread_manager.add_thread(query_object.execute_query)
            out.append(thread_uuid)

        return out


class QuerySplitter(object):
    def __init__(self):
        pass

    def split_by_treshold(self, query: Query, threshold: int = None) -> list[Query | None, Query | None]:
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
            start = calc.calculate_past_five_years_timestamp(now)
            start = str(start)

        end = str(now.timestamp()) if end is None else end

        split = str((now - td(days=threshold)).timestamp())

        if end > split > start:
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
