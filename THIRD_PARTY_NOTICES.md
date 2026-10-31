# Third-party notices and license scope

The existing root [LICENSE](LICENSE) is MIT. It applies to documentation, project metadata, and other original material without a more specific notice. It does **not** replace the licenses below. Source adapters, tests, and scripts marked `GPL-2.0-or-later` retain that license; [COPYING](COPYING) provides the GPL text. The linked firmware contains GPL engine code.

| Material | Source / scope | Terms |
| --- | --- | --- |
| KWS-X1 board implementation | [kralonur/kws-x1-standalone-rs](https://github.com/kralonur/kws-x1-standalone-rs): panel, DMA, startup reference, container, unpacker, flasher | MIT OR Apache-2.0; copies in `notices/kws-x1-*` |
| KM003C integration | [inuchanbt/apdo-doom-on-km003c](https://github.com/inuchanbt/apdo-doom-on-km003c): C engine bridge, harness, converter patch, USB bring-up adaptation, and browser keyboard/pointer flow | C integration is GPL-2.0-or-later; `web/` is marked MIT; original project MIT notice retained in `notices/km003c-project-MIT.txt` |
| USB bring-up lineage | [okhsunrog/km003c-firmware](https://github.com/okhsunrog/km003c-firmware), through the APDO integration | Upstream MIT terms continue to apply; `overlays/firmware/usb.rs` is marked MIT |
| Low-memory engine/converter | [ArturBieniek4/DMC100-Doom](https://github.com/ArturBieniek4/DMC100-Doom) | GPL-2.0-or-later; retain upstream per-file notices and licenses in reconstructed source |
| Engine lineage | [ozkl/doomgeneric](https://github.com/ozkl/doomgeneric), id Software | GPL-2.0; retain upstream notices |
| Game assets | [Freedoom 0.13.0](https://freedoom.github.io/), including `overlays/firmware/game_pages.bin` | Freedoom's BSD license and credits in `notices/freedoom-0.13.0/` |

`game_pages.bin` is a compressed subset of the hash-verified converted Freedoom E1M1 pack. Its generated lookup table is `pinned_assets.rs`; its source and hashes are recorded in `SOURCE_LOCK.json`. It is game data, not manufacturer firmware. No commercial DOOM IWAD is included.

`overlays/firmware/freedoom-banner.bin` contains the original Freedoom 0.13.0 Phase 1 `M_DOOM` menu logo, flattened onto black and stored as an exact RGB565 palette with indices. Its BSD license and credits are in `notices/freedoom-0.13.0/`; extraction provenance and hashes are in the adjacent JSON. `scripts/extract-splash.py`, adapted from this project's KM003C independent firmware, reproduces it from the hash-verified official archive. The logo does not imply endorsement by Freedoom or its contributors.

The HC32 HAL/PAC, Embassy, and other Rust dependencies keep their own upstream terms. `locks/board.Cargo.lock` fixes dependency revisions. Dependency source remains in ignored local checkouts rather than being relicensed by this project. A complete redistribution must preserve the corresponding upstream notices and satisfy the terms of the combined firmware.

Manufacturer X1C files, vendor update executables, bootloader dumps, calibration data and recovery backups are not redistributed. Compiled experimental game firmware is provided separately as GitHub Release assets, with checksums, license notices and corresponding source. Binary releases retain the GPL terms of the linked engine and the original terms of the other components; the root MIT license does not relicense the combined firmware.

`web/assets/kws-x1-shell.png` is the enclosure photograph supplied by the user as `KOWSI_KWS-X1.png`, copied without image edits. Its original rights remain with its rights holder; the project's source-code MIT/GPL notices do not relicense this photograph.
