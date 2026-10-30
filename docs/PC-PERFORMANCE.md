# PC-connected E1M1 performance work

This work lives on `codex/kws-pc-performance`, based on PC v5 (`79c28bf`). The standalone mini-map remains on `codex/standalone-mini-doom`. The full E1M1 pack still requires the PC asset server.

## Changes adapted from KM003C

- Build input commands before simulation, rather than after drawing or between already scheduled tics. A slow draw must not pre-fill the next frame with old button states. The original 35 Hz simulation and bounded command buffer remain in use.
- Preserve the existing `D_WillBuildTic` guard, which keeps queued short presses intact when the command buffer is full.
- Use `-O2` for the C engine. Move `R_*` render functions into main application flash so the larger code fits alongside pinned assets. `P_*` functions and the existing asset blob remain in upper application flash.
- Add a four-way cache for reads of at most 16 bytes: 4 KiB of data plus 1,088 bytes of tags/replacement state. Longer column/flat reads bypass it. EOF fills are clipped to the pack size.
- The v6r1 follow-up replaces byte-at-a-time LZ4 overlap expansion with bounded prefix copies and doubling, with a fill fast path for offset one. The firmware package uses Rust `opt-level=2`; dependencies retain the upstream size profile. No additional asset RAM is allocated.

KM003C's faster external NOR setting does not apply to this board's USB/internal-flash asset path. Frame timing remains uncapped and scene-dependent.

These builds are named **PC v6/v6r1**, and deliberately retain the v5 USB protocol and `KWSX1DOOM05` development identity. The existing controller, enclosure preview, LCD rotation and enlarged menu view remain compatible.

## Offline results

A 100 ms simulated draw reproduces delayed turn press/release with `--legacy-input-queue`. With the fix, both changes take effect in the first following rendered frame. The full-buffer short-tap regression also passes.

The cache replay uses the real E1M1 engine: 35 neutral frames, 35 forward, 30 turning, 25 firing, then 15 neutral frames. Totals below exclude the first two frames. The decode model uses the same eight-page decoded LRU capacity as the firmware; it does not measure USB latency or MCU time.

| Short-record cache | Physical asset reads | Bytes requested | Modeled page decodes |
| --- | ---: | ---: | ---: |
| Disabled | 224,915 | 8,014,816 | 96,019 |
| 2 KiB | 223,261 | 8,247,906 | 93,796 |
| 4 KiB | 200,340 | 7,881,170 | 81,079 |

The selected cache reduces modeled decodes by **15.6%** and physical read calls by **10.9%** in this replay. All 140 complete framebuffer hashes match the no-cache build, including the `-O2` candidate. The cache also passes 1,044 byte-for-byte pack reads, unaligned/line/EOF boundaries, zero-length EOF reads and out-of-range rejection. These figures are not a hardware FPS improvement claim.

## Build budget

The audited `kws-x1-doom-pc-v6.X1C` has SHA-256:

```text
aafcd12456d43617bee677cb714b2612a2350b553b285bdb1f5771724cfd3aba
```

Main application: 158,832 bytes. Upper application: 150,972 bytes, with 12,868 bytes free. The update container has 10,127 unused content bytes and passes the full decompression/erase-layout audit and flasher dry-run. The linked stack reservation is 12,208 bytes; actual untouched stack must still be measured on hardware. SRAM2 remains at 64,984 of 65,536 bytes.

### v6r1 image

The same full audit and flasher dry-run passed for `kws-x1-doom-pc-v6r1.X1C`, SHA-256:

```text
4342c3b43ee7633038209333f6a14f78a6113c767a9824792bfa27f54ef5250d
```

Main application: 175,524 bytes. Upper: 150,944 bytes, with 12,896 bytes free. The container has 3,610 unused content bytes. The optimized decoder passes all 2,737 real pack pages and periodic-match tests spanning short/long matches, aligned/unaligned offsets and truncated output; all 13 Rust optimization tests pass at `opt-level=2`. Installation and native results are recorded below.

## Native v6 measurement

On 2026-10-31, v6 installed with final bootloader acceptance, reboot command and flasher exit **0**. It enumerated the v5-compatible CDC interface, completed the handshake, and streamed E1M1 plus live previews.

With preview temporarily disabled and all controls released, 180 starting-area frames (484–663) measured:

| Metric | v6 |
| --- | ---: |
| Median engine/render/LCD frame time | 166 ms |
| 1,000 / median frame time | 6.02 fps |
| Host-observed throughput including frame handoff | 5.73 fps |
| 95th-percentile frame time | 195 ms |
| Median USB wait | 4 ms |
| Median decoded pages | 838 |
| Minimum observed untouched stack | 9,848 bytes |

Preview was restored afterward. The historical v3 starting-area median was 180 ms; this is a modest improvement, not a matched v5 benchmark. Asset decoding remains frequent. See [validation/pc-v6.json](validation/pc-v6.json).

## Native v6r1 result

v6r1 also installed with final bootloader acceptance, reboot command and flasher exit **0**. After reconnecting the same controller, another 180 stationary starting-area frames (335–514) were collected with preview disabled:

| Metric | v6 | v6r1 |
| --- | ---: | ---: |
| Median engine/render/LCD frame time | 166 ms | **135 ms** |
| 1,000 / median frame time | 6.02 fps | **7.41 fps** |
| Host-observed throughput including handoff | 5.73 fps | **7.02 fps** |
| 95th-percentile frame time | 195 ms | 163 ms |
| Median USB wait | 4 ms | 3 ms |
| Median decoded pages | 838 | 837.5 |
| Minimum observed untouched stack | 9,848 bytes | 9,896 bytes |

In these two runs, the median rate improved by about **23%**. Decode counts are similar, consistent with improving the cost of each decode/read rather than changing the asset workload substantially. These are sequential runs at the same starting position, not identical game-tic snapshots, a matched v5 benchmark, or a worst-case scene measurement.

After measuring, 20/20 10 ms Esc press/release pairs sent through local HTTP toggled the native menu. Observed command-to-menu-telemetry delays were 156–391 ms; this does not measure browser event timing or photon latency. Forward, left/right turns, fire and use were acknowledged in applied-input telemetry and released. Rotation to 180° and back to 0° was acknowledged. Real preview BMPs were captured before and after controls; the final frame shows the scene and complete HUD. The test ended with menu closed, all remote inputs released, rotation 0° and preview enabled.

The user subsequently confirmed normal on-device display and PC controls, and reported that gameplay felt lighter than before. This supports the functional result and perceived improvement; it is not an additional FPS or endurance measurement. See [validation/pc-v6r1.json](validation/pc-v6r1.json). Refresh an already open browser page after a server restart so it obtains the new session token.

## Reproduce

After source/data preparation and loading `scripts/env.ps1`, compare cache builds:

```powershell
& $env:KWS_PYTHON scripts/build-engine.py --host-test --opt Oz --cache-kib 0
& $env:KWS_PYTHON tests/test-record-cache.py --report artifacts/cache-off.json
& $env:KWS_PYTHON scripts/build-engine.py --host-test --opt Oz --cache-kib 4
& $env:KWS_PYTHON tests/test-record-cache.py --reference artifacts/cache-off.json
& $env:KWS_PYTHON scripts/build-engine.py --host-test --opt O2 --cache-kib 4
& $env:KWS_PYTHON tests/test-record-cache.py --reference artifacts/cache-off.json
```

Reproduce the input regression, then restore the normal host build:

```powershell
& $env:KWS_PYTHON scripts/build-engine.py --host-test --legacy-input-queue
& $env:KWS_PYTHON tests/test-input-cadence.py --expect-legacy-lag
& $env:KWS_PYTHON scripts/build-engine.py --host-test
& $env:KWS_PYTHON tests/test-input-cadence.py
.\scripts\test.ps1
.\scripts\build.ps1 -Name kws-x1-doom-pc-v6r1
```

The image builder refuses an existing output name. Use a new name for a repeat build. Raw comparison reports and matching image/ELFs are retained under ignored `artifacts/`.
