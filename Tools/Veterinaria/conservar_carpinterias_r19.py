"""Retain untouched disconnected trim assemblies exactly; edit only affected assemblies."""
import numpy as np
import trimesh
from shapely.geometry import Point,LineString,Polygon
from shapely.ops import unary_union

def assemblies(b,part):
 triangles=np.asarray(b.materialize_vertices(part),dtype=np.float32).astype(float).reshape(-1,3,3)
 mesh=trimesh.Trimesh(vertices=triangles.reshape(-1,3),faces=np.arange(triangles.size//3).reshape(-1,3),process=False);mesh.merge_vertices()
 groups=trimesh.graph.connected_components(mesh.face_adjacency,nodes=np.arange(len(triangles)),min_len=1)
 result=[]
 for group in groups:
  ts=triangles[group];nn=np.cross(ts[:,1]-ts[:,0],ts[:,2]-ts[:,0]);profiles=[Polygon(t[:,[0,2]]) for t,n in zip(ts,nn) if n[1]>1e-12]
  profile=unary_union(profiles);result.append((ts,profile,float(ts[:,:,1].min()),float(ts[:,:,1].max())))
 return result

def preserve(b,model,original,posts,joins):
 prior={p['id']:p for p in original['items']}
 for part in model['items']:
  if not part['group'].endswith('/Marcos_Puertas') or part['level']>3:continue
  lev=part['level'];mask=unary_union([Point(p['center']).buffer(.18) for p in posts if p['level']==lev]+[LineString([p['start'],p['wallPoint']]).buffer(.12) for p in joins if p['level']==lev])
  if mask.is_empty:continue
  old=assemblies(b,prior[part['id']]);new=assemblies(b,part)
  affected=[q for q in new if q[1].intersects(mask) and q[2]<b.NPT[lev]+2.16 and q[3]>b.NPT[lev]-.01]
  kept=[]
  for q in old:
   touched=q[1].intersects(mask) and q[2]<b.NPT[lev]+2.16 and q[3]>b.NPT[lev]-.01
   inherited=any(q[1].intersection(z[1]).area>.000001 and q[2]<z[3] and q[3]>z[2] for z in affected)
   if not touched and not inherited:kept.append(q)
  triangles=np.concatenate([q[0] for q in kept+affected]);nn=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);nn/=np.maximum(np.linalg.norm(nn,axis=1,keepdims=True),1e-15)
  lo,hi=b.y_range(part['role'],lev,part['bottom'],part['top']);v=triangles.reshape(-1,3);v[:,1]=(v[:,1]-lo)/(hi-lo)
  part['vertices']=v.flatten().tolist();part['normals']=np.repeat(nn,3,axis=0).flatten().tolist();part['uv']=np.c_[v[:,0]/3,v[:,2]/3].flatten().tolist()
  part.pop('materialGuids',None);part.pop('triangleMaterials',None)
