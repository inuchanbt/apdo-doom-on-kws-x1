# SPDX-License-Identifier: GPL-2.0-or-later
param([string]$FreedoomZip = '')
. "$PSScriptRoot\env.ps1"
$taskRoot = Split-Path -Parent $PSScriptRoot
& $env:KWS_PYTHON "$PSScriptRoot\prepare-sources.py" --check
if ($LASTEXITCODE) { throw 'Prepare the pinned sources before generating data' }
$env:HOSTCC = 'clang'
$taskArguments = @('-I', 'tools/conv/__main__.py', '--packs', 'E1M1')
if ($FreedoomZip) { $taskArguments += @('--zip', (Resolve-Path -LiteralPath $FreedoomZip).Path) }
$taskArguments += 'all'
Push-Location "$taskRoot\vendor\dmc100-doom"
try {
    & $env:KWS_PYTHON @taskArguments
    if ($LASTEXITCODE) { throw 'Freedoom data conversion failed' }
} finally { Pop-Location }
& $env:KWS_PYTHON "$PSScriptRoot\serve-game.py" --check
if ($LASTEXITCODE) { throw 'Generated data does not match the pinned pack' }
