from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs

from support import LoopbackServer, TestResponse, create_api_header_client, create_settings

from yikd_web_client import (
    AttachmentHelper,
    CommonFunctionHelper,
    FileChunk,
    SSOHelper,
    SSOLogoutObject,
    UploadModel,
    UploadModelData,
)


class SsoTests(unittest.TestCase):
    OVERRIDE = "https://override.test/k3cloud/"

    @staticmethod
    def create_helper() -> SSOHelper:
        helper = SSOHelper()
        helper.appSettingsModel = create_settings("https://configured.test/k3cloud/")
        helper.Url = "https://configured.test/k3cloud/"
        return helper

    @staticmethod
    def decode_args(helper: SSOHelper, url: str) -> dict[str, object]:
        encoded = url.split("?ud=", 1)[1]
        value = base64.b64decode(encoded).decode("utf-8")
        if helper.argJosn != value:
            raise AssertionError("argJosn does not match URL payload")
        return json.loads(value)

    def test_v4_v3_v2_signed_urls(self) -> None:
        helper = self.create_helper()
        helper.permitcount = "1"
        v4 = helper.GetSsoUrlsV4("v4-user", self.OVERRIDE.rstrip("/"))
        args4 = self.decode_args(helper, v4.html5Url)
        values4 = ["account-id", "v4-user", "app-id", "app-secret", args4["timestamp"], "1"]
        self.assertEqual(
            CommonFunctionHelper.Sha256Hex("".join(sorted(values4))),
            args4["signeddata"],
        )
        self.assertEqual("|{'permitcount':'1'}", args4["otherargs"])
        self.assertTrue(v4.html5Url.startswith(self.OVERRIDE))
        self.assertIn("override.test:443", v4.wpfUrl)

        helper = self.create_helper()
        for version, function in ((3, helper.GetSsoUrlsV3), (2, helper.GetSsoUrlsV2)):
            with self.subTest(version=version):
                urls = function(f"v{version}-user", self.OVERRIDE)
                args = self.decode_args(helper, urls.html5Url)
                values = [
                    "account-id",
                    f"v{version}-user",
                    "app-id",
                    "app-secret",
                    args["timestamp"],
                ]
                self.assertEqual(
                    CommonFunctionHelper.GetSignatureSHA1Util(values),
                    args["signeddata"],
                )

    def test_v1_pipe_payload(self) -> None:
        helper = self.create_helper()
        urls = helper.GetSsoUrlsV1("v1-user", self.OVERRIDE)
        encoded = urls.html5Url.split("?ud=", 1)[1]
        payload = base64.b64decode(encoded).decode("utf-8")
        parts = payload.split("|")
        self.assertEqual(7, len(parts))
        self.assertEqual("account-id", parts[1])
        self.assertEqual("v1-user", parts[2])
        self.assertEqual("app-id", parts[3])
        self.assertEqual(
            CommonFunctionHelper.GetSignatureSHA1Util(
                ["account-id", "v1-user", "app-id", "app-secret", parts[5]]
            ),
            parts[4],
        )
        self.assertIn(payload, helper.argJosn or "")

    def test_logout_payload_versions_and_execution(self) -> None:
        for version, method, sha256 in (
            (4, "GetSSOLogoutap0StrV4", True),
            (3, "GetSSOLogoutap0StrV3", False),
            (2, "GetSSOLogoutap0StrV2V1", False),
        ):
            with self.subTest(version=version):
                helper = self.create_helper()
                logout = getattr(helper, method)("logout-user", self.OVERRIDE)
                root = json.loads(logout.ap0)
                values = [
                    "account-id",
                    "logout-user",
                    "app-id",
                    "app-secret",
                    str(root["Timestamp"]),
                ]
                expected = (
                    CommonFunctionHelper.Sha256Hex("".join(sorted(values)))
                    if sha256
                    else CommonFunctionHelper.GetSignatureSHA1Util(values)
                )
                self.assertEqual(expected, root["SignedData"])
                self.assertTrue(logout.RequestLogoutUrl.startswith(self.OVERRIDE))

        with LoopbackServer(lambda _: TestResponse(body="logout-ok")) as server:
            helper = self.create_helper()
            ap0 = '{"AcctID":"db","Username":"user"}'
            response = helper.SSOExcuteLogout(SSOLogoutObject(server.root_url + "logout", ap0))
            self.assertEqual("logout-ok", response)
            request = server.single_request()
            self.assertEqual("POST", request.method)
            self.assertEqual(ap0, parse_qs(request.body)["ap0"][0])
            self.assertIn("application/x-www-form-urlencoded", request.headers["Content-Type"])


class AttachmentTests(unittest.TestCase):
    def test_file_and_base64_chunking(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.bin"
            path.write_bytes(bytes([0, 1, 2, 3, 4]))
            chunks: list[FileChunk] = []
            AttachmentHelper.ReadFileInChunksByAction(path, chunks.append, 2)
            self.assertEqual([0, 1, 2], [chunk.Chunkindex for chunk in chunks])
            self.assertEqual(
                [b"\x00\x01", b"\x02\x03", b"\x04"], [chunk.Chunkbyte for chunk in chunks]
            )
            self.assertEqual([False, False, True], [chunk.IsLast for chunk in chunks])
            self.assertTrue(all(chunk.Filename == "sample.bin" for chunk in chunks))

        base64_chunks: list[FileChunk] = []
        AttachmentHelper.ReadBase64ChunksByAction(
            base64.b64encode(bytes([0, 1, 2, 3, 4])).decode(),
            "sample.bin",
            base64_chunks.append,
            2,
        )
        self.assertEqual(
            [chunk.Chunkbyte for chunk in chunks], [chunk.Chunkbyte for chunk in base64_chunks]
        )
        with self.assertRaises(ValueError):
            AttachmentHelper.ReadBase64ChunksByAction("AQ==", "x", lambda _: None, 0)

    def test_file_chunk_base64_and_model_validation(self) -> None:
        chunk = FileChunk()
        chunk.Chunkbyte = bytes([0, 1, 2, 255])
        self.assertEqual("AAEC/w==", chunk.ChunkBase64)
        valid = UploadModel(
            UploadModelData(
                FileName="sample.bin",
                FormId="TEST_Form",
                InterId="100",
                EntryinterId="-1",
                FileId="file-id",
                SendByte="AQ==",
            )
        )
        AttachmentHelper.CheckUploadModelData(valid)
        for field, message in (
            ("FileName", "文件名"),
            ("FormId", "表单ID"),
            ("InterId", "单据内码"),
            ("FileId", "文件ID"),
            ("SendByte", "文件字节流"),
        ):
            with self.subTest(field=field):
                model = UploadModel(UploadModelData(**valid.data.__dict__))
                setattr(model.data, field, "")
                with self.assertRaisesRegex(ValueError, message):
                    AttachmentHelper.CheckUploadModelData(model)
        valid.data.Entrykey = "FEntity"
        valid.data.EntryinterId = ""
        with self.assertRaisesRegex(ValueError, "Entrykey"):
            AttachmentHelper.CheckUploadModelData(valid)

    def test_upload_base64_and_file_path_update_file_id(self) -> None:
        upload_call = 0

        def respond(request):
            nonlocal upload_call
            if "AttachmentUpLoad" in request.path:
                upload_call += 1
                return TestResponse(
                    body=json.dumps(
                        {
                            "Result": {
                                "ResponseStatus": {"IsSuccess": True},
                                "FileId": f"file-{upload_call}",
                            }
                        },
                        separators=(",", ":"),
                    )
                )
            return TestResponse()

        with LoopbackServer(respond) as server:
            client = create_api_header_client(server.k3cloud_url)
            template = UploadModel(
                UploadModelData(FormId="TEST_Form", InterId="100", EntryinterId="-1")
            )
            progress: list[FileChunk] = []
            response = AttachmentHelper.AttachmentUploadByBase64(
                base64.b64encode(bytes([0, 1, 2, 3, 4])).decode(),
                "sample.bin",
                client,
                template,
                2,
                lambda chunk, _: progress.append(chunk),
            )
            self.assertIn('"FileId":"file-3"', response)
            self.assertEqual("file-3", template.data.FileId)
            self.assertEqual(3, len(progress))
            self.assertTrue(progress[-1].IsLast)
            self.assertEqual(3, upload_call)
            self.assertEqual(3, sum("AuthService.Logout" in r.path for r in server.requests))

        with tempfile.TemporaryDirectory() as directory, LoopbackServer(respond) as server:
            path = Path(directory) / "file.bin"
            path.write_bytes(b"abc")
            client = create_api_header_client(server.k3cloud_url)
            template = UploadModel(UploadModelData(FormId="F", InterId="1"))
            response = AttachmentHelper.AttachmentUploadByFilePath(path, client, template, 2)
            self.assertEqual("file.bin", template.data.FileName)
            self.assertTrue(template.data.IsLast)
            self.assertTrue(response)

    def test_upload_failure_returns_raw_response(self) -> None:
        failed = '{"Result":{"ResponseStatus":{"IsSuccess":false},"FileId":""}}'
        with LoopbackServer(
            lambda request: (
                TestResponse(body=failed) if "AttachmentUpLoad" in request.path else TestResponse()
            )
        ) as server:
            response = AttachmentHelper.AttachmentUploadByBase64(
                "AQ==",
                "sample.bin",
                create_api_header_client(server.k3cloud_url),
                UploadModel(UploadModelData(FormId="F", InterId="1")),
                2,
            )
            self.assertEqual(failed, response)


if __name__ == "__main__":
    unittest.main()
