"""与 C# ``YiKdWebClient.Model`` 对应的公开模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from requests.cookies import RequestsCookieJar


def normalize_server_url(url: Optional[str]) -> str:
    """为空值返回空字符串，否则保证服务地址以 ``/`` 结尾。"""

    if url is None or not str(url).strip():
        return ""
    value = str(url)
    return value if value.endswith("/") else value + "/"


class LoginType(str, Enum):
    LoginBySignSHA256 = "LoginBySignSHA256"
    LoginBySignSHA1 = "LoginBySignSHA1"
    LoginByAppSecret = "LoginByAppSecret"
    LoginByApiSignHeaders = "ApiSignHeaders"
    ValidateLogin = "ValidateLogin"
    LoginBySimplePassport = "LoginBySimplePassport"
    ValidateUserEnDeCode = "ValidateUserEnDeCode"


class OperationType(str, Enum):
    View = "View"
    Save = "Save"
    BatchSave = "BatchSave"
    Submit = "Submit"
    Audit = "Audit"
    UnAudit = "UnAudit"
    Delete = "Delete"
    ExecuteBillQuery = "ExecuteBillQuery"
    Draft = "Draft"
    Allocate = "Allocate"
    Push = "Push"
    GroupSave = "GroupSave"
    FlexSave = "FlexSave"
    SendMsg = "SendMsg"
    Logout = "Logout"
    ExecuteOperation = "ExecuteOperation"
    SwitchOrg = "SwitchOrg"
    WorkflowAudit = "WorkflowAudit"
    DynamicFormService = "DynamicFormService"


class BySimplePassportType(str, Enum):
    CnfFile = "CnfFile"
    ForBase64 = "ForBase64"


class AppSettingsModel:
    """第三方系统登录授权配置。

    ``path`` 为空时读取 ``YiKdWebCfg/appsettings.xml``。与原项目一致，配置文件
    不存在或内容无效时保留空字符串默认值。
    """

    def __init__(self, path: str = "") -> None:
        self.XKDApiAcctID = ""
        self.XKDApiAppID = ""
        self.XKDApiAppSec = ""
        self.XKDApiUserName = ""
        self.XKDApiLCID = ""
        self._xkd_api_server_url = ""
        self.XKDApiOrgNum = ""

        try:
            from .common import XmlConfigHelper

            values = XmlConfigHelper.GetAllCfgDic(path)
            self.XKDApiAcctID = values.get("X-KDApi-AcctID", "")
            self.XKDApiAppID = values.get("X-KDApi-AppID", "")
            self.XKDApiAppSec = values.get("X-KDApi-AppSec", "")
            self.XKDApiUserName = values.get("X-KDApi-UserName", "")
            self.XKDApiLCID = values.get("X-KDApi-LCID", "")
            self.XKDApiServerUrl = values.get("X-KDApi-ServerUrl", "")
            self.XKDApiOrgNum = values.get("X-KDApi-OrgNum", "")
        except Exception:
            pass

    @property
    def XKDApiServerUrl(self) -> str:
        return self._xkd_api_server_url

    @XKDApiServerUrl.setter
    def XKDApiServerUrl(self, value: Optional[str]) -> None:
        self._xkd_api_server_url = normalize_server_url(value)

    # Python 风格别名。
    account_id = property(
        lambda self: self.XKDApiAcctID, lambda self, v: setattr(self, "XKDApiAcctID", v)
    )
    app_id = property(
        lambda self: self.XKDApiAppID, lambda self, v: setattr(self, "XKDApiAppID", v)
    )
    app_secret = property(
        lambda self: self.XKDApiAppSec, lambda self, v: setattr(self, "XKDApiAppSec", v)
    )
    username = property(
        lambda self: self.XKDApiUserName, lambda self, v: setattr(self, "XKDApiUserName", v)
    )
    language_id = property(
        lambda self: self.XKDApiLCID, lambda self, v: setattr(self, "XKDApiLCID", v)
    )
    server_url = property(
        lambda self: self.XKDApiServerUrl, lambda self, v: setattr(self, "XKDApiServerUrl", v)
    )
    organization_number = property(
        lambda self: self.XKDApiOrgNum, lambda self, v: setattr(self, "XKDApiOrgNum", v)
    )


@dataclass
class CustomServicesStubpath:
    ProjetNamespace: str = ""
    ProjetClassName: str = ""
    ProjetClassMethod: str = ""

    @staticmethod
    def RemoveSpaces(value: Optional[str]) -> str:
        return "" if value is None else value.replace(" ", "")

    def GetCustomServicesStubpathUrl(self) -> str:
        namespace = self.RemoveSpaces(self.ProjetNamespace)
        return (
            f"{namespace}.{self.RemoveSpaces(self.ProjetClassName)}."
            f"{self.RemoveSpaces(self.ProjetClassMethod)},{namespace}.common.kdsvc"
        )

    remove_spaces = RemoveSpaces
    get_custom_services_stubpath_url = GetCustomServicesStubpathUrl


class ValidateLoginSettingsModel:
    def __init__(
        self,
        url: str = "",
        *,
        DbId: str = "",
        UserName: str = "",
        Password: str = "",
        lcid: int = 2052,
    ) -> None:
        self.DbId = DbId
        self.UserName = UserName
        self.Password = Password
        self.lcid = lcid
        self._url = normalize_server_url(url)

    @property
    def Url(self) -> str:
        return self._url

    @Url.setter
    def Url(self, value: Optional[str]) -> None:
        self._url = normalize_server_url(value)

    @staticmethod
    def GetServerUrl(url: Optional[str]) -> str:
        return normalize_server_url(url)

    get_server_url = GetServerUrl


class LoginBySimplePassportModel:
    def __init__(
        self,
        url: str = "",
        *,
        CnfFilePath: str = "",
        SimplePassportForBase64: str = "",
        Lcid: int = 2052,
        bySimplePassportType: BySimplePassportType = BySimplePassportType.CnfFile,
    ) -> None:
        self.Url = normalize_server_url(url)
        self.CnfFilePath = CnfFilePath
        self.SimplePassportForBase64 = SimplePassportForBase64
        self.Lcid = Lcid
        self.bySimplePassportType = bySimplePassportType

    @staticmethod
    def GetServerUrl(url: Optional[str]) -> str:
        return normalize_server_url(url)

    get_server_url = GetServerUrl


@dataclass
class RequestWebModel:
    Cookie: RequestsCookieJar = field(default_factory=RequestsCookieJar)
    RequestUrl: str = ""
    RealRequestBody: str = ""
    RealResponseBody: str = ""


@dataclass
class UploadModelData:
    FileName: str = ""
    FormId: str = ""
    IsLast: bool = False
    InterId: str = ""
    Entrykey: str = ""
    EntryinterId: str = "-1"
    BillNO: str = ""
    AliasFileName: str = ""
    FileId: str = ""
    SendByte: str = ""


@dataclass
class UploadModel:
    data: UploadModelData = field(default_factory=UploadModelData)


@dataclass
class SimplePassportLoginArg:
    dbid: Optional[str] = None
    username: Optional[str] = None
    appid: Optional[str] = None
    signeddata: Optional[str] = None
    timestamp: Optional[str] = None
    lcid: Optional[str] = "2052"
    origintype: Optional[str] = "SimPas"
    entryrole: Optional[str] = ""
    formid: Optional[str] = ""
    formtype: Optional[str] = ""
    pkid: Optional[str] = ""
    otherargs: Optional[str] = ""
    openmode: Optional[str] = None
    loginthen: Optional[str] = None


@dataclass
class SSOLoginUrlObject:
    silverlightUrl: str = ""
    html5Url: str = ""
    wpfUrl: str = ""


@dataclass
class SSOLogoutObject:
    RequestLogoutUrl: str = ""
    ap0: str = ""

    # 保留 C# 中误命名的无操作成员，避免移植代码失效。
    def SSOLoginUrlObject(self) -> None:
        return None


__all__ = [
    "AppSettingsModel",
    "BySimplePassportType",
    "CustomServicesStubpath",
    "LoginBySimplePassportModel",
    "LoginType",
    "OperationType",
    "RequestWebModel",
    "SimplePassportLoginArg",
    "SSOLoginUrlObject",
    "SSOLogoutObject",
    "UploadModel",
    "UploadModelData",
    "ValidateLoginSettingsModel",
    "normalize_server_url",
]
