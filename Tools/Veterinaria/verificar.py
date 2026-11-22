#!/usr/bin/env python3
"""Independent checks over the serialized deliverable, not Unity Play tests."""
from pathlib import Path
import collections,hashlib,json,re,struct,subprocess
import numpy as np
import trimesh
from shapely.geometry import Polygon,Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely import wkt
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'Assets/UPCH/Veterinaria'

def mesh(path):
 s=path.read_text();data=bytes.fromhex(re.search(r'_typelessdata: (\w+)',s)[1]);v=np.frombuffer(data,dtype='<f4').reshape(-1,8)
 raw=bytes.fromhex(re.search(r'm_IndexBuffer: (\w+)',s)[1]);dtype='<u4' if 'm_IndexFormat: 1' in s else '<u2';t=np.frombuffer(raw,dtype=dtype).reshape(-1,3)
 return v,t

def circulation_vertices(part,vertices):
 """Evaluate the defined open pose, including the actual leaf collision."""
 if part['role']!='door' or 'doorHinge' not in part:return vertices
 result=vertices.copy();hinge=np.asarray(part['doorHinge']);angle=np.deg2rad(part['doorOpenDegrees']);c,s=np.cos(angle),np.sin(angle)
 xyz=result[:,:3]-hinge
 result[:,0]=c*xyz[:,0]+s*xyz[:,2]+hinge[0]
 result[:,2]=-s*xyz[:,0]+c*xyz[:,2]+hinge[2]
 return result

class MetalSurfaceIndex:
 """Height-clipped triangle surfaces of joined railings; no whole-part AABB barrier."""
 def __init__(self,triangles,identifiers):
  from shapely.geometry import MultiPoint
  self.triangles=np.asarray(triangles);self.ids=identifiers;self.projected=[MultiPoint(t[:,[0,2]]).convex_hull.buffer(.00005) for t in self.triangles];self.tree=STRtree(self.projected)
 def clipped(self,k,y):
  p=list(self.triangles[k]);low=y+.21;high=y+1.75
  if max(q[1] for q in p)<=low or min(q[1] for q in p)>=high:return None
  for height,sign in [(low,1),(high,-1)]:
   result=[]
   for a,b in zip(p,p[1:]+p[:1]):
    aa=sign*(a[1]-height)>=0;bb=sign*(b[1]-height)>=0
    if aa:result.append(a)
    if aa!=bb:result.append(a+(b-a)*((height-a[1])/(b[1]-a[1])))
   p=result
   if not p:return None
  from shapely.geometry import MultiPoint
  return MultiPoint([q[[0,2]] for q in p]).convex_hull.buffer(.00005)
 def collisions(self,point,y,radius=.25):
  body=point.buffer(radius);hits=set()
  for k in self.tree.query(body):
   g=self.clipped(int(k),y)
   if g is not None and g.intersects(body):hits.add(self.ids[k])
  return sorted(hits)
 def barriers(self,y,region):
  gs=[]
  for k in self.tree.query(region):
   g=self.clipped(int(k),y)
   if g is not None:gs.append(g)
  return unary_union(gs)

def main():
 model=json.loads((BASE/'Datos/Modelo_H.json').read_text());errors=[];observed=[];summaries=[];hashes={};walls=[];floors=[];support_surfaces=[];junctions=[];metal_triangles=[];metal_ids=[];planes=collections.defaultdict(lambda:collections.defaultdict(list))
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
  if not p['hidden'] and p['material']!='glass':
   for tri,n,area in zip(tris,norm,a):
    if area<1e-10:continue
    n=n/area
    key=tuple(np.round(n,4))+(round(float(n@tri[0]),4),);axis=int(np.argmax(np.abs(n)));g=Polygon(np.delete(tri,axis,axis=1))
    if g.area>1e-6:planes[key][p['id']].append(g)
  m=trimesh.Trimesh(vertices=v[:,:3],faces=t,process=True)
  watertight=m.is_watertight
  if not watertight:observed.append([p['id'],'no_manifold_despues_de_soldadura_float32'])
  if m.volume<-.000001:errors.append([p['id'],'negative_volume'])
  if p['collider'] and not p['hidden']:
   collision_tri=circulation_vertices(p,v)[t,:3].astype(float);collision_norm=np.cross(collision_tri[:,1]-collision_tri[:,0],collision_tri[:,2]-collision_tri[:,0])
   cap=collision_tri[collision_norm[:,1]>1e-9];g=unary_union([Polygon(t[:,[0,2]]) for t in cap])
   if p['name']=='Barandas_y_pasamanos_continuos':metal_triangles.extend(tris);metal_ids.extend([p['id']]*len(tris))
   elif p['material']!='floor':walls.append((p['id'],g,float(v[:,1].min()),float(v[:,1].max())))
   elif p['role']=='slab':floors.append((p['level'],g,float(v[:,1].min())))
   if p['material']=='floor' and p['role'] in ['slab','fixed']:support_surfaces.append((p['level'],g,float(v[:,1].max()),p['id']))
   if p['material'] in ['wall','glass'] and p['role'] in ['wall','sill','doorLintel','windowLintel','fixed']:junctions.append((p['id'],g,float(v[:,1].min()),float(v[:,1].max()),p['level']))
  if p['role']=='slab':
   npt=model['npt'][p['level']]
   if abs(v[:,1].max()-npt)>.00001:errors.append([p['id'],'NPT'])
  canonical=sorted(tuple(sorted(tuple(q) for q in tri)) for tri in np.round(tris,5));h=hashlib.sha256(repr(canonical).encode()).hexdigest()
  if h in hashes:observed.append([p['id'],'geometria_repetida',hashes[h]])
  hashes[h]=p['id']
  summaries.append({'id':p['id'],'group':p['group'],'vertices':len(v),'triangles':len(t),'watertight':bool(watertight),'bounds':[v[:,:3].min(axis=0).tolist(),v[:,:3].max(axis=0).tolist()]})
 prefab=(BASE/'Prefabs/Pabellon_H_Veterinaria.prefab').read_text();ids=re.findall(r'^--- !u!\d+ &(\d+)',prefab,re.M)
 if len(ids)!=len(set(ids)):errors.append(['prefab','duplicate_fileIDs'])
 if len(re.findall(r'^  m_Name: "?Pabellon_H_Veterinaria"?\s*$',prefab,re.M))!=1:errors.append(['prefab','root_count'])
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
 circulation=[];metal=MetalSurfaceIndex(metal_triangles,metal_ids)
 for step in steps:
  center=wkt.loads(step['tread']).representative_point();body=center.buffer(.25);y=step['upper']
  if abs(step['riser'])>.20:circulation.append([step['stair'],step['index'],'riser_above_player_stepOffset'])
  for ident,g,lo,hi in walls:
   if lo<y+1.75 and hi>y+.21 and g.intersects(body):circulation.append([step['stair'],step['index'],'possible_capsule_obstacle',ident])
  for ident in metal.collisions(center,y):circulation.append([step['stair'],step['index'],'possible_capsule_obstacle',ident])
  for level,g,lo in floors:
   if y+.21<lo<y+1.75 and g.intersects(center.buffer(.20)):circulation.append([step['stair'],step['index'],'possible_ceiling_obstacle',level])
 doorCandidates=[]
 for level,doors in enumerate(circulationData['doors']):
  y=model['npt'][level]
  for j,door in enumerate(doors):
   center=np.mean([door['hinge'],door['closed']],axis=0)
   body=Point(center).buffer(.25)
   for ident,g,lo,hi in walls:
    if lo<y+1.75 and hi>y+.21 and g.intersects(body):doorCandidates.append([level,j,ident])
 coincident=[]
 for plane,objects in planes.items():
  ids=list(objects);gs=[unary_union(objects[k]) for k in ids];tree=STRtree(gs)
  for i,g in enumerate(gs):
   for j in tree.query(g):
    if j<=i:continue
    area=g.intersection(gs[j]).area
    if area>.0001:coincident.append({'a':ids[i],'b':ids[j],'areaProjected':float(area),'plane':list(plane)})
 for q in coincident:errors.append([q['a'],q['b'],'same_facing_coplanar_faces'])
 # Full enclosure/slab junctions, not only selected walking lines.
 slab_planes={i:unary_union([g for level,g,y,ident in support_surfaces if abs(y-npt)<.00002]) for i,npt in enumerate(model['npt'])};junction_checks=[]
 for ident,g,lo,hi,level in junctions:
  for i,npt in enumerate(model['npt']):
   if i==0:continue
   for kind,relevant in [('base',abs(lo-npt)<.00002),('cabeza',abs(hi-(npt-model['parameters']['slabThickness']))<.00002)]:
    if not relevant:continue
    missing=g.difference(slab_planes[i].buffer(.002));area=float(missing.area)
    junction_checks.append({'asset':ident,'junction':kind,'level':i,'uncoveredArea':area})
    if area>.001:errors.append([ident,kind,i,'encuentro_muro_losa_abierto',area])
 cad=json.loads((ROOT/'Tools/Veterinaria/Fuentes/CAD_H.json').read_text());review=cad.get('reviewedArchitecture',{});entry_area=None
 if review.get('entryPlatform'):
  entry_area=float(Polygon(review['entryPlatform']['outline']).difference(slab_planes[1].buffer(.002)).area)
  if entry_area>.001:errors.append(['entrada_A02','plataforma_CAD_sin_apoyo',entry_area])
 # R6 checks the full annex surface and every source floor footprint, not only labels.
 annex_area=None;floor_coverage=[]
 annex=review.get('exteriorAnnexRoof',{})
 if annex.get('verificationOutline'):
  mask=Polygon(annex['verificationOutline']);annex_area=float(mask.difference(slab_planes[1].buffer(.002)).area)
  if annex_area>.001:errors.append(['cubierta_anexo_ingreso','superficie_sin_cubierta',annex_area])
 for i,source in enumerate(model.get('expectedFloorCoverage',[])):
  expected=wkt.loads(source)
  occupied=unary_union([g for ident,g,lo,hi in walls if lo<=model['npt'][i]+.003 and hi>=model['npt'][i]-.003])
  missing=expected.difference(slab_planes[i].union(occupied).buffer(.002));area=float(missing.area)
  floor_coverage.append({'level':i,'sourceFootprintArea':float(expected.area),'uncoveredArea':area,'scope':'Contorno fuente previo a resolver solidos; excluye cajas y vacios previstos y huellas de cerramientos. No certifica exactitud de cada recinto.'})
  if area>.001:errors.append(['piso_completo',i,'superficie_interior_sin_apoyo',area])
 # Independent source-label support check. A text insertion point is not
 # a room outline; this specifically guards against deleting a labelled hall.
 label_checks=[];cad=json.loads((ROOT/'Tools/Veterinaria/Fuentes/CAD_H.json').read_text())
 for i,level in enumerate(cad['levels']):
  for text in level['texts']:
   name=text['text'].strip()
   if not re.search(r'LABORATORIO|CIRUG|AULA |DOCENTES|RECEPC|COMEDOR|HALL|CISTERNA|BOMBAS|CONSEJO|DECAN|POSGRADO|EPIDEMIO|PARASITO|BIOLOGIA|NUTRICION|MICROBIO|PATOLOGIA|FISIOLOG|REPRODUC|PREPARAC|TRAMITE|SECRETARIA|DIRECCION',name,re.I):continue
   expected=-4.5 if i==0 and name in ['CISTERNA','CUARTO DE BOMBAS'] else model['npt'][i]
   point=Point(text['local']);supports=[ident for lev,g,y,ident in support_surfaces if lev==i and abs(y-expected)<.005 and g.buffer(.005).covers(point)]
   label_checks.append({'sheet':level['sheet'],'text':name,'sourceXZ':text['local'],'expectedNPT':expected,'floorSupport':bool(supports),'supportAssets':supports})
   if not supports:errors.append([level['sheet'],name,'rotulo_arquitectonico_sin_piso_en_NPT'])
 result={'annexUncoveredArea':annex_area,'fullFloorCoverage':floor_coverage,'coincidentFaces':coincident,'enclosureSlabJunctions':junction_checks,'entryPlatformUncoveredArea':entry_area,'coplanarScope':'Caras opacas con igual normal, verticales/horizontales/inclinadas; cuantizacion 0.1 mm, area proyectada >0.0001 m2. No comprueba todos los solapes volumetricos.','architecturalLabelSupports':label_checks,'labelCheckScope':'Puntos de insercion de 46 rotulos seleccionados del CAD; comprueba apoyo en NPT, no delimitacion completa ni recorrido de cada ambiente.','baseCommit':model['baseCommit'],'sourcePdfSha256':model['sourcePdfSha256'],'sourceDWG_SHA256':model.get('sourceDWG_SHA256'),'updateBaseCommit':'38a6b895e22e6a94eefedf66065cd0cd7260e70c','preservedFromUpdateBase':preserved,'root':model['rootName'],'anchor':model['anchor'],'npt':model['npt'],'parts':len(model['items']),'staticErrors':errors,'staticObservations':observed,'coplanarVerticalFaces':coincident,'circulationStaticCandidates':circulation,'doorCenterStaticCandidates':doorCandidates,'circulationScope':'Centros representativos de huellas; capsula radio 0.25 / altura 1.75. No es simulacion fisica ni comprobacion de todas las rutas entre ambientes.','sceneChangedOriginalFileIDs':changed,'sceneAddedFileIDs':sorted(set(new)-set(old)),'UnityCompilation':'NOT_RUN','UnityEditModeTests':'NOT_RUN','UnityWalkthrough':'NOT_RUN','architecturalStatus':'Construido a partir de plantas; alturas estimadas y conexiones inferidas requieren validacion. No equivale a un levantamiento BIM certificado.','meshes':summaries}
 (BASE/'Documentacion/Verificacion_Estatica.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in result.items() if k not in ['meshes','staticObservations']},ensure_ascii=False,indent=2))
 print('Observations',len(observed),collections.Counter(q[1] for q in observed))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
