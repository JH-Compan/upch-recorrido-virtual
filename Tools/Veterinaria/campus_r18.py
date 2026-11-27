"""Correccion R18: entrada triangular y vacios del campus sobre R17, limitada al exterior."""
import json,re,copy,ast,collections
import numpy as np
import manifold3d as mf
from shapely.geometry import box,Point,LineString,Polygon
from shapely.ops import unary_union
import construir as b
from fachada_campus import solid,part_solid,replace_part,as_mesh,louver
path=b.BASE/'Datos/Modelo_H.json';m=json.loads(path.read_text());assert m['revision']=='R17_Correccion_Fachada_Campus'
b.PARAMS.update(m['parameters']);b.NPT[:]=m['npt'];old=copy.deepcopy(m);changed=set();added=[]
def guid(name):return re.search(r'^guid: (\w+)',(b.BASE/'Materiales'/(name+'.mat.meta')).read_text(),re.M)[1]
grey=guid('H_Zocalo_Gris');concrete=guid('H_Hormigon_Beige');dark=guid('H_Carpinteria_Oscura');glass=guid('H_Vidrio_Gris');red=guid('H_Zocalo_Rojizo')
node=next(n for n in ast.parse((b.ROOT/'Tools/Veterinaria/cierre_visible_icrea_r14.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='transfer');exec(compile(ast.Module(body=[node],type_ignores=[]),'<material-transfer>','exec'))
def edit(q,body):
 prior=copy.deepcopy(q);replace_part(b,q,body.simplify(.00001));transfer(q,prior);changed.add(q['id'])
def add(body,name,mat,material,level):
 if body.is_empty() or body.volume()<1e-8:return
 b.add_mesh(as_mesh(body),'0%d_%s/Campus_R18'%(level+1,['Sotano','Primer_Piso','Segundo_Piso','Tercer_Piso','Azotea'][level]),name,mat,True,'fixed',level,0,1,'Fotos corregidas por usuario y vanos nativos CAD','Cotas verticales inferidas de foto, no alzado medido.')
 q=b.PARTS[-1];q['id']='H_%d_Campus_R18_%04d'%(level,len(added)+1);q['materialGuid']=material;m['items'].append(q);added.append(q)
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
# Undo the three exterior additions explicitly rejected in the new reference.
for q in m['items']:
 if q['name'] in ['Pano_central_sin_rejilla','Proteccion_vertical_ventana_ingreso','Volumen_naranja_oblicuo_entrada','Ventilacion_muro_naranja'] or q['id']=='H_1_Barandas_0001':disable(q)
# Keep the native seven stair treads and their handrail unchanged.
# Triangular edge is derived from their right ends and the existing laboratory roof corner.
A=np.array([16.7047,-13.9525]);B=np.array([16.7047,-17.412]);C=np.array([18.8183,-15.7127]);D=np.array([22.8818,-11.6492])
triangle=Polygon([A,B,C]);newfloor=solid(b,triangle,-.24,0)
for q in m['items']:
 if q['hidden'] or not q['active'] or q['material'] not in ['wall','floor','metal']:continue
 v=b.materialize_vertices(q)
 if v[:,1].max()<=-.24 or v[:,1].min()>=0 or not b.part_footprint(q).intersects(triangle):continue
 newfloor=newfloor-part_solid(b,q).minkowski_sum(mf.Manifold.cube((.002,.002,.002),center=True))
newfloor=newfloor.simplify(.0001)
add(newfloor,'Plataforma_triangular_costado_escalera','floor',grey,1)
# Wall thickness lies on the platform side, x >= the right edge of the treads.
side=box(16.7050,-17.412,16.8550,-13.9525)
pathBC=LineString([B,C]);pathCD=LineString([C,D]);shell=side.union(pathBC.buffer(.075,cap_style='flat')).union(pathCD.parallel_offset(.15,'right').buffer(.18,cap_style='flat'))
# Prevent any extension into the stair tread footprints.
steps=[b.part_footprint(q) for q in m['items'] if q['id'].startswith('H_1_Acceso_Principal_') and q['name'].startswith('Ingreso_7_')]
shell=shell.difference(unary_union(steps).buffer(.0003,join_style='mitre'))
wall=solid(b,shell,-1.17,.78);axis=(D-C)/np.linalg.norm(D-C);outside=np.array([axis[1],-axis[0]])
windows=[]
for q in m['items']:
 if q['level']!=0 or q['material']!='glass' or q['hidden']:continue
 v=b.materialize_vertices(q);lo,hi=v.min(0),v.max(0)
 if lo[0]>19 and hi[0]<22.8 and lo[2]<-11.9 and hi[2]>-15.6:windows.append(q)
assert len(windows)==4,[q['id'] for q in windows]
for q in sorted(windows,key=lambda q:b.materialize_vertices(q)[:,0].mean()):
 v=b.materialize_vertices(q);center=v[:,[0,2]].mean(0);mid=C+axis*np.dot(center-C,axis)+outside*.25
 half=(v[:,0].max()-v[:,0].min())/2**.5
 toolprofile=LineString([mid-axis*(half+.025),mid+axis*(half+.025)]).buffer(.45,cap_style='flat')
 lo=v[:,1].min()-.015;hi=v[:,1].max()+.015;wall=wall-solid(b,toolprofile,lo,hi)
 louver(b,[(mid-axis*half+outside*.065).tolist(),(mid+axis*half+outside*.065).tolist()],lo+.02,hi-.02,.08,'01_Sotano/Campus_R18','Rejilla_alineada_vano_laboratorio',0)
 n=b.PARTS[-1];n['id']='H_0_Campus_R18_%04d'%(len(added)+1);n['materialGuid']=dark;m['items'].append(n);added.append(n)
# Native lab glazing and walls remain intact; boolean ownership prevents overlapping surfaces.
existing=[]
for q in m['items']:
 if q in added or q['hidden'] or not q['active'] or q['material'] not in ['wall','floor','metal']:continue
 v=b.materialize_vertices(q)
 if v[:,1].max()<=-1.17 or v[:,1].min()>=.78 or not b.part_footprint(q).intersects(shell):continue
 existing.append(part_solid(b,q).minkowski_sum(mf.Manifold.cube((.0004,.0004,.0004),center=True)))
existing.append(solid(b,triangle.buffer(.001,join_style='mitre'),-.241,.001))
if existing:wall=wall-mf.Manifold.batch_boolean(existing,mf.OpType.Add)
add(wall.simplify(.001),'Cerramiento_naranja_triangulo_entrada','wall',red,1)
# Low metal rail follows the new perimeter above the opaque parapet.
pieces=[]
for p0,p1 in [(A,B),(B,C),(C,D)]:
 line=LineString([p0,p1]);strip=line.buffer(.012,cap_style='flat')
 for y in [.84,1.10]:pieces.append(solid(b,strip,y,y+.022))
 length=np.linalg.norm(p1-p0)
 for t in np.linspace(0,1,max(2,int(length/1.4)+1)):
  point=p0+t*(p1-p0);pieces.append(solid(b,Point(point).buffer(.014,resolution=4),.78,1.122))
add(mf.Manifold.batch_boolean(pieces,mf.OpType.Add).simplify(.00002),'Baranda_sobre_cerramiento_triangular','metal',grey,1)
# Uniform orange on all exposed vertical faces at the adjacent old slab return.
for q in m['items']:
 if q['id'] not in ['H_1_Losas_0001','H_1_Losas_0007','H_1_Losas_0008']:continue
 ts=b.materialize_vertices(q).reshape(-1,3,3);slots=q.get('materialGuids',[q['materialGuid']]);cols=[slots[i] for i in q.get('triangleMaterials',[0]*len(ts))];touch=False
 for i,tv in enumerate(ts):
  cc=tv.mean(0);nn=np.cross(tv[1]-tv[0],tv[2]-tv[0]);nn/=max(np.linalg.norm(nn),1e-15)
  if cc[0]>16.65 and cc[2]<-9.72 and abs(nn[1])<.1:cols[i]=red;touch=True
 if touch:
  pal=list(dict.fromkeys(cols));q['materialGuids']=pal;q['triangleMaterials']=[pal.index(g) for g in cols];changed.add(q['id'])
b.PARTS[:]=added;b.repair_float32_topology();assert {q['id'] for q in b.PARTS}=={q['id'] for q in added};newby={q['id']:q for q in b.PARTS}
for i,q in enumerate(m['items']):
 if q['id'] in newby:m['items'][i]=newby[q['id']]
added[:]=b.PARTS
for q in added:
 if q['name']=='Plataforma_triangular_costado_escalera':
  ts=b.materialize_vertices(q).reshape(-1,3,3);ns=np.cross(ts[:,1]-ts[:,0],ts[:,2]-ts[:,0]);ns/=np.maximum(np.linalg.norm(ns,axis=1,keepdims=True),1e-15)
  q['materialGuids']=[grey,red];q['triangleMaterials']=[0 if abs(n[1])>.5 else 1 for n in ns]

# Preserve every existing prefab fileID. Clone one fixed five-component object for additions.
pp=b.BASE/'Prefabs/Pabellon_H_Veterinaria.prefab';raw=pp.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n';text=raw.decode().replace('\r\n','\n');prefix=text[:text.index('--- !u!')];blocks=re.split(r'(?=^--- !u!)',text,flags=re.M)[1:]
by={int(re.search(r'&(\d+)',z)[1]):z for z in blocks};names={re.search(r'&(\d+)',z)[1]:re.search(r'  m_Name: (.*)',z)[1].strip().strip('"') for z in blocks if z.startswith('--- !u!1 ')}
items={q['id']:q for q in m['items']}
for i,z in enumerate(blocks):
 if not z.startswith(('--- !u!1 ','--- !u!23 ')):continue
 gid=re.search(r'&(\d+)',z)[1] if z.startswith('--- !u!1 ') else re.search(r'm_GameObject: \{fileID: (\d+)\}',z)[1]
 for ident in changed:
  if not names[gid].startswith(ident+'_'):continue
  q=items[ident]
  if z.startswith('--- !u!23 '):blocks[i]=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+','  m_Materials:\n'+''.join('  - {fileID: 2100000, guid: '+g+', type: 2}\n' for g in q.get('materialGuids',[q['materialGuid']])),z)
  else:blocks[i]=re.sub(r'm_IsActive: [01]','m_IsActive: '+str(int(q['active'])),z)
source_go=next(g for g,name in names.items() if name.startswith('H_1_Cierre_Icrea_R14_0001_'))
selected=[by[int(source_go)]]+[z for z in blocks if 'm_GameObject: {fileID: '+source_go+'}' in z]
tr=next(z for z in selected if z.startswith('--- !u!4 '));parent=int(re.search(r'm_Father: \{fileID: (\d+)\}',tr)[1]);children=[]
# New objects are grouped under the existing fixed-object group to preserve hierarchy IDs.
for j,q in enumerate(added):
 b.write_mesh_asset(b.BASE/'Generado/Mallas'/(q['id']+'.asset'),q);mg=b.meta(b.BASE/'Generado/Mallas'/(q['id']+'.asset'))
 ids={int(re.search(r'&(\d+)',z)[1]):700000000000040000+j*10+k for k,z in enumerate(selected)};children.append(ids[int(re.search(r'&(\d+)',tr)[1])])
 for z in selected:
  z=re.sub(r'&(\d+)',lambda x:'&'+str(ids[int(x[1])]),z,count=1);z=re.sub(r'fileID: (\d+)',lambda x:'fileID: '+str(ids.get(int(x[1]),int(x[1]))),z)
  if z.startswith('--- !u!1 '):z=re.sub(r'  m_Name: .*','  m_Name: '+q['id']+'_'+q['name'],z)
  if z.startswith(('--- !u!33 ','--- !u!64 ')):z=re.sub(r'm_Mesh: \{fileID: 4300000, guid: \w+, type: 2\}','m_Mesh: {fileID: 4300000, guid: '+mg+', type: 2}',z)
  if z.startswith('--- !u!23 '):z=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+','  m_Materials:\n'+''.join('  - {fileID: 2100000, guid: '+g+', type: 2}\n' for g in q.get('materialGuids',[q['materialGuid']])),z)
  blocks.append(z)
for i,z in enumerate(blocks):
 if z.startswith('--- !u!4 &'+str(parent)+'\n'):blocks[i]=z.replace('  m_Father:',''.join('  - {fileID: '+str(k)+'}\n' for k in children)+'  m_Father:',1)
from grupos_campus_r18 import organize
blocks=organize(blocks,added)
blocks=[re.sub(r"[ \t]+(?=\n)","",z) if int(re.search(r"&(\d+)",z)[1])>=700000000000040000 else z for z in blocks]
blocks=[by[int(re.search(r'&(\d+)',z)[1])] if int(re.search(r'&(\d+)',z)[1]) in by and ' '.join(by[int(re.search(r'&(\d+)',z)[1])].split())==' '.join(z.split()) else z for z in blocks]
pp.write_bytes((prefix+''.join(blocks)).replace('\n',nl).encode())
for ident in changed:b.write_mesh_asset(b.BASE/'Generado/Mallas'/(ident+'.asset'),items[ident])
m['revision']='R18_Entrada_Triangular_Vacios_Campus';path.write_text(json.dumps(m,ensure_ascii=False,separators=(',',':')))
report={'revision':m['revision'],'changed':sorted(changed),'added':[q['id'] for q in added],'estimated':'Parapeto +0.78 y espesor 0.15; triangulo enlazado con extremos de huellas y esquina de losa existente. Las cotas verticales de ventilacion son las del modelo CAD previo, estimadas en ausencia de alzado.','entry':'Peldaños y pasamanos de la escalera principal conservados. Se corrige solo el costado triangular, el cerramiento y su baranda.','basementWindowsPreserved':[q['id'] for q in windows],'basementGrilles':4,'centralOpening':'Se retiran los dos paños R17; se conservan remates exteriores de techo y vacios previstos del CAD.','UnityPlay':'NOT_RUN'}
rp=b.BASE/'Documentacion/Fachada_Campus_R18.json';rp.write_text(json.dumps(report,ensure_ascii=False,indent=2));b.meta(rp)
cp=b.BASE/'Documentacion/Construccion.json';c=json.loads(cp.read_text());c['parts']=len(m['items']);c['byGroup']=dict(collections.Counter(q['group'] for q in m['items']));cp.write_text(json.dumps(c,ensure_ascii=False,indent=2));print({'changed':len(changed),'added':len(added),'parts':len(m['items'])})
