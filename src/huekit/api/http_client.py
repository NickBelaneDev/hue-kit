import requests

class HttpClient:
    def __init__(self, base_url: str, headers: dict[str, str]):
        self.session = requests.Session()
        self.base_url = base_url
        self.headers = headers

    def get(self, path: str, *, timeout: int = 5):
        ...

    def put(self, path: str, payload: dict, *, timeout: int = 5):
        ...

    def post(self, path: str, payload: dict, *, timeout: int = 5):
        ...

    