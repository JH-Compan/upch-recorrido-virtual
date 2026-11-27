"""Correccion R17 de referencias fotograficas sobre R16, limitada al exterior."""
import json,re,copy,ast,collections
import numpy as np
import manifold3d as mf
from shapely.geometry import box,Point,LineString,Polygon
from shapely.ops import unary_union
import construir as b
from fachada_campus import solid,part_solid,replace_part,as_mesh,louver
path=b.BASE/'Datos/Modelo_H.json';m=json.loads(path.read_text());assert m['revision']=='R16_Fachada_Interna_Campus'
b.PARAMS.update(m['parameters']);b.NPT[:]=m['npt'];old=copy.deepcopy(m);changed=set();added=[]
def guid(name):return re.search(r'^guid: (\w+)',(b.BASE/'Materiales'/(name+'.mat.meta')).read_text(),re.M)[1]
grey=guid('H_Zocalo_Gris');concrete=guid('H_Hormigon_Beige');dark=guid('H_Carpinteria_Oscura');glass=guid('H_Vidrio_Gris');red=guid('H_Zocalo_Rojizo')
node=next(n for n in ast.parse((b.ROOT/'Tools/Veterinaria/cierre_visible_icrea_r14.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='transfer');exec(compile(ast.Module(body=[node],type_ignores=[]),'<material-transfer>','exec'))
def edit(q,body):
 prior=copy.deepcopy(q);replace_part(b,q,body.simplify(.00001));transfer(q,prior);changed.add(q['id'])
def add(body,name,mat,material,level):
 if body.is_empty() or body.volume()<1e-8:return
 b.add_mesh(as_mesh(body),'0%d_%s/Campus_R17'%(level+1,['Sotano','Primer_Piso','Segundo_Piso','Tercer_Piso','Azotea'][level]),name,mat,True,'fixed',level,0,1,'Fotos corregidas por usuario y vanos nativos CAD','Cotas verticales inferidas de foto, no alzado medido.')
 q=b.PARTS[-1];q['id']='H_%d_Campus_R17_%04d'%(level,len(added)+1);q['materialGuid']=material;m['items'].append(q);added.append(q)
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
# Correct the mistaken central closure and invented vertical light from R16.
for q in m['items']:
 if q['name'] in ['Pano_opaco_central','Luz_vertical_central'] or '/Celosias_Campus' in q['group']:disable(q)
# Restore native central glass and its consolidated frames from the accepted R15 source.
prior={q['id']:q for q in json.loads((b.ROOT/'Tools/Veterinaria/Fuentes/Restauracion_Central_R17.json').read_text())}
restore={'H_1_Ventanas_0031','H_1_Ventanas_0004','H_1_Ventanas_0006','H_1_Ventanas_0007'}
for i,q in enumerate(m['items']):
 if q['id'] in restore:m['items'][i]=copy.deepcopy(prior[q['id']]);changed.add(q['id'])
opaque(box(2.7,-10.0953,2.94,-9.7945),.55,2.7,'Cierre_luz_inventada_R16',1)
# Remove the old central glazing/frame strips before closing the opaque panels.
for level in [2,3]:
 profile=box(-3.41,-10.102,.5901,-9.7944);tool=solid(b,profile,b.NPT[level],b.NPT[level+1])
 for q in m['items'][:]:
  if q in added or q['hidden'] or q['level']!=level or q['material'] not in ['glass','metal'] or not b.part_footprint(q).intersects(profile):continue
  body=part_solid(b,q);result=body-tool
  if body.volume()-result.volume()<1e-8:continue
  if result.is_empty():disable(q)
  else:edit(q,result)
# Native walls stop short of their window frames at these junctions.
for level in [2,3]:
 opaque(box(-19.4655,-10.0953,-19.0907,-9.7947),b.NPT[level],b.NPT[level+1]-.24,'Jamba_izquierda_continua',level)
 opaque(box(-3.4095,-10.0953,.5895,-9.7947),b.NPT[level]+.7,b.NPT[level+1]-.24,'Pano_central_sin_rejilla',level)
 # Cap only the exterior wall strip at the slab junction; no interior floor infill.
 cap_profile=box(-3.4095,-10.0953,.5895,-9.7947);cap=solid(b,cap_profile,b.NPT[level+1]-.24,b.NPT[level+1]);bodies=[]
 for q in m['items']:
  if q['hidden'] or not q['active'] or q['material'] not in ['wall','floor']:continue
  v=b.materialize_vertices(q)
  if v[:,1].max()<=b.NPT[level+1]-.24 or v[:,1].min()>=b.NPT[level+1] or not b.part_footprint(q).intersects(cap_profile):continue
  bodies.append(part_solid(b,q))
 if bodies:cap=cap-mf.Manifold.batch_boolean(bodies,mf.OpType.Add)
 add(cap,'Remate_cabeza_pano_central','floor',concrete,level+1)
opaque(box(19.0734,-10.0953,19.2215,-9.7969),7.1,10.46,'Encuentro_derecho_enrasado',3)
# The two metal screens correspond to the narrower right bays, not the centre.
for level in [2,3]:
 louver(b,[[3.811,-10.015],[5.722,-10.015]],b.NPT[level]+.745,b.NPT[level]+2.855,.065,'0%d_%s/Campus_R17'%(level+1,'Segundo_Piso' if level==2 else 'Tercer_Piso'),'Reja_vano_derecho',level)
 q=b.PARTS[-1];q['id']='H_%d_Campus_R17_%04d'%(level,len(added)+1);q['materialGuid']=dark;m['items'].append(q);added.append(q)
# Distinct first-floor bay: vertical metal protection, retaining its native glass.
pieces=[]
for x in np.arange(6.416,10.931,.15):pieces.append(solid(b,box(x,-10.015,x+.018,-9.99),.755,2.845))
for y in [.755,2.825]:pieces.append(solid(b,box(6.396,-10.015,10.931,-9.99),y,y+.02))
add(mf.Manifold.batch_boolean(pieces,mf.OpType.Add),'Proteccion_vertical_ventana_ingreso','metal',dark,1)
# Orange retaining/parapet volume, on the existing oblique entry perimeter.
# Keep the seven stair treads and all entry slabs byte-identical.
a=np.array([18.8183,-15.7127]);c=np.array([22.8818,-11.6492]);t=(c-a)/np.linalg.norm(c-a);inside=np.array([-t[1],t[0]])
outside=-inside;offset=outside*.15
outer=LineString([a+offset,c+offset]).buffer(.18,cap_style='flat');ret=LineString([[16.88,-13.7744],a+offset]).buffer(.075,cap_style='flat');profile=outer.union(ret)
wall=solid(b,profile,-1.17,.78)
# Two tall vents in the orange face; the existing basement skin remains behind.
for dist in [3.55,4.30]:
 mid=a+t*dist+outside*.25;seg=LineString([mid-t*.15,mid+t*.15]).buffer(.30,cap_style='flat');wall=wall-solid(b,seg,-.80,-.28)
 # Dark inset louver, local tangent to the oblique facade.
 axis=[(mid-t*.13+outside*.065).tolist(),(mid+t*.13+outside*.065).tolist()]
 louver(b,axis,-.78,-.30,.08,'02_Primer_Piso/Campus_R17','Ventilacion_muro_naranja',1)
 q=b.PARTS[-1];q['id']='H_1_Campus_R17_%04d'%(len(added)+1);q['materialGuid']=dark;m['items'].append(q);added.append(q)
existing=[]
for q in m['items']:
 if q in added or q['hidden'] or q['material'] not in ['wall','floor','metal']:continue
 v=b.materialize_vertices(q)
 if v[:,1].max()<=-1.17 or v[:,1].min()>=.78 or not b.part_footprint(q).intersects(profile):continue
 existing.append(part_solid(b,q).minkowski_sum(mf.Manifold.cube((.0004,.0004,.0004),center=True)))
if existing:wall=wall-mf.Manifold.batch_boolean(existing,mf.OpType.Add)
add(wall.simplify(.0005),'Volumen_naranja_oblicuo_entrada','wall',red,1)
# The exposed slab fascia at the orange return has the same finish as its wall.
for q in m['items']:
 if q['id'] not in ['H_1_Losas_0001','H_1_Losas_0007','H_1_Losas_0008']:continue
 ts=b.materialize_vertices(q).reshape(-1,3,3);slots=q.get('materialGuids',[q['materialGuid']]);cols=[slots[i] for i in q.get('triangleMaterials',[0]*len(ts))];touch=False
 for i,tv in enumerate(ts):
  cc=tv.mean(0);nn=np.cross(tv[1]-tv[0],tv[2]-tv[0]);nn/=max(np.linalg.norm(nn),1e-15)
  if cc[0]>16.65 and cc[2]<-9.72 and abs(nn[1])<.1 and nn[2]<-.35:cols[i]=red;touch=True
 if touch:
  pal=list(dict.fromkeys(cols));q['materialGuids']=pal;q['triangleMaterials']=[pal.index(g) for g in cols];changed.add(q['id'])
# Repair only new meshes after float32 quantization.
b.PARTS[:]=added;b.repair_float32_topology();assert {q['id'] for q in b.PARTS}=={q['id'] for q in added};newby={q['id']:q for q in b.PARTS}
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
  else:blocks[i]=re.sub(r'm_IsActive: [01]','m_IsActive: '+str(int(q['active'])),z)
source_go=next(g for g,name in names.items() if name.startswith('H_1_Cierre_Icrea_R14_0001_'))
selected=[by[int(source_go)]]+[z for z in blocks if 'm_GameObject: {fileID: '+source_go+'}' in z]
tr=next(z for z in selected if z.startswith('--- !u!4 '));parent=int(re.search(r'm_Father: \{fileID: (\d+)\}',tr)[1]);children=[]
# New objects are grouped under the existing fixed-object group to preserve hierarchy IDs.
for j,q in enumerate(added):
 b.write_mesh_asset(b.BASE/'Generado/Mallas'/(q['id']+'.asset'),q);mg=b.meta(b.BASE/'Generado/Mallas'/(q['id']+'.asset'))
 ids={int(re.search(r'&(\d+)',z)[1]):700000000000030000+j*10+k for k,z in enumerate(selected)};children.append(ids[int(re.search(r'&(\d+)',tr)[1])])
 for z in selected:
  z=re.sub(r'&(\d+)',lambda x:'&'+str(ids[int(x[1])]),z,count=1);z=re.sub(r'fileID: (\d+)',lambda x:'fileID: '+str(ids.get(int(x[1]),int(x[1]))),z)
  if z.startswith('--- !u!1 '):z=re.sub(r'  m_Name: .*','  m_Name: '+q['id']+'_'+q['name'],z)
  if z.startswith(('--- !u!33 ','--- !u!64 ')):z=re.sub(r'm_Mesh: \{fileID: 4300000, guid: \w+, type: 2\}','m_Mesh: {fileID: 4300000, guid: '+mg+', type: 2}',z)
  if z.startswith('--- !u!23 '):z=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+','  m_Materials:\n  - {fileID: 2100000, guid: '+q['materialGuid']+', type: 2}\n',z)
  blocks.append(z)
for i,z in enumerate(blocks):
 if z.startswith('--- !u!4 &'+str(parent)+'\n'):blocks[i]=z.replace('  m_Father:',''.join('  - {fileID: '+str(k)+'}\n' for k in children)+'  m_Father:',1)
from grupos_campus_r17 import organize
blocks=organize(blocks,added)
blocks=[re.sub(r"[ \t]+(?=\n)","",z) if int(re.search(r"&(\d+)",z)[1])>=700000000000030000 else z for z in blocks]
blocks=[by[int(re.search(r'&(\d+)',z)[1])] if int(re.search(r'&(\d+)',z)[1]) in by and ' '.join(by[int(re.search(r'&(\d+)',z)[1])].split())==' '.join(z.split()) else z for z in blocks]
pp.write_bytes((prefix+''.join(blocks)).replace('\n',nl).encode())
for ident in changed:b.write_mesh_asset(b.BASE/'Generado/Mallas'/(ident+'.asset'),items[ident])
m['revision']='R17_Correccion_Fachada_Campus';path.write_text(json.dumps(m,ensure_ascii=False,separators=(',',':')))
report={'revision':m['revision'],'changed':sorted(changed),'added':[q['id'] for q in added],'estimated':'Rejas reposicionadas en vanos estrechos derechos. Volumen naranja: cota superior +0.78; inferior -1.17. Proporcion de foto; no alzado medido.','entry':'Siete huellas y losas de entrada conservadas. Nuevo cerramiento oblicuo sobre el perimetro existente.','UnityPlay':'NOT_RUN'}
rp=b.BASE/'Documentacion/Fachada_Campus_R17.json';rp.write_text(json.dumps(report,ensure_ascii=False,indent=2));b.meta(rp)
cp=b.BASE/'Documentacion/Construccion.json';c=json.loads(cp.read_text());c['parts']=len(m['items']);c['byGroup']=dict(collections.Counter(q['group'] for q in m['items']));cp.write_text(json.dumps(c,ensure_ascii=False,indent=2));print({'changed':len(changed),'added':len(added),'parts':len(m['items'])})
