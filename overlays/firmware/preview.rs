// SPDX-License-Identifier: GPL-2.0-or-later
//! Sampling the completed 180x135 wire-order framebuffer, without a second image.
pub const WIDTH:usize=120;
pub const HEIGHT:usize=90;
pub const BYTES:usize=WIDTH*HEIGHT*2;
pub fn chunk(frame:&[u16],offset:usize,out:&mut [u8]) {
    assert_eq!(frame.len(),180*135);
    assert!(offset%2==0 && out.len()%2==0 && offset+out.len()<=BYTES);
    for (i,pixel) in out.chunks_exact_mut(2).enumerate() {
        let at=offset/2+i;
        let source=(at/WIDTH*3/2)*180+(at%WIDTH*3/2);
        pixel.copy_from_slice(&frame[source].swap_bytes().to_le_bytes());
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn chunking_sampling_and_wire_order() {
        let mut frame=vec![0u16;180*135];
        for (i,v) in frame.iter_mut().enumerate(){*v=(i as u16).swap_bytes();}
        let mut image=vec![0;BYTES];
        for offset in (0..BYTES).step_by(64) {let end=(offset+64).min(BYTES);chunk(&frame,offset,&mut image[offset..end]);}
        for y in 0..HEIGHT {for x in 0..WIDTH {
            assert_eq!(u16::from_le_bytes(image[(y*WIDTH+x)*2..(y*WIDTH+x)*2+2].try_into().unwrap()),((y*3/2)*180+x*3/2) as u16);
        }}
        assert!(std::panic::catch_unwind(||chunk(&frame,BYTES,&mut [0;2])).is_err());
    }
}
