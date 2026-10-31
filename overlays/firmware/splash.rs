// SPDX-License-Identifier: MIT
//! Original Freedoom Phase 1 M_DOOM; asset license/provenance in freedoom-banner.json.
use crate::indexed_frame::{Frame,WIDTH,HEIGHT};
const IMAGE:&[u8;6021]=include_bytes!("freedoom-banner.bin");
const SOURCE_WIDTH:usize=159;
const SOURCE_HEIGHT:usize=37;
const COLORS:usize=66;
const PIXELS:usize=6+COLORS*2;
pub const DRAW_WIDTH:usize=216;
pub const DRAW_HEIGHT:usize=DRAW_WIDTH*SOURCE_HEIGHT/SOURCE_WIDTH;

/// Draw into the existing indexed frame; no extra framebuffer or game-time work.
pub fn draw(frame:&mut Frame) {
    frame.pixels.fill(0);
    frame.palette.fill(0);
    for i in 0..COLORS {
        frame.palette[i]=u16::from_le_bytes([IMAGE[6+i*2],IMAGE[7+i*2]]).swap_bytes();
    }
    let left=(WIDTH-DRAW_WIDTH)/2;
    let top=(HEIGHT-DRAW_HEIGHT)/2;
    for y in 0..DRAW_HEIGHT {
        let sy=y*SOURCE_HEIGHT/DRAW_HEIGHT;
        for x in 0..DRAW_WIDTH {
            let sx=x*SOURCE_WIDTH/DRAW_WIDTH;
            frame.pixels[(top+y)*WIDTH+left+x]=IMAGE[PIXELS+sy*SOURCE_WIDTH+sx];
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn original_pixels_are_centered_and_old_frame_is_fully_cleared() {
        assert_eq!(&IMAGE[..6],&[159,0,37,0,66,0]);
        assert_eq!(&IMAGE[6..8],&[0,0]);
        assert!(IMAGE[PIXELS..].iter().all(|&i|(i as usize)<COLORS));
        let mut frame=Frame::new();frame.pixels.fill(255);frame.palette.fill(0xffff);
        draw(&mut frame);
        for y in 0..HEIGHT {for x in 0..WIDTH {
            let index=frame.pixels[y*WIDTH+x];
            if (12..228).contains(&x) && (42..92).contains(&y) {
                assert_eq!(index,IMAGE[PIXELS+(y-42)*37/50*159+(x-12)*159/216]);
            } else {assert_eq!(index,0);}
        }}
        for i in 0..COLORS {assert_eq!(frame.palette[i].swap_bytes(),u16::from_le_bytes([IMAGE[6+i*2],IMAGE[7+i*2]]));}
        assert!(frame.palette[COLORS..].iter().all(|&c|c==0));
        assert_eq!((DRAW_WIDTH,DRAW_HEIGHT),(216,50));
    }
}
