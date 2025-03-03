"""Module documentation"""

import json
import logging
import os

from utilities.data_filter import create_time_ranges

logger = logging.getLogger("alertmagnet")


class DataCleaner(object):
    def __init__(self):
        self.data = None
        self.metric_index_map = {}

    def __reset(self):
        self.data = None
        self.metric_index_map = {}

    def clear_query_results(self, path: str, step: int):
        logger.debug("clear_query_results called with path: %s and step: %s", path, step)
        groups = os.listdir(path)

        logger.info("Scanning files")
        files = [
            os.path.join(path, group, file)
            for group in groups
            if group.startswith("group")
            for file in os.listdir(os.path.join(path, group))
        ]

        logger.info("Staging %s files", len(files))
        with open(file=files[0], mode="r", encoding="utf-8") as f:
            data = json.load(f)
            self.data = data["data"]["result"]

        for index, result in enumerate(self.data):
            metric = result["metric"]
            flatted_key = str(metric)
            self.metric_index_map[flatted_key] = index

        for file in files[1:]:
            with open(file=file, mode="r", encoding="utf-8") as f:
                sub_data = json.load(f)

            if sub_data["status"] == "error":
                continue

            self.__assert_index_to_metrics(results=sub_data["data"]["result"])

        for result in self.data:
            result["values"] = sorted(set(result["values"]))

        for result in self.data:
            result["values"] = create_time_ranges(data=result["values"], step=step)

        logger.info("Writing files")
        with open(file=os.path.join(path, "finalData.json"), mode="w", encoding="utf-8") as f:
            f.write(json.dumps(self.data, indent=4))

        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                if name != "finalData.json":
                    os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

        self.__reset()

    def __assert_index_to_metrics(self, results) -> int | None:
        for result in results:
            metric = result["metric"]
            flatted_key = str(metric)

            metric_index = self.metric_index_map.get(flatted_key, -1)

            if metric_index == -1:
                length = len(self.metric_index_map)
                self.metric_index_map[flatted_key] = length
                self.data.append(result)
            else:
                self.data[metric_index]["values"].extend(result["values"])

        return
