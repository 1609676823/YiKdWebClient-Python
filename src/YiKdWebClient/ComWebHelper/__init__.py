"""C#/Java ``YiKdWebClient.ComWebHelper`` 兼容命名空间。"""

from yikd_web_client.media_types import BodyType as BodyType
from yikd_web_client.media_types import CustomMediaTypeNames as CustomMediaTypeNames
from yikd_web_client.media_types import HttpMethod as HttpMethod
from yikd_web_client.transport import MultipartFormData as MultipartFormData
from yikd_web_client.transport import WebHelper as WebHelper

__all__ = [
    "BodyType",
    "CustomMediaTypeNames",
    "HttpMethod",
    "MultipartFormData",
    "WebHelper",
]
