[CmdletBinding()]
param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$utf8Encoding = [System.Text.UTF8Encoding]::new($false)
$originalConsoleOutputEncoding = [Console]::OutputEncoding
$originalPipelineOutputEncoding = $OutputEncoding
[Console]::OutputEncoding = $utf8Encoding
$OutputEncoding = $utf8Encoding

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$screenshotDirectory = Join-Path $PSScriptRoot "screenshots"
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"
$buildScript = Join-Path $repositoryRoot "build-release.bat"
$runnerPath = Join-Path $repositoryRoot "examples\readme_runner.py"

$edgeCandidates = @(
    (Join-Path ${env:ProgramFiles(x86)} "Microsoft\Edge\Application\msedge.exe"),
    (Join-Path $env:ProgramFiles "Microsoft\Edge\Application\msedge.exe")
)
$edgePath = $edgeCandidates |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
if (-not $edgePath) {
    throw "找不到 Microsoft Edge。该脚本使用 Edge 无头模式把控制台输出保存为 PNG。"
}

if (-not (Test-Path -LiteralPath $runnerPath)) {
    throw "找不到 README 示例运行器：$runnerPath"
}

function Get-FreeTcpPort {
    $probe = [System.Net.Sockets.TcpListener]::new(
        [System.Net.IPAddress]::Loopback,
        0)
    $probe.Start()
    try {
        return ([System.Net.IPEndPoint]$probe.LocalEndpoint).Port
    }
    finally {
        $probe.Stop()
    }
}

function Save-ConsoleScreenshot {
    param(
        [Parameter(Mandatory = $true)][string]$Title,
        [Parameter(Mandatory = $true)][string]$Meta,
        [Parameter(Mandatory = $true)][string]$Output,
        [Parameter(Mandatory = $true)][string]$FileName
    )

    $encodedOutput = [System.Net.WebUtility]::HtmlEncode($Output)
    $encodedTitle = [System.Net.WebUtility]::HtmlEncode($Title)
    $encodedMeta = [System.Net.WebUtility]::HtmlEncode($Meta)
    $html = @"
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>$encodedTitle</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; background: #0b1120; color: #d7e0ee; }
  body { padding: 18px; font-family: "Segoe UI", "Microsoft YaHei", sans-serif; }
  .window { overflow: hidden; border: 1px solid #334155; border-radius: 10px; background: #0f172a; box-shadow: 0 18px 48px rgba(0,0,0,.35); }
  .titlebar { display: flex; align-items: center; justify-content: space-between; min-height: 52px; padding: 0 20px; background: #1e293b; border-bottom: 1px solid #334155; }
  .title { font-size: 16px; font-weight: 650; color: #f8fafc; }
  .meta { font-size: 12px; color: #94a3b8; }
  pre { margin: 0; padding: 22px; white-space: pre-wrap; overflow-wrap: anywhere; tab-size: 4; font: 14px/1.55 "Cascadia Mono", "Microsoft YaHei UI", Consolas, monospace; color: #d7e0ee; }
</style>
</head>
<body>
  <section class="window">
    <header class="titlebar">
      <div class="title">$encodedTitle</div>
      <div class="meta">$encodedMeta</div>
    </header>
    <pre>$encodedOutput</pre>
  </section>
</body>
</html>
"@

    $temporaryHtmlPath = Join-Path $temporaryRoot (
        "render-" + [guid]::NewGuid().ToString("N") + ".html")
    [System.IO.File]::WriteAllText($temporaryHtmlPath, $html, $utf8Encoding)

    try {
        $visualLineCount = 0
        foreach ($line in ($Output -split "`r?`n")) {
            $visualLineCount += [Math]::Max(
                1,
                [Math]::Ceiling($line.Length / 132.0))
        }

        $imageHeight = [Math]::Min(
            9000,
            [Math]::Max(900, [int]($visualLineCount * 23 + 120)))
        $outputPath = Join-Path $screenshotDirectory $FileName
        $pageUri = ([Uri]$temporaryHtmlPath).AbsoluteUri

        & $edgePath --headless=new --disable-gpu --disable-sync --no-first-run `
            --no-default-browser-check --hide-scrollbars `
            --force-device-scale-factor=1 --log-level=3 `
            "--window-size=1440,$imageHeight" `
            "--screenshot=$outputPath" $pageUri | Out-Null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $outputPath)) {
            throw "Edge 未能生成截图：$outputPath"
        }
    }
    finally {
        Remove-Item -LiteralPath $temporaryHtmlPath -Force `
            -ErrorAction SilentlyContinue
    }
}

$examples = @(
    @{ Command = "sign-sha256";        File = "01-sign-sha256.png" },
    @{ Command = "sign-sha1";          File = "02-sign-sha1.png" },
    @{ Command = "app-secret";         File = "03-app-secret.png" },
    @{ Command = "validate-login";     File = "04-validate-login.png" },
    @{ Command = "simple-passport";    File = "05-simple-passport.png" },
    @{ Command = "api-sign-headers";   File = "06-api-sign-headers.png" },
    @{ Command = "dynamic-config";     File = "07-dynamic-config.png" },
    @{ Command = "custom-config-path"; File = "08-custom-config-path.png" },
    @{ Command = "custom-webapi";      File = "09-custom-webapi.png" },
    @{ Command = "sso-v4";             File = "10-sso-v4.png" },
    @{ Command = "upload-file";        File = "11-upload-file.png" },
    @{ Command = "upload-progress";    File = "12-upload-progress.png" },
    @{ Command = "upload-base64";      File = "13-upload-base64.png" }
)

$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) (
    "yikd-python-readme-" + [guid]::NewGuid().ToString("N"))
$temporaryRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
$temporaryBase = [System.IO.Path]::GetFullPath(
    [System.IO.Path]::GetTempPath())
if (-not $temporaryRoot.StartsWith(
        $temporaryBase,
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "临时目录不在系统临时目录下：$temporaryRoot"
}

$environmentNames = @(
    "PYTHONUTF8",
    "YIKD_SCREENSHOT_MODE",
    "YIKD_SCREENSHOT_TEMP_ROOT",
    "YIKD_CONFIG_PATH",
    "YIKD_CNF_PATH",
    "YIKD_SERVER_URL",
    "YIKD_ACCT_ID",
    "YIKD_USER_NAME",
    "YIKD_APP_ID",
    "YIKD_APP_SECRET",
    "YIKD_LCID",
    "YIKD_ORG_NUM",
    "YIKD_VALIDATE_DBID",
    "YIKD_VALIDATE_USERNAME",
    "YIKD_VALIDATE_PASSWORD",
    "YIKD_VALIDATE_LCID",
    "YIKD_UPLOAD_FILE",
    "YIKD_UPLOAD_FORM_ID",
    "YIKD_UPLOAD_INTER_ID",
    "YIKD_UPLOAD_BILL_NO",
    "YIKD_UPLOAD_CHUNK_SIZE",
    "YIKD_CUSTOM_SQL"
)
$originalEnvironment = @{}
foreach ($name in $environmentNames) {
    $originalEnvironment[$name] = [System.Environment]::GetEnvironmentVariable(
        $name,
        "Process")
}

$mockServerJob = $null
$mockServerPort = $null
New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null
New-Item -ItemType Directory -Path $screenshotDirectory -Force | Out-Null

try {
    $buildOutput = @()
    if (-not $SkipBuild) {
        if (-not (Test-Path -LiteralPath $buildScript)) {
            throw "找不到发布构建脚本：$buildScript"
        }
        Write-Host "运行 Python 发布前检查并构建发行包……"
        Push-Location $repositoryRoot
        try {
            # unittest 会把正常测试进度写到 stderr。这里只捕获全部原生输出，
            # 最终仍严格使用 build-release.bat 的退出码判断构建是否成功。
            $savedErrorActionPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"
            try {
                $buildOutput = @(
                    & $buildScript 2>&1 |
                        ForEach-Object { $_.ToString() })
                $buildExitCode = $LASTEXITCODE
            }
            finally {
                $ErrorActionPreference = $savedErrorActionPreference
            }
        }
        finally {
            Pop-Location
        }
        if ($buildExitCode -ne 0) {
            throw "Python 发布构建失败：`n$($buildOutput -join [Environment]::NewLine)"
        }
    }

    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw "找不到项目虚拟环境 Python：$pythonPath"
    }

    $buildHighlights = @(
        $buildOutput | Where-Object {
            $_ -match "^\[[1-6]/6\]" -or
            $_ -match "All checks passed" -or
            $_ -match "Ran [0-9]+ tests" -or
            $_ -eq "OK" -or
            $_ -match "Successfully built" -or
            $_ -match "Checking .*PASSED" -or
            $_ -match "^\[SUCCESS\]"
        })
    if ($buildHighlights.Count -eq 0) {
        $buildHighlights = @(
            "（本次使用 -SkipBuild，沿用已有虚拟环境和 dist 发行包。）")
    }
    $distributionFiles = @(
        Get-ChildItem -LiteralPath (Join-Path $repositoryRoot "dist") `
            -File -ErrorAction SilentlyContinue |
            Sort-Object Name |
            ForEach-Object { "  " + $_.Name })
    $pythonVersion = (& $pythonPath --version 2>&1 | Out-String).Trim()
    $installOutput = @(
        "PS $repositoryRoot> .\build-release.bat",
        "",
        "运行环境：$pythonVersion",
        "",
        $buildHighlights,
        "",
        "dist 中生成的发行包：",
        $distributionFiles,
        "",
        "结果：Ruff、单元测试、wheel/sdist 构建和 Twine 严格检查全部通过。",
        "业务项目也可执行：python -m pip install -e ."
    ) | ForEach-Object { $_ }
    $installScreenshotPath = Join-Path $screenshotDirectory "00-pip-install.png"
    if (-not $SkipBuild -or -not (Test-Path -LiteralPath $installScreenshotPath)) {
        Save-ConsoleScreenshot `
            -Title "YiKdWebClient-Python · pip 安装与发行包构建" `
            -Meta "Python 3.9+ · wheel + sdist · local build" `
            -Output ($installOutput -join [Environment]::NewLine) `
            -FileName "00-pip-install.png"
    }

    $mockServerPort = Get-FreeTcpPort
    $mockServerJob = Start-Job -ArgumentList $mockServerPort -ScriptBlock {
        param([int]$Port)
        $ErrorActionPreference = "Stop"
        $listener = [System.Net.HttpListener]::new()
        $listener.Prefixes.Add("http://127.0.0.1:$Port/")
        $listener.Start()
        try {
            while ($listener.IsListening) {
                try {
                    $context = $listener.GetContext()
                }
                catch {
                    break
                }

                try {
                    $stopAfterResponse = $false
                    $reader = [System.IO.StreamReader]::new(
                        $context.Request.InputStream,
                        $context.Request.ContentEncoding)
                    try {
                        [void]$reader.ReadToEnd()
                    }
                    finally {
                        $reader.Dispose()
                    }

                    $path = $context.Request.Url.AbsolutePath
                    if ($path -eq "/__shutdown") {
                        $body = '{"stopping":true}'
                        $stopAfterResponse = $true
                    }
                    elseif ($path -match "AuthService\.(LoginByAppSecret|LoginBySign|ValidateUser|ValidateUserEnDeCode|LoginBySimplePassport)\.common\.kdsvc$") {
                        $body = '{"LoginResultType":1,"IsSuccessByAPI":true,"Message":"本地回环认证成功","Context":{"SessionId":"MOCK-SESSION"}}'
                        $context.Response.AppendHeader(
                            "Set-Cookie",
                            "ASP.NET_SessionId=MOCK-SESSION; Path=/")
                    }
                    elseif ($path -match "AuthService\.Logout\.common\.kdsvc$") {
                        $body = '{"LogoutResultType":1,"Message":"本地回环登出成功"}'
                    }
                    elseif ($path -match "AttachmentUpLoad\.common\.kdsvc$") {
                        $body = '{"Result":{"ResponseStatus":{"IsSuccess":true,"Errors":[]},"FileId":"MOCK-FILE-ID"}}'
                    }
                    elseif ($path -match "GlobalServiceCustom\.WebApi") {
                        $body = '{"Result":{"ResponseStatus":{"IsSuccess":true,"Errors":[]},"Rows":[{"FNumber":"MATERIAL-001","FName":"本地回环物料"}]}}'
                    }
                    elseif ($path -eq "/__health") {
                        $body = '{"ok":true}'
                    }
                    else {
                        $body = '{"Result":{"ResponseStatus":{"IsSuccess":true,"Errors":[]},"Result":{"Id":"10001","Number":"Administrator","Name":"本地回环用户"}}}'
                    }

                    $bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
                    $context.Response.StatusCode = 200
                    $context.Response.ContentType = "application/json; charset=utf-8"
                    $context.Response.ContentLength64 = $bytes.Length
                    $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
                    $context.Response.Close()
                    if ($stopAfterResponse) {
                        break
                    }
                }
                catch {
                    try {
                        $context.Response.StatusCode = 500
                        $context.Response.Close()
                    }
                    catch {
                    }
                }
            }
        }
        finally {
            $listener.Stop()
            $listener.Close()
        }
    }

    $serverUrl = "http://127.0.0.1:$mockServerPort/K3Cloud/"
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $health = Invoke-WebRequest -UseBasicParsing `
                -Uri "http://127.0.0.1:$mockServerPort/__health" `
                -TimeoutSec 1
            if ($health.StatusCode -eq 200) {
                $ready = $true
                break
            }
        }
        catch {
            Start-Sleep -Milliseconds 100
        }
    }
    if (-not $ready) {
        throw "本地回环截图服务未能启动。"
    }

    $configPath = Join-Path $temporaryRoot "appsettings.xml"
    $cnfPath = Join-Path $temporaryRoot "mock-passport.cnf"
    $uploadPath = Join-Path $temporaryRoot "upload-demo.txt"
    $config = @"
<?xml version="1.0" encoding="utf-8" ?>
<configuration>
  <appSettings>
    <add key="X-KDApi-AcctID" value="MOCK-ACCOUNT" />
    <add key="X-KDApi-UserName" value="Administrator" />
    <add key="X-KDApi-AppID" value="client_frperg" />
    <add key="X-KDApi-AppSec" value="MOCK_APP_SECRET_DO_NOT_USE" />
    <add key="X-KDApi-LCID" value="2052" />
    <add key="X-KDApi-OrgNum" value="100" />
    <add key="X-KDApi-ServerUrl" value="$serverUrl" />
  </appSettings>
</configuration>
"@
    [System.IO.File]::WriteAllText($configPath, $config, $utf8Encoding)
    [System.IO.File]::WriteAllBytes($cnfPath, [byte[]](1..32))
    [System.IO.File]::WriteAllText(
        $uploadPath,
        "YiKdWebClient-Python local loopback upload sample.`nSecond line for chunking.",
        $utf8Encoding)

    $env:PYTHONUTF8 = "1"
    $env:YIKD_SCREENSHOT_MODE = "1"
    $env:YIKD_SCREENSHOT_TEMP_ROOT = $temporaryRoot
    $env:YIKD_CONFIG_PATH = $configPath
    $env:YIKD_CNF_PATH = $cnfPath
    $env:YIKD_SERVER_URL = $serverUrl
    $env:YIKD_ACCT_ID = "MOCK-ACCOUNT"
    $env:YIKD_USER_NAME = "Administrator"
    $env:YIKD_APP_ID = "client_frperg"
    $env:YIKD_APP_SECRET = "MOCK_APP_SECRET_DO_NOT_USE"
    $env:YIKD_LCID = "2052"
    $env:YIKD_ORG_NUM = "100"
    $env:YIKD_VALIDATE_DBID = "MOCK-ACCOUNT"
    $env:YIKD_VALIDATE_USERNAME = "demo"
    $env:YIKD_VALIDATE_PASSWORD = "MOCK_PASSWORD_DO_NOT_USE"
    $env:YIKD_VALIDATE_LCID = "2052"
    $env:YIKD_UPLOAD_FILE = $uploadPath
    $env:YIKD_UPLOAD_FORM_ID = "SAL_SaleOrder"
    $env:YIKD_UPLOAD_INTER_ID = "100020"
    $env:YIKD_UPLOAD_BILL_NO = "XSDD-MOCK-0001"
    $env:YIKD_UPLOAD_CHUNK_SIZE = "32"
    $env:YIKD_CUSTOM_SQL = "SELECT TOP 2 * FROM T_BD_MATERIAL_L"

    foreach ($example in $examples) {
        $command = [string]$example.Command
        $fileName = [string]$example.File
        Write-Host "运行 Python 本地回环示例并截图：$command"

        $output = (& $pythonPath $runnerPath $command 2>&1 | Out-String)
        $exitCode = $LASTEXITCODE
        $output = $output.Replace($env:YIKD_VALIDATE_PASSWORD, "******")
        $output = $output.Replace($env:YIKD_APP_SECRET, "******")
        $output = $output.Replace($temporaryRoot, "<TEMP>")
        if ($exitCode -ne 0) {
            throw "示例 $command 运行失败（退出码 $exitCode）。输出：`n$output"
        }

        Save-ConsoleScreenshot `
            -Title "YiKdWebClient-Python · $command · 本地回环实际输出" `
            -Meta "python · requests · loopback mock" `
            -Output $output `
            -FileName $fileName
    }
}
finally {
    [Console]::OutputEncoding = $originalConsoleOutputEncoding
    $OutputEncoding = $originalPipelineOutputEncoding

    foreach ($name in $environmentNames) {
        [System.Environment]::SetEnvironmentVariable(
            $name,
            $originalEnvironment[$name],
            "Process")
    }

    if ($null -ne $mockServerJob) {
        if ($mockServerJob.State -eq "Running" -and $null -ne $mockServerPort) {
            try {
                Invoke-WebRequest -UseBasicParsing `
                    -Uri "http://127.0.0.1:$mockServerPort/__shutdown" `
                    -TimeoutSec 2 | Out-Null
            }
            catch {
            }
            Wait-Job -Job $mockServerJob -Timeout 5 `
                -ErrorAction SilentlyContinue | Out-Null
        }
        if ($mockServerJob.State -eq "Running") {
            Stop-Job -Job $mockServerJob -ErrorAction SilentlyContinue
        }
        Remove-Job -Job $mockServerJob -Force -ErrorAction SilentlyContinue
    }

    if (Test-Path -LiteralPath $temporaryRoot) {
        $resolvedTemporaryRoot = [System.IO.Path]::GetFullPath($temporaryRoot)
        if ($resolvedTemporaryRoot.StartsWith(
                $temporaryBase,
                [System.StringComparison]::OrdinalIgnoreCase)) {
            Remove-Item -LiteralPath $resolvedTemporaryRoot -Recurse -Force
        }
    }
}

Write-Host "Python README 截图已生成：$screenshotDirectory"
