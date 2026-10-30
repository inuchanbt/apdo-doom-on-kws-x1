# SPDX-License-Identifier: GPL-2.0-or-later
$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
if (Test-Path -LiteralPath "$taskRoot\local\tools.ps1") { . "$taskRoot\local\tools.ps1" }
$taskCargoRoot = if ($env:CARGO_HOME) { $env:CARGO_HOME } else { Join-Path $env:USERPROFILE '.cargo' }
$taskRustupRoot = if ($env:RUSTUP_HOME) { $env:RUSTUP_HOME } else { Join-Path $env:USERPROFILE '.rustup' }
if (-not $env:APDO_LLVM_BIN) {
    $taskLocalLlvm = Join-Path $taskRoot 'tools\llvm-mingw-20261020-ucrt-x86_64\bin'
    if (Test-Path -LiteralPath $taskLocalLlvm) { $env:APDO_LLVM_BIN = $taskLocalLlvm }
}
$taskToolchain = Join-Path $taskRustupRoot 'toolchains\stable-x86_64-pc-windows-gnu'
$taskGcc = Join-Path $taskToolchain 'lib\rustlib\x86_64-pc-windows-gnu\bin\self-contained'
if (Test-Path -LiteralPath "$taskGcc\x86_64-w64-mingw32-gcc.exe") {
    $env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_LINKER = Join-Path $taskGcc 'x86_64-w64-mingw32-gcc.exe'
}
if ($env:APDO_LLVM_BIN) { $env:CARGO_TARGET_X86_64_PC_WINDOWS_GNU_RUSTFLAGS = "-C dlltool=$env:APDO_LLVM_BIN\llvm-dlltool.exe" }
$env:CARGO_NET_GIT_FETCH_WITH_CLI = 'true'
$taskPaths = @("$taskToolchain\bin", "$taskCargoRoot\bin", $taskGcc, $env:APDO_LLVM_BIN) + ($env:PATH -split ';')
$env:PATH = ($taskPaths | Where-Object { $_ } | Select-Object -Unique) -join ';'
if (-not $env:KWS_PYTHON) { $env:KWS_PYTHON = 'python' }
