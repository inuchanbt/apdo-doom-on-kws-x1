// SPDX-License-Identifier: GPL-2.0-or-later
// Game-only rectangle transport. Keeps the 30-pixel sidebars out of SRAM.
pub async unsafe fn game_clear(orientation: Orientation) -> bool {
    let mut owner = DISPLAY.lock().await;
    let Some(bus) = owner.as_mut() else { return false; };
    if !command(bus, panel::CMD_COLUMN_ADDRESS, &COLUMNS).await
        || !command(bus, panel::CMD_ROW_ADDRESS, &span(orientation.first_row(), panel::HEIGHT)).await
        || !command(bus, panel::CMD_MEMORY_WRITE, &[]).await
        || !bus.idle().await { return false; }
    let row = [0u8; ROW_BYTES];
    bus.dc(true);
    for _ in 0..panel::HEIGHT { if !bus.pixels(&row).await { return false; } }
    bus.idle().await
}
/// The 180x135 wire-order frame is immutable until this DMA future completes.
pub async unsafe fn game_flush(frame: *const u16, orientation: Orientation) -> bool {
    let mut owner = DISPLAY.lock().await;
    let Some(bus) = owner.as_mut() else { return false; };
    if !command(bus, panel::CMD_COLUMN_ADDRESS, &span(panel::X_OFFSET+30,180)).await
        || !command(bus, panel::CMD_ROW_ADDRESS, &span(orientation.first_row(),135)).await
        || !command(bus, panel::CMD_MEMORY_WRITE, &[]).await
        || !bus.idle().await { return false; }
    bus.dc(true);
    let bytes = unsafe { core::slice::from_raw_parts(frame.cast::<u8>(),180*135*2) };
    bus.pixels(bytes).await && bus.idle().await
}
