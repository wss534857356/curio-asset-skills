"""Small NumPy/stdlib PBR helpers; arrays use top-to-bottom image rows."""
from pathlib import Path
import struct,zlib
import numpy as np

def png(path,pixels,bits=8):
    a=np.asarray(pixels);a=a[...,None] if a.ndim==2 else a
    height,width,channels=a.shape
    if channels not in (1,3,4):raise ValueError('PNG needs 1, 3 or 4 channels')
    if not np.all(np.isfinite(a)):raise ValueError('Non-finite image data')
    data=np.rint(np.clip(a,0,1)*((1<<bits)-1)).astype('>u2' if bits==16 else 'u1')
    def chunk(kind,body):return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
    raw=b''.join(b'\x00'+row.tobytes() for row in data)
    encoded=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,bits,{1:0,3:2,4:6}[channels],0,0,0))+chunk(b'IDAT',zlib.compress(raw,6))+chunk(b'IEND',b'')
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded)

def grid(width,height):
    u=(np.arange(width)+.5)/width;v=1-(np.arange(height)+.5)/height
    return np.meshgrid(u,v)

def normal(height_m,width_m,height_extent_m,tile=False):
    h=np.asarray(height_m,dtype=float)
    if min(width_m,height_extent_m)<=0:raise ValueError('Positive physical map extents required')
    dy,dx=height_extent_m/h.shape[0],width_m/h.shape[1]
    if tile:gy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*dy);gx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*dx)
    else:gy,gx=np.gradient(h,dy,dx)
    n=np.stack([-gx,gy,np.ones_like(h)],axis=-1)
    n/=np.linalg.norm(n,axis=-1,keepdims=True)
    return n*.5+.5

def smooth(a,iterations=2):
    for _ in range(iterations):
        p=np.pad(a,1,mode='edge');a=(p[1:-1,1:-1]*4+p[:-2,1:-1]+p[2:,1:-1]+p[1:-1,:-2]+p[1:-1,2:])/8
    return a

def material_set(out,height_m,roughness,width_m,height_extent_m,base_color=None,metallic=0,tile=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    h=np.asarray(height_m);lo=float(h.min());hi=float(h.max());span=max(hi-lo,1e-12)
    png(out/'height.png',(h-lo)/span,16);png(out/'normal.png',normal(h,width_m,height_extent_m,tile))
    png(out/'roughness.png',roughness)
    orm=np.stack([np.ones_like(h),np.clip(roughness,0,1),np.broadcast_to(metallic,h.shape)],axis=-1);png(out/'orm.png',orm)
    if base_color is not None:png(out/'basecolor.png',base_color)
    return {'height_min_m':lo,'height_max_m':hi,'extent_m':[width_m,height_extent_m],'pixels':[h.shape[1],h.shape[0]],'normal_convention':'tangent +Y, top-to-bottom PNG rows','color_space':{'basecolor':'sRGB','normal':'Non-Color','roughness':'Non-Color','orm':'Non-Color','height':'Non-Color'},'orm_channels':{'R':'occlusion=1 (not baked AO)','G':'roughness','B':'metallic'}}

def read_height(path,size):
    import bpy
    image=bpy.data.images.load(str(Path(path).resolve()),check_existing=False);image.colorspace_settings.name='Non-Color'
    w,h=image.size;pixels=np.empty(w*h*4,dtype=np.float32);image.pixels.foreach_get(pixels)
    a=pixels.reshape(h,w,4)[::-1,:,0].copy();bpy.data.images.remove(image)
    if (w,h)!=tuple(size):raise ValueError(f'Height guide must match {size}; received {(w,h)}. Register it explicitly; no silent stretch.')
    return a
