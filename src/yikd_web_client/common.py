"""通用哈希、JSON 报文和 XML 配置工具。"""

from __future__ import annotations

import base64
import hashlib
import json
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Union

from .models import normalize_server_url

BytesLike = Union[bytes, bytearray, memoryview]


class CommonFunctionHelper:
    UnixStart = datetime(1970, 1, 1)

    @staticmethod
    def CurrentTimeMillis() -> int:
        return time.time_ns() // 1_000_000

    @staticmethod
    def GetTimestamp() -> int:
        return int(time.time())

    @staticmethod
    def GetServerUrl(url: Optional[str]) -> str:
        return normalize_server_url(url)

    @staticmethod
    def Sha256Hex(data: Union[str, BytesLike], encoding: str = "utf-8") -> str:
        raw = data.encode(encoding) if isinstance(data, str) else bytes(data)
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def ToHexString(data: BytesLike, toLowerCase: bool = True) -> str:
        value = bytes(data).hex()
        return value if toLowerCase else value.upper()

    @staticmethod
    def ToBase64(data: BytesLike) -> str:
        return base64.b64encode(bytes(data)).decode("ascii")

    @staticmethod
    def GetSignatureSHA1Util(values: Iterable[str]) -> str:
        return CommonFunctionHelper.GetSHA1(values)

    @staticmethod
    def GetSHA1(values: Iterable[str]) -> str:
        joined = "".join(sorted(str(value) for value in values))
        return hashlib.sha1(joined.encode("utf-8")).hexdigest()

    @staticmethod
    def GetSHA256(values: Optional[Iterable[str]]) -> str:
        if values is None:
            return ""
        materialized = [str(value) for value in values]
        if not materialized:
            return ""
        return hashlib.sha256("".join(sorted(materialized)).encode("utf-8")).hexdigest()

    current_time_millis = CurrentTimeMillis
    get_timestamp = GetTimestamp
    get_server_url = GetServerUrl
    sha256_hex = Sha256Hex
    to_hex_string = ToHexString
    to_base64 = ToBase64
    get_signature_sha1 = GetSignatureSHA1Util
    get_sha1 = GetSHA1
    get_sha256 = GetSHA256


def _json_dumps(
    value: Any,
    unsafe_relaxed_json_escaping: bool,
    *,
    write_indented: bool = False,
) -> str:
    result = json.dumps(
        value,
        ensure_ascii=not unsafe_relaxed_json_escaping,
        indent=2 if write_indented else None,
        separators=None if write_indented else (",", ":"),
    )
    if not unsafe_relaxed_json_escaping:
        # System.Text.Json 的默认 JavaScriptEncoder 还会转义 HTML 敏感字符。
        result = (
            result.replace("<", r"\u003C")
            .replace(">", r"\u003E")
            .replace("&", r"\u0026")
            .replace("'", r"\u0027")
        )
    return result


def _new_rid() -> str:
    number = int.from_bytes(uuid.uuid4().bytes[:4], byteorder="little", signed=True)
    return str(number)


def _standard_envelope(parameters: str) -> dict[str, Any]:
    return {
        "format": 1,
        "useragent": "ApiClient",
        "rid": _new_rid(),
        "parameters": parameters,
        "timestamp": datetime.now().astimezone().isoformat(),
        "v": "1.0",
    }


class JsonHelperServices:
    @staticmethod
    def getRequestBodystring(
        Formid: str,
        strjson: str,
        UnsafeRelaxedJsonEscaping: bool,
        opNumber: str,
    ) -> str:
        parameters: list[str] = []
        if Formid and Formid.strip():
            parameters.append(Formid)
        if opNumber and opNumber.strip():
            parameters.append(opNumber)
        parameters.append(strjson)
        content = _json_dumps(parameters, UnsafeRelaxedJsonEscaping)
        return _json_dumps(
            _standard_envelope(content),
            UnsafeRelaxedJsonEscaping,
            write_indented=True,
        )

    @staticmethod
    def getLoginRequestBodystring(
        strjson: str,
        UnsafeRelaxedJsonEscaping: bool,
        WriteIndented: bool = False,
    ) -> str:
        return _json_dumps(
            _standard_envelope(strjson),
            UnsafeRelaxedJsonEscaping,
            write_indented=WriteIndented,
        )

    @staticmethod
    def getLoginRequestBodystringByParameters(
        strjson: str,
        UnsafeRelaxedJsonEscaping: bool,
        WriteIndented: bool = False,
    ) -> str:
        return _json_dumps(
            {"parameters": strjson},
            UnsafeRelaxedJsonEscaping,
            write_indented=WriteIndented,
        )

    get_request_body_string = getRequestBodystring
    get_login_request_body_string = getLoginRequestBodystring
    get_login_request_body_string_by_parameters = getLoginRequestBodystringByParameters


class XmlConfigHelper:
    Currentpath = Path.cwd()
    AppConfigPath = Currentpath / "YiKdWebCfg" / "appsettings.xml"

    @staticmethod
    def GetAllCfgDic(path: Union[str, Path] = "") -> dict[str, str]:
        config_path = Path(path) if path and str(path).strip() else XmlConfigHelper.AppConfigPath
        try:
            root = ET.parse(config_path).getroot()
        except (OSError, ET.ParseError, ValueError):
            return {}

        app_settings = root.find("appSettings")
        if app_settings is None:
            return {}

        result: dict[str, str] = {}
        for child in app_settings:
            key = child.attrib.get("key", "")
            if key and key not in result:
                result[key] = child.attrib.get("value", "")
        return result

    get_all_cfg_dict = GetAllCfgDic


__all__ = [
    "CommonFunctionHelper",
    "JsonHelperServices",
    "XmlConfigHelper",
]
