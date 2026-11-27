import bpy,json,math,struct
from pathlib import Path
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
BASE=Path(__file__).resolve().parents[2]/'Assets/UPCH/Veterinaria';D=json.loads((BASE/'Datos/Modelo_H.json').read_text());P=D['parameters'];N=D['npt']
def yr(p):
 y=N[p['level']];h=N[p['level']+1]-y-P['slabThickness'] if p['level']<4 else P['roofWallHeight']
 return {'wall':(y,y+h),'slab':(y-P['slabThickness'],y),'sill':(y,y+P['windowSill']),'glass':(y+P['windowSill'],y+P['windowHead']),'windowFrameVertical':(y+P['windowSill']+.045,y+P['windowHead']-.045),'windowFrameBottom':(y+P['windowSill'],y+P['windowSill']+.045),'windowFrameTop':(y+P['windowHead']-.045,y+P['windowHead']),'windowLintel':(y+P['windowHead'],y+h),'doorLintel':(y+P['doorHeight'],y+h),'door':(y+.025,y+P['doorHeight']-.025),'beam':(y+h-P['beamDepth'],y+h),'railing':(y,y+P['railingHeight']),'roofCover':(y+P['roofWallHeight'],y+P['roofWallHeight']+.14)}.get(p['role'],(p['bottom'],p['top']))
colors={'wall':(.72,.70,.64,1),'floor':(.52,.57,.59,1),'metal':(.16,.22,.25,1),'glass':(.12,.16,.17,1)}
local={}
import re
needed={g for p in D['items'] for g in p.get('materialGuids',[p['materialGuid']])}
for path in (BASE.parents[2]/'Assets').rglob('*.mat'):
 meta=path.with_name(path.name+'.meta')
 if not meta.exists():continue
 guid=re.search(r'^guid: (\w+)',meta.read_text(),re.M)[1]
 if guid not in needed:continue
 m=re.search(r'_BaseColor: \{r: ([^,]+), g: ([^,]+), b: ([^,]+), a: ([^}]+)',path.read_text())
 if m:local[guid]=tuple(map(float,m.groups()[:3]))+(1,)
buckets={}
for p in D['items']:
 if p['hidden']:continue
 lo,hi=yr(p);v=p['vertices'];vs=[(v[k],-v[k+2],lo+(hi-lo)*v[k+1]) for k in range(0,len(v),3)]
 slots=p.get('materialGuids',[p['materialGuid']]);masks=p.get('triangleMaterials',[0]*(len(vs)//3))
 for j in range(0,len(vs),3):
  guid=slots[masks[j//3]];color=local.get(guid,colors[p['material']]);vertices,faces=buckets.setdefault((guid,color,p['material']),([],[]));base=len(vertices);vertices.extend(vs[j:j+3]);faces.append((base,base+1,base+2))
for (guid,color,kind),(vertices,faces) in buckets.items():
 mesh=bpy.data.meshes.new(guid);mesh.from_pydata(vertices,[],faces);mesh.update();ob=bpy.data.objects.new(guid,mesh);bpy.context.collection.objects.link(ob)
 mat=bpy.data.materials.new(guid);mat.diffuse_color=color;mat.use_nodes=True
 bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=color;bsdf.inputs['Roughness'].default_value=.65 if kind!='glass' else .18
 if kind=='metal':bsdf.inputs['Metallic'].default_value=.5
 ob.data.materials.append(mat)
# Render the actual protected campus terrain, not a plane below the basement.
scene_text=(BASE.parents[0]/'Scenes/Campus.unity').read_text()
blocks=re.split(r'(?=^--- !u!)',scene_text,flags=re.M)[1:]
ground_go=next(re.search(r'&(\d+)',b)[1] for b in blocks if b.startswith('--- !u!1 ') and re.search(r'  m_Name: [\"]?Terreno[\"]?\n',b))
trs={re.search(r'&(\d+)',b)[1]:b for b in blocks if b.startswith('--- !u!4 ')}
ground_tr=next(k for k,b in trs.items() if 'm_GameObject: {fileID: '+ground_go+'}' in b)
def world_translation(tid):
 if tid=='0':return Vector((0,0,0))
 t=trs[tid];m=re.search(r'm_LocalPosition: \{x: ([^,]+), y: ([^,]+), z: ([^}]+)',t);parent=re.search(r'm_Father: \{fileID: (\d+)\}',t)[1]
 return Vector(tuple(map(float,m.groups())))+world_translation(parent)
site_position=world_translation(ground_tr);anchor=Vector(D['anchor']);text=(BASE/'Generado/Terreno_Recortado_H.asset').read_text()
raw=bytes.fromhex(re.search(r'_typelessdata: (\w+)',text)[1]);ground_vertices=[]
for row in struct.iter_unpack('<8f',raw):
 point=Vector(row[:3])+site_position-anchor;ground_vertices.append((point.x,-point.z,point.y))
raw=bytes.fromhex(re.search(r'm_IndexBuffer: (\w+)',text)[1]);code='I' if 'm_IndexFormat: 1' in text else 'H';ind=struct.unpack('<'+code*(len(raw)//struct.calcsize(code)),raw);ground_faces=[tuple(ind[k:k+3]) for k in range(0,len(ind),3)]
mesh=bpy.data.meshes.new('Terreno_recortado_real');mesh.from_pydata(ground_vertices,[],ground_faces);mesh.update();ob=bpy.data.objects.new('Terreno_recortado_real',mesh);bpy.context.collection.objects.link(ob)
mat=bpy.data.materials.new('Suelo_campus');mat.diffuse_color=(.68,.70,.69,1);ob.data.materials.append(mat)

bpy.ops.object.light_add(type='AREA',location=(-12,-22,40));bpy.context.object.data.energy=16000;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=25
bpy.ops.object.light_add(type='SUN',location=(0,0,30));bpy.context.object.rotation_euler=(.4,-.5,-.6);bpy.context.object.data.energy=2
bpy.ops.object.camera_add(location=(48,78,45));cam=bpy.context.object;target=Vector((0,3,3.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=63;bpy.context.scene.camera=cam
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=False
scene.world.color=(.75,.75,.75);scene.render.resolution_x=1500;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(BASE/'Documentacion/Vistas/Vista_3D_H.png');scene.render.film_transparent=False

bpy.ops.render.render(write_still=True)
