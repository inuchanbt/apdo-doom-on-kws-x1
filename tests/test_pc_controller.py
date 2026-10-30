# SPDX-License-Identifier: GPL-2.0-or-later
"""PC control boundaries and v4 multiplexing; no real keyboard or USB."""
import http.client
import importlib.util
import json
from pathlib import Path
import struct
import sys
import threading
import unittest
from unittest.mock import patch
import zlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import usb_link
spec=importlib.util.spec_from_file_location('pc_controller',ROOT/'scripts/pc-controller.py')
pc=importlib.util.module_from_spec(spec);spec.loader.exec_module(pc)

class InputTests(unittest.TestCase):
    def setUp(self):
        self.now=10.0;self.bridge=pc.Bridge(start=False,clock=lambda:self.now);self.bridge.on_connected()
    def test_short_tap_preserved_and_stale_input_cleared(self):
        self.assertTrue(self.bridge.update(1));self.assertTrue(self.bridge.update(0))
        c=self.bridge.control({'frame':2});self.assertEqual(c['events'],[1,0]);self.assertFalse(c['clear'])
        self.bridge.update(2);self.now+=0.501
        c=self.bridge.control({'frame':3});self.assertTrue(c['clear']);self.assertEqual(c['buttons'],0);self.assertEqual(c['events'],[])
    def test_explicit_release_discards_old_edges_and_reconnect_clears(self):
        self.bridge.update(2);self.bridge.release();self.assertTrue(self.bridge.control({'frame':2})['clear'])
        self.bridge.update(4);self.bridge.on_connected();self.assertEqual(self.bridge.control({'frame':3})['events'],[])
    def test_preview_throttle_and_pause_do_not_inject_keys(self):
        self.assertTrue(self.bridge.control({'frame':2})['preview'])
        self.now+=0.2;self.assertFalse(self.bridge.control({'frame':3})['preview'])
        self.bridge.set_preview(False);self.now+=2;self.assertFalse(self.bridge.control({'frame':4})['preview'])
        self.assertEqual(self.bridge.buttons,0)
    def test_render_rate_includes_preview_and_control_wait(self):
        self.bridge.on_frame({'frame':10,'frame_ms':100});self.now+=0.5
        self.bridge.on_frame({'frame':11,'frame_ms':100});self.assertEqual(self.bridge.snapshot()['render_fps'],2)

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.bridge=pc.Bridge(start=False);self.bridge.on_connected()
        self.server=pc.ThreadingHTTPServer(('127.0.0.1',0),pc.handler_for(self.bridge))
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':0.01});self.thread.start()
        self.origin=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def request(self,path,data=None,headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=2)
        try:
            actual={'Origin':self.origin,'X-APDO-Token':self.bridge.token,'Content-Type':'application/json'};actual.update(headers or {})
            connection.request('POST' if data is not None else 'GET',path,json.dumps(data) if data is not None else None,actual)
            response=connection.getresponse();return response.status,response.read()
        finally: connection.close()
    def test_input_release_and_preview(self):
        self.assertEqual(self.request('/api/keys',{'buttons':2})[0],200)
        self.assertEqual(self.request('/api/keys',{'buttons':0})[0],200)
        self.assertEqual([v for _,v in self.bridge.pending],[2,0])
        self.assertEqual(self.request('/api/release',{})[0],200);self.assertEqual(list(self.bridge.pending),[])
        self.assertEqual(self.request('/api/preview',{'enabled':False})[0],200);self.assertFalse(self.bridge.preview_enabled)
    def test_other_origins_sessions_and_hosts_cannot_send(self):
        for headers in ({'Origin':'https://example.com'},{'X-APDO-Token':''},{'Host':'example.com'}):
            self.assertEqual(self.request('/api/keys',{'buttons':1},headers)[0],403)
        self.assertEqual(list(self.bridge.pending),[])
    def test_invalid_masks_and_private_paths_rejected(self):
        for data in ({'buttons':True},{'buttons':256},{'buttons':-1},{'buttons':'2'},{'buttons':2,'extra':'x'},[]):
            self.assertEqual(self.request('/api/keys',data)[0],400)
        for path in ('/../local/tools.ps1','/local/tools.ps1','/artifacts/runtime.jsonl','/scripts/usb_link.py'):
            self.assertEqual(self.request(path)[0],404)
        self.assertEqual(self.request('/api/frame.bmp')[0],404)
    def test_frame_is_a_frozen_top_down_rgb565_bitmap(self):
        pixels=bytearray(b'\0\xf8'*(120*90))
        self.bridge.on_image(dict(width=120,height=90,game_frame=7,pixels=pixels))
        pixels[:2]=b'\0\0'
        status,body=self.request('/api/frame.bmp?snapshot=1')
        self.assertEqual(status,200);self.assertEqual(struct.unpack_from('<ii',body,18),(120,-90))
        self.assertEqual(struct.unpack_from('<III',body,54),(0xf800,0x07e0,0x001f));self.assertEqual(body[66:68],b'\0\xf8')

class FakePort:
    def __init__(self,stop): self.pending=bytearray();self.writes=[];self.stop=stop
    def __enter__(self): return self
    def __exit__(self,*_): pass
    def flush(self): pass
    def read(self,n):
        n=min(n,13,len(self.pending));out=bytes(self.pending[:n]);del self.pending[:n];return out
    def write(self,data):
        self.writes.append(bytes(data))
        if len(self.writes)==1:
            assert data==usb_link.HELLO4
            self.pending+=usb_link.HELLO4+b'GET2'+struct.pack('<III',1,0,1024)
        elif len(self.writes)==2:
            seq,address,length,crc,encoded=struct.unpack('<IIIII',data[:20]);assert (seq,address,length)==(1,0,1024)
            assert encoded==len(data)-20 and crc==zlib.crc32(bytes(1024))
            self.pending+=b'FRM4'+struct.pack('<11I',2,180,0,1,2,15000,100,0,0,0,21600)
        else:
            assert len(data)==36 and data[:4]==b'CTL4' and zlib.crc32(data[:32])==struct.unpack_from('<I',data,32)[0]
            pixels=b'\0\xf8'*(120*90)
            self.pending+=b'IMG4'+struct.pack('<IIIII',2,120,90,len(pixels),zlib.crc32(pixels))+pixels
            self.stop.set()
        return len(data)

class ProtocolTests(unittest.TestCase):
    def test_fragmented_asset_control_and_preview_share_one_port(self):
        stop=threading.Event();port=FakePort(stop);images=[];frames=[]
        with patch('serial.Serial',return_value=port):
            usb_link.serve('TEST',bytes(1024),4,None,control=lambda _:dict(buttons=2,events=[2,0],preview=True),
                on_frame=frames.append,on_image=images.append,stop=stop)
        self.assertEqual(len(port.writes),3);self.assertEqual(frames[0]['frame'],2)
        self.assertEqual(images[0]['pixels'][:2],b'\0\xf8')
    def test_control_bounds_and_preview_crc(self):
        for kwargs in ({'buttons':True},{'buttons':256},{'lease_ms':1},{'events':[1]*9},{'preview':1}):
            with self.assertRaises(ValueError): usb_link.control_packet(1,**kwargs)
        packet=usb_link.control_packet(7,buttons=2,events=[2,0],clear=False)
        self.assertEqual(len(packet),36);self.assertEqual(zlib.crc32(packet[:32]),struct.unpack_from('<I',packet,32)[0])
        class BadImage:
            payload=bytearray(b'IMG4'+struct.pack('<IIIII',1,120,90,21600,0)+bytes(21600))
            def read(self,n): out=bytes(self.payload[:n]);del self.payload[:n];return out
        with self.assertRaises(ValueError): usb_link.receive_image(BadImage(),1)

if __name__=='__main__': unittest.main()
