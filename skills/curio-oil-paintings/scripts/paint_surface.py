"""Registered technical PBR layers: paint, weave, independent oil and connected repair beads."""
from pathlib import Path
import argparse,json,math,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from pbr_core import grid,normal,png,smooth,material_set,read_height

def stroke_stamp(field,x,y,cx,cy,length,width,angle,amplitude,extent):
    dx,dy=extent[0]/field.shape[1],extent[1]/field.shape[0]
    rx=3*math.sqrt((length*math.cos(angle))**2+(width*math.sin(angle))**2);ry=3*math.sqrt((length*math.sin(angle))**2+(width*math.cos(angle))**2)
    x0=max(0,int((cx-rx)/dx));x1=min(field.shape[1],int((cx+rx)/dx)+1)
    y0=max(0,int((extent[1]-cy-ry)/dy));y1=min(field.shape[0],int((extent[1]-cy+ry)/dy)+1)
    if x0>=x1 or y0>=y1:return
    xx=x[y0:y1,x0:x1]-cx;yy=y[y0:y1,x0:x1]-cy
    along=xx*math.cos(angle)+yy*math.sin(angle);across=-xx*math.sin(angle)+yy*math.cos(angle)
    value=np.exp(-.5*((along/length)**2+(across/width)**2))*amplitude
    field[y0:y1,x0:x1]=np.maximum(field[y0:y1,x0:x1],value)

def build(spec,out,spec_dir=None):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    width,height=map(int,spec.get('resolution',[1024,1280]));extent=list(map(float,spec.get('canvas_m',[.4,.5])))
    if min(width,height)<32 or min(extent)<=0:raise ValueError('Positive physical dimensions and resolution >=32 required')
    if abs((width/height)/(extent[0]/extent[1])-1)>.015:raise ValueError('Material pixels and physical canvas aspect disagree; do not stretch painting maps')
    u,v=grid(width,height);x=u*extent[0];y=v*extent[1];rng=np.random.default_rng(int(spec.get('seed',1907)))
    pigment=np.zeros((height,width));guide=spec.get('height_guide');amp=float(spec.get('pigment_height_m',.00018))
    if guide:
        guide=Path(guide);guide=guide if guide.is_absolute() else Path(spec_dir or '.')/guide
        pigment=read_height(guide,[width,height])*amp;mode='registered-height-guide'
    else:
        for _ in range(int(spec.get('brush_strokes',180))):
            stroke_stamp(pigment,x,y,rng.uniform(0,extent[0]),rng.uniform(0,extent[1]),rng.uniform(.008,.026),rng.uniform(.0007,.0024),rng.normal(.35,.8),amp*rng.uniform(.25,1),extent)
        mode='generic-relief-preview-not-form-aware'
    spacing=float(spec.get('weave_spacing_m',.0018));pixel=max(extent[0]/width,extent[1]/height)
    attenuation=np.clip((spacing/pixel-2)/2,0,1)
    weave=(np.cos(2*np.pi*x/spacing)+np.cos(2*np.pi*y/spacing))*.25+.5
    weave*=float(spec.get('weave_height_m',.000016))*attenuation
    base=weave+pigment;rough=np.clip(.61-(pigment/max(amp,1e-12))*.10+(weave/max(float(spec.get('weave_height_m',.000016)),1e-12))*.05,.2,.9)
    material_set(out/'base',base,rough,*extent)
    png(out/'pigment-height.png',pigment/max(amp,1e-12),16);png(out/'weave-height.png',weave/max(float(spec.get('weave_height_m',.000016)),1e-12),16)
    oil=spec.get('oil',{});oil_mask=np.zeros_like(base);oil_height=np.zeros_like(base)
    if oil.get('enabled',False):
        cx,cy=oil.get('center_uv',[.70,.25]);rx,ry=oil.get('radius_uv',[.12,.09]);xx=(u-cx)/rx;yy=(v-cy)/ry;angle=np.arctan2(yy,xx)
        distance=np.hypot(xx,yy);edge=1+.10*np.sin(angle*5)+.065*np.cos(angle*9)
        oil_mask=np.clip((edge-distance)/.15,0,1);oil_mask=smooth(oil_mask,2);oil_height=oil_mask*float(oil.get('height_m',.000012))
    oil_dir=out/'layers/oil';oil_dir.mkdir(parents=True,exist_ok=True);png(oil_dir/'mask.png',oil_mask)
    rgba=np.empty((height,width,4));rgba[:,:,:3]=[.20,.115,.045];rgba[:,:,3]=oil_mask*float(oil.get('opacity',.42));png(oil_dir/'color.png',rgba)
    material_set(oil_dir,oil_height,np.full_like(base,.12),*extent)
    repair=spec.get('repair',{});repair_height=np.zeros_like(base);repair_mask=np.zeros_like(base);centres=[]
    if repair.get('enabled',False):
        start=np.array(repair.get('start_uv',[.18,.20]))*extent;end=np.array(repair.get('end_uv',[.39,.30]))*extent;delta=end-start;length=np.linalg.norm(delta)
        count=max(2,int(length/float(repair.get('spacing_m',.0042)))+1);radius=float(repair.get('bead_radius_m',.0025));height_m=float(repair.get('bead_height_m',.00055))
        direction=delta/max(length,1e-12);cross=np.array([-direction[1],direction[0]])
        # The continuous seam beneath the beads makes a connected repair, not scattered noise.
        t=np.clip(((x-start[0])*delta[0]+(y-start[1])*delta[1])/max(length*length,1e-12),0,1)
        distance=np.hypot(x-start[0]-t*delta[0],y-start[1]-t*delta[1]);repair_height=np.exp(-2*(distance/(radius*.60))**2)*height_m*.22
        for index in range(count):
            fraction=index/(count-1);center=start+fraction*delta+cross*radius*.22*math.sin(index*1.7);centres.append(center.tolist())
            bead=np.exp(-2*((x-center[0])**2+(y-center[1])**2)/radius**2)*height_m
            repair_height=np.maximum(repair_height,bead)
        repair_mask=np.clip(repair_height/(height_m*.20),0,1)
    repair_dir=out/'layers/repair';repair_dir.mkdir(parents=True,exist_ok=True);png(repair_dir/'mask.png',repair_mask)
    material_set(repair_dir,repair_height,np.full_like(base,.78),*extent)
    clean=float(spec.get('clean_amount',0))
    if not 0<=clean<=1:raise ValueError('clean_amount must be within [0,1]')
    effective_oil=oil_mask*(1-clean);composite=base+repair_height+oil_height*(1-clean)
    combined_rough=rough*(1-repair_mask)+.78*repair_mask;combined_rough=combined_rough*(1-effective_oil)+.12*effective_oil
    meta=material_set(out/'composite',composite,combined_rough,*extent)
    rgba[:,:,3]*=1-clean;png(out/'composite/oil-color.png',rgba)
    record={'id':spec.get('id','surface'),'authenticity':spec.get('authenticity','unspecified'),'mode':mode,'source_painting_pixels_modified':False,'clean_amount':clean,'base_height_range_m':[float(base.min()),float(base.max())],'oil_height_max_m':float(oil_height.max()),'repair_height_max_m':float(repair_height.max()),'repair_bead_centers_m':centres,'weave_attenuation_for_texel_density':float(attenuation),'maps':meta,'layers_independent':True,'dynamic_cleaning_implemented':False,'notes':['Art-directed physical amplitudes, not measurements of a historic painting','Color layer remains separate and must be composited with the chosen genuine or forged artwork','Generic mode does not infer brush direction from depicted faces or clothing']}
    (out/'surface-report.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if spec.get('preview'):preview(out,extent)
    return record

def preview(out,extent):
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    def texture(mat,path,data=False):
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path));tex.image.colorspace_settings.name='Non-Color' if data else 'sRGB';return tex
    for index,folder in enumerate(['base','composite']):
        mat=bpy.data.materials.new(folder);mat.use_nodes=True;bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Base Color'].default_value=(.34,.24,.13,1)
        normal_tex=texture(mat,out/folder/'normal.png',True);node=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(normal_tex.outputs['Color'],node.inputs['Color']);mat.node_tree.links.new(node.outputs['Normal'],bs.inputs['Normal'])
        mat.node_tree.links.new(texture(mat,out/folder/'roughness.png',True).outputs['Color'],bs.inputs['Roughness'])
        if folder=='composite':
            oil=texture(mat,out/folder/'oil-color.png');mix=mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.inputs[1].default_value=(.34,.24,.13,1);mat.node_tree.links.new(oil.outputs['Alpha'],mix.inputs[0]);mat.node_tree.links.new(oil.outputs['Color'],mix.inputs[2]);mat.node_tree.links.new(mix.outputs[0],bs.inputs['Base Color'])
        w,h=extent;x=(index-.5)*(w+.055);vertices=[(x-w/2,0,-h/2),(x+w/2,0,-h/2),(x+w/2,0,h/2),(x-w/2,0,h/2)]
        mesh=bpy.data.meshes.new(folder);mesh.from_pydata(vertices,[],[(0,1,2,3)]);mesh.update();uv=mesh.uv_layers.new(name='UVMap')
        for li,co in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=co
        ob=bpy.data.objects.new(folder,mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(mat)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.render.resolution_x=1200;scene.render.resolution_y=760;scene.render.resolution_percentage=100
    world=bpy.data.worlds.new('world');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[1].default_value=.12;scene.world=world
    data=bpy.data.lights.new('grazing key','AREA');data.energy=110;data.size=.30;light=bpy.data.objects.new('grazing key',data);scene.collection.objects.link(light)
    data=bpy.data.cameras.new('camera');cam=bpy.data.objects.new('camera',data);scene.collection.objects.link(cam);cam.location=(.1,-2,.15);cam.rotation_euler=(-cam.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=(extent[0]*2+.08)*1.13;scene.camera=cam
    for name,position in [('grazing-left',(-1,-.35,.5)),('grazing-right',(1,-.35,.5))]:
        light.location=position;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]);r=build(json.loads(a.spec.read_text(encoding='utf-8')),a.out,a.spec.parent);print(json.dumps({'id':r['id'],'mode':r['mode'],'layers_independent':True}))
if __name__=='__main__':main()
