[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$giteeUrl = 'https://gitee.com/lnsyzjw/yi-kd-web-client-python.git'
$githubUrl = 'https://github.com/1609676823/YiKdWebClient-Python.git'

git rev-parse --is-inside-work-tree | Out-Null

$originExists = $null -ne (git remote 2>$null | Where-Object { $_ -eq 'origin' })
if ($originExists) {
    git remote set-url origin $giteeUrl
}
else {
    git remote add origin $giteeUrl
}

git config --unset-all remote.origin.pushurl 2>$null
if ($LASTEXITCODE -notin @(0, 5)) {
    throw 'Failed to clear the existing origin pushurl values.'
}

git config --add remote.origin.pushurl $giteeUrl
git config --add remote.origin.pushurl $githubUrl
git config remote.pushDefault origin
git config push.default current

$branch = git branch --show-current
if ($branch) {
    git config "branch.$branch.remote" origin
    git config "branch.$branch.merge" "refs/heads/$branch"
}

Write-Host 'Fetch URL:'
git remote get-url origin
Write-Host 'Push URLs:'
git remote get-url --push --all origin
