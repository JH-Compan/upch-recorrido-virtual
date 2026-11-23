"""Correccion R19: encuentros y acabados interiores sin reconstruir el exterior."""
import json,re,copy,ast,collections
import numpy as np
import manifold3d as mf
from shapely.geometry import box,Point,LineString,Polygon
from shapely.ops import unary_union
import construir as b
from fachada_campus import solid,part_solid,replace_part,as_mesh,louver
path=b.BASE/'Datos/Modelo_H.json';m=json.loads(path.read_text())
if m['revision']=='R19_Revision_Interiores':
 print('R19 ya aplicada; no se reconstruye el edificio.');raise SystemExit(0)
assert m['revision']=='R18_Entrada_Triangular_Vacios_Campus'
b.PARAMS.update(m['parameters']);b.NPT[:]=m['npt'];old=copy.deepcopy(m);changed=set();added=[]
def guid(name):return re.search(r'^guid: (\w+)',(b.BASE/'Materiales'/(name+'.mat.meta')).read_text(),re.M)[1]
grey=guid('H_Zocalo_Gris');concrete=guid('H_Hormigon_Beige');dark=guid('H_Carpinteria_Oscura');glass=guid('H_Vidrio_Gris');red=guid('H_Zocalo_Rojizo')
node=next(n for n in ast.parse((b.ROOT/'Tools/Veterinaria/cierre_visible_icrea_r14.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='transfer');exec(compile(ast.Module(body=[node],type_ignores=[]),'<material-transfer>','exec'))
def edit(q,body):
 prior=copy.deepcopy(q);replace_part(b,q,body.simplify(.00001));transfer(q,prior);changed.add(q['id'])
def add(body,name,mat,material,level,collider=True):
 if body.is_empty() or body.volume()<1e-8:return
 b.add_mesh(as_mesh(body),'0%d_%s/Interiores_R19'%(level+1,['Sotano','Primer_Piso','Segundo_Piso','Tercer_Piso','Azotea'][level]),name,mat,collider,'fixed',level,0,1,'A-01/A-04, perfiles CAD y encuentros interiores','Correccion local: no reconstruye fachadas ni altera cotas NPT.')
 q=b.PARTS[-1];q['id']='H_%d_Interiores_R19_%04d'%(level,len(added)+1);q['materialGuid']=material;m['items'].append(q);added.append(q)
def opaque(profile,lo,hi,name,level,material=concrete):
 desired=solid(b,profile,lo,hi);existing=[]
 for q in m['items']:
  if q['hidden'] or not q['active'] or q['material'] not in ['wall','floor','metal','glass']:continue
  v=b.materialize_vertices(q)
  if v[:,1].max()<=lo or v[:,1].min()>=hi or not b.part_footprint(q).intersects(profile):continue
  existing.append(part_solid(b,q))
 if existing:desired=desired-mf.Manifold.batch_boolean(existing,mf.OpType.Add)
 add(desired,name,'wall',material,level)
def disable(q):q['active']=False;q['hidden']=True;changed.add(q['id'])
from auditar_interiores_r19 import section,opaque_native,candidates,anchor_summary
from cad_h import geometry
cad=json.loads((b.ROOT/'Tools/Veterinaria/Fuentes/CAD_H.json').read_text());cir_path=b.BASE/'Documentacion/Puertas_y_Niveles.json';cir=json.loads(cir_path.read_text())
initial=candidates(b,m,cir);initial_anchors=anchor_summary(b,m,cir);pending_ids={p['id'] for level in initial_anchors for p in level['unanchoredHingeCandidates']};restored=[];joins=[];removed_posts=[];paint=[];excluded=[]
interior_regions=[]
for lev in range(4):
 floor=unary_union([b.part_footprint(q) for q in m['items'] if q['active'] and not q['hidden'] and q['material']=='floor' and abs(b.materialize_vertices(q)[:,1].max()-b.NPT[lev])<.00002])
 interior_regions.append(b.envelope(lev).buffer(-.65).intersection(floor.buffer(-.35)).difference(box(16.2,-10.2,25,8.4)))

white='1f59cf1d4a0e3657b921b243f038d9b1';floor_material=b.MATS['floor']
# Six isolated equipment separators were extruded to ceiling height in the surgery room.
# A-01 depicts surgical stations, without a VIDRIO TEMPLADO wall annotation here.
for q in m['items']:
 if q['id'] in {'H_0_Cerramientos_Vidrio_%04d'%i for i in range(2,8)}:
  disable(q);q['note']+=' R19: simbolo de separacion de estaciones de cirugia; se retira la extrusion de vidrio hasta techo no respaldada por rotulo arquitectonico.';excluded.append(q['id'])
# Restore narrow source glazing omitted by the historical p.area < .03 filter.
for lev in range(4):
 region=interior_regions[lev]
 if lev in [2,3]:region=region.union(box(-3.56,-7.745,-3.30,-6.93))
 if lev==0:region=region.difference(box(-1.30,-.75,5.90,4.75))
 native=cad['levels'][lev];vv=geometry(native['window']+native.get('windowBacking',[])).difference(geometry(native['wall']+native['drywall']+native['low']))
 floor=unary_union([b.part_footprint(q) for q in m['items'] if q['active'] and not q['hidden'] and q['material']=='floor' and abs(b.materialize_vertices(q)[:,1].max()-b.NPT[lev])<.00002])
 opening=unary_union([LineString([q['hinge'],q['closed']]).buffer(.32,cap_style='flat') for q in cir['doors'][lev]])
 vv=vv.intersection(region).intersection(floor.buffer(.0002)).difference(opening)
 for p in b.polygons(vv):
  rr=np.array(p.minimum_rotated_rectangle.exterior.coords)[:4];length=np.linalg.norm(np.roll(rr,-1,axis=0)-rr,axis=1).max()
  if p.area<.0005 or p.area>=.03 or length<.20 or p.area/max(length,1e-6)>.075 or p.area/p.minimum_rotated_rectangle.area<.25:continue
  lo=b.NPT[lev];hi=b.NPT[lev+1]-b.PARAMS['slabThickness'];desired=solid(b,p,lo,hi);prior_volume=desired.volume()
  for q in m['items']:
   if q['level']!=lev or not q['active'] or q['hidden'] or q['material'] not in ['wall','glass'] or q['role']=='door' or not b.part_footprint(q).intersects(p):continue
   desired=desired-part_solid(b,q).minkowski_sum(mf.Manifold.cube((.0004,.0004,.0004),center=True))
  desired=desired.simplify(.0001)
  if desired.volume()<.0005:continue
  add(desired,'Paño_estrecho_CAD_recuperado','glass',glass,lev);restored.append({'id':added[-1]['id'],'level':lev,'sourceArea':p.area,'restoredVolume':desired.volume(),'bounds':list(p.bounds)})
# A double-leaf opening has a header and two outer jambs, not a fixed centre post.
for lev in range(4):
 frame=next(q for q in m['items'] if q['group'].endswith('/Marcos_Puertas') and q['level']==lev);tools=[];groups={}
 for j,d in enumerate(cir['doors'][lev]):
  h=d.get('dimensionHandle');width=np.linalg.norm(np.array(d['closed'])-d['hinge'])
  if h and d.get('confirmedOpeningDimension',0)>width*1.9:groups.setdefault(h,[]).append(d)
 for h,ds in groups.items():
  if len(ds)!=2 or np.linalg.norm(np.array(ds[0]['closed'])-ds[1]['closed'])>.01:continue
  center=np.mean([d['closed'] for d in ds],axis=0)
  if not interior_regions[lev].covers(Point(center)):continue
  u=np.array(ds[0]['closed'])-ds[0]['hinge'];u/=np.linalg.norm(u);profile=LineString([center-u*.024,center+u*.024]).buffer(.067,cap_style='flat')
  tools.append(solid(b,profile,b.NPT[lev]-.001,b.NPT[lev]+b.PARAMS['doorHeight']-.046));removed_posts.append({'level':lev,'dimensionHandle':h,'center':center.tolist()})
 if tools:
  body=part_solid(b,frame)-mf.Manifold.batch_boolean(tools,mf.OpType.Add);replace_part(b,frame,body.simplify(.0001));changed.add(frame['id'])
# Connect the existing CAD leaves to the surrounding wall/glazing via short jamb returns.
# Door leaf size, hinge, runtime opening and every circulation line remain unchanged.
for lev in range(4):
 y=b.NPT[lev]+1.;region=interior_regions[lev]
 if lev in [2,3]:region=region.union(box(-3.56,-7.745,-3.30,-6.93))
 if lev==0:region=region.union(box(16.6,-2.6,16.9,-1.6))
 surroundings=[q for q in m['items'] if q['level']==lev and q['active'] and not q['hidden'] and q['material'] in ['wall','glass'] and q['role']!='door'];support=unary_union([section(b,q,y) for q in surroundings]);frames=next(q for q in m['items'] if q['level']==lev and q['group'].endswith('/Marcos_Puertas'));pieces=[];prior_frames=part_solid(b,frames)
 for j,d in enumerate(cir['doors'][lev]):
  a,z=np.array(d['hinge']),np.array(d['closed']);u=(z-a)/np.linalg.norm(z-a)
  for end,pnt in [('hinge',a),('closed',z)]:
   if end=='closed' and any(k!=j and np.linalg.norm(pnt-np.array(other['closed']))<.05 for k,other in enumerate(cir['doors'][lev])):continue
   point=Point(pnt);distance=support.distance(point)
   leaf_id=next(p['id'] for p in m['items'] if p['level']==lev and p['role']=='door' and p['name']=='Puerta_'+str(j+1)+'_cerrada')
   minimum=.04 if end=='hinge' and leaf_id in pending_ids else .075
   if not minimum<distance<.31 or not region.covers(point):continue
   from shapely.ops import nearest_points
   target=np.array(nearest_points(point,support)[1].coords[0]);delta=target-pnt;direction=delta/max(np.linalg.norm(delta),1e-12)
   # A return must go away from the clear width, not make a post across the doorway.
   if (direction@u> .35 if end=='hinge' else direction@u<-.35):continue
   profile=LineString([pnt,target+direction*.015]).buffer(.025,cap_style='square')
   body=solid(b,profile,b.NPT[lev],b.NPT[lev]+b.PARAMS['doorHeight'])
   # Union with the existing jamb mesh below, rather than making near-coincident trim shells.
   for q in surroundings:
    if q['material']=='wall' and b.part_footprint(q).intersects(profile):body=body-part_solid(b,q)
   if body.volume()<1e-7:continue
   pieces.append(body);joins.append({'level':lev,'doorIndex':j+1,'end':end,'gap_m':distance,'start':pnt.tolist(),'wallPoint':target.tolist()})
 if pieces:
  body=mf.Manifold.batch_boolean([prior_frames,*pieces],mf.OpType.Add).simplify(.00001);replace_part(b,frames,body);changed.add(frames['id'])
# Uniform existing white paint only on strict interior wall faces. No new material is introduced.
for q in m['items']:
 if not q['active'] or q['hidden'] or q['role']=='door' or q['material']!='wall' or q['level']>3:continue
 if any(tag in q['group'] for tag in ['Campus','Icrea','Fachada','Escalera','Acceso','Estructura_General']):continue
 region=interior_regions[q['level']];ts=b.materialize_vertices(q).reshape(-1,3,3);slots=q.get('materialGuids',[q['materialGuid']]);cols=[slots[k] for k in q.get('triangleMaterials',[0]*len(ts))];count=0;planes={}
 for i,t in enumerate(ts):
  c=t.mean(0);n=np.cross(t[1]-t[0],t[2]-t[0]);n/=max(np.linalg.norm(n),1e-15)
  if abs(n[1])>.1:continue
  key=tuple(np.round(n,4))+(round(float(n@t[0]),4),);eligible=region.covers(Point(c[0]+n[0]*.05,c[2]+n[2]*.05)) and region.covers(Point(c[0]-n[0]*.05,c[2]-n[2]*.05));planes.setdefault(key,[]).append((i,eligible))
 for group in planes.values():
  if not all(eligible for _,eligible in group):continue
  for i,_ in group:
   if cols[i]!=white:cols[i]=white;count+=1
 if count:
  pal=list(dict.fromkeys(cols));q['materialGuids']=pal;q['triangleMaterials']=[pal.index(g) for g in cols];changed.add(q['id']);paint.append({'id':q['id'],'faces':count})
# Regularize only additions, retaining every architectural source footprint.
repair_parts=added+[q for q in m['items'] if q['id'] in changed and q['group'].endswith('/Marcos_Puertas')]
b.PARTS[:]=repair_parts;b.repair_float32_topology();assert {q['id'] for q in b.PARTS}=={q['id'] for q in repair_parts};newby={q['id']:q for q in b.PARTS}
for i,q in enumerate(m['items']):
 if q['id'] in newby:m['items'][i]=newby[q['id']]
added[:]=[newby[q['id']] for q in added]
from conservar_carpinterias_r19 import preserve
preserve(b,m,old,removed_posts,joins)
# Preserve every existing prefab fileID. Clone one fixed five-component object for additions.
pp=b.BASE/'Prefabs/Pabellon_H_Veterinaria.prefab';raw=pp.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n';text=raw.decode().replace('\r\n','\n');prefix=text[:text.index('--- !u!')];blocks=re.split(r'(?=^--- !u!)',text,flags=re.M)[1:]
by={int(re.search(r'&(\d+)',z)[1]):z for z in blocks};names={re.search(r'&(\d+)',z)[1]:re.search(r'  m_Name: (.*)',z)[1].strip().strip('"') for z in blocks if z.startswith('--- !u!1 ')}
items={q['id']:q for q in m['items']}
for i,z in enumerate(blocks):
 if not z.startswith(('--- !u!1 ','--- !u!23 ')):continue
 gid=re.search(r'&(\d+)',z)[1] if z.startswith('--- !u!1 ') else re.search(r'm_GameObject: \{fileID: (\d+)\}',z)[1]
 for ident in changed:
  if names[gid]!=ident+'_'+items[ident]['name']:continue
  q=items[ident]
  if z.startswith('--- !u!23 '):blocks[i]=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+','  m_Materials:\n'+''.join('  - {fileID: 2100000, guid: '+g+', type: 2}\n' for g in q.get('materialGuids',[q['materialGuid']])),z)
  else:blocks[i]=re.sub(r'm_IsActive: [01]','m_IsActive: '+str(int(q['active'])),z)
source_go=next(g for g,name in names.items() if name.startswith('H_1_Cierre_Icrea_R14_0001_'))
selected=[by[int(source_go)]]+[z for z in blocks if 'm_GameObject: {fileID: '+source_go+'}' in z]
tr=next(z for z in selected if z.startswith('--- !u!4 '));parent=int(re.search(r'm_Father: \{fileID: (\d+)\}',tr)[1]);children=[]
# New objects are grouped under the existing fixed-object group to preserve hierarchy IDs.
for j,q in enumerate(added):
 b.write_mesh_asset(b.BASE/'Generado/Mallas'/(q['id']+'.asset'),q);mg=b.meta(b.BASE/'Generado/Mallas'/(q['id']+'.asset'))
 ids={int(re.search(r'&(\d+)',z)[1]):700000000000050000+j*10+k for k,z in enumerate(selected)};children.append(ids[int(re.search(r'&(\d+)',tr)[1])])
 for z in selected:
  z=re.sub(r'&(\d+)',lambda x:'&'+str(ids[int(x[1])]),z,count=1);z=re.sub(r'fileID: (\d+)',lambda x:'fileID: '+str(ids.get(int(x[1]),int(x[1]))),z)
  if z.startswith('--- !u!64 ') and not q['collider']:z=z.replace('m_Enabled: 1','m_Enabled: 0')
  if z.startswith('--- !u!1 '):z=re.sub(r'  m_Name: .*','  m_Name: '+q['id']+'_'+q['name'],z)
  if z.startswith(('--- !u!33 ','--- !u!64 ')):z=re.sub(r'm_Mesh: \{fileID: 4300000, guid: \w+, type: 2\}','m_Mesh: {fileID: 4300000, guid: '+mg+', type: 2}',z)
  if z.startswith('--- !u!23 '):z=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+','  m_Materials:\n'+''.join('  - {fileID: 2100000, guid: '+g+', type: 2}\n' for g in q.get('materialGuids',[q['materialGuid']])),z)
  blocks.append(z)
for i,z in enumerate(blocks):
 if z.startswith('--- !u!4 &'+str(parent)+'\n'):blocks[i]=z.replace('  m_Father:',''.join('  - {fileID: '+str(k)+'}\n' for k in children)+'  m_Father:',1)
from grupos_interiores_r19 import organize
blocks=organize(blocks,added)
blocks=[re.sub(r"[ \t]+(?=\n)","",z) if int(re.search(r"&(\d+)",z)[1])>=700000000000050000 else z for z in blocks]
blocks=[by[int(re.search(r'&(\d+)',z)[1])] if int(re.search(r'&(\d+)',z)[1]) in by and ' '.join(by[int(re.search(r'&(\d+)',z)[1])].split())==' '.join(z.split()) else z for z in blocks]
pp.write_bytes((prefix+''.join(blocks)).replace('\n',nl).encode())
for ident in changed:b.write_mesh_asset(b.BASE/'Generado/Mallas'/(ident+'.asset'),items[ident])
m['revision']='R19_Revision_Interiores';path.write_text(json.dumps(m,ensure_ascii=False,separators=(',',':')))
report={'revision':m['revision'],'changed':sorted(changed),'added':[q['id'] for q in added],'initialDoorMasonryGapCandidates':initial,'initialDoorFrameAnchors':initial_anchors,'finalDoorFrameAnchors':anchor_summary(b,m,cir),'narrowGlazingRestored':restored,'jambReturns':joins,'removedDoubleDoorCentrePosts':removed_posts,'excludedSurgicalEquipmentExtrusions':excluded,'interiorPaintChanges':paint,'estimated':'Alturas de vidrio recuperado hasta intrados y secciones de jambas siguen siendo estimadas. No se afirma validacion de interiores reales por fotos.','preserved':'Puertas, bisagras, aperturas runtime, losas, cotas, escaleras, fachada y Campus conservados; los marcos interiores se corrigen localmente.','UnityPlay':'NOT_RUN'}
rp=b.BASE/'Documentacion/Revision_Interiores_R19.json';rp.write_text(json.dumps(report,ensure_ascii=False,indent=2));b.meta(rp)
cp=b.BASE/'Documentacion/Construccion.json';c=json.loads(cp.read_text());c['parts']=len(m['items']);c['byGroup']=dict(collections.Counter(q['group'] for q in m['items']));cp.write_text(json.dumps(c,ensure_ascii=False,indent=2));print({'changed':len(changed),'added':len(added),'restoredGlass':len(restored),'jambReturns':len(joins),'doubleDoorPosts':len(removed_posts),'paintedParts':len(paint)})
