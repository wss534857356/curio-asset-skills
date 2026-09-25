"""Create an actionable image-generation task; never generate or label an image as verified."""
from pathlib import Path
import argparse,hashlib,json,struct
ROOT=Path(__file__).resolve().parents[1]
def write(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def prepare(recipe,project,out,custom=None):
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True)
    if (out/'task.json').exists():raise FileExistsError('Use a new task directory to preserve the previous source and decisions')
    data=json.loads((ROOT/'assets/painting-recipes.json').read_text(encoding='utf-8'));r=custom or next((r for r in data['recipes'] if r['id']==recipe),None)
    if not r:raise ValueError('Unknown painting recipe; supported C01-C10')
    required=['id','name','ratio','baseline_scene_en','genuine','forged','change_type','roster','details']
    if any(k not in r for k in required):raise ValueError('Recipe requires '+', '.join(required))
    recipe=r['id'];r.setdefault('default_frame','walnut_plain');r.setdefault('legacy_canvas_role','candidate-genuine-reference')
    source=(Path(project).resolve()/r['legacy_canvas_relative']) if r.get('legacy_canvas_relative') else None
    w,h=map(int,r['ratio'].split(':'));width=round(1280*w/h);height=1280;custody=None
    if source and source.exists():
        raw=source.read_bytes();custody={'path':str(source),'sha256':hashlib.sha256(raw).hexdigest(),'role':r['legacy_canvas_role']}
        if raw[:8]==b'\x89PNG\r\n\x1a\n':width,height=struct.unpack('>II',raw[16:24])
    invariant='Keep the same animals, identities, anatomy, poses, gaze, clothing, background, camera, dimensions and oil-painting style except the explicit change. No frame, text, signature or watermark.'
    genuine=r['baseline_scene_en']+' '+data['canvas_suffix']+' Genuine requirement: '+r['genuine']+'.'
    if recipe=='C04':genuine+=' If using the old water image as reference, edit only jug mouth, stream and liquid in the receiving vessel to opaque creamy milk; preserve the rest.'
    forged='Edit the supplied VERIFIED GENUINE canvas image. '+invariant+' Change only: '+r['forged']+'. Genuine baseline: '+r['genuine']+'.'
    if r['change_type'] in ['add_person','remove_person']:forged+=' Count the principal characters exactly. '+json.dumps(r['details'],ensure_ascii=False)+' Shadows and reflections are not extra people.'
    if recipe in ['C01','C10']:forged+=' The changed jewellery is painted inside the artwork, not a physical object attached on top of the canvas.'
    if recipe=='C04':forged+=' Water is visibly transparent with a continuous stream and a transparent receiving pool, not an absent stream or white milk.'
    height_prompt='Using the selected canvas as registered reference, create a grayscale OIL PAINT RELIEF HEIGHT GUIDE with the exact composition and aspect. White is raised paint, black lower paint. Brush ridges follow painted forms. No lighting, shadows, perspective, frame or RGB normal colors. Do not turn bright garments or face highlights into thick paint by luminance.'
    prompts={'genuine':genuine,'forged_edit':forged,'height_guide':height_prompt}
    for name,text in prompts.items():(out/(name+'-prompt.txt')).write_text(text+'\n',encoding='utf-8')
    task={'schema_version':1,'id':r['id'],'name':r['name'],'status':'pending-image-generation-and-visual-review','source':custody,'expected_canvas_pixels':[width,height],'recipe':r,'prompts':prompts,'independent_axes':{'authenticity':['genuine','forged'],'condition':['clean','oily','repaired','oily-and-repaired']},'expected_difference':{'genuine':r['genuine'],'forged':r['forged'],'details':r['details']},'visual_checks':['Inspect the actual original and choose its correct role','Verify the one intended change','Check every unchanged animal and the declared roster','Verify the two canvases share framing and aspect','Check the height guide is relief, not luminance','Inspect material response under moving grazing light'],'completion':{'genuine_image':False,'forged_image':False,'pair_visual_review':False,'registered_materials':False,'runtime_cleaning':False}}
    write(out/'task.json',task)
    surface={'id':r['id'],'resolution':[width,height],'canvas_m':[.5*width/height,.5],'authenticity':'forged','seed':1907+int(hashlib.sha256(recipe.encode()).hexdigest()[:4],16),'height_guide':None,'pigment_height_m':.00018,'brush_strokes':180,'weave_spacing_m':.0018,'weave_height_m':.000016,'clean_amount':0,'oil':{'enabled':True,'center_uv':[.70,.25],'radius_uv':[.12,.09],'height_m':.000012,'opacity':.42},'repair':{'enabled':True,'start_uv':[.18,.20],'end_uv':[.39,.30],'bead_radius_m':.0025,'bead_height_m':.00055,'spacing_m':.0042},'preview':False}
    write(out/'surface.json',surface)
    write(out/'frame.json',{'id':r['id']+'_frame','preset':r['default_frame'],'canvas':{'height_m':.5,'aspect_ratio':width/height,'image_path':None,'fit':'contain'},'badge':{'placement':'none'},'render':True})
    return task
def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True);g.add_argument('--recipe');g.add_argument('--recipe-file',type=Path);p.add_argument('--project-root',type=Path,default=Path.cwd());p.add_argument('--out',required=True,type=Path);a=p.parse_args();custom=json.loads(a.recipe_file.read_text(encoding='utf-8')) if a.recipe_file else None;task=prepare(a.recipe,a.project_root,a.out,custom);print(json.dumps({'id':task['id'],'status':task['status'],'source_role':task['source']['role'] if task['source'] else None}))
if __name__=='__main__':main()
