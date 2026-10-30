// SPDX-License-Identifier: GPL-2.0-or-later
//! Full LCD, preserving the engine palette and separate world/UI geometry.
pub const WIDTH:usize=240;
pub const HEIGHT:usize=135;
#[repr(C)]
pub struct Frame {pub pixels:[u8;WIDTH*HEIGHT],pub palette:[u16;256]}
impl Frame {
    pub const fn new()->Self {Self{pixels:[0;WIDTH*HEIGHT],palette:[0;256]}}
    pub fn set_palette(&mut self,colors:&[u16]) {
        assert_eq!(colors.len(),256);
        for (to,from) in self.palette.iter_mut().zip(colors){*to=from.swap_bytes();}
    }
    pub fn column(&mut self,x:i32,y:i32,pixels:&[u8],ui:bool) {
        assert!((0..320).contains(&x) && y>=0 && y+pixels.len() as i32<=240);
        let (step,den)=if ui {(9,16)}else{(3,4)};
        if (x+1)*step/den==x*step/den {return;}
        let base=(x+1)*step/den-1;
        for (i,&index) in pixels.iter().enumerate() {
            let sy=y+i as i32;
            let dy=(sy+1)*9/16;
            if dy==sy*9/16 {continue;}
            let offset=if !ui {0} else if sy<208 {30}
                else if x<48 {0} else if x<104 {12} else if x<140 {24}
                else if x<176 {30} else if x<248 {36} else {60};
            let dx=base+offset;
            self.pixels[((dy-1)*WIDTH as i32+dx) as usize]=index;
        }
    }
    pub fn row(&self,y:usize,out:&mut [u16]) {
        assert!(y<HEIGHT && out.len()==WIDTH);
        for (dst,&index) in out.iter_mut().zip(&self.pixels[y*WIDTH..(y+1)*WIDTH]) {
            *dst=self.palette[index as usize];
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn world_covers_both_edges_and_ui_remains_unstretched() {
        let mut f=Frame::new();
        for x in 0..320 {f.column(x,0,&[1;200],false);}
        assert!(f.pixels[..WIDTH*112].iter().all(|&p|p==1));
        for x in 0..320 {f.column(x,0,&[2;200],true);}
        for row in f.pixels[..WIDTH*112].chunks_exact(WIDTH) {
            assert!(row[..30].iter().chain(&row[210..]).all(|&p|p==1));
            assert!(row[30..210].iter().all(|&p|p==2));
        }
    }
    #[test] fn all_hud_sections_survive_and_palette_is_exact() {
        let mut f=Frame::new();
        for x in 0..320 {f.column(x,208,&[3;32],true);}
        assert_eq!(f.pixels[134*WIDTH],3);
        assert_eq!(f.pixels[135*WIDTH-1],3);
        assert_eq!(f.pixels[134*WIDTH+120],3);
        let colors:Vec<u16>=(0..256).collect();f.set_palette(&colors);
        for x in 0..WIDTH {f.pixels[x]=x as u8;}
        let mut row=[0;WIDTH];f.row(0,&mut row);
        for (x,&v) in row.iter().enumerate(){assert_eq!(v.swap_bytes(),x as u16);}
    }
}
