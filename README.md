# APDO — DOOM on KWS-X1

[English](README.md) · [日本語](README.ja.md)

**Widescreen development branch:** v7r1 uses the 240×135 LCD, keeps natural proportions, widens horizontal FOV to about 106°, and redistributes the HUD. Native/API checks pass, and the user confirmed complete display/HUD, normal operation and responsive gameplay. A 180-frame starting-area sample measured **158 ms (6.3 fps)** with preview disabled. See [WIDESCREEN.md](docs/WIDESCREEN.md). Historical 4:3 results are identified by their earlier version numbers below.

**The KOWSI KWS-X1 USB-C power meter runs DOOM.** This port executes a low-memory DOOM engine and renders Freedoom's E1M1 on the meter's HC32F460. A USB-connected PC supplies game assets that do not fit on the device.

The game runs on the meter. **A PC connection is required during play.** Browser keyboard/pointer controls and a switchable, low-rate preview of the actual device framebuffer are available. v5 adds an enclosure mockup and real LCD rotation through 180 degrees. Physical buttons remain available.

This branch adapts KM003C performance improvements for PC-connected E1M1: faster compilation, a small record cache, reduced stale-input queuing and faster asset decoding. v6r1 measured **135 ms per frame (7.4 fps)** in a 180-frame starting-area sample with preview disabled; wall throughput was 7.0 fps. See [changes, measurements and verification scope](docs/PC-PERFORMANCE.md).

The user confirmed normal on-device display and PC controls, and smoother gameplay than before.

## Verified on hardware

| Item | Result |
| --- | --- |
| Device | One KOWSI KWS-X1; Bootloader V1.1 |
| Execution | Native Cortex-M4 / HC32F460; nominal 192 MHz profile |
| Game | Freedoom 0.13.0, E1M1 |
| Display (v7r1) | Full 240×135 LCD, about 106° horizontal FOV, natural proportions and complete HUD confirmed by the user |
| Controls | Movement, turning, firing, use, and menus confirmed |
| v3 performance | Median 180 ms per frame, about **5.6 fps**, in the starting area |
| USB | CDC asset streaming; length, sequence, address, and CRC32 validation |
| PC link (v4) | Remote input, short taps, timed release, preview pause/resume, and capture checked through the local API on hardware |
| LCD rotation (v5) | 0°/180° acknowledged through the browser; physical rotation and complete HUD confirmed by the user |
| Update | Bootloader acceptance and flasher exit code 0 confirmed for v2/v3/v4 |
| Stock restoration | Compatible stock-container structure checked; **restoration not tested** |

The initial v2 sample measured 1,174 ms per frame and 669 ms of USB wait. v3 measured 180 ms per frame and 4 ms of USB wait: about **6.5× faster** in these starting-area samples. Scene changes and uncached assets affect the rate. See [validation and limits](docs/VALIDATION.md) for sample sizes and evidence.

No sound, saves, persistent game settings, or supported map transition is included. Meter measurement, PD, and QC tasks do not run. Use the PC's data-capable USB connection and leave other equipment disconnected.

The separate [standalone mini-DOOM branch](https://github.com/inuchanbt/apdo-doom-on-kws-x1/tree/codex/standalone-mini-doom) contains a small dedicated map confirmed to boot and play on power alone. This branch keeps the full, PC-connected E1M1 version.

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

## Play from the PC (v4/v5)

After building and installing the current firmware, start the controller:

```powershell
.\scripts\play.ps1
```

Keep the server running and open its printed local URL. Click **Enable keyboard**, then use:

| Action | PC input |
| --- | --- |
| Move forward / backward | W / S or Up / Down |
| Turn left / right | A / D or Left / Right |
| Fire | Space or Ctrl |
| Use | E |
| Menu / confirm | Esc / Enter |

The page also has holdable pointer/touch buttons. **Release all** clears PC input while continuing asset delivery. Switching away from the page releases the keys and disables keyboard capture. Press **Enable keyboard** again when returning.

The wide preview is **160×90, at most one capture per second** (120×90 for earlier 4:3 firmware); the meter still renders at its own rate. Disable **Live preview** to prioritize gameplay speed, or use **Save frame** to download the latest BMP. The meter FPS shown on the page includes preview transfer pauses. The v3 benchmark above remains a separate historical measurement.

The preview is inset into the supplied KWS-X1 enclosure photograph. On v5, **Rotate LCD 180°** rotates the real meter display at a frame boundary and waits for device confirmation. Choose **Follow LCD · upright game** to turn the enclosure around the upright preview, or **Fixed enclosure · LCD view** to show how the LCD looks in the stationary enclosure. Rotation keeps input mappings unchanged and resets on power-up. Saved BMPs retain the upright logical frame.

Use **Enlarge preview** for a larger view without the enclosure, useful for inspecting menus. It enlarges the same 120×90 capture; it does not restore detail lost at capture resolution. Opening it releases PC keys. **Close** or Esc returns to the controls; enable the keyboard again to continue playing.

The controller supplies assets and owns the USB port: stop any other asset server first. It recognizes v4's `KWSX1DOOM04` and v5's `KWSX1DOOM05` serial strings; rotation is disabled on v4. Older firmware needs an update. `-NoBrowser`, `-Port 8080`, and `-UsbPort COM6` are optional launcher arguments. **Stop server** also ends asset delivery; restart the server and power-cycle the meter to play again. See [PC controls and protocol](docs/PC-CONTROLS.md) for details and verification limits.

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

## Headless asset server / older firmware

For v5 without browser controls or preview, run the headless server instead:

```powershell
. .\scripts\env.ps1
& $env:KWS_PYTHON scripts\serve-game.py --auto --version 5
```

Automatic discovery selects only this port's development USB identity and serial string. With multiple meters, use `--port COM5` with the correct port instead. Keep one asset server running while playing; it owns the USB connection. It has no flashing commands.

The headless server logs frame time, asset requests, USB wait, inputs, decoded-page count, and untouched stack space to `artifacts/runtime.jsonl`. The browser controller defaults to `artifacts/runtime-v4.jsonl` (also for v5). Choose a separate file with `--stats artifacts/run.jsonl` when invoking either Python entry point. v1/v2/v3/v4 can use the corresponding `--version` value in the headless server.

A disconnect, bad response, or asset-read timeout stops this experimental firmware. To resume, restart the server and power-cycle the meter. Automatic gameplay reconnection is not implemented.

## How it fits

- The same low-memory engine integration used in [DOOM on KM003C](https://github.com/inuchanbt/apdo-doom-on-km003c) runs on the KWS-X1.
- Board startup, LCD/DMA transport, the original-loader update format, and the unpacker come from [kralonur/kws-x1-standalone-rs](https://github.com/kralonur/kws-x1-standalone-rs).
- 179 frequently read Freedoom pages occupy 122,863 compressed bytes in the existing upper application region. Remaining assets stream over USB as bounded LZ4 blocks.
- An 8 KiB decoded-page cache and a 32 KiB compressed LRU cache reduce repeat transfers. The framebuffer stores the 180×135 game rectangle; the LCD's black sidebars consume no framebuffer memory.
- Packaging computes a stream placement that protects unread compressed bytes during first-boot unpacking, then rehearses the exact decoder and checks every output byte.
- v4 multiplexes assets, leased controls, telemetry, and optional previews over the same CDC connection. It samples the completed framebuffer in bounded chunks without allocating another framebuffer.

## Repository layout

| Path | Contents |
| --- | --- |
| `native/` | C engine bridge and host test harness |
| `overlays/firmware/` | KWS-X1 adapters and the licensed pinned Freedoom subset |
| `patches/` | Changes applied to fixed upstream sources |
| `locks/` | Pinned Rust dependency resolution |
| `scripts/` | Source/data preparation, build, tests, profiling, and PC/asset servers |
| `web/` | Local browser controller and real-device preview |
| `tests/` | Engine, protocol, decoder, and cache checks |
| `docs/` | Build, recovery, and validation details |
| `notices/` | Third-party license copies and Freedoom credits |
| `config/` | Example machine-local tool settings |
| `vendor/`, `tools/` | Local sources and toolchains; ignored |
| `local/`, `firmware/`, `artifacts/`, `backups/` | Local settings, vendor downloads, generated files, and evidence; ignored |

## Credits and licenses

Thanks to the KWS-X1 firmware and HC32 HAL authors, [DMC100-Doom](https://github.com/ArturBieniek4/DMC100-Doom), [doomgeneric](https://github.com/ozkl/doomgeneric), id Software, and [Freedoom](https://freedoom.github.io/).

The original repository [MIT license](LICENSE) remains in place for material without a more specific notice. Engine integration and files marked `GPL-2.0-or-later` use [COPYING](COPYING). The included Freedoom subset uses its own BSD license; no commercial DOOM IWAD or manufacturer firmware is included. Upstream licenses remain applicable. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the scope and attributions.
