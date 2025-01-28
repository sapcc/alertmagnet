import os


def create_storage_path(path: str):
    path_parts = path.split("/")
    for index, value in enumerate(path_parts):
        partial_path = "/" + "/".join(path_parts[0:index]) + value
        if not os.path.exists():
            os.mkdir(partial_path)
