// SPDX-License-Identifier: GPL-2.0-or-later
//! KWS-X1 display and button adapter. C keeps its original km_* ABI.
use firmware_core::buttons;
use core::sync::atomic::{AtomicU8,Ordering};
pub static APPLIED:AtomicU8=AtomicU8::new(0);
pub static MENU:core::sync::atomic::AtomicBool=core::sync::atomic::AtomicBool::new(false);
#[unsafe(link_section = ".sram2.framebuffer")]
static mut FRAME: [u16; 180 * 135] = [0; 180 * 135];
unsafe extern "C" {
    fn km_doom_init();
    fn km_doom_step();
    fn km_doom_menu() -> i32;
}
#[unsafe(no_mangle)]
extern "C" fn km_millis() -> u32 { embassy_time::Instant::now().as_millis() as u32 }
#[unsafe(no_mangle)]
extern "C" fn km_sleep(ms: u32) {
    let start = embassy_time::Instant::now();
    while start.elapsed().as_millis() < u64::from(ms) { cortex_m::asm::wfi(); }
}
#[unsafe(no_mangle)]
extern "C" fn km_keys() -> u32 {
    let raw = crate::input::next();
    let menu = unsafe { km_doom_menu() } != 0;
    MENU.store(menu,Ordering::Relaxed);
    let local=if menu {
        u32::from(raw & buttons::LEFT != 0) << 1 |
        u32::from(raw & buttons::RIGHT != 0) << 7 |
        u32::from(raw & buttons::OK != 0) << 6 |
        u32::from(raw & buttons::BACK != 0) << 5
    } else if raw & (buttons::OK | buttons::BACK) == (buttons::OK | buttons::BACK) { 32 }
    else if raw & (buttons::LEFT | buttons::RIGHT) == (buttons::LEFT | buttons::RIGHT) { 16 }
    else {
        u32::from(raw & buttons::BACK != 0) |
        u32::from(raw & buttons::OK != 0) << 1 |
        u32::from(raw & buttons::LEFT != 0) << 2 |
        u32::from(raw & buttons::RIGHT != 0) << 3
    };
    let keys=local|u32::from(crate::remote::next());
    APPLIED.store(keys as u8,Ordering::Relaxed);
    keys
}
/// The engine must remain blocked in its frame handoff until all reads finish.
pub unsafe fn preview_chunk(offset:usize,out:&mut [u8]) {
    unsafe {crate::preview::chunk(&*(&raw const FRAME),offset,out);}
}
#[unsafe(no_mangle)]
extern "C" fn km_exit() -> ! { cortex_m::peripheral::SCB::sys_reset() }
#[unsafe(no_mangle)]
extern "C" fn km_fail(_: *const core::ffi::c_char) -> ! { panic!("DOOM failed") }
#[unsafe(no_mangle)]
unsafe extern "C" fn km_flash_read(address: u32, dst: *mut u8, count: u32) {
    unsafe { crate::stream::read(address, dst, count as usize); }
}

// Uniform 9/16 downscale: full 320x240 picture -> 180x135, centered.
// A source coordinate is kept when the floor mapping advances at its end.
#[unsafe(no_mangle)]
unsafe extern "C" fn km_column(x: i32, y: i32, height: i32, pixels: *const u16) {
    if !(0..320).contains(&x) || y < 0 || height <= 0 || height > 240 - y { return; }
    let dx = (x + 1) * 9 / 16;
    if dx == x * 9 / 16 { return; }
    for i in 0..height {
        let sy = y + i;
        let dy = (sy + 1) * 9 / 16;
        if dy != sy * 9 / 16 {
            unsafe { (&raw mut FRAME).cast::<u16>().add(((dy - 1) * 180 + dx - 1) as usize).write(pixels.add(i as usize).read().swap_bytes()); }
        }
    }
}

pub async fn run() -> ! {
    // SRAM2 is NOLOAD: initialize every parity word before any DMA read.
    unsafe {
        core::ptr::write_bytes((&raw mut FRAME).cast::<u16>(), 0, 180 * 135);
        crate::stream::init();
        assert!(crate::panel::game_clear().await);
    }
    while !crate::stream::CONNECTED.load(core::sync::atomic::Ordering::Acquire) {
        embassy_time::Timer::after_millis(20).await;
    }
    unsafe { km_doom_init(); }
    crate::stream::reset_counters();
    let mut frames = 0u32;
    loop {
        let start = embassy_time::Instant::now();
        unsafe {
            km_doom_step();
            assert!(crate::panel::game_flush((&raw const FRAME).cast()).await);
        }
        frames = frames.wrapping_add(1);
        crate::stream::frame(frames,start.elapsed().as_millis() as u32,
            u32::from(crate::input::APPLIED.load(core::sync::atomic::Ordering::Relaxed)));
        embassy_time::Timer::after_millis(1).await;
    }
}
