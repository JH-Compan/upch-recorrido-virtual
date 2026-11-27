"""UPCH H: vector provenance and inspection of A-01..A-05.
Development utility only; does not run inside Unity or change other buildings.
"""
from __future__ import annotations
import argparse, hashlib, json, math, re
from pathlib import Path
import fitz
import numpy as np
from shapely.geometry import LineString, Polygon, MultiPolygon, Point, box
from shapely.ops import unary_union, polygonize
from shapely import affinity, make_valid

PT_PER_METRE=72/2.54
# Registration from repeated column and service-patio corners (NOT independent
# bounding-box scaling). Same metric conversion on every sheet.
REG=[(36.12,57.24),(21.36,.60),(0,0),(0,0),(0,0)]
ORIGIN=(824.76,498.36)
NPT=[-3.55,0.,3.55,7.10,10.70]

def point(pg,p):
 q=p*pg.rotation_matrix
 return np.array([q.x,q.y])

def path_lines(pg,d):
 result=[]
 for it in d['items']:
  tag=it[0];pts=[]
  if tag=='l':pts=it[1:]
  elif tag=='re':
   r=it[1];pts=[r.tl,r.tr,r.br,r.bl,r.tl]
  elif tag=='qu':
   q=it[1];pts=[q.ul,q.ur,q.lr,q.ll,q.ul]
  elif tag=='c':
   a,b,c,e=it[1:]
   pts=[a*(1-t)**3+b*(3*t*(1-t)**2)+c*(3*t*t*(1-t))+e*t**3 for t in np.linspace(0,1,25)]
  if pts: result.append(LineString([tuple(np.round(point(pg,p),3)) for p in pts]))
 return result

def polys(g):
 if isinstance(g,Polygon):return [g]
 return [p for p in getattr(g,'geoms',[]) if isinstance(p,Polygon)]

def metric(g,i):
 dx,dy=REG[i]
 return affinity.affine_transform(g,[1/PT_PER_METRE,0,0,-1/PT_PER_METRE,(dx-ORIGIN[0])/PT_PER_METRE,(ORIGIN[1]-dy)/PT_PER_METRE])

def raw(g,i):
 dx,dy=REG[i]
 return affinity.affine_transform(g,[PT_PER_METRE,0,0,-PT_PER_METRE,ORIGIN[0]-dx,ORIGIN[1]-dy])

def repaired_solid(lines):
 from scipy.spatial import cKDTree
 if not lines:return Polygon()
 coords=np.array([p for l in lines for p in l.coords]);parent=list(range(len(coords)))
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 for a,b in cKDTree(coords).query_pairs(.22):parent[find(a)]=find(b)
 sums={}
 for n in range(len(coords)):sums.setdefault(find(n),[]).append(coords[n])
 means={k:np.mean(v,axis=0) for k,v in sums.items()};coords=np.array([means[find(n)] for n in range(len(coords))]);fixed=[];offset=0
 for l in lines:
  n=len(l.coords);q=coords[offset:offset+n];offset+=n
  if np.ptp(q,axis=0).max()>0:fixed.append(LineString(q))
 ps=[p for p in polygonize(unary_union(fixed)) if p.area>1 and p.buffer(-10).is_empty]
 return unary_union(ps)

def extract(source,out):
 pdf=fitz.open(source); levels=[]
 for i,pg in enumerate(pdf):
  ds=pg.get_drawings();thick=[];thin=[];recovery=[]
  for d in ds:
   if d.get('color')!=(0,0,0) or d.get('dashes')!='[] 0':continue
   w=d.get('width',0)
   if w>.70:recovery.extend(path_lines(pg,d))
   if w>1: thick.extend(path_lines(pg,d))
   elif abs(w-.6)<.001:thin.extend(path_lines(pg,d))
  # Closed narrow faces represent wall section, not the enclosed room. A 10 pt
  # negative buffer rejects rooms/shafts while retaining <=0.55 m columns and
  # T/L wall junctions. All accepted faces retain their source vertices.
  def solid(lines):
   if not lines:return Polygon()
   faces=[p for p in polygonize(unary_union(lines)) if p.area>1 and p.buffer(-10).is_empty]
   return unary_union(faces)
  structural=solid(thick)
  combined=solid(thick+thin)
  supplemental=combined.difference(structural)
  all_vertices=[]
  for d in ds:
   for ln in path_lines(pg,d):all_vertices.extend(list(ln.coords))
  doors=[]
  for d in ds:
   if d.get('dashes')!='[] 0':continue
   curves=[it for it in d['items'] if it[0]=='c']
   if not curves:continue
   for it in [curves[0]]:
    a,b=[point(pg,p) for p in curves[0][1:3]]
    c,e=[point(pg,p) for p in curves[-1][3:5]]
    t0=b-a;t1=e-c
    normals=np.column_stack(([-t0[1],t0[0]],[t1[1],-t1[0]]))
    try:
     k=np.linalg.solve(normals,e-a);centre=a+k[0]*np.array([-t0[1],t0[0]])
    except np.linalg.LinAlgError:continue
    r=np.linalg.norm(a-centre);r1=np.linalg.norm(e-centre)
    if not 15<r<47 or abs(r-r1)>.15:continue
    angle=np.dot(a-centre,e-centre)/(r*r1)
    if abs(angle)>.08:continue
    # Require an actual jamb within 0.14 m and exclude title-block geometry.
    if not 35<centre[0]<1535 or not 170<centre[1]<795:continue
    da=structural.distance(Point(a));de=structural.distance(Point(e))
    if min(da,de)>4:continue
    closed,opened=(a,e) if da<de else (e,a)
    if any(np.linalg.norm(centre-np.array(q['hinge']))<1 for q in doors):continue
    doors.append({'hinge':centre.tolist(),'closed':closed.tolist(),'opened':opened.tolist(),'width':r/PT_PER_METRE,'evidence':'arco de giro vectorial; altura de hoja no especificada'})
  labels=[]
  for b in pg.get_text('dict')['blocks']:
   for line in b.get('lines',[]):
    s=' '.join(z['text'] for z in line['spans']).strip()
    if s and any(k in s.upper() for k in ['LABORATOR','SALA','AULA','HALL','CORREDOR','CISTERNA','BOMBAS','DIRECCI','TÓPICO','RECEPCI','COMEDOR','VACIO','PARAPETO','NPT=','RAMPA']):
     r=fitz.Rect(line['bbox'])*pg.rotation_matrix
     labels.append({'text':s,'pdfCentre':[(r.x0+r.x1)/2,(r.y0+r.y1)/2]})
  level={'sheet':f'A-0{i+1}','npt':NPT[i],'registrationPoints':list(REG[i]),'structuralRepaired':[{'outline':list(p.exterior.coords),'holes':[list(r.coords) for r in p.interiors]} for p in polys(repaired_solid(recovery))],'structural':[{'outline':list(p.exterior.coords),'holes':[list(r.coords) for r in p.interiors]} for p in polys(structural)],'supplemental':[{'outline':list(p.exterior.coords),'holes':[list(r.coords) for r in p.interiors]} for p in polys(supplemental)],'doorCandidates':doors,'labels':labels}
  levels.append(level)
 data={'schema':1,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source':source.name,'metresPerPdfPoint':1/PT_PER_METRE,'originRegisteredPdfPoints':ORIGIN,'levels':levels,'status':'extraccion vectorial preliminar; requiere clasificacion arquitectonica y comprobacion en Unity'}
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2))
 return data

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('pdf',type=Path);ap.add_argument('--out',type=Path,default=Path(__file__).parent/'Fuentes/Trazado_Vectorial.json');a=ap.parse_args();d=extract(a.pdf,a.out)
 for l in d['levels']:print(l['sheet'],len(l['structural']),'secciones estructurales',len(l['supplemental']),'poligonos complementarios',len(l['doorCandidates']),'candidatos de puerta')
