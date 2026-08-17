from __future__ import annotations

import base64
import hashlib
import json
import tempfile
import time
import unittest
from pathlib import Path

from Crypto.Cipher import DES
from Crypto.Util.Padding import unpad

from yikd_web_client import (
    AppSettingsModel,
    BySimplePassportType,
    CommonFunctionHelper,
    CustomMediaTypeNames,
    CustomServicesStubpath,
    EnDecode,
    JsonHelperServices,
    LoginBySimplePassportModel,
    RequestWebModel,
    ValidateLoginSettingsModel,
    XmlConfigHelper,
)


class CommonFunctionTests(unittest.TestCase):
    def test_time_helpers_are_current(self) -> None:
        before_ms = time.time_ns() // 1_000_000
        actual_ms = CommonFunctionHelper.CurrentTimeMillis()
        after_ms = time.time_ns() // 1_000_000
        self.assertLessEqual(before_ms, actual_ms)
        self.assertLessEqual(actual_ms, after_ms)
        self.assertLessEqual(abs(CommonFunctionHelper.GetTimestamp() - int(time.time())), 1)

    def test_url_hash_hex_and_base64_helpers(self) -> None:
        self.assertEqual(
            "https://example.test/k3cloud/",
            CommonFunctionHelper.GetServerUrl("https://example.test/k3cloud"),
        )
        self.assertEqual("", CommonFunctionHelper.GetServerUrl("  "))
        self.assertEqual(
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            CommonFunctionHelper.Sha256Hex("abc"),
        )
        self.assertEqual(
            hashlib.sha256("abc".encode("utf-16-le")).hexdigest(),
            CommonFunctionHelper.Sha256Hex("abc", "utf-16-le"),
        )
        self.assertEqual("000aabff", CommonFunctionHelper.ToHexString(bytes([0, 10, 171, 255])))
        self.assertEqual(
            "000AABFF", CommonFunctionHelper.ToHexString(bytes([0, 10, 171, 255]), False)
        )
        self.assertEqual("AAEC/v8=", CommonFunctionHelper.ToBase64(bytes([0, 1, 2, 254, 255])))

    def test_sorted_sha_helpers(self) -> None:
        sha1 = "a9993e364706816aba3e25717850c26c9cd0d89d"
        self.assertEqual(sha1, CommonFunctionHelper.GetSignatureSHA1Util(["c", "a", "b"]))
        self.assertEqual(sha1, CommonFunctionHelper.GetSHA1(["b", "c", "a"]))
        self.assertEqual(
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            CommonFunctionHelper.GetSHA256(["c", "b", "a"]),
        )
        self.assertEqual("", CommonFunctionHelper.GetSHA256(None))
        self.assertEqual("", CommonFunctionHelper.GetSHA256([]))


class JsonTests(unittest.TestCase):
    @staticmethod
    def parameters(envelope: str) -> list[object]:
        return json.loads(json.loads(envelope)["parameters"])

    def test_request_envelope_and_optional_parameters(self) -> None:
        envelope = JsonHelperServices.getRequestBodystring("TEST_Form", '{"Id":1}', True, "Forbid")
        root = json.loads(envelope)
        self.assertEqual(1, root["format"])
        self.assertEqual("ApiClient", root["useragent"])
        self.assertEqual("1.0", root["v"])
        self.assertTrue(root["rid"])
        self.assertEqual(["TEST_Form", "Forbid", '{"Id":1}'], self.parameters(envelope))
        self.assertEqual(
            ["{}"], self.parameters(JsonHelperServices.getRequestBodystring("", "{}", True, ""))
        )

    def test_safe_and_relaxed_escaping_round_trip(self) -> None:
        relaxed = JsonHelperServices.getRequestBodystring("FORM", "<tag>", True, "")
        safe = JsonHelperServices.getRequestBodystring("FORM", "<tag>", False, "")
        self.assertIn("<tag>", relaxed)
        self.assertNotIn("<tag>", safe)
        self.assertIn(r"\\u003Ctag\\u003E", safe)
        self.assertEqual(self.parameters(relaxed), self.parameters(safe))

    def test_login_envelopes(self) -> None:
        standard = JsonHelperServices.getLoginRequestBodystring('["db"]', True)
        self.assertEqual('["db"]', json.loads(standard)["parameters"])
        indented = JsonHelperServices.getLoginRequestBodystring("[]", True, True)
        self.assertIn("\n", indented)
        parameter_only = JsonHelperServices.getLoginRequestBodystringByParameters("[1,2]", True)
        self.assertEqual({"parameters": "[1,2]"}, json.loads(parameter_only))


class EncryptionTests(unittest.TestCase):
    def test_legacy_des_is_deterministic_and_decryptable(self) -> None:
        encrypted = EnDecode.Encode("hello")
        self.assertEqual(encrypted, EnDecode.Encode("hello"))
        self.assertEqual(encrypted, EnDecode.EncodeNew1("hello"))
        cipher = DES.new(b"KingdeeK", DES.MODE_CBC, iv=b"KingdeeK")
        decrypted = unpad(cipher.decrypt(base64.b64decode(encrypted)), DES.block_size)
        self.assertEqual("hello", decrypted.decode("utf-8"))

    def test_hmac_hex_and_url_encoding(self) -> None:
        import hmac

        digest = hmac.new(b"secret", b"message", hashlib.sha256).digest()
        self.assertEqual(
            base64.b64encode(digest).decode(), EnDecode.HmacSHA256("message", "secret", "utf-8")
        )
        expected_hex = base64.b64encode(digest.hex().encode()).decode()
        self.assertEqual(expected_hex, EnDecode.HmacSHA256("message", "secret", "ascii", True))
        self.assertEqual("000AABFF", EnDecode.ByteToHexStr(bytes([0, 10, 171, 255])))
        self.assertEqual("", EnDecode.ByteToHexStr(None))
        self.assertEqual("a+b%2Bc%2F%3F", EnDecode.UrlEncodeWithUpperCode("a b+c/?"))


class ConfigurationModelTests(unittest.TestCase):
    def test_compatibility_namespace_reexports_public_types(self) -> None:
        import YiKdWebClient
        from YiKdWebClient.AuthService import LoginBySign
        from YiKdWebClient.ComWebHelper import WebHelper
        from YiKdWebClient.Model import AppSettingsModel as CompatibilitySettings
        from YiKdWebClient.SSO import SSOHelper
        from YiKdWebClient.ToolsHelper import AttachmentHelper

        self.assertEqual("1.0.0.32", YiKdWebClient.__version__)
        self.assertIs(AppSettingsModel, CompatibilitySettings)
        self.assertTrue(all((LoginBySign, WebHelper, SSOHelper, AttachmentHelper)))

    def test_xml_and_app_settings(self) -> None:
        content = """<?xml version="1.0"?><configuration><appSettings>
        <add key="X-KDApi-AcctID" value="account-from-test" />
        <add key="X-KDApi-AppID" value="app-from-test" />
        <add key="X-KDApi-AppSec" value="secret-from-test" />
        <add key="X-KDApi-UserName" value="user-from-test" />
        <add key="X-KDApi-LCID" value="2052" />
        <add key="X-KDApi-ServerUrl" value="https://example.test/k3cloud" />
        <add key="X-KDApi-OrgNum" value="100" />
        </appSettings></configuration>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.xml"
            path.write_text(content, encoding="utf-8")
            values = XmlConfigHelper.GetAllCfgDic(path)
            self.assertEqual(7, len(values))
            model = AppSettingsModel(str(path))
            self.assertEqual("account-from-test", model.XKDApiAcctID)
            self.assertEqual("https://example.test/k3cloud/", model.XKDApiServerUrl)
            self.assertEqual({}, XmlConfigHelper.GetAllCfgDic(Path(directory) / "missing.xml"))

    def test_model_url_and_custom_stub_defaults(self) -> None:
        validate = ValidateLoginSettingsModel("https://example.test/k3cloud")
        self.assertEqual("https://example.test/k3cloud/", validate.Url)
        passport = LoginBySimplePassportModel()
        self.assertEqual(2052, passport.Lcid)
        self.assertEqual(BySimplePassportType.CnfFile, passport.bySimplePassportType)
        stub = CustomServicesStubpath(" Sample .WebApi ", " Service ", " Run ")
        self.assertEqual(
            "Sample.WebApi.Service.Run,Sample.WebApi.common.kdsvc",
            stub.GetCustomServicesStubpathUrl(),
        )
        request = RequestWebModel()
        self.assertEqual("", request.RealResponseBody)
        self.assertEqual("application/json", CustomMediaTypeNames.Application.Json)


if __name__ == "__main__":
    unittest.main()
