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
