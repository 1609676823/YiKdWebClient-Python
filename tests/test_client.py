from __future__ import annotations

import json
import unittest

from support import LoopbackServer, TestResponse, create_api_header_client, create_settings

from yikd_web_client import (
    BySimplePassportType,
    CustomServicesStubpath,
    LoginBySimplePassportModel,
    LoginType,
    ValidateLoginSettingsModel,
    YiK3CloudClient,
)


class ClientBehaviorTests(unittest.TestCase):
    def test_constructor_helpers_context_and_dispose(self) -> None:
        client = YiK3CloudClient()
        self.assertEqual(LoginType.LoginByAppSecret, client.LoginType)
        self.assertEqual(60, client.Timeout)
        self.assertTrue(client.UnsafeRelaxedJsonEscaping)
        self.assertEqual(
            "https://example.test/k3cloud/",
            client.GetServerUrl("https://example.test/k3cloud"),
        )
        self.assertEqual("Service.Run.common.kdsvc", client.EnsureSuffixServicesStub("Service.Run"))
        self.assertEqual(
            "Service.Run.custom", client.EnsureSuffixServicesStub("Service.Run", ".custom")
        )
        client.Dispose()
        client.Dispose()
        self.assertIsNone(client.LoginType)

    def test_login_input_validation_and_api_header_noop(self) -> None:
        client = YiK3CloudClient()
        client.LoginType = None
        with self.assertRaisesRegex(ValueError, "LoginType"):
            client.Login()

        client.LoginType = LoginType.ValidateLogin
        with self.assertRaisesRegex(ValueError, "validateLoginSettingsModel"):
            client.Login()
        client.validateLoginSettingsModel = ValidateLoginSettingsModel()
        with self.assertRaisesRegex(ValueError, "Url"):
            client.Login()

        client.LoginType = LoginType.LoginBySimplePassport
        client.LoginBySimplePassportModel = None
        with self.assertRaisesRegex(ValueError, "LoginBySimplePassportModel"):
            client.Login()

        client.LoginType = LoginType.LoginByApiSignHeaders
        result = client.Login()
        self.assertEqual("", result.RequestUrl)
        self.assertEqual("", result.RealResponseBody)

    def test_auto_login_operation_logout_and_cookie_reuse(self) -> None:
        def respond(request):
            if "AuthService.LoginByAppSecret" in request.path:
                return TestResponse(
                    body='{"LoginResultType":1}',
                    headers={"Set-Cookie": "session=abc; Path=/"},
                )
            return TestResponse()

        with LoopbackServer(respond) as server:
            client = YiK3CloudClient()
            client.LoginType = LoginType.LoginByAppSecret
            client.AppSettingsModel = create_settings(server.k3cloud_url)
            client.Timeout = 5
            response = client.View("TEST_Form", "{}", True, True)
            self.assertEqual('{"ok":true}', response)
            self.assertEqual(3, len(server.requests))
            self.assertIn("AuthService.LoginByAppSecret", server.requests[0].path)
            self.assertIn("DynamicFormService.View", server.requests[1].path)
            self.assertIn("AuthService.Logout", server.requests[2].path)
            self.assertIn("session=abc", server.requests[1].headers.get("Cookie", ""))

    def test_failed_login_does_not_call_operation(self) -> None:
        rejected = '{"LoginResultType":0,"Message":"denied"}'
        with LoopbackServer(lambda _: TestResponse(body=rejected)) as server:
            client = YiK3CloudClient()
            client.LoginType = LoginType.LoginByAppSecret
            client.AppSettingsModel = create_settings(server.k3cloud_url)
            client.Timeout = 5
            self.assertEqual(rejected, client.View("TEST_Form", "{}", True, False))
            self.assertEqual(1, len(server.requests))

    def test_client_dispatches_each_login_mode(self) -> None:
        expected = {
            LoginType.LoginByAppSecret: "LoginByAppSecret",
            LoginType.LoginBySignSHA256: "LoginBySign",
            LoginType.LoginBySignSHA1: "LoginBySign",
            LoginType.ValidateLogin: "ValidateUser.common",
            LoginType.ValidateUserEnDeCode: "ValidateUserEnDeCode",
            LoginType.LoginBySimplePassport: "LoginBySimplePassport",
        }
        for login_type, endpoint in expected.items():
            with (
                self.subTest(login_type=login_type),
                LoopbackServer(lambda _: TestResponse(body='{"LoginResultType":1}')) as server,
            ):
                client = YiK3CloudClient()
                client.LoginType = login_type
                client.AppSettingsModel = create_settings(server.k3cloud_url)
                client.Timeout = 5
                if login_type in (LoginType.ValidateLogin, LoginType.ValidateUserEnDeCode):
                    client.validateLoginSettingsModel = ValidateLoginSettingsModel(
                        server.k3cloud_url,
                        DbId="db",
                        UserName="user",
                        Password="pass",
                    )
                if login_type == LoginType.LoginBySimplePassport:
                    client.LoginBySimplePassportModel = LoginBySimplePassportModel(
                        server.k3cloud_url,
                        SimplePassportForBase64="AQID",
                        bySimplePassportType=BySimplePassportType.ForBase64,
                    )
                result = client.Login()
                self.assertEqual('{"LoginResultType":1}', result.RealResponseBody)
                self.assertIn(endpoint, server.single_request().path)


class ClientApiTests(unittest.TestCase):
    PAYLOAD = '{"Id":123}'
    PREFIX = "Kingdee.BOS.WebApi.ServicesStub.DynamicFormService."

    def test_all_public_api_routes_and_envelopes(self) -> None:
        with LoopbackServer() as server:
            client = create_api_header_client(server.k3cloud_url)
            form_calls = {
                "View": client.View,
                "Save": client.Save,
                "BatchSave": client.BatchSave,
                "Submit": client.Submit,
                "Audit": client.Audit,
                "UnAudit": client.UnAudit,
                "Delete": client.Delete,
                "Draft": client.Draft,
                "Allocate": client.Allocate,
                "Push": client.Push,
                "GroupSave": client.GroupSave,
                "FlexSave": client.FlexSave,
                "GetSysReportData": client.GetSysReportData,
                "CancelAllocate": client.CancelAllocate,
                "CancelAssign": client.CancelAssign,
                "Disassembly": client.Disassembly,
            }
            for operation, function in form_calls.items():
                with self.subTest(operation=operation):
                    response = function("TEST_Form", self.PAYLOAD, False, False)
                    self._assert_last_wrapped(
                        client,
                        server,
                        self.PREFIX + operation + ".common.kdsvc",
                        ["TEST_Form", self.PAYLOAD],
                        response,
                    )

            payload_calls = {
                "ExecuteBillQuery": client.ExecuteBillQuery,
                "SendMsg": client.SendMsg,
                "SwitchOrg": client.SwitchOrg,
                "WorkflowAudit": client.WorkflowAudit,
                "GroupDelete": client.GroupDelete,
                "QueryBusinessInfo": client.QueryBusinessInfo,
                "QueryGroupInfo": client.QueryGroupInfo,
            }
            for operation, function in payload_calls.items():
                with self.subTest(operation=operation):
                    response = function(self.PAYLOAD, False, False)
                    self._assert_last_wrapped(
                        client,
                        server,
                        self.PREFIX + operation + ".common.kdsvc",
                        [self.PAYLOAD],
                        response,
                    )

            raw_calls = {
                "AttachmentUpLoad": client.AttachmentUpLoad,
                "AttachmentDownLoad": client.AttachmentDownLoad,
                "UploadFile": client.UploadFile,
            }
            for operation, function in raw_calls.items():
                with self.subTest(operation=operation):
                    response = function(self.PAYLOAD, False, False)
                    request = server.requests[-1]
                    self.assertEqual(self.PAYLOAD, request.body)
                    self.assertEqual(
                        "/k3cloud/" + self.PREFIX + operation + ".common.kdsvc",
                        request.path,
                    )
                    self.assertEqual('{"ok":true}', response)

    def test_execute_operation_custom_services_and_direct_stub(self) -> None:
        with LoopbackServer() as server:
            client = create_api_header_client(server.k3cloud_url)
            response = client.ExecuteOperation("TEST_Form", "Forbid", self.PAYLOAD, False, False)
            self._assert_last_wrapped(
                client,
                server,
                self.PREFIX + "ExecuteOperation.common.kdsvc",
                ["TEST_Form", "Forbid", self.PAYLOAD],
                response,
            )

            service = "Sample.WebApi.Service.Run,Sample.WebApi"
            client.CustomBusinessService(self.PAYLOAD, service, False, False)
            self._assert_last_wrapped(
                client,
                server,
                service + ".common.kdsvc",
                [self.PAYLOAD],
                '{"ok":true}',
            )
            model = CustomServicesStubpath("Sample.WebApi", "Service", "Run")
            client.CustomBusinessServiceByParameters(self.PAYLOAD, model, False, False)
            self.assertEqual(self.PAYLOAD, server.requests[-1].body)
            self.assertEqual(
                "/k3cloud/Sample.WebApi.Service.Run,Sample.WebApi.common.kdsvc",
                server.requests[-1].path,
            )

            client.ExecApiDynamicFormService(
                "TEST_Form",
                self.PAYLOAD,
                "Custom.Service.Run.common.kdsvc",
                False,
                False,
            )
            self._assert_last_wrapped(
                client,
                server,
                "Custom.Service.Run.common.kdsvc",
                ["TEST_Form", self.PAYLOAD],
                '{"ok":true}',
            )
            self.assertIs(client, YiK3CloudClient.Instance)

    def test_get_data_center_list_uses_override(self) -> None:
        with LoopbackServer() as server:
            client = create_api_header_client("http://unused.invalid/")
            self.assertEqual(
                '{"ok":true}', client.GetDataCenterList(server.k3cloud_url.rstrip("/"))
            )
            self.assertEqual(
                "/k3cloud/Kingdee.BOS.ServiceFacade.ServicesStub.Account.AccountService."
                "GetDataCenterList.common.kdsvc",
                server.single_request().path,
            )

    def _assert_last_wrapped(
        self,
        client: YiK3CloudClient,
        server: LoopbackServer,
        service_path: str,
        expected_parameters: list[str],
        response: str,
    ) -> None:
        self.assertEqual('{"ok":true}', response)
        request = server.requests[-1]
        self.assertEqual("POST", request.method)
        self.assertEqual("/k3cloud/" + service_path, request.path)
        self.assertIn("application/json", request.headers["Content-Type"])
        self.assertIn("X-Kd-Appkey", request.headers)
        parameters = json.loads(json.loads(request.body)["parameters"])
        self.assertEqual(expected_parameters, parameters)
        self.assertEqual(
            server.k3cloud_url + service_path, client.ReturnOperationWebModel.RequestUrl
        )
        self.assertEqual(request.body, client.ReturnOperationWebModel.RealRequestBody)
        self.assertEqual('{"ok":true}', client.ReturnOperationWebModel.RealResponseBody)


if __name__ == "__main__":
    unittest.main()
