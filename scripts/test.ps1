# SPDX-License-Identifier: GPL-2.0-or-later
. "$PSScriptRoot\env.ps1"
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    & $env:KWS_PYTHON scripts\prepare-sources.py --check
    if ($LASTEXITCODE) { throw 'Source verification failed' }
    & $env:KWS_PYTHON scripts\build-engine.py --host-test
    if ($LASTEXITCODE) { throw 'Host engine build failed' }
    foreach ($taskTest in @('tests/test-engine.py','tests/test-short-input.py','tests/test-input-cadence.py','tests/test-record-cache.py','tests/test-stream.py','scripts/make-codec-vectors.py')) {
        & $env:KWS_PYTHON $taskTest
        if ($LASTEXITCODE) { throw "Failed: $taskTest" }
    }
    & $env:KWS_PYTHON -m unittest discover -s tests -p test_pc_controller.py -v
    if ($LASTEXITCODE) { throw 'PC controller tests failed' }
    & $env:KWS_PYTHON scripts\profile-cache.py | Set-Content artifacts\cache-comparison.log -Encoding utf8
    if ($LASTEXITCODE) { throw 'Engine access trace failed' }
    $taskRustArgs = @('--edition=2024', '--test', 'tests/optimizations.rs', '-o', 'artifacts/optimizations-test.exe')
    if ($env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER) { $taskRustArgs += @('-C', "linker=$env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER") }
    if ($env:APDO_LLVM_BIN) { $taskRustArgs += @('-C', "dlltool=$env:APDO_LLVM_BIN\llvm-dlltool.exe") }
    rustc @taskRustArgs
    if ($LASTEXITCODE) { throw 'Optimization test build failed' }
    & .\artifacts\optimizations-test.exe --nocapture
    if ($LASTEXITCODE) { throw 'Optimization tests failed' }
    cargo test --manifest-path vendor\kws-x1-standalone-rs\Cargo.toml --release --locked -p firmware-pack -p firmware-image -p flasher --target x86_64-pc-windows-gnu
    if ($LASTEXITCODE) { throw 'Container/flasher tests failed' }
    Write-Output 'All offline checks passed; no device accessed'
} finally { Pop-Location }
