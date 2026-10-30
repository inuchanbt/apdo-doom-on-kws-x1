// SPDX-License-Identifier: GPL-2.0-or-later
use core::{cell::RefCell,sync::atomic::{AtomicU8,Ordering}};
use embassy_sync::blocking_mutex::{Mutex,raw::CriticalSectionRawMutex};
static INPUT:Mutex<CriticalSectionRawMutex,RefCell<crate::control::Remote>>=Mutex::new(RefCell::new(crate::control::Remote::new()));
pub static APPLIED:AtomicU8=AtomicU8::new(0);
fn now()->u64 {embassy_time::Instant::now().as_millis()}
pub fn update(c:crate::control::Control) {INPUT.lock(|i|i.borrow_mut().update(c,now()));}
pub fn clear() {INPUT.lock(|i|i.borrow_mut().clear());APPLIED.store(0,Ordering::Relaxed);}
pub fn expire() {INPUT.lock(|i|i.borrow_mut().expire(now()));}
pub fn next()->u8 {let v=INPUT.lock(|i|i.borrow_mut().next(now()));APPLIED.store(v,Ordering::Relaxed);v}
