from __future__ import annotations

import asyncio
import unittest

import requests
from support import LoopbackServer, TestResponse

from yikd_web_client import (
    BodyType,
    HttpMethod,
    MultipartFormData,
    WebHelper,
    WebHelperServices,
)


class WebHelperServicesTests(unittest.TestCase):
    def test_json_headers_cookies_and_async_method(self) -> None:
        with LoopbackServer(
            lambda _: TestResponse(headers={"Set-Cookie": "next=xyz; Path=/"})
        ) as server:
            helper = WebHelperServices()
            helper.Timeout = 5
            helper.RequestHeaders = {"X-Test": "value"}
            helper.cookies.set("session", "abc", path="/")
            response = asyncio.run(helper.SendHttpRequestAsync(server.root_url + "api", '{"id":1}'))
            self.assertEqual('{"ok":true}', response)
            request = server.single_request()
            self.assertEqual("POST", request.method)
            self.assertEqual('{"id":1}', request.body)
            self.assertEqual("value", request.headers["X-Test"])
            self.assertIn("session=abc", request.headers["Cookie"])
            self.assertEqual("xyz", helper.cookies.get("next"))

    def test_method_and_http_errors(self) -> None:
        with LoopbackServer(lambda _: TestResponse(status=400, body="bad")) as server:
            helper = WebHelperServices()
            helper.HttpMethod = HttpMethod.PUT
            helper.Timeout = 5
            with self.assertRaises(requests.HTTPError):
                helper.SendHttpRequest(server.root_url + "bad", "{}")
            self.assertEqual("PUT", server.single_request().method)


class WebHelperTests(unittest.TestCase):
    def test_query_raw_urlencoded_and_multipart(self) -> None:
        with LoopbackServer() as server:
            query = WebHelper()
            query.HttpMethod = HttpMethod.GET
            query.Timeout = 5
            query.queryParameters = {"a b": "x+y", "中文": "值"}
            query.SendHttpRequest(server.root_url + "query")
            self.assertIn("a+b=x%2By", server.requests[-1].path)
            self.assertIn("%E4%B8%AD%E6%96%87", server.requests[-1].path)

            raw = WebHelper()
            raw.Timeout = 5
            raw.bodyType = BodyType.raw
            raw.Body_Raw = "raw-body"
            raw.RequestmediaType = "text/plain"
            raw.SendHttpRequest(server.root_url + "raw")
            self.assertEqual("raw-body", server.requests[-1].body)
            self.assertIn("text/plain", server.requests[-1].headers["Content-Type"])

            form = WebHelper()
            form.Timeout = 5
            form.bodyType = BodyType.urlencoded
            form.Body_UrlEncoded = {"ap0": '{"id":1}', "space": "a b"}
            form.SendHttpRequest(server.root_url + "form")
            self.assertIn("ap0=%7B%22id%22%3A1%7D", server.requests[-1].body)
            self.assertIn("space=a+b", server.requests[-1].body)
            self.assertIn(
                "application/x-www-form-urlencoded", server.requests[-1].headers["Content-Type"]
            )

            multipart = WebHelper()
            multipart.Timeout = 5
            multipart.bodyType = BodyType.formdata
            multipart.Body_FormData = (
                MultipartFormData()
                .add_field("description", "demo")
                .add_file("file", b"hello", "sample.txt", "text/plain")
            )
            multipart.SendHttpRequest(server.root_url + "upload")
            request = server.requests[-1]
            self.assertIn("multipart/form-data", request.headers["Content-Type"])
            self.assertIn('name="description"', request.body)
            self.assertIn('filename="sample.txt"', request.body)
            self.assertIn("hello", request.body)

    def test_create_query_string_and_non_success(self) -> None:
        self.assertEqual("a+b=x%2By", WebHelper.CreateQueryString({"a b": "x+y"}))
        with LoopbackServer(lambda _: TestResponse(status=500, body="failed")) as server:
            helper = WebHelper()
            helper.Timeout = 5
            with self.assertRaises(requests.HTTPError):
                helper.SendHttpRequest(server.root_url)


if __name__ == "__main__":
    unittest.main()
