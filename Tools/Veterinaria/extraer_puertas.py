import fitz,numpy as np,json,sys,math
from pathlib import Path
from shapely.geometry import Point,Polygon,LineString,box
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).parent));from extraer_planos import metric,point,raw
import argparse
ap=argparse.ArgumentParser();ap.add_argument('pdf',type=Path);ap.add_argument('--out',type=Path,default=Path(__file__).parent/'Fuentes');args=ap.parse_args();args.out.mkdir(parents=True,exist_ok=True)
D=json.loads((args.out/'Trazado_Vectorial.json').read_text());pdf=fitz.open(args.pdf)
for i,pg in enumerate(pdf):
 l=D['levels'][i];walls=unary_union([metric(Polygon(d['outline'],d['holes']),i) for kind in ['structural','supplemental'] for d in l[kind] if metric(Polygon(d['outline'],d['holes']),i).area>.025 and not metric(Polygon(d['outline'],d['holes']),i).buffer(-.050).is_empty])
 structural=unary_union([metric(Polygon(d['outline'],d['holes']),i) for d in l['structural']])

 if i==4:
  walls=unary_union([metric(box(*r).boundary.buffer(1.6),i) for r in [(223,243,425,444),(474,270,620,415),(886,270,1032,415),(1139,300,1286,402)]])
  structural=Polygon()
 candidates=[]
 for d in pg.get_drawings():
  if d['dashes']!='[] 0':continue
  groups=[];g=[]
  for it in d['items']:
   if it[0]=='c':
    if g and np.linalg.norm(point(pg,g[-1][4])-point(pg,it[1]))>.05:groups.append(g);g=[]
    g.append(it)
   elif g:groups.append(g);g=[]
  if g:groups.append(g)
  for group in groups:
   coords=[]
   for it in group:
    a,b,c,e=[point(pg,q) for q in it[1:]]
    for t in np.linspace(0,1,7):coords.append(a*(1-t)**3+3*b*t*(1-t)**2+3*c*t*t*(1-t)+e*t**3)
   points=np.array(coords);a=points[0];b=points[-1]
   A=np.c_[2*points[:,0],2*points[:,1],np.ones(len(points))];v=np.sum(points*points,axis=1)
   try:cx,cy,k=np.linalg.lstsq(A,v,rcond=None)[0]
   except:continue
   ctr=np.array([cx,cy]);rs=np.linalg.norm(points-ctr,axis=1);r=np.mean(rs)
   ang=np.unwrap(np.arctan2(points[:,1]-cy,points[:,0]-cx));sweep=abs(ang[-1]-ang[0])*180/math.pi
   if not 14.4<r<48 or max(abs(rs-r))>.35 or not 70<sweep<110:continue
   if not 40<cx<1510 or not 170<cy<790:continue
   h=metric(Point(ctr),i);ends=[metric(Point(p),i) for p in [a,b]]
   if walls.distance(h)>.35:continue
   jambs=structural if structural.distance(h)<.35 and min(structural.distance(ep) for ep in ends)<.25 else walls
   scores=[]
   for ep in ends:
    line=LineString([h,ep]);trim=LineString([line.interpolate(.12),line.interpolate(max(.13,line.length-.12))]);scores.append(trim.intersection(jambs.buffer(-.002)).length*3+jambs.distance(ep))
   c=int(np.argmin(scores));closed=ends[c];opened=ends[1-c]
   if min(walls.distance(ep) for ep in ends)>.4:continue
   if any(h.distance(Point(q['hinge']))<.08 for q in candidates):continue
   candidates.append({'hinge':list(h.coords)[0],'closed':list(closed.coords)[0],'opened':list(opened.coords)[0],'width':r/(72/2.54),'sweep':sweep,'score':scores})

 if i==2:
  for q in candidates:
   h=list(raw(Point(q['hinge']),i).coords)[0];c=list(raw(Point(q['closed']),i).coords)[0]
   if 425<h[0]<725 and 500<h[1]<530 and abs(c[1]-h[1])>5:q['closed'],q['opened']=q['opened'],q['closed']
 (args.out/f'doors_{i+1}.json').write_text(json.dumps(candidates,indent=2))
 print(i+1,len(candidates))
