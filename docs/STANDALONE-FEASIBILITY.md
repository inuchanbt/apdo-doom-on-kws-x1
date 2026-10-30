# Standalone feasibility ｡ｪ KWS-X1

Measured 2026-10-30 against the current v4r1 engine and pinned Freedoom 0.13.0 E1M1. This is a size study; no source firmware, installed image, or running USB server was changed.

## Flash budget

The current linker permits 209,916 main-region bytes plus 163,840 upper-region bytes: 373,756 bytes total. v4r1 uses 105,920 + 158,480 bytes, including 122,863 bytes of pinned compressed assets. Subtracting those assets leaves approximately 141,537 bytes for code/metadata, and a theoretical asset budget of 232,219 bytes after relocation. Indexes, alignment, decoder changes and code removal/addition change this budget. Reserved bootloader/calibration/settings regions are excluded.

There is also an independent installer constraint: the currently audited v4r1 update has only 26,392 unused content bytes. Filling runtime flash therefore requires revisiting packaging/installation as well as the linker.

## Offline conversion measurements

| Candidate | Converted bytes | Whole-file LZMA bytes |
| --- | ---: | ---: |
| Current E1M1 | 2,802,000 | 757,832 |
| Half wall dimensions, fewer mips, half-width sprites, half-height monster sprites, reduced UI | 992,304 | 320,444 |
| Quarter wall dimensions, same reduced sprites/UI | 759,856 | 267,624 |

These LZMA values use Python preset 9 on the whole file and are optimistic comparison figures, not an MCU-compatible random-access storage design. The current independently decoded 1 KiB LZ4 pages total 2,038,612 bytes for the unmodified pack. A new codec needs bounded decode RAM and random-read performance; decompressing the entire game into RAM is not viable with the current engine allocation. Reduced candidates were converted in memory and measured, not rendered or verified in-game.

The current pack already contains just E1M1 and selects required map assets. Its dominant sections are wall texture data (1,641,856 bytes) and sprite/UI patch data (955,968 bytes). Geometry/other map streams occupy 120,592 bytes. Sounds occupy only 5,527 bytes, and demos only four bytes, so deleting sound/demo data alone cannot solve the gap.

## Assessment

An unchanged E1M1 pack does not fit through compression alone. A heavily reduced full E1M1 remains an unproven research target. A dedicated small map with few texture families, a limited enemy/weapon roster, reduced sprite directions/frames, and simplified HUD/UI is the more credible first standalone target. Target a compressed asset package around 100ｨC150 KiB for an initial experiment, then validate the actual runtime/installer budgets and a bounded random-access decoder. This is a design target, not a demonstrated build size.

Keep the existing PC-linked E1M1 build available while developing a separate standalone variant. External memory has not been confirmed on this unit; this study assumes only the currently permitted internal flash regions.
