"""Module documentation"""

import json
import os

from utilities.data_filter import create_time_ranges


class DataCleaner(object):  # new file
    def __init__(self):
        self.data = None

    def clear_query_results(self, path: str, step: int):
        if not path.endswith("/"):
            path += "/"

        files = []
        groups = os.listdir(path)

        print("Scanning files")
        for group in groups:
            if not group.startswith("group"):
                continue

            for file in os.listdir(path + group):
                files.append(path + group + "/" + file)

        with open(file=files[0], mode="r", encoding="utf-8") as f:
            self.data = json.load(f)

        print("Staging files")
        for file in files[1:]:
            with open(file=file, mode="r", encoding="utf-8") as f:
                sub_data = json.load(f)

            if sub_data["status"] == "error":
                continue

            for result in sub_data["data"]["result"]:
                index = self.__check_metric_in_data(result["metric"])
                if not index is None:
                    data = result["values"]
                    self.data["data"]["result"][index]["values"].extend(data)
                else:
                    data = result["values"]
                    result["values"] = data
                    self.data["data"]["result"].append(result)

        for result in self.data["data"]["result"]:
            result["values"] = list(set(result["values"]))
            result["values"].sort()

        for result in self.data["data"]["result"]:
            result["values"] = create_time_ranges(data=result["values"], step=step)

        print("Writing files")
        with open(file=path + "finalData.json", mode="w", encoding="utf-8") as f:
            f.write(json.dumps(self.data, indent=4))

    def __check_metric_in_data(self, metric) -> int | None:
        for index, result in enumerate(self.data["data"]["result"]):
            if result["metric"] == metric:
                return index

            return None

        return None
