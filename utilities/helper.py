import json
import os

from io import StringIO

import requests


class ResponseDummy(requests.Response):
    def __init__(self, value):
        self.value = value
        self._text = value
        super().__init__()

    def json(self, **kwargs):
        return self.value

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        self._text = value


def read_json_content(filename: str):
    io_stream = read_file(filename=filename)
    data = json.load(io_stream)

    return data


def read_file(filename: str) -> StringIO:
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Path {filename} does not exist.")

    file_stream = open(file=filename, mode="r", encoding="utf-8")
    return file_stream
