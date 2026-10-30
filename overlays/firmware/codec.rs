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
        for _ in 0..matched { output[out] = output[out-offset]; out += 1; }
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
}
