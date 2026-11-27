"""Secciones horizontales y anclaje de puertas contra perfiles CAD; no reemplaza Play."""
import json,math
import numpy as np
from shapely import build_area,set_precision
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union

def section(b,p,y):
 lines=[]
 for t in b.materialize_vertices(p).reshape(-1,3,3):
  if t[:,1].min()>y or t[:,1].max()<y:continue
  pts=[]
  for a,z in zip(t,np.roll(t,-1,axis=0)):
   if (a[1]<=y<z[1]) or (z[1]<=y<a[1]):pts.append((a+(z-a)*(y-a[1])/(z[1]-a[1]))[[0,2]])
  if len(pts)==2 and np.linalg.norm(pts[0]-pts[1])>1e-8:lines.append(set_precision(LineString(pts),.000001))
 return build_area(unary_union(lines))

def opaque_native(level):
 return set_precision(unary_union([Polygon(q['outline'],q['holes']) for k in ['wall','drywall'] for q in level[k]]),.00001)

def door_parts(model,level):return [p for p in model['items'] if p['level']==level and p['role']=='door' and p['active'] and not p['hidden']]

def candidates(b,m,circulation):
 out=[]
 for lev in range(5):
  bodies=[section(b,p,b.NPT[lev]+1.) for p in m['items'] if p['level']==lev and p['active'] and not p['hidden'] and p['material'] in ['wall','glass'] and p['role']!='door'];support=unary_union(bodies)
  for p in door_parts(m,lev):
   j=int(p['name'].split('_')[1])-1;record=circulation['doors'][lev][j];a=np.array(record['hinge']);z=np.array(record['closed']);gap=support.distance(Point(a))
   if gap>.075:out.append({'id':p['id'],'level':lev,'doorIndex':j,'hingeGap':gap,'hinge':a.tolist(),'closed':z.tolist()})
 return out

def anchor_summary(b,m,circulation):
 results=[]
 for lev in range(5):
  walls=unary_union([section(b,p,b.NPT[lev]+1.) for p in m['items'] if p['level']==lev and p['active'] and not p['hidden'] and p['material'] in ['wall','glass'] and p['role']!='door'])
  frames=unary_union([section(b,p,b.NPT[lev]+1.) for p in m['items'] if p['level']==lev and p['active'] and not p['hidden'] and p['group'].endswith('/Marcos_Puertas')])
  combined=unary_union([walls.buffer(.0015,join_style='mitre'),frames.buffer(.0015,join_style='mitre')]);connected=unary_union([g for g in getattr(combined,'geoms',[combined]) if g.intersection(walls).area>.00001]);missing=[]
  for p in door_parts(m,lev):
   j=int(p['name'].split('_')[1])-1;d=circulation['doors'][lev][j];dist=connected.distance(Point(d['hinge']))
   if dist>.04:missing.append({'id':p['id'],'hinge':d['hinge'],'gap_m':dist})
  results.append({'level':lev,'doors':len(door_parts(m,lev)),'unanchoredHingeCandidates':missing})
 return results
