# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare asset caches using real engine read traces; no USB access."""
import ctypes as C
import json
import struct
from collections import OrderedDict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
dll = C.CDLL(str(ROOT/'artifacts/host-engine/kmdoom-test.dll'))
dll.km_host_init.argtypes = [C.c_void_p, C.c_uint32]
dll.km_host_step.argtypes = [C.c_uint32]
dll.km_host_trace.restype = C.POINTER(C.c_uint32)
dll.km_host_trace_count.restype = C.c_uint32
dll.km_host_error.restype = C.c_char_p
pack = (ROOT/'vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT').read_bytes()
data = C.create_string_buffer(pack)
assert dll.km_host_init(data,len(pack)) == 0, dll.km_host_error()
traces = []
for frame in range(24):
    dll.km_host_trace_reset()
    assert dll.km_host_step(8 if frame >= 12 else 0) == 0, dll.km_host_error()
    count = dll.km_host_trace_count()
    assert count < 262144, 'trace truncated'
    trace = dll.km_host_trace()
    traces.append([(trace[i*2],trace[i*2+1]) for i in range(count)])
with (ROOT/'artifacts/cache-traces.bin').open('wb') as output:
    output.write(struct.pack('<I',len(traces)))
    for trace in traces:
        output.write(struct.pack('<I',len(trace)))
        for address,count in trace: output.write(struct.pack('<II',address,count))
results = []
for page in (256,512,1024,2048,4096):
    for capacity in (8192,16384,32768):
        for policy in ('FIFO','LRU'):
            cache = OrderedDict()
            misses = []
            for trace in traces:
                missed = 0
                for at,n in trace:
                    if not n: continue
                    for base in range(at//page*page, (at+n-1)//page*page+1, page):
                        if base in cache:
                            if policy == 'LRU': cache.move_to_end(base)
                        else:
                            missed += 1
                            if len(cache) == capacity//page: cache.popitem(last=False)
                            cache[base] = None
                misses.append(missed)
            results.append(dict(page=page,cache_bytes=capacity,policy=policy,
                mean_roundtrips=round(sum(misses[2:])/len(misses[2:]),1),
                mean_bytes=round(sum(misses[2:])*page/len(misses[2:])),per_frame=misses))
results.sort(key=lambda r:r['mean_roundtrips'])
(ROOT/'artifacts/cache-profile.json').write_text(json.dumps(results,indent=2)+'\n')
for result in results:
    print({k:v for k,v in result.items() if k!='per_frame'})
