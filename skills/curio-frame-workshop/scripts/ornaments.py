"""Authored vector heraldry and matching height fields, not photo-derived normals."""
from pathlib import Path
import json,math
import numpy as np
from pbr_core import grid,smooth,material_set

def primitives(family):
    # Coordinates are a square, x right and y up; negative features are engraved.
    e=lambda x,y,rx,ry,h=1:('ellipse',[x,y,rx,ry],h)
    p=lambda points,h=1:('polygon',points,h)
    line=lambda points,width,h=1:('line',[points,width],h)
    eyes=[e(.40,.48,.022,.025,-.6),e(.60,.48,.022,.025,-.6)]
    if family=='rabbit':return [e(.5,.42,.19,.23),e(.39,.76,.065,.21),e(.61,.76,.065,.21),e(.39,.78,.027,.145,-.55),e(.61,.78,.027,.145,-.55),*eyes,p([[.465,.34],[.535,.34],[.5,.30]],-.7),line([[.25,.18],[.35,.115],[.5,.09],[.65,.115],[.75,.18]],.025,.6)]
    if family=='wolf':return [p([[.2,.85],[.38,.73],[.62,.73],[.8,.85],[.78,.57],[.86,.42],[.67,.30],[.5,.16],[.33,.30],[.14,.42],[.22,.57]]),p([[.38,.47],[.62,.47],[.57,.25],[.5,.20],[.43,.25]],.5),line([[.31,.56],[.43,.52]],.023,-.7),line([[.57,.52],[.69,.56]],.023,-.7),p([[.44,.34],[.56,.34],[.5,.27]],-.7),line([[.5,.72],[.5,.62]],.02,-.5)]
    if family=='red_deer':
        shapes=[p([[.35,.64],[.65,.64],[.60,.37],[.50,.18],[.40,.37]]),p([[.35,.60],[.17,.69],[.22,.53],[.38,.50]]),p([[.65,.60],[.83,.69],[.78,.53],[.62,.50]]),*eyes,e(.5,.25,.048,.033,-.6)]
        for side in [-1,1]:
            tr=lambda pts:[[.5+side*x,y] for x,y in pts]
            shapes.extend([line(tr([[.12,.62],[.21,.75],[.25,.91],[.21,.98]]),.035),line(tr([[.21,.75],[.36,.82],[.41,.92]]),.03),line(tr([[.23,.84],[.32,.96]]),.023),line(tr([[.30,.79],[.40,.78]]),.022)])
        return shapes
    if family=='bear':return [e(.26,.69,.12,.12),e(.74,.69,.12,.12),e(.5,.49,.31,.30),e(.5,.34,.18,.13,.45),e(.26,.69,.054,.052,-.5),e(.74,.69,.054,.052,-.5),*eyes,e(.5,.39,.085,.054,-.7),line([[.5,.35],[.5,.29]],.018,-.5)]
    if family=='tiger':
        shapes=[e(.25,.72,.095,.10),e(.75,.72,.095,.10),p([[.24,.73],[.5,.82],[.76,.73],[.85,.48],[.69,.28],[.5,.19],[.31,.28],[.15,.48]]),e(.5,.34,.16,.10,.35),*eyes,p([[.45,.40],[.55,.40],[.5,.33]],-.7)]
        for y,w in [(.72,.11),(.65,.09),(.59,.065)]:shapes.append(line([[.5-w,y+.018],[.5,y-.012],[.5+w,y+.018]],.027,-.85))
        for s in [-1,1]:
            for y in [.54,.44,.35]:shapes.append(line([[.5+s*.27,y+.045],[.5+s*.18,y]],.025,-.8))
        return shapes
    raise ValueError('Unknown family '+family)

def mask(kind,args,x,y):
    if kind=='ellipse':
        cx,cy,rx,ry=args;return (((x-cx)/rx)**2+((y-cy)/ry)**2<=1).astype(float)
    if kind=='polygon':
        inside=np.zeros(x.shape,dtype=bool)
        for a,b in zip(args,args[1:]+args[:1]):
            if abs(b[1]-a[1])<1e-12:continue
            inside^=((a[1]>y)!=(b[1]>y))&(x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0])
        return inside.astype(float)
    points,width=args;distance=np.ones(x.shape)*10
    for a,b in zip(points,points[1:]):
        dx,dy=b[0]-a[0],b[1]-a[1];t=np.clip(((x-a[0])*dx+(y-a[1])*dy)/max(dx*dx+dy*dy,1e-12),0,1)
        distance=np.minimum(distance,np.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
    return (distance<=width).astype(float)

def outline(carrier):
    if carrier=='center':return [[-.45,.50],[.45,.50],[.48,.12],[.34,-.25],[0,-.50],[-.34,-.25],[-.48,.12]]
    if carrier=='edge':return [[0,.5],[.42,.29],[.46,-.26],[0,-.5],[-.46,-.26],[-.42,.29]]
    return [[-.38,.5],[.38,.5],[.5,.38],[.5,-.38],[.38,-.5],[-.38,-.5],[-.5,-.38],[-.5,.38]]

def badge_maps(family,carrier,out,res=512):
    aspect={'center':.92,'edge':.76,'corner':1}[carrier];width_m=.06;height_m=width_m/aspect
    u,v=grid(res,round(res/aspect));fraction={'center':.74,'edge':.66,'corner':.66}[carrier]
    x=(u-.5)/fraction+.5;y=(v-.5)/aspect/fraction+.5
    relief=np.zeros(u.shape);ink=np.zeros(u.shape)
    for kind,args,h in primitives(family):
        m=mask(kind,args,x,y)
        if h>0:relief=np.maximum(relief,m*h)
        else:relief+=m*h;ink=np.maximum(ink,m)
    relief=smooth(np.maximum(relief,0),3)
    # A restrained engraved carrier border, separate from the family symbol.
    edge=np.minimum.reduce([u,1-u,v,1-v]);border=np.exp(-((edge-.075)/.010)**2)*.13
    height=(relief+border)*.00065
    palettes={
        'rabbit':([.48,.48,.44],[.73,.72,.65]),
        'wolf':([.16,.18,.20],[.52,.56,.59]),
        'red_deer':([.43,.19,.12],[.67,.39,.21]),
        'bear':([.46,.32,.18],[.63,.48,.29]),
        'tiger':([.58,.41,.18],[.76,.62,.36])}
    low,high=map(np.array,palettes[family]);raised=np.clip(relief,0,1)[...,None]
    color=low+(high-low)*raised;color*=1-ink[...,None]*.42
    rough=.48-raw_clip(relief)*.09+ink*.13
    record=material_set(out,height,rough,width_m,height_m,color,.88)
    record.update(family=family,carrier=carrier,authored_vector_shapes=True,detail='height-driven shallow relief; animal does not affect plaque silhouette')
    Path(out,'material.json').write_text(json.dumps(record,indent=2)+'\n')
    return record

def raw_clip(a):return np.clip(a,0,1)

def svg(family,path):
    elements=[]
    for kind,args,h in primitives(family):
        color='#d8ba7d' if h>0 else '#332c24'
        if kind=='ellipse':
            x,y,rx,ry=args;elements.append(f'<ellipse cx="{x*256}" cy="{(1-y)*256}" rx="{rx*256}" ry="{ry*256}" fill="{color}"/>')
        elif kind=='polygon':elements.append('<polygon points="'+' '.join(f'{x*256},{(1-y)*256}' for x,y in args)+f'" fill="{color}"/>')
        else:
            points,width=args;elements.append('<polyline points="'+' '.join(f'{x*256},{(1-y)*256}' for x,y in points)+f'" fill="none" stroke="{color}" stroke-width="{width*512}" stroke-linecap="round" stroke-linejoin="round"/>')
    Path(path).write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><rect width="256" height="256" rx="24" fill="#332c24"/>'+''.join(elements)+'</svg>',encoding='utf-8')

def frame_maps(style,out,res=512):
    u,v=grid(res,res);wave=np.sin(2*np.pi*(v*23+.08*np.sin(2*np.pi*u*3)))
    fine=np.sin(2*np.pi*(v*89+.11*np.sin(2*np.pi*u*7)))
    grain=.5+.32*wave+.18*fine;noise=np.sin(2*np.pi*(u*67+v*43))*np.sin(2*np.pi*(u*37-v*71))
    palette={'walnut':[.29,.18,.10],'redwood':[.31,.105,.073],'ebon':[.070,.073,.069],'gilt':[.64,.48,.23]}
    base=np.array(palette[style])[None,None,:]*(.85+.23*grain[...,None]+.035*noise[...,None])
    height=grain*.000065+noise*.000008;rough=.56+.065*wave;metal=0
    if style=='gilt':
        seam=np.exp(-(np.sin(2*np.pi*u*4)/.045)**2)+np.exp(-(np.sin(2*np.pi*v*3)/.055)**2)
        leaves=(np.cos(2*np.pi*u*8)*np.sin(2*np.pi*v*3))**6
        height+=leaves*.00020-seam*.00007;base*=1-.08*seam[...,None];rough=.43+.07*wave+.1*seam;metal=.86
    record=material_set(out,height,rough,.20,.045,base,metal,tile=True);record['style']=style
    Path(out,'material.json').write_text(json.dumps(record,indent=2)+'\n');return record
