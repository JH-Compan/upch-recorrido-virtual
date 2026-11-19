import bpy,json,math
from pathlib import Path
from mathutils import Vector
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
BASE=Path(__file__).resolve().parents[2]/'Assets/UPCH/Veterinaria';D=json.loads((BASE/'Datos/Modelo_H.json').read_text());P=D['parameters'];N=D['npt']
def yr(p):
 y=N[p['level']];h=N[p['level']+1]-y-P['slabThickness'] if p['level']<4 else P['roofWallHeight']
 return {'wall':(y,y+h),'slab':(y-P['slabThickness'],y),'sill':(y,y+P['windowSill']),'glass':(y+P['windowSill'],y+P['windowHead']),'windowLintel':(y+P['windowHead'],y+h),'doorLintel':(y+P['doorHeight'],y+h),'door':(y+.025,y+P['doorHeight']-.025),'beam':(y+h-P['beamDepth'],y+h),'railing':(y,y+P['railingHeight']),'roofCover':(y+P['roofWallHeight'],y+P['roofWallHeight']+.14)}.get(p['role'],(p['bottom'],p['top']))
colors={'wall':(.72,.70,.64,1),'floor':(.52,.57,.59,1),'metal':(.16,.22,.25,1),'glass':(.12,.16,.17,1)}
local={}
import re
for path in (BASE/'Materiales').glob('*.mat'):
 guid=re.search(r'^guid: (\w+)',path.with_name(path.name+'.meta').read_text(),re.M)[1]
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
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-4.82));mat=bpy.data.materials.new('base');mat.diffuse_color=(.85,.87,.86,1);bpy.context.object.data.materials.append(mat)
bpy.ops.object.light_add(type='AREA',location=(-12,-22,40));bpy.context.object.data.energy=16000;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=25
bpy.ops.object.light_add(type='SUN',location=(0,0,30));bpy.context.object.rotation_euler=(.4,-.5,-.6);bpy.context.object.data.energy=2
bpy.ops.object.camera_add(location=(48,78,45));cam=bpy.context.object;target=Vector((0,3,3.5));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=63;bpy.context.scene.camera=cam
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=48;scene.cycles.use_denoising=False
scene.world.color=(.75,.75,.75);scene.render.resolution_x=1500;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=str(BASE/'Documentacion/Vistas/Vista_3D_H.png');scene.render.film_transparent=False

bpy.ops.render.render(write_still=True)
