"""R14: recorte exterior sobre R13 del usuario; no reconstruye interiores."""
import json,re,copy
from pathlib import Path
import numpy as np
import manifold3d as mf
from shapely.geometry import box
from shapely import wkt
from shapely.ops import unary_union
import construir as b
from fachada_campus import solid,part_solid,replace_part
m=json.loads((b.BASE/'Datos/Modelo_H.json').read_text());
if m['revision']=='R14_Retoque_Exterior_Icrea':
 print('R14 ya aplicada; se conserva la revision local.');raise SystemExit(0)
assert m['revision']=='R13_Retoque_Exterior_Icrea'
b.PARAMS.update(m['parameters']);b.NPT[:]=m['npt'];before=copy.deepcopy(m);items={p['id']:p for p in m['items']}
grey=re.search(r'^guid: (\w+)',(b.BASE/'Materiales/H_Zocalo_Gris.mat.meta').read_text(),re.M)[1]
concrete=re.search(r'^guid: (\w+)',(b.BASE/'Materiales/H_Hormigon_Beige.mat.meta').read_text(),re.M)[1]
changed=[]
def transfer(p,old):
 oldtri=b.materialize_vertices(old).reshape(-1,3,3);cent=oldtri.mean(1);norm=np.cross(oldtri[:,1]-oldtri[:,0],oldtri[:,2]-oldtri[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-18)
 slots=old.get('materialGuids',[old['materialGuid']]);mask=old.get('triangleMaterials',[0]*len(oldtri));colour=[]
 for tri in b.materialize_vertices(p).reshape(-1,3,3):
  c=tri.mean(0);n=np.cross(tri[1]-tri[0],tri[2]-tri[0]);n/=max(np.linalg.norm(n),1e-18)
  dist=abs(np.einsum('ij,ij->i',c-cent,norm));v0=oldtri[:,1]-oldtri[:,0];v1=oldtri[:,2]-oldtri[:,0];v2=c-oldtri[:,0]
  dot=lambda a,z:np.einsum('ij,ij->i',a,z)
  d00,d01,d11,d20,d21=dot(v0,v0),dot(v0,v1),dot(v1,v1),dot(v2,v0),dot(v2,v1);den=d00*d11-d01*d01;den=np.where(abs(den)<1e-25,1e-25,den);u=(d11*d20-d01*d21)/den;v=(d00*d21-d01*d20)/den
  valid=(u>=-1e-5)&(v>=-1e-5)&(u+v<=1.00001)&(dist<.00002)&(norm@n>.999)
  scores=np.linalg.norm(c-cent,axis=1)+dist*1e5+(1-norm@n)*1e4
  if valid.any():scores=np.where(valid,scores,1e30)
  j=int(np.argmin(scores));g=slots[mask[j]]
  if 20.4565<c[0]<22.05 and -1.5031<c[2]<-.6524 and p['material']=='wall':g=grey if c[1]<=.98001 else concrete
  colour.append(g)
 palette=list(dict.fromkeys(colour));p['materialGuids']=palette;p['triangleMaterials']=[palette.index(g) for g in colour]
def cut(ident,profile,lo,hi):
 p=items[ident];old=copy.deepcopy(p);body=part_solid(b,p);result=(body-solid(b,profile,lo,hi)).simplify(.00001)
 if abs(body.volume()-result.volume())<1e-8:return
 replace_part(b,p,result);transfer(p,old);b.write_mesh_asset(b.BASE/'Generado/Mallas'/(ident+'.asset'),p);changed.append(ident)
cut('H_1_Muros_0062',box(20.4565,-1.5031,22.05,-.6524),.98,3.3101)
# Trim the unsupported exterior fascia, never the slab underneath real walls.
mask=box(20.4565,-1.5031,22.05,-.6524)
occupied=unary_union([b.part_footprint(p).buffer(.0003,join_style='mitre') for p in m['items'] if p['level']==2 and p['material']=='wall' and not p['hidden']])
mask=mask.difference(occupied)
cut('H_2_Losas_0001',mask,3.3099,3.5501)
if 'H_2_Losas_0001' in changed:m['expectedFloorCoverage'][2]=wkt.loads(m['expectedFloorCoverage'][2]).difference(mask).wkt
# Continuous service-volume roof at the existing head level, outside the stair box.
profile=box(18.5571,-2.4342,21.7046,-.752)
desired=solid(b,profile,.90,.98);tools=[]
for q in m['items']:
 if q['hidden'] or q['material'] not in ['wall','floor','metal']:continue
 v=b.materialize_vertices(q)
 if v[:,1].max()<=.90 or v[:,1].min()>=.98 or not b.part_footprint(q).intersects(profile):continue
 tools.append(part_solid(b,q).minkowski_sum(mf.Manifold.cube((.0004,.0004,.0004),center=True)))
if tools:desired=desired-mf.Manifold.batch_boolean(tools,mf.OpType.Add)
from fachada_campus import as_mesh
b.add_mesh(as_mesh(desired.simplify(.00002)),'02_Primer_Piso/Cierre_Icrea_R12','Techo_continuo_exterior_Icrea_R14','wall',True,'fixed',1,0,1,'Volumen exterior marcado por usuario; remate alineado al dintel R12','Tapa exterior; caja de escalera y piso interior conservados.')
roof=b.PARTS[-1];roof['id']='H_1_Cierre_Icrea_R14_0001';replace_part(b,roof,desired.simplify(.00002));roof['materialGuid']=grey
m['items'].append(roof);b.write_mesh_asset(b.BASE/'Generado/Mallas'/(roof['id']+'.asset'),roof)
# Preserve existing prefab IDs; replace only affected renderer material arrays.
pp=b.BASE/'Prefabs/Pabellon_H_Veterinaria.prefab';text=pp.read_bytes().decode();newline='\r\n' if '\r\n' in text else '\n';text=text.replace('\r\n','\n');prefix=text[:text.index('--- !u!')];blocks=re.split(r'(?=^--- !u!)',text,flags=re.M)[1:];names={}
for s in blocks:
 if s.startswith('--- !u!1 '):names[re.search(r'&(\d+)',s)[1]]=re.search(r'  m_Name: (.*)',s)[1].strip().strip('"')
for i,s in enumerate(blocks):
 if not s.startswith('--- !u!23 '):continue
 gid=re.search(r'm_GameObject: \{fileID: (\d+)\}',s)[1]
 for ident in changed:
  if names[gid].startswith(ident+'_'):
   p=items[ident];slots=p.get('materialGuids',[p['materialGuid']]);blocks[i]=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+','  m_Materials:\n'+''.join('  - {fileID: 2100000, guid: '+g+', type: 2}\n' for g in slots),s)
# Clone the existing service roof components without changing any existing fileID.
by={int(re.search(r'&(\d+)',z)[1]):z for z in blocks}
source_go=next(g for g,name in names.items() if name.startswith('H_1_Cierre_Icrea_R12_0001_'))
selected=[z for z in blocks if re.search(r'm_GameObject: \{fileID: '+source_go+r'\}',z)]
selected.insert(0,by[int(source_go)])
ids={int(re.search(r'&(\d+)',z)[1]):700000000000010000+k for k,z in enumerate(selected)}
tr=next(z for z in selected if z.startswith('--- !u!4 '));parent=int(re.search(r'm_Father: \{fileID: (\d+)\}',tr)[1]);trid=ids[int(re.search(r'&(\d+)',tr)[1])]
meshguid=b.meta(b.BASE/'Generado/Mallas'/(roof['id']+'.asset'))
for z in selected:
 z=re.sub(r'&(\d+)',lambda x:'&'+str(ids[int(x[1])]),z,count=1)
 z=re.sub(r'fileID: (\d+)',lambda x:'fileID: '+str(ids.get(int(x[1]),int(x[1]))),z)
 if z.startswith('--- !u!1 '):z=re.sub(r'  m_Name: .*', '  m_Name: '+roof['id']+'_'+roof['name'],z)
 if z.startswith(('--- !u!33 ','--- !u!64 ')):z=re.sub(r'm_Mesh: \{fileID: 4300000, guid: \w+, type: 2\}', 'm_Mesh: {fileID: 4300000, guid: '+meshguid+', type: 2}',z)
 if z.startswith('--- !u!23 '):z=re.sub(r'  m_Materials:\r?\n(?:  - [^\n]+\n)+','  m_Materials:\n  - {fileID: 2100000, guid: '+grey+', type: 2}\n',z)
 blocks.append(z)
for i,z in enumerate(blocks):
 if z.startswith('--- !u!4 &'+str(parent)+'\n') or z.startswith('--- !u!4 &'+str(parent)+'\r\n'):
  blocks[i]=z.replace('  m_Father:','  - {fileID: '+str(trid)+'}\n  m_Father:',1)
pp.write_bytes((prefix+''.join(blocks).replace('\r\n','\n').replace('\n',newline)).encode())
scene=b.ROOT/'Assets/UPCH/Scenes/Campus.unity';n=0
import hashlib
m['userSceneSha256NormalizedLF']=hashlib.sha256(scene.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
m['revision']='R14_Retoque_Exterior_Icrea';(b.BASE/'Datos/Modelo_H.json').write_text(json.dumps(m,ensure_ascii=False,separators=(',',':')))
r={'revision':m['revision'],'changedMeshes':changed,'addedRoof':roof['id'],'roofNPT':.98,'removedSceneMaterialOverrides':n,'stairsUnchanged':True,'windowHeightsUnchanged':True,'stairReview':'Plantas: descanso curvo R1.48 junto a esa cara. Alturas de vanos y NPT intermedios no acotados en alzado; no se mueven peldaños ni descansos para ocultar barandas.','scope':'Solo saliente exterior y fascia frente a I-crea. Interior y frente universitario sin reconstruir.','roofReview':'Techo plano nuevo de 8 cm, entre NPT 0.90 y 0.98, cubre el volumen exterior rectangular junto al remate triangular existente. No se rellena la caja de escalera.','UnityPlay':'NOT_RUN'}
p=b.BASE/'Documentacion/Revision_Icrea_R14.json';p.write_text(json.dumps(r,ensure_ascii=False,indent=2));b.meta(p);print(r)
