"""C#/Java ``YiKdWebClient.AuthService`` 兼容命名空间。"""

from yikd_web_client.auth import LoginByApiSignHeaders as LoginByApiSignHeaders
from yikd_web_client.auth import LoginByAppSecret as LoginByAppSecret
from yikd_web_client.auth import LoginBySign as LoginBySign
from yikd_web_client.auth import LoginBySimplePassport as LoginBySimplePassport
from yikd_web_client.auth import ValidateLogin as ValidateLogin
from yikd_web_client.auth import ValidateUserEnDeCode as ValidateUserEnDeCode

__all__ = [
    "LoginByApiSignHeaders",
    "LoginByAppSecret",
    "LoginBySign",
    "LoginBySimplePassport",
    "ValidateLogin",
    "ValidateUserEnDeCode",
]
