// SPDX-License-Identifier: GPL-2.0-or-later
//! 32 KiB compressed LRU cache, in two 16 KiB banks of 128-byte cells.
pub const CELLS: usize = 256;
pub const CELL_BYTES: usize = 128;
pub const BANK_BYTES: usize = 16_384;
pub const BANK_CELLS: usize = BANK_BYTES/CELL_BYTES;
const ENTRIES: usize = 128;
#[derive(Clone, Copy)]
pub struct Entry { pub tag: u32, pub cell: usize, pub len: usize, age: u32 }
const EMPTY: Entry = Entry { tag: u32::MAX, cell: 0, len: 0, age: 0 };
pub struct Cache { entries: [Entry; ENTRIES], used: [u64;4], clock: u32 }
impl Cache {
    pub const fn new() -> Self { Self { entries: [EMPTY; ENTRIES], used: [0;4], clock: 0 } }
    fn tick(&mut self) -> u32 { self.clock = self.clock.wrapping_add(1); self.clock }
    pub fn get(&mut self, tag: u32) -> Option<Entry> {
        let age = self.tick();
        let entry = self.entries.iter_mut().find(|e| e.tag == tag)?;
        entry.age = age;
        Some(*entry)
    }
    fn remove(&mut self, i: usize) {
        let entry = self.entries[i];
        if entry.tag != u32::MAX {
            let cells = entry.len.div_ceil(CELL_BYTES);
            for cell in entry.cell..entry.cell+cells { self.used[cell/64] &= !(1u64 << (cell%64)); }
            self.entries[i] = EMPTY;
        }
    }
    fn oldest(&self) -> usize {
        self.entries.iter().enumerate().filter(|(_,e)| e.tag != u32::MAX)
            .max_by_key(|(_,e)| self.clock.wrapping_sub(e.age)).unwrap().0
    }
    pub fn insert(&mut self, tag: u32, len: usize) -> Entry {
        assert!(tag != u32::MAX && len > 0 && len <= 1024);
        if let Some(i) = self.entries.iter().position(|e| e.tag == tag) { self.remove(i); }
        let cells = len.div_ceil(CELL_BYTES);
        loop {
            let free_cell = (0..CELLS).find(|&cell| {
                cell % BANK_CELLS + cells <= BANK_CELLS &&
                    (cell..cell+cells).all(|c|self.used[c/64] & (1u64 << (c%64)) == 0)
            });
            if let (Some(cell), Some(i)) = (free_cell, self.entries.iter().position(|e|e.tag == u32::MAX)) {
                let entry = Entry { tag, cell, len, age: self.tick() };
                self.entries[i] = entry;
                for c in cell..cell+cells { self.used[c/64] |= 1u64 << (c%64); }
                return entry;
            }
            self.remove(self.oldest());
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn all_cells_and_lru_eviction() {
        let mut cache = Cache::new();
        for tag in 0..128 { assert_eq!(cache.insert(tag,100).cell, tag as usize); }
        cache.get(0).unwrap();
        cache.insert(128,100);
        assert!(cache.get(0).is_some());
        assert!(cache.get(1).is_none());
    }
    #[test]
    fn mixed_sizes_never_overlap_or_cross_banks() {
        let mut cache = Cache::new();
        for tag in 0..1000 {
            cache.insert(tag, if tag%3==0 {1024} else {400});
            let mut used = [0u64;4];
            for entry in cache.entries.iter().filter(|e|e.tag != u32::MAX) {
                let n = entry.len.div_ceil(CELL_BYTES);
                assert!(entry.cell%BANK_CELLS+n <= BANK_CELLS);
                for cell in entry.cell..entry.cell+n {
                    let mask = 1u64 << (cell%64);
                    assert_eq!(used[cell/64] & mask,0);
                    used[cell/64] |= mask;
                }
            }
            assert_eq!(used,cache.used);
        }
    }
}
