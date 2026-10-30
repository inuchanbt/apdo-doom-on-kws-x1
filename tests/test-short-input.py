# SPDX-License-Identifier: GPL-2.0-or-later
"""A tap at a full tic buffer must survive until a real game command is built."""
import ctypes as C
from pathlib import Path

root=Path(__file__).resolve().parents[1]
dll=C.CDLL(str(root/'artifacts/host-engine/kmdoom-test.dll'))
dll.km_host_init.argtypes=[C.c_void_p,C.c_uint32]
dll.km_host_input_script.argtypes=[C.c_void_p,C.c_uint32]
dll.km_host_step.argtypes=[C.c_uint32]
dll.km_host_build_tics.argtypes=[C.c_uint32]
dll.km_host_error.restype=C.c_char_p
pack=(root/'vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT').read_bytes()
data=C.create_string_buffer(pack)
assert dll.km_host_init(data,len(pack))==0,dll.km_host_error()
before=(dll.km_host_player_x(),dll.km_host_player_y())
# NetUpdate makes five commands, then polls again although its buffer is full.
# That sixth poll must leave the forward press and following release untouched.
states=(C.c_uint8*7)(0,0,0,0,0,2,0)
assert dll.km_host_input_script(states,len(states))==0
assert dll.km_host_build_tics(200)==0,dll.km_host_error()
assert dll.km_host_input_pending()==2,'full tic buffer consumed the queued short press'
for _ in range(3):
    assert dll.km_host_step(0)==0,dll.km_host_error()
after=(dll.km_host_player_x(),dll.km_host_player_y())
assert after!=before,'queued forward tap never moved the real player'
assert dll.km_host_input_pending()==0,'press/release did not reach real game tics'
print('PASS: full tic buffer preserves short press/release and the real player moves')
