# SPDX-License-Identifier: GPL-2.0-or-later
"""Exercise asset framing, bounds, partial reads and EOF against the real pack."""
import importlib.util
from pathlib import Path
import struct
import zlib
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
spec = importlib.util.spec_from_file_location('serve_game', Path(__file__).resolve().parents[1]/'scripts/serve-game.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
data = m.load_pack(m.ROOT/'vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT')
for address in (0, 1024, 65536, len(data)//1024*1024):
    header, page = m.reply(data, b'READ'+struct.pack('<III', 73, address, 1024))
    assert struct.unpack('<IIII', header) == (73, address, 1024, zlib.crc32(page))
    assert page == data[address:address+1024].ljust(1024, b'\0')
    header,encoded = m.reply(data,b'GET2'+struct.pack('<III',73,address,1024))
    assert struct.unpack('<IIIII',header) == (73,address,1024,zlib.crc32(page),len(encoded))
    assert 0<len(encoded)<=1024
for request in (b'', b'FAIL'+bytes(12), b'READ'+struct.pack('<III', 0, 1, 1024),
                b'READ'+struct.pack('<III', 0, 0, 4096), b'READ'+struct.pack('<III', 0, 0xffffff00, 1024)):
    try: m.reply(data, request)
    except ValueError: pass
    else: raise AssertionError('invalid read accepted')
class Partial:
    def __init__(self, payload): self.payload = payload
    def read(self, n):
        n = min(n, 3)
        result, self.payload = self.payload[:n], self.payload[n:]
        return result
assert m.read_exact(Partial(m.HELLO), 16) == m.HELLO
stats = m.frame_stats(b'STAT'+struct.pack('<IIIII',17,250,4,200,150),1.75)
assert stats['frame']==17 and stats['fps']==4 and stats['buttons']==4
assert stats['misses']==200 and stats['usb_wait_ms']==150
stats3=m.frame_stats(b'STA3'+struct.pack('<IIIIIII',7,180,2,4,10,16000,250),2.5)
assert stats3['stack_free_bytes']==16000 and stats3['decoded_pages']==250
try: m.frame_stats(b'STAT'+bytes(10),0)
except ValueError: pass
else: raise AssertionError('truncated telemetry accepted')
try: m.read_exact(Partial(b'short'), 16)
except TimeoutError: pass
else: raise AssertionError('truncated packet accepted')
print('PASS: real pack hash, framing, bounds, partial reads, EOF padding and disconnect')
