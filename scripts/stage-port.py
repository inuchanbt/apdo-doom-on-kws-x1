# SPDX-License-Identifier: GPL-2.0-or-later
"""Apply the KWS-X1 DOOM adapter to the pinned board source, without USB I/O."""
from pathlib import Path
import shutil
import subprocess
import json
import hashlib
import argparse

ROOT = Path(__file__).resolve().parents[1]
CHECK = argparse.ArgumentParser(description=__doc__)
CHECK.add_argument('--check',action='store_true',help='Verify staged files without writing or accessing USB')
CHECK = CHECK.parse_args().check
OVERLAY = ROOT/'overlays/firmware'
BOARD = ROOT / 'vendor/kws-x1-standalone-rs'
REVISION = '517c5a9bf3fa9bda0be8f9ade435b108e588ad82'
assert subprocess.check_output(['git', '-C', str(BOARD), 'rev-parse', 'HEAD'], text=True).strip() == REVISION
lock=json.loads((ROOT/'SOURCE_LOCK.json').read_text())
if 'pinned_game_pages' in lock:
    blob=(OVERLAY/'game_pages.bin').read_bytes()
    assert len(blob)==lock['pinned_game_pages']['bytes']
    assert hashlib.sha256(blob).hexdigest()==lock['pinned_game_pages']['sha256'], 'Pinned game asset hash mismatch'
STATE = ROOT / 'artifacts/staged-hashes.json'
previous = json.loads(STATE.read_text()) if STATE.exists() else {}
managed = set()
def matches_previous(path):
    return previous.get(path) == hashlib.sha256((BOARD/path).read_bytes()).hexdigest()

def original(path):
    return subprocess.check_output(['git', '-C', str(BOARD), 'show', f'HEAD:{path}']).decode()

def edited(path, source):
    target = BOARD / path
    # Only replace a clean upstream file or the exact previously staged result.
    current = target.read_text(encoding='utf-8')
    assert current in (original(path), source) or matches_previous(path), f'Unrecognized local changes: {target}'
    if CHECK:
        assert current==source, f'Staged file differs: {target}'
    else:
        target.write_text(source, encoding='utf-8', newline='\n')
    managed.add(path)

for file in sorted([*OVERLAY.glob('*.rs'),*OVERLAY.glob('*.bin')]):
    if file.name == 'main.rs':
        edited('firmware/src/main.rs', file.read_text())
    else:
        target = BOARD / 'firmware/src' / file.name
        if target.exists():
            assert target.read_bytes() == file.read_bytes() or matches_previous('firmware/src/'+file.name), f'Conflicting overlay: {target}'
        if CHECK:
            assert target.exists() and target.read_bytes()==file.read_bytes(), f'Missing or changed overlay: {target}'
        else:
            shutil.copyfile(file, target)
        managed.add('firmware/src/'+file.name)

cargo = original('firmware/Cargo.toml') + '''
embassy-futures = "0.1.2"
embassy-usb = "0.6.0"
embassy-usb-synopsys-otg = { git = "https://github.com/embassy-rs/embassy.git", rev = "c2413d5994bbd8b7e6d5975fd49e6427cb903a02", version = "0.4.0" }
static_cell = "2.1.1"
'''
edited('firmware/Cargo.toml', cargo)
workspace = original('Cargo.toml') + '''
[patch.crates-io]
embassy-time = { git = "https://github.com/embassy-rs/embassy.git", rev = "c2413d5994bbd8b7e6d5975fd49e6427cb903a02" }
embassy-time-driver = { git = "https://github.com/embassy-rs/embassy.git", rev = "c2413d5994bbd8b7e6d5975fd49e6427cb903a02" }
embassy-time-queue-utils = { git = "https://github.com/embassy-rs/embassy.git", rev = "c2413d5994bbd8b7e6d5975fd49e6427cb903a02" }
embassy-executor-timer-queue = { git = "https://github.com/embassy-rs/embassy.git", rev = "c2413d5994bbd8b7e6d5975fd49e6427cb903a02" }
embassy-sync = { git = "https://github.com/embassy-rs/embassy.git", rev = "c2413d5994bbd8b7e6d5975fd49e6427cb903a02" }
embassy-usb = { git = "https://github.com/embassy-rs/embassy.git", rev = "c2413d5994bbd8b7e6d5975fd49e6427cb903a02" }
embassy-usb-driver = { git = "https://github.com/embassy-rs/embassy.git", rev = "c2413d5994bbd8b7e6d5975fd49e6427cb903a02" }
'''
edited('Cargo.toml', workspace)
edited('Cargo.lock', (ROOT / 'locks/board.Cargo.lock').read_text())
build = original('firmware/build.rs').replace('    Ok(())', '''    let engine = PathBuf::from(env::var_os("KWS_ENGINE_LIB").expect("set KWS_ENGINE_LIB"));
    println!("cargo:rustc-link-search=native={}", engine.display());
    println!("cargo:rustc-link-lib=static=kmdoom");
    println!("cargo:rerun-if-env-changed=KWS_ENGINE_LIB");
    println!("cargo:rerun-if-changed={}", engine.join("libkmdoom.a").display());
    Ok(())''')
edited('firmware/build.rs', build)
memory = original('firmware/memory.x').replace('    __supper = .;', '    __supper = .;\n    *(.text.P_* .text.R_*);\n    *(.upper.assets);')
edited('firmware/memory.x', memory)
edited('firmware/src/panel.rs', original('firmware/src/panel.rs') + '\ninclude!("panel_extension.rs");\n')
packer = original('firmware-pack/src/main.rs').replace('const CUSTOM_IRQS: [usize; 16] = [\n    1, 4, 13, 31, 38, 39, 40, 41, 86, 87, 88, 110, 111, 112, 113, 116,\n];',
    'const CUSTOM_IRQS: [usize; 7] = [4, 31, 38, 39, 86, 87, 88];')
assert packer != original('firmware-pack/src/main.rs')
packer = packer.replace('    let record = Packed {', '''    // Place streams at the earliest sector boundary that never erases unread
    // compressed main bytes. The identical unpacker rehearsal remains mandatory.
    let mut data_offset = unpacker_bytes;
    let mut placement_window = vec![0; WINDOW_BYTES];
    let placement_window: &mut [u8; WINDOW_BYTES] = placement_window.as_mut_slice().try_into()?;
    inflate_sectors(&main_packed, placement_window, |chunk| {
        let required = (chunk.offset + SECTOR_BYTES as usize)
            .saturating_sub(upper_packed.len() + chunk.consumed);
        data_offset = data_offset.max(required);
        true
    }).map_err(|error| anyhow::anyhow!("Planning unpack placement: {error:?}"))?;
    data_offset = data_offset.next_multiple_of(SECTOR_BYTES as usize);
    let record = Packed {''',1)
packer = packer.replace('unpacker_bytes.next_multiple_of(size_of::<u32>())','data_offset')
edited('firmware-pack/src/main.rs', packer)
fixture = original('firmware-pack/tests/cli.rs').replace('const CUSTOM_IRQS: [usize; 16] = [\n    1, 4, 13, 31, 38, 39, 40, 41, 86, 87, 88, 110, 111, 112, 113, 116,\n];',
    'const CUSTOM_IRQS: [usize; 7] = [4, 31, 38, 39, 86, 87, 88];')
edited('firmware-pack/tests/cli.rs', fixture)
if not CHECK:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({p:hashlib.sha256((BOARD/p).read_bytes()).hexdigest() for p in sorted(managed)},indent=2)+'\n')
print(('Verified' if CHECK else 'Staged')+' KWS-X1 native DOOM port; no device accessed')
