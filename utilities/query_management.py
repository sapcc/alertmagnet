# standard lib imports
from __future__ import annotations
import copy
import json
import os
import time
import uuid

from datetime import datetime as dt
from datetime import timedelta as td
from datetime import timezone as tz

# third party imports
import requests

# first party imports
from utilities import calc
from utilities import directory_management
from utilities import errors
from utilities import response_messages
from utilities import semaphore

# TODO add META information to query -> QueryGroup


class Query(object):  # Outsource Query logic with split; remove combine
    def __init__(
        self,
        base_url: str = None,
        start: str = None,
        end: str = None,
        kwargs: dict = None,
    ):
        self.query_uuid = None
        self.chunk = 0
        self.path = None

        self.base_url = base_url
        self.global_start = start
        self.global_end = end

        # maybe apply kwargs as kwargs
        self.kwargs = {} if kwargs is None else kwargs

        self.cert = None
        self.timeout = None

        self.initialize()

    def initialize(self):
        now = dt.now(tz.utc)

        self.global_end = str(now.timestamp()) if self.global_end is None else self.global_end  # ensures end has value

        if self.global_start is None:  # ensures start has value
            self.global_start = calc.calculate_past_five_years_timestamp(now)
            self.global_start = str(self.global_start)

    def execute(self, query_uuid: str):
        self.query_uuid = query_uuid

        self.request_alerts(start=self.global_start, end=self.global_end)

    def get_alert_request_data(self, start: str = None, end: str = None):
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

        out = {"target": target, "params": params}

        return out

    def create_requests(self, target: str, params: list[tuple]) -> dict:
        url = self.base_url + target

        for i in range(3):
            try:
                print(f"starting request… [{dt.fromtimestamp(float(params['start']))}]")  # TODO remove print statements
                res = requests.get(url=url, cert=self.cert, params=params, timeout=self.timeout)
                print(f"request finished [{dt.fromtimestamp(float(params['start']))}]")
            except requests.ConnectTimeout:
                print("requests.ConnectTimeout")
                continue
            except requests.exceptions.ReadTimeout:
                print("requests.exceptions.ReadTimeout")
                return response_messages.MESSAGE_EXCEEDED_MAXIMUM
            except requests.exceptions.SSLError:
                print("requests.exceptions.SSLError")
                continue
            except requests.exceptions.ConnectionError:
                print("requests.exceptions.ConnectionError")
                continue
            except requests.exceptions.ChunkedEncodingError:
                print("requests.exceptions.ChunkedEncodingError")
                return response_messages.MESSAGE_EXCEEDED_MAXIMUM
            except Exception as e:
                raise e
            else:
                try:
                    data = res.json()
                except requests.exceptions.JSONDecodeError:
                    print("=" * 50)
                    print(res.text)
                    print("=" * 50)
                else:
                    return data
        else:
            print("safety catch invoked")
            return {}

    # TODO maybe extend back
    def combine_queries(self, start: str = None, mid: str = None, end: str = None) -> dict:
        request_data1 = self.get_alert_request_data(start=start, end=mid)
        request_data2 = self.get_alert_request_data(start=mid, end=end)

        result1 = self.create_requests(**request_data1)
        result2 = self.create_requests(**request_data2)

        if result1 == response_messages.MESSAGE_EXCEEDED_MAXIMUM:
            self.__split_request_by_half(start=start, end=mid)
        elif "status" in result1:
            if result1["status"] == "success":
                filename = self.path + rf"/data{self.chunk}.json"

                with open(filename, "w", encoding="utf-8") as f:
                    f.write(json.dumps(result1, indent=4))

                self.chunk += 1
        else:
            self.chunk += 1

        del result1

        if result2 == response_messages.MESSAGE_EXCEEDED_MAXIMUM:
            self.__split_request_by_half(start=mid, end=end)
        elif "status" in result2:
            if result2["status"] == "success":
                filename = self.path + rf"/data{self.chunk}.json"

                with open(filename, "w", encoding="utf-8") as f:
                    f.write(json.dumps(result2, indent=4))

                self.chunk += 1
        else:
            self.chunk += 1

        del result2

        return

    def __split_request_by_half(self, start: str = None, end: str = None) -> dict:
        start_tt = float(start)
        end_tt = float(end)

        time_difference = end_tt - start_tt
        half = time_difference / 2
        mid = end_tt - half

        self.combine_queries(start=start, mid=mid, end=end)

        return

    def start_request(self, cert: str = None, timeout: int = 30, path: str = None):
        self.path = r"data/" if path is None else path

        self.cert = cert
        self.timeout = timeout

        self.request_alerts(start=self.global_start, end=self.global_end)

    def request_alerts(self, start: str, end: str):
        request_data = self.get_alert_request_data(start=start, end=end)
        results = self.create_requests(**request_data)

        if results == response_messages.MESSAGE_EXCEEDED_MAXIMUM:
            print("splitting necessary")
            self.__split_request_by_half(start=start, end=end)
        else:
            if not self.path.endswith("/"):
                self.path += "/"

            filename = rf"{self.path}data{self.chunk}.json"

            with open(file=filename, mode="w", encoding="utf-8") as f:
                f.write(json.dumps(results, indent=4))

        return


# TODO develop own tool


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
        self.storage_path = r"data/" if storage_path is None else storage_path

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
            directory_management.create_storage_path(path=path)

        if not path.endswith("/"):
            path += "/"

        self.path = rf"{path}group{self.object_nr}"
        os.mkdir(self.path)

    def execute_query(self):
        cert = self.query_queue.query_manager.cert
        timeout = self.query_queue.query_manager.timeout
        path = self.path
        self.query.start_request(cert=cert, timeout=timeout, path=path)


class QueryQueue(object):
    def __init__(self, query_manager: QueryManager):
        self.query_manager = query_manager
        self.query_objects: list[QueryObject] = []
        self.path = None

    def create_query_queue_environemt(self, path: str):
        if not os.path.exists(path=path):
            directory_management.create_storage_path(path=path)

        queue_uuid = uuid.uuid4().hex

        if not path.endswith("/"):
            path += "/"

        self.path = rf"{path}{queue_uuid}"

        os.mkdir(self.path)

        for query_object in self.query_objects:
            query_object.create_query_object_environment(self.path)

    def add_query_object(self, query_object: QueryObject):
        self.query_objects.append(query_object)

    def execute_queries(self):
        for query_object in self.query_objects:
            thread_uuid = self.query_manager.thread_manager.add_thread(query_object.execute_query)
            self.query_manager.thread_manager.start_thread(thread_uuid=thread_uuid)
            time.sleep(1)


class QuerySplitter(object):
    def __init__(self):
        pass

    def split_by_treshold(self, query: Query, threshold: int = None) -> list[Query, Query]:
        queries = []

        if not threshold:
            queries.append(Query)
        else:

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
                    print("Unexpected split")

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
        query_copy.global_start = start.timestamp()
        query_copy.global_end = end.timestamp()

        return query_copy
