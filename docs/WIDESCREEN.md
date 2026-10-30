# Full-width KWS-X1 prototype

Branch: `codex/kws-widescreen`, based on the verified v6r1 performance checkpoint `2aacd7a`. The user selected natural proportions and a wider field of view. **v7r1 is installed; native checks pass, and the user confirmed complete full-width display/HUD, normal operation and responsive gameplay.** The prior user-confirmed baseline was the 180×135 v6r1 build.

## Display geometry

The 3D scene fills **240×112** above a five-row message area and an 18-row status band. The whole LCD is **240×135**. It keeps the existing 320×200 world renderer and 320×240 combined source coordinates, with 160 logical columns in low detail.

Source columns map at 3/4 scale and rows at 9/16. To preserve geometry, horizontal focal length is reduced to 3/4 while vertical projection remains unchanged. Horizontal FOV increases from about 90° to **106°**. Sprite horizontal/vertical scales, weapon scale and floor texture stepping are adjusted separately. This preserves the vertical view and reveals more scene at the sides.

The HUD retains its original uniform 9/16 scale. Ammo, health, arms, face, armor/keys and the ammunition table are distributed across the bottom, with gaps between groups. Group boundaries preserve complete three-digit counters, including 200% health/armor. Menus and messages retain their proportions in the central 180-pixel area.

## Indexed framebuffer and RAM

The original 180×135 RGB565 frame used 48,600 bytes. A full RGB565 frame would need 64,800 bytes, conflicting with the asset cache in SRAM2. The prototype instead stores 32,400 palette indices plus the 512-byte RGB565 palette. All world, sprite and UI colors remain exact palette colors. Four rows are expanded into a temporary RGB565 buffer for each DMA transfer.

The freed space allows the decoded-page cache to move from ordinary RAM into SRAM2 and grow from 8 to 12 KiB. SRAM2 uses **62,464 / 65,536 bytes**, including alignment and the existing compressed-cache bank. The linked ordinary-RAM stack reservation is **20,120 bytes**. Minimum untouched stack observed was 17,712 bytes during measurement and 17,700 bytes after the functional checks. SRAM2 parity is initialized before any byte writes or reads.

## PC preview

The wide capture is **160×90 RGB565**, sampled from the same frozen indexed frame, with no second framebuffer. The controller accepts both the legacy 120×90 and new 160×90 captures, preserving their actual dimensions in BMP exports and the enclosure view. The enlarged preview also follows the capture aspect ratio.

The control/rotation transport retains v5 framing and the development identity. **Restart the updated PC server before running wide firmware**: older servers reject the new preview dimensions. Existing 4:3 firmware remains supported by the updated server.

## Offline verification

- Real engine: 140 game frames, movement, turn, fire, menus, HUD redraw, input cadence and short-tap regressions passed.
- The production LCD mapper is connected directly to real engine column/palette callbacks in a host test. Captures show both LCD edges, menus and complete HUD counters at 200% health/armor and 200 ammo.
- Projection telemetry confirms horizontal FOV between 105° and 108°.
- All 15 Python controller tests and 15 Rust optimization/mapper tests pass, including both preview sizes, exact palette expansion and frame-edge coverage.
- All 2,737 real asset pages decode exactly; nine container/packer regressions pass.
- The update image passed full decompression/layout audit and flasher dry-run. No device was opened during these checks.

Image: `artifacts/kws-x1-doom-wide-v7r1.X1C`, SHA-256:

```text
ef2af25051599bb57ac712b1602ce017d0b59f2486ba1ad940ac2da40b8f3bbc
```

Main application: 176,788 bytes. Upper application: 150,944 bytes. Update content free: 3,275 bytes. Upper flash free: 12,896 bytes. Bootloader/settings/calibration bounds and unpacker rehearsal are unchanged.

## Native device result (2026-10-31)

The loader accepted the image, sent the reboot command, and exited **0**. The device completed the v5-compatible handshake and produced CRC-validated 160×90 captures. Captures before and after controls show the wider scene, weapon and complete HUD.

180 stationary starting-area frames (196–375), preview disabled and all inputs released:

| Metric | Prior 4:3 v6r1 | Wide v7r1 |
| --- | ---: | ---: |
| Median engine/render/LCD frame time | 135 ms | 158 ms |
| Reciprocal of median frame time | 7.41 fps | 6.33 fps |
| Host-observed throughput | 7.02 fps | 6.31 fps |
| 95th-percentile frame time | 163 ms | 188 ms |
| Median USB wait | 3 ms | 26 ms |
| Median asset requests | 2 | 19 |
| Median decoded pages | 837.5 | 713 |
| Median of each frame's time minus its USB wait | 131 ms | 131 ms |

The wider view is slower in these sequential samples. The equal median after subtracting recorded USB wait suggests the extra asset requests are a major remaining cost. This is an inference, not a CPU-only profile or a matched game-tic benchmark. The pinned asset selection still targets the earlier view; it has not been retuned for wide FOV.

All 20 short 10 ms Esc taps sent through local HTTP toggled the native menu. Forward, left/right, fire and use were acknowledged in applied-input telemetry and released. Rotation to 180° and back to 0° was acknowledged. The tests ended with menu closed, rotation 0°, remote input released and preview enabled. The user subsequently confirmed that the full scene and HUD display correctly, operation is normal and gameplay feels responsive. This is qualitative confirmation, not an additional FPS or endurance measurement. Automatic live-browser inspection could not run because the browser tool reported `browser.user is unavailable`; capture framing and BMP output were verified separately.

See [validation/wide-v7r1.json](validation/wide-v7r1.json). The prior v6r1 135 ms result belongs to the 4:3 build. Host output is a rendering/functional check, not an MCU benchmark.

Rebuild with `scripts/build.ps1 -Name <new-name>` and run `scripts/test.ps1`. The test suite builds `tests/wide-output.rs` as a host DLL and runs `tests/test-wide-engine.py`, saving actual mapper output under ignored `artifacts/`. `--host-test --classic-view` is available for projection comparisons; device builds always use the wide mapper/projection together.
