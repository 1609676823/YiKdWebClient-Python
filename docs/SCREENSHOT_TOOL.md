# Python 截图工具使用说明

本文件专门说明同目录 `generate-readme-screenshots.ps1` 的使用方法。脚本执行 Python 发布检查、启动本地回环 HTTP 服务、运行 `examples/readme_runner.py`，再使用 Microsoft Edge 无头模式生成 PNG。

## 文件与输出位置

- 生成脚本：`docs/generate-readme-screenshots.ps1`
- 示例运行器：`examples/readme_runner.py`
- 发布构建脚本：`build-release.bat`
- 项目 Python：`.venv/Scripts/python.exe`
- 输出目录：`docs/screenshots`

完整运行会生成 `00-pip-install.png`，以及 `01-sign-sha256.png` 至 `14-validate-user-endecode.png`。

## 前置条件

1. Windows PowerShell 5.1 或 PowerShell 7。
2. Python 3.9 或更高版本。
3. 已创建项目 `.venv` 并安装项目与开发依赖。
4. Microsoft Edge 安装在标准 Program Files 路径。
5. `build-release.bat` 和 `examples/readme_runner.py` 存在。

脚本只连接随机本地端口上的回环 mock，不需要真实金蝶地址、账号、密码或 CNF，也不会写入真实业务系统。

## 完整构建并生成全部图片

在项目根目录执行：

~~~powershell
& .\docs\generate-readme-screenshots.ps1
~~~

或：

~~~powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File .\docs\generate-readme-screenshots.ps1
~~~

完整模式先运行 `build-release.bat`，包括 Ruff、单元测试、wheel/sdist 构建和 Twine 检查，然后生成 `00-pip-install.png`。

## 跳过发布构建

已经完成发布检查，只需要运行示例和渲染时：

~~~powershell
& .\docs\generate-readme-screenshots.ps1 -SkipBuild
~~~

使用 `-SkipBuild` 时仍必须存在 `.venv/Scripts/python.exe`。脚本会沿用当前虚拟环境和 `dist` 内容。

## 只生成指定场景

~~~powershell
& .\docs\generate-readme-screenshots.ps1 `
  -SkipBuild `
  -ExampleCommand sign-sha256
~~~

多个场景：

~~~powershell
& .\docs\generate-readme-screenshots.ps1 `
  -SkipBuild `
  -ExampleCommand "sign-sha256","app-secret"
~~~

`-ExampleCommand` 只过滤编号业务场景。未使用 `-SkipBuild` 时仍会执行发布构建并更新安装结果图片。

## 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `-SkipBuild` | 关闭 | 跳过 `build-release.bat` |
| `-ExampleCommand` | 全部场景 | 只运行一个或多个指定场景 |

## 支持的场景

| 命令 | 输出文件 |
| --- | --- |
| 发布构建摘要 | `00-pip-install.png` |
| `sign-sha256` | `01-sign-sha256.png` |
| `sign-sha1` | `02-sign-sha1.png` |
| `app-secret` | `03-app-secret.png` |
| `validate-login` | `04-validate-login.png` |
| `simple-passport` | `05-simple-passport.png` |
| `api-sign-headers` | `06-api-sign-headers.png` |
| `dynamic-config` | `07-dynamic-config.png` |
| `custom-config-path` | `08-custom-config-path.png` |
| `custom-webapi` | `09-custom-webapi.png` |
| `sso-v4` | `10-sso-v4.png` |
| `upload-file` | `11-upload-file.png` |
| `upload-progress` | `12-upload-progress.png` |
| `upload-base64` | `13-upload-base64.png` |
| `validate-user-endecode` | `14-validate-user-endecode.png` |

## 执行流程

1. 可选地运行完整发布构建。
2. 创建系统临时工作目录。
3. 启动只监听 `127.0.0.1` 随机端口的临时 HTTP 服务。
4. 创建 mock XML、CNF 和上传文件。
5. 临时设置运行器需要的 `YIKD_*` 进程变量。
6. 使用项目虚拟环境逐个执行 `examples/readme_runner.py`。
7. 再次替换测试密码、应用密钥和临时路径。
8. 使用 Edge 把临时 HTML 渲染为 PNG。
9. 恢复环境变量、停止回环服务并删除临时目录。

SSO V4 场景只在本地生成签名参数，不发送 HTTP 请求。其他场景会经过 Python 客户端的真实 HTTP 传输层，但响应来自本机 mock。

## 失败排查

- 找不到虚拟环境 Python：先创建 `.venv` 并安装项目依赖。
- 发布构建失败：单独运行 `build-release.bat` 查看完整步骤。
- 本地回环服务无法启动：检查 PowerShell 作业、HttpListener 权限和安全软件。
- 示例导入失败：确认项目已安装到当前 `.venv`。
- Edge 未生成文件：确认 Edge 位于标准路径，并检查 `docs/screenshots` 写权限。
- 使用 `-SkipBuild` 后内容过期：去掉该参数重新运行完整构建。

生成完成后应检查全部图片和 `git diff`，确认输出内容符合提交要求。
