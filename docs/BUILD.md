# Build and source reconstruction

The supported, tested workflow is Windows with PowerShell, Python 3.12, Rust's `stable-x86_64-pc-windows-gnu` toolchain, and LLVM-MinGW. The experiment used Rust 1.99.1 and LLVM-MinGW 20261020 UCRT x86_64. Those are recorded tool versions, not a claim that every newer or older toolchain works.

## 1. Install tools

- Git and Python 3.12, available on PATH or configured explicitly.
- Rustup, then the GNU host toolchain and ARM target:

```powershell
rustup toolchain install stable-x86_64-pc-windows-gnu
rustup target add --toolchain stable-x86_64-pc-windows-gnu thumbv7em-none-eabihf
python -m pip install -r requirements.txt
```

- Extract [LLVM-MinGW](https://github.com/mstorsjo/llvm-mingw/releases) with Clang, `llvm-ar`, `llvm-nm`, and `llvm-dlltool`. Either use `tools/llvm-mingw-20261020-ucrt-x86_64/` or set `APDO_LLVM_BIN` to its `bin` directory.

`scripts/env.ps1` uses standard Rustup/Cargo locations and respects existing environment variables. It does not depend on another project directory. Optional machine-local overrides:

```powershell
New-Item -ItemType Directory -Force local
Copy-Item config/tools.example.ps1 local/tools.ps1
# Edit local/tools.ps1 to point to your LLVM and Python executables.
. .\scripts\env.ps1
```

`KWS_PYTHON` is one Python executable path, without command-line arguments. `CARGO_HOME` and `RUSTUP_HOME` can be set for nonstandard installations. `local/` is ignored by Git.

## 2. Reconstruct fixed sources

```powershell
& $env:KWS_PYTHON scripts\prepare-sources.py
```

This obtains the exact board, DMC100-Doom, and doomgeneric revisions from `SOURCE_LOCK.json`, applies `patches/dmc100-doom.patch`, and stages the board adapters from `overlays/firmware/`. It refuses a different HEAD, a non-repository source directory, or conflicting edits. It never resets or deletes an existing checkout.

Board dependencies are fixed by `locks/board.Cargo.lock`. The staging script accepts the upstream version, its exact generated result, or the previous staged hash saved in `artifacts/staged-hashes.json`. The latter lets a later adapter revision replace the known previous revision while preserving unrelated edits.

Verify prepared sources without writing or fetching:

```powershell
& $env:KWS_PYTHON scripts\prepare-sources.py --check
```

Source preparation does not require a stock application, bootloader dump, device serial, recovery backup, or USB device.

## 3. Generate Freedoom data

```powershell
.\scripts\prepare-data.ps1
```

The converter obtains Freedoom 0.13.0 and checks the upstream release ZIP's SHA-256 before extraction. To use a local copy:

```powershell
.\scripts\prepare-data.ps1 -FreedoomZip C:\Downloads\freedoom-0.13.0.zip
```

It generates the engine's `gen/` files and `vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT`. The final pack must be exactly **2,802,000 bytes** with SHA-256:

```text
6b25a4f1adb6f1f1f5f42226c272b93ccff4f356ac8d7034cf83712b2da70c08
```

The pinned 179-page subset is already included under `overlays/firmware/` with its Freedoom license and credits in `notices/`. Staging validates its size and hash. Normal builds do not reselect pages. `pin-assets.py` is an optimization-development tool: it uses a recorded host-engine trace, and changing its output requires updating the source lock and revalidating the firmware.

## 4. Build and audit

```powershell
.\scripts\build.ps1 -Name kws-x1-doom
```

The script:

1. Stages the board adapters and compiles the C engine for Cortex-M4 hard-float.
2. Builds the firmware, first-boot unpacker, packer, and flasher.
3. Creates `artifacts/kws-x1-doom.X1C` without replacing an existing output.
4. Audits the image against the linked ELFs and runs the flasher's `--dry-run`.
5. Saves the SHA-256 and matching firmware/unpacker ELFs alongside the image.

No build step opens USB. The firmware starts at `0x10000`; selected engine functions and pinned asset pages occupy the existing upper application region. The packer computes the earliest sector-aligned stream position that preserves unread compressed data during unpacking. It retains the upstream erase-margin guard, rehearses the same decoder used by the device, and compares the full decompressed output with both linked regions.

See [RECOVERY.md](RECOVERY.md) for the separate device-update procedure.

## 5. Offline validation

```powershell
.\scripts\test.ps1
```

This runs the real host engine for 140 frames, verifies asset protocol framing and failure handling, round-trips every Freedoom page through the Python encoder and Rust decoder, checks cache allocation/eviction, replays engine reads, and runs the board packer's/container tests. It does not contact USB. Cargo may download locked dependencies on the first run; after fetching them, `CARGO_NET_OFFLINE=true` can enforce offline dependency use.

These checks do not emulate the MCU, panel, USB controller, or bootloader. See [VALIDATION.md](VALIDATION.md) for the actual hardware evidence and its limits.
