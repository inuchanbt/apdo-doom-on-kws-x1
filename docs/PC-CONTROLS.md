# PC controls and preview (v4)

v4 runs game logic and rendering on the KWS-X1. The PC supplies the pinned game pack, forwards input, and optionally displays a reduced capture of the device framebuffer. This is a local browser controller backed by a Python server.

## Start and play

1. Follow [BUILD.md](BUILD.md) to prepare sources/data and build v4. Follow [RECOVERY.md](RECOVERY.md) to install it. Building alone does not update the device.
2. Stop any existing asset server: only one program can own the meter's COM port.
3. Run `./scripts/play.ps1` from PowerShell. Keep it running while playing. The browser opens the printed `http://127.0.0.1:<port>/` URL.
4. Wait for **KWS-X1 connected**, then click **Enable keyboard**.

Use W/S or Up/Down for forward/backward, A/D or Left/Right for turning, Space/Ctrl to fire, E to use, Esc for the menu, and Enter to confirm. Menu navigation uses Up/Down. Screen buttons can be held with a mouse or touch; the physical meter buttons remain available.

**Release all** clears PC input while keeping the game assets flowing. Changing tabs/windows, hiding the page, and leaving the page also release PC input and disable keyboard capture. Click **Enable keyboard** again to resume. Browser delivery can be interrupted, so the server and firmware additionally expire stale input. A release takes effect when the game next reads input.

**Live preview** requests a 120×90 RGB565 capture at most once per second. The meter renders its own 180×135 LCD view at an independent rate. Preview transfer blocks the next native frame briefly; disable it to prioritize local play. **Save frame** downloads the latest capture as a BMP. Pausing preview keeps the last image available. The page's Meter FPS uses frame-counter progress over wall time, including preview/control pauses; engine milliseconds exclude those pauses.

Optional PowerShell arguments:

```powershell
.\scripts\play.ps1 -NoBrowser -Port 8080 -UsbPort COM6
```

Omit `-UsbPort` for automatic discovery, and omit `-Port` for a free local HTTP port. Automatic discovery requires VID `c0de`, PID `d00d`, and serial `KWSX1DOOM04`; v1–v3 have a different serial string. This development USB identity is not a production allocation. Explicit COM selection must point to the installed v4 application, not its HID bootloader.

The Python entry point also accepts `--stats` and `--session-file`; see `scripts/pc-controller.py --help`. Its default log is `artifacts/runtime-v4.jsonl`. The headless alternative is `scripts/serve-game.py --auto --version 4`, which clears remote input and requests no previews.

## Stop and reconnect

**Stop server**, Ctrl+C, or closing the server also stops asset delivery. The controller tries to send a final clear at a frame boundary, and the firmware's input lease still expires independently. Asset requests cannot succeed after the server stops, so gameplay will stop too.

Restart the server and power-cycle the meter to resume after USB loss or server shutdown. The server waits/retries discovery, but the firmware does not resume an existing game after a failed USB transfer. Input state is cleared on a new connection, and the page requires keyboard capture to be enabled again. If another program already owns the COM port, close it first.

## Input lifetime and local HTTP

- The page sends input heartbeats every 100 ms while keyboard capture is enabled. It sends ordered state changes, so a quick press/release can survive between native frames.
- The server keeps at most 32 pending changes, sends at most eight per native frame, and clears input after 500 ms without an update. Old queued changes are discarded. Explicit release discards pending presses immediately.
- The firmware has a 16-state bounded queue and a 750 ms lease with the supplied server. Expiry is checked by the 5 ms input task as well as when input is read. Overflow clears input. Physical input is combined with remote input.
- HTTP listens only on `127.0.0.1`. Mutating requests require the exact Host, same Origin, and a random per-process token. The server serves only the three controller files and its named API routes; it does not expose the workspace. A controller page in another tab shares input state, so use one active control page.

These measures prevent indefinitely held remote keys; they do not make rendering faster or guarantee sub-frame input latency. Slow scenes and preview transfers still affect responsiveness.

## CDC protocol

All integers are unsigned little-endian unless specified. One serial worker owns all USB reads/writes. Asset requests retain v3's bounded `GET2` compressed-page exchange with the pack hash, response length, sequence/address, and CRC validation.

The 16-byte greeting is `X1DOOM04`, the 32-bit pack size, then IEEE CRC32 of the preceding 12 bytes. The host sends the matching greeting; no game starts with an unmatched size/version/CRC.

At each completed LCD frame, the meter sends:

| Packet | Layout |
| --- | --- |
| `FRM4` (48 bytes) | Magic + 11 u32 values: frame number, engine/render/LCD ms, physical button state, asset misses, USB wait ms, untouched stack bytes, decoded pages, remote input applied, combined engine input applied, menu active, preview byte count |
| `CTL4` (36 bytes, host response) | Magic, frame echo u32, held mask u32, lease ms u32, flags u32, event count u32, eight one-byte state masks, CRC32 of the first 32 bytes |
| `IMG4` (24-byte header, only when requested) | Magic, frame echo u32, width u32, height u32, payload length u32, payload CRC32; followed by 21,600 bytes of top-down RGB565 little-endian pixels |

`CTL4` masks use Fire=1, Forward=2, TurnLeft=4, TurnRight=8, Use=16, Menu=32, Confirm=64, Backward=128. Flags are Preview=1 and Clear=2; other flags are rejected. Count must be 0–8, held mask 0–255, and lease 100–1000 ms. Clear discards queued/held input. Each event is an ordered complete input state, not a key number. Frame echo and CRC are checked before applying input.

`IMG4` must be exactly 120×90/21,600 bytes. The host validates dimensions, frame echo, and pixel CRC before publishing it. The firmware leaves the main game task at its frame handoff until the transfer finishes. It samples the frozen framebuffer twice in 64-byte chunks (CRC, then payload), allocating no second framebuffer. The source's LCD wire byte order is converted to RGB565 little-endian for the PC.

## Verification

On one Bootloader V1.1 KWS-X1, v4 installed with flasher exit 0. Direct local HTTP requests were followed through USB to native telemetry: short Esc taps changed menu state; forward/backward/turn/fire masks reached the engine and released; heartbeat silence released held input; preview pause/resume and a CRC-validated BMP capture passed. The captured scene/HUD was visually inspected. These are real-device API checks, separate from browser interaction checks.

Ten Python tests cover the HTTP boundaries, leases/short taps, frozen BMP, wall-time FPS, fragmented single-port asset/control/preview traffic, and invalid controls/captures. Four added Rust tests cover the actual firmware parser/leased queue and preview coordinates/byte order, alongside seven existing optimization tests. Build packaging and offline image checks also pass.

The user confirmed basic browser preview/keyboard operation, but reported intermittent lost short presses. A separate real-engine regression then reproduced a concrete edge loss: `BuildNewTic` polls input once even with a full five-command buffer, so that poll could consume a queued press without building its command. The adapter now checks `D_WillBuildTic`, matching upstream's input adapter. `tests/test-short-input.py` verifies that the queued press/release survives this boundary and moves the real player. The v4r1 fix installed successfully, reconnected to the existing controller, and passed 20/20 real-device menu toggles using 10 ms presses through the local API. The user then confirmed that browser short presses were stable.

Automatic browser interaction/visual checking was unavailable: the Windows computer-use tool stopped because it could not determine the active browser URL with sufficient confidence. Focus-loss behavior has not been manually confirmed. See [VALIDATION.md](VALIDATION.md) for the hardware image hash and wider limits.
