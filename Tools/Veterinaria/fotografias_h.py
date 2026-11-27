"""Photographic corrections to native plan geometry. Dimensions stay explicit."""
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon,LineString

def stair_outer_guard(b,sections,y0,y1,edge,group,name,level):
 a=b.pt(*sections[0][edge],2);z=b.pt(*sections[-1][edge],2)
 across=b.pt(*sections[0][1-edge],2)-a;across/=np.linalg.norm(across)
 # The outer face stays on the CAD edge; the 0.12 m body lies inside.
 c=a+across*.12;d=z+across*.12
 v=np.array([[a[0],y0-.18,a[1]],[c[0],y0-.18,c[1]],[d[0],y1-.18,d[1]],[z[0],y1-.18,z[1]],
             [a[0],y0+1.10,a[1]],[c[0],y0+1.10,c[1]],[d[0],y1+1.10,d[1]],[z[0],y1+1.10,z[1]]])
 faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
 m=trimesh.Trimesh(vertices=v,faces=faces,process=False);m.fix_normals()
 b.add_mesh(m,group,name,'wall',True,'fixed',level,0,1,'Fotografia fachada hacia la calle; bordes de huellas A-01/A-03','Antepecho exterior macizo; altura 1.10 y espesor 0.12 m estimados. No cambia huellas ni NPT.')

def body(b,part):
 v=b.materialize_vertices(part);mesh=trimesh.Trimesh(vertices=v,faces=np.arange(len(v)).reshape(-1,3),process=True);mesh.fix_normals()
 result=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
 if result.status()!=mf.Error.NoError:raise ValueError('Perfil fotografico no manifold: '+part['id'])
 return result

def street_screens(b,data):
 review=data['reviewedArchitecture']['photoRevision'];meshes=[]
 # One L-shaped CAD symbol was treated as an interior glass wall and hidden
 # behind the facade. Put its glazing on the same exterior plane as its bays.
 for key,index in review.get('correctedStreetWindowProfiles',{}).items():
  level=int(key);a,z=np.asarray(review['streetScreens'][-1]['axis']);footprint=LineString([a,z]).buffer(.27,cap_style='flat')
  lo=b.NPT[level]+b.PARAMS['windowSill'];hi=b.NPT[level]+b.PARAMS['windowHead'];cut=b.section(footprint,hi-lo);cut.vertices[:,1]+=lo
  tool=mf.Manifold(mf.Mesh(np.asarray(cut.vertices,dtype=np.float32),np.asarray(cut.faces,dtype=np.uint32)))
  b.PARTS[:]=[p for p in b.PARTS if not (p['level']==level and p['name']==f'CAD_Vidrio_interior_{index+1}')]
  for p in b.PARTS:
   if p['level']!=level or p['material']!='wall' or '/Columnas' in p['group'] or p['role']=='door':continue
   v=b.materialize_vertices(p)
   if v[:,1].max()<=lo or v[:,1].min()>=hi or not footprint.intersects(b.part_footprint(p)):continue
   original=body(b,p);result=original-tool
   if abs(result.volume()-original.volume())<1e-8:continue
   out=result.to_mesh();vv=np.asarray(out.vert_properties[:,:3],dtype=float);y0,y1=b.y_range(p['role'],level,p['bottom'],p['top']);vv[:,1]=(vv[:,1]-y0)/(y1-y0)
   mesh=trimesh.Trimesh(vertices=vv,faces=np.asarray(out.tri_verts),process=True);mesh.fix_normals();v=mesh.vertices[mesh.faces].reshape(-1,3);p.update(vertices=v.flatten().tolist(),normals=np.repeat(mesh.face_normals,3,axis=0).flatten().tolist(),uv=np.c_[v[:,0]/3,v[:,2]/3].flatten().tolist())
  from cad_h import window_frame
  window_frame(b,LineString([a,z]).buffer(.075,cap_style='flat'),level,900+level,[])
 for j,q in enumerate(review['streetScreens']):
  a,z=np.asarray(q['axis']);u=(z-a)/np.linalg.norm(z-a)
  footprint=LineString([a,z]).buffer(.27,cap_style='flat')
  lo,hi=review['screenSillEstimated'],review['screenHeadEstimated']
  tool=b.section(footprint,hi-lo);tool.vertices[:,1]+=lo
  cutter=mf.Manifold(mf.Mesh(np.asarray(tool.vertices,dtype=np.float32),np.asarray(tool.faces,dtype=np.uint32)))
  for p in b.PARTS:
   if p['level']!=1 or p['material']!='wall' or '/Columnas' in p['group'] or p['role']=='door':continue
   v=b.materialize_vertices(p)
   if v[:,1].max()<=lo or v[:,1].min()>=hi or not footprint.intersects(b.part_footprint(p)):continue
   original=body(b,p);result=original-cutter
   if abs(result.volume()-original.volume())<1e-8:continue
   out=result.to_mesh();vv=np.asarray(out.vert_properties[:,:3],dtype=float);y0,y1=b.y_range(p['role'],p['level'],p['bottom'],p['top']);vv[:,1]=(vv[:,1]-y0)/(y1-y0)
   mesh=trimesh.Trimesh(vertices=vv,faces=np.asarray(out.tri_verts),process=True);mesh.fix_normals();v=mesh.vertices[mesh.faces].reshape(-1,3)
   p.update(vertices=v.flatten().tolist(),normals=np.repeat(mesh.face_normals,3,axis=0).flatten().tolist(),uv=np.c_[v[:,0]/3,v[:,2]/3].flatten().tolist())
   p['note']+=' Celosia exterior de concreto cotejada con fotografias; cotas verticales estimadas.'
  # Real horizontal blades block the opening physically; no invisible plane.
  panel=LineString([a+u*.035,z-u*.035]).buffer(.075,cap_style='flat')
  count=max(2,round((hi-lo)/review['screenPitchEstimated'])+1)
  for y in np.linspace(lo+.035,hi-.035,count):
   mesh=b.section(panel,.07);mesh.vertices[:,1]+=y-.035;meshes.append(mesh)
  for x,y in [(a,a+u*.07),(z-u*.07,z)]:
   mesh=b.section(LineString([x,y]).buffer(.095,cap_style='flat'),hi-lo);mesh.vertices[:,1]+=lo;meshes.append(mesh)
 solids=[mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32))) for m in meshes]
 result=mf.Manifold.batch_boolean(solids,mf.OpType.Add).simplify(.0001)
 if result.status()!=mf.Error.NoError:raise ValueError('Celosias exteriores no validas')
 out=result.to_mesh();mesh=trimesh.Trimesh(vertices=np.asarray(out.vert_properties[:,:3]),faces=np.asarray(out.tri_verts),process=False);mesh.fix_normals()
 b.add_mesh(mesh,b.LEVEL_NAMES[1]+'/Celosias_Calle','Celosias_horizontales_concreto','wall',True,'fixed',1,0,1,'Fotos fachada hacia la calle 21/11/2026; ejes registrados de modulos CAD A-03','Identificacion de celosia confirmada visualmente; asignacion a modulos compartidos entre niveles y secciones verticales estimadas. Se conservan las columnas y el acceso de clinica.')
 b.EVIDENCE.append({'element':'Envolvente fotografica','confirmed':'Celosias horizontales de concreto en fachada larga hacia calle y antepechos macizos en escalera curva y nucleo oriental','estimated':'Secciones, alturas, paso de lamas y correspondencia de modulos de celosia entre A-02/A-03','status':'Comparar vistas finales y recorrer en Unity; no se afirma levantamiento metrico de fotos'})
