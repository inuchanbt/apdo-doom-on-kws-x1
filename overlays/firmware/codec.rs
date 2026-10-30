// SPDX-License-Identifier: GPL-2.0-or-later
//! Bounded raw LZ4 block decoder; equal-length blocks are sent uncompressed.
pub fn decode(input: &[u8], output: &mut [u8]) -> Result<(), ()> {
    if input.len() == output.len() { output.copy_from_slice(input); return Ok(()); }
    let (mut at, mut out) = (0usize, 0usize);
    fn length(input: &[u8], at: &mut usize, initial: usize) -> Result<usize, ()> {
        let mut n = initial;
        if initial == 15 {
            loop {
                let byte = *input.get(*at).ok_or(())?;
                *at += 1;
                n = n.checked_add(byte as usize).ok_or(())?;
                if byte != 255 { break; }
            }
        }
        Ok(n)
    }
    while at < input.len() {
        let token = input[at]; at += 1;
        let literals = length(input, &mut at, (token >> 4) as usize)?;
        if literals > input.len() - at || literals > output.len() - out { return Err(()); }
        output[out..out+literals].copy_from_slice(&input[at..at+literals]);
        at += literals; out += literals;
        if at == input.len() { return if out == output.len() { Ok(()) } else { Err(()) }; }
        if input.len() - at < 2 { return Err(()); }
        let offset = u16::from_le_bytes([input[at], input[at+1]]) as usize;
        at += 2;
        if offset == 0 || offset > out { return Err(()); }
        let matched = length(input, &mut at, (token & 15) as usize)?.checked_add(4).ok_or(())?;
        if matched > output.len() - out { return Err(()); }
        // Seed a non-overlapping prefix, then duplicate initialized bytes in
        // growing chunks. Byte-at-a-time overlap copies dominate decode time
        // on the Cortex-M4 when hundreds of 1 KiB pages miss the hot cache.
        let (past,future)=output.split_at_mut(out);
        let future=&mut future[..matched];
        if offset==1 {
            future.fill(past[out-1]);
        } else {
            let mut copied=offset.min(matched);
            future[..copied].copy_from_slice(&past[out-offset..out-offset+copied]);
            while copied<matched {
                let (seed,tail)=future.split_at_mut(copied);
                let n=seed.len().min(tail.len());
                tail[..n].copy_from_slice(&seed[..n]);
                copied+=n;
            }
        }
        out+=matched;
    }
    if out == output.len() { Ok(()) } else { Err(()) }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn overlap_and_long_match() {
        let mut out = [0; 1024];
        // One literal 'A', then a 1023-byte overlapping match at offset 1.
        decode(&[0x1f, b'A', 1, 0, 255, 255, 255, 239], &mut out).unwrap();
        assert!(out.iter().all(|&b| b == b'A'));
    }
    #[test]
    fn corrupt_blocks_cannot_read_or_write_outside_buffers() {
        for input in [&[][..], &[0xf0], &[0x00,0,0], &[0x00,1,0], &[0x1f,1,1,0,255]] {
            assert!(decode(input, &mut [0;1024]).is_err());
        }
        assert!(decode(&[0x10,1,1,0], &mut [0;3]).is_err());
    }
    #[test]
    fn periodic_matches_cover_short_long_and_unaligned_offsets() {
        fn extra(bytes:&mut Vec<u8>,mut n:usize) {
            while n>=255 {bytes.push(255);n-=255;}
            bytes.push(n as u8);
        }
        for offset in [1usize,2,3,4,7,15,16,17,255,256,511] {
            for matched in [4usize,7,16,18,19,20,255,512,1023] {
                let mut block=vec![(offset.min(15) as u8)<<4 | (matched-4).min(15) as u8];
                if offset>=15 {extra(&mut block,offset-15);}
                let seed:Vec<u8>=(0..offset).map(|i|(i%251) as u8).collect();
                block.extend_from_slice(&seed);
                block.extend_from_slice(&(offset as u16).to_le_bytes());
                if matched>=19 {extra(&mut block,matched-19);}
                let expected:Vec<u8>=seed.iter().copied().cycle().take(offset+matched).collect();
                // Equal lengths denote a raw block in this wire format.
                if block.len()==expected.len() {continue;}
                let mut output=vec![0;expected.len()];
                decode(&block,&mut output).unwrap();
                assert_eq!(output,expected,"offset={offset}, matched={matched}");
                let short=expected.len()-if block.len()==expected.len()-1 {2}else{1};
                assert!(decode(&block,&mut output[..short]).is_err());
            }
        }
    }
}
