"""Module documentation"""

import json
import os

from utilities.data_filter import create_time_ranges


class DataCleaner(object):  # new file
    def __init__(self):
        self.data = None

    def clear_query_results(self, path: str, step: int):
        groups = os.listdir(path)

        print("Scanning files")
        files = [
            os.path.join(path, group, file)
            for group in groups
            if group.startswith("group")
            for file in os.listdir(os.path.join(path, group))
        ]

        """for group in groups:
            if not group.startswith("group"):
                continue

            for file in os.listdir(os.path.join(path, group)):
                files.append(os.path.join(path, group, file))"""

        with open(file=files[0], mode="r", encoding="utf-8") as f:
            self.data = json.load(f)

        print("Staging files")
        for file in files[1:]:
            print(f"file {files.index(file)+1} from {len(files)}")
            with open(file=file, mode="r", encoding="utf-8") as f:
                sub_data = json.load(f)

            if sub_data["status"] == "error":
                continue

            self.__assert_index_to_metrics(results=sub_data["data"]["result"])
            """for result in sub_data["data"]["result"]:
                index = self.__check_metric_in_data(result["metric"])
                data = result["values"]
                if index is None:
                    result["values"] = data
                    self.data["data"]["result"].append(result)
                else:
                    self.data["data"]["result"][index]["values"].extend(data)"""

        for result in self.data["data"]["result"]:
            result["values"] = sorted(set(result["values"]))

        for result in self.data["data"]["result"]:
            result["values"] = create_time_ranges(data=result["values"], step=step)

        print("Writing files")
        with open(file=os.path.join(path, "finalData.json"), mode="w", encoding="utf-8") as f:
            f.write(json.dumps(self.data, indent=4))

    def __check_metric_in_data(self, metric) -> int | None:
        for index, result in enumerate(self.data["data"]["result"]):
            if result["metric"] == metric:
                return index

    def __assert_index_to_metrics(self, results) -> int | None:
        trans = {}
        a = [None for i in range(len(results))]
        for index, result in enumerate(results):
            a[index] = result["metric"]
            trans[index] = [result["metric"], None]
            break

        for index, result in enumerate(self.data["data"]["result"]):
            if result["metric"] in a:
                i = a.index(result["metric"])
                trans[i][1] = i
                break

        for value in trans.values():
            i = a.index(value[0])
            if value[1] is None:
                self.data["data"]["result"].append(results[i])
            else:
                self.data["data"]["result"][value[1]]["values"].extend(results[i]["values"])

        return None
