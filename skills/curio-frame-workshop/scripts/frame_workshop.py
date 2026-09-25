"""Blender CLI: resizeable mouldings, PBR relief and independent heraldic badges."""
from pathlib import Path
import argparse,json,math,re,sys
import bpy,bmesh
import numpy as np
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from ornaments import frame_maps,badge_maps,outline,svg
PRESETS=json.loads((ROOT/'assets/frame-presets.json').read_text(encoding='utf-8'))
HERALDRY=json.loads((ROOT/'assets/heraldry.json').read_text(encoding='utf-8'))

def write(path,data):Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def empty(name,parent=None,**props):
    ob=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(ob);ob.parent=parent
    for k,v in props.items():ob[k]=v
    return ob
def part(root,name,label,direction):return empty(name,root,part_id=name,label=label,explode_direction=direction,explode_distance=.35)
def mesh(name,vertices,faces,parent,mat,uv=None):
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update()
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.parent=parent;me.materials.append(mat)
    layer=me.uv_layers.new(name='UVMap')
    if uv:
        for loop in me.loops:layer.data[loop.index].uv=uv[loop.vertex_index]
    return ob
def box(name,center,size,parent,mat):
    vertices=[tuple(center[k]+s[k]*size[k]/2 for k in range(3)) for s in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    return mesh(name,vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],parent,mat)
def material(name,folder=None,color=(.18,.13,.07),metal=0,rough=.5):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough
    if folder:
        def tex(file,data=False):
            node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(Path(folder)/file),check_existing=True)
            node.image.colorspace_settings.name='Non-Color' if data else 'sRGB';node.image.pack();node.extension='REPEAT';return node
        if (Path(folder)/'basecolor.png').exists():mat.node_tree.links.new(tex('basecolor.png').outputs['Color'],bs.inputs['Base Color'])
        nm=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(tex('normal.png',True).outputs['Color'],nm.inputs['Color']);mat.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        channels=mat.node_tree.nodes.new('ShaderNodeSeparateColor');mat.node_tree.links.new(tex('orm.png',True).outputs['Color'],channels.inputs['Color'])
        mat.node_tree.links.new(channels.outputs['Green'],bs.inputs['Roughness']);mat.node_tree.links.new(channels.outputs['Blue'],bs.inputs['Metallic'])
    return mat
def image_material(path):
    mat=material('painting_image',rough=.72);bs=mat.node_tree.nodes['Principled BSDF'];tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(Path(path).resolve()),check_existing=True);tex.image.pack();mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);return mat,list(tex.image.size)

def bar(root,side,w,h,b,profile,mat):
    vertices=[];uv=[];arc=0.;prior=None
    # Each cross-section ring has its own mitred endpoint; no nonuniform mesh scale.
    for offset,depth in profile:
        if prior is not None:arc+=math.hypot(offset-prior[0],depth-prior[1])*b
        prior=(offset,depth);o=offset*b;y=depth*b;gap=.00010
        pairs=[((-w/2-o+gap,y,h/2+o),(w/2+o-gap,y,h/2+o)),((w/2+o,y,h/2+o-gap),(w/2+o,y,-h/2-o+gap)),((w/2+o-gap,y,-h/2-o),(-w/2-o+gap,y,-h/2-o)),((-w/2-o,y,-h/2-o+gap),(-w/2-o,y,h/2+o-gap))]
        a,z=pairs[side];vertices.extend([a,z]);length=Vector(z)-Vector(a)
        uv.extend([(0,arc/.045),(length.length/.20,arc/.045)])
    n=len(profile);faces=[(2*i,2*i+1,2*((i+1)%n)+1,2*((i+1)%n)) for i in range(n)]+[tuple(range(0,2*n,2)),tuple(reversed(range(1,2*n,2)))]
    parent=next((p for p in root.children if p.get('part_id')=='frame_'+str(side)),None)
    if parent is None:parent=part(root,'frame_'+str(side),['上框条','右框条','下框条','左框条'][side],[(0,0,1),(1,0,0),(0,0,-1),(-1,0,0)][side])
    return mesh('moulding_'+str(side),vertices,faces,parent,mat,uv)

def plaque(root,family,carrier,name,center,width,mat):
    height=width/HERALDRY['carriers'][carrier]['aspect'];thickness=width*.045;poly=outline(carrier);n=len(poly)
    vertices=[(center[0]+x*width,center[1]+y,center[2]+z*height) for y in [0,thickness] for x,z in poly]
    # Polygon faces are planar; shallow symbol relief is a true normal texture.
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    uv=[(x+.5,z+.5) for _ in range(2) for x,z in poly]
    parent=part(root,name,HERALDRY['families'][family]['label']+' · '+HERALDRY['carriers'][carrier]['label'],(0,-1,0))
    parent['family']=family;parent['carrier']=carrier;parent['anchor_position']=list(center);parent['emblem_upright']=True
    return mesh(name+'_plate',vertices,faces,parent,mat,uv)

def render(out,root):
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
    scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX'
    world=bpy.data.worlds.new('studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.18,.19,.21,1);world.node_tree.nodes['Background'].inputs[1].default_value=.32;scene.world=world
    for name,position,power in [('key',(-2,-3,3),240),('fill',(2,-1,1),90),('rim',(0,2,3),180)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=2;ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=position;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('camera');cam=bpy.data.objects.new('camera',data);scene.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO'
    pts=np.array([list(o.matrix_world@Vector(p)) for o in root.children_recursive if o.type=='MESH' for p in o.bound_box]);target=Vector(((pts.min(0)+pts.max(0))/2).tolist())
    for view,offset in [('front',(0,-3,0)),('hero',(1.15,-3,.9))]:
        cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
        p=np.array([list(cam.matrix_world.inverted()@Vector(v)) for v in pts]);data.ortho_scale=max(np.ptp(p[:,0]),np.ptp(p[:,1]))*1.15
        scene.render.filepath=str(out/(view+'.png'));bpy.ops.render.render(write_still=True)

def build(spec,out):
    if not re.fullmatch(r'[A-Za-z0-9_-]+',spec['id']):raise ValueError('id must be a filename-safe identifier')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    preset=PRESETS['presets'][spec['preset']];canvas=spec['canvas'];ratio=float(canvas.get('aspect_ratio',.8));image=canvas.get('image_path');paint_mat=None
    if image:paint_mat,pixels=image_material(image);ratio=pixels[0]/pixels[1]
    h=float(canvas.get('height_m') or float(canvas['width_m'])/ratio);w=float(canvas.get('width_m') or h*ratio)
    if min(w,h)<=0:raise ValueError('Canvas dimensions must be positive')
    if canvas.get('fit','contain')!='contain':raise ValueError('This generator preserves the full image; prepare an explicitly requested crop separately')
    b=float(spec.get('border_m') or np.clip(min(w,h)*preset['border_fraction'],*PRESETS['border_limits_m']))
    if spec.get('profile_mode','proportional')=='physical' and not spec.get('border_m'):b=.035
    if b<=0:raise ValueError('Positive moulding width required')
    res=int(spec.get('maps_resolution',512));maps=out/'maps';fm=maps/'frame';frame_maps(preset['material'],fm,res)
    timber=material('frame_surface',fm);backmat=material('linen_backing',color=(.19,.16,.11),rough=.86)
    trim=material('trim',color=(.46,.43,.36) if preset['material']=='ebon' else (.28,.16,.055),metal=.82,rough=.37)
    root=empty(spec['id'],asset_id=spec['id'],units='metres',front_axis='-Y',canvas_width_m=w,canvas_height_m=h)
    for side in range(4):bar(root,side,w,h,b,preset['profile'],timber)
    if preset['material'] in ['gilt','ebon']:
        def front_at(offset):
            hits=[];profile=preset['profile']
            for a,z in zip(profile,profile[1:]+profile[:1]):
                if min(a[0],z[0])<=offset<=max(a[0],z[0]) and abs(z[0]-a[0])>1e-12:
                    t=(offset-a[0])/(z[0]-a[0]);hits.append(a[1]+t*(z[1]-a[1]))
            return min(hits)
        a,z=.065,.125;offsets=sorted({a,z,*[p[0] for p in preset['profile'] if a<p[0]<z]})
        trim_profile=[(o,front_at(o)+.008) for o in offsets]+[(o,front_at(o)-.025) for o in reversed(offsets)]
        for side in range(4):bar(root,side,w,h,b,trim_profile,trim)
    crown=0
    if preset['crown']:
        crown=min(w*.17,h*.15);parent=part(root,'crown','独立拱冠',(0,0,1));width=w+2*b
        front=[(-width/2,0,h/2+b)]+[(width/2*math.cos(math.pi-i*math.pi/24),0,h/2+b+crown*math.sin(i*math.pi/24)) for i in range(1,25)]
        vertices=[(x,y+dy,z) for dy in [-b*.4,b*.2] for x,y,z in front];n=len(front)
        mesh('arch_crown',vertices,[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],parent,timber,[(x/.2,z/.045) for _ in range(2) for x,_,z in front])
    back=part(root,'backing','独立背板',(0,1,0));box('backing',(0,.008,0),(w+.006,.009,h+.006),back,backmat)
    paint=part(root,'canvas','完整画芯',(0,-1,0));pw=min(w,h*ratio);ph=pw/ratio
    if paint_mat is None:paint_mat=material('canvas_unpainted',color=(.43,.36,.25),rough=.79)
    mesh('canvas_front',[(-pw/2,-.002,-ph/2),(pw/2,-.002,-ph/2),(pw/2,-.002,ph/2),(-pw/2,-.002,ph/2)],[(0,1,2,3)],paint,paint_mat,[(0,0),(1,0),(1,1),(0,1)])
    badge=spec.get('badge',{});layout=badge.get('placement','none');anchors=[]
    if layout not in HERALDRY['placements']:raise ValueError('Unknown badge placement')
    if layout!='none':
        family=badge['family'];carrier={'edge_centers':'edge','top_center':'center','canvas_center':'center','four_corners':'corner'}[layout]
        size=float(badge.get('size_m') or (.060 if carrier=='center' else b*.78))
        if carrier in ['edge','corner']:size=min(size,b*.74*HERALDRY['carriers'][carrier]['aspect'])
        folder=maps/('badge_'+family+'_'+carrier);badge_maps(family,carrier,folder,res);mat=material('heraldry_'+family,folder)
        yy=-b*.82;bh=size/HERALDRY['carriers'][carrier]['aspect']
        if layout=='edge_centers':anchors=[(-w/2-b/2,yy,0),(w/2+b/2,yy,0)]
        elif layout=='four_corners':anchors=[(sx*(w/2+b/2),yy,sz*(h/2+b/2)) for sx,sz in [(-1,1),(1,1),(1,-1),(-1,-1)]]
        elif layout=='top_center':anchors=[(0,yy,h/2+b+crown+bh/2-min(b,bh)*.25)]
        else:anchors=[(0,yy,0)]
        for i,point in enumerate(anchors):plaque(root,family,carrier,'badge_'+str(i),point,size,mat)
    bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');root.select_set(True)
    for ob in root.children_recursive:ob.select_set(True)
    glb=out/(spec['id']+'.glb');bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_extras=True,export_animations=False,export_cameras=False,export_lights=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(spec['id']+'.blend')))
    # Compute after explicit tessellation, not an estimate from profile length.
    count=0
    for o in root.children_recursive:
        if o.type=='MESH':o.data.calc_loop_triangles();count+=len(o.data.loop_triangles)
    report={'id':spec['id'],'preset':spec['preset'],'canvas_m':[w,h],'painted_image_m':[pw,ph],'image_aspect':ratio,'frame_border_m':b,'texture_repeat_m':[.20,.045],'canvas_uv':'complete [0,1]','badge_layout':layout,'badge_anchors_m':anchors,'triangles':count,'glb':str(glb),'parts':[{'name':o.name,'label':o['label']} for o in root.children_recursive if o.get('part_id')],'material_sources':'authored procedural height and color; not image-generated artwork','spec':spec}
    write(out/'build-report.json',report)
    if spec.get('render',False):render(out,root)
    return report

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spec',type=Path);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--kit',action='store_true');parser.add_argument('--badges-only',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if args.badges_only:
        records=[];args.out.mkdir(parents=True,exist_ok=True)
        for family in HERALDRY['families']:
            svg(family,args.out/(family+'.svg'))
            for carrier in HERALDRY['carriers']:
                bpy.ops.wm.read_factory_settings(use_empty=True);folder=args.out/(family+'_'+carrier);record=badge_maps(family,carrier,folder,512)
                id=family+'_'+carrier;root=empty(id,asset_id=id,units='metres');mat=material(id,folder)
                obj=plaque(root,family,carrier,id+'_part',(0,0,0),.06,mat);bpy.context.view_layer.update()
                bpy.ops.export_scene.gltf(filepath=str(folder/(id+'.glb')),export_format='GLB',export_extras=True,export_animations=False,export_cameras=False,export_lights=False)
                bpy.ops.wm.save_as_mainfile(filepath=str(folder/(id+'.blend')));obj.data.calc_loop_triangles()
                record.update(id=id,triangles=len(obj.data.loop_triangles),width_m=.06,glb=id+'.glb');write(folder/'badge-report.json',record);records.append(record)
        write(args.out/'badge-library.json',{'badges':records})
    elif args.kit:
        records=[]
        for preset,family,layout,ratio in [('walnut_plain','rabbit','edge_centers',.8),('gilt_cove','wolf','top_center',.75),('abbey_crown','red_deer','top_center',.75),('ebon_silver','tiger','four_corners',.8),('gilt_cove','bear','four_corners',1.6)]:
            spec={'id':preset+'_'+family,'preset':preset,'canvas':{'height_m':.5,'aspect_ratio':ratio},'badge':{'family':family,'placement':layout},'maps_resolution':512,'render':True};records.append(build(spec,args.out/spec['id']))
        library=args.out/'heraldry';library.mkdir(parents=True,exist_ok=True)
        for family in HERALDRY['families']:
            svg(family,library/(family+'.svg'))
            for carrier in HERALDRY['carriers']:badge_maps(family,carrier,library/(family+'_'+carrier),512)
        write(args.out/'kit.json',{'frames':records,'families':HERALDRY,'presets':PRESETS})
    else:
        if not args.spec:parser.error('--spec or --kit required')
        spec=json.loads(args.spec.read_text(encoding='utf-8'));path=spec.get('canvas',{}).get('image_path')
        if path and not Path(path).is_absolute():spec['canvas']['image_path']=str((args.spec.parent/path).resolve())
        build(spec,args.out)

if __name__=='__main__':main()
