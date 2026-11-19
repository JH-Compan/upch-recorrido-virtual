#!/usr/bin/env python3
"""Independent checks over the serialized deliverable, not Unity Play tests."""
from pathlib import Path
import collections,hashlib,json,re,struct,subprocess
import numpy as np
import trimesh
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import wkt
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'Assets/UPCH/Veterinaria'

def mesh(path):
 s=path.read_text();data=bytes.fromhex(re.search(r'_typelessdata: (\w+)',s)[1]);v=np.frombuffer(data,dtype='<f4').reshape(-1,8)
 raw=bytes.fromhex(re.search(r'm_IndexBuffer: (\w+)',s)[1]);dtype='<u4' if 'm_IndexFormat: 1' in s else '<u2';t=np.frombuffer(raw,dtype=dtype).reshape(-1,3)
 return v,t

def main():
 model=json.loads((BASE/'Datos/Modelo_H.json').read_text());errors=[];observed=[];summaries=[];hashes={};walls=[];floors=[]
 for p in model['items']:
  path=BASE/'Generado/Mallas'/f"{p['id']}.asset";v,t=mesh(path)
  if not np.isfinite(v).all():errors.append([p['id'],'nonfinite'])
  if t.max()>=len(v) or t.min()<0:errors.append([p['id'],'indices'])
  tris=v[t,:3].astype(float);norm=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);a=np.linalg.norm(norm,axis=1)
  if np.any(a<1e-10):observed.append([p['id'],'triangulos_de_area_muy_pequena',int(np.sum(a<1e-10))])
  if np.any((np.linalg.norm(v[:,3:6],axis=1)<.98)|(np.linalg.norm(v[:,3:6],axis=1)>1.02)):errors.append([p['id'],'normals'])
  # Validate the on-disk submesh index ranges, not only source JSON masks.
  serialized=path.read_text();ranges=re.findall(r'firstByte: (\d+)\n\s+indexCount: (\d+)',serialized)
  slots=p.get('materialGuids',[p['materialGuid']]);indexSize=4 if 'm_IndexFormat: 1' in serialized else 2
  if len(ranges)!=len(slots):errors.append([p['id'],'submesh_material_count'])
  cursor=0
  for first,count in ranges:
   if int(first)!=cursor*indexSize or int(count)%3:errors.append([p['id'],'submesh_index_range'])
   cursor+=int(count)
  if cursor!=t.size:errors.append([p['id'],'submesh_index_total'])
  m=trimesh.Trimesh(vertices=v[:,:3],faces=t,process=True)
  watertight=m.is_watertight
  if not watertight:observed.append([p['id'],'no_manifold_despues_de_soldadura_float32'])
  if m.volume<-.000001:errors.append([p['id'],'negative_volume'])
  if p['collider'] and not p['hidden']:
   cap=tris[norm[:,1]>1e-9];g=unary_union([Polygon(t[:,[0,2]]) for t in cap])
   if p['material']!='floor':walls.append((p['id'],g,float(v[:,1].min()),float(v[:,1].max())))
   elif p['role']=='slab':floors.append((p['level'],g,float(v[:,1].min())))
  if p['role']=='slab':
   npt=model['npt'][p['level']]
   if abs(v[:,1].max()-npt)>.00001:errors.append([p['id'],'NPT'])
  canonical=sorted(tuple(sorted(tuple(q) for q in tri)) for tri in np.round(tris,5));h=hashlib.sha256(repr(canonical).encode()).hexdigest()
  if h in hashes:observed.append([p['id'],'geometria_repetida',hashes[h]])
  hashes[h]=p['id']
  summaries.append({'id':p['id'],'group':p['group'],'vertices':len(v),'triangles':len(t),'watertight':bool(watertight),'bounds':[v[:,:3].min(axis=0).tolist(),v[:,:3].max(axis=0).tolist()]})
 prefab=(BASE/'Prefabs/Pabellon_H_Veterinaria.prefab').read_text();ids=re.findall(r'^--- !u!\d+ &(\d+)',prefab,re.M)
 if len(ids)!=len(set(ids)):errors.append(['prefab','duplicate_fileIDs'])
 if prefab.count('m_Name: "Pabellon_H_Veterinaria"')!=1:errors.append(['prefab','root_count'])
 source=subprocess.check_output(['git','show','98e8d8030f6ea5e9bee3360b28c86395f0abf28e:Assets/UPCH/Scenes/Campus.unity'],cwd=ROOT).decode()
 actual=(ROOT/'Assets/UPCH/Scenes/Campus.unity').read_text()
 def blocks(s):return {int(re.search(r'&(\d+)',x)[1]):x for x in re.split(r'(?=^--- !u!)',s,flags=re.M)[1:]}
 old=blocks(source);new=blocks(actual)
 changed=[i for i in old if old[i]!=new.get(i)]
 allowed={357576547,357576549,1237960108,6118289441634658740,1084190064,834378008}
 if set(changed)-allowed:errors.append(['scene','unrelated_changes',sorted(set(changed)-allowed)])
 if len(set(new)-set(old))!=2:errors.append(['scene','new_instance_docs'])
 guid=re.search(r'^guid: (\w+)',(BASE/'Prefabs/Pabellon_H_Veterinaria.prefab.meta').read_text(),re.M)[1]
 if actual.count('m_SourcePrefab: {fileID: 100100000, guid: '+guid)!=1:errors.append(['scene','H_prefab_instances'])
 # Every new mesh reference must resolve to an owned local asset.
 localGuids={re.search(r'^guid: (\w+)',p.read_text(),re.M)[1] for p in BASE.rglob('*.meta')}
 for g in re.findall(r'm_Mesh: \{fileID: 4300000, guid: (\w+)',prefab):
  if g not in localGuids:errors.append(['prefab','missing_mesh_guid',g])
 allGuids={re.search(r'^guid: (\w+)',p.read_text(),re.M)[1] for p in (ROOT/'Assets').rglob('*.meta') if re.search(r'^guid: (\w+)',p.read_text(),re.M)}
 for p in model['items']:
  for materialGuid in p.get('materialGuids',[p['materialGuid']]):
   if materialGuid not in allGuids:errors.append([p['id'],'unresolved_material_guid',materialGuid])
 protected=['Assets/UPCH/Scenes/Campus.unity','Assets/UPCH/Veterinaria/Generado/Terreno_Recortado_H.asset','Assets/UPCH/Veterinaria/Generado/Estado_Recorte_H.asset']
 preserved={}
 for rel in protected:
  original=subprocess.check_output(['git','show','38a6b895e22e6a94eefedf66065cd0cd7260e70c:'+rel],cwd=ROOT)
  preserved[rel]=(ROOT/rel).read_bytes()==original
  if not preserved[rel]:errors.append([rel,'modified_outside_building_revision'])
 circulationData=json.loads((BASE/'Documentacion/Puertas_y_Niveles.json').read_text());steps=circulationData['steps']
 circulation=[]
 for step in steps:
  center=wkt.loads(step['tread']).representative_point();body=center.buffer(.25);y=step['upper']
  if abs(step['riser'])>.20:circulation.append([step['stair'],step['index'],'riser_above_player_stepOffset'])
  for ident,g,lo,hi in walls:
   if lo<y+1.75 and hi>y+.21 and g.intersects(body):circulation.append([step['stair'],step['index'],'possible_capsule_obstacle',ident])
  for level,g,lo in floors:
   if y+.21<lo<y+1.75 and g.intersects(center.buffer(.20)):circulation.append([step['stair'],step['index'],'possible_ceiling_obstacle',level])
 doorCandidates=[]
 for level,doors in enumerate(circulationData['doors']):
  y=model['npt'][level]
  for j,door in enumerate(doors):
   center=np.mean([door['hinge'],door['closed']],axis=0)
   from shapely.geometry import Point
   body=Point(center).buffer(.25)
   for ident,g,lo,hi in walls:
    if lo<y+1.75 and hi>y+.21 and g.intersects(body):doorCandidates.append([level,j,ident])
 result={'baseCommit':model['baseCommit'],'sourcePdfSha256':model['sourcePdfSha256'],'sourceDWG_SHA256':model.get('sourceDWG_SHA256'),'updateBaseCommit':'38a6b895e22e6a94eefedf66065cd0cd7260e70c','preservedFromUpdateBase':preserved,'root':model['rootName'],'anchor':model['anchor'],'npt':model['npt'],'parts':len(model['items']),'staticErrors':errors,'staticObservations':observed,'circulationStaticCandidates':circulation,'doorCenterStaticCandidates':doorCandidates,'circulationScope':'Centros representativos de huellas; capsula radio 0.25 / altura 1.75. No es simulacion fisica ni comprobacion de todas las rutas entre ambientes.','sceneChangedOriginalFileIDs':changed,'sceneAddedFileIDs':sorted(set(new)-set(old)),'UnityCompilation':'NOT_RUN','UnityEditModeTests':'NOT_RUN','UnityWalkthrough':'NOT_RUN','architecturalStatus':'Construido a partir de plantas; alturas estimadas y conexiones inferidas requieren validacion. No equivale a un levantamiento BIM certificado.','meshes':summaries}
 (BASE/'Documentacion/Verificacion_Estatica.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k not in ['meshes','staticObservations']},ensure_ascii=False,indent=2))
 print('Observations',len(observed),collections.Counter(q[1] for q in observed))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
