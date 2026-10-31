# APDO — DOOM on KWS-X1

[English](README.md) · [日本語](README.ja.md)

## Firmware downloads and risks

**Experimental, unofficial firmware: flashing can leave the meter unbootable, and recovery is not guaranteed.** The stock measurement/PD/QC application is replaced. Electrical passthrough and protection behavior are not qualified; use only the required power/data connection, with other equipment disconnected. Hardware damage is possible. Stock restoration, full calibration/loader recovery and long-duration stability are unverified. Use at your own risk, without warranty; only one Bootloader V1.1 device was tested.

Choose the [PC-connected wide E1M1 release](https://github.com/inuchanbt/apdo-doom-on-kws-x1/releases/tag/pc-wide-v7r2) or [power-only standalone wide mini release](https://github.com/inuchanbt/apdo-doom-on-kws-x1/releases/tag/standalone-wide-v3). Each provides an `.X1C`, checksums, instructions, notices and corresponding source. **Read [the full risks and vendor OTA instructions](docs/FIRMWARE.md) before updating.** Both release images were installed with **KWS-X1 OTA Tool V1.0**, directly connected to the PC, and their startup logo/game operation were confirmed on the same Bootloader V1.1 unit. See the [OTA validation record](docs/validation/vendor-ota-banner.json).

Release source is on each matching tag; `main` retains the earlier baseline.

**The KOWSI KWS-X1 USB-C power meter runs DOOM.** This port executes a low-memory DOOM engine and renders Freedoom's E1M1 on the meter's HC32F460. A USB-connected PC supplies game assets that do not fit on the device.

The game runs on the meter. **A PC connection is required during play.** The current version uses the physical buttons; browser controls and a PC video preview have not been implemented.

## Verified on hardware

| Item | Result |
| --- | --- |
| Device | One KOWSI KWS-X1; Bootloader V1.1 |
| Execution | Native Cortex-M4 / HC32F460; nominal 192 MHz profile |
| Game | Freedoom 0.13.0, E1M1 |
| Display | 180×135, centered on the 240×135 LCD; full 4:3 game view |
| Controls | Movement, turning, firing, use, and menus confirmed |
| v3 performance | Median 180 ms per frame, about **5.6 fps**, in the starting area |
| USB | CDC asset streaming; length, sequence, address, and CRC32 validation |
| Update | Bootloader acceptance and flasher exit code 0 confirmed for v2/v3 |
| Stock restoration | Compatible stock-container structure checked; **restoration not tested** |

The initial v2 sample measured 1,174 ms per frame and 669 ms of USB wait. v3 measured 180 ms per frame and 4 ms of USB wait: about **6.5× faster** in these starting-area samples. Scene changes and uncached assets affect the rate. See [validation and limits](docs/VALIDATION.md) for sample sizes and evidence.

No sound, saves, persistent game settings, or supported map transition is included. Meter measurement, PD, and QC tasks do not run. Use the PC's data-capable USB connection and leave other equipment disconnected.

## Controls

| Action | Meter buttons |
| --- | --- |
| Move forward | OK |
| Turn | Left / Right |
| Fire | Back |
| Open a door / use a switch | Left + Right |
| Open the menu | OK + Back |
| Menu up / down | Left / Right |
| Menu confirm / back | OK / Back |
| Enter the original update loader | Hold Back + OK while connecting USB |

Buttons are sampled every 5 ms, with debouncing and a bounded edge queue so short presses survive slow rendered frames.

## Source and build

The tested build environment is **Windows, PowerShell, Python 3.12, Rust's Windows GNU toolchain, and LLVM-MinGW**. Other build environments are not qualified. Install the tools and optional local configuration described in [BUILD.md](docs/BUILD.md), then:

```powershell
git clone https://github.com/inuchanbt/apdo-doom-on-kws-x1.git
cd apdo-doom-on-kws-x1
. .\scripts\env.ps1
& $env:KWS_PYTHON -m pip install -r requirements.txt
& $env:KWS_PYTHON scripts\prepare-sources.py
.\scripts\prepare-data.ps1
.\scripts\build.ps1 -Name kws-x1-doom
```

The source revisions and asset hashes are fixed in [SOURCE_LOCK.json](SOURCE_LOCK.json); Rust dependencies are fixed in [locks/board.Cargo.lock](locks/board.Cargo.lock). Source preparation refuses conflicting edits. Data conversion downloads and verifies Freedoom, or accepts its verified release ZIP from a local cache.

**These commands do not open USB or flash a device.** The build creates an X1C, audits its decompressed contents and erase layout, and runs the flasher's offline validation. Read [updating and recovery](docs/RECOVERY.md) before a hardware update. This repository publishes source, not a universal firmware installer.

## Supply assets from the PC

With v3 installed, start the server before or after connecting the meter:

```powershell
. .\scripts\env.ps1
& $env:KWS_PYTHON scripts\serve-game.py --auto --version 3
```

Automatic discovery selects only this port's development USB identity and serial string. With multiple meters, use `--port COM5` with the correct port instead. Keep one asset server running while playing; it owns the USB connection. It has no flashing commands.

The server logs frame time, asset requests, USB wait, inputs, decoded-page count, and untouched stack space to `artifacts/runtime.jsonl`. Choose a separate file with `--stats artifacts/run.jsonl`. v1/v2 can use the corresponding `--version` value.

A disconnect, bad response, or asset-read timeout stops this experimental firmware. To resume, restart the server and power-cycle the meter. Automatic gameplay reconnection is not implemented.

## How v3 fits

- The same low-memory engine integration used in [DOOM on KM003C](https://github.com/inuchanbt/apdo-doom-on-km003c) runs on the KWS-X1.
- Board startup, LCD/DMA transport, the original-loader update format, and the unpacker come from [kralonur/kws-x1-standalone-rs](https://github.com/kralonur/kws-x1-standalone-rs).
- 179 frequently read Freedoom pages occupy 122,863 compressed bytes in the existing upper application region. Remaining assets stream over USB as bounded LZ4 blocks.
- An 8 KiB decoded-page cache and a 32 KiB compressed LRU cache reduce repeat transfers. The framebuffer stores the 180×135 game rectangle; the LCD's black sidebars consume no framebuffer memory.
- Packaging computes a stream placement that protects unread compressed bytes during first-boot unpacking, then rehearses the exact decoder and checks every output byte.

## Repository layout

| Path | Contents |
| --- | --- |
| `native/` | C engine bridge and host test harness |
| `overlays/firmware/` | KWS-X1 adapters and the licensed pinned Freedoom subset |
| `patches/` | Changes applied to fixed upstream sources |
| `locks/` | Pinned Rust dependency resolution |
| `scripts/` | Source/data preparation, build, tests, profiling, and asset server |
| `tests/` | Engine, protocol, decoder, and cache checks |
| `docs/` | Build, recovery, and validation details |
| `notices/` | Third-party license copies and Freedoom credits |
| `config/` | Example machine-local tool settings |
| `vendor/`, `tools/` | Local sources and toolchains; ignored |
| `local/`, `firmware/`, `artifacts/`, `backups/` | Local settings, vendor downloads, generated files, and evidence; ignored |

## Credits and licenses

Thanks to the KWS-X1 firmware and HC32 HAL authors, [DMC100-Doom](https://github.com/ArturBieniek4/DMC100-Doom), [doomgeneric](https://github.com/ozkl/doomgeneric), id Software, and [Freedoom](https://freedoom.github.io/).

The original repository [MIT license](LICENSE) remains in place for material without a more specific notice. Engine integration and files marked `GPL-2.0-or-later` use [COPYING](COPYING). The included Freedoom subset uses its own BSD license; no commercial DOOM IWAD or manufacturer firmware is included. Upstream licenses remain applicable. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the scope and attributions.
