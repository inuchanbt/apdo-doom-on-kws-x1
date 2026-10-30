# SPDX-License-Identifier: GPL-2.0-or-later
"""Build a tiny, original two-sector arena using licensed Freedoom artwork.

Only artifacts/mini is written. The PC-linked E1M1 pack and generated tables
are left intact. The resulting PWAD is map-only; converted assets are separate.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'vendor/dmc100-doom'))
sys.path.insert(0,str(ROOT/'scripts'))
from tools.conv import fetch,format as F,info,pack,plan,trig,upstream,wadread
from block_codec import encode

def wad_bytes(lumps,ident=b'PWAD'):
    payload=bytearray();directory=bytearray()
    for name,data in lumps:
        directory+=struct.pack('<ii8s',12+len(payload),len(data),name.encode().ljust(8,b'\0'))
        payload+=data
    return struct.pack('<4sii',ident,len(lumps),12+len(payload))+payload+directory

def arena(wall,floor,ceiling):
    name=lambda v:v.encode().ljust(8,b'\0')
    verts=[(-256,-192),(-256,192),(0,192),(256,192),(256,-192),(0,-192)]
    edges=[(0,1,0),(1,2,0),(2,3,1),(3,4,1),(4,5,1),(5,0,0),(5,2,1)]
    sides=[];lines=[]
    for i,(a,b,sector) in enumerate(edges):
        sides.append(struct.pack('<hh8s8s8sh',0,0,name(wall if i==6 else '-'),name('-'),name('-' if i==6 else wall),sector))
        lines.append(struct.pack('<HHHHhhh',a,b,4 if i==6 else 1,0,0,i,7 if i==6 else -1))
    sides.append(struct.pack('<hh8s8s8sh',0,0,name(wall),name('-'),name('-'),0))
    sectors=b''.join(struct.pack('<hh8s8shhh',0,h,name(floor),name(ceiling),light,0,0) for h,light in [(128,176),(144,208)])
    segspec=[(0,1,0,0),(1,2,1,0),(2,5,6,1),(5,0,5,0),(5,2,6,0),(2,3,2,0),(3,4,3,0),(4,5,4,0)]
    segs=bytearray()
    for a,b,line,side in segspec:
        x0,y0=verts[a];x1,y1=verts[b]
        angle=round(math.atan2(y1-y0,x1-x0)*32768/math.pi)
        if angle>=32768:angle-=65536
        segs+=struct.pack('<HHhHhh',a,b,angle,line,side,0)
    node=struct.pack('<hhhh8hHH',0,-192,0,384,192,-192,0,256,192,-192,-256,0,0x8001,0x8000)
    cols,rows=6,5;offset=4+cols*rows
    blockmap=struct.pack('<hhhh',-384,-320,cols,rows)+struct.pack('<30H',*[offset]*30)+struct.pack('<9h',0,0,1,2,3,4,5,6,-1)
    things=[(-144,0,0,1,7),(128,0,180,3004,7),(176,-96,180,3004,7),(-32,-112,0,2007,7),(-128,128,0,2011,7)]
    return [('THINGS',b''.join(struct.pack('<5h',*t) for t in things)),('LINEDEFS',b''.join(lines)),('SIDEDEFS',b''.join(sides)),
        ('VERTEXES',b''.join(struct.pack('<hh',*v) for v in verts)),('SEGS',bytes(segs)),('SSECTORS',struct.pack('<4H',4,0,4,4)),
        ('NODES',node),('SECTORS',sectors),('REJECT',b'\0'),('BLOCKMAP',blockmap)]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freedoom-zip',type=Path)
    parser.add_argument('--upstream-cache',type=Path,help='Optional verified-converter dumper cache for development')
    args=parser.parse_args()
    out=ROOT/'artifacts/mini';gen=out/'gen';gen.mkdir(parents=True,exist_ok=True)
    original,notices=fetch.extract(str(args.freedoom_zip) if args.freedoom_zip else None)
    base=wadread.Wad(original)
    texture_names={t[0] for t in wadread.textures(base)}
    wall=next(n for n in ('STARTAN3','BROWN1','STARTAN2') if n in texture_names)
    old_sectors=wadread.parse_sectors(base.map_lumps('E1M1')['SECTORS'])
    floor=old_sectors[0][2]
    ceiling=next(s[3] for s in old_sectors if s[3]!='F_SKY1')
    lumps=arena(wall,floor,ceiling)
    (out/'mini-arena.wad').write_bytes(wad_bytes([('E1M1',b''),*lumps]))
    # Override just E1M1. The converted image contains only this arena.
    merged=[(base.name(i),base.read(i)) for i in range(len(base.lumps))]
    merged += [('E1M1',b''),*lumps]
    source=wad_bytes(merged,b'IWAD');wad=wadread.Wad(source)
    up=json.loads(args.upstream_cache.read_text()) if args.upstream_cache else upstream.load()
    # Engine C names the full E1 actor roster even in discarded functions.
    # Retain those compatible code tables, while build_image prunes artwork
    # using only the actors actually placed in the arena.
    deh=wadread.dehacked(wad);inf,dense=info.build(base,up,deh)
    ctx=pack.Ctx(wad,source,notices,up,deh,inf,dense,plan.load_layout(None))
    # One front-facing artwork per frame; gameplay/animation states are kept.
    for sprite in ctx.frames:
        for frame in sprite:
            frame['rotate']=False;frame['lumps']=[frame['lumps'][0]]*8
    # The arena has no sky ceiling, but the format still requires a sky slot.
    sky=ctx.ts.list[ctx.ts.first['SKY1']]
    sky.width=sky.height=sky.w2=sky.sh=32;sky.log2_w=sky.log2_sh=5
    ctx.ts._cols[sky.num]=[(bytes([0])*32,[(0,bytes([0])*32)]) for _ in range(32)]
    # Reuse the neutral face for health/expression variants; retain dead face.
    face=wad.num('STFST00')
    for n in F.UI_NAMES:
        if n.startswith('STF') and n!='STFDEAD0':wad.last[n]=face
    excluded=tuple(n for n in F.UI_NAMES if n.startswith(('WI','AMMNUM')) or n in ('TITLEPIC','HELP1','CREDIT'))
    cfg=dict(pack.PACKS['E1M1'],base=1,mips=1,xshift=1,ui_exclude=excluded,ui_half=tuple(n for n in F.UI_NAMES if n.startswith('M_')))
    built=pack.build_image(ctx,'E1M1',cfg,{'half_monsters':True,'drop_demo':True})
    data,_,_=pack.finish(ctx,'E1M1',built)
    (out/'DOOM.DAT').write_bytes(data)
    ih,ic,_=info.emit(inf,dense,hashlib.sha256(source).digest())
    generated,_=trig.emit(trig.build(up,wad.lump('COLORMAP')),None)
    generated.update({'dmcdat.h':F.emit_header(),'info.h':ih,'info.c':ic})
    for n,text in generated.items():(gen/n).write_text(text,encoding='utf-8',newline='\n')
    blob=bytearray();offsets=[0];crcs=[]
    import zlib
    for at in range(0,len(data),1024):
        page=data[at:at+1024].ljust(1024,b'\0')
        blob+=encode(page);offsets.append(len(blob));crcs.append(zlib.crc32(page))
    (out/'mini-assets.bin').write_bytes(blob)
    rust='// SPDX-License-Identifier: GPL-2.0-or-later\n// Generated Freedoom-derived assets; see notices/freedoom-0.13.0.\n'
    rust+=f'pub const IMAGE_BYTES:u32={len(data)};\n#[unsafe(link_section=".upper.assets")]\nstatic DATA:[u8;{len(blob)}]=*include_bytes!("mini-assets.bin");\n'
    rust+='const OFFSETS:&[u32]=&['+','.join(map(str,offsets))+'];\n'
    rust+='const CRCS:&[u32]=&['+','.join(map(str,crcs))+'];\n'
    rust+='pub fn page(index:usize)->(&\'static [u8],u32) {let a=OFFSETS[index] as usize;let b=OFFSETS[index+1] as usize;(&DATA[a..b],CRCS[index])}\n'
    (out/'mini_assets.rs').write_text(rust,encoding='utf-8',newline='\n')
    report=dict(name='Mini arena',map_sectors=2,map_enemies=2,wall=wall,floor=floor,ceiling=ceiling,converted_bytes=len(data),
        compressed_bytes=len(blob),page_count=len(crcs),sha256=hashlib.sha256(data).hexdigest(),compressed_sha256=hashlib.sha256(blob).hexdigest(),sections=built.report['sections'],sprites=len(dense.sprite_list))
    (out/'size-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    lock_path=ROOT/'standalone/ASSET_LOCK.json'
    if lock_path.exists():
        lock=json.loads(lock_path.read_text(encoding='utf-8'))
        for key in ('converted_bytes','compressed_bytes','sha256','compressed_sha256'):
            if report[key]!=lock[key]:raise ValueError(f'Mini asset lock mismatch: {key}')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
