from __future__ import annotations

import base64
import json
import tempfile
import time
import unittest
from pathlib import Path

from support import LoopbackServer, TestResponse, create_settings

from yikd_web_client import (
    BySimplePassportType,
    CommonFunctionHelper,
    EnDecode,
    LoginByApiSignHeaders,
    LoginByAppSecret,
    LoginBySign,
    LoginBySimplePassport,
    LoginBySimplePassportModel,
    LoginType,
    ValidateLogin,
    ValidateLoginSettingsModel,
    ValidateUserEnDeCode,
)


class AuthenticationTests(unittest.TestCase):
    @staticmethod
    def wrapped_parameters(value: str) -> list[object]:
        return json.loads(json.loads(value)["parameters"])

    def test_app_secret_json_and_endpoint(self) -> None:
        settings = create_settings()
        service = LoginByAppSecret()
        parameters = self.wrapped_parameters(service.GetLoginJson(settings, True))
        self.assertEqual(
            ["account-id", "api-user", "app-id", "app-secret", "2052"],
            parameters,
        )
        self._assert_login_endpoint(
            service,
            "Kingdee.BOS.WebApi.ServicesStub.AuthService.LoginByAppSecret.common.kdsvc",
        )

    def test_sha256_and_sha1_login_json(self) -> None:
        settings = create_settings()
        for login_type, helper in (
            (LoginType.LoginBySignSHA256, CommonFunctionHelper.GetSHA256),
            (LoginType.LoginBySignSHA1, CommonFunctionHelper.GetSHA1),
        ):
            with self.subTest(login_type=login_type):
                service = LoginBySign()
                service.LoginType = login_type
                root = json.loads(service.GetLoginJson(settings, True))
                parameters = json.loads(root["parameters"])
                timestamp = parameters[3]
                self.assertLessEqual(abs(int(timestamp) - int(time.time())), 2)
                signed = ["account-id", "api-user", "app-id", "app-secret", timestamp]
                self.assertEqual(helper(signed), parameters[4])
                self.assertEqual("2052", parameters[5])
        self._assert_login_endpoint(
            LoginBySign(),
            "Kingdee.BOS.WebApi.ServicesStub.AuthService.LoginBySign.common.kdsvc",
        )

    def test_validate_login_json_and_endpoints(self) -> None:
        settings = ValidateLoginSettingsModel(
            DbId="db-id", UserName="user", Password="password", lcid=2052
        )
        plain = ValidateLogin()
        self.assertEqual(
            ["db-id", "user", "password", 2052],
            self.wrapped_parameters(plain.GetLoginJson(settings, True)),
        )
        encoded = ValidateUserEnDeCode()
        self.assertEqual(
            ["db-id", EnDecode.Encode("user"), EnDecode.Encode("password"), 2052],
            self.wrapped_parameters(encoded.GetLoginJson(settings, True)),
        )
        self._assert_login_endpoint(
            plain,
            "Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUser.common.kdsvc",
        )
        self._assert_login_endpoint(
            encoded,
            "Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUserEnDeCode.common.kdsvc",
        )

    def test_simple_passport_file_base64_and_validation(self) -> None:
        service = LoginBySimplePassport()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.cnf"
            path.write_bytes(bytes([1, 2, 3, 4]))
            model = LoginBySimplePassportModel(
                CnfFilePath=str(path),
                Lcid=1033,
                bySimplePassportType=BySimplePassportType.CnfFile,
            )
            self.assertEqual(bytes([1, 2, 3, 4]), service.GetCnfBytes(path))
            self.assertEqual("AQIDBA==", service.GetPassportForBase64(path))
            self.assertEqual(
                ["AQIDBA==", 1033],
                self.wrapped_parameters(service.GetLoginJson(model, True)),
            )
            self.assertEqual("AQIDBA==", model.SimplePassportForBase64)

        encoded = LoginBySimplePassportModel(
            SimplePassportForBase64="AQIDBA==",
            bySimplePassportType=BySimplePassportType.ForBase64,
        )
        self.assertEqual(
            ["AQIDBA==", 2052],
            self.wrapped_parameters(service.GetLoginJson(encoded, False)),
        )
        with self.assertRaisesRegex(ValueError, "CnfFilePath"):
            service.GetLoginJson(LoginBySimplePassportModel(), True)
        with self.assertRaisesRegex(ValueError, "SimplePassportForBase64"):
            service.GetLoginJson(
                LoginBySimplePassportModel(bySimplePassportType=BySimplePassportType.ForBase64),
                True,
            )
        self._assert_login_endpoint(
            service,
            "Kingdee.BOS.WebApi.ServicesStub.AuthService.LoginBySimplePassport.common.kdsvc",
        )

    def test_api_sign_headers_base_and_v2(self) -> None:
        settings = create_settings()
        headers = LoginByApiSignHeaders.GetApiHeaders(
            settings, "https://example.test/k3cloud/service?x=1"
        )
        self.assertEqual("app-id", headers["X-Kd-Appkey"])
        app_data = base64.b64decode(headers["X-Kd-Appdata"]).decode()
        self.assertEqual("account-id,api-user,2052,100", app_data)
        self.assertEqual(
            EnDecode.HmacSHA256("app-id" + app_data, "app-secret", "utf-8", True),
            headers["X-Kd-Signature"],
        )
        self.assertNotIn("X-Api-ClientID", headers)

        settings.XKDApiAppID = "client_frperg"
        uri = "https://example.test/k3cloud/service?a=hello world"
        v2 = LoginByApiSignHeaders.GetApiHeaders(settings, uri)
        self.assertEqual("client", v2["X-Api-ClientID"])
        self.assertEqual("2.0", v2["X-Api-Auth-Version"])
        self.assertEqual(32, len(v2["x-api-nonce"]))
        message = (
            "POST\n"
            + EnDecode.UrlEncodeWithUpperCode("/k3cloud/service?a=hello%20world", "ascii")
            + "\n\n"
            + f"x-api-nonce:{v2['x-api-nonce']}\n"
            + f"x-api-timestamp:{v2['x-api-timestamp']}\n"
        )
        self.assertEqual(
            EnDecode.HmacSHA256(message, "secret", "ascii", True),
            v2["X-Api-Signature"],
        )
        formatted = LoginByApiSignHeaders.GetApiHeadersStr({"A": "one", "B": "two"})
        self.assertIn("A:one", formatted)
        self.assertTrue(formatted.endswith("\n"))

    def _assert_login_endpoint(self, service: object, expected_path: str) -> None:
        with LoopbackServer(
            lambda _: TestResponse(
                body='{"LoginResultType":1}',
                headers={"Set-Cookie": "session=abc; Path=/"},
            )
        ) as server:
            service.RequestHeaders = {"X-Test": "auth"}
            service.Timeout = 5
            result = service.Login(server.k3cloud_url.rstrip("/"), '{"parameters":"[]"}')
            self.assertEqual(server.k3cloud_url + expected_path, result.RequestUrl)
            self.assertEqual('{"LoginResultType":1}', result.RealResponseBody)
            self.assertEqual("abc", result.Cookie.get("session"))
            request = server.single_request()
            self.assertEqual("POST", request.method)
            self.assertEqual("/k3cloud/" + expected_path, request.path)
            self.assertEqual("auth", request.headers["X-Test"])


if __name__ == "__main__":
    unittest.main()
