# Updating and recovery

This workflow was exercised on one KWS-X1 showing **Bootloader V1.1**. Keep a compatible original manufacturer X1C before changing the application. Manufacturer firmware, vendor update tools, calibration data, and device dumps are not published in this repository.

## What the image changes

| Flash range | Use |
| --- | --- |
| `[0x00000, 0x10000)` | Original bootloader; not written |
| `[0x10000, 0x44000)` | Application update erase envelope |
| `[0x44000, 0x6c000)` | Upper application code and pinned game pages; programmed by the first-boot unpacker |
| `[0x6c000, 0x80000)` | Outside this project's write ranges |

The bootloader writes only the application envelope. On first boot, the bundled unpacker verifies its streams, installs the upper region and main application, and resets. Application startup checks the installed upper-region hash before calling its code or reading its assets.

This is not a full-flash backup or an independent readback verification. Original calibration/settings were not acquired as a full dump. The reported flashing success means the bootloader accepted the image and the application subsequently ran.

## Validate before USB access

Build the tools/image as described in [BUILD.md](BUILD.md). In PowerShell:

```powershell
. .\scripts\env.ps1
$image = (Resolve-Path artifacts/kws-x1-doom.X1C).Path
$hash = (Get-FileHash -LiteralPath $image -Algorithm SHA256).Hash.ToLowerInvariant()
$flasher = '.\vendor\kws-x1-standalone-rs\target\x86_64-pc-windows-gnu\release\flasher.exe'
& $flasher --dry-run --image $image --confirm-sha256 $hash
```

`--dry-run` validates the exact bytes and erase bounds without discovering or opening a device. The build has already audited decompressed contents against its ELFs.

## Update the meter

Stop its PC controller or asset server, unplug the meter, then **hold Back + OK while connecting a data-capable USB cable**. Confirm the bootloader screen. An optional `--info` query opens USB and should report mode `0`.

To write the reviewed image and its exact hash:

```powershell
& $flasher --info
& $flasher --image $image --confirm-sha256 $hash
```

The flasher checks the supported HID identity and refuses ambiguous device selection. It writes checked batches, waits for final acceptance, and sends reboot only after acceptance. The upstream tool can retry a complete application pass after verification code 4. Do not disconnect during writing or first-boot unpacking.

Then start the v4 PC controller (it also supplies assets):

```powershell
.\scripts\play.ps1
```

For headless v4 play use `scripts/serve-game.py --auto --version 4`; older images need their corresponding version. Gameplay always requires asset delivery from one server. If gameplay stops after a USB loss, restart the server and power-cycle the meter. If the application does not start, re-enter the original loader with Back + OK rather than relying on the application USB interface. See [PC-CONTROLS.md](PC-CONTROLS.md) for controller setup.

## Going back to stock

The same flasher accepts compatible original X1C containers. Select your own stock file, compute its hash, run `--dry-run`, enter the loader, then use the same hash-confirmed update command with that file.

**Stock restoration has not been tested on this unit.** The locally retained V1.0.5V container passed structural validation only. The upstream project reports a stock-restoration test, but that is not this port's hardware verification. This project has no supported complete flash-dump/restore procedure, and it must not substitute another unit's private calibration or loader data.
