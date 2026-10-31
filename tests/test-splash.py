# SPDX-License-Identifier: GPL-2.0-or-later
"""Check actual production splash pixels against the verified original KM003C asset."""
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct

root=Path(__file__).resolve().parents[1]
image=(root/'overlays/firmware/freedoom-banner.bin').read_bytes()
meta=json.loads((root/'overlays/firmware/freedoom-banner.json').read_text())
assert hashlib.sha256(image).hexdigest()==meta['sha256']
w,h,n=struct.unpack_from('<HHH',image)
palette=struct.unpack_from(f'<{n}H',image,6)
indices=image[6+n*2:]
original=struct.pack('<HH',w,h)+b''.join(struct.pack('<H',palette[i]) for i in indices)
# Exact raw RGB565 hash of the original banner previously verified on KM003C.
assert hashlib.sha256(original).hexdigest()=='e045db13adc950717ba167b27a22871a600c872717b90afe001cd24ce6f579f5'
lcd=C.CDLL(str(root/'artifacts/wide-output.dll'))
lcd.wide_splash()
pixels=(C.c_uint16*(240*135))()
lcd.wide_rgb(pixels)
for y in range(135):
    for x in range(240):
        expected=0
        if 12<=x<228 and 42<=y<92:
            expected=palette[indices[(y-42)*37//50*159+(x-12)*159//216]]
        assert pixels[y*240+x]==expected,(x,y)
raw=bytes(pixels)
header=struct.pack('<2sIHHI',b'BM',66+len(raw),0,0,66)
header+=struct.pack('<IiiHHIIiiII',40,240,-135,1,16,3,len(raw),0,0,0,0)
header+=struct.pack('<III',0xf800,0x07e0,0x001f)
(root/'artifacts/startup-banner.bmp').write_bytes(header+raw)
print('PASS: original Freedoom logo pixels, exact palette, 216x50 centered on 240x135 LCD')
