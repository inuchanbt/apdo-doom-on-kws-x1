// SPDX-License-Identifier: GPL-2.0-or-later
use embassy_usb::{Builder, class::cdc_acm::device::{CdcAcmClass, State}};
use crate::stream;

#[embassy_executor::task]
pub async fn task() {
    static RX: static_cell::StaticCell<[u8; 256]> = static_cell::StaticCell::new();
    let (driver, _route) = unsafe { crate::usb::driver(RX.init([0; 256])) };
    // Development identity only; no claim of an allocated production PID.
    let mut config = embassy_usb::Config::new(0xc0de, 0xd00d);
    config.manufacturer = Some("APDO experiment");
    config.product = Some("KWS-X1 native DOOM data link");
    config.serial_number = Some("KWSX1DOOM05");
    let mut cfg = [0; 256];
    let mut bos = [0; 256];
    let mut control = [0; 64];
    let mut state = State::new();
    let mut builder = Builder::new(driver, config, &mut cfg, &mut bos, &mut [], &mut control);
    let mut class = CdcAcmClass::new(&mut builder, &mut state, 64);
    let mut usb = builder.build();
    embassy_futures::join::join(usb.run(), async {
        class.wait_connection().await;
        // Hello must echo format, image size and CRC before native startup.
        let mut hello = [0u8; 16];
        hello[..8].copy_from_slice(b"X1DOOM05");
        hello[8..12].copy_from_slice(&stream::IMAGE_BYTES.to_le_bytes());
        let hello_crc = stream::crc32(&hello[..12]);
        hello[12..].copy_from_slice(&hello_crc.to_le_bytes());
        assert!(class.write_packet(&hello).await.is_ok());
        let mut packet = [0u8; 64];
        assert!(class.read_packet(&mut packet).await == Ok(16));
        assert!(packet[..16] == hello);
        stream::CONNECTED.store(true, core::sync::atomic::Ordering::Release);
        let mut seq = 0u32;
        loop {
            let request = stream::REQUESTS.receive().await;
            let address = match request {
                stream::Request::Read(address) => address,
                stream::Request::Frame {number,ms,keys,misses,wait_ms,stack_free,decodes} => {
                    use core::sync::atomic::Ordering;
                    let mut stats = [0u8;52];
                    stats[..4].copy_from_slice(b"FRM5");
                    for (out,value) in stats[4..].chunks_exact_mut(4).zip([number,ms,keys,misses,wait_ms,stack_free,decodes,
                        u32::from(crate::remote::APPLIED.load(Ordering::Relaxed)),
                        u32::from(crate::game::APPLIED.load(Ordering::Relaxed)),
                        u32::from(crate::game::MENU.load(Ordering::Relaxed)),crate::preview::BYTES as u32,
                        if crate::display::APPLIED.load(Ordering::Acquire) {180} else {0}]) {
                        out.copy_from_slice(&value.to_le_bytes());
                    }
                    assert!(class.write_packet(&stats).await.is_ok());
                    let mut bytes=[0u8;crate::control::CONTROL_BYTES];
                    let mut received=0;
                    while received<bytes.len() {
                        let n=class.read_packet(&mut packet).await.expect("PC control disconnected");
                        assert!(n<=bytes.len()-received);
                        bytes[received..received+n].copy_from_slice(&packet[..n]);received+=n;
                    }
                    let control=crate::control::parse(&bytes,number).unwrap_or_else(|_|{crate::remote::clear();panic!("bad PC control frame")});
                    crate::display::DESIRED.store(control.flags&crate::control::INVERTED!=0,Ordering::Release);
                    crate::remote::update(control);
                    if control.flags&crate::control::PREVIEW!=0 {
                        // FRAME stays immutable until READY. Two bounded passes
                        // compute CRC then send pixels without another framebuffer.
                        let mut pixels=[0u8;64];
                        let mut crc=!0u32;
                        for offset in (0..crate::preview::BYTES).step_by(64) {
                            let n=(crate::preview::BYTES-offset).min(64);
                            unsafe {crate::game::preview_chunk(offset,&mut pixels[..n]);}
                            crc=crate::control::crc_update(crc,&pixels[..n]);
                        }
                        let mut header=[0u8;24];header[..4].copy_from_slice(b"IMG4");
                        for (out,value) in header[4..].chunks_exact_mut(4).zip([number,crate::preview::WIDTH as u32,crate::preview::HEIGHT as u32,crate::preview::BYTES as u32,!crc]) {out.copy_from_slice(&value.to_le_bytes());}
                        assert!(class.write_packet(&header).await.is_ok());
                        for offset in (0..crate::preview::BYTES).step_by(64) {
                            let n=(crate::preview::BYTES-offset).min(64);
                            unsafe {crate::game::preview_chunk(offset,&mut pixels[..n]);}
                            assert!(class.write_packet(&pixels[..n]).await.is_ok());
                        }
                    }
                    stream::READY.store(true,core::sync::atomic::Ordering::Release);
                    continue;
                }
            };
            seq = seq.wrapping_add(1);
            let mut request = [0u8; 16];
            request[..4].copy_from_slice(b"GET2");
            request[4..8].copy_from_slice(&seq.to_le_bytes());
            request[8..12].copy_from_slice(&address.to_le_bytes());
            request[12..].copy_from_slice(&(stream::PAGE as u32).to_le_bytes());
            assert!(class.write_packet(&request).await.is_ok());
            // CDC is a byte stream: neither header nor page must align with a
            // USB packet. Also accept harmless zero-length OUT packets.
            let mut response = [0u8; 20 + stream::PAGE];
            let mut done = 0;
            let mut total = response.len();
            while done != total {
                let n = class.read_packet(&mut packet).await.expect("USB game data disconnected");
                assert!(n <= total - done);
                response[done..done+n].copy_from_slice(&packet[..n]);
                done += n;
                if done >= 20 {
                    let encoded_len = u32::from_le_bytes(response[16..20].try_into().unwrap()) as usize;
                    assert!(encoded_len > 0 && encoded_len <= stream::PAGE);
                    total = 20+encoded_len;
                    assert!(done <= total);
                }
            }
            assert!(response[..12] == request[4..16]);
            let expected_crc = u32::from_le_bytes(response[12..16].try_into().unwrap());
            unsafe { stream::publish(&response[20..total],expected_crc); }
        }
    }).await;
}
