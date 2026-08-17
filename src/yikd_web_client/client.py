"""金蝶云星空 WebAPI 主客户端。"""

from __future__ import annotations

import json as json_module
from typing import ClassVar, Optional, Union

from requests.cookies import RequestsCookieJar

from .auth import (
    LoginByApiSignHeaders,
    LoginByAppSecret,
    LoginBySign,
    LoginBySimplePassport,
    ValidateLogin,
    ValidateUserEnDeCode,
)
from .common import CommonFunctionHelper, JsonHelperServices
from .models import (
    AppSettingsModel,
    CustomServicesStubpath,
    LoginBySimplePassportModel,
    LoginType,
    RequestWebModel,
    ValidateLoginSettingsModel,
)
from .transport import WebHelperServices


class YiK3CloudClient:
    """与 C# ``YiK3CloudClient`` 对应的同步客户端。"""

    Instance: ClassVar[Optional["YiK3CloudClient"]] = None
    _DYNAMIC_FORM_PREFIX = "Kingdee.BOS.WebApi.ServicesStub.DynamicFormService."

    def __init__(self) -> None:
        self.Cookie = RequestsCookieJar()
        self.RequestHeaders: dict[str, str] = {}
        self.RequestHeadersString = ""
        self.LoginType: Optional[LoginType] = LoginType.LoginByAppSecret
        self.AppSettingsModel = AppSettingsModel()
        self.ReturnLoginWebModel = RequestWebModel()
        self.ReturnOperationWebModel = RequestWebModel()
        self.UnsafeRelaxedJsonEscaping = True
        self.Timeout: Optional[float] = 60
        self.validateLoginSettingsModel: Optional[ValidateLoginSettingsModel] = None
        self.LoginBySimplePassportModel: Optional[LoginBySimplePassportModel] = None
        self._disposed = False

    def _operation_base_url(self) -> str:
        if self.LoginType in (LoginType.ValidateLogin, LoginType.ValidateUserEnDeCode):
            if self.validateLoginSettingsModel is None:
                raise ValueError("validateLoginSettingsModel 需要实例化赋值")
            return self.validateLoginSettingsModel.Url
        if self.LoginType == LoginType.LoginBySimplePassport:
            if self.LoginBySimplePassportModel is None:
                raise ValueError("LoginBySimplePassportModel 需要实例化赋值")
            return self.LoginBySimplePassportModel.Url
        return self.AppSettingsModel.XKDApiServerUrl

    def _exec_services_stub_by_form_id(
        self,
        formid: str,
        json: str,
        services_stub_path: str,
        op_number: str = "",
        use_raw_json: bool = False,
    ) -> str:
        if self.LoginType is None:
            raise ValueError("LoginType is not null")

        api_url = self._operation_base_url() + services_stub_path
        web = WebHelperServices()
        if self.LoginType == LoginType.LoginByApiSignHeaders:
            api_headers = LoginByApiSignHeaders.GetApiHeaders(self.AppSettingsModel, api_url)
            self.RequestHeaders = api_headers
            self.RequestHeadersString = LoginByApiSignHeaders.GetApiHeadersStr(api_headers)
        else:
            web.cookies = self.Cookie

        web.Timeout = self.Timeout
        web.RequestHeaders = self.RequestHeaders
        request_body = (
            json
            if use_raw_json
            else JsonHelperServices.getRequestBodystring(
                formid,
                json,
                self.UnsafeRelaxedJsonEscaping,
                op_number,
            )
        )
        self.ReturnOperationWebModel.RequestUrl = api_url
        self.ReturnOperationWebModel.RealRequestBody = request_body
        response = web.SendHttpRequest(api_url, request_body)
        self.ReturnOperationWebModel.RealResponseBody = response
        self.ReturnOperationWebModel.Cookie = web.cookies
        self.Cookie = web.cookies
        return response

    def _ensure_logged_in(self, auto_login: bool) -> Optional[str]:
        if self.LoginType is None:
            raise ValueError("LoginType is not null")
        if self.LoginType == LoginType.LoginByApiSignHeaders:
            return None
        try:
            if auto_login:
                self.Login()
            login_result = ""
            try:
                body = json_module.loads(self.ReturnLoginWebModel.RealResponseBody)
                value = body.get("LoginResultType") if isinstance(body, dict) else None
                login_result = "" if value is None else str(value)
            except Exception:
                pass
            return (
                None
                if login_result.casefold() == "1"
                else self.ReturnLoginWebModel.RealResponseBody
            )
        except Exception as exc:
            return str(exc)

    def ExecApiDynamicFormService(
        self,
        formid: str,
        json: str,
        ServicesStubpath: str,
        AutoLogin: bool = True,
        AutoLogout: bool = True,
        userawjson: bool = False,
    ) -> str:
        YiK3CloudClient.Instance = self
        failure = self._ensure_logged_in(AutoLogin)
        if failure is not None:
            return failure
        try:
            response = self._exec_services_stub_by_form_id(
                formid, json, ServicesStubpath, "", userawjson
            )
            if AutoLogout:
                self.Logout()
            return response
        except Exception as exc:
            return str(exc)

    def Login(self) -> RequestWebModel:
        if self.LoginType is None:
            raise ValueError("LoginType is not null")

        request = RequestWebModel()
        if self.LoginType == LoginType.LoginByApiSignHeaders:
            return request

        if self.LoginType == LoginType.LoginByAppSecret:
            service = LoginByAppSecret()
            settings = self.AppSettingsModel
            login_json = service.GetLoginJson(settings, self.UnsafeRelaxedJsonEscaping)
            login_url = settings.XKDApiServerUrl
        elif self.LoginType in (LoginType.LoginBySignSHA256, LoginType.LoginBySignSHA1):
            service = LoginBySign()
            service.LoginType = self.LoginType
            settings = self.AppSettingsModel
            login_json = service.GetLoginJson(settings, self.UnsafeRelaxedJsonEscaping)
            login_url = settings.XKDApiServerUrl
        elif self.LoginType == LoginType.ValidateLogin:
            self._require_validate_settings("ValidateLogin")
            service = ValidateLogin()
            assert self.validateLoginSettingsModel is not None
            login_json = service.GetLoginJson(
                self.validateLoginSettingsModel, self.UnsafeRelaxedJsonEscaping
            )
            login_url = self.validateLoginSettingsModel.Url
        elif self.LoginType == LoginType.ValidateUserEnDeCode:
            self._require_validate_settings("ValidateUserEnDeCode")
            service = ValidateUserEnDeCode()
            assert self.validateLoginSettingsModel is not None
            login_json = service.GetLoginJson(
                self.validateLoginSettingsModel, self.UnsafeRelaxedJsonEscaping
            )
            login_url = self.validateLoginSettingsModel.Url
        elif self.LoginType == LoginType.LoginBySimplePassport:
            self._require_simple_passport_settings()
            service = LoginBySimplePassport()
            assert self.LoginBySimplePassportModel is not None
            login_json = service.GetLoginJson(
                self.LoginBySimplePassportModel, self.UnsafeRelaxedJsonEscaping
            )
            login_url = self.LoginBySimplePassportModel.Url
        else:
            raise ValueError(f"Unsupported LoginType: {self.LoginType}")

        service.Timeout = self.Timeout
        service.RequestHeaders = self.RequestHeaders
        self.ReturnLoginWebModel.RealRequestBody = login_json
        request = service.Login(login_url, login_json, True)
        self.Cookie = request.Cookie
        self.ReturnLoginWebModel = request
        return request

    def _require_validate_settings(self, login_name: str) -> None:
        if self.validateLoginSettingsModel is None:
            raise ValueError(
                f"LoginType使用{login_name}方式的时候，validateLoginSettingsModel 需要实例化赋值"
            )
        if not self.validateLoginSettingsModel.Url.strip():
            raise ValueError(
                f"LoginType使用{login_name}方式的时候，validateLoginSettingsModel.Url需要赋值"
            )

    def _require_simple_passport_settings(self) -> None:
        if self.LoginBySimplePassportModel is None:
            raise ValueError(
                "LoginType使用LoginBySimplePassport方式的时候，LoginBySimplePassportModel需要实例化赋值"
            )
        if not self.LoginBySimplePassportModel.Url.strip():
            raise ValueError(
                "LoginType使用LoginBySimplePassport方式的时候，LoginBySimplePassportModel.Url需要赋值"
            )

    def Logout(self) -> None:
        try:
            web = WebHelperServices()
            web.cookies = self.Cookie
            web.Timeout = self.Timeout
            web.RequestHeaders = self.RequestHeaders
            api_url = (
                self.AppSettingsModel.XKDApiServerUrl
                + "Kingdee.BOS.WebApi.ServicesStub.AuthService.Logout.common.kdsvc"
            )
            web.SendHttpRequest(api_url)
            self.Cookie = web.cookies
        except Exception:
            # 与原项目一致，登出失败不覆盖业务调用结果。
            pass

    def ExecuteOperation(
        self,
        formid: str,
        opNumber: str,
        json: str,
        AutoLogin: bool = True,
        AutoLogout: bool = True,
    ) -> str:
        failure = self._ensure_logged_in(AutoLogin)
        if failure is not None:
            return failure
        try:
            response = self._exec_services_stub_by_form_id(
                formid,
                json,
                self._dynamic_form_path("ExecuteOperation"),
                opNumber,
            )
            if AutoLogout:
                self.Logout()
            return response
        except Exception as exc:
            return str(exc)

    @classmethod
    def _dynamic_form_path(cls, operation: str) -> str:
        return cls._DYNAMIC_FORM_PREFIX + operation + ".common.kdsvc"

    def _call_form(
        self,
        operation: str,
        formid: str,
        json: str,
        AutoLogin: bool,
        AutoLogout: bool,
    ) -> str:
        return self.ExecApiDynamicFormService(
            formid, json, self._dynamic_form_path(operation), AutoLogin, AutoLogout
        )

    def _call_payload(self, operation: str, json: str, AutoLogin: bool, AutoLogout: bool) -> str:
        return self.ExecApiDynamicFormService(
            "", json, self._dynamic_form_path(operation), AutoLogin, AutoLogout
        )

    def _call_raw(self, operation: str, json: str, AutoLogin: bool, AutoLogout: bool) -> str:
        return self.ExecApiDynamicFormService(
            "", json, self._dynamic_form_path(operation), AutoLogin, AutoLogout, True
        )

    def View(self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_form("View", formid, json, AutoLogin, AutoLogout)

    def Save(self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_form("Save", formid, json, AutoLogin, AutoLogout)

    def BatchSave(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("BatchSave", formid, json, AutoLogin, AutoLogout)

    def Submit(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("Submit", formid, json, AutoLogin, AutoLogout)

    def Audit(self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_form("Audit", formid, json, AutoLogin, AutoLogout)

    def UnAudit(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("UnAudit", formid, json, AutoLogin, AutoLogout)

    def Delete(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("Delete", formid, json, AutoLogin, AutoLogout)

    def ExecuteBillQuery(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_payload("ExecuteBillQuery", json, AutoLogin, AutoLogout)

    def CustomBusinessService(
        self,
        json: str,
        apiname: Union[str, CustomServicesStubpath],
        AutoLogin: bool = True,
        AutoLogout: bool = True,
    ) -> str:
        service_path = (
            apiname.GetCustomServicesStubpathUrl()
            if isinstance(apiname, CustomServicesStubpath)
            else self.EnsureSuffixServicesStub(apiname)
        )
        return self.ExecApiDynamicFormService("", json, service_path, AutoLogin, AutoLogout)

    def CustomBusinessServiceByParameters(
        self,
        json: str,
        apiname: Union[str, CustomServicesStubpath],
        AutoLogin: bool = True,
        AutoLogout: bool = True,
    ) -> str:
        service_path = (
            apiname.GetCustomServicesStubpathUrl()
            if isinstance(apiname, CustomServicesStubpath)
            else self.EnsureSuffixServicesStub(apiname)
        )
        return self.ExecApiDynamicFormService("", json, service_path, AutoLogin, AutoLogout, True)

    def Draft(self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_form("Draft", formid, json, AutoLogin, AutoLogout)

    def Allocate(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("Allocate", formid, json, AutoLogin, AutoLogout)

    def Push(self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_form("Push", formid, json, AutoLogin, AutoLogout)

    def GroupSave(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("GroupSave", formid, json, AutoLogin, AutoLogout)

    def FlexSave(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("FlexSave", formid, json, AutoLogin, AutoLogout)

    def SendMsg(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_payload("SendMsg", json, AutoLogin, AutoLogout)

    def SwitchOrg(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_payload("SwitchOrg", json, AutoLogin, AutoLogout)

    def WorkflowAudit(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_payload("WorkflowAudit", json, AutoLogin, AutoLogout)

    def GetSysReportData(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("GetSysReportData", formid, json, AutoLogin, AutoLogout)

    def AttachmentUpLoad(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_raw("AttachmentUpLoad", json, AutoLogin, AutoLogout)

    def AttachmentDownLoad(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_raw("AttachmentDownLoad", json, AutoLogin, AutoLogout)

    def UploadFile(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_raw("UploadFile", json, AutoLogin, AutoLogout)

    def GroupDelete(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_payload("GroupDelete", json, AutoLogin, AutoLogout)

    def CancelAllocate(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("CancelAllocate", formid, json, AutoLogin, AutoLogout)

    def CancelAssign(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("CancelAssign", formid, json, AutoLogin, AutoLogout)

    def Disassembly(
        self, formid: str, json: str, AutoLogin: bool = True, AutoLogout: bool = True
    ) -> str:
        return self._call_form("Disassembly", formid, json, AutoLogin, AutoLogout)

    def QueryBusinessInfo(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_payload("QueryBusinessInfo", json, AutoLogin, AutoLogout)

    def QueryGroupInfo(self, json: str, AutoLogin: bool = True, AutoLogout: bool = True) -> str:
        return self._call_payload("QueryGroupInfo", json, AutoLogin, AutoLogout)

    def GetDataCenterList(self, url: str = "") -> str:
        try:
            web = WebHelperServices()
            web.cookies = self.Cookie
            web.Timeout = self.Timeout
            web.RequestHeaders = self.RequestHeaders
            base_url = (
                CommonFunctionHelper.GetServerUrl(url)
                if url and url.strip()
                else self.AppSettingsModel.XKDApiServerUrl
            )
            api_url = (
                base_url + "Kingdee.BOS.ServiceFacade.ServicesStub.Account.AccountService."
                "GetDataCenterList.common.kdsvc"
            )
            return web.SendHttpRequest(api_url)
        except Exception as exc:
            return str(exc)

    @staticmethod
    def GetServerUrl(url: str) -> str:
        return CommonFunctionHelper.GetServerUrl(url)

    @staticmethod
    def EnsureSuffixServicesStub(input: str, suffix: str = ".common.kdsvc") -> str:
        return input if input.endswith(suffix) else input + suffix

    def Dispose(self) -> None:
        if not self._disposed:
            self.LoginType = None
            self._disposed = True

    def close(self) -> None:
        self.Dispose()

    def __enter__(self) -> "YiK3CloudClient":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.Dispose()

    # Python 风格方法名。
    exec_api_dynamic_form_service = ExecApiDynamicFormService
    login = Login
    logout = Logout
    execute_operation = ExecuteOperation
    view = View
    save = Save
    batch_save = BatchSave
    submit = Submit
    audit = Audit
    unaudit = UnAudit
    delete = Delete
    execute_bill_query = ExecuteBillQuery
    custom_business_service = CustomBusinessService
    custom_business_service_by_parameters = CustomBusinessServiceByParameters
    draft = Draft
    allocate = Allocate
    push = Push
    group_save = GroupSave
    flex_save = FlexSave
    send_message = SendMsg
    switch_organization = SwitchOrg
    workflow_audit = WorkflowAudit
    get_system_report_data = GetSysReportData
    attachment_upload = AttachmentUpLoad
    attachment_download = AttachmentDownLoad
    upload_file = UploadFile
    group_delete = GroupDelete
    cancel_allocate = CancelAllocate
    cancel_assign = CancelAssign
    disassembly = Disassembly
    query_business_info = QueryBusinessInfo
    query_group_info = QueryGroupInfo
    get_data_center_list = GetDataCenterList
    get_server_url = GetServerUrl
    ensure_suffix_services_stub = EnsureSuffixServicesStub
    dispose = Dispose


__all__ = ["YiK3CloudClient"]
