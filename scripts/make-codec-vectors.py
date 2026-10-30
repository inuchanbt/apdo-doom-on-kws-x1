# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
import struct
from block_codec import encode
ROOT = Path(__file__).resolve().parents[1]
data = (ROOT/'vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT').read_bytes()
pages = [data[at:at+1024].ljust(1024,b'\0') for at in range(0,len(data),1024)]
encoded = [encode(page) for page in pages]
with (ROOT/'artifacts/codec-vectors.bin').open('wb') as output:
    output.write(struct.pack('<I',len(pages)))
    for raw,block in zip(pages,encoded):
        output.write(struct.pack('<H',len(block)))
        output.write(block)
        output.write(raw)
print(f'{len(pages)} pages, {sum(map(len,encoded))} encoded / {len(pages)*1024} raw bytes')
