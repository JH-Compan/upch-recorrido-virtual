import sys,json,fitz,numpy as np
from pathlib import Path
from shapely.geometry import Polygon,LineString
from shapely.ops import unary_union
sys.path.insert(0,str(Path(__file__).parent));import extraer_planos as e;import construir as b
import argparse
ap=argparse.ArgumentParser();ap.add_argument('pdf',type=Path);ap.add_argument('--trace',type=Path,default=Path(__file__).parent/'Fuentes/Trazado_Vectorial.json');args=ap.parse_args()
D=json.loads(args.trace.read_text());pdf=fitz.open(args.pdf)
for i,pg in enumerate(pdf):
 seg=[]
 for d in pg.get_drawings():
  if d['color']!=(0,0,0) or d['dashes']!='[] 0' or d['width']<.58:continue
  for ln in e.path_lines(pg,d):
   if len(ln.coords)!=2 or ln.length<10:continue
   a,z=np.array(ln.coords);u=(z-a)/ln.length
   if u[0]<0 or abs(u[0])<1e-6 and u[1]<0:u=-u
   seg.append((a,z,u))
 recovered=[]
 for j,(a,c,u) in enumerate(seg):
  n=np.array([-u[1],u[0]]);L0=sorted([a@u,c@u]);d0=a@n
  for bb,dd,v in seg[j+1:]:
   if abs(u[0]*v[1]-u[1]*v[0])>.001:continue
   dist=(bb@n)-d0
   if not 3.85<abs(dist)<14.5:continue
   L1=sorted([bb@u,dd@u]);lo=max(L0[0],L1[0]);hi=min(L0[1],L1[1])
   if hi-lo<10:continue
   recovered.append(Polygon([u*lo+n*d0,u*hi+n*d0,u*hi+n*(d0+dist),u*lo+n*(d0+dist)]))
 g=unary_union(recovered).intersection(e.raw(b.envelope(i),i))
 # Stair treads and their graphic breaks are not wall profiles.
 stair=b.metric(b.WEST_SLAB.union(b.WEST_HALL),2).union(b.east_opening())
 stair=stair.union(b.rect(920,579,1110,633,2)).union(b.rect(425,590,625,639,2))
 if i==0:stair=stair.union(b.rect(70,537,160,690,0))
 g=g.difference(e.raw(stair,i))
 old=unary_union([Polygon(q['outline'],q['holes']) for q in D['levels'][i]['structuralRepaired']]);g=g.difference(old)
 D['levels'][i]['pairedRecovery']=[{'outline':list(p.exterior.coords),'holes':[list(r.coords) for r in p.interiors]} for p in e.polys(g)]
 print(i,'pair recovered m2',g.area/(e.PT_PER_METRE**2))
args.trace.write_text(json.dumps(D,ensure_ascii=False,indent=2))
