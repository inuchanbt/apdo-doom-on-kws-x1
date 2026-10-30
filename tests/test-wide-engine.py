# SPDX-License-Identifier: GPL-2.0-or-later
"""Render the real engine through the exact firmware LCD mapper; no USB."""
import ctypes as C
from pathlib import Path
import struct
root=Path(__file__).resolve().parents[1]
engine=C.CDLL(str(root/'artifacts/host-engine/kmdoom-test.dll'))
lcd=C.CDLL(str(root/'artifacts/wide-output.dll'))
engine.km_host_display_callbacks.argtypes=[C.c_void_p,C.c_void_p]
engine.km_host_display_callbacks(lcd.wide_column,lcd.wide_palette)
engine.km_host_init.argtypes=[C.c_void_p,C.c_uint32]
engine.km_host_error.restype=C.c_char_p
pack=(root/'vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT').read_bytes()
data=C.create_string_buffer(pack)
assert engine.km_host_init(data,len(pack))==0,engine.km_host_error()
engine.km_host_horizontal_fov.restype=C.c_uint32
fov=engine.km_host_horizontal_fov()*360/2**32
assert 105<fov<108, fov
def save(name):
    pixels=(C.c_uint16*(240*135))()
    lcd.wide_rgb(pixels)
    # A 240x135 top-down RGB565 BMP, exactly what the panel receives.
    raw=bytes(pixels)
    header=struct.pack('<2sIHHI',b'BM',66+len(raw),0,0,66)
    header+=struct.pack('<IiiHHIIiiII',40,240,-135,1,16,3,len(raw),0,0,0,0)
    header+=struct.pack('<III',0xf800,0x07e0,0x001f)
    (root/f'artifacts/{name}.bmp').write_bytes(header+raw)
    # Both world edges must contain a scene rather than persistent sidebars.
    assert any(pixels[y*240] for y in range(112)), 'left edge stayed blank'
    assert any(pixels[y*240+239] for y in range(112)), 'right edge stayed blank'
for i in range(140):
    keys=(2 if 35<=i<70 else 0)|(8 if 70<=i<100 else 0)|(1 if 100<=i<125 else 0)
    assert engine.km_host_step(keys)==0,(i,engine.km_host_error())
    if i in (12,69,99,124):save(f'wide-frame-{i:03}')
engine.km_host_clear_and_redraw()
save('wide-redraw')
engine.km_host_hud_values(200,200,200)
for _ in range(3):assert engine.km_host_step(0)==0,engine.km_host_error()
save('wide-hud-200')
for key in (32,0):assert engine.km_host_step(key)==0,engine.km_host_error()
save('wide-menu')
print('PASS: real 140-frame wide LCD output, edge coverage, HUD redraw and menu capture')
