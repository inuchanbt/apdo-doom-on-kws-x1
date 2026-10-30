// SPDX-License-Identifier: GPL-2.0-or-later
//! Sample independently of rendering and preserve short press/release edges.
use core::sync::atomic::{AtomicU8, Ordering};
use embassy_hc32::gpio::InputPin;
use embassy_sync::{blocking_mutex::raw::CriticalSectionRawMutex, channel::Channel};
use firmware_core::buttons::Debounced;
static EDGES: Channel<CriticalSectionRawMutex,u8,16> = Channel::new();
static HELD: AtomicU8 = AtomicU8::new(0);
pub static APPLIED: AtomicU8 = AtomicU8::new(0);
#[embassy_executor::task]
pub async fn task(inputs: [InputPin;4]) {
    let mut debounce = Debounced::default();
    let mut previous = 0;
    loop {
        crate::remote::expire();
        let mut raw = 0;
        for (i,pin) in inputs.iter().enumerate() { if pin.is_low() { raw |= 1 << i; } }
        let stable = debounce.update(raw,3);
        HELD.store(stable,Ordering::Relaxed);
        if stable != previous {
            if EDGES.try_send(stable).is_err() {
                // Overflow discards stale history and preserves the current
                // release state, rather than leaving a button stuck down.
                while EDGES.try_receive().is_ok() {}
                let _ = EDGES.try_send(stable);
            }
            previous = stable;
        }
        embassy_time::Timer::after_millis(5).await;
    }
}
pub fn next() -> u8 {
    let raw = EDGES.try_receive().unwrap_or_else(|_|HELD.load(Ordering::Relaxed));
    APPLIED.store(raw,Ordering::Relaxed);
    raw
}
