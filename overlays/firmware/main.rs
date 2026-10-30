// SPDX-License-Identifier: GPL-2.0-or-later
#![no_std]
#![no_main]
mod panel;
mod upper;
mod usb;
mod stream;
mod game;
mod input;
mod codec;
mod page_cache;
mod pinned_assets;
mod usb_service;
mod control;
mod remote;
mod preview;
mod display;
use embassy_hc32::{gpio::{self, AlternateMode, AlternatePin, InputPin, Port}, intc};
use hc32f460_pac::interrupt;
use panic_halt as _;
static USB_EXECUTOR: embassy_executor::InterruptExecutor = embassy_executor::InterruptExecutor::new();
#[cortex_m_rt::interrupt]
fn INT031() { unsafe { USB_EXECUTOR.on_interrupt(); } }
#[cortex_m_rt::interrupt]
fn INT038() { embassy_hc32::dma::on_interrupt(panel::DMA_UNIT); }
#[cortex_m_rt::interrupt]
fn INT039() { embassy_hc32::dma::on_interrupt(panel::DMA_UNIT); }
#[cortex_m_rt::interrupt]
fn INT086() { embassy_hc32::spi::on_interrupt(); }
#[cortex_m_rt::interrupt]
fn INT087() { embassy_hc32::spi::on_interrupt(); }
#[cortex_m_rt::interrupt]
fn INT088() { embassy_hc32::spi::on_interrupt(); }
#[cortex_m_rt::exception]
fn SysTick() { embassy_hc32::time_driver::systick_tick(); }

#[embassy_executor::main]
async fn main(_spawner: embassy_executor::Spawner) {
    use embassy_hc32::clocks::{Config, Divider, Dividers, Mpll};
    unsafe {
        (0x40050804 as *mut u16).write_volatile(0x77);
        (0x4005080c as *mut u16).write_volatile(0x77);
        (0x40050800 as *mut u16).write_volatile(1 << 12 | 1 << 8);
        (0x40050804 as *mut u16).write_volatile(0x76);
        (0x4005080c as *mut u16).write_volatile(0x76);
        let scb = &*cortex_m::peripheral::SCB::PTR;
        scb.cpacr.modify(|v| v | 0xf << 20);
        let nvic = &*cortex_m::peripheral::NVIC::PTR;
        for (i, mask) in [!0u32, !0, !0, !0, 0xffff].iter().enumerate() { nvic.icer[i].write(*mask); }
        scb.vtor.write(firmware_core::APP_BASE);
        core::arch::asm!("dsb", "isb", options(nostack, preserves_flags));
        // DDL HRC monitor readback selects 16/20 MHz. Both profiles derive a
        // 384 MHz VCO, 192 MHz CPU and an exact nominal 48 MHz USB PLLR.
        let m = if (0x40010684 as *const u32).read_volatile() & 1 != 0 { 4 } else { 5 };
        let clocks = embassy_hc32::clocks::configure(Config {
            mpll: Mpll::new(m, 96, [2, 2, 8]).unwrap(),
            dividers: Dividers { hclk: Divider::Div1, exclk: Divider::Div2,
                pclk: [Divider::Div1, Divider::Div2, Divider::Div4, Divider::Div4, Divider::Div2] },
        }).unwrap();
        embassy_hc32::init(clocks);
        intc::clear_routes();
        cortex_m::interrupt::enable();
        assert!(upper::installed(), "upper engine region does not match build");
        gpio::release_jtag();
        let inputs = [InputPin::new_pull_up(Port::B, 2), InputPin::new_pull_up(Port::B, 10),
            InputPin::new_pull_up(Port::H, 0), InputPin::new_pull_up(Port::C, 14)];
        let mut backlight = embassy_hc32::pwm::TimerA4Pwm::new(hc32f460_pac::Tmra4::steal(), 7, 1875).unwrap();
        let backlight_pin = AlternatePin::new(Port::H, 2, 4, AlternateMode::DigitalOutput);
        backlight.start(900).unwrap();
        for (event, line) in [(panel::DMA_UNIT.complete_event(panel::DMA_CHANNEL).0, 38), (panel::DMA_UNIT.error_event().0, 39)] {
            intc::register(event, intc::Line::new(line).unwrap(), 8).unwrap();
        }
        assert!(panel::init(backlight_pin).await);
        let mut core = cortex_m::Peripherals::steal();
        core.NVIC.set_priority(interrupt::INT031, 0xa0);
        let usb_spawner = USB_EXECUTOR.start(interrupt::INT031);
        usb_spawner.spawn(usb_service::task().unwrap());
        usb_spawner.spawn(input::task(inputs).unwrap());
        game::run().await;
    }
}
