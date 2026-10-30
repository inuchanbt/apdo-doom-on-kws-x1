// SPDX-License-Identifier: GPL-2.0-or-later
#[path="../overlays/firmware/codec.rs"] mod codec;
#[path="../overlays/firmware/control.rs"] mod control;
#[path="../artifacts/mini/mini_assets.rs"] mod mini_assets;
#[path="../standalone/firmware/stream.rs"] mod stream;

#[test]
fn actual_internal_flash_reader_matches_pack_across_pages_and_evictions() {
    let raw=std::fs::read("artifacts/mini/DOOM.DAT").unwrap();
    assert_eq!(raw.len(),mini_assets::IMAGE_BYTES as usize);
    let mut full=vec![0;raw.len()];
    unsafe {stream::read(0,full.as_mut_ptr(),full.len());}
    assert_eq!(full,raw);
    let mut rng=0x514b7751u32;
    for _ in 0..600 {
        rng=rng.wrapping_mul(1664525).wrapping_add(1013904223);
        let at=rng as usize%raw.len();
        rng=rng.wrapping_mul(1664525).wrapping_add(1013904223);
        let n=(rng as usize%4097).min(raw.len()-at);
        let mut got=vec![0;n];
        unsafe {stream::read(at as u32,got.as_mut_ptr(),n);}
        assert_eq!(got,&raw[at..at+n]);
    }
    unsafe {stream::read(raw.len() as u32,core::ptr::null_mut(),0);}
    assert!(std::panic::catch_unwind(||unsafe {stream::read(mini_assets::IMAGE_BYTES+1,core::ptr::null_mut(),1)}).is_err());
    println!("All mini pages and 600 crossing/eviction reads match without USB");
}
