"""Static sampled passages and stair routes over serialized meshes; not Unity physics."""
import json,collections,re
from pathlib import Path
import numpy as np
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree
from shapely import wkt
import verificar as v
ROOT=v.ROOT;BASE=v.BASE

def main():
 model=json.loads((BASE/'Datos/Modelo_H.json').read_text());cir=json.loads((BASE/'Documentacion/Puertas_y_Niveles.json').read_text());walls=[];tops=[];heights=[];floorNames=[];landings=[];ceilings=[];ceilingTriangles=[];metalTriangles=[];metalIds=[];steppedWalls={}
 for p in model['items']:
  if p['hidden'] or not p['collider']:continue
  vs,ts=v.mesh(BASE/'Generado/Mallas'/f"{p['id']}.asset");vs=v.circulation_vertices(p,vs);tri=vs[ts,:3].astype(float);norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]);cap=tri[norm[:,1]>1e-9]
  if p['material']=='floor':
   for t in tri[norm[:,1]<-1e-9]:
    g=Polygon(t[:,[0,2]])
    if g.area>1e-10:ceilings.append(g);ceilingTriangles.append((t,p['id']))
   if re.fullmatch(r'(Oeste|Este)_\d+_descanso_curvo',p['name']):landings.append((p['name'],unary_union([Polygon(t[:,[0,2]]) for t in cap]),float(vs[:,1].max())))
   for t in cap:
    g=Polygon(t[:,[0,2]])
    if g.area>1e-10:tops.append(g);heights.append(t);floorNames.append(p['id'])
  elif p['name']=='Barandas_y_pasamanos_continuos':metalTriangles.extend(tri);metalIds.extend([p['id']]*len(tri))
  else:
   g=unary_union([Polygon(t[:,[0,2]]) for t in cap]);walls.append((p['id'],g,float(vs[:,1].min()),float(vs[:,1].max())))
   if len(cap) and np.ptp(cap[:,:,1])>.00002:
    steppedWalls[p['id']]=v.MetalSurfaceIndex(tri,[p['id']]*len(tri))
   # Flush concrete crowns around the underground technical rooms also
   # provide real collider support at street elevation.
   if p['material']=='wall':
    for t in cap[np.all(np.abs(cap[:,:,1]+1.17)<.00002,axis=1)]:
     g=Polygon(t[:,[0,2]])
     if g.area>1e-10:tops.append(g);heights.append(t);floorNames.append(p['id'])
 # Exterior approaches must also use the campus collider, not only H floors.
 tv,tf=v.terrain_local(model);tri=tv[tf];norm=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0])
 for t in tri[norm[:,1]>1e-9]:
  g=Polygon(t[:,[0,2]])
  if g.area>1e-10:tops.append(g);heights.append(t);floorNames.append('Terreno_Recortado_H')
 tree=STRtree(tops);ceilingTree=STRtree(ceilings);metal=v.MetalSurfaceIndex(metalTriangles,metalIds);wallCache={};issues=[];total=0
 def sample(x,z,expected,route,index):
  nonlocal total
  total+=1;point=Point(x,z);near=[]
  for k in tree.query(point):
   if not tops[k].buffer(.00002).covers(point):continue
   t=heights[k];n=np.cross(t[1]-t[0],t[2]-t[0]);y=t[0,1]-(n[0]*(x-t[0,0])+n[2]*(z-t[0,2]))/n[1]
   near.append((y,floorNames[k]))
  supports=[q for q in near if abs(q[0]-expected)<.201]
  if not supports:issues.append({'route':route,'sample':index,'issue':'sin_apoyo_cercano','xz':[x,z],'expectedY':expected});return
  y=min(supports,key=lambda q:abs(q[0]-expected))[0];key=round(y,4)
  if key not in wallCache:wallCache[key]=[(ident,g) for ident,g,lo,hi in walls if lo<y+1.75 and hi>y+.21]
  body=point.buffer(.25)
  for ident,g in wallCache[key]:
   if g.intersection(body).area>.00001 and (ident not in steppedWalls or steppedWalls[ident].collisions(point,y)):
    issues.append({'route':route,'sample':index,'issue':'obstaculo_capsula_estatica','object':ident,'xz':[x,z],'footY':float(y)})
  for ident in metal.collisions(point,y):issues.append({'route':route,'sample':index,'issue':'obstaculo_baranda_triangulos_3D','object':ident,'xz':[x,z],'footY':float(y)})
  for k in ceilingTree.query(point):
   if not ceilings[k].buffer(.00002).covers(point):continue
   t,ident=ceilingTriangles[k];n=np.cross(t[1]-t[0],t[2]-t[0]);yy=t[0,1]-(n[0]*(x-t[0,0])+n[2]*(z-t[0,2]))/n[1]
   if y+.21<yy<y+1.75:issues.append({'route':route,'sample':index,'issue':'intradós_bajo_rayo_central','object':ident,'xz':[x,z],'footY':float(y),'ceilingY':float(yy)})

 def door_detour(start,end,axis,y):
  from shapely.ops import nearest_points
  support=unary_union([g for g,t in zip(tops,heights) if abs(float(t[:,1].mean())-y)<.02])
  barriers=unary_union([g for ident,g,lo,hi in walls if lo<y+1.75 and hi>y+.21])
  region=Point((start+end)/2).buffer(1.5)
  free=support.buffer(.0005,join_style='mitre').buffer(-.2505,join_style='mitre').difference(barriers.buffer(.251)).intersection(region)
  if free.is_empty:return None
  aa=np.array(nearest_points(Point(start),free)[1].coords[0]);zz=np.array(nearest_points(Point(end),free)[1].coords[0])
  if max(np.linalg.norm(aa-start),np.linalg.norm(zz-end))>.20:return None
  origin=np.minimum(start,end)-1.5;pitch=.025
  seed=tuple(np.round((aa-origin)/pitch).astype(int))
  def at(cell):return origin+np.array(cell)*pitch
  starts=[(seed[0]+dx,seed[1]+dz) for dx in range(-2,3) for dz in range(-2,3) if free.covers(Point(at((seed[0]+dx,seed[1]+dz))))]
  if not starts:return None
  seed=min(starts,key=lambda c:np.linalg.norm(at(c)-aa));queue=collections.deque([seed]);parents={seed:None};found=None
  while queue:
   cell=queue.popleft();here=at(cell)
   if np.linalg.norm(here-zz)<.04:found=cell;break
   for dx,dz in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
    nxt=(cell[0]+dx,cell[1]+dz)
    if nxt not in parents and free.covers(LineString([here,at(nxt)])):parents[nxt]=cell;queue.append(nxt)
  if found is None:return None
  path=[]
  while found is not None:path.append(at(found));found=parents[found]
  path=path[::-1];line=LineString(path)
  if line.length>3 or not line.intersects(axis):return None
  return path

 routes=0;doorPaths=[]
 for level,doors in enumerate(cir['doors']):
  for j,d in enumerate(doors):
   a,z=np.array(d['hinge']),np.array(d['closed']);mid=(a+z)/2;u=(z-a)/np.linalg.norm(z-a);n=np.array([-u[1],u[0]]);routes+=1
   begin=len(issues)
   for k,t in enumerate(np.linspace(-.45,.45,10)):
    p=mid+n*t;sample(*p,model['npt'][level],f'Puerta_{level}_{j}',k)
   direct_issues=issues[begin:]
   if direct_issues and all(x.get('object','').split('_')[2:3]==['Puertas'] for x in direct_issues):
    path=door_detour(mid-n*.45,mid+n*.45,LineString([a,z]),model['npt'][level])
    if path is not None:
     del issues[begin:]
     for k,p in enumerate(path):sample(*p,model['npt'][level],f'Puerta_{level}_{j}_giro',k)
     doorPaths.append({'level':level,'doorIndex':j,'xz':[q.tolist() for q in path],'reason':'Giro para rodear hoja vecina abierta; colision de hojas incluida'})
 flights=collections.defaultdict(list)
 for s in cir['steps']:flights[s['stair']].append(s)
 for name,steps in flights.items():
  ordered=sorted(steps,key=lambda q:q['index']);routes+=1
  centers=[np.array(wkt.loads(q['tread']).representative_point().coords[0]) for q in ordered]
  for j,(a,z) in enumerate(zip(centers,centers[1:])):
   count=max(2,int(np.linalg.norm(z-a)/.08)+1)
   for k,t in enumerate(np.linspace(0,1,count)):
    p=a+(z-a)*t;y=ordered[j]['upper']+(ordered[j+1]['upper']-ordered[j]['upper'])*t;sample(*p,y,name,j*100+k)
 source=json.loads((Path(__file__).parent/'Fuentes/CAD_H.json').read_text())
 # A-03 explicitly labels this hall at +3.55. Its void is oblique, not
 # the whole bounding rectangle; test passage from the label to stair 02.
 if source.get('reviewedArchitecture',{}).get('hall02VoidA03'):
  case=next(c for c in source['eastStairs'] if c['fromLevel']==2)
  row=np.array(case['up'][0]);u=np.mean(case['up'][1],axis=0)-row.mean(axis=0);u/=np.linalg.norm(u);arrival=row.mean(axis=0)-u*.20
  labels=[np.array(t['local']) for t in source['levels'][2]['texts'] if t['text'].strip()=='HALL']
  label=min(labels,key=lambda q:np.linalg.norm(q-arrival));routes+=1
  count=max(2,int(np.ceil(np.linalg.norm(label-arrival)/.08))+1)
  for k,t in enumerate(np.linspace(0,1,count)):
   sample(*(label+(arrival-label)*t),model['npt'][2],'Hall02_A03_rotulo_a_escalera',k)
 for c in source.get('eastStairs',[]):
  i=c['fromLevel'];up=np.array(c['up']);back=np.array(c['return']);first=sorted(flights[f'Este_{i}_tramo_1'],key=lambda q:q['index'])[0];last=sorted(flights[f'Este_{i}_tramo_2'],key=lambda q:q['index'])[-1]
  direction=up[1].mean(axis=0)-up[0].mean(axis=0);direction/=np.linalg.norm(direction);a=up[0].mean(axis=0)-direction*.15;b=np.array(wkt.loads(first['tread']).representative_point().coords[0])
  direction=back[-1].mean(axis=0)-back[-2].mean(axis=0);direction/=np.linalg.norm(direction);z=back[-1].mean(axis=0)+direction*.20;y=np.array(wkt.loads(last['tread']).representative_point().coords[0])
  for name,start,end,y0,y1 in [(f'Este_{i}_acceso',a,b,model['npt'][i],first['upper']),(f'Este_{i}_llegada',y,z,last['upper'],model['npt'][i+1])]:
   routes+=1
   for k,t in enumerate(np.linspace(0,1,max(2,int(np.linalg.norm(end-start)/.08)+1))):
    p=start+(end-start)*t;sample(*p,y0+(y1-y0)*t,name,k)
 landingPaths=[]
 for name,g,midY in landings:
  prefix=name.replace('_descanso_curvo','');first=sorted(flights[prefix+'_tramo_1'],key=lambda q:q['index']);second=sorted(flights[prefix+'_tramo_2'],key=lambda q:q['index']);a=np.array(wkt.loads(first[-1]['tread']).representative_point().coords[0]);z=np.array(wkt.loads(second[0]['tread']).representative_point().coords[0]);routes+=1
  # Find a feasible route; the geometric centroid may be behind an enclosing
  # wall or central guardrail. Never remove that wall to make a straight chord.
  floor=unary_union([p for p,t in zip(tops,heights) if abs(float(t[:,1].mean())-midY)<.201]);blocked=unary_union([g for ident,g,lo,hi in walls if lo<midY+1.75 and hi>midY+.21]+[metal.barriers(midY,Point(a).buffer(7).union(Point(z).buffer(7)))]);free=floor.buffer(.0005,join_style='mitre').buffer(-.0005,join_style='mitre').buffer(-.25).difference(blocked.buffer(.251))
  from shapely.ops import nearest_points
  aa=np.array(nearest_points(Point(a),free)[1].coords[0]);zz=np.array(nearest_points(Point(z),free)[1].coords[0]);pitch=.05;origin=np.minimum(aa,zz)-3.;end=np.maximum(aa,zz)+3.
  def at(cell):return origin+np.array(cell)*pitch
  seed=tuple(np.round((aa-origin)/pitch).astype(int));goal=tuple(np.round((zz-origin)/pitch).astype(int))
  seeds=[(seed[0]+dx,seed[1]+dz) for dx in range(-2,3) for dz in range(-2,3) if free.covers(Point(at((seed[0]+dx,seed[1]+dz))))]
  if not seeds:issues.append({'route':name,'issue':'sin_celda_inicial_libre'});continue
  start=min(seeds,key=lambda c:np.linalg.norm(at(c)-aa));queue=collections.deque([start]);parents={start:None};found=None;inside={} 
  while queue:
   c=queue.popleft();here=at(c)
   if np.linalg.norm(here-zz)<.09:found=c;break
   for dx,dz in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
    nxt=(c[0]+dx,c[1]+dz)
    if nxt in parents:continue
    pt=at(nxt)
    if np.any(pt<origin) or np.any(pt>end):continue
    if nxt not in inside:inside[nxt]=free.covers(Point(pt))
    if inside[nxt] and free.covers(LineString([here,pt])):parents[nxt]=c;queue.append(nxt)
  if found is None or np.linalg.norm(aa-a)>.20 or np.linalg.norm(zz-z)>.20:
   issues.append({'route':name,'issue':'sin_ruta_con_apoyo_y_radio_0_25','pathFound':found is not None,'startShift':float(np.linalg.norm(aa-a)),'endShift':float(np.linalg.norm(zz-z))});continue
  path=[]
  while found is not None:path.append(at(found));found=parents[found]
  path=[a]+path[::-1]+[z];landingPaths.append({'name':name,'xz':[q.tolist() for q in path],'midY':midY})
  for k,pt in enumerate(path):sample(*pt,midY,name,k)
 # R6: sample across the annex roof that was previously left open at the entry.
 cad=json.loads((ROOT/'Tools/Veterinaria/Fuentes/CAD_H.json').read_text());outline=cad.get('reviewedArchitecture',{}).get('exteriorAnnexRoof',{}).get('verificationOutline')
 if outline:
  quad=np.array(outline[:4])
  for row,across in enumerate([.2,.5,.8]):
   routes+=1
   for k,along in enumerate(np.linspace(.15,.85,9)):
    a=quad[0]*(1-along)+quad[1]*along;z=quad[3]*(1-along)+quad[2]*along;point=a*(1-across)+z*across
    sample(*point,0.,f'Cubierta_ingreso_franja_{row+1}',k)
 # R9: approach from the forecourt, through the photographed side doorway,
 # to the stair landing at the same elevation, including head clearance.
 side=cad.get('reviewedArchitecture',{}).get('lateralIcrea')
 if side:
  for name,a,z in [('Lateral_Icrea_vereda_a_descanso',(24.5,-6.645),(21.1,-6.645)),
                   ('Lateral_Icrea_vereda_longitudinal',(22.5,-8.8),(22.5,-1.0))]:
   a,z=np.array(a),np.array(z);routes+=1
   for k,t in enumerate(np.linspace(0,1,int(np.ceil(np.linalg.norm(z-a)/.05))+1)):
    sample(*(a+(z-a)*t),side['gradeNPT'],name,k)
  if side.get('finishReview'):
   ramp=cad['reviewedArchitecture']['posteriorRamp'];points=np.asarray(ramp['outline'])
   start,end=(points[1]+points[-2])/2,(points[0]+points[-1])/2
   direction=(end-start)/np.linalg.norm(end-start)
   for row,across in enumerate([.3,.5,.7]):
    routes+=1
    for k,along in enumerate(np.linspace(.015,.985,300)):
     left=points[0]+along*(points[1]-points[0]);right=points[-1]+along*(points[-2]-points[-1]);point=left+(right-left)*across
     y=ramp['upperNPTEstimated']+ramp['slope']*((point-end)@direction)
     sample(*point,y,f'Rampa_CAD_8_por_ciento_franja_{row+1}',k)
   routes+=1
   for k,x in enumerate(np.linspace(22.25,21.6,20)):
    point=np.array([x,end[1]]);y=ramp['upperNPTEstimated']+ramp['slope']*min(0.,(point-end)@direction)
    sample(*point,y,'Rampa_CAD_boca_a_vereda',k)
 result={'parts':len(model['items']),'routes':routes,'samples':total,'supportJointTolerance':.001,'capsuleRadius':.25,'capsuleHeight':1.75,'stepTolerance':.20,'issues':issues,'landingPaths':landingPaths,'doorPaths':doorPaths,'doorState':'Hojas abiertas segun doorHinge/doorOpenDegrees, con collider; no simula transicion animada','scope':'Lineas de paso de puertas +/-0.45 m y ejes entre centros consecutivos de huellas, cada <=0.08 m. Apoyo e intrados reales por rayos verticales y barreras proyectadas por intervalo de altura. Busqueda de apoyo con cierre numerico de juntas de hasta 1 mm, sin cubrir vacios arquitectonicos. Barandas unidas comprobadas por triangulos recortados a la altura del cuerpo, no por la caja completa. Incluye el hall02 rotulado en A-03 hasta la escalera, accesos y desembarcos de escalera02 y busqueda de ruta de 5 cm con radio 0.25 m sobre apoyo continuo en los siete descansos curvos; se conservan sus muros y barandas. Incluye tres franjas longitudinales y boca superior de la rampa posterior CAD al 8%. No simula CharacterController ni todas las trayectorias por ambientes o giros posibles.','UnityPlay':'NOT_RUN'}
 (BASE/'Documentacion/Verificacion_Recorridos.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print({k:x for k,x in result.items() if k not in ['issues','landingPaths']});print('issues',len(issues),collections.Counter(x['issue'] for x in issues));print(issues[:12])
 if issues:raise SystemExit(1)
if __name__=='__main__':main()
