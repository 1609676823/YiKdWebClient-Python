"""C#/Java ``YiKdWebClient.SSO`` 兼容命名空间。"""

from yikd_web_client.models import SimplePassportLoginArg as SimplePassportLoginArg
from yikd_web_client.models import SSOLoginUrlObject as SSOLoginUrlObject
from yikd_web_client.models import SSOLogoutObject as SSOLogoutObject
from yikd_web_client.sso import SSOHelper as SSOHelper

__all__ = ["SSOHelper", "SSOLoginUrlObject", "SSOLogoutObject", "SimplePassportLoginArg"]
