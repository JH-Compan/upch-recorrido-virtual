"""R15: elimina solo los dos salientes de H_2_Losas_0001 marcados en R14."""
import ast,copy,json,re
import numpy as np
from shapely.geometry import box,Point
from shapely.ops import unary_union
from shapely import wkt
import construir as b
from fachada_campus import solid,part_solid,replace_part
path=b.BASE/'Datos/Modelo_H.json';m=json.loads(path.read_text())
if m['revision']=='R15_Recorte_Salientes_Icrea':
 print('R15 ya aplicada.');raise SystemExit(0)
assert m['revision']=='R14_Retoque_Exterior_Icrea',m['revision']
b.PARAMS.update(m['parameters']);b.NPT[:]=m['npt']
p=next(x for x in m['items'] if x['id']=='H_2_Losas_0001');old=copy.deepcopy(p)
# Outside the straight facade edge, plus the left triangular projection.
# Only this slab is cut: no walls, roofs, stairs or other slabs are processed.
scope=box(18.5711,-2.4341,21.974,-.6531)
wall_support=unary_union([b.part_footprint(q) for q in m['items'] if q['level']==2 and q['material']=='wall' and not q['hidden']])
mask=scope.difference(wall_support)
body=part_solid(b,p);tool=solid(b,mask,3.3099,3.5501)
result=(body-tool).simplify(.00001);assert result.volume()<body.volume()-.01
replace_part(b,p,result)
# Reuse the material interpolation only; never execute the R14 building changes.
source=ast.parse((b.ROOT/'Tools/Veterinaria/cierre_visible_icrea_r14.py').read_text())
fn=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='transfer')
grey=re.search(r'^guid: (\w+)',(b.BASE/'Materiales/H_Zocalo_Gris.mat.meta').read_text(),re.M)[1]
concrete=re.search(r'^guid: (\w+)',(b.BASE/'Materiales/H_Hormigon_Beige.mat.meta').read_text(),re.M)[1]
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<transfer-R14>','exec'));transfer(p,old)
# The retained support is exactly flush with the wall, with its concrete finish.
slots=p['materialGuids'];colours=[slots[i] for i in p['triangleMaterials']]
for i,tri in enumerate(b.materialize_vertices(p).reshape(-1,3,3)):
 c=tri.mean(0)
 if scope.covers(Point(c[0],c[2])) and wall_support.distance(Point(c[0],c[2]))<.00003:colours[i]=concrete
palette=list(dict.fromkeys(colours));p['materialGuids']=palette;p['triangleMaterials']=[palette.index(g) for g in colours]
b.write_mesh_asset(b.BASE/'Generado/Mallas'/(p['id']+'.asset'),p)
m['expectedFloorCoverage'][2]=wkt.loads(m['expectedFloorCoverage'][2]).difference(mask).wkt
m['revision']='R15_Recorte_Salientes_Icrea';path.write_text(json.dumps(m,ensure_ascii=False,separators=(',',':')))
pp=b.BASE/'Prefabs/Pabellon_H_Veterinaria.prefab';raw=pp.read_bytes();nl='\r\n' if b'\r\n' in raw else '\n';s=raw.decode().replace('\r\n','\n');blocks=re.split(r'(?=^--- !u!)',s,flags=re.M)
go=next(z for z in blocks if z.startswith('--- !u!1 ') and 'm_Name: '+p['id']+'_' in z);gid=re.search(r'&(\d+)',go)[1]
for i,z in enumerate(blocks):
 if z.startswith('--- !u!23 ') and 'm_GameObject: {fileID: '+gid+'}' in z:
  blocks[i]=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+','  m_Materials:\n'+''.join('  - {fileID: 2100000, guid: '+g+', type: 2}\n' for g in p.get('materialGuids',[p['materialGuid']])),z)
pp.write_bytes(''.join(blocks).replace('\n',nl).encode())
report={'revision':m['revision'],'changedMesh':p['id'],'removedVolume_m3':body.volume()-result.volume(),'maskXZ':list(scope.bounds),'wallSupport':'Solo huella exacta de muros; sin vuelo ni margen exterior','heightRange':[3.31,3.55],'roofR14Preserved':True,'scope':'Solo recorte de los dos salientes marcados en la captura del usuario. No se desactiva la losa del edificio.','UnityPlay':'NOT_RUN'}
q=b.BASE/'Documentacion/Recorte_Icrea_R15.json';q.write_text(json.dumps(report,indent=2,ensure_ascii=False));b.meta(q);print(report)
