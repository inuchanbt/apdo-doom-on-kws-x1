// SPDX-License-Identifier: GPL-2.0-or-later
//! Compressed game-data cache shared with the IRQ USB executor by handoff only.
use core::sync::atomic::{AtomicBool, Ordering};
use embassy_sync::{blocking_mutex::raw::CriticalSectionRawMutex, channel::Channel};
use crate::page_cache::{Cache, Entry, BANK_BYTES, CELL_BYTES, BANK_CELLS};
pub const PAGE: usize = 1024;
pub const IMAGE_BYTES: u32 = 2_802_000;
#[derive(Clone,Copy,Debug)]
pub enum Request { Read(u32), Frame { number:u32, ms:u32, keys:u32, misses:u32, wait_ms:u32, stack_free:u32, decodes:u32 } }
pub static REQUESTS: Channel<CriticalSectionRawMutex, Request, 1> = Channel::new();
pub static READY: AtomicBool = AtomicBool::new(false);
pub static CONNECTED: AtomicBool = AtomicBool::new(false);
static mut RESPONSE: [u8;PAGE] = [0;PAGE];
static mut RESPONSE_LEN: usize = 0;
static mut RESPONSE_CRC: u32 = 0;
static mut CACHE: Cache = Cache::new();
#[unsafe(link_section = ".sram2.asset_cache")]
static mut BANK0: [u8;BANK_BYTES] = [0;BANK_BYTES];
static mut BANK1: [u8;BANK_BYTES] = [0;BANK_BYTES];
static mut CURRENT: u32 = u32::MAX;
static mut CURRENT_SLOT: usize = 0;
// Keep individual pages from straddling the Cortex-M memory-region boundary
// between SRAMH and SRAM1, including when memcpy uses unaligned word loads.
#[repr(C,align(1024))]
struct HotPages([[u8;PAGE];12]);
#[unsafe(link_section = ".sram2.hot_pages")]
static mut HOT: HotPages = HotPages([[0;PAGE];12]);
static mut HOT_TAGS: [u32;12] = [u32::MAX;12];
static mut HOT_AGES: [u32;12] = [0;12];
static mut HOT_CLOCK: u32 = 0;
static mut MISSES: u32 = 0;
static mut WAIT_US: u64 = 0;
static mut DECODES: u32 = 0;
pub fn crc32(bytes: &[u8]) -> u32 {
    !crate::control::crc_update(!0,bytes)
}
/// Initialize NOLOAD SRAM2 parity before copying arbitrary-length blocks into it.
pub unsafe fn init() {
    unsafe { core::ptr::write_bytes((&raw mut BANK0).cast::<u8>(),0,BANK_BYTES); }
    unsafe { core::ptr::write_bytes((&raw mut HOT).cast::<u8>(),0,12*PAGE); }
}
/// USB exclusively writes the response before release-publishing it. The
/// engine consumes it completely before issuing another request.
pub unsafe fn publish(bytes: &[u8], crc:u32) {
    assert!(!bytes.is_empty() && bytes.len() <= PAGE);
    unsafe {
        core::ptr::copy_nonoverlapping(bytes.as_ptr(),(&raw mut RESPONSE).cast(),bytes.len());
        RESPONSE_LEN = bytes.len(); RESPONSE_CRC = crc;
    }
    READY.store(true,Ordering::Release);
}
fn wait() {
    let start = embassy_time::Instant::now();
    while !READY.load(Ordering::Acquire) {
        assert!(start.elapsed().as_millis() < 10_000,"game data USB timeout");
        cortex_m::asm::wfi();
    }
}
unsafe fn pointer(entry:Entry) -> *mut u8 {
    let bank = if entry.cell < BANK_CELLS { (&raw mut BANK0).cast::<u8>() } else { (&raw mut BANK1).cast::<u8>() };
    unsafe { bank.add(entry.cell%BANK_CELLS*CELL_BYTES) }
}
/// The engine is the sole owner of cache state and the uncompressed hot page.
pub unsafe fn read(mut address:u32, mut dst:*mut u8, mut count:usize) {
    assert!(address <= IMAGE_BYTES && count <= (IMAGE_BYTES-address) as usize);
    while count != 0 {
        let base = address/PAGE as u32*PAGE as u32;
        if unsafe { CURRENT } != base {
            let hot = (0..12).find(|&i|unsafe {HOT_TAGS[i]}==base);
            let slot=hot.unwrap_or_else(||(0..12).max_by_key(|&i|unsafe {HOT_CLOCK.wrapping_sub(HOT_AGES[i])}).unwrap());
            if hot.is_none() {
            let pinned=crate::pinned_assets::get(base);
            let (encoded_ptr,encoded_len,expected_crc) = if let Some(bytes)=pinned {
                (bytes.as_ptr(),bytes.len(),None)
            } else {
            let found = unsafe { (&mut *(&raw mut CACHE)).get(base) };
            let (entry, expected_crc) = match found {
                Some(entry) => (entry,None),
                None => {
                    READY.store(false,Ordering::Release);
                    REQUESTS.try_send(Request::Read(base)).expect("one outstanding read");
                    let start = embassy_time::Instant::now();
                    wait();
                    let len = unsafe { RESPONSE_LEN };
                    let entry = unsafe { (&mut *(&raw mut CACHE)).insert(base,len) };
                    unsafe {
                        core::ptr::copy_nonoverlapping((&raw const RESPONSE).cast::<u8>(),pointer(entry),len);
                        MISSES = MISSES.wrapping_add(1);
                        WAIT_US = WAIT_US.wrapping_add(start.elapsed().as_micros());
                    }
                    (entry,Some(unsafe { RESPONSE_CRC }))
                }
            };
            (unsafe {pointer(entry)} as *const u8,entry.len,expected_crc)
            };
            unsafe {
                let encoded = core::slice::from_raw_parts(encoded_ptr,encoded_len);
                let decoded = &mut *(&raw mut HOT).cast::<[u8;PAGE]>().add(slot);
                crate::codec::decode(encoded,decoded).expect("bad compressed page");
                if let Some(crc) = expected_crc { assert!(crc32(decoded)==crc,"page CRC"); }
                HOT_TAGS[slot]=base;
                DECODES=DECODES.wrapping_add(1);
            }
            }
            unsafe {
                HOT_CLOCK=HOT_CLOCK.wrapping_add(1);
                HOT_AGES[slot]=HOT_CLOCK;
                CURRENT = base;
                CURRENT_SLOT=slot;
            }
        }
        let offset = (address-base) as usize;
        let n = count.min(PAGE-offset);
        unsafe {
            core::ptr::copy_nonoverlapping((&raw const HOT).cast::<u8>().add(CURRENT_SLOT*PAGE+offset),dst,n);
            dst = dst.add(n);
        }
        address += n as u32; count -= n;
    }
}
pub fn frame(number:u32, ms:u32, keys:u32) {
    READY.store(false,Ordering::Release);
    let (misses,wait_ms,decodes) = unsafe { let result=(MISSES,(WAIT_US/1000) as u32,DECODES); MISSES=0;WAIT_US=0;DECODES=0;result };
    let stack_free=stack_unused();
    REQUESTS.try_send(Request::Frame {number,ms,keys,misses,wait_ms,stack_free,decodes}).expect("frame report");
    wait();
}
pub fn reset_counters() { unsafe { MISSES=0;WAIT_US=0;DECODES=0; } }
fn stack_unused() -> u32 {
    unsafe extern "C" { static _stack_end:u32; static _stack_start:u32; }
    let low=&raw const _stack_end as usize;
    let high=&raw const _stack_start as usize;
    let words=(high-low)/4;
    let used=firmware_core::stack::peak_bytes(words,|i|unsafe { ((low+i*4) as *const u32).read_volatile() });
    ((high-low)-used) as u32
}
