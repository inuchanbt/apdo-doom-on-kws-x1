# Firmware downloads, risks and vendor OTA update

[English](FIRMWARE.md) · [日本語](FIRMWARE.ja.md)

These are experimental, unofficial game firmwares for **KOWSI KWS-X1**, tested on **one device with Bootloader V1.1**. They replace the meter application. Read the risks before downloading or updating.

## Choose a firmware

| Release | Image | During play |
| --- | --- | --- |
| [PC-connected wide E1M1 v7r2](https://github.com/inuchanbt/apdo-doom-on-kws-x1/releases/tag/pc-wide-v7r2) | `kws-x1-doom-wide-v7r2.X1C` | A data-capable USB connection and the PC asset/controller server must remain running. |
| [Standalone wide mini v3](https://github.com/inuchanbt/apdo-doom-on-kws-x1/releases/tag/standalone-wide-v3) | `kws-x1-mini-wide-v3.X1C` | Power only; assets are internal. Small custom arena with two enemies, no Web controls. |

Both use the full 240×135 LCD with natural proportions and approximately 106° horizontal FOV. Neither includes sound, saves or supported map progression. Releases are marked **prerelease** because testing is limited to one unit.

Both show the original Freedoom Phase 1 logo, centered at 216×50, for at least 1.2 seconds on startup. The PC version keeps it visible while waiting for the server. Logo pixels are stored internally and require no additional framebuffer or work during gameplay.

## Risks and limits

- **The device can become unbootable.** A wrong image, incompatible hardware/loader, interrupted update, USB failure or first-boot flash error can leave it unable to start. Keeping the loader outside the intended write ranges does not guarantee recovery; hardware programming or repair may be needed.
- **Stock recovery is not verified here.** Keep the correct original manufacturer firmware for your exact unit before updating. No complete bootloader/calibration/settings backup was acquired; preserving address ranges is not proof that these data can be restored. Do not copy another unit's private calibration or bootloader dump.
- **It stops being a working power meter.** Measurement, PD/QC control and the stock application's protections are not provided by these game firmwares. Electrical behavior, passthrough and compatibility with loads/chargers are not qualified. During this experiment use only the required power/data connection and leave other ports and downstream equipment disconnected. Damage to the meter, connected devices, chargers or cables is possible.
- **Gameplay can stop.** The PC version stops if asset delivery/USB is lost and needs its server restarted and the meter power-cycled. The standalone version needs no PC, but hangs, visual faults and long-duration failures remain possible in either version. A successful update is not a stability or electrical safety certification.
- **Use is at your own risk, without warranty.** This is not manufacturer-approved firmware. It may affect warranty/support eligibility. Testing on one Bootloader V1.1 unit does not establish compatibility with other revisions or similarly named meters.

## Download and verify

Download the selected `.X1C`, its release's `SHA256SUMS`, the English/Japanese instructions, license notices and `corresponding-source.zip`. PC users also need `pc-runtime.zip`; it includes the matching E1M1 pack and Python controller, without a compiler requirement. Install Python 3.12 and run `python -m pip install -r requirements.txt`, then `./scripts/play.ps1` from its extracted folder.

Use PowerShell to check the image against the entry in the release's `SHA256SUMS`:

```powershell
Get-FileHash -LiteralPath .\kws-x1-doom-wide-v7r2.X1C -Algorithm SHA256
# For standalone, substitute kws-x1-mini-wide-v3.X1C.
```

Checksums detect changed downloads; they do not prove that a firmware is safe or compatible.

## Update with the manufacturer's Windows OTA tool

Use your own copy of **`KWS-X1 OTA 英文版.exe`**, whose window title is **KWS-X1 OTA Tool V1.0**. The manufacturer executable and stock firmware are not redistributed here. A supplied filename is not proof of authenticity; obtain them from a source you trust.

1. Stop the game controller/asset server and other USB tools. Connect only one KWS-X1.
2. Unplug the meter, hold **Back + OK**, and reconnect it **directly to the PC**, using a data-capable USB cable without a hub. Check that its screen says **Bootloader V1.1**. A hub-connected attempt failed final verification during this release's test; the same PC image subsequently succeeded after the user changed to a direct connection. This does not isolate the hub as the sole cause or guarantee every direct connection.
3. Open the OTA tool. Wait for `Connected to KWS-X1!` and `KWS-X1:Entered OTA mode!`.
4. Click the left **Browse** button (this English tool still labels it `浏览文件`), and select the exact verified `.X1C`. Check the filename and file size before continuing.
5. Click the right **Send** button (`发送文件`). Keep the cable and power connected throughout writing **and the first boot**, which installs the upper application region. Wait for final `Upgrade successful!` and `KWS-X1:Write completed.Restart!`, then close the success dialog. Do not treat a stalled progress bar or a partial transfer as success.
6. PC version: start `./scripts/play.ps1` and keep it running while playing. Standalone: wait for the game screen, then a power-only connection is sufficient.

If a timeout or verification error remains without a final success message, do not assume completion. Save the log, wait until the tool has stopped sending, and recover through the original loader using a compatible image. There is no guaranteed recovery procedure. See [RECOVERY.md](RECOVERY.md) for flash layout and the alternative hash-confirmed developer flasher.

## Exact tested images and source

Both exact images below were installed with **KWS-X1 OTA Tool V1.0** through a direct PC connection on one Bootloader V1.1 unit. The tool showed `Upgrade successful!` and `KWS-X1:Write completed.Restart!` for both. The user confirmed the PC logo/full-width display/local and PC controls, and the standalone logo/game/local controls after a power-only reconnection. See the [OTA evidence](validation/vendor-ota-banner.json). This is not stock-restoration, endurance or independent full flash-readback verification.

| Image | SHA-256 |
| --- | --- |
| PC wide v7r2 | `dd8fb79765193f8ae55286d20730f6b2e936b994141f9ba7efabc0464ad67c18` |
| Standalone wide v3 | `acc8b85c2ec24a51b43a9348eac16ab68fda019c512fb74537a577dc15285d4f` |

The release's `corresponding-source.zip` supplies the tagged project source, prepared board/engine sources, pinned doomgeneric source, generated inputs and dependency source with their notices. See [BUILD.md](BUILD.md), [standalone instructions](https://github.com/inuchanbt/apdo-doom-on-kws-x1/tree/standalone-wide-v3/standalone/README.md), [third-party notices](../THIRD_PARTY_NOTICES.md) and the included GPL text. Do not substitute commercial DOOM assets when redistributing these images.
