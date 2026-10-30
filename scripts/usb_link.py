# SPDX-License-Identifier: GPL-2.0-or-later
"""Serve read-only Freedoom pages to native DOOM on a KWS-X1 USB CDC link."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import time
import zlib
from block_codec import encode

ROOT = Path(__file__).resolve().parents[1]
PACK_SIZE = 2_802_000
PACK_SHA256 = '6b25a4f1adb6f1f1f5f42226c272b93ccff4f356ac8d7034cf83712b2da70c08'
PAGE = 1024
HELLO = b'X1DOOM01' + struct.pack('<I', PACK_SIZE)
HELLO += struct.pack('<I', zlib.crc32(HELLO))
HELLO2 = b'X1DOOM02' + struct.pack('<I', PACK_SIZE)
HELLO2 += struct.pack('<I', zlib.crc32(HELLO2))
HELLO3 = b'X1DOOM03' + struct.pack('<I', PACK_SIZE)
HELLO3 += struct.pack('<I', zlib.crc32(HELLO3))
HELLO4 = b'X1DOOM04' + struct.pack('<I',PACK_SIZE)
HELLO4 += struct.pack('<I',zlib.crc32(HELLO4))

def control_packet(frame, *, buttons=0, events=(), preview=False, clear=False, lease_ms=750):
    if (type(frame) is not int or not 0<=frame<=0xffffffff or type(buttons) is not int or not 0<=buttons<=255
            or type(lease_ms) is not int or not 100<=lease_ms<=1000 or len(events)>8
            or type(preview) is not bool or type(clear) is not bool
            or any(type(v) is not int or not 0<=v<=255 for v in events)):
        raise ValueError('Invalid PC input frame')
    body=b'CTL4'+struct.pack('<IIIII',frame,buttons,lease_ms,int(preview)|(2 if clear else 0),len(events))+bytes(events).ljust(8,b'\0')
    return body+struct.pack('<I',zlib.crc32(body))

def receive_image(port, frame):
    header=read_exact(port,24)
    if header[:4]!=b'IMG4': raise ValueError('Missing capture header')
    number,width,height,length,crc=struct.unpack('<IIIII',header[4:])
    if (number,width,height,length)!=(frame,120,90,21600): raise ValueError('Invalid capture dimensions or frame')
    pixels=read_exact(port,length)
    if zlib.crc32(pixels)!=crc: raise ValueError('Capture CRC mismatch')
    return dict(game_frame=number,width=width,height=height,pixels=pixels)

def load_pack(path):
    data = Path(path).read_bytes()
    if len(data) != PACK_SIZE or hashlib.sha256(data).hexdigest() != PACK_SHA256:
        raise ValueError('Expected the pinned Freedoom 0.13.0 E1M1 pack')
    return data

def reply(data, request, encoded_pages=None):
    if len(request) != 16 or request[:4] not in (b'READ',b'GET2'):
        raise ValueError('Invalid game data request')
    seq, address, count = struct.unpack('<III', request[4:])
    if count != PAGE or address % PAGE or address >= len(data):
        raise ValueError('Game data request outside the pack')
    page = data[address:address+count].ljust(PAGE, b'\0')
    if request[:4] == b'GET2':
        encoded = encoded_pages[address//PAGE] if encoded_pages is not None else encode(page)
        return struct.pack('<IIIII',seq,address,count,zlib.crc32(page),len(encoded)),encoded
    return struct.pack('<IIII', seq, address, count, zlib.crc32(page)), page

def read_exact(port, count):
    data = bytearray()
    while len(data) < count:
        part = port.read(count-len(data))
        if not part:
            raise TimeoutError('KWS-X1 data link timed out')
        data += part
    return bytes(data)

def frame_stats(packet, elapsed):
    if (len(packet),packet[:4]) not in ((24,b'STAT'),(32,b'STA3'),(48,b'FRM4')):
        raise ValueError('Invalid frame telemetry')
    number,ms,keys,misses,wait_ms = struct.unpack('<IIIII',packet[4:24])
    result = dict(frame=number,frame_ms=ms,fps=round(1000/max(1,ms),2),buttons=keys,
        misses=misses,usb_wait_ms=wait_ms,host_elapsed_s=round(elapsed,3))
    if packet[:4] in (b'STA3',b'FRM4'):
        result['stack_free_bytes'],result['decoded_pages'] = struct.unpack('<II',packet[24:32])
    if packet[:4]==b'FRM4':
        result['remote_buttons'],result['applied_buttons'],menu,result['preview_bytes'] = struct.unpack('<IIII',packet[32:])
        result['menu_active']=bool(menu)
    return result

def serve(port_name, data, version, stats_path, *, control=None,on_frame=None,on_image=None,on_connected=None,on_activity=None,stop=None):
    import serial
    # CDC ignores the baud rate. This serves data only and has no flash commands.
    with serial.Serial(port_name, 115200, timeout=30, write_timeout=10) as port:
        # Windows may consume the device's first greeting before COM open.
        # Send our exact identity first; firmware verifies it before any read.
        hello = {1:HELLO,2:HELLO2,3:HELLO3,4:HELLO4}[version]
        encoded_pages = [encode(data[at:at+PAGE].ljust(PAGE,b'\0')) for at in range(0,len(data),PAGE)] if version>=2 else None
        port.write(hello)
        port.flush()
        first = read_exact(port, 16)
        pending = None if first == hello else first
        if pending is not None:
            reply(data, pending,encoded_pages)
        print('Connected. The KWS-X1 runs the game; this PC serves read-only assets.', flush=True)
        if on_connected: on_connected()
        requests = 0
        started = time.monotonic()
        if stats_path:
            stats_path.parent.mkdir(parents=True,exist_ok=True)
        while True:
            request = pending if pending is not None else read_exact(port, 16)
            pending = None
            if on_activity: on_activity()
            if request[:4] in (b'STAT',b'STA3',b'FRM4'):
                tail={b'STAT':8,b'STA3':16,b'FRM4':32}[request[:4]]
                record = frame_stats(request+read_exact(port,tail),time.monotonic()-started)
                if on_frame: on_frame(record)
                if request[:4]==b'FRM4':
                    command=control_packet(record['frame'],**(control(record) if control else {'clear':True}))
                    port.write(command)
                    if struct.unpack_from('<I',command,16)[0]&1:
                        image=receive_image(port,record['frame'])
                        if on_image: on_image(image)
                    if stop is not None and stop.is_set(): return
                number,ms,keys,misses,wait_ms = [record[k] for k in ('frame','frame_ms','buttons','misses','usb_wait_ms')]
                if stats_path:
                    with stats_path.open('a',encoding='utf-8') as log: log.write(json.dumps(record)+'\n')
                if number <= 3 or number%10==0:
                    print(f"frame {number}: {ms} ms, {record['fps']} fps, {misses} reads, USB wait {wait_ms} ms, buttons {keys:04b}",flush=True)
                continue
            header, page = reply(data, request,encoded_pages)
            port.write(header + page)
            requests += 1
            if requests % 1000 == 0:
                print(f'{requests} game-data pages served', flush=True)

def find_port(wait_seconds,version=3):
    from serial.tools import list_ports
    deadline = time.monotonic() + wait_seconds
    while True:
        matches = [p.device for p in list_ports.comports()
                   if p.device and p.vid == 0xc0de and p.pid == 0xd00d and p.serial_number == ('KWSX1DOOM04' if version>=4 else 'KWSX1DOOM01')]
        if len(matches) == 1:
            print(f'Found KWS-X1 DOOM on {matches[0]}', flush=True)
            return matches[0]
        if len(matches) > 1:
            raise ValueError('Multiple DOOM devices; select an exact --port')
        if time.monotonic() >= deadline:
            raise TimeoutError('KWS-X1 DOOM USB port did not appear')
        time.sleep(0.25)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', help='Exact Windows COM port of the DOOM application')
    parser.add_argument('--auto', action='store_true', help='Wait for the exact DOOM USB identity')
    parser.add_argument('--wait', type=float, default=60, help='Maximum automatic discovery wait in seconds')
    parser.add_argument('--version',type=int,choices=(1,2,3,4),default=4,help='Protocol of the installed firmware')
    parser.add_argument('--stats',type=Path,default=ROOT/'artifacts/runtime.jsonl',help='Frame telemetry log')
    parser.add_argument('--pack', type=Path, default=ROOT/'vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT')
    parser.add_argument('--check', action='store_true', help='Validate pack offline, without USB discovery')
    args = parser.parse_args()
    data = load_pack(args.pack)
    if args.check:
        print(f'PASS: {len(data)} bytes, SHA-256 {PACK_SHA256}; no device accessed')
        return
    if not args.port and not args.auto:
        parser.error('--port or --auto is required unless --check is used')
    serve(args.port or find_port(args.wait,args.version), data,args.version,args.stats)

if __name__ == '__main__':
    main()
