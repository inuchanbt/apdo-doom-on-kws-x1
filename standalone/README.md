# Standalone Mini DOOM — widescreen branch

**Experimental firmware: an interrupted or incompatible update can leave the meter unbootable; recovery and stock restoration are not verified or guaranteed.** Meter measurement/PD/QC functions are replaced, and electrical passthrough/protection behavior is unqualified. Leave downstream equipment disconnected. See [release downloads, full risks and vendor OTA instructions](../docs/FIRMWARE.md) ([日本語](../docs/FIRMWARE.ja.md)) before updating. Use at your own risk, without warranty.

This variant runs an original two-sector arena with Freedoom artwork entirely from the KWS-X1's internal application flash. It displays the original Freedoom startup logo for 1.2 seconds, then starts the game, samples the physical buttons independently, and does not initialize USB or wait for a host. USB is needed only as a power source during play. The original Back+OK update loader remains available.

Development branch: `codex/standalone-widescreen`, based on standalone commit `546d560` and importing shared engine/display changes from the verified PC-wide checkpoint `fe61b00`. **Mini-wide v3 is installed through the manufacturer OTA tool and user-confirmed: startup logo, power-only reconnection, full-width display/HUD and local controls.** Its full 240×135 output keeps natural proportions, about 106° horizontal FOV and a HUD distributed across the bottom.

The earlier 4:3 mini image on `codex/standalone-mini-doom` installed with clean final loader acceptance and flasher exit 0 after one complete retry. The user confirmed power-only startup and physical controls on one Bootloader V1.1 unit, and reported very smooth gameplay. That feedback belongs to the earlier image, not a numeric benchmark of this wide build.

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

The unchanged pack is **144,320 bytes**, stored as **112,095 bytes** in 141 independent 1 KiB LZ4 pages, plus offsets/CRCs. Every page is internal; there is no fallback request to a PC. An 8 KiB decoded LRU cache serves arbitrary engine reads, with a 4 KiB short-record cache in the engine. Decode/CRC bounds are checked.

The full-width display uses 32,400 palette indices and a 512-byte RGB565 palette. Four rows are expanded per LCD DMA transfer. World, enemy, weapon, menu and HUD artwork retain their palette colors; horizontal projection, sprite scales and floor stepping compensate for the wide LCD. Menus retain their proportions in the middle, while complete HUD groups are spaced across the bottom. The C engine and firmware package use speed optimization; the power-only startup and local buttons stay separate from the PC adapters.

### Wide v3 image with startup logo

The release image `kws-x1-mini-wide-v3.X1C` adds the original Freedoom Phase 1 logo for 1.2 seconds before starting the game. Its 216×50 render uses the existing indexed frame and a 6,021-byte internal logo asset; no additional framebuffer or gameplay-loop work is added. SHA-256:

```text
acc8b85c2ec24a51b43a9348eac16ab68fda019c512fb74537a577dc15285d4f
```

Main application: **150,844 bytes**. Upper application: **140,176 bytes**, with **23,664 bytes free**. Update content free: **26,055 bytes**. The game asset pack, protected flash ranges and no-USB startup remain unchanged. The exact image passed decompression/layout audit and dry-run, then the manufacturer's **KWS-X1 OTA Tool V1.0** displayed `Upgrade successful!` and `KWS-X1:Write completed.Restart!` over a direct PC USB connection. The asset server was stopped before updating. The user confirmed the logo, full-width game/HUD and local controls, including a power-only reconnection. See [vendor OTA evidence](../docs/validation/vendor-ota-banner.json).

### Earlier wide v2 image

`artifacts/mini/kws-x1-mini-wide-v2.X1C` passed full decompression/layout audit and flasher dry-run. SHA-256:

```text
e8352e4d4a0ceca482cff35fbbff179a469591ed151c0f29dbc98b10b5ddb7f7
```

Main application: **143,692 bytes**. Upper application: **140,176 bytes**, with **23,664 bytes free**. Update content free: **28,610 bytes**. SRAM2 uses **32,912 / 65,536 bytes**; the linked ordinary-RAM stack reservation is **34,184 bytes**. These are linked size budgets, not measured runtime stack headroom. The audit's IRQ list is exactly `[31,38,39,86,87,88]`, without a USB IRQ. Protected flash bounds are unchanged.

The image subsequently installed on the Bootloader V1.1 unit with final loader acceptance, reboot command and flasher exit **0**. The PC asset/controller server was stopped before installation; no KWS-X1 DOOM CDC port appeared after the update. The user then confirmed power-only startup, complete full-width display/HUD, physical controls and smooth gameplay. See the [mini-wide v2 validation record](../docs/validation/mini-wide-v2.json).

### Earlier 4:3 image

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

The wide engine ran 198 functional-test frames, consumed pistol ammo, killed both enemies, moved/turned the player, opened/closed the menu, and reproduced both canonical and indexed full-width HUD output after a clear/redraw. The actual production LCD mapper is attached to the engine's palette/column callbacks during the test, and its 240×135 captures show both LCD edges and intact HUD/menu output. Measured host projection FOV is 106.259765625°. These are functional checks, not MCU FPS measurements.

The actual standalone asset reader matches the full pack and 600 randomized crossing/eviction reads without any USB implementation. All eight mini reader/codec/control tests pass. The shared PC suite also passes: 15 Python controller tests, 16 Rust optimization/mapper tests, real engine/cadence/short-input tests, all 2,737 PC-pack codec pages and nine container regressions.

Physical power-only startup, full-width display/HUD and controls of **wide v3 are user-confirmed**, after a direct-PC vendor OTA update. This is qualitative feedback: FPS and runtime stack margin are not instrumented, and sustained stability has not been tested. The original loader and reserved manufacturer data are not acquired as a complete flash backup.

For the earlier 4:3 image, the PC asset/controller server was stopped before installation, and no DOOM CDC interface appeared after the update, as expected. See [the earlier validation record](../docs/validation/mini-v1.json).
