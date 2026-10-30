// SPDX-License-Identifier: GPL-2.0-or-later
//! Display commands apply only at a game-frame boundary.
use core::sync::atomic::AtomicBool;
pub static DESIRED: AtomicBool = AtomicBool::new(false);
pub static APPLIED: AtomicBool = AtomicBool::new(false);
