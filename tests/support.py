from __future__ import annotations

import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Optional

from yikd_web_client import AppSettingsModel, LoginType, YiK3CloudClient


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: str


@dataclass
class TestResponse:
    body: str = '{"ok":true}'
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)


class LoopbackServer:
    def __init__(
        self,
        callback: Optional[Callable[[RecordedRequest], TestResponse]] = None,
    ) -> None:
        self.requests: list[RecordedRequest] = []
        self._callback = callback or (lambda _: TestResponse())
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8") if length else ""
                request = RecordedRequest(
                    method=self.command,
                    path=self.path,
                    headers={key: value for key, value in self.headers.items()},
                    body=body,
                )
                owner.requests.append(request)
                response = owner._callback(request)
                payload = response.body.encode("utf-8")
                self.send_response(response.status)
                for key, value in response.headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)

            do_GET = _handle
            do_POST = _handle
            do_PUT = _handle
            do_PATCH = _handle
            do_DELETE = _handle

            def log_message(self, format: str, *args: object) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        self.root_url = f"http://127.0.0.1:{self._server.server_port}/"
        self.k3cloud_url = self.root_url + "k3cloud/"

    def single_request(self) -> RecordedRequest:
        if len(self.requests) != 1:
            raise AssertionError(f"expected one request, got {len(self.requests)}")
        return self.requests[0]

    def close(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    def __enter__(self) -> "LoopbackServer":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def create_settings(server_url: str = "https://example.test/k3cloud/") -> AppSettingsModel:
    settings = AppSettingsModel()
    settings.XKDApiAcctID = "account-id"
    settings.XKDApiAppID = "app-id"
    settings.XKDApiAppSec = "app-secret"
    settings.XKDApiUserName = "api-user"
    settings.XKDApiLCID = "2052"
    settings.XKDApiServerUrl = server_url
    settings.XKDApiOrgNum = "100"
    return settings


def create_api_header_client(server_url: str) -> YiK3CloudClient:
    client = YiK3CloudClient()
    client.LoginType = LoginType.LoginByApiSignHeaders
    client.AppSettingsModel = create_settings(server_url)
    client.Timeout = 5
    return client
