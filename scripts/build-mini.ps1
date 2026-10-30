# SPDX-License-Identifier: GPL-2.0-or-later
param([string]$Name=('kws-x1-mini-'+(Get-Date -Format yyyyMMdd-HHmmss)),[string]$FreedoomZip='',[string]$UpstreamCache='')
if ($Name -notmatch '^[A-Za-z0-9_-]+$') {throw 'Use a simple output name'}
. "$PSScriptRoot\env.ps1"
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskMini=Join-Path $taskRoot 'artifacts\mini'
$taskBoard=Join-Path $taskMini 'board'
$taskImage=Join-Path $taskMini "$Name.X1C"
if (Test-Path -LiteralPath $taskImage) {throw 'Output exists; choose a new Name'}
Push-Location $taskRoot
try {
    & $env:KWS_PYTHON scripts\prepare-sources.py --check
    if ($LASTEXITCODE) {throw 'Prepare the pinned PC sources first'}
    $env:HOSTCC='clang'
    $taskGenArgs=@('standalone\generate.py')
    if ($FreedoomZip) {$taskGenArgs+=@('--freedoom-zip',(Resolve-Path -LiteralPath $FreedoomZip).Path)}
    if ($UpstreamCache) {$taskGenArgs+=@('--upstream-cache',(Resolve-Path -LiteralPath $UpstreamCache).Path)}
    & $env:KWS_PYTHON @taskGenArgs
    if ($LASTEXITCODE) {throw 'Mini data generation failed'}
    if (!(Test-Path -LiteralPath "$taskBoard\.git")) {
        if ((Test-Path -LiteralPath $taskBoard) -and (Get-ChildItem -LiteralPath $taskBoard -Force)) {throw 'Preserve the existing non-repository mini board directory'}
        git clone --no-hardlinks "$taskRoot\vendor\kws-x1-standalone-rs" $taskBoard
        if ($LASTEXITCODE) {throw 'Separate board checkout failed'}
    }
    & $env:KWS_PYTHON scripts\stage-port.py --mini --board $taskBoard
    if ($LASTEXITCODE) {throw 'Mini adapter staging failed'}
    & $env:KWS_PYTHON scripts\build-engine.py --host-test --generated artifacts\mini\gen --output artifacts\mini\host-engine
    if ($LASTEXITCODE) {throw 'Mini host engine build failed'}
    & $env:KWS_PYTHON standalone\test-mini.py
    if ($LASTEXITCODE) {throw 'Mini real-engine verification failed'}
    $taskRustArgs=@('--edition=2024','--test','tests/mini-assets.rs','-o',"$taskMini\asset-reader-test.exe")
    if ($env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER) {$taskRustArgs+=@('-C',"linker=$env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER")}
    if ($env:APDO_LLVM_BIN) {$taskRustArgs+=@('-C',"dlltool=$env:APDO_LLVM_BIN\llvm-dlltool.exe")}
    rustc @taskRustArgs
    if ($LASTEXITCODE) {throw 'Mini asset reader test build failed'}
    & "$taskMini\asset-reader-test.exe"
    if ($LASTEXITCODE) {throw 'Mini internal flash reader verification failed'}
    & $env:KWS_PYTHON scripts\build-engine.py --generated artifacts\mini\gen --output artifacts\mini\engine
    if ($LASTEXITCODE) {throw 'Mini ARM engine build failed'}
    $env:KWS_ENGINE_LIB=Join-Path $taskMini 'engine'
    Push-Location $taskBoard
    try {
        cargo build --release --locked -p firmware --target thumbv7em-none-eabihf
        if ($LASTEXITCODE) {throw 'Standalone firmware build failed'}
        cargo build --release --locked -p firmware-pack -p flasher --target x86_64-pc-windows-gnu
        if ($LASTEXITCODE) {throw 'Mini host tools build failed'}
        $taskPack=Join-Path $taskBoard 'target\x86_64-pc-windows-gnu\release\firmware-pack.exe'
        $taskFlash=Join-Path $taskBoard 'target\x86_64-pc-windows-gnu\release\flasher.exe'
        $taskFirmware=Join-Path $taskBoard 'target\thumbv7em-none-eabihf\release\firmware'
        $taskUnpacker=Join-Path $taskBoard 'target\thumbv7em-none-eabihf\release\unpacker'
        & $taskPack pack --firmware $taskFirmware --unpacker $taskUnpacker --out $taskImage
        if ($LASTEXITCODE) {throw 'Standalone image packing failed'}
        $taskHash=(Get-FileHash -LiteralPath $taskImage -Algorithm SHA256).Hash.ToLowerInvariant()
        & $taskPack audit --firmware $taskFirmware --unpacker $taskUnpacker --image $taskImage --confirm-sha256 $taskHash
        if ($LASTEXITCODE) {throw 'Standalone image audit failed'}
        & $taskFlash --dry-run --image $taskImage --confirm-sha256 $taskHash
        if ($LASTEXITCODE) {throw 'Standalone offline update validation failed'}
        "$taskHash  $Name.X1C" | Set-Content -LiteralPath "$taskImage.sha256" -Encoding ascii
        Copy-Item -LiteralPath $taskFirmware -Destination "$taskImage.firmware.elf"
        Copy-Item -LiteralPath $taskUnpacker -Destination "$taskImage.unpacker.elf"
        Write-Output "Created and audited $taskImage; no USB or device accessed"
    } finally {Pop-Location}
} finally {Pop-Location}
