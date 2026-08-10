"""金蝶云星空登录认证与 API 请求头签名。"""

from __future__ import annotations

import base64
import os
import time
import uuid
from pathlib import Path
from typing import Optional, Union
from urllib.parse import urlsplit

from requests.utils import requote_uri

from .common import CommonFunctionHelper, JsonHelperServices, _json_dumps
from .encryption import EnDecode
from .models import (
    AppSettingsModel,
    BySimplePassportType,
    LoginBySimplePassportModel,
    LoginType,
    RequestWebModel,
    ValidateLoginSettingsModel,
    normalize_server_url,
)
from .transport import WebHelperServices


class _LoginService:
    service_path = ""

    def __init__(self) -> None:
        self.Timeout: Optional[float] = 30
        self.RequestHeaders: dict[str, str] = {}

    def Login(
        self,
        url: str,
        json: str,
        UnsafeRelaxedJsonEscaping: bool = True,
    ) -> RequestWebModel:
        del UnsafeRelaxedJsonEscaping
        result = RequestWebModel()
        result.RequestUrl = normalize_server_url(url) + self.service_path
        result.RealRequestBody = json
        try:
            web = WebHelperServices()
            web.Timeout = self.Timeout
            web.RequestHeaders = self.RequestHeaders
            result.RealResponseBody = web.SendHttpRequest(result.RequestUrl, json)
            result.Cookie = web.cookies
        except Exception as exc:
            result.RealResponseBody = str(exc)
        return result

    login = Login


class LoginByAppSecret(_LoginService):
    service_path = "Kingdee.BOS.WebApi.ServicesStub.AuthService.LoginByAppSecret.common.kdsvc"

    def GetLoginJson(
        self,
        AppSettingsModel: AppSettingsModel,
        UnsafeRelaxedJsonEscaping: bool,
    ) -> str:
        parameters = [
            AppSettingsModel.XKDApiAcctID,
            AppSettingsModel.XKDApiUserName,
            AppSettingsModel.XKDApiAppID,
            AppSettingsModel.XKDApiAppSec,
            AppSettingsModel.XKDApiLCID,
        ]
        content = _json_dumps(parameters, UnsafeRelaxedJsonEscaping)
        return JsonHelperServices.getLoginRequestBodystring(
            content, UnsafeRelaxedJsonEscaping, True
        )

    get_login_json = GetLoginJson


class LoginBySign(_LoginService):
    service_path = "Kingdee.BOS.WebApi.ServicesStub.AuthService.LoginBySign.common.kdsvc"

    def __init__(self) -> None:
        super().__init__()
        self.LoginType = LoginType.LoginBySignSHA256

    def GetLoginJson(
        self,
        AppSettingsModel: AppSettingsModel,
        UnsafeRelaxedJsonEscaping: bool,
    ) -> str:
        timestamp = str(CommonFunctionHelper.GetTimestamp())
        signed_values = [
            AppSettingsModel.XKDApiAcctID,
            AppSettingsModel.XKDApiUserName,
            AppSettingsModel.XKDApiAppID,
            AppSettingsModel.XKDApiAppSec,
            timestamp,
        ]
        if self.LoginType == LoginType.LoginBySignSHA256:
            signature = CommonFunctionHelper.GetSHA256(signed_values)
        elif self.LoginType == LoginType.LoginBySignSHA1:
            signature = CommonFunctionHelper.GetSHA1(signed_values)
        else:
            signature = ""
        parameters = [
            AppSettingsModel.XKDApiAcctID,
            AppSettingsModel.XKDApiUserName,
            AppSettingsModel.XKDApiAppID,
            timestamp,
            signature,
            AppSettingsModel.XKDApiLCID,
        ]
        content = _json_dumps(parameters, UnsafeRelaxedJsonEscaping)
        return JsonHelperServices.getLoginRequestBodystringByParameters(
            content, UnsafeRelaxedJsonEscaping, False
        )

    get_login_json = GetLoginJson


class ValidateLogin(_LoginService):
    service_path = "Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUser.common.kdsvc"

    def GetLoginJson(
        self,
        validateLoginSettingsModel: ValidateLoginSettingsModel,
        UnsafeRelaxedJsonEscaping: bool,
    ) -> str:
        parameters = [
            validateLoginSettingsModel.DbId,
            validateLoginSettingsModel.UserName,
            validateLoginSettingsModel.Password,
            validateLoginSettingsModel.lcid,
        ]
        content = _json_dumps(parameters, UnsafeRelaxedJsonEscaping)
        return JsonHelperServices.getLoginRequestBodystring(
            content, UnsafeRelaxedJsonEscaping, True
        )

    get_login_json = GetLoginJson


class ValidateUserEnDeCode(_LoginService):
    service_path = "Kingdee.BOS.WebApi.ServicesStub.AuthService.ValidateUserEnDeCode.common.kdsvc"

    def GetLoginJson(
        self,
        validateLoginSettingsModel: ValidateLoginSettingsModel,
        UnsafeRelaxedJsonEscaping: bool = True,
    ) -> str:
        parameters = [
            validateLoginSettingsModel.DbId,
            EnDecode.Encode(validateLoginSettingsModel.UserName),
            EnDecode.Encode(validateLoginSettingsModel.Password),
            validateLoginSettingsModel.lcid,
        ]
        content = _json_dumps(parameters, UnsafeRelaxedJsonEscaping)
        return JsonHelperServices.getLoginRequestBodystring(
            content, UnsafeRelaxedJsonEscaping, True
        )

    get_login_json = GetLoginJson


class LoginBySimplePassport(_LoginService):
    service_path = "Kingdee.BOS.WebApi.ServicesStub.AuthService.LoginBySimplePassport.common.kdsvc"

    @staticmethod
    def GetCnfBytes(cnffilepath: Union[str, Path]) -> bytes:
        return Path(cnffilepath).read_bytes()

    def GetPassportForBase64(self, cnffilepath: Union[str, Path]) -> str:
        return base64.b64encode(self.GetCnfBytes(cnffilepath)).decode("ascii")

    def GetLoginJson(
        self,
        loginBySimplePassportModel: LoginBySimplePassportModel,
        UnsafeRelaxedJsonEscaping: bool,
    ) -> str:
        if loginBySimplePassportModel.bySimplePassportType == BySimplePassportType.CnfFile:
            if not loginBySimplePassportModel.CnfFilePath.strip():
                raise ValueError("CnfFile类型下,loginBySimplePassportModel.CnfFilePath必须传值")
            passport = self.GetPassportForBase64(loginBySimplePassportModel.CnfFilePath)
            loginBySimplePassportModel.SimplePassportForBase64 = passport
        elif loginBySimplePassportModel.bySimplePassportType == BySimplePassportType.ForBase64:
            if not loginBySimplePassportModel.SimplePassportForBase64.strip():
                raise ValueError(
                    "ForBase64类型下,loginBySimplePassportModel.SimplePassportForBase64必须传值"
                )
            passport = loginBySimplePassportModel.SimplePassportForBase64
        else:
            raise ValueError("未知的 bySimplePassportType")

        content = _json_dumps(
            [passport, loginBySimplePassportModel.Lcid],
            UnsafeRelaxedJsonEscaping,
        )
        return JsonHelperServices.getLoginRequestBodystring(
            content, UnsafeRelaxedJsonEscaping, True
        )

    get_cnf_bytes = GetCnfBytes
    get_passport_for_base64 = GetPassportForBase64
    get_login_json = GetLoginJson


class LoginByApiSignHeaders:
    @staticmethod
    def GetApiHeaders(*args: object) -> dict[str, str]:
        if len(args) == 1:
            settings = AppSettingsModel()
            uri = str(args[0])
        elif len(args) == 2 and isinstance(args[0], AppSettingsModel):
            settings = args[0]
            uri = str(args[1])
        else:
            raise TypeError("GetApiHeaders 接受 (uri) 或 (AppSettingsModel, uri)")

        headers: dict[str, str] = {}
        timestamp = str(time.time_ns() // 1_000_000)
        nonce = uuid.uuid4().hex
        app_id = settings.XKDApiAppID

        if "_" in app_id:
            client_id, encoded_secret = app_id.split("_", 1)
            api_secret = EnDecode.DecryptAppSecret(encoded_secret)
            if client_id.strip():
                headers.update(
                    {
                        "X-Api-ClientID": client_id,
                        "X-Api-Auth-Version": "2.0",
                        "x-api-signheaders": "x-api-timestamp,x-api-nonce",
                        "x-api-nonce": nonce,
                        "x-api-timestamp": timestamp,
                    }
                )
                # .NET ``Uri.PathAndQuery`` 使用规范化后的转义形式；先 requote
                # 可让空格和非 ASCII 路径与 C#/Java 的签名输入保持一致。
                parsed = urlsplit(requote_uri(uri))
                path_and_query = parsed.path + (f"?{parsed.query}" if parsed.query else "")
                message = (
                    "POST\n"
                    + EnDecode.UrlEncodeWithUpperCode(path_and_query, "ascii")
                    + "\n\n"
                    + f"x-api-nonce:{nonce}\n"
                    + f"x-api-timestamp:{timestamp}\n"
                )
                headers["X-Api-Signature"] = EnDecode.HmacSHA256(message, api_secret, "ascii", True)

        headers["X-Kd-Appkey"] = app_id
        app_data = ",".join(
            [
                settings.XKDApiAcctID,
                settings.XKDApiUserName,
                settings.XKDApiLCID,
                settings.XKDApiOrgNum,
            ]
        )
        headers["X-Kd-Appdata"] = base64.b64encode(app_data.encode("utf-8")).decode("ascii")
        headers["X-Kd-Signature"] = EnDecode.HmacSHA256(
            app_id + app_data, settings.XKDApiAppSec, "utf-8", True
        )
        return headers

    @staticmethod
    def GetApiHeadersStr(HeadersDictionary: Optional[dict[str, str]]) -> str:
        if not HeadersDictionary:
            return ""
        return "".join(f"{key}:{value}{os.linesep}" for key, value in HeadersDictionary.items())

    get_api_headers = GetApiHeaders
    get_api_headers_string = GetApiHeadersStr


__all__ = [
    "LoginByApiSignHeaders",
    "LoginByAppSecret",
    "LoginBySign",
    "LoginBySimplePassport",
    "ValidateLogin",
    "ValidateUserEnDeCode",
]
