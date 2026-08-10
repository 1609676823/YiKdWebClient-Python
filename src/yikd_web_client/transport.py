"""同步/异步 HTTP 传输层。"""

from __future__ import annotations

import asyncio
import mimetypes
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Optional, Sequence, Union
from urllib.parse import urlencode

import requests
from requests.cookies import RequestsCookieJar

from .media_types import BodyType, CustomMediaTypeNames, HttpMethod

TimeoutValue = Optional[Union[int, float, timedelta]]


def _timeout_seconds(value: TimeoutValue) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, timedelta):
        return value.total_seconds()
    return float(value)


def _method_name(value: Union[str, HttpMethod]) -> str:
    return value.value if isinstance(value, HttpMethod) else str(value).upper()


@dataclass
class MultipartFormData:
    """Python 版 multipart/form-data 请求体。

    ``files`` 的值采用 requests 的 ``(filename, content, content_type)`` 形式。
    """

    fields: MutableMapping[str, Any] = field(default_factory=dict)
    files: MutableMapping[str, Any] = field(default_factory=dict)

    def add_field(self, name: str, value: Any) -> "MultipartFormData":
        self.fields[name] = value
        return self

    def add_file(
        self,
        name: str,
        content: Any,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> "MultipartFormData":
        inferred_name = filename
        if inferred_name is None and isinstance(content, (str, Path)):
            inferred_name = Path(content).name
        inferred_name = inferred_name or name
        inferred_type = (
            content_type or mimetypes.guess_type(inferred_name)[0] or "application/octet-stream"
        )
        if isinstance(content, (str, Path)):
            content = Path(content).read_bytes()
        self.files[name] = (inferred_name, content, inferred_type)
        return self


class WebHelperServices:
    def __init__(self) -> None:
        self.cookies = RequestsCookieJar()
        self.RequestHeaders: dict[str, str] = {}
        self.ResponseHeaders: Optional[dict[str, str]] = None
        self.HttpMethod: Union[str, HttpMethod] = HttpMethod.POST
        self.Timeout: TimeoutValue = None

    def SendHttpRequest(self, url: str, postData: str = "") -> str:
        session = requests.Session()
        session.cookies.update(self.cookies)
        headers = {"Accept-Charset": "utf-8", "Content-Type": "application/json; charset=utf-8"}
        headers.update(self.RequestHeaders)
        response = session.request(
            _method_name(self.HttpMethod),
            url,
            data=postData.encode("utf-8"),
            headers=headers,
            timeout=_timeout_seconds(self.Timeout),
        )
        response.raise_for_status()
        self.ResponseHeaders = dict(response.headers)
        self.cookies = session.cookies.copy()
        return response.content.decode("utf-8")

    async def SendHttpRequestAsync(self, url: str, postData: str = "") -> str:
        return await asyncio.to_thread(self.SendHttpRequest, url, postData)

    send_http_request = SendHttpRequest
    send_http_request_async = SendHttpRequestAsync


class WebHelper:
    def __init__(self) -> None:
        self.queryParameters: dict[str, str] = {}
        self.Requestcookies = RequestsCookieJar()
        self.Responsecookies = RequestsCookieJar()
        self.RequestHeaders: dict[str, str] = {}
        self.ResponseHeaders: Optional[dict[str, str]] = None
        self.HttpMethod: Union[str, HttpMethod] = HttpMethod.POST
        self.bodyType = BodyType.none
        self.Body_FormData: Union[MultipartFormData, Mapping[str, Any]] = MultipartFormData()
        self.Body_UrlEncoded: Union[Mapping[str, Any], Sequence[tuple[str, Any]]] = {}
        self.Body_Raw = ""
        self.RequestmediaType = CustomMediaTypeNames.Application.Json
        self.Timeout: TimeoutValue = 120

    def SendHttpRequest(self, url: str) -> str:
        session = requests.Session()
        session.cookies.update(self.Requestcookies)
        headers = {"Accept-Charset": "utf-8"}
        headers.update(self.RequestHeaders)

        kwargs: dict[str, Any] = {}
        if self.bodyType == BodyType.formdata:
            if isinstance(self.Body_FormData, MultipartFormData):
                kwargs["data"] = dict(self.Body_FormData.fields)
                kwargs["files"] = dict(self.Body_FormData.files)
                if not kwargs["files"]:
                    kwargs["files"] = {
                        key: (None, str(value)) for key, value in self.Body_FormData.fields.items()
                    }
                    kwargs["data"] = {}
            else:
                kwargs["files"] = {
                    key: (None, str(value)) for key, value in self.Body_FormData.items()
                }
        elif self.bodyType == BodyType.urlencoded:
            kwargs["data"] = self.Body_UrlEncoded
        elif self.bodyType == BodyType.raw:
            kwargs["data"] = self.Body_Raw.encode("utf-8")
            headers.setdefault("Content-Type", f"{self.RequestmediaType}; charset=utf-8")

        response = session.request(
            _method_name(self.HttpMethod),
            url,
            params=self.queryParameters or None,
            headers=headers,
            timeout=_timeout_seconds(self.Timeout),
            **kwargs,
        )
        response.raise_for_status()
        self.ResponseHeaders = dict(response.headers)
        self.Responsecookies = session.cookies.copy()
        return response.content.decode("utf-8")

    async def SendHttpRequestAsync(self, url: str) -> str:
        return await asyncio.to_thread(self.SendHttpRequest, url)

    @staticmethod
    def CreateQueryString(parameters: Mapping[str, Any]) -> str:
        return urlencode([(key, value) for key, value in parameters.items()])

    send_http_request = SendHttpRequest
    send_http_request_async = SendHttpRequestAsync
    create_query_string = CreateQueryString


__all__ = ["MultipartFormData", "WebHelper", "WebHelperServices"]
