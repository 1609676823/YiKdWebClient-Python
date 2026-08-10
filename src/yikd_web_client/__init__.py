"""YiKdWebClient Python API。"""

from .attachments import AttachmentHelper, FileChunk
from .auth import (
    LoginByApiSignHeaders,
    LoginByAppSecret,
    LoginBySign,
    LoginBySimplePassport,
    ValidateLogin,
    ValidateUserEnDeCode,
)
from .client import YiK3CloudClient
from .common import CommonFunctionHelper, JsonHelperServices, XmlConfigHelper
from .encryption import EnDecode
from .media_types import BodyType, CustomMediaTypeNames, HttpMethod
from .models import (
    AppSettingsModel,
    BySimplePassportType,
    CustomServicesStubpath,
    LoginBySimplePassportModel,
    LoginType,
    OperationType,
    RequestWebModel,
    SimplePassportLoginArg,
    SSOLoginUrlObject,
    SSOLogoutObject,
    UploadModel,
    UploadModelData,
    ValidateLoginSettingsModel,
)
from .sso import SSOHelper
from .transport import MultipartFormData, WebHelper, WebHelperServices

__version__ = "1.0.0.32"

__all__ = [
    "AppSettingsModel",
    "AttachmentHelper",
    "BodyType",
    "BySimplePassportType",
    "CommonFunctionHelper",
    "CustomMediaTypeNames",
    "CustomServicesStubpath",
    "EnDecode",
    "FileChunk",
    "HttpMethod",
    "JsonHelperServices",
    "LoginByApiSignHeaders",
    "LoginByAppSecret",
    "LoginBySign",
    "LoginBySimplePassport",
    "LoginBySimplePassportModel",
    "LoginType",
    "MultipartFormData",
    "OperationType",
    "RequestWebModel",
    "SimplePassportLoginArg",
    "SSOHelper",
    "SSOLoginUrlObject",
    "SSOLogoutObject",
    "UploadModel",
    "UploadModelData",
    "ValidateLogin",
    "ValidateLoginSettingsModel",
    "ValidateUserEnDeCode",
    "WebHelper",
    "WebHelperServices",
    "XmlConfigHelper",
    "YiK3CloudClient",
    "__version__",
]
