# SPDX-License-Identifier: GPL-2.0-or-later
param([string]$Name = ('kws-x1-doom-' + (Get-Date -Format yyyyMMdd-HHmmss)))
if ($Name -notmatch '^[A-Za-z0-9_-]+$') { throw 'Use a simple output name' }
. "$PSScriptRoot\env.ps1"
$taskRoot = Split-Path -Parent $PSScriptRoot
$taskBoard = Join-Path $taskRoot 'vendor\kws-x1-standalone-rs'
$taskOutput = Join-Path $taskRoot "artifacts\$Name.X1C"
if (Test-Path -LiteralPath $taskOutput) { throw 'Output already exists; select another Name' }
& $env:KWS_PYTHON "$PSScriptRoot\stage-port.py"
if ($LASTEXITCODE) { throw 'Source staging failed' }
& $env:KWS_PYTHON "$PSScriptRoot\build-engine.py"
if ($LASTEXITCODE) { throw 'Engine build failed' }
$env:KWS_ENGINE_LIB = Join-Path $taskRoot 'artifacts\engine'
Push-Location $taskBoard
try {
    cargo build --release --locked -p firmware --target thumbv7em-none-eabihf
    if ($LASTEXITCODE) { throw 'Firmware build failed' }
    cargo build --release --locked -p firmware-pack -p flasher --target x86_64-pc-windows-gnu
    if ($LASTEXITCODE) { throw 'Host tools build failed' }
    $taskPack = Join-Path $taskBoard 'target\x86_64-pc-windows-gnu\release\firmware-pack.exe'
    $taskFlasher = Join-Path $taskBoard 'target\x86_64-pc-windows-gnu\release\flasher.exe'
    $taskFirmware = Join-Path $taskBoard 'target\thumbv7em-none-eabihf\release\firmware'
    $taskUnpacker = Join-Path $taskBoard 'target\thumbv7em-none-eabihf\release\unpacker'
    & $taskPack pack --firmware $taskFirmware --unpacker $taskUnpacker --out $taskOutput
    if ($LASTEXITCODE) { throw 'Image packing failed' }
    $taskHash = (Get-FileHash -LiteralPath $taskOutput -Algorithm SHA256).Hash.ToLowerInvariant()
    & $taskPack audit --firmware $taskFirmware --unpacker $taskUnpacker --image $taskOutput --confirm-sha256 $taskHash
    if ($LASTEXITCODE) { throw 'Image audit failed' }
    & $taskFlasher --dry-run --image $taskOutput --confirm-sha256 $taskHash
    if ($LASTEXITCODE) { throw 'Offline update validation failed' }
    "$taskHash  $Name.X1C" | Set-Content -LiteralPath "$taskOutput.sha256" -Encoding ascii
    Copy-Item -LiteralPath $taskFirmware -Destination "$taskOutput.firmware.elf"
    Copy-Item -LiteralPath $taskUnpacker -Destination "$taskOutput.unpacker.elf"
    Write-Output "Created and audited $taskOutput; no device accessed"
} finally { Pop-Location }
