# SPDX-License-Identifier: GPL-2.0-or-later
"""Run the actual C engine against the mini pack; no device or USB required."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/mini'
dll=C.CDLL(str(OUT/'host-engine/kmdoom-test.dll'))
dll.km_host_init.argtypes=[C.c_void_p,C.c_uint32]
dll.km_host_step.argtypes=[C.c_uint32]
dll.km_host_error.restype=C.c_char_p
dll.km_host_screen.restype=C.POINTER(C.c_uint16)
dll.km_host_player_angle.restype=C.c_uint32
lcd=C.CDLL(str(OUT/'wide-output.dll'))
dll.km_host_display_callbacks.argtypes=[C.c_void_p,C.c_void_p]
dll.km_host_display_callbacks(lcd.wide_column,lcd.wide_palette)
pack=(OUT/'DOOM.DAT').read_bytes();data=C.create_string_buffer(pack)
assert dll.km_host_init(data,len(pack))==0,dll.km_host_error()
dll.km_host_horizontal_fov.restype=C.c_uint32
fov=dll.km_host_horizontal_fov()*360/2**32
assert 105<fov<108,fov
frames=0
def step(keys=0,count=1):
    global frames
    for _ in range(count):
        assert dll.km_host_step(keys)==0,dll.km_host_error()
        frames+=1
def frame():return C.string_at(dll.km_host_screen(),320*240*2)
def wide():
    pixels=(C.c_uint16*(240*135))();lcd.wide_rgb(pixels);return bytes(pixels)
def save_wide(name):
    raw=wide();pixels=memoryview(raw).cast('H')
    assert any(pixels[y*240] for y in range(112)),'left edge blank'
    assert any(pixels[y*240+239] for y in range(112)),'right edge blank'
    bmp=struct.pack('<2sIHHI',b'BM',66+len(raw),0,0,66)+struct.pack('<IiiHHIIiiII',40,240,-135,1,16,3,len(raw),0,0,0,0)+struct.pack('<III',0xf800,0x7e0,0x1f)+raw
    (OUT/name).write_bytes(bmp)
step(count=12);start=frame();ammo=dll.km_host_player_ammo()
save_wide('host-start-wide.bmp')
step(1,160)
assert dll.km_host_player_ammo()<ammo,'pistol did not consume ammo'
assert dll.km_host_player_kills()>=1,'pistol did not kill an arena enemy'
assert dll.km_host_player_health()>0,'player did not survive the functional test'
before=(dll.km_host_player_x(),dll.km_host_player_y());step(2,12)
assert (dll.km_host_player_x(),dll.km_host_player_y())!=before,'player did not move'
angle=dll.km_host_player_angle();step(8,8)
assert dll.km_host_player_angle()!=angle,'player did not turn'
step(0,2);step(32);step(0);assert dll.km_host_menu(),'menu did not open'
save_wide('host-menu-wide.bmp')
step(32);step(0);assert not dll.km_host_menu(),'menu did not close'
dll.km_host_redraw();hud=frame()[200*320*2:]
wide_hud=wide()[112*240*2:]
lcd.wide_clear()
dll.km_host_clear_and_redraw();assert frame()[200*320*2:]==hud,'full HUD redraw failed'
assert wide()[112*240*2:]==wide_hud,'indexed wide HUD redraw failed'
save_wide('host-frame-wide.bmp')
raw=frame();assert raw!=start,'scene did not change'
bmp=struct.pack('<2sIHHI',b'BM',66+len(raw),0,0,66)+struct.pack('<IiiHHIIiiII',40,320,-240,1,16,3,len(raw),0,0,0,0)+struct.pack('<III',0xf800,0x7e0,0x1f)+raw
(OUT/'host-frame.bmp').write_bytes(bmp)
report=dict(frames=frames,ammo=dll.km_host_player_ammo(),kills=dll.km_host_player_kills(),health=dll.km_host_player_health(),
    frame_sha256=hashlib.sha256(raw).hexdigest(),pack_sha256=hashlib.sha256(pack).hexdigest(),lcd=[240,135],horizontal_fov_degrees=fov,wide_frame_sha256=hashlib.sha256(wide()).hexdigest())
(OUT/'host-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('PASS: mini arena movement, turn, pistol ammo, enemy kill, menu and complete HUD redraw',report)
