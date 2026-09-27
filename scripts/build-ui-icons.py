"""Reproducible original line icons. Build-time standard library only."""
import math
from pathlib import Path
import struct
import zlib

SHAPES={
 'new':[[(5,5),(14,5)],[(5,5),(5,20),(20,20),(20,11)],[(10,14),(11,10),(19,2),(22,5),(14,13),(10,14)],[(17,4),(20,7)]],
 'more':[[(5,11),(5,13)],[(12,11),(12,13)],[(19,11),(19,13)]],
 'todo':[[(5,3),(19,3),(19,21),(5,21),(5,3)],[(8,8),(10,10),(15,6)],[(8,15),(16,15)],[(8,18),(13,18)]],
 'activity':[[(12,3),(18,5),(21,11),(19,17),(13,21),(6,19),(3,13),(4,7),(8,4)],[(12,7),(12,12),(16,14)]],
 'team':[[(8,4),(5,6),(5,10),(8,12),(11,10),(11,6),(8,4)],[(3,21),(3,17),(6,14),(10,14),(13,17),(13,21)],[(16,5),(19,7),(19,10),(16,12)],[(16,15),(19,15),(22,18),(22,21)]],
 'help':[[(12,3),(18,5),(21,11),(19,18),(12,21),(5,18),(3,11),(6,5),(12,3)],[(9,8),(10,6),(14,6),(16,9),(12,12),(12,14)],[(12,17),(12,18)]],
 'collapse':[[(3,4),(21,4),(21,20),(3,20),(3,4)],[(8,4),(8,20)],[(16,9),(13,12),(16,15)]],
 'expand':[[(3,4),(21,4),(21,20),(3,20),(3,4)],[(8,4),(8,20)],[(13,9),(16,12),(13,15)]],
 'chat':[[(4,4),(20,4),(20,16),(11,16),(6,21),(6,16),(4,16),(4,4)]],
 'query':[[(4,4),(20,4),(20,20),(4,20),(4,4)],[(4,9),(20,9)],[(10,9),(10,20)]],
 'work':[[(5,5),(8,8),(12,3)],[(14,6),(21,6)],[(5,13),(8,16),(12,11)],[(14,14),(21,14)],[(5,21),(21,21)]],
 'result':[[(5,3),(15,3),(20,8),(20,21),(5,21),(5,3)],[(15,3),(15,8),(20,8)],[(9,12),(16,12)],[(9,16),(16,16)]],
 'schedule':[[(4,5),(20,5),(20,21),(4,21),(4,5)],[(8,2),(8,8)],[(16,2),(16,8)],[(4,10),(20,10)],[(8,14),(11,14),(11,17),(8,17),(8,14)]],
 'notice':[[(5,17),(7,14),(7,8),(9,5),(15,5),(17,8),(17,14),(19,17),(5,17)],[(10,20),(14,20)]],
 'issue':[[(3,20),(12,3),(21,20),(3,20)],[(12,9),(12,14)],[(12,17),(12,18)]],
 'settings':[[(4,6),(20,6)],[(4,12),(20,12)],[(4,18),(20,18)],[(8,3),(8,9)],[(16,9),(16,15)],[(10,15),(10,21)]],
 'send':[[(3,3),(22,12),(3,21),(6,12),(3,3)],[(6,12),(16,12)]],
 'attach':[[(8,14),(15,7),(18,7),(19,10),(10,19),(6,19),(3,16),(3,12),(13,2),(18,2),(22,6),(22,11),(11,22)]]}

def png(paths,color,size=24):
    scale=4;pixels=[]
    paths=[[(x*size/24,y*size/24) for x,y in line] for line in paths]
    segments=[(a,b) for line in paths for a,b in zip(line,line[1:])]
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            count=0
            for sy in range(scale):
                for sx in range(scale):
                    px=x+(sx+.5)/scale;py=y+(sy+.5)/scale
                    for (ax,ay),(bx,by) in segments:
                        dx=bx-ax;dy=by-ay;t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/(dx*dx+dy*dy)))
                        if math.hypot(px-ax-t*dx,py-ay-t*dy)<=.8*size/24:count+=1;break
            pixels.extend((*color,round(255*count/(scale*scale))))
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(pixels)))+chunk(b'IEND',b'')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--names',nargs='+',choices=SHAPES)
    args=parser.parse_args();selected=args.names or SHAPES
    folder=Path(__file__).resolve().parents[1]/'desktop_app/assets/ui';folder.mkdir(exist_ok=True)
    for name,paths in SHAPES.items():
        if name not in selected:continue
        for variant,color in [('dark',(168,185,202)),('light',(76,96,112))]:
            if name=='send':color=(16,36,42) if variant=='dark' else (255,255,255)
            (folder/f'{name}-{variant}.png').write_bytes(png(paths,color))
            for size in (24,30,36,48,60,72,96):
                (folder/f'{name}-{variant}-{size}.png').write_bytes(png(paths,color,size))
    print(str(len(selected)*16)+' original multi-resolution PNG icons generated; no network or runtime dependencies.')
