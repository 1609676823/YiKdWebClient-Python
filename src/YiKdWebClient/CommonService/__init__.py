"""C#/Java ``YiKdWebClient.CommonService`` 兼容命名空间。"""

from yikd_web_client.common import JsonHelperServices as JsonHelperServices
from yikd_web_client.common import XmlConfigHelper as XmlConfigHelper
from yikd_web_client.transport import WebHelperServices as WebHelperServices

__all__ = ["JsonHelperServices", "WebHelperServices", "XmlConfigHelper"]
