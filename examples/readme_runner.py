"""README 可复现示例运行器。

每个命令都会输出客户端实际生成的 URL、请求报文、响应报文或 SSO 参数。
``docs/generate-readme-screenshots.ps1`` 使用临时回环服务运行这些命令。
"""

from __future__ import annotations

import base64
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.parse import quote_plus

from yikd_web_client import (
    AppSettingsModel,
    AttachmentHelper,
    CustomServicesStubpath,
    EnDecode,
    FileChunk,
    LoginBySimplePassportModel,
    LoginType,
    RequestWebModel,
    SSOHelper,
    UploadModel,
    UploadModelData,
    ValidateLoginSettingsModel,
    XmlConfigHelper,
    YiK3CloudClient,
)

FORM_ID = "SEC_User"
VIEW_JSON = json.dumps(
    {
        "IsUserModelInit": "true",
        "Number": "Administrator",
        "IsSortBySeq": "false",
    },
    ensure_ascii=False,
    separators=(",", ":"),
)
RULE_WIDTH = 108
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Example:
    command: str
    title: str
    description: str
    action: Callable[[], None]


def _environment_value(name: str, fallback: str = "") -> str:
    value = os.environ.get(name, "").strip()
    return value or fallback


def _environment_int(name: str, fallback: int) -> int:
    try:
        return int(os.environ.get(name, ""))
    except (TypeError, ValueError):
        return fallback


def _config_path() -> Path:
    configured = _environment_value("YIKD_CONFIG_PATH")
    return Path(configured) if configured else REPOSITORY_ROOT / "YiKdWebCfg" / "appsettings.xml"


def _cnf_path() -> Path:
    configured = _environment_value("YIKD_CNF_PATH")
    return Path(configured) if configured else REPOSITORY_ROOT / "YiKdWebCfg" / "API测试.cnf"


def _upload_path() -> Path:
    configured = _environment_value("YIKD_UPLOAD_FILE")
    return Path(configured) if configured else REPOSITORY_ROOT / "examples" / "upload-demo.txt"


def _require_file(path: Path, display_name: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(
            f"找不到{display_name}：{path}。请检查路径或使用 YIKD_* 环境变量覆盖。"
        )


def _config_values() -> dict[str, str]:
    path = _config_path()
    _require_file(path, "配置文件")
    return XmlConfigHelper.GetAllCfgDic(path)


def _server_url() -> str:
    return _environment_value(
        "YIKD_SERVER_URL",
        _config_values().get("X-KDApi-ServerUrl", ""),
    )


def _settings_from_file() -> AppSettingsModel:
    path = _config_path()
    _require_file(path, "配置文件")
    return AppSettingsModel(str(path))


def _dynamic_settings() -> AppSettingsModel:
    values = _config_values()
    settings = AppSettingsModel()
    settings.XKDApiAcctID = _environment_value(
        "YIKD_ACCT_ID", values.get("X-KDApi-AcctID", "")
    )
    settings.XKDApiUserName = _environment_value(
        "YIKD_USER_NAME", values.get("X-KDApi-UserName", "")
    )
    settings.XKDApiAppID = _environment_value(
        "YIKD_APP_ID", values.get("X-KDApi-AppID", "")
    )
    settings.XKDApiAppSec = _environment_value(
        "YIKD_APP_SECRET", values.get("X-KDApi-AppSec", "")
    )
    settings.XKDApiLCID = _environment_value(
        "YIKD_LCID", values.get("X-KDApi-LCID", "2052")
    )
    settings.XKDApiOrgNum = _environment_value(
        "YIKD_ORG_NUM", values.get("X-KDApi-OrgNum", "")
    )
    settings.XKDApiServerUrl = _server_url()
    return settings


def _client(login_type: LoginType) -> YiK3CloudClient:
    client = YiK3CloudClient()
    client.AppSettingsModel = _settings_from_file()
    client.LoginType = login_type
    return client


def _simple_passport_client() -> YiK3CloudClient:
    cnf_path = _cnf_path()
    _require_file(cnf_path, "集成密钥文件")
    client = _client(LoginType.LoginBySimplePassport)
    client.LoginBySimplePassportModel = LoginBySimplePassportModel(
        _server_url(),
        CnfFilePath=str(cnf_path),
    )
    return client


def _is_screenshot_mode() -> bool:
    return os.environ.get("YIKD_SCREENSHOT_MODE") == "1"


def _redact_secrets(value: str) -> str:
    result = value
    for name in ("YIKD_VALIDATE_PASSWORD", "YIKD_APP_SECRET"):
        secret = os.environ.get(name, "")
        if not secret:
            continue
        result = result.replace(secret, "******")
        if name == "YIKD_VALIDATE_PASSWORD":
            encoded_password = EnDecode.Encode(secret)
            if encoded_password:
                result = result.replace(
                    encoded_password,
                    "******（旧式编码值已脱敏）",
                )
        result = result.replace(quote_plus(secret, safe=""), "******")
    temporary_root = os.environ.get("YIKD_SCREENSHOT_TEMP_ROOT", "")
    if temporary_root:
        result = result.replace(temporary_root, "<TEMP>")
    return result


def _compact_for_screenshot(value: str) -> str:
    maximum_line_length = 240
    maximum_line_count = 34
    leading_line_count = 24
    trailing_line_count = 8
    lines = value.replace("\r\n", "\n").split("\n")
    compact_lines = [
        line
        if len(line) <= maximum_line_length
        else line[:maximum_line_length] + " …（长字段已折叠，运行命令可查看完整值）"
        for line in lines
    ]
    if len(compact_lines) <= maximum_line_count:
        return "\n".join(compact_lines)
    omitted = len(compact_lines) - leading_line_count - trailing_line_count
    return "\n".join(
        compact_lines[:leading_line_count]
        + [f"  …（中间 {omitted} 行已折叠，运行命令可查看完整报文）…"]
        + compact_lines[-trailing_line_count:]
    )


def _write_rule(character: str) -> None:
    print(character * RULE_WIDTH)


def _write_section(title: str) -> None:
    print()
    _write_rule("-")
    print(title)
    _write_rule("-")


def _write_payload(payload: str) -> None:
    if not payload or not payload.strip():
        print("（空）")
        return
    redacted = _redact_secrets(payload)
    try:
        formatted = json.dumps(json.loads(redacted), ensure_ascii=False, indent=2)
    except (TypeError, ValueError, json.JSONDecodeError):
        formatted = redacted
    print(_compact_for_screenshot(formatted) if _is_screenshot_mode() else formatted)


def _print_setting(name: str, value: object) -> None:
    rendered = "" if value is None else str(value)
    print(f"{name}：{rendered or '（空）'}")


def _print_secret_setting(name: str) -> None:
    print(f"{name}：******（已脱敏）")


def _has_exchange(exchange: RequestWebModel) -> bool:
    return any(
        value and value.strip()
        for value in (
            exchange.RequestUrl,
            exchange.RealRequestBody,
            exchange.RealResponseBody,
        )
    )


def _print_exchange(title: str, exchange: RequestWebModel) -> None:
    _write_section(title)
    print("请求地址：")
    print(exchange.RequestUrl or "（空）")
    print("\n实际请求报文：")
    _write_payload(exchange.RealRequestBody)
    print("\n实际返回报文：")
    _write_payload(exchange.RealResponseBody)


def _print_client_exchange(client: YiK3CloudClient, method_result: str) -> None:
    if _has_exchange(client.ReturnLoginWebModel):
        _print_exchange("登录请求 / 响应", client.ReturnLoginWebModel)
    else:
        _write_section("登录请求 / 响应")
        print("本示例没有发送登录请求。API 请求头签名模式会直接调用业务接口。")

    if client.RequestHeaders or client.RequestHeadersString.strip():
        _write_section("实际请求头")
        if client.RequestHeadersString.strip():
            print(_redact_secrets(client.RequestHeadersString.strip()))
        else:
            for name, value in client.RequestHeaders.items():
                print(f"{name}: {_redact_secrets(value)}")

    _print_exchange("业务操作请求 / 响应", client.ReturnOperationWebModel)
    _write_section("方法返回值")
    if method_result.strip() == client.ReturnOperationWebModel.RealResponseBody.strip():
        print("与上面的“业务操作实际返回报文”相同。")
    elif method_result.strip() == client.ReturnLoginWebModel.RealResponseBody.strip():
        print("业务请求未发送；与上面的“登录实际返回报文”相同。")
    else:
        _write_payload(method_result)


def _print_header(example: Example) -> None:
    _write_rule("=")
    print(f"YiKdWebClient-Python 实际报文示例：{example.title}")
    print(f"命令：{example.command}")
    print(f"说明：{example.description}")
    print(f"运行时间：{datetime.now().astimezone().isoformat(timespec='milliseconds')}")
    _write_rule("=")
    print(
        "截图模式：报文来自本次本地回环调用；仅为控制图片高度折叠长字段和部分中间行。"
        if _is_screenshot_mode()
        else "提示：JSON 为便于阅读进行了缩进；请勿公开含真实密钥的控制台输出。"
    )


def _print_footer(completed: bool) -> None:
    _write_rule("=")
    print(
        "示例程序执行结束。请根据返回报文中的业务状态判断接口是否成功。"
        if completed
        else "示例程序因异常结束，请检查上面的错误和环境配置。"
    )
    _write_rule("=")


def _run_view_example(login_type: LoginType) -> None:
    with _client(login_type) as client:
        result = client.View(FORM_ID, VIEW_JSON)
        _print_client_exchange(client, result)


def _run_sign_sha256() -> None:
    _run_view_example(LoginType.LoginBySignSHA256)


def _run_sign_sha1() -> None:
    _run_view_example(LoginType.LoginBySignSHA1)


def _run_app_secret() -> None:
    _run_view_example(LoginType.LoginByAppSecret)


def _run_api_sign_headers() -> None:
    _run_view_example(LoginType.LoginByApiSignHeaders)


def _run_validate_login() -> None:
    password = os.environ.get("YIKD_VALIDATE_PASSWORD", "")
    if not password.strip():
        raise ValueError(
            "运行 validate-login 或 validate-user-endecode 前，"
            "请设置 YIKD_VALIDATE_PASSWORD 环境变量。"
        )
    settings = ValidateLoginSettingsModel(
        _server_url(),
        DbId=_environment_value(
            "YIKD_VALIDATE_DBID",
            _config_values().get("X-KDApi-AcctID", ""),
        ),
        UserName=_environment_value("YIKD_VALIDATE_USERNAME", "demo"),
        Password=password,
        lcid=_environment_int("YIKD_VALIDATE_LCID", 2052),
    )
    with _client(LoginType.ValidateLogin) as client:
        client.validateLoginSettingsModel = settings
        _write_section("本次旧版登录参数")
        _print_setting("服务地址", settings.Url)
        _print_setting("数据中心 ID", settings.DbId)
        _print_setting("用户名", settings.UserName)
        _print_secret_setting("密码")
        _print_setting("语系", settings.lcid)
        result = client.View(FORM_ID, VIEW_JSON)
        _print_client_exchange(client, result)


def _run_validate_user_endecode() -> None:
    password = os.environ.get("YIKD_VALIDATE_PASSWORD", "")
    if not password.strip():
        raise ValueError(
            "运行 validate-login 或 validate-user-endecode 前，"
            "请设置 YIKD_VALIDATE_PASSWORD 环境变量。"
        )
    settings = ValidateLoginSettingsModel(
        _server_url(),
        DbId=_environment_value(
            "YIKD_VALIDATE_DBID",
            _config_values().get("X-KDApi-AcctID", ""),
        ),
        UserName=_environment_value("YIKD_VALIDATE_USERNAME", "demo"),
        Password=password,
        lcid=_environment_int("YIKD_VALIDATE_LCID", 2052),
    )
    with _client(LoginType.ValidateUserEnDeCode) as client:
        client.validateLoginSettingsModel = settings
        _write_section("本次已弃用兼容登录参数")
        _print_setting("兼容模式", client.LoginType.value)
        _print_setting("服务地址", settings.Url)
        _print_setting("数据中心 ID", settings.DbId)
        _print_setting("用户名", settings.UserName)
        _print_secret_setting("密码")
        _print_setting("语系", settings.lcid)
        result = client.View(FORM_ID, VIEW_JSON)
        _print_client_exchange(client, result)


def _run_simple_passport() -> None:
    with _simple_passport_client() as client:
        model = client.LoginBySimplePassportModel
        assert model is not None
        _write_section("本次集成密钥配置")
        _print_setting("服务地址", model.Url)
        _print_setting("CNF 路径", model.CnfFilePath)
        result = client.View(FORM_ID, VIEW_JSON)
        _print_client_exchange(client, result)


def _run_dynamic_config() -> None:
    settings = _dynamic_settings()
    with YiK3CloudClient() as client:
        client.AppSettingsModel = settings
        client.LoginType = LoginType.LoginByAppSecret
        _write_section("本次由代码动态传入的配置")
        _print_setting("账套 ID", settings.XKDApiAcctID)
        _print_setting("集成用户", settings.XKDApiUserName)
        _print_setting("应用 ID", settings.XKDApiAppID)
        _print_secret_setting("应用密钥")
        _print_setting("语系", settings.XKDApiLCID)
        _print_setting("组织编码", settings.XKDApiOrgNum)
        _print_setting("服务地址", settings.XKDApiServerUrl)
        result = client.View(FORM_ID, VIEW_JSON)
        _print_client_exchange(client, result)


def _run_custom_config_path() -> None:
    path = _config_path()
    _require_file(path, "配置文件")
    XmlConfigHelper.AppConfigPath = path
    _write_section("自定义配置文件路径")
    _print_setting("XmlConfigHelper.AppConfigPath", path)
    with YiK3CloudClient() as client:
        client.LoginType = LoginType.LoginBySignSHA256
        result = client.View(FORM_ID, VIEW_JSON)
        _print_client_exchange(client, result)


def _run_custom_webapi() -> None:
    service = CustomServicesStubpath(
        ProjetNamespace="GlobalServiceCustom.WebApi",
        ProjetClassName="DataServiceHandler",
        ProjetClassMethod="CommonRunnerService",
    )
    payload = json.dumps(
        {
            "parameters": [
                _environment_value(
                    "YIKD_CUSTOM_SQL",
                    "SELECT TOP 10 * FROM T_BD_MATERIAL_L",
                )
            ]
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    with _client(LoginType.LoginByAppSecret) as client:
        _write_section("自定义服务定位信息")
        _print_setting("命名空间", service.ProjetNamespace)
        _print_setting("类名", service.ProjetClassName)
        _print_setting("方法名", service.ProjetClassMethod)
        result = client.CustomBusinessServiceByParameters(payload, service)
        _print_client_exchange(client, result)


def _run_sso_v4() -> None:
    settings = _dynamic_settings()
    helper = SSOHelper()
    helper.appSettingsModel = settings
    helper.Url = settings.XKDApiServerUrl
    urls = helper.GetSsoUrlsV4(settings.XKDApiUserName)
    _write_section("SSO V4 请求参数")
    _print_setting("数据中心 ID", helper.simplePassportLoginArg.dbid)
    _print_setting("应用 ID", helper.simplePassportLoginArg.appid)
    _print_setting("用户名称", helper.simplePassportLoginArg.username)
    _print_setting("时间戳", helper.timestamp)
    _print_setting("签名", helper.simplePassportLoginArg.signeddata)
    print("\n请求参数（JSON）：")
    _write_payload(helper.argJosn or "")
    print("\n请求参数（Base64）：")
    print(helper.argJsonBase64 or "（空）")
    _write_section("生成的单点登录入口")
    print(f"Silverlight：\n{urls.silverlightUrl}")
    print(f"\nHTML5：\n{urls.html5Url}")
    print(f"\nWPF 客户端：\n{urls.wpfUrl}")
    print("\n说明：GetSsoUrlsV4 只在本地生成带签名的入口，不发送 HTTP 请求。")


def _upload_model() -> UploadModel:
    return UploadModel(
        data=UploadModelData(
            FormId=_environment_value("YIKD_UPLOAD_FORM_ID", "SAL_SaleOrder"),
            InterId=_environment_value("YIKD_UPLOAD_INTER_ID", "100020"),
            BillNO=_environment_value("YIKD_UPLOAD_BILL_NO", "XSDD000019"),
        )
    )


def _print_upload_settings(path: Path, upload: UploadModel, chunk_size: int) -> None:
    _write_section("本次附件上传参数")
    _print_setting("文件路径", path)
    _print_setting("文件大小（字节）", path.stat().st_size)
    _print_setting("分块大小（字节）", chunk_size)
    _print_setting("表单 ID", upload.data.FormId)
    _print_setting("单据内码", upload.data.InterId)
    _print_setting("单据编号", upload.data.BillNO)


def _print_progress(chunk: FileChunk, client: YiK3CloudClient) -> None:
    _write_section(f"上传分块 {chunk.Chunkindex + 1}（IsLast={chunk.IsLast}）")
    _print_exchange("本分块请求 / 响应", client.ReturnOperationWebModel)


def _run_upload(*, show_progress: bool, from_base64: bool) -> None:
    path = _upload_path()
    _require_file(path, "待上传文件")
    chunk_size = max(1, _environment_int("YIKD_UPLOAD_CHUNK_SIZE", 2 * 1024 * 1024))
    upload = _upload_model()
    with _simple_passport_client() as client:
        _print_upload_settings(path, upload, chunk_size)
        progress = _print_progress if show_progress else None
        if from_base64:
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            result = AttachmentHelper.AttachmentUploadByBase64(
                encoded,
                path.name,
                client,
                upload,
                chunkSize=chunk_size,
                progressaction=progress,
            )
        else:
            result = AttachmentHelper.AttachmentUploadByFilePath(
                path,
                client,
                upload,
                chunkSize=chunk_size,
                progressaction=progress,
            )
        _print_client_exchange(client, result)


def _run_upload_file() -> None:
    _run_upload(show_progress=False, from_base64=False)


def _run_upload_progress() -> None:
    _run_upload(show_progress=True, from_base64=False)


def _run_upload_base64() -> None:
    _run_upload(show_progress=False, from_base64=True)


EXAMPLES = (
    Example(
        "sign-sha256",
        "签名信息认证（SHA256）",
        "推荐用于支持 SHA256 的金蝶云星空版本。",
        _run_sign_sha256,
    ),
    Example("sign-sha1", "签名信息认证（SHA1）", "用于旧版本兼容。", _run_sign_sha1),
    Example(
        "app-secret",
        "第三方系统登录授权",
        "使用账套 ID、集成用户、应用 ID 和应用密钥登录。",
        _run_app_secret,
    ),
    Example(
        "validate-login",
        "旧版用户名密码认证",
        "仅建议兼容旧系统时使用。",
        _run_validate_login,
    ),
    Example(
        "validate-user-endecode",
        "已弃用的 ValidateUserEnDeCode",
        "对用户名和密码执行旧式编码；仅用于兼容历史系统。",
        _run_validate_user_endecode,
    ),
    Example(
        "simple-passport",
        "集成密钥文件认证",
        "读取 .cnf 集成密钥完成登录。",
        _run_simple_passport,
    ),
    Example(
        "api-sign-headers",
        "API 请求头签名认证",
        "不调用登录接口，直接为业务请求生成签名请求头。",
        _run_api_sign_headers,
    ),
    Example(
        "dynamic-config",
        "代码动态配置授权信息",
        "适合多环境、多账套或动态用户。",
        _run_dynamic_config,
    ),
    Example(
        "custom-config-path",
        "自定义配置文件路径",
        "运行前显式指定 appsettings.xml 路径。",
        _run_custom_config_path,
    ),
    Example(
        "custom-webapi",
        "调用自定义 WebAPI",
        "客户端调用示例；服务端示例仍使用 C#。",
        _run_custom_webapi,
    ),
    Example(
        "sso-v4",
        "单点登录 V4",
        "生成 Silverlight、HTML5 和 WPF 入口。",
        _run_sso_v4,
    ),
    Example(
        "upload-file",
        "文件分块上传",
        "从文件路径读取内容并上传。",
        _run_upload_file,
    ),
    Example(
        "upload-progress",
        "文件分块上传（进度回调）",
        "每个分块完成后输出实际请求和响应。",
        _run_upload_progress,
    ),
    Example(
        "upload-base64",
        "Base64 流分块上传",
        "把已有 Base64 内容按块上传。",
        _run_upload_base64,
    ),
)
EXAMPLES_BY_COMMAND = {example.command: example for example in EXAMPLES}


def _print_help() -> None:
    print("YiKdWebClient-Python README 示例运行器")
    print("\n用法：")
    print("  python examples/readme_runner.py <示例命令>")
    print("\n示例命令：")
    width = max(len(example.command) for example in EXAMPLES) + 2
    for example in EXAMPLES:
        print(f"  {example.command:<{width}}{example.title}")
        print(f"  {'':<{width}}{example.description}")
    print("\n先复制 YiKdWebCfg/appsettings.example.xml 并填写本地测试配置。")
    print("真实密钥也可通过 YIKD_* 环境变量传入，请勿提交到 Git。")


def main(arguments: list[str] | None = None) -> int:
    args = sys.argv[1:] if arguments is None else arguments
    if not args or args[0].lower() in {"help", "-h", "--help"}:
        _print_help()
        return 0
    example = EXAMPLES_BY_COMMAND.get(args[0].lower())
    if example is None:
        print(f"未知示例命令：{args[0]}\n", file=sys.stderr)
        _print_help()
        return 2

    XmlConfigHelper.AppConfigPath = _config_path()
    _print_header(example)
    try:
        example.action()
    except Exception as exc:
        _write_section("示例运行异常")
        print(f"{type(exc).__name__}: {_redact_secrets(str(exc))}")
        _print_footer(False)
        return 1
    _print_footer(True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
