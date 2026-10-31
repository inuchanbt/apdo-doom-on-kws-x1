// SPDX-License-Identifier: GPL-2.0-or-later
//! Host FFI for the production LCD mapper, connected to the real C engine.
#[path="../overlays/firmware/indexed_frame.rs"] mod indexed_frame;
#[path="../overlays/firmware/splash.rs"] mod splash;
static mut FRAME:indexed_frame::Frame=indexed_frame::Frame::new();
#[unsafe(no_mangle)]
pub unsafe extern "C" fn wide_splash() {
    unsafe {splash::draw(&mut *(&raw mut FRAME));}
}
#[unsafe(no_mangle)]
pub unsafe extern "C" fn wide_clear() {
    unsafe {(&mut *(&raw mut FRAME)).pixels.fill(0);}
}
#[unsafe(no_mangle)]
pub unsafe extern "C" fn wide_column(x:i32,y:i32,h:i32,pixels:*const u8,ui:u32) {
    unsafe {(&mut *(&raw mut FRAME)).column(x,y,core::slice::from_raw_parts(pixels,h as usize),ui!=0);}
}
#[unsafe(no_mangle)]
pub unsafe extern "C" fn wide_palette(colors:*const u16) {
    unsafe {(&mut *(&raw mut FRAME)).set_palette(core::slice::from_raw_parts(colors,256));}
}
#[unsafe(no_mangle)]
pub unsafe extern "C" fn wide_rgb(out:*mut u16) {
    let frame=unsafe {&*(&raw const FRAME)};
    let dst=unsafe {core::slice::from_raw_parts_mut(out,240*135)};
    for y in 0..135 {
        let row=&mut dst[y*240..(y+1)*240];frame.row(y,row);
        for word in row {*word=word.swap_bytes();}
    }
}
