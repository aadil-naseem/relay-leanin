# Phase 0.10 - C: drive leak audit.
# Prints where pip/npm/temp actually point and how much data is sitting on C:.
# Every cache/temp path must resolve to E:\. Run again after Phases 4, 12 and 14.
#
# Why this is not a plain $env: check: Windows only gives a NEW process the updated
# user environment. A long-lived shell (or an agent session) keeps its old block.
# So each variable is resolved process -> user -> machine, and the source is printed.
# A variable that is correct at user level but missing from the current process is
# reported as STALE-PROCESS, not LEAK.

$ErrorActionPreference = 'SilentlyContinue'

function Resolve-Env([string]$name) {
    foreach ($scope in @('Process','User','Machine')) {
        $v = [Environment]::GetEnvironmentVariable($name, $scope)
        if ($v) { return [pscustomobject]@{ Value = $v; Source = $scope } }
    }
    return [pscustomobject]@{ Value = ''; Source = 'unset' }
}

function Get-DirSizeMb($path) {
    if (-not (Test-Path $path)) { return 'absent' }
    $bytes = (Get-ChildItem -LiteralPath $path -Recurse -Force -File -ErrorAction SilentlyContinue |
              Measure-Object -Property Length -Sum).Sum
    if ($null -eq $bytes) { $bytes = 0 }
    return [math]::Round($bytes / 1MB, 1)
}

$rows = @()
function Add-Row([string]$name, [string]$value, [string]$source, [bool]$mustBeE) {
    $ok = -not $mustBeE -or ($value -like 'E:*')
    $state = if ($value -eq '') { 'UNSET' } elseif ($ok) { 'OK' } elseif ($source -ne 'Process') { 'OK' } else { 'STALE-PROCESS' }
    if ($source -eq 'Process' -and $ok -and $value -like 'E:*') { $state = 'OK' }
    if (-not $ok -and $source -eq 'Process') { $state = 'LEAK' }
    if ($value -eq '' -and $source -eq 'unset') {
        # fall back to the persisted value for advice
        $u = [Environment]::GetEnvironmentVariable($name,'User')
        if ($u -like 'E:*') { $state = 'STALE-PROCESS'; $value = $u; $source = 'User' }
    }
    $script:rows += [pscustomobject]@{ Name = $name; State = $state; Source = $source; Value = $value }
}

foreach ($n in @('PIP_CACHE_DIR','TEMP','TMP','HF_HOME','PLAYWRIGHT_BROWSERS_PATH')) {
    # The persisted (User/Machine) value is the one that matters. A process value
    # pointing at C: while the persisted value is on E: only means this shell is old.
    $p = [Environment]::GetEnvironmentVariable($n,'Process')
    $u = [Environment]::GetEnvironmentVariable($n,'User')
    $m = [Environment]::GetEnvironmentVariable($n,'Machine')

    if ($u -like 'E:*') {
        $state = if ($p -and $p -notlike 'E:*') { 'STALE-PROCESS' } else { 'OK' }
        $script:rows += [pscustomobject]@{ Name = $n; State = $state; Source = 'User'; Value = $u }
    } elseif ($p -like 'E:*') {
        $script:rows += [pscustomobject]@{ Name = $n; State = 'OK'; Source = 'Process'; Value = $p }
    } elseif ($m -like 'E:*') {
        $script:rows += [pscustomobject]@{ Name = $n; State = 'OK'; Source = 'Machine'; Value = $m }
    } else {
        $shown = if ($p) { $p } elseif ($u) { $u } elseif ($m) { $m } else { '' }
        $script:rows += [pscustomobject]@{ Name = $n; State = $(if ($shown) { 'LEAK' } else { 'UNSET' }); Source = 'none'; Value = $shown }
    }
}

# npm reads .npmrc, which is authoritative regardless of environment lineage.
$npm = 'E:\Program Files\nodejs\npm.cmd'
$npmCache = (& $npm config get cache 2>$null)
$npmPrefix = (& $npm config get prefix 2>$null)
Add-Row 'npm cache (npmrc)' "$npmCache" 'npmrc' $true
Add-Row 'npm prefix (npmrc)' "$npmPrefix" 'npmrc' $true

# pip consults PIP_CACHE_DIR; ask pip itself, with the resolved value applied.
$pipEnv = [Environment]::GetEnvironmentVariable('PIP_CACHE_DIR','User')
if ($pipEnv) { $env:PIP_CACHE_DIR = $pipEnv }
$pipCache = (& 'E:\VihaanX-Build\backend\.venv\Scripts\python.exe' -m pip cache dir 2>$null)
Add-Row 'pip cache dir (live)' "$pipCache" 'pip' $true

$nodePath = (Get-Command node).Source
Add-Row 'where node' "$nodePath" 'process' $true
Add-Row 'where python' (Get-Command python).Source 'process' $false

Write-Output '=== Path checks ==='
foreach ($r in $rows) { '{0,-26} {1,-14} {2,-8} {3}' -f $r.Name, $r.State, $r.Source, $r.Value }

Write-Output ''
Write-Output '=== User-level persisted values (what new terminals will get) ==='
foreach ($n in @('PIP_CACHE_DIR','TEMP','TMP','HF_HOME','PLAYWRIGHT_BROWSERS_PATH','npm_config_cache','npm_config_prefix')) {
    '{0,-26} {1}' -f $n, [Environment]::GetEnvironmentVariable($n,'User')
}

Write-Output ''
Write-Output '=== Existing data on C: (MB, informational - not created by this project) ==='
$sizes = [ordered]@{
    'C:\Users\Aadil\AppData\Local\pip'       = Get-DirSizeMb 'C:\Users\Aadil\AppData\Local\pip'
    'C:\Users\Aadil\AppData\Local\npm-cache' = Get-DirSizeMb 'C:\Users\Aadil\AppData\Local\npm-cache'
    'C:\Users\Aadil\AppData\Local\Temp'      = Get-DirSizeMb 'C:\Users\Aadil\AppData\Local\Temp'
    'C:\Users\Aadil\AppData\Roaming\npm'     = Get-DirSizeMb 'C:\Users\Aadil\AppData\Roaming\npm'
}
foreach ($k in $sizes.Keys) { '{0,-45} {1}' -f $k, $sizes[$k] }

Write-Output ''
Write-Output '=== Project footprint ==='
'E: free GB                ' + [math]::Round((Get-PSDrive E).Free / 1GB, 2)
'E:\VihaanX-Build size MB  ' + (Get-DirSizeMb 'E:\VihaanX-Build')

$leaks = @($rows | Where-Object { $_.State -eq 'LEAK' })
$stale = @($rows | Where-Object { $_.State -eq 'STALE-PROCESS' -or $_.State -eq 'UNSET' })
Write-Output ''
if ($leaks.Count -gt 0) {
    Write-Output ('RESULT: LEAK -> ' + (($leaks | ForEach-Object { $_.Name }) -join ', '))
    exit 1
}
if ($stale.Count -gt 0) {
    Write-Output ('RESULT: PASS (with stale process env: ' + (($stale | ForEach-Object { $_.Name }) -join ', ') + ')')
    Write-Output 'Open a NEW terminal for these values to appear in-process.'
    exit 0
}
Write-Output 'RESULT: PASS - all cache/temp paths on E:'
exit 0