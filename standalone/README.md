# Standalone Mini DOOM — experimental branch

This variant runs an original two-sector arena with Freedoom artwork entirely from the KWS-X1's internal application flash. It starts directly into the game, samples the physical buttons independently, and does not initialize USB or wait for a host. USB is needed only as a power source during play. The original Back+OK update loader remains available.

Development branch: `codex/standalone-mini-doom`, based on the verified PC-linked v5 commit `79c28bf364c7cdac4a5630e5266672fbec20b4ac`. The first image installed with clean final loader acceptance and flasher exit 0 after one complete retry. The user confirmed power-only startup and physical controls on one Bootloader V1.1 unit, and reported very smooth gameplay. This is separate from the PC-linked E1M1 build.

## What is in the first arena

- Two connected rectangular sectors with different ceilings and lighting.
- Pistol/fist, two zombieman enemies, an ammo pickup, and a stimpack.
- Movement, turning, shooting, enemy AI/death, normal HUD, and the game menu.
- One wall texture family and a small floor/ceiling set; half-size wall/sprite artwork, one viewing direction per sprite frame, and a reused neutral HUD face.
- No exit or map progression, sound, save files, USB streaming, Web controls/preview, or runtime LCD rotation in this initial variant. Restart by power-cycling or through the game menu.

The map-only `mini-arena.wad` is original geometry. Artwork comes from the hash-verified Freedoom 0.13.0 release and retains its BSD license/credits in `../notices/freedoom-0.13.0/`. Generated WADs, converted packs, compressed blobs and binaries stay in ignored `artifacts/mini/`.

## Build

Prepare the pinned sources/tools using [BUILD.md](../docs/BUILD.md), then:

```powershell
.\scripts\build-mini.ps1 -Name kws-x1-mini
```

To use a locally cached, verified Freedoom release:

```powershell
.\scripts\build-mini.ps1 -Name kws-x1-mini -FreedoomZip C:\Downloads\freedoom-0.13.0.zip
```

The default converter reconstructs its upstream table cache from the pinned sources; `-UpstreamCache` is an optional development shortcut. Converted/compressed hashes are checked against [ASSET_LOCK.json](ASSET_LOCK.json).

The workflow creates a separate pinned board checkout at `artifacts/mini/board`, stages the mini adapters there, generates separate C tables in `artifacts/mini/gen`, and places engine libraries/tests/images under `artifacts/mini/`. The normal PC board checkout, E1M1 pack and generated tables remain available for the existing build workflow.

Before creating an X1C, the script runs the real host engine, tests the actual Rust internal-flash reader against every byte of the pack and 600 cross-page/eviction reads, and compiles the native ARM firmware. Packaging then audits the exact decompression output, vector table and erase bounds, and runs a flasher dry-run. It does not open a USB device. Updating uses the separate hash-confirmed procedure in [RECOVERY.md](../docs/RECOVERY.md), with the mini X1C path substituted.

## Storage and runtime

The first pack is **144,320 bytes**, stored as **112,095 bytes** in 141 independent 1 KiB LZ4 pages, plus offsets/CRCs. Every page is internal; there is no fallback request to a PC. An 8 KiB decoded LRU cache serves arbitrary engine reads. Decode/CRC bounds are checked. The 180×135 framebuffer and black sidebars use the same display path as the PC port.

The first audited image (`kws-x1-mini-v1r1.X1C`) installs 83,812 main-region bytes and 147,680 upper-region bytes, leaving 16,160 upper-region bytes free. Its compressed update contents leave 47,183 unused bytes inside the fixed container. The asset and installation budgets both fit; no protected flash range was expanded. Image SHA-256:

```text
f6a0ae64f398cb81f9dde2931c974fbe33d88fc2f85ee37ef50052cce57dc23b
```

Mini firmware uses the same protected bootloader/application/upper-region bounds and first-boot unpacker. Its expected custom IRQ set omits the USB IRQ and explicitly contains only `[31,38,39,86,87,88]`; the packer checks that set rather than relaxing vector validation.

## Controls

| Action | Meter buttons |
| --- | --- |
| Forward | OK |
| Turn | Left / Right |
| Fire | Back |
| Use | Left + Right |
| Game menu | OK + Back |
| Menu up / down | Left / Right |
| Menu confirm / back | OK / Back |
| Original update loader | Hold Back + OK while connecting power |

## Offline evidence and limits

The real engine ran 198 functional-test frames, consumed pistol ammo, killed both enemies, moved/turned the player, opened/closed the menu, and reproduced the complete HUD after a clear/redraw. The actual standalone asset reader matches the full pack and randomized crossing/eviction reads without any USB implementation. The normal PC test suite also passes after the shared build-helper changes.

Physical power-only startup and controls were subsequently confirmed by the user. FPS and runtime stack margin were not instrumented, and sustained stability was not tested. The original loader and reserved manufacturer data are not acquired as a complete flash backup.

The PC asset/controller server was stopped before installation, and no DOOM CDC interface appeared after the update, as expected for this firmware. See [the curated validation record](../docs/validation/mini-v1.json).
