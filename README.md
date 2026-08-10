# YiKdWebClient-Python

金蝶云星空 WebAPI Python 客户端。项目以 C#
[`YiKdWebClient`](https://gitee.com/lnsyzjw/yi-kd-web-client) 1.0.0.32 为主
基准移植，并参考 Java
[`YiKdWebClient-Java`](https://gitee.com/lnsyzjw/yi-kd-web-client-java) 的已验证
跨语言实现。

已包含：签名信息认证（SHA256/SHA1）、第三方应用密钥认证、API 请求头签名、
用户名密码认证、集成密钥认证、动态表单 API、自定义 WebAPI、SSO V1–V4、
附件分块上传、Cookie 会话复用和同步/异步 HTTP 工具。

## 环境与安装

- Python 3.9–3.13
- `requests` 2.x
- `pycryptodome` 3.x（仅旧版 `ValidateUserEnDeCode` 的 DES 兼容实现需要）

开发目录安装：

```powershell
python -m pip install -e .
```

以后发布到 PyPI 后可使用：

```powershell
python -m pip install yikd-web-client
```

## 配置

复制 [`YiKdWebCfg/appsettings.example.xml`](YiKdWebCfg/appsettings.example.xml)
为 `YiKdWebCfg/appsettings.xml`，再填写自己的授权信息。真实密钥文件已由
`.gitignore` 排除，不要提交到仓库。

```xml
<configuration>
  <appSettings>
    <add key="X-KDApi-AcctID" value="your-account-id" />
    <add key="X-KDApi-AppID" value="your-app-id" />
    <add key="X-KDApi-AppSec" value="your-app-secret" />
    <add key="X-KDApi-UserName" value="your-user-name" />
    <add key="X-KDApi-LCID" value="2052" />
    <add key="X-KDApi-ServerUrl" value="https://example.test/k3cloud/" />
    <add key="X-KDApi-OrgNum" value="" />
  </appSettings>
</configuration>
```

## 五分钟示例

SHA256 签名信息认证是当前推荐方式：

```python
from yikd_web_client import AppSettingsModel, LoginType, YiK3CloudClient

settings = AppSettingsModel("YiKdWebCfg/appsettings.xml")

with YiK3CloudClient() as client:
    client.AppSettingsModel = settings
    client.LoginType = LoginType.LoginBySignSHA256
    result = client.View(
        "BD_MATERIAL",
        '{"CreateOrgId":0,"Number":"PRE001"}',
    )
    print(result)
    print(client.ReturnOperationWebModel.RealRequestBody)
```

所有 C#/Java 公开方法名均保留。Python 风格也可以写成：

```python
result = client.view("BD_MATERIAL", '{"Number":"PRE001"}')
```

迁移既有示例时也可使用兼容命名空间，例如
`from YiKdWebClient.Model import AppSettingsModel`；新代码仍推荐小写包名。

## 认证方式

### 第三方应用密钥

```python
client.LoginType = LoginType.LoginByAppSecret
client.AppSettingsModel = AppSettingsModel("YiKdWebCfg/appsettings.xml")
```

### SHA1（旧补丁兼容）

```python
client.LoginType = LoginType.LoginBySignSHA1
```

### API 请求头签名

这种方式每个业务请求独立签名，不发送登录请求：

```python
client.LoginType = LoginType.LoginByApiSignHeaders
result = client.ExecuteBillQuery(
    '{"FormId":"BD_MATERIAL","FieldKeys":"FNumber,FName","Limit":10}'
)
print(client.RequestHeadersString)
```

### 用户名密码（旧方式）

```python
from yikd_web_client import ValidateLoginSettingsModel

client.LoginType = LoginType.ValidateLogin
client.validateLoginSettingsModel = ValidateLoginSettingsModel(
    "https://example.test/k3cloud/",
    DbId="account-id",
    UserName="Administrator",
    Password="password",
    lcid=2052,
)
```

### 集成密钥文件或 Base64

```python
from yikd_web_client import BySimplePassportType, LoginBySimplePassportModel

client.LoginType = LoginType.LoginBySimplePassport
client.LoginBySimplePassportModel = LoginBySimplePassportModel(
    "https://example.test/k3cloud/",
    CnfFilePath="YiKdWebCfg/API测试.cnf",
    bySimplePassportType=BySimplePassportType.CnfFile,
)
```

使用预先编码的 Base64 时，将类型设为 `ForBase64` 并填写
`SimplePassportForBase64`。

## 会话复用

高层接口默认依次执行登录、业务请求和登出。批量调用时可复用同一 Cookie：

```python
client.Login()
first = client.View("BD_MATERIAL", "{}", AutoLogin=False, AutoLogout=False)
second = client.Save("BD_MATERIAL", '{"Model":{}}', AutoLogin=False, AutoLogout=False)
client.Logout()
```

## 自定义 WebAPI

```python
from yikd_web_client import CustomServicesStubpath

service = CustomServicesStubpath(
    ProjetNamespace="Sample.WebApi",
    ProjetClassName="DataService",
    ProjetClassMethod="Execute",
)

result = client.CustomBusinessService('{"value":1}', service)
raw_result = client.CustomBusinessServiceByParameters('["one",2]', service)
```

## SSO V1–V4

```python
from yikd_web_client import AppSettingsModel, SSOHelper

sso = SSOHelper()
sso.appSettingsModel = AppSettingsModel("YiKdWebCfg/appsettings.xml")
sso.Url = sso.appSettingsModel.XKDApiServerUrl
sso.permitcount = "1"

urls = sso.GetSsoUrlsV4()
print(urls.html5Url)

logout = sso.GetSSOLogoutap0StrV4()
print(sso.SSOExcuteLogout(logout))
```

## 附件分块上传

```python
from yikd_web_client import AttachmentHelper, UploadModel, UploadModelData

template = UploadModel(
    data=UploadModelData(
        FormId="PUR_PurchaseOrder",
        InterId="100001",
        Entrykey="",
        EntryinterId="-1",
    )
)

def report(chunk, _client):
    print(chunk.Chunkindex, chunk.Filename, chunk.IsLast)

result = AttachmentHelper.AttachmentUploadByFilePath(
    "sample.pdf",
    client,
    template,
    chunkSize=1024 * 1024,
    progressaction=report,
)
```

也可使用 `AttachmentUploadByBase64` 上传已有 Base64 流。

## HTTP 工具

`WebHelperServices` 对应原项目的 JSON 请求工具；`WebHelper` 支持 query、raw、
URL encoded 和 multipart 请求。二者都有同步 `SendHttpRequest` 和真正可等待的
`SendHttpRequestAsync`：

```python
response = await helper.SendHttpRequestAsync(url)
```

## 测试

```powershell
python -m unittest discover -s tests -v
```

测试使用本机环回 HTTP 服务，不需要真实账套、真实密钥或外部金蝶环境。

## API 对照与移植边界

完整映射见 [`docs/API_MAPPING.md`](docs/API_MAPPING.md)。自动化测试覆盖算法、
报文、认证路径、请求头、Cookie、全部公开业务路由、SSO 和附件分块。目标金蝶
版本、补丁、许可、公私有云网关及自定义服务 DLL 仍需在使用者自己的环境中做
最终集成验证。

## Git 双远程

本地 `origin` 默认从 Gitee 拉取，普通 `git push` 会依次推送到 Gitee 与
GitHub：

```text
fetch: https://gitee.com/lnsyzjw/yi-kd-web-client-python.git
push:  https://gitee.com/lnsyzjw/yi-kd-web-client-python.git
push:  https://github.com/1609676823/YiKdWebClient-Python.git
```

在新的克隆目录中运行一次下面的脚本，即可恢复相同配置：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure-remotes.ps1
```

脚本会将当前分支的拉取上游设为 Gitee，并重建两个 `pushurl`；可重复执行，
不会累积重复地址。用 `git remote -v` 可随时复核。

项目地址：

- [Gitee](https://gitee.com/lnsyzjw/yi-kd-web-client-python)
- [GitHub](https://github.com/1609676823/YiKdWebClient-Python)
