# Changelog

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
