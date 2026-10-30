// SPDX-License-Identifier: GPL-2.0-or-later
//! Read the entire mini pack from internal flash. No USB or host handoff.
pub const PAGE:usize=1024;
pub const IMAGE_BYTES:u32=crate::mini_assets::IMAGE_BYTES;
#[repr(C,align(1024))]
struct HotPages([[u8;PAGE];8]);
static mut HOT:HotPages=HotPages([[0;PAGE];8]);
static mut TAGS:[u32;8]=[u32::MAX;8];
static mut AGES:[u32;8]=[0;8];
static mut CLOCK:u32=0;
pub fn crc32(bytes:&[u8])->u32 {!crate::control::crc_update(!0,bytes)}
pub unsafe fn init() {}
/// The native engine is the sole owner; each decoded page stays within a bank.
pub unsafe fn read(mut address:u32,mut dst:*mut u8,mut count:usize) {
    assert!(address<=IMAGE_BYTES && count<=(IMAGE_BYTES-address) as usize);
    while count!=0 {
        let page=address/PAGE as u32;
        let found=(0..8).find(|&i|unsafe{TAGS[i]}==page);
        let slot=found.unwrap_or_else(||(0..8).max_by_key(|&i|unsafe{CLOCK.wrapping_sub(AGES[i])}).unwrap());
        if found.is_none() {
            let (encoded,crc)=crate::mini_assets::page(page as usize);
            unsafe {
                let decoded=&mut *(&raw mut HOT).cast::<[u8;PAGE]>().add(slot);
                crate::codec::decode(encoded,decoded).expect("bad internal asset page");
                assert_eq!(crc32(decoded),crc,"internal asset CRC");
                TAGS[slot]=page;
            }
        }
        let offset=address as usize%PAGE;
        let n=count.min(PAGE-offset);
        unsafe {
            CLOCK=CLOCK.wrapping_add(1);AGES[slot]=CLOCK;
            core::ptr::copy_nonoverlapping((&raw const HOT).cast::<u8>().add(slot*PAGE+offset),dst,n);
            dst=dst.add(n);
        }
        address+=n as u32;count-=n;
    }
}
pub fn reset_counters() {}
pub fn frame(_:u32,_:u32,_:u32) {}
