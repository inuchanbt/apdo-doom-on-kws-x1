# Validation record

Recorded on **2026-10-30 (Asia/Tokyo)**. One KOWSI KWS-X1 was used, showing Bootloader V1.1. This is a one-unit experiment, not a compatibility result for every hardware revision.

## Actual hardware

- The original HID loader was detected as VID `1105`, PID `000a`, mode `0`.
- v1 displayed the game map. The user confirmed the physical key assignments, including movement, turning, firing, and the button combinations.
- v2 installed, ran, and improved responsiveness; the user still observed substantial input-to-picture delay.
- v3r1 installed with final bootloader acceptance and flasher exit code **0**. The device enumerated its development CDC interface, completed the v3 handshake, and continued native game rendering and asset requests.
- The user confirmed a substantial further improvement with v3. This is qualitative feedback, not a measured performance comparison against the KM003C.
- v4 installed with final bootloader acceptance and flasher exit code **0**, enumerated as `KWSX1DOOM04`, and ran the asset/control/preview exchange on the real meter. See the v4 record below.

v1's flashing process reported code 4 and retried; its final completion log was not captured and the command exited 1. Its subsequent display/controls were confirmed. v2 and v3 have separate recorded clean update completions.

## Starting-area measurements

| Metric | v2 | v3r1 |
| --- | ---: | ---: |
| Frames retained after startup exclusion | 177 | 383 |
| Median frame time | 1,174 ms | 180 ms |
| 1,000 / median frame time | 0.85 fps | 5.56 fps |
| Median USB wait per frame | 669 ms | 4 ms |
| Minimum untouched stack observed | — | 15,308 bytes |

The first five frames were excluded. The v3 sample is frames 6–388. The ratio of median frame times is about 6.52. These samples describe the initial area; movement into uncached scenes changes timing. The FPS value is the reciprocal of median frame time, not an average of individual FPS values. Frame reports measure engine/render/LCD time; the small report-transfer and scheduler gap is outside that measurement.

Curated, non-identifying summaries are included in [validation/v2-starting-area.json](validation/v2-starting-area.json) and [validation/v3-starting-area.json](validation/v3-starting-area.json). Raw per-frame logs, USB paths, generated images, update logs, and machine-local details remain under ignored `artifacts/` and `local/`.

## Offline checks

- Real C engine and real E1M1 pack: 140 frames, changing scene output, movement, turning, firing, menu actions, and complete HUD redraw.
- Protocol: pinned pack hash, request bounds, sequence/address/length fields, CRC32, EOF padding, fragmented reads, truncated input, and telemetry formats.
- Compression: all **2,737** padded asset pages encoded by Python and decoded byte-for-byte with the firmware's Rust LZ4 decoder; invalid streams rejected.
- Cache: mixed-size allocation without overlapping cells or crossing banks, LRU eviction, and actual engine-read replay.
- Access replay: v1's 8 KiB FIFO averaged about 917 requests and 939 KB per frame; v2's compressed cache about 493 and 349 KB; adding pinned pages about 4 and 3.5 KB. This replay is not hardware FPS measurement.
- Image packaging: nine container/packer regressions, plus full decompression audit and flasher dry-run for the actual update image.
- The published build workflow is also checked from a separately reconstructed source tree; the current running meter is not reflashed for publication checks.

The clean reconstruction of the published v3r1 baseline (commit `747899b96839c72242649d99fbf673d107801dbe`) regenerated the exact E1M1 data and produced an X1C
byte-for-byte identical to the hardware-tested v3r1 image (210,498 bytes):

```text
a5c9056c9aca93aa8f1fece727f275637440fe391991d87a8e75aa1123392e71
```

This equality was observed with the recorded Windows toolchain. It is not a
promise of identical output from arbitrary compiler versions. The image itself
remains a local generated artifact rather than a committed firmware binary.

## v4 PC controls and preview

The hardware-installed v4 image passed a full decompression/erase-layout audit and flasher dry-run before installation. Its SHA-256 is:

```text
3383cdc89ecc4aff96f3b579883d49d477f49fcc63ea88491ad8f3143e1deb5e
```

On real hardware, local HTTP requests were traced to native input/menu telemetry:

- A short Esc press/release opened and closed the menu.
- Forward, backward, right turn, and fire reached the combined engine input; explicit release returned it to zero.
- A held left turn released after browser-heartbeat silence.
- Preview OFF stopped new captures while native frames continued; ON resumed captures. A 120×90 BMP was retrieved and its scene/HUD visually inspected.
- Untouched stack space remained at least 15,004 bytes in this functional test. This is a short test, not a worst-case stack bound.

The browser controller reported about 5.2 native fps and 0.9 preview fps in an initial stationary observation. Later movement changed the scene and rate. These are functional observations, not a matched v3/v4 benchmark. The controller's Meter FPS includes preview/control transfer pauses; the per-frame engine time does not.

All 10 Python PC-controller tests and 11 Rust optimization tests (including four new control/preview tests) passed. The controller tests use fake USB and local HTTP; actual USB behavior was separately checked as above. Curated evidence is in [validation/pc-v4.json](validation/pc-v4.json), with raw logs and BMPs retained in ignored `artifacts/`.

The user confirmed basic browser preview/keyboard operation, while reporting intermittent lost short presses. A real-engine regression reproduced a queued press being consumed by an input poll with a full five-command tic buffer. The adapter now uses upstream's `D_WillBuildTic` check to preserve queued edges until a command can be built; the regression passes and verifies real player movement.

The v4r1 follow-up image passed full decompression/erase-layout audit and flasher dry-run. SHA-256:

```text
59380db785fe136916211e6561243db434763eaf01fa21115d634af7cfe874a7
```

v4r1 installed with final bootloader acceptance and flasher exit **0**, and reconnected to the existing controller. All **20/20** 10 ms Esc taps sent through local HTTP toggled the native menu; the observed command-to-menu-telemetry delays were 234–406 ms. The test ended with menu closed and remote/applied masks zero. Preview capture also succeeded. This checks API-to-device delivery, not browser event timing, and is not a performance benchmark. The user then manually confirmed that browser short presses were stable. See [validation/pc-v4r1.json](validation/pc-v4r1.json).

Automatic browser visual/input checking stopped because the Windows computer-use tool could not determine the active browser URL with sufficient confidence. Browser focus-loss behavior remains unconfirmed. See [PC-CONTROLS.md](PC-CONTROLS.md).

## v5 enclosure preview and LCD rotation

The v5 candidate passed the complete offline suite: the real host engine/HUD and full-tic-buffer short-press regression, 14 Python controller tests, 12 Rust optimization/control/preview tests, all-page codec checks, and nine image/container regressions. The built image passed the full decompression/erase-layout audit and flasher dry-run. SHA-256:

```text
037f4d2a481e7723d94b434c0913bb1d682bd16b655f562f676722ebf3536298
```

The source adds versioned rotation commands, applied-angle telemetry, correct panel row offsets for both orientations, and a complete clear/HUD redraw at rotation boundaries. The browser uses the supplied enclosure photograph unchanged and preserves the preview aspect ratio. Its layout was visually checked in the in-app browser using a saved real-device frame in an explicitly labelled offline fixture. The normal desktop view and 390-pixel breakpoint were checked; the narrow document width was 375 pixels, with no horizontal overflow. The temporary viewport override was reset afterward.

The installed device subsequently booted v5, completed its versioned handshake, and streamed the game and previews. Both 180° and return-to-0° commands were exercised through the real browser, including acknowledgement from native telemetry. The user confirmed normal physical rotation and complete screen/HUD output. Upright-game and fixed-enclosure presentation modes were visually checked. PC Esc opened/closed the native game menu, and the enlarged-preview dialog showed the live menu and closed with Esc while PC input was disabled. The test ended at 0° with menu closed and remote input released. The local server was restarted as a hidden background process at the same URL.

Unlike the clean v3/v4 updates, this v5 flasher process ended with Windows access violation `0xC0000005` (signed exit `-1073741819`) during final completion. All 26 batch checksums were accepted, but the final acceptance/reboot log was not captured. The later v5 boot, image-matching upper-region startup check, gameplay, rotation, and user confirmation establish subsequent application operation; this is not recorded as a clean flasher exit or an independent flash readback. See [validation/pc-v5.json](validation/pc-v5.json).

## Limits

- No independent complete application/upper-flash readback was performed.
- Stock V1.0.5V passed container validation; stock restoration and a complete flash recovery were not tested here.
- Clock frequencies are configured nominal values; oscillator accuracy was not measured.
- Sound, saves, map transitions, automatic gameplay reconnect, and long-duration stability remain outside the verified scope.
- The code preserves the defined flash bounds; that does not qualify electrical safety, USB compliance, or compatibility with other units.
