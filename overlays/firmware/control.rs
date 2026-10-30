// SPDX-License-Identifier: GPL-2.0-or-later
//! Fixed v4 input frame and allocation-free leased input state.
pub const CONTROL_BYTES: usize = 36;
pub const PREVIEW: u32 = 1;
pub const CLEAR: u32 = 2;
#[derive(Debug,Clone,Copy)]
pub struct Control { pub buttons:u8, pub lease_ms:u16, pub flags:u32, pub events:[u8;8], pub count:usize }
pub fn crc_update(mut reg:u32, bytes:&[u8]) -> u32 {
    const TABLE:[u32;256] = {
        let mut t=[0;256]; let mut i=0;
        while i<256 { let mut v=i as u32;let mut j=0;while j<8 {v=(v>>1)^(0xedb88320 & 0u32.wrapping_sub(v&1));j+=1;} t[i]=v;i+=1; } t
    };
    for &b in bytes {reg=(reg>>8)^TABLE[((reg as u8)^b) as usize];} reg
}
pub fn parse(bytes:&[u8;CONTROL_BYTES], frame:u32) -> Result<Control,()> {
    let word=|at|u32::from_le_bytes(bytes[at..at+4].try_into().unwrap());
    if &bytes[..4]!=b"CTL4" || word(4)!=frame || !crc_update(!0,&bytes[..32])!=word(32) {return Err(());}
    let (buttons,lease,flags,count)=(word(8),word(12),word(16),word(20));
    if buttons>255 || !(100..=1000).contains(&lease) || flags & !(PREVIEW|CLEAR)!=0 || count>8 {return Err(());}
    let events=bytes[24..32].try_into().unwrap();
    Ok(Control {buttons:buttons as u8,lease_ms:lease as u16,flags,events,count:count as usize})
}
pub struct Remote {held:u8, current:u8, until:u64, queue:[u8;16], head:usize, len:usize}
impl Remote {
    pub const fn new()->Self { Self {held:0,current:0,until:0,queue:[0;16],head:0,len:0} }
    pub fn clear(&mut self) {self.held=0;self.current=0;self.until=0;self.head=0;self.len=0;}
    pub fn expire(&mut self,now:u64) {if now>=self.until {self.clear();}}
    pub fn update(&mut self,c:Control,now:u64) {
        self.expire(now);
        if c.flags&CLEAR!=0 {self.clear();return;}
        if self.len+c.count>self.queue.len() {self.clear();return;}
        for &value in &c.events[..c.count] {self.queue[(self.head+self.len)%16]=value;self.len+=1;}
        self.held=c.buttons;
        self.until=now.saturating_add(u64::from(c.lease_ms));
    }
    pub fn next(&mut self,now:u64)->u8 {
        self.expire(now);
        if self.len!=0 {self.current=self.queue[self.head];self.head=(self.head+1)%16;self.len-=1;}
        else {self.current=self.held;}
        self.current
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn state(buttons:u8,events:&[u8])->Control {
        let mut c=Control {buttons,lease_ms:750,flags:0,events:[0;8],count:events.len()};
        c.events[..events.len()].copy_from_slice(events);c
    }
    #[test] fn short_tap_release_and_expiry() {
        let mut r=Remote::new();r.update(state(0,&[1,0]),100);
        assert_eq!(r.next(110),1);assert_eq!(r.next(110),0);
        r.update(state(2,&[2]),200);assert_eq!(r.next(300),2);assert_eq!(r.next(950),0);
        r.update(state(8,&[8]),1000);let mut c=state(0,&[]);c.flags=CLEAR;r.update(c,1001);assert_eq!(r.next(1002),0);
    }
    #[test] fn overflow_releases_instead_of_sticking() {
        let mut r=Remote::new();for _ in 0..3 {r.update(state(1,&[1;8]),100);}
        assert_eq!(r.next(110),0);
    }
    #[test] fn frame_crc_and_bounds_are_checked() {
        let mut b=[0u8;36];b[..4].copy_from_slice(b"CTL4");b[4..8].copy_from_slice(&7u32.to_le_bytes());
        b[12..16].copy_from_slice(&750u32.to_le_bytes());
        let crc=!crc_update(!0,&b[..32]);b[32..].copy_from_slice(&crc.to_le_bytes());
        assert!(parse(&b,7).is_ok());assert!(parse(&b,8).is_err());
        b[24]^=1;assert!(parse(&b,7).is_err());
        assert_eq!(!crc_update(!0,b"123456789"),0xcbf43926);
    }
}
