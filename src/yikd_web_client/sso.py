"""单点登录 V1–V4 URL 与退出报文。"""

from __future__ import annotations

import base64
from dataclasses import asdict
from typing import Optional
from urllib.parse import urlsplit

from .common import CommonFunctionHelper, _json_dumps
from .media_types import BodyType
from .models import (
    AppSettingsModel,
    SimplePassportLoginArg,
    SSOLoginUrlObject,
    SSOLogoutObject,
    normalize_server_url,
)
from .transport import WebHelper


class SSOHelper:
    def __init__(self) -> None:
        self.timestamp: Optional[int] = None
        self.argJosn: Optional[str] = ""
        self.argJsonBase64: Optional[str] = ""
        self.permitcount: Optional[str] = ""
        self.UnsafeRelaxedJsonEscaping = True
        self.simplePassportLoginArg = SimplePassportLoginArg()
        self.SSOLoginUrlObject = SSOLoginUrlObject()
        self.appSettingsModel = AppSettingsModel()
        self._url = ""
        self.SSOLogoutObject = SSOLogoutObject()
        self._init_login_args()

    @property
    def Url(self) -> str:
        return self._url

    @Url.setter
    def Url(self, value: Optional[str]) -> None:
        self._url = normalize_server_url(value)

    def _init_login_args(self) -> None:
        settings = self.appSettingsModel
        self.Url = settings.XKDApiServerUrl
        self.simplePassportLoginArg = SimplePassportLoginArg(
            dbid=settings.XKDApiAcctID,
            appid=settings.XKDApiAppID,
            username=settings.XKDApiUserName,
            lcid=settings.XKDApiLCID,
        )

    def _server_url(self, override: str) -> str:
        return normalize_server_url(override) if override and override.strip() else self.Url

    def _signature_values(self, username: str, timestamp: str) -> list[str]:
        settings = self.appSettingsModel
        return [
            settings.XKDApiAcctID,
            username,
            settings.XKDApiAppID,
            settings.XKDApiAppSec,
            timestamp,
        ]

    def _make_urls(self, server_url: str, encoded: str) -> SSOLoginUrlObject:
        parsed = urlsplit(server_url)
        port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        host_port = f"{parsed.hostname or ''}:{port}"
        return SSOLoginUrlObject(
            silverlightUrl=server_url + "Silverlight/index.aspx?ud=" + encoded,
            html5Url=server_url + "html5/index.aspx?ud=" + encoded,
            wpfUrl=(
                f"K3cloud://{host_port}/k3cloud/Clientbin/K3cloudclient/"
                f"K3cloudclient.manifest?Lcid=2052&ExeType=WPFRUNTIME&LoginUrl="
                f"{server_url}&ud={encoded}"
            ),
        )

    def _get_json_sso_urls(self, version: int, usserName: str, url: str) -> SSOLoginUrlObject:
        server_url = self._server_url(url)
        username = usserName or self.appSettingsModel.XKDApiUserName
        self.timestamp = CommonFunctionHelper.GetTimestamp()
        timestamp = str(self.timestamp)
        values = self._signature_values(username, timestamp)

        if version in (3, 4) and self.permitcount and self.permitcount.strip():
            values.append(self.permitcount)
            self.simplePassportLoginArg.otherargs = f"|{{'permitcount':'{self.permitcount}'}}"

        signature = (
            CommonFunctionHelper.Sha256Hex("".join(sorted(values)))
            if version == 4
            else CommonFunctionHelper.GetSignatureSHA1Util(values)
        )

        settings = self.appSettingsModel
        args = self.simplePassportLoginArg
        args.dbid = settings.XKDApiAcctID
        args.appid = settings.XKDApiAppID
        args.username = username
        args.lcid = settings.XKDApiLCID
        args.signeddata = signature
        args.timestamp = timestamp
        self.Url = server_url
        self.argJosn = _json_dumps(asdict(args), self.UnsafeRelaxedJsonEscaping)
        self.argJsonBase64 = base64.b64encode(self.argJosn.encode("utf-8")).decode("ascii")
        self.SSOLoginUrlObject = self._make_urls(self.Url, self.argJsonBase64)
        return self.SSOLoginUrlObject

    def GetSsoUrlsV4(self, usserName: str = "", url: str = "") -> SSOLoginUrlObject:
        return self._get_json_sso_urls(4, usserName, url)

    def GetSsoUrlsV3(self, usserName: str = "", url: str = "") -> SSOLoginUrlObject:
        return self._get_json_sso_urls(3, usserName, url)

    def GetSsoUrlsV2(self, usserName: str = "", url: str = "") -> SSOLoginUrlObject:
        return self._get_json_sso_urls(2, usserName, url)

    def GetSsoUrlsV1(self, usserName: str = "", url: str = "") -> SSOLoginUrlObject:
        server_url = self._server_url(url)
        username = usserName or self.appSettingsModel.XKDApiUserName
        self.timestamp = CommonFunctionHelper.GetTimestamp()
        timestamp = str(self.timestamp)
        signature = CommonFunctionHelper.GetSignatureSHA1Util(
            self._signature_values(username, timestamp)
        )
        settings = self.appSettingsModel
        payload = (
            f"|{settings.XKDApiAcctID}|{username}|{settings.XKDApiAppID}|"
            f"{signature}|{timestamp}|{settings.XKDApiLCID}"
        )
        self.argJosn = "V1版本构建参数(非json): \n" + payload + "\n"
        self.argJsonBase64 = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        self.Url = server_url
        self.SSOLoginUrlObject = self._make_urls(self.Url, self.argJsonBase64)
        return self.SSOLoginUrlObject

    def _get_logout(self, version: int, usserName: str, url: str) -> SSOLogoutObject:
        server_url = self._server_url(url)
        username = usserName or self.appSettingsModel.XKDApiUserName
        timestamp = CommonFunctionHelper.GetTimestamp()
        values = self._signature_values(username, str(timestamp))
        signature = (
            CommonFunctionHelper.Sha256Hex("".join(sorted(values)))
            if version == 4
            else CommonFunctionHelper.GetSignatureSHA1Util(values)
        )
        payload = {
            "AcctID": self.appSettingsModel.XKDApiAcctID,
            "AppId": self.appSettingsModel.XKDApiAppID,
            "Username": username,
            "SignedData": signature,
            "Timestamp": timestamp,
        }
        self.SSOLogoutObject = SSOLogoutObject(
            RequestLogoutUrl=(
                server_url + "Kingdee.BOS.ServiceFacade.ServicesStub.User.UserService."
                "LogoutByOtherSystem.common.kdsvc"
            ),
            ap0=_json_dumps(payload, self.UnsafeRelaxedJsonEscaping),
        )
        return self.SSOLogoutObject

    def GetSSOLogoutap0StrV4(self, usserName: str = "", url: str = "") -> SSOLogoutObject:
        return self._get_logout(4, usserName, url)

    def GetSSOLogoutap0StrV3(self, usserName: str = "", url: str = "") -> SSOLogoutObject:
        return self._get_logout(3, usserName, url)

    def GetSSOLogoutap0StrV2V1(self, usserName: str = "", url: str = "") -> SSOLogoutObject:
        return self._get_logout(2, usserName, url)

    def SSOExcuteLogout(self, sSOLogoutObject: SSOLogoutObject) -> str:
        try:
            web = WebHelper()
            web.Timeout = 30
            web.Body_UrlEncoded = {"ap0": sSOLogoutObject.ap0}
            web.bodyType = BodyType.urlencoded
            return web.SendHttpRequest(sSOLogoutObject.RequestLogoutUrl)
        except Exception as exc:
            return str(exc)

    get_sso_urls_v4 = GetSsoUrlsV4
    get_sso_urls_v3 = GetSsoUrlsV3
    get_sso_urls_v2 = GetSsoUrlsV2
    get_sso_urls_v1 = GetSsoUrlsV1
    get_sso_logout_v4 = GetSSOLogoutap0StrV4
    get_sso_logout_v3 = GetSSOLogoutap0StrV3
    get_sso_logout_v2_v1 = GetSSOLogoutap0StrV2V1
    execute_logout = SSOExcuteLogout


__all__ = ["SSOHelper", "SimplePassportLoginArg", "SSOLoginUrlObject", "SSOLogoutObject"]
