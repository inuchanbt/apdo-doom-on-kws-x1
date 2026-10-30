# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare real E1M1 frames/read traces and check cache boundaries against the pack."""
import argparse
import ctypes as C
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
import random

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--library', type=Path, default=root/'artifacts/host-engine/kmdoom-test.dll')
parser.add_argument('--reference', type=Path)
parser.add_argument('--report', type=Path, default=root/'artifacts/record-cache.json')
args = parser.parse_args()
dll = C.CDLL(str(args.library.resolve()))
dll.km_host_init.argtypes = [C.c_void_p, C.c_uint32]
dll.km_host_error.restype = C.c_char_p
dll.km_host_screen.restype = C.POINTER(C.c_uint16)
dll.km_host_trace.restype = C.POINTER(C.c_uint32)
dll.km_host_trace_count.restype = C.c_uint32
dll.km_host_read.argtypes = [C.c_uint32, C.c_void_p, C.c_uint32]
pack = (root/'vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT').read_bytes()
data = C.create_string_buffer(pack)
assert dll.km_host_init(data,len(pack)) == 0, dll.km_host_error()
hot = OrderedDict()
frames = []
for i in range(140):
    keys=(2 if 35<=i<70 else 0)|(8 if 70<=i<100 else 0)|(1 if 100<=i<125 else 0)
    dll.km_host_trace_reset()
    assert dll.km_host_step(keys) == 0, (i,dll.km_host_error())
    count = dll.km_host_trace_count()
    assert count < 262144, 'trace truncated'
    trace = dll.km_host_trace()
    total_bytes = decodes = 0
    for j in range(count):
        at,n = trace[j*2],trace[j*2+1]
        total_bytes += n
        if not n: continue
        for page in range(at//1024,(at+n-1)//1024+1):
            if page not in hot:
                decodes += 1
                if len(hot) == 8: hot.popitem(last=False)
                hot[page] = None
            hot.move_to_end(page)
    frames.append(dict(frame=i, reads=count, bytes=total_bytes, modeled_decodes=decodes,
        sha256=hashlib.sha256(C.string_at(dll.km_host_screen(),320*240*2)).hexdigest()))
if args.reference:
    reference = json.loads(args.reference.read_text())['frames']
    assert [f['sha256'] for f in frames] == [f['sha256'] for f in reference], 'cache changed rendered frames'
# Hit and miss reads at line boundaries, unaligned records, final partial line,
# long bypass reads, zero-length EOF and invalid requests that might hit a tag.
out = C.create_string_buffer(65)
rng = random.Random(460)
cases = [(at,n) for at in (0,1,15,16,1023,len(pack)-17,len(pack)-1,len(pack))
         for n in (0,1,2,15,16,17,65) if at+n <= len(pack)]
cases += [(rng.randrange(len(pack)-65),rng.randrange(66)) for _ in range(1000)]
for at,n in cases:
    assert dll.km_host_read(at,out,n) == 0, dll.km_host_error()
    assert out.raw[:n] == pack[at:at+n], (at,n)
for at,n in ((len(pack),1),(len(pack)-1,2),(0xffffffff,16)):
    assert dll.km_host_read(at,out,n) == -1, 'invalid read accepted'
summary = {key:sum(f[key] for f in frames[2:]) for key in ('reads','bytes','modeled_decodes')}
args.report.write_text(json.dumps(dict(summary=summary,frames=frames),indent=2)+'\n')
print(f'PASS: 140 frame hashes, {len(cases)} pack reads, EOF/bounds; {summary}')
