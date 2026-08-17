"""与原项目兼容的签名、编码和旧版 DES 工具。"""

from __future__ import annotations

import base64
import codecs
import hashlib
import hmac
import re
from typing import Optional
from urllib.parse import quote_plus

from Crypto.Cipher import DES
from Crypto.Util.Padding import pad


class EnDecode:
    _DES_KEY = b"KingdeeK"
    _XOR_KEY = b"0054f397c6234378b09ca7d3e5debce7"

    @staticmethod
    def Encode(data: object) -> str:
        try:
            raw = str(data).encode("utf-8")
            cipher = DES.new(EnDecode._DES_KEY, DES.MODE_CBC, iv=EnDecode._DES_KEY)
            return base64.b64encode(cipher.encrypt(pad(raw, DES.block_size))).decode("ascii")
        except Exception as exc:
            return str(exc)

    @staticmethod
    def EncodeNew1(data: object) -> str:
        return EnDecode.Encode(data)

    @staticmethod
    def HmacSHA256(
        message: str,
        secret: Optional[str],
        encoding: str = "utf-8",
        isHex: bool = False,
    ) -> str:
        key = (secret or "").encode(encoding)
        digest = hmac.new(key, message.encode(encoding), hashlib.sha256).digest()
        if isHex:
            return base64.b64encode(digest.hex().encode(encoding)).decode("ascii")
        return base64.b64encode(digest).decode("ascii")

    @staticmethod
    def ByteToHexStr(data: Optional[bytes]) -> str:
        return "" if data is None else data.hex().upper()

    @staticmethod
    def EncryptAppSecret(appSecret: str) -> str:
        if re.fullmatch(r"[0-9a-zA-Z]{32}", appSecret):
            decoded = base64.b64decode(appSecret, validate=True)
            return base64.b64encode(EnDecode._xor_encode(decoded)).decode("ascii")
        return codecs.encode(appSecret, "rot_13")

    @staticmethod
    def DecryptAppSecret(appSecret: str) -> str:
        if len(appSecret) == 32:
            decoded = base64.b64decode(appSecret, validate=True)
            return base64.b64encode(EnDecode._xor_encode(decoded)).decode("ascii")
        return codecs.encode(appSecret, "rot_13")

    @staticmethod
    def _xor_encode(data: bytes) -> bytes:
        return bytes(value ^ EnDecode._XOR_KEY[index] for index, value in enumerate(data))

    @staticmethod
    def UrlEncodeWithUpperCode(value: str, encoding: str = "utf-8") -> str:
        # urllib 的百分号转义本身即为大写；safe="" 对应 HttpUtility.UrlEncode。
        return quote_plus(value, safe="", encoding=encoding)

    encode = Encode
    encode_new = EncodeNew1
    hmac_sha256 = HmacSHA256
    byte_to_hex = ByteToHexStr
    encrypt_app_secret = EncryptAppSecret
    decrypt_app_secret = DecryptAppSecret
    url_encode_with_upper_code = UrlEncodeWithUpperCode


__all__ = ["EnDecode"]
