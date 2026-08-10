# C# / Java / Python API 对照

本移植以 C# `YiKdWebClient` 1.0.0.32 为主基准，Java 1.0.0 移植版用于交叉
核对。Python 的发行包名是 `yikd-web-client`，推荐导入名是
`yikd_web_client`；同时保留 `YiKdWebClient` 根包别名。
`YiKdWebClient.AuthService`、`CommonService`、`ComWebHelper`、`Model`、`SSO`
和 `ToolsHelper` 兼容命名空间也可直接导入，便于逐行迁移现有示例。

## 模块映射

| C# / Java | Python |
| --- | --- |
| `YiK3CloudClient` | `yikd_web_client.client.YiK3CloudClient` |
| `AuthService` | `yikd_web_client.auth` |
| `CommonService` / `CommonFunctionHelper` | `yikd_web_client.common` |
| `ComWebHelper` | `yikd_web_client.transport`、`media_types` |
| `Model` | `yikd_web_client.models` |
| `SSO` | `yikd_web_client.sso` |
| `ToolsHelper` | `yikd_web_client.attachments` |
| `EnDecode` | `yikd_web_client.encryption.EnDecode` |

## 认证方式

`LoginBySignSHA256`、`LoginBySignSHA1`、`LoginByAppSecret`、
`LoginByApiSignHeaders`、`ValidateLogin`、`LoginBySimplePassport` 和已弃用的
`ValidateUserEnDeCode` 均已映射。

## 业务方法

以下 C#/Java 名称在 Python 中原样可用，并另有 `snake_case` 别名：

`ExecuteOperation`、`View`、`Save`、`BatchSave`、`Submit`、`Audit`、
`UnAudit`、`Delete`、`ExecuteBillQuery`、`Draft`、`Allocate`、`Push`、
`GroupSave`、`FlexSave`、`SendMsg`、`SwitchOrg`、`WorkflowAudit`、
`GetSysReportData`、`AttachmentUpLoad`、`AttachmentDownLoad`、`UploadFile`、
`GroupDelete`、`CancelAllocate`、`CancelAssign`、`Disassembly`、
`QueryBusinessInfo`、`QueryGroupInfo`、`CustomBusinessService`、
`CustomBusinessServiceByParameters`、`GetDataCenterList`。

`ExecuteOperation` 的参数顺序与官方 SDK 及当前 C# 项目一致：
`formid, opNumber, json`。

## 运行时类型

| .NET / Java | Python |
| --- | --- |
| `CookieContainer` / `CookieManager` | `requests.cookies.RequestsCookieJar` |
| `TimeSpan` / `Duration` | 秒数（`float`），也可在传输类中使用 `timedelta` |
| `Dictionary<K,V>` / `Map<K,V>` | `dict` |
| `Action<T>` / `Consumer<T>` | 可调用对象 `Callable` |
| `IDisposable` / `AutoCloseable` | 上下文管理器 `with` 与 `close()` |
| `Task<string>` / `CompletableFuture<String>` | `async def SendHttpRequestAsync(...)` |
