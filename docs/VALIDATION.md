# Validation record

Recorded on **2026-10-30 (Asia/Tokyo)**. One KOWSI KWS-X1 was used, showing Bootloader V1.1. This is a one-unit experiment, not a compatibility result for every hardware revision.

## Actual hardware

- The original HID loader was detected as VID `1105`, PID `000a`, mode `0`.
- v1 displayed the game map. The user confirmed the physical key assignments, including movement, turning, firing, and the button combinations.
- v2 installed, ran, and improved responsiveness; the user still observed substantial input-to-picture delay.
- v3r1 installed with final bootloader acceptance and flasher exit code **0**. The device enumerated its development CDC interface, completed the v3 handshake, and continued native game rendering and asset requests.
- The user confirmed a substantial further improvement with v3. This is qualitative feedback, not a measured performance comparison against the KM003C.

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

The clean reconstruction regenerated the exact E1M1 data and produced an X1C
byte-for-byte identical to the hardware-tested v3r1 image (210,498 bytes):

```text
a5c9056c9aca93aa8f1fece727f275637440fe391991d87a8e75aa1123392e71
```

This equality was observed with the recorded Windows toolchain. It is not a
promise of identical output from arbitrary compiler versions. The image itself
remains a local generated artifact rather than a committed firmware binary.

## Limits

- No independent complete application/upper-flash readback was performed.
- Stock V1.0.5V passed container validation; stock restoration and a complete flash recovery were not tested here.
- Clock frequencies are configured nominal values; oscillator accuracy was not measured.
- Sound, saves, map transitions, browser controls, PC preview, automatic gameplay reconnect, and long-duration stability are outside this baseline.
- The code preserves the defined flash bounds; that does not qualify electrical safety, USB compliance, or compatibility with other units.
