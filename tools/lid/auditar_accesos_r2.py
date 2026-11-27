"""Sample 292 treads against architectural overhead geometry; not a Unity Play test."""
from pathlib import Path
import sys,re,json,numpy as np,trimesh
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lid'))
from unity_text import *
A=ROOT/'Assets/UPCH/LIDCompleto';p=UnityText(A/'Prefabs/Edificio_LID.prefab');guids=asset_guids(ROOT/'Assets');cache={};architecture=[];names=[];stairs=[]
for ident,(kind,body) in p.docs.items():
 if kind!=33:continue
 go=ref(body,'m_GameObject');tr=p.go_transforms[go];path=p.path_for(tr);name=p.names[go]
 g=re.search(r'm_Mesh: \{[^}]*guid: ([a-f0-9]{32})',body)[1]
 if g not in cache:cache[g]=read_mesh(guids[g])
 mesh=cache[g].copy();mesh.apply_transform(p.world(tr))
 if ('Escaler' in path or '/Exterior/Ingreso/' in path) and 'Peldano' in name:stairs.append((name,path,mesh))
 if any('/'+category+'/' in path for category in ['Losas','Muros','Tabiques','Vigas','Ventanas','Ingreso']) and not any(s in name for s in ['Peldano','Pasamano','Poste','Baranda','Marco','Montante','Mueble','Jardin','Losa_Inclinada']):
  architecture.append(mesh);names.extend([name]*len(mesh.faces))
combined=trimesh.util.concatenate(architecture);names=np.array(names);orig=[];ids=[]
for name,path,m in stairs:
 ts=m.vertices[m.faces];ys=ts[:,:,1];top=ts[np.all(np.abs(ys-m.bounds[1,1])<1e-4,axis=1)]
 if not len(top):continue
 from shapely.geometry import Polygon,Point
 from shapely.ops import unary_union
 poly=unary_union([Polygon(t[:,[0,2]]) for t in top]).buffer(-.08)
 if poly.is_empty:continue
 points=[poly.representative_point()]
 lo,hi=m.bounds
 for xx in np.linspace(lo[0]+.1,hi[0]-.1,3):
  for zz in np.linspace(lo[2]+.1,hi[2]-.1,3):
   if poly.contains(Point(xx,zz)):points.append(Point(xx,zz))
 for point in points:
  origin=np.array([point.x,m.bounds[1,1]+.025,point.y]);orig.append(origin);ids.append((name,path,origin.tolist()))
hits,rays,faces=combined.ray.intersects_location(orig,np.tile([0,1,0],(len(orig),1)),multiple_hits=True)
bad=[]; clearances=[]
for i,row in enumerate(ids):
 select=np.where(rays==i)[0]
 if not len(select):continue
 ix=select[np.argmin(hits[select,1])];clearance=hits[ix,1]-orig[i][1]+.025
 clearances.append(float(clearance))
 if clearance<2.0:bad.append({'tread':row[0],'path':row[1],'xyz':row[2],'headroom':round(float(clearance),4),'obstacle':str(names[faces[ix]])})
result={'revision':'LID_R2_Accesos_Estructura','tread_count':len(stairs),'sample_count':len(ids),'minimum_measured_headroom_m':min(clearances),'issues':bad,'samples':ids,'unity_play_tested':False,'threshold_m':2.0,'threshold_is_regulatory_certification':False}
(A/'Documentacion/Validacion_Accesos_R2.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='samples'},indent=2))
raise SystemExit(bool(bad))
