# Changelog

## Unreleased — standalone mini arena

- Add an original two-sector arena with two enemies, pistol/fist and small pickup/texture sets derived from Freedoom.
- Store the complete 144,320-byte pack in 112,095 compressed internal-flash bytes, with an 8 KiB decoded cache and per-page CRC validation.
- Start without USB initialization or a host handshake; retain physical controls and the original update-loader path.
- Isolate mini generated tables, board checkout, engine libraries and update images under `artifacts/mini/`.
- Verify real-engine gameplay and the exact internal-flash reader; power-only startup and physical controls confirmed on one unit. The user reported smooth gameplay; FPS was not measured.

## Unreleased — v5 enclosure preview and LCD rotation

- Inset the actual live preview into the user-supplied KWS-X1 enclosure photograph without changing the photograph or stretching the game image.
- Add 0/180-degree real LCD rotation, applied at a frame boundary with device acknowledgement, full clear/redraw, and the correct controller row offset.
- Provide upright-game and fixed-enclosure preview modes; keep input mappings and the saved logical bitmap unchanged.
- Add an enlarged live-preview dialog for inspecting menus; opening it releases PC input, and Close/Esc returns to controls.
- Discover v4/v5 separately and disable LCD rotation on v4; validate versioned control packets and bounded rotation values.

## Unreleased — v4 PC controls

- Local browser keyboard and pointer controls, with queued short presses, explicit release, focus-loss handling, and bounded input leases.
- Optional 120×90 real-device preview, throttled to one capture per second, with BMP download and a preview pause switch.
- A single CDC owner handles assets, controls, telemetry, and preview; v4 has its own discovery serial string.
- Offline protocol/controller tests and real-device API verification; English/Japanese setup documentation.
- Preserve input edges while the engine's tic-command buffer is full; a real-engine regression reproduces the lost short press before the fix and verifies player movement afterward.
- Record offline reduced-asset measurements and flash/installer constraints for a possible standalone variant; no standalone firmware is included.

## 2026-10-30 — Initial source publication

- Native HC32F460 DOOM/Freedoom E1M1 gameplay on the KWS-X1.
- v3r1 baseline: 180×135 LCD output, physical controls, 179 pinned asset pages, compressed USB CDC streaming, and two cache layers.
- About 5.6 fps in the recorded starting-area sample; hardware flashing and gameplay confirmed on one unit.
- Pinned source reconstruction, offline image audit, tests, English/Japanese READMEs, and recovery/validation notes.

PC keyboard controls and a PC video preview were not part of the v3r1 baseline.
