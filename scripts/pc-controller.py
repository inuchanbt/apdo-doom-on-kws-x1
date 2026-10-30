# SPDX-License-Identifier: GPL-2.0-or-later
"""Loopback browser controls, preview, and assets on one KWS-X1 USB connection."""
import argparse
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import struct
import threading
import time
import webbrowser
import usb_link

ROOT=Path(__file__).resolve().parents[1]

def frame_bmp(image):
    width,height=image['width'],image['height']
    pixels=image['pixels']
    if (width,height)!=(120,90) or len(pixels)!=width*height*2:
        raise ValueError('Invalid captured frame')
    stride=(width*2+3)&~3
    raw=b''.join(pixels[y*width*2:(y+1)*width*2]+bytes(stride-width*2) for y in range(height))
    return (struct.pack('<2sIHHI',b'BM',66+len(raw),0,0,66)
        +struct.pack('<IiiHHIIiiII',40,width,-height,1,16,3,len(raw),0,0,0,0)
        +struct.pack('<III',0xf800,0x07e0,0x001f)+raw)

class Bridge:
    def __init__(self,port=None,stats=None,*,start=True,clock=time.monotonic):
        self.lock=threading.RLock()
        self.clock=clock
        self.port=port
        self.stats=stats
        self.token=secrets.token_urlsafe(32)
        self.stopped=threading.Event()
        self.preview_enabled=True
        self.last_preview=0.0
        self.connected=False
        self.protocol=4
        self.rotation=0
        self.connection_id=0
        self.last_seen=0.0
        self.record={}
        self.frame_times=deque(maxlen=32)
        self.screen=None
        self.bitmap=None
        self.snapshot_id=0
        self.last_image=0.0
        self.error='Waiting for KWS-X1 PC-control firmware (v4/v5).'
        self.pending=deque()
        self.buttons=0
        self.updated=0.0
        self.clear_requested=True
        self.worker=None
        if start:
            self.data=usb_link.load_pack(ROOT/'vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT')
            self.worker=threading.Thread(target=self.run,daemon=True)
            self.worker.start()

    def alive(self):
        return self.connected and self.clock()-self.last_seen<3 and not self.stopped.is_set()

    def release(self):
        with self.lock:
            self.buttons=0;self.pending.clear();self.clear_requested=True;self.updated=0.0
            return True

    def update(self,buttons):
        with self.lock:
            if not self.alive():
                self.release()
                return buttons==0
            if buttons!=self.buttons:
                if len(self.pending)>=32:
                    self.release();return False
                self.pending.append((self.clock(),buttons))
                self.buttons=buttons
            if buttons: self.clear_requested=False
            self.updated=self.clock()
            return True

    def control(self,record):
        with self.lock:
            now=self.clock()
            if self.stopped.is_set() or now-self.updated>=0.5:
                self.release()
            while self.pending and now-self.pending[0][0]>=0.5:
                self.pending.popleft()
            clear=self.clear_requested
            events=[]
            if not clear:
                while self.pending and len(events)<8: events.append(self.pending.popleft()[1])
            buttons=events[-1] if self.pending and events else self.buttons
            self.clear_requested=False
            preview=(self.preview_enabled and not self.stopped.is_set() and record['frame']>1 and now-self.last_preview>=1)
            if preview: self.last_preview=now
            return dict(buttons=buttons,events=events,clear=clear,preview=preview,lease_ms=750,rotation=self.rotation)

    def on_connected(self,version=4):
        with self.lock:
            self.release();self.connected=True;self.connection_id+=1;self.last_seen=self.clock()
            self.protocol=version;self.rotation=0
            self.record={};self.frame_times.clear();self.screen=None;self.bitmap=None
            self.last_preview=0.0;self.last_image=0.0;self.error=''

    def on_activity(self):
        with self.lock: self.last_seen=self.clock()

    def on_frame(self,record):
        with self.lock:
            self.last_seen=self.clock();self.record=dict(record)
            self.frame_times.append((self.clock(),record['frame']))

    def on_image(self,image):
        bitmap=frame_bmp(image)
        with self.lock:
            now=self.clock();self.snapshot_id+=1
            rate=1/(now-self.last_image) if self.last_image and now>self.last_image else 0
            self.last_image=now;self.bitmap=bitmap
            self.screen=dict(width=120,height=90,game_frame=image['game_frame'],snapshot=self.snapshot_id,preview_fps=rate)

    def set_preview(self,enabled):
        with self.lock:
            self.preview_enabled=enabled
            if enabled: self.last_preview=0.0
            return True

    def set_rotation(self,value):
        with self.lock:
            if self.protocol<5 or not self.alive(): return False
            self.release();self.rotation=value
            return True

    def snapshot(self):
        with self.lock:
            alive=self.alive()
            if not alive: self.release()
            fps=0.0
            if len(self.frame_times)>1:
                first,last=self.frame_times[0],self.frame_times[-1]
                if last[0]>first[0] and last[1]>=first[1]: fps=(last[1]-first[1])/(last[0]-first[0])
            return dict(connected=alive,connection_id=self.connection_id,reply=dict(self.record),render_fps=fps,
                preview_enabled=self.preview_enabled,screen=dict(self.screen) if alive and self.screen else None,
                error=self.error if not alive else '',buttons=self.buttons,
                display=dict(supported=self.protocol>=5,rotation=self.record.get('rotation',0),requested_rotation=self.rotation))

    def frame(self):
        with self.lock: return self.bitmap if self.alive() else None

    def run(self):
        while not self.stopped.is_set():
            try:
                port,version=usb_link.find_controller_port(1,self.port)
                usb_link.serve(port,self.data,version,self.stats,control=self.control,on_connected=lambda:self.on_connected(version),
                    on_frame=self.on_frame,on_image=self.on_image,on_activity=self.on_activity,stop=self.stopped)
            except Exception as error:
                with self.lock:
                    self.connected=False;self.release();self.screen=None;self.bitmap=None
                    self.error=f'{error}. Waiting for v4/v5; power-cycle the meter after USB loss.'
            if self.stopped.wait(1): break

    def close(self):
        self.release();self.stopped.set()
        if self.worker: self.worker.join(timeout=3)

def handler_for(bridge):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_): pass
        def valid_host(self): return self.headers.get('Host')==f'127.0.0.1:{self.server.server_port}'
        def respond(self,status,body,content_type='application/json'):
            if isinstance(body,dict): body=json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if not self.valid_host(): return self.respond(403,{'error':'Invalid host'})
            path=self.path.split('?',1)[0]
            if path=='/api/session': return self.respond(200,{'token':bridge.token})
            if path=='/api/status': return self.respond(200,bridge.snapshot())
            if path=='/api/frame.bmp':
                frame=bridge.frame()
                return self.respond(200,frame,'image/bmp') if frame else self.respond(404,{'error':'No captured frame yet'})
            assets={'/':('controller.html','text/html; charset=utf-8'),'/controller.js':('controller.js','text/javascript; charset=utf-8'),
                    '/controller.css':('controller.css','text/css; charset=utf-8'),
                    '/assets/kws-x1-shell.png':('assets/kws-x1-shell.png','image/png')}
            if path not in assets: return self.respond(404,{'error':'Not found'})
            name,mime=assets[path];return self.respond(200,(ROOT/'web'/name).read_bytes(),mime)
        def do_POST(self):
            try:
                self.connection.settimeout(2)
                length=int(self.headers.get('Content-Length','0'))
                body=self.rfile.read(min(max(length,0),4096))
                if (not self.valid_host() or self.headers.get('Origin')!=f'http://127.0.0.1:{self.server.server_port}'
                    or not secrets.compare_digest(self.headers.get('X-APDO-Token',''),bridge.token)):
                    return self.respond(403,{'error':'Invalid session'})
                if not 0<length<=64: raise ValueError()
                data=json.loads(body)
                if not isinstance(data,dict): raise ValueError()
                if self.path=='/api/keys':
                    value=data.get('buttons')
                    if set(data)!={'buttons'} or type(value) is not int or not 0<=value<=255: raise ValueError()
                    ok=bridge.update(value);return self.respond(200 if ok else 409,{'ok':ok})
                if self.path=='/api/preview':
                    if set(data)!={'enabled'} or type(data['enabled']) is not bool: raise ValueError()
                    return self.respond(200,{'ok':bridge.set_preview(data['enabled'])})
                if self.path=='/api/display':
                    value=data.get('rotation')
                    if set(data)!={'rotation'} or type(value) is not int or value not in (0,180): raise ValueError()
                    ok=bridge.set_rotation(value)
                    return self.respond(200 if ok else 409,{'ok':ok})
                if self.path=='/api/release':
                    if data: raise ValueError()
                    return self.respond(200,{'ok':bridge.release()})
                if self.path=='/api/stop':
                    if data: raise ValueError()
                    bridge.release();self.respond(200,{'ok':True})
                    threading.Thread(target=self.server.shutdown,daemon=True).start();return
                return self.respond(404,{'error':'Not found'})
            except (ValueError,TypeError,TimeoutError): return self.respond(400,{'error':'Invalid controller request'})
    return Handler

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--usb-port',help='Exact USB COM port; otherwise discover v4/v5')
    parser.add_argument('--port',type=int,default=0,help='Local HTTP port; default chooses a free port')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--session-file',type=Path)
    parser.add_argument('--stats',type=Path,default=ROOT/'artifacts/runtime-v4.jsonl')
    args=parser.parse_args()
    bridge=Bridge(args.usb_port,args.stats)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(bridge));server.daemon_threads=True
    try:
        url=f'http://127.0.0.1:{server.server_port}/'
        if args.session_file:
            args.session_file.parent.mkdir(parents=True,exist_ok=True)
            args.session_file.write_text(json.dumps(dict(url=url,pid=os.getpid()))+'\n')
        print(f'KWS-X1 controller: {url}',flush=True)
        print('Keep this server running. Release all pauses PC input; Stop server ends assets too.',flush=True)
        if not args.no_browser: webbrowser.open(url)
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt: pass
    finally:
        server.server_close();bridge.close()

if __name__=='__main__': main()
