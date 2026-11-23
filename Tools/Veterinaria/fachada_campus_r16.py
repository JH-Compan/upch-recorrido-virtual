"""R16: intervencion localizada del frente hacia campus sobre R15."""
import json,re,copy,ast,collections
import numpy as np
import manifold3d as mf
from shapely.geometry import box,Point,LineString
from shapely.ops import unary_union
import construir as b
from fachada_campus import solid,part_solid,replace_part,as_mesh,louver
path=b.BASE/'Datos/Modelo_H.json';m=json.loads(path.read_text());assert m['revision']=='R15_Recorte_Salientes_Icrea'
b.PARAMS.update(m['parameters']);b.NPT[:]=m['npt'];old=copy.deepcopy(m);changed=set();added=[]
def guid(name):return re.search(r'^guid: (\w+)',(b.BASE/'Materiales'/(name+'.mat.meta')).read_text(),re.M)[1]
grey=guid('H_Zocalo_Gris');concrete=guid('H_Hormigon_Beige');dark=guid('H_Carpinteria_Oscura');glass=guid('H_Vidrio_Gris');red=guid('H_Zocalo_Rojizo')
node=next(n for n in ast.parse((b.ROOT/'Tools/Veterinaria/cierre_visible_icrea_r14.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='transfer');exec(compile(ast.Module(body=[node],type_ignores=[]),'<material-transfer>','exec'))
def edit(q,body):
 prior=copy.deepcopy(q);replace_part(b,q,body.simplify(.00001));transfer(q,prior);changed.add(q['id'])
def add(body,name,mat,material,level):
 if body.is_empty() or body.volume()<1e-8:return
 b.add_mesh(as_mesh(body),'0%d_%s/Campus_R16'%(level+1,['Sotano','Primer_Piso','Segundo_Piso','Tercer_Piso','Azotea'][level]),name,mat,True,'fixed',level,0,1,'Fotos campus y plantas A-01/A-04; alturas fotograficas estimadas','Solo fachada. No se reproducen decoraciones ni objetos.')
 q=b.PARTS[-1];q['id']='H_%d_Campus_R16_%04d'%(level,len(added)+1);q['materialGuid']=material;m['items'].append(q);added.append(q)
# Narrow upper openings follow each existing glazed bay; original main windows remain.
bays=[]
for q in old['items']:
 v=b.materialize_vertices(q);lo,hi=v.min(0),v.max(0)
 if q['material']=='glass' and q['role']=='glass' and q['level'] in [1,2,3] and -10.02<lo[2]<-9.9 and hi[2]<-9.85 and lo[0]>-20 and hi[0]<20:
  if q['level']==1 and -2<lo[0]<1:continue
  bays.append((q['level'],lo[0],hi[0]))
for level,x0,x1 in bays:
 y0=b.NPT[level]+2.96;y1=b.NPT[level]+3.18;profile=box(x0,-10.102,x1,-9.7945);tool=solid(b,profile,y0,y1)
 for q in m['items'][:]:
  if q in added or q['level']!=level or q['material']!='wall' or q['hidden']:continue
  v=b.materialize_vertices(q)
  if v[:,1].min()>=y1 or v[:,1].max()<=y0 or not b.part_footprint(q).intersects(profile):continue
  body=part_solid(b,q);result=body-tool
  if body.volume()-result.volume()>1e-8:edit(q,result)
 add(solid(b,box(x0+.008,-9.935,x1-.008,-9.923),y0+.015,y1-.015),'Vano_superior_oscuro','glass',glass,level)
 # Thin dark perimeter, no decorative strips across the entry landing.
 frame=solid(b,box(x0,-9.956,x1,-9.936),y0,y1)-solid(b,box(x0+.015,-9.96,x1-.015,-9.93),y0+.015,y1-.015)
 add(frame,'Marco_vano_superior','metal',dark,level)
# First-floor central panel is opaque in photos, unlike upper metal louvers.
profile=box(-1.405,-10.021,.593,-9.871);tool=solid(b,profile,.7,2.9)
for q in m['items'][:]:
 if q in added or q['level']!=1 or q['material'] not in ['glass','metal'] or q['hidden']:continue
 if not b.part_footprint(q).intersects(profile):continue
 body=part_solid(b,q);result=body-tool
 if body.volume()-result.volume()<1e-8:continue
 if result.is_empty():q['active']=False;q['hidden']=True;changed.add(q['id'])
 else:edit(q,result)
existing=[part_solid(b,q) for q in m['items'] if q['level']==1 and q['material']=='wall' and not q['hidden'] and b.part_footprint(q).intersects(profile)]
add(tool-mf.Manifold.batch_boolean(existing,mf.OpType.Add),'Pano_opaco_central','wall',concrete,1)
# Narrow vertical light beside the central panel, interpreted from photo.
profile=box(2.7,-10.102,2.94,-9.7945);tool=solid(b,profile,.55,2.7)
for q in m['items'][:]:
 if q in added or q['level']!=1 or q['material']!='wall' or q['hidden'] or not b.part_footprint(q).intersects(profile):continue
 body=part_solid(b,q);result=body-tool
 if body.volume()-result.volume()>1e-8:edit(q,result)
add(solid(b,box(2.715,-9.952,2.925,-9.94),.565,2.685),'Luz_vertical_central','glass',glass,1)
# Dark low ventilation, on the native basement bays, not a solid plinth overlay.
for q in old['items']:
 v=b.materialize_vertices(q);lo,hi=v.min(0),v.max(0)
 if q['material']!='glass' or q['level']!=0 or not(-10.04<lo[2]<-9.94) or hi[0]>11.1 or lo[0]<-20:continue
 louver(b,[[lo[0],-9.995],[hi[0],-9.995]],lo[1],hi[1],.09,'01_Sotano/Campus_R16','Rejilla_baja_campus',0)
 n=b.PARTS[-1];n['id']='H_0_Campus_R16_%04d'%(len(added)+1);n['materialGuid']=dark;m['items'].append(n);added.append(n)
# Upper louvers retain their native bays; only dark finish is unified.
for q in m['items']:
 if '/Celosias_Campus' in q['group']:q['materialGuid']=dark;q.pop('materialGuids',None);q.pop('triangleMaterials',None);changed.add(q['id'])
# Exterior basement skin below triangular entry: finish only, no stair or slab edits.
entry=next(q for q in m['items'] if q['id']=='H_1_Losas_0008');outline=b.part_footprint(entry)
for q in m['items']:
 if q['level']!=0 or q['material']!='wall' or q['role']=='door' or q['hidden']:continue
 vs=b.materialize_vertices(q).reshape(-1,3,3);slots=q.get('materialGuids',[q['materialGuid']]);colours=[slots[i] for i in q.get('triangleMaterials',[0]*len(vs))];touched=False
 for i,t in enumerate(vs):
  c=t.mean(0);n=np.cross(t[1]-t[0],t[2]-t[0]);n/=max(np.linalg.norm(n),1e-15)
  pt=Point(c[0],c[2]);outside=Point(c[0]+n[0]*.03,c[2]+n[2]*.03)
  if c[0]>16.65 and c[2]<-9.72 and abs(n[1])<.1 and n[0]>.5 and n[2]<-.5:colours[i]=red;touched=True
 if touched:
  pal=list(dict.fromkeys(colours));q['materialGuids']=pal;q['triangleMaterials']=[pal.index(g) for g in colours];changed.add(q['id'])
# Keep the front concrete consistent, limiting finish changes to outward faces.
for q in m['items']:
 if q in added or q['level'] not in [1,2,3] or q['material']!='wall' or q['role']=='door' or q['hidden']:continue
 ts=b.materialize_vertices(q).reshape(-1,3,3);slots=q.get('materialGuids',[q['materialGuid']]);colours=[slots[i] for i in q.get('triangleMaterials',[0]*len(ts))];touched=False
 for i,t in enumerate(ts):
  c=t.mean(0);n=np.cross(t[1]-t[0],t[2]-t[0]);n/=max(np.linalg.norm(n),1e-15)
  if -22.1<c[0]<21.4 and -10.12<c[2]<-9.78 and n[2]<-.9:
   if q['level']==3 or c[0]<11.02:colours[i]=concrete;touched=True
 if touched:
  pal=list(dict.fromkeys(colours));q['materialGuids']=pal;q['triangleMaterials']=[pal.index(g) for g in colours];changed.add(q['id'])
# Repair only added meshes after float32 quantization; retain their identities.
b.PARTS[:]=added;b.repair_float32_topology();assert {q['id'] for q in b.PARTS}=={q['id'] for q in added}
newby={q['id']:q for q in b.PARTS}
for i,q in enumerate(m['items']):
 if q['id'] in newby:m['items'][i]=newby[q['id']]
added[:]=b.PARTS
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
  elif not q['active']:blocks[i]=z.replace('m_IsActive: 1','m_IsActive: 0')
source_go=next(g for g,name in names.items() if name.startswith('H_1_Cierre_Icrea_R14_0001_'))
selected=[by[int(source_go)]]+[z for z in blocks if 'm_GameObject: {fileID: '+source_go+'}' in z]
tr=next(z for z in selected if z.startswith('--- !u!4 '));parent=int(re.search(r'm_Father: \{fileID: (\d+)\}',tr)[1]);children=[]
# New objects are grouped under the existing fixed-object group to preserve hierarchy IDs.
for j,q in enumerate(added):
 b.write_mesh_asset(b.BASE/'Generado/Mallas'/(q['id']+'.asset'),q);mg=b.meta(b.BASE/'Generado/Mallas'/(q['id']+'.asset'))
 ids={int(re.search(r'&(\d+)',z)[1]):700000000000020000+j*10+k for k,z in enumerate(selected)};children.append(ids[int(re.search(r'&(\d+)',tr)[1])])
 for z in selected:
  z=re.sub(r'&(\d+)',lambda x:'&'+str(ids[int(x[1])]),z,count=1);z=re.sub(r'fileID: (\d+)',lambda x:'fileID: '+str(ids.get(int(x[1]),int(x[1]))),z)
  if z.startswith('--- !u!1 '):z=re.sub(r'  m_Name: .*','  m_Name: '+q['id']+'_'+q['name'],z)
  if z.startswith(('--- !u!33 ','--- !u!64 ')):z=re.sub(r'm_Mesh: \{fileID: 4300000, guid: \w+, type: 2\}','m_Mesh: {fileID: 4300000, guid: '+mg+', type: 2}',z)
  if z.startswith('--- !u!23 '):z=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+','  m_Materials:\n  - {fileID: 2100000, guid: '+q['materialGuid']+', type: 2}\n',z)
  blocks.append(z)
for i,z in enumerate(blocks):
 if z.startswith('--- !u!4 &'+str(parent)+'\n'):blocks[i]=z.replace('  m_Father:',''.join('  - {fileID: '+str(k)+'}\n' for k in children)+'  m_Father:',1)
from grupos_campus_r16 import organize
blocks=organize(blocks,added)
blocks=[re.sub(r"[ \t]+(?=\n)","",z) if int(re.search(r"&(\d+)",z)[1])>=700000000000020000 else z for z in blocks]
pp.write_bytes((prefix+''.join(blocks)).replace('\n',nl).encode())
for ident in changed:b.write_mesh_asset(b.BASE/'Generado/Mallas'/(ident+'.asset'),items[ident])
m['revision']='R16_Fachada_Interna_Campus';path.write_text(json.dumps(m,ensure_ascii=False,separators=(',',':')))
report={'revision':m['revision'],'changed':sorted(changed),'added':[q['id'] for q in added],'upperBays':bays,'estimated':'Bandas altas 2.96-3.18 m sobre NPT, luz vertical x2.70-2.94: proporcion fotografica, no cotas de alzado.','entry':'Geometria CAD de plataforma oblicua y siete contrahuellas conservada; solo acabado exterior inferior.','UnityPlay':'NOT_RUN'}
rp=b.BASE/'Documentacion/Fachada_Campus_R16.json';rp.write_text(json.dumps(report,ensure_ascii=False,indent=2));b.meta(rp)
cp=b.BASE/'Documentacion/Construccion.json';c=json.loads(cp.read_text());c['parts']=len(m['items']);c['byGroup']=dict(collections.Counter(q['group'] for q in m['items']));cp.write_text(json.dumps(c,ensure_ascii=False,indent=2))
print({'changed':len(changed),'added':len(added),'parts':len(m['items'])})
