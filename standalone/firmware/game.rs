// SPDX-License-Identifier: GPL-2.0-or-later
//! KWS-X1 display and button adapter. C keeps its original km_* ABI.
use firmware_core::buttons;
use core::sync::atomic::{AtomicU8,Ordering};
pub static APPLIED:AtomicU8=AtomicU8::new(0);
pub static MENU:core::sync::atomic::AtomicBool=core::sync::atomic::AtomicBool::new(false);
#[unsafe(link_section = ".sram2.framebuffer")]
static mut FRAME: crate::indexed_frame::Frame = crate::indexed_frame::Frame::new();
unsafe extern "C" {
    fn km_doom_init();
    fn km_doom_step();
    fn km_doom_menu() -> i32;
    fn km_doom_redraw();
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
    let keys=local;
    APPLIED.store(keys as u8,Ordering::Relaxed);
    keys
}
#[unsafe(no_mangle)]
extern "C" fn km_exit() -> ! { cortex_m::peripheral::SCB::sys_reset() }
#[unsafe(no_mangle)]
extern "C" fn km_fail(_: *const core::ffi::c_char) -> ! { panic!("DOOM failed") }
#[unsafe(no_mangle)]
unsafe extern "C" fn km_flash_read(address: u32, dst: *mut u8, count: u32) {
    unsafe { crate::stream::read(address, dst, count as usize); }
}

#[unsafe(no_mangle)]
unsafe extern "C" fn km_set_palette(colors:*const u16) {
    unsafe {(&mut *(&raw mut FRAME)).set_palette(core::slice::from_raw_parts(colors,256));}
}
#[unsafe(no_mangle)]
unsafe extern "C" fn km_index_column(x:i32,y:i32,height:i32,pixels:*const u8,ui:u32) {
    assert!(height>=0);
    unsafe {(&mut *(&raw mut FRAME)).column(x,y,core::slice::from_raw_parts(pixels,height as usize),ui!=0);}
}
// Compatibility for rare direct-color fills; game/UI columns stay indexed.
#[unsafe(no_mangle)]
unsafe extern "C" fn km_column(x: i32, y: i32, height: i32, pixels: *const u16) {
    if !(0..320).contains(&x) || y < 0 || height <= 0 || height > 240 - y { return; }
    let frame=unsafe {&mut *(&raw mut FRAME)};
    let mut indices=[0u8;240];
    for i in 0..height as usize {
        let color=unsafe {*pixels.add(i)};
        indices[i]=frame.palette.iter().position(|&p|p==color.swap_bytes()).unwrap_or(0) as u8;
    }
    frame.column(x,y,&indices[..height as usize],false);
}

pub async fn run() -> ! {
    // SRAM2 is NOLOAD: initialize every parity word before any DMA read.
    unsafe {
        core::ptr::write_bytes(&raw mut FRAME, 0, 1);
        crate::stream::init();
        assert!(crate::panel::game_clear(crate::panel::Orientation::Normal).await);
    }
    unsafe {
        crate::splash::draw(&mut *(&raw mut FRAME));
        assert!(crate::panel::game_flush(&*(&raw const FRAME),crate::panel::Orientation::Normal).await);
    }
    embassy_time::Timer::after_millis(1200).await;
    unsafe {
        (&mut *(&raw mut FRAME)).pixels.fill(0);
        km_doom_init();
    }
    crate::stream::reset_counters();
    let mut frames = 0u32;
    loop {
        let start = embassy_time::Instant::now();
        let orientation = crate::panel::Orientation::Normal;
        unsafe {
            km_doom_step();
            assert!(crate::panel::game_flush(&*(&raw const FRAME),orientation).await);
        }
        frames = frames.wrapping_add(1);
        crate::stream::frame(frames,start.elapsed().as_millis() as u32,
            u32::from(crate::input::APPLIED.load(core::sync::atomic::Ordering::Relaxed)));
        embassy_time::Timer::after_millis(1).await;
    }
}
