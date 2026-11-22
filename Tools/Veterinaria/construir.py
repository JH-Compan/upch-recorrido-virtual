#!/usr/bin/env python3
"""Build H in the inspected UPCH project. No Unity dependencies are added.
Python is used for vector preparation and offline serialization. Unity's Editor
regenerates the same assets from Datos/Modelo_H.json without Python.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math,re,struct,sys
from pathlib import Path
import numpy as np
import fitz
import trimesh
from shapely import affinity,make_valid,set_precision
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union
import mapbox_earcut

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Assets/UPCH/Veterinaria'
DATA=BASE/'Datos'
SCALE=72/2.54
REG=[(36.12,57.24),(21.36,.60),(0.,0.),(0.,0.),(0.,0.)]
ORIGIN=(824.76,498.36)
NPT=[-3.55,0.,3.55,7.1,10.7]
LEVEL_NAMES=['01_Sotano','02_Primer_Piso','03_Segundo_Piso','04_Tercer_Piso','05_Azotea']
ANCHOR=[-8.720671,1.17,144.78705]
PARAMS={'slabThickness':.24,'doorHeight':2.15,'windowSill':.70,'windowHead':2.90,'roofWallHeight':2.60,'beamDepth':.40,'railingHeight':1.10,'sourceWallLowHeight':2.20,'stairSlabThickness':.20}
MATS={'wall':'08662882bf39bd747b7f698c5562ad94','floor':'1598c48964f6bec48b597f568adaf921','metal':'012d18913d3db4640b7467fcd7917545','glass':'d1b9e06e823bed44f869d425de7da733'}
EAST_CASES=[]
ARCH_REVIEW={}
NATIVE_BEAMS=[]
ROOF_NATIVE=False
ROOF_VOID_PROFILES=[]
ROOF_SUPPORT_PROFILE=Polygon()
PARTS=[];STEPS=[];DOORS=[];FLOORS=[];WALLS=[];OPENINGS=[];GROUND_PATCHES=[];LINTELS=[[] for _ in range(5)];EVIDENCE=[];COUNTS=collections.Counter()

def uid(path):return hashlib.sha256(('UPCH-H-20261118:'+str(path).replace('\\','/')).encode()).hexdigest()[:32]
def meta(path,kind=None):
 path=Path(path);m=path.with_name(path.name+'.meta')
 if m.exists():return re.search(r'^guid: (\w+)',m.read_text(),re.M)[1]
 g=uid(path.relative_to(ROOT));m.parent.mkdir(parents=True,exist_ok=True)
 if path.is_dir():tail='folderAsset: yes\nDefaultImporter:\n  externalObjects: {}\n'
 elif path.suffix=='.asset':tail='NativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 4300000\n'
 elif path.suffix=='.prefab':tail='PrefabImporter:\n  externalObjects: {}\n'
 elif path.suffix=='.cs':tail='MonoImporter:\n  externalObjects: {}\n  serializedVersion: 2\n  defaultReferences: []\n  executionOrder: 0\n  icon: {instanceID: 0}\n'
 else:tail='TextScriptImporter:\n  externalObjects: {}\n'
 m.write_text(f'fileFormatVersion: 2\nguid: {g}\n'+tail+'  userData: \n  assetBundleName: \n  assetBundleVariant: \n');return g

def polygons(g):
 g=make_valid(g)
 if isinstance(g,Polygon):return [g] if g.area>1e-9 else []
 return [p for part in getattr(g,'geoms',[]) for p in polygons(part)]
def metric(g,i):
 dx,dy=REG[i];return affinity.affine_transform(g,[1/SCALE,0,0,-1/SCALE,(dx-ORIGIN[0])/SCALE,(ORIGIN[1]-dy)/SCALE])
def raw(g,i):
 dx,dy=REG[i];return affinity.affine_transform(g,[SCALE,0,0,-SCALE,ORIGIN[0]-dx,ORIGIN[1]-dy])
def pt(x,y,i):return np.array(metric(Point(x,y),i).coords[0])
def poly(points,i):return metric(Polygon(points),i)
def rect(x0,y0,x1,y1,i):return metric(box(x0,y0,x1,y1),i)
def section(p,height=1.,_repair=0):
 p=p.simplify(.0003,preserve_topology=True)
 m=trimesh.creation.extrude_polygon(p,height=height,engine='earcut')
 # trimesh XY is architectural XZ, extrusion +Z is Unity +Y.
 m.vertices=m.vertices[:,[0,2,1]]
 m.faces=m.faces[:,[0,2,1]]
 facev=m.vertices[m.faces]
 area=np.linalg.norm(np.cross(facev[:,1]-facev[:,0],facev[:,2]-facev[:,0]),axis=1)
 m.update_faces(area>1e-10)
 # Earcut may span a collinear boundary vertex at a CAD hole bridge. Split
 # that cap edge so side faces and cap share the same edge subdivisions.
 for _ in range(8):
  counts=np.bincount(m.edges_unique_inverse)
  boundary=m.edges_unique[counts==1]
  if not len(boundary):break
  changed=False
  for a,c in boundary:
   vec=m.vertices[c]-m.vertices[a];den=np.dot(vec,vec)
   if den<1e-14:continue
   for b in np.unique(boundary):
    if b in (a,c):continue
    t=np.dot(m.vertices[b]-m.vertices[a],vec)/den
    if not 1e-6<t<1-1e-6 or np.linalg.norm(m.vertices[a]+t*vec-m.vertices[b])>1e-6:continue
    faceids=np.where(np.sum(np.isin(m.faces,[a,c]),axis=1)==2)[0]
    if len(faceids)!=1:continue
    fi=faceids[0];face=list(m.faces[fi]);k=next(k for k in range(3) if set([face[k],face[(k+1)%3]])=={a,c})
    start,end,opposite=face[k],face[(k+1)%3],face[(k+2)%3]
    m.faces=np.concatenate([np.delete(m.faces,fi,axis=0),[[start,b,opposite],[b,end,opposite]]]);changed=True;break
   if changed:break
  if not changed:break
 counts=np.bincount(m.edges_unique_inverse)
 if np.any(counts>2):
  # A CAD hole can touch the outside at one vertex, producing four faces on
  # one vertical edge. A local 0.6 mm closure removes that pinched junction.
  if _repair>=3:raise ValueError('Perfil CAD no manifold; revisar seccion antes de exportar.')
  return section(p.buffer(.0006,join_style='mitre'),height,_repair+1)
 m.fix_normals();return m

def y_range(role,level,lo=0,hi=1):
 h=NPT[level+1]-NPT[level]-PARAMS['slabThickness'] if level<4 else PARAMS['roofWallHeight']
 y=NPT[level]
 if role=='wall':return y,y+h
 if role=='slab':return y-PARAMS['slabThickness'],y
 if role=='sill':return y,y+PARAMS['windowSill']
 if role=='glass':return y+PARAMS['windowSill'],y+PARAMS['windowHead']
 if role=='windowFrameVertical':return y+PARAMS['windowSill']+.045,y+PARAMS['windowHead']-.045
 if role=='windowFrameBottom':return y+PARAMS['windowSill'],y+PARAMS['windowSill']+.045
 if role=='windowFrameTop':return y+PARAMS['windowHead']-.045,y+PARAMS['windowHead']
 if role=='windowLintel':return y+PARAMS['windowHead'],y+h
 if role=='doorLintel':return y+PARAMS['doorHeight'],y+h
 if role=='door':return y+.025,y+PARAMS['doorHeight']-.025
 if role=='beam':return y+h-PARAMS['beamDepth'],y+h
 if role=='railing':return y,y+PARAMS['railingHeight']
 if role=='roofCover':return y+PARAMS['roofWallHeight'],y+PARAMS['roofWallHeight']+.14
 return lo,hi

def add_mesh(mesh,group,name,mat='wall',collider=True,role='fixed',level=0,lo=0,hi=1,source='',note='',active=True,hidden=False):
 if len(mesh.faces)==0:return
 mesh.remove_unreferenced_vertices()
 COUNTS[group]+=1;ident=f'H_{level}_{re.sub("[^A-Za-z0-9_]","_",group.split("/")[-1])}_{COUNTS[group]:04}'
 # Geometry is kept indexed in memory; JSON and .asset use hard face normals.
 v=mesh.vertices[mesh.faces].reshape(-1,3)
 n=np.repeat(mesh.face_normals,3,axis=0)
 keep=np.linalg.norm(np.cross(v[1::3]-v[::3],v[2::3]-v[::3]),axis=1)>1e-18 if name in ['Marcos_puertas_consolidados','HV_Marcos_consolidados','Celosias_horizontales_concreto'] else np.linalg.norm(np.cross(v[1::3]-v[::3],v[2::3]-v[::3]),axis=1)>1e-10
 v=v.reshape(-1,3,3)[keep].reshape(-1,3);n=n.reshape(-1,3,3)[keep].reshape(-1,3)
 if len(v)==0:return
 uv=np.c_[v[:,0]/3,v[:,2]/3]
 p={'id':ident,'name':name,'group':group,'materialGuid':MATS[mat],'material':mat,'collider':collider,'role':role,'level':level,'bottom':lo,'top':hi,'active':active,'hidden':hidden,'source':source,'note':note,'vertices':np.round(v,7).flatten().tolist(),'normals':np.round(n,7).flatten().tolist(),'uv':np.round(uv,7).flatten().tolist()}
 if name in ['Marcos_puertas_consolidados','HV_Marcos_consolidados','Celosias_horizontales_concreto']:p['vertices']=v.flatten().tolist()
 PARTS.append(p)

def add_poly(g,group,name,mat='wall',collider=True,role='wall',level=0,lo=0,hi=1,source='',note='',**kw):
 # CAD intersections contain submillimetre collinear fragments. Snap at 0.1 mm
 # before triangulation so float32 export cannot open the cap of a prism.
 g=set_precision(make_valid(g),.0001)
 for j,p in enumerate(polygons(g)):
  if p.area<.00001:continue
  add_mesh(section(p),group,name+(f'_{j+1}' if j else ''),mat,collider,role,level,lo,hi,source,note,**kw)

def fixed_prism(g,y0,y1,group,name,mat='floor',collider=True,level=0,source='',note=''):
 if y1-y0<1e-5:return
 if mat=='floor' and collider and y1<=-1.17+.00001:GROUND_PATCHES.append(g)
 add_poly(g,group,name,mat,collider,'fixed',level,y0,y1,source,note)

def wall_line(a,b,width,group,name,level,mat='wall',height=None,base=None,role='wall',source='',note=''):
 line=LineString([a,b]);g=line.buffer(width/2,cap_style='flat',join_style='mitre')
 if height is None:add_poly(g,group,name,mat,True,role,level,source=source,note=note)
 else:fixed_prism(g,NPT[level] if base is None else base,(NPT[level] if base is None else base)+height,group,name,mat,True,level,source,note)
 return g

# Contours are independent, measured/traced from the five vector sheets.
# Coordinates remain in each original PDF page's rotated display frame.
CONTOURS=[
 [(171.72,155.4),(1410.72,218.16),(1410.72,265.92),(1529.88,272.16),(1529.88,611.88),(1410.72,611.88),(1410.72,708.72),(1393.2,708.72),(1447.2,771.24),(1321.92,896.52),(1198.08,772.56),(1100.76,772.56),(1100.76,727.2),(156.72,727.2),(156.72,684.6),(100.56,684.6),(93.72,687.36),(43.08,677.4)],
 [(186.84,212.28),(1576.68,282.6),(1576.68,288.24),(1425.72,288.24),(1425.72,516.24),(1384.92,540.36),(1425.72,579.84),(1425.72,744.96),(1276.92,893.16),(1212.96,829.32),(1127.88,829.32),(1127.88,784.08),(170.76,784.08),(170.76,627.72),(83.88,627.72)],
 [(209.76,212.28),(1517.88,278.4),(1517.88,516.24),(1349.28,516.24),(1349.28,566.76),(1447.92,665.4),(1447.92,735.6),(1429.92,735.6),(1429.92,784.56),(905.4,784.56),(841.56,784.56),(841.56,718.08),(728.16,718.08),(728.16,784.56),(191.88,784.56),(191.88,637.68),(192.6,516.24),(135.0,516.24)],
 [(209.76,212.28),(1517.88,278.4),(1517.88,516.24),(1349.28,516.24),(1349.28,566.76),(1447.92,665.4),(1447.92,735.6),(1429.92,735.6),(1429.92,784.56),(905.4,784.56),(841.56,784.56),(841.56,718.08),(728.16,718.08),(728.16,784.56),(191.88,784.56),(191.88,637.68),(192.6,516.24),(135.0,516.24)],
 [(208.2,212.28),(1517.88,278.4),(1517.88,516.24),(1349.28,516.24),(1349.28,566.76),(1447.92,665.4),(1447.92,735.6),(1429.92,735.6),(1429.92,784.56),(903.48,784.56),(841.56,784.56),(841.56,718.08),(728.16,718.08),(728.16,784.56),(191.88,784.56),(191.88,637.68),(192.6,516.24),(135.0,516.24)]
]
# Stair 03 has a common plan origin with an oblique straight pair and a
# semicircular landing. These anchors follow the repeatable A-03/A-04 box.
WEST_CURVES=[[(85.314,719.466),(80.912,737.421),(86.805,756.338),(100.626,768.616)],[(100.626,768.616),(114.447,780.894),(133.927,784.516),(151.238,778.029)],[(151.238,778.029),(168.549,771.541),(180.849,756.008),(183.196,737.671)]]
def bezier_points(curves):
 result=[]
 for curve in curves:
  a,b,c,d=np.array(curve)
  result.extend([tuple(a*(1-t)**3+3*b*t*(1-t)**2+3*c*t*t*(1-t)+d*t**3) for t in np.linspace(0,1,33)])
 return result
WEST_ARC=bezier_points(WEST_CURVES)
WEST_SLAB=Polygon([(100.32,658.8)]+WEST_ARC+[(183.12,655.56)])
WEST_HALL=Polygon([(135,516.24),(192.6,516.24),(192.6,637.68),(194,658.8),(96,658.8)])
EAST_LOWER=[((1304.88+(1365.84-1304.88)*t,649.44+(710.52-649.44)*t),(1328.88+(1389.96-1328.88)*t,625.44+(686.40-625.44)*t)) for t in np.linspace(0,1,12)]
EAST_UPPER=[((1332.24+(1393.20-1332.24)*t,606.24+(667.20-606.24)*t),(1356.24+(1417.20-1356.24)*t,582.12+(643.20-582.12)*t)) for t in np.linspace(0,1,12)]
CLINIC_SECTIONS=[((x,y),(xx,289.68)) for x,y,xx in [(185.88,219.12,168.36),(195.60,219.72,178.44),(205.68,220.20,188.76),(215.76,220.68,198.96),(225.96,221.16,209.16),(236.04,221.64,219.36),(246.12,222.24,229.56),(256.20,222.72,239.76)]]

def flight_footprint(sections):return Polygon([q[0] for q in sections]+[q[1] for q in sections[::-1]])
def east_landing():
 a=np.array(EAST_LOWER[-1][0]);b=np.array(EAST_UPPER[-1][1]);c=(a+b)/2;v=(a-c);normal=np.array([v[1],-v[0]])
 arc=[c+v*math.cos(t)+normal*math.sin(t) for t in np.linspace(0,math.pi,49)]
 return Polygon([tuple(q) for q in arc]+[EAST_UPPER[-1][0],EAST_LOWER[-1][1]]),arc
def east_opening(floor=None):
 if EAST_CASES:
  cases=[c for c in EAST_CASES if floor is None and c['fromLevel']==1 or floor is not None and (c['fromLevel']==floor or c['toLevel']==floor)]
  return unary_union([unary_union([flight_footprint(c['up']),flight_footprint(c['return']),Polygon(c['landingOutline'])]) for c in cases]).buffer(.025)
 land,_=east_landing()
 return metric(unary_union([flight_footprint(EAST_LOWER),flight_footprint(EAST_UPPER),land]).buffer(.10),2)

HOLE_DATA={
 0:[[(1410.72,273.24),(1522.8,278.88),(1522.8,521.52),(1410.72,521.52)],[(1410.72,528.6),(1524.12,528.6),(1524.12,606.24),(1410.72,606.24)]],
 1:[[(827.28,721.68),(876.84,721.68),(876.84,776.88),(827.28,776.88)]],
 2:[[(848.64,516.24),(1142,516.24),(1142,634.2),(848.64,634.2)],[(1147.80,516.60),(1170.48,516.60),(1288.08,634.20),(1147.80,634.20)],[(1149,642),(1291,642),(1429.92,784.56),(1149,784.56)],[(848.64,722.16),(898.2,722.16),(898.2,777.48),(848.64,777.48)],[(728,250),(841,256),(841,267),(728,261)]],
 3:[[(430,516.24),(716,516.24),(716,634.2),(430,634.2)],[(848.64,516.24),(1142,516.24),(1142,634.2),(848.64,634.2)],[(848.64,722.16),(898.2,722.16),(898.2,777.48),(848.64,777.48)],[(728,250),(841,256),(841,267),(728,261)]],
 4:[[(430,516.24),(570,516.24),(570,634.2),(430,634.2)],[(848.64,516.24),(992,516.24),(992,634.2),(848.64,634.2)],[(848.64,722.16),(898.2,722.16),(898.2,777.48),(848.64,777.48)],[(728,250),(841,256),(841,267),(728,261)]]
}


def envelope(i):
 p=poly(CONTOURS[i],i)
 if i>=1:
  # Registration of the shared west stair is based on A-03; it is not resized.
  p=p.union(metric(WEST_HALL,2)).union(metric(WEST_SLAB,2))
 return make_valid(p)

def make_slabs():
 for i in range(5):
  p=envelope(i)
  if i==4 and not ROOF_SUPPORT_PROFILE.is_empty:p=p.union(ROOF_SUPPORT_PROFILE)
  if i==1:
   p=p.union(unary_union([poly(q,0) for q in HOLE_DATA[0]]))
   if ARCH_REVIEW.get('entryPlatform'):p=p.union(Polygon(ARCH_REVIEW['entryPlatform']['outline']))
  holes=[poly(q,i) for q in HOLE_DATA.get(i,[])]
  if i==4 and ROOF_VOID_PROFILES:holes=list(ROOF_VOID_PROFILES)
  if i>=1:holes.append(metric(WEST_SLAB,2).buffer(-.012))
  # Diagonal stair 02 has its own landings, never a horizontal infill slab.
  if i in (1,2,3):holes.append(east_opening(i))
  if i==1:
   clinic=flight_footprint(CLINIC_SECTIONS[:-1])
   a,b=np.array(CLINIC_SECTIONS[0]);c,d=np.array(CLINIC_SECTIONS[1])
   approach=Polygon([a-(c-a),b-(d-b),b,a])
   holes.append(metric(clinic.union(approach),1))
   if ARCH_REVIEW.get('posteriorRamp'):holes.append(Polygon(ARCH_REVIEW['posteriorRamp']['outline']))
   else:
    a=pt(550,203,0);u=np.array([1.,-.0504]);u/=np.linalg.norm(u);b=a+u*29.75;n=np.array([-u[1],u[0]])*.60
    holes.append(Polygon([a-n,a+n,b+n,b-n]))
  p=p.difference(unary_union(holes))
  for c in EAST_CASES:
   if c['fromLevel']!=i:continue
   a,b=np.array(c['up'][0]);direction=np.mean(c['up'][1],axis=0)-np.mean(c['up'][0],axis=0);direction/=np.linalg.norm(direction)
   p=p.union(Polygon([a,b,b-direction*.20,a-direction*.20]))

  if i==0:
   # The two explicit technical floors use -4.50, not basement -3.55.
   for j,h in enumerate(holes):fixed_prism(h,-4.50-.24,-4.50,LEVEL_NAMES[i]+'/Losas',f'Tecnico_NPT_menos_4_50_{j+1}',level=i,source='A-01 NPT=-4.50')
  add_poly(p,LEVEL_NAMES[i]+'/Losas','Losa_contorno_y_vacios','floor',True,'slab',i,source=f'A-0{i+1}',note='Espesor configurable estimado; cara superior coincide con NPT.')
  FLOORS.append(p)
  OPENINGS.append(unary_union(holes))


def load_sections(trace):
 for i,l in enumerate(trace['levels']):
  # Clear teaching rooms checked against A-03/A-04. Some black 0.72 pt chair
  # profiles polygonize as tiny structural sections. These are furniture,
  # not repeated columns. Preserve the actual perimeter and its jambs.
  clear_rooms=[]
  if i in (2,3):
   front=508 if i==2 else 443
   clear_rooms=[[(141,front),(425,front),(425,230),(209,219)],
                [(435,front),(717,front),(717,243),(435,230)],
                [(999 if i==2 else 849,443),(1214,443),(1214,267),(999 if i==2 else 849,252)],
                [(1227,443),(1513,443),(1513,282),(1227,267)]]
  furniture_exclusion=unary_union([poly(q,i).buffer(-.18) for q in clear_rooms])
  structurals=[metric(Polygon(q['outline'],q['holes']),i) for key in ['structural','structuralRepaired'] for q in l.get(key,[])]
  # Recover open interior wall profiles; outer thin profiles remain windows.
  recovered=unary_union([metric(Polygon(q['outline'],q['holes']),i) for q in l.get('pairedRecovery',[])]).intersection(envelope(i).buffer(-.45))
  supplements=[metric(Polygon(q['outline'],q['holes']),i) for q in l['supplemental']]
  # Suppress open door leaves, cabinet outlines and isolated drafting slivers.
  thin=[]
  for j,p in enumerate(supplements):
   if p.area<.055 or p.buffer(-.035).is_empty:continue
   if not p.buffer(-.18).is_empty and p.area>.30:continue
   thin.append((j,p))
  W=unary_union(structurals+[recovered]).intersection(envelope(i).buffer(.012)).difference(furniture_exclusion)
  W=W.difference(metric(WEST_SLAB,2).buffer(.005))
  # A-05 section pen weights differ: its perimeter is a single 0.60 pt path.
  if i==4:W=Polygon()
  windows=[];drywall=[];rail=[];glass_partitions=[];low_dividers=[]
  for j,p in thin:
   if i==4:continue
   outer=p.intersection(envelope(i).boundary.buffer(.42))
   if p.area>.18 and outer.area>.12:
    windows.append(outer);p=p.difference(outer)
   if p.area<.10:continue
   if i==0 and j in [90,91]:continue # canil equipment, not room partition
   if i==3 and j in [44,51,52,53,54]:continue # ARMARIO outlines
   if i==2 and j in [30,40,44,47,55,37]:low_dividers.append(p);continue
   if i==3 and j in [46,47]:glass_partitions.append(p);continue
   if i in [2,3] and j in ([36] if i==2 else [62,68]):glass_partitions.append(p);continue
   if i>=2 and p.distance(OPENINGS[i].boundary)<.08 and p.area>.20:
    rail.append(p);continue
   if p.area>.23:drywall.append(p)
  W=W.difference(unary_union(low_dividers+glass_partitions+rail))
  D=unary_union(drywall).difference(W).difference(furniture_exclusion)
  for j,p in enumerate(low_dividers):
   fixed_prism(p,NPT[i],NPT[i]+1.60,LEVEL_NAMES[i]+'/Divisorios_1_60',f'Divisorio_bajo_{j+1}','wall',True,i,f'A-0{i+1}: DIVISORIO H=1.60 m')
  for j,p in enumerate(glass_partitions):
   add_poly(p,LEVEL_NAMES[i]+'/Cerramientos_Vidrio',f'Division_vidrio_{j+1}','glass',True,'wall',i,source=f'A-0{i+1}: VIDRIO TEMPLADO',note='Altura estimada; posicion vectorial.')
  for j,p in enumerate(rail):
   rr=np.array(p.minimum_rotated_rectangle.exterior.coords)[:4];ds=[np.linalg.norm(rr[(k+1)%4]-rr[k]) for k in range(4)];k=int(np.argmax(ds));a=(rr[k]+rr[(k+3)%4])/2;b=(rr[(k+1)%4]+rr[(k+2)%4])/2
   rail_path([a,b],NPT[i],1.10,LEVEL_NAMES[i]+'/Barandas',f'Baranda_vectorial_{j+1}',i,f'A-0{i+1} BARANDA; altura estimada')
  # Fixed low walls explicitly marked H=2.20 are kept separately where known.
  if i==0:
   low=rect(535,249,684,366,0).boundary.buffer(.08).intersection(D)
   D=D.difference(low)
   add_poly(low,LEVEL_NAMES[i]+'/Muros','Muro_H_2_20_confirmado','wall',True,'fixed',i,NPT[i],NPT[i]+2.20,source='A-01 MURO H=2.20 m')
  if i==0:
   tech=unary_union([poly(q,0) for q in HOLE_DATA[0]]).buffer(.30)
   lower=W.intersection(tech)
   lower=lower.difference(rect(1380,544,1420,579,0))
   fixed_prism(lower,-4.50,-3.55,LEVEL_NAMES[i]+'/Muros','Muros_hasta_NPT_menos_4_50','wall',True,i,'A-01: niveles tecnicos -4.50')
  # Door opening rectangles are applied to both structural and drywall sections.
  cutters=[]
  for q in DOORS[i]:
   a=np.array(q['hinge']);b=np.array(q['closed']);line=LineString([a,b]);cutters.append(line.buffer(.50,cap_style='flat'))
  opening=unary_union(cutters)
  for kind,g in [('Muros',W),('Tabiques_Drywall',D)]:
   for j,p in enumerate(polygons(g)):
    short=max(p.bounds[2]-p.bounds[0],p.bounds[3]-p.bounds[1])<.72
    group=LEVEL_NAMES[i]+('/Columnas' if short else '/'+kind)
    # Restore lintel above genuine cutouts, leaving a real opening below.
    bottom=p.difference(opening)
    add_poly(bottom,group,f'{kind}_seccion_{j+1}','wall',True,'wall',i,source=f'A-0{i+1}: contorno vectorial')
    cap=p.intersection(opening)
    LINTELS[i].append(cap)
  # Add sill, glass and head only on window sections visible in that sheet.
  win=unary_union(windows).difference(W).difference(D).difference(opening)
  for j,p in enumerate(polygons(win)):
   if p.area<.12:continue
   for role,mat in [('sill','wall'),('glass','glass'),('windowLintel','wall')]:
    add_poly(p,LEVEL_NAMES[i]+'/Ventanas',f'Ventana_{j+1}_{role}',mat,True,role,i,source=f'A-0{i+1}',note='Posicion en planta vectorial; antepecho y dintel estimados configurables.')
  WALLS.append(unary_union([W,D]))


def part_footprint(part):
 vertices=materialize_vertices(part).reshape(-1,3,3)
 normal=np.cross(vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0])
 return unary_union([Polygon(t[:,[0,2]]) for t in vertices[normal[:,1]>1e-9]])


def fit_slabs_to_enclosures():
 # Native wall faces define the edge of a slab at their common junction.
 # Add only their footprint, never an infill across a courtyard or stairwell.
 supports=[[] for _ in NPT]
 for part in PARTS:
  if part['hidden'] or not part['collider'] or part['material']=='floor':continue
  vertices=materialize_vertices(part);lo,hi=vertices[:,1].min(),vertices[:,1].max()
  footprint=part_footprint(part)
  for i,y in enumerate(NPT):
   if abs(lo-y)<.00002 or i>0 and abs(hi-(y-PARAMS['slabThickness']))<.00002:supports[i].append(footprint)
 for i,items in enumerate(supports):
  if not items:continue
  original=FLOORS[i];FLOORS[i]=set_precision(make_valid(original.union(unary_union(items))),.0001)
  group=LEVEL_NAMES[i]+'/Losas'
  PARTS[:]=[p for p in PARTS if not(p['level']==i and p['role']=='slab')]
  COUNTS[group]=max([int(p['id'].split('_')[-1]) for p in PARTS if p['group']==group]+[0])
  add_poly(FLOORS[i],group,'Losa_contorno_y_vacios','floor',True,'slab',i,source=f'A-0{i+1}; encuentros con perfiles CAD de cerramientos',note='NPT conservado. Se completan solo huellas de cerramientos en sus encuentros, sin rellenar vacios libres ni recortar cotas.')
  EVIDENCE.append({'element':f'Encuentros losa nivel {i}','sheet':f'A-0{i+1}','confirmed':'Huella de los cerramientos CAD ya construidos','estimated':'Espesor de losa 0.24 m; detalle de encuentro no acotado','addedFootprintArea':float(FLOORS[i].difference(original).area),'status':'Comprobacion de continuidad geometrica; no calculo estructural'})


def rear_containment():
 if not ARCH_REVIEW.get('posteriorRamp'):return
 # Continue the actual rear boundary below level zero, not an invisible
 # movement blocker. Basement windows and existing walls remain untouched.
 rear=envelope(1).boundary.buffer(.65).intersection(box(-1.7,6.0,22.3,10.5));faces=[];existing=[]
 for part in PARTS:
  if part['hidden'] or not part['collider'] or part['material'] not in ['wall','glass']:continue
  if part['level']==1 and part['material']=='wall' and part['role'] in ['wall','sill','fixed']:faces.append(part_footprint(part))
  if part['level']==0:existing.append(part_footprint(part))
 g=set_precision(unary_union(faces).intersection(rear).difference(unary_union(existing).buffer(.0001)),.0001)
 fixed_prism(g,NPT[0],NPT[1]-PARAMS['slabThickness'],'00_Estructura_General','Cierre_inferior_del_limite_posterior_CAD','wall',True,0,'A-01/A-02: perfiles del cerramiento posterior','Continuidad inferior del cerramiento adaptada; altura inferida entre NPT. No se anade una reja ni un acceso sin evidencia. Se conserva toda ventana existente del sotano.')
 WALLS[0]=WALLS[0].union(g)


def exterior_annex_roof():
 review=ARCH_REVIEW.get('exteriorAnnexRoof')
 if not review:return
 entry=poly([(1114.80,829.32),(1276.92,991.32),(1276.92,893.16),(1212.96,829.32)],1)
 # GEOS fixed-grid buffers at one grid unit can close an entire narrow-boundary
 # opening. Drop the precision model before the buffer and verify its area.
 basement=set_precision(FLOORS[0],0);upper=set_precision(FLOORS[1],0)
 expanded=upper.buffer(.0001)
 if expanded.area-upper.area>upper.length*.0002+.001:
  raise ValueError('El buffer de encuentro cerro una abertura arquitectonica.')
 roof=set_precision(basement.difference(expanded).intersection(box(*review['bounds'])).difference(set_precision(OPENINGS[1],0)).difference(entry.buffer(.005)),.0001)
 fixed_prism(roof,review['NPTEstimated']-PARAMS['slabThickness'],review['NPTEstimated'],'02_Primer_Piso/Losas','Cubierta_exterior_sobre_laboratorio_sotano','floor',True,1,review['source'],review['limitation'])
 paths=review.get('guardEdges')
 if paths:
  for k,points in enumerate(paths):
   rail_path(points,review['NPTEstimated'],PARAMS['railingHeight'],'02_Primer_Piso/Barandas',f'Anexo_ingreso_borde_exterior_{k+1}',1,'Fotografia del ingreso: barandas sobre los dos bordes expuestos del zocalo rojo; traza en borde de huella de cubierta, altura 1.10 m estimada')
 else:
  free_edge=roof.boundary.difference(upper.buffer(.08)).difference(entry.buffer(.08))
  lines=[free_edge] if isinstance(free_edge,LineString) else list(getattr(free_edge,'geoms',[]))
  for k,line in enumerate(lines):
   if not isinstance(line,LineString) or line.length<.25:continue
   rail_path(list(line.simplify(.01,preserve_topology=True).coords),review['NPTEstimated'],PARAMS['railingHeight'],'02_Primer_Piso/Barandas',f'Plataforma_exterior_sotano_borde_{k+1}',1,'Fotografias del ingreso y borde de la huella CAD del sotano; nivel +0.00 y altura 1.10 m estimados')
 if abs(review['NPTEstimated']-NPT[1])<.0001:FLOORS[1]=FLOORS[1].union(roof)
 EVIDENCE.append({'element':'Cubierta exterior sobre laboratorio de sotano','sheet':'A-01/A-02','area':float(roof.area),'confirmed':'Huella horizontal del sotano y ausencia de rotulo VACIO en A-02 sobre el sector','estimated':'Cota +0.00 por continuidad con hall y fotografias; espesor 0.24 y baranda 1.10','status':'Adaptacion arquitectonica; confirmar cota por corte/inspeccion'})


def make_doors():
 frames={}
 for i,doors in enumerate(DOORS):
  for j,q in enumerate(doors):
   a=np.array(q['hinge']);b=np.array(q['closed']);e=np.array(q['opened']);width=np.linalg.norm(b-a)
   if width<.50:continue
   group=LEVEL_NAMES[i]+'/Puertas'
   # Resting pose is closed. Unity opens on approach around the CAD hinge;
   # the leaf no longer stands permanently across the circulation.
   u=(b-a)/width
   leaf=LineString([a+u*.025,b-u*.025]).buffer(.018,cap_style='flat')
   add_poly(leaf,group,f'Puerta_{j+1}_cerrada','wall',True,'door',i,source=f'A-0{i+1}: arco de giro',note='Hoja cerrada en reposo; apertura de proximidad en Unity, con colision. Altura y espesor estimados.')
   opened=e-a;angle=-math.degrees(math.atan2(u[0]*opened[1]-u[1]*opened[0],u@opened))
   PARTS[-1]['doorHinge']=[float(a[0]),NPT[i],float(a[1])];PARTS[-1]['doorOpenDegrees']=angle
   lintel=LineString([a,b]).buffer(.075,cap_style='flat')
   LINTELS[i].append(lintel)
   normal=np.array([-u[1],u[0]])
   frame_parts=[(Polygon([p-u*.0225-normal*.065,p+u*.0225-normal*.065,p+u*.0225+normal*.065,p-u*.0225+normal*.065]),NPT[i],NPT[i]+PARAMS['doorHeight']) for p in [a,b]]
   frame_parts.append((LineString([a,b]).buffer(.065,cap_style='flat'),NPT[i]+PARAMS['doorHeight']-.045,NPT[i]+PARAMS['doorHeight']))
   for shape,lo,hi in frame_parts:
    mesh=section(shape,hi-lo);mesh.vertices[:,1]+=lo;frames.setdefault(i,[]).append(mesh)
   COUNTS[group]+=2 # retain the original leaf IDs while consolidating the old jamb files.
 for i,meshes in frames.items():
  import manifold3d as mf
  bodies=[mf.Manifold(mf.Mesh(np.asarray(x.vertices,dtype=np.float32),np.asarray(x.faces,dtype=np.uint32))) for x in meshes]
  out=mf.Manifold.batch_boolean(bodies,mf.OpType.Add).simplify(.0001).to_mesh();mesh=trimesh.Trimesh(vertices=np.asarray(out.vert_properties[:,:3]),faces=np.asarray(out.tri_verts),process=False);mesh.fix_normals()
  add_mesh(mesh,LEVEL_NAMES[i]+'/Marcos_Puertas','Marcos_puertas_consolidados','metal',False,'fixed',i,0,1,'Vanos registrados del plano','Marcos rectangulares completos; 45 x 130 mm estimados. Una malla por nivel.')

 for i in range(5):
  full_walls=[]
  for part in PARTS:
   if part['level']==i and part['role']=='wall' and part['material']=='wall':
    triangles=np.array(part['vertices']).reshape(-1,3,3);norm=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);full_walls.extend(Polygon(t[:,[0,2]]) for t in triangles[norm[:,1]>1e-9])
  lintels=set_precision(unary_union(LINTELS[i]),.0001).difference(set_precision(unary_union(full_walls),.0001))
  add_poly(lintels,LEVEL_NAMES[i]+'/Dinteles','Dinteles_unificados_sin_solape','wall',True,'doorLintel',i,source=f'A-0{i+1}',note='Altura de vano configurable; secciones unidas para evitar caras superpuestas.')


def merge_meshes(meshes):
 return trimesh.util.concatenate(meshes) if meshes else trimesh.Trimesh()

def beam(a,b,y0,y1,width,group,name,level,source):wall_line(a,b,width,group,name,level,height=y1-y0,base=y0,source=source)

def stair_flight(left0,right0,left1,right1,y0,y1,risers,group,name,level,source,boundaries=None):
 # All horizontal edges interpolate between measured box sides. Riser height
 # follows the two NPTs, never an assumed floor-to-floor distance.
 a=np.array(left0);b=np.array(right0);c=np.array(left1);d=np.array(right1)
 if boundaries is None:boundaries=np.linspace(0,1,risers+1)
 for k,(t0,t1) in enumerate(zip(boundaries,boundaries[1:])):
  q=Polygon([a+(c-a)*t0,b+(d-b)*t0,b+(d-b)*t1,a+(c-a)*t1])
  low=y0+(y1-y0)*k/risers;top=y0+(y1-y0)*(k+1)/risers
  fixed_prism(q,min(low,top)-.18,top,group,f'{name}_peldaño_{k+1:02}','floor',True,level,source,'Contrahuella calculada entre NPT; espesor portante 0.18 m estimado.')
  STEPS.append({'stair':name,'level':level,'index':k+1,'tread':q.wkt,'lower':low,'upper':top,'riser':top-low})


def rail_path(points,y0,height,group,name,level,source):
 pts=[np.array(p) for p in points]
 for a,b in zip(pts,pts[1:]):
  if np.linalg.norm(b-a)<.02:continue
  for frac in [.28,.60,1.0]:
   fixed_prism(LineString([a,b]).buffer(.018,cap_style='flat'),y0+height*frac-.018,y0+height*frac+.018,group,name+'_travesano','metal',True,level,source)
 path=LineString(pts)
 for distance in np.linspace(0,path.length,max(2,math.ceil(path.length/1.1)+1)):
  p=path.interpolate(distance)
  fixed_prism(p.buffer(.022,resolution=3),y0,y0+height,group,name+'_poste','metal',True,level,source)


def stair_rail(a,b,y0,y1,group,name,level,source,height=1.10):
 a=np.array(a);b=np.array(b);d=b-a;length=np.linalg.norm(d)
 if length<.01:return
 n=np.array([-d[1],d[0]])/length*.019
 for h in [.55,height]:
  # A sloping closed prism, not horizontal rails floating over stairs.
  vertices=np.array([[a[0]-n[0],y0+h-.02,a[1]-n[1]],[a[0]+n[0],y0+h-.02,a[1]+n[1]],[b[0]+n[0],y1+h-.02,b[1]+n[1]],[b[0]-n[0],y1+h-.02,b[1]-n[1]],
                     [a[0]-n[0],y0+h+.02,a[1]-n[1]],[a[0]+n[0],y0+h+.02,a[1]+n[1]],[b[0]+n[0],y1+h+.02,b[1]+n[1]],[b[0]-n[0],y1+h+.02,b[1]-n[1]]])
  faces=np.array([[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]])
  m=trimesh.Trimesh(vertices=vertices,faces=faces,process=False);m.fix_normals();add_mesh(m,group,name+'_pasamanos','metal',True,level=level,source=source)
 for t in np.linspace(0,1,max(2,math.ceil(length/1.0)+1)):
  p=a+d*t;y=y0+(y1-y0)*t
  fixed_prism(Point(p).buffer(.022,resolution=3),y,y+height,group,name+'_poste','metal',True,level,source)


def west_stair():
 group='06_Escaleras_Rampas/Escalera_03_Oeste'
 # Original A-03 tread endpoints. The interrupted tread at y=710.04 is
 # completed under its graphic break, using the two adjacent straight edges.
 right=[((146.28,655.56),(183.12,655.56)),((146.28,663.36),(183.12,663.36)),((148.80,671.16),(183.12,671.16)),((147.84,678.96),(183.12,678.96)),((146.88,686.76),(183.12,686.76)),((145.92,694.56),(183.12,694.56)),((144.96,702.36),(183.12,702.36)),((144.00,710.04),(183.12,710.04)),((143.04,717.84),(183.12,717.84)),((142.08,725.64),(183.12,725.64)),((141.12,733.44),(183.12,733.44)),((140.16,741.24),(182.64,741.24))]
 left=[((83.88,735.36),(127.44,740.64)),((83.88,727.44),(125.52,732.60)),((85.20,719.76),(126.48,724.92)),((87.12,712.20),(127.44,717.12)),((89.04,704.64),(128.40,709.44)),((90.96,696.96),(129.36,701.64)),((92.88,689.40),(130.32,693.96)),((94.56,681.72),(131.16,686.16)),((96.48,674.16),(132.12,678.48)),((98.40,666.48),(133.08,670.68)),((100.32,658.80),(134.04,662.88))]
 left_outer=np.array(left[0][0]);right_outer=np.array(right[-1][1]);arc=np.array(WEST_ARC)
 ia=int(np.argmin(np.linalg.norm(arc-left_outer,axis=1)));ib=int(np.argmin(np.linalg.norm(arc-right_outer,axis=1)))
 right[-1]=(right[-1][0],tuple(arc[ib]));left[0]=(tuple(arc[ia]),left[0][1])
 landing=Polygon([tuple(q) for q in arc[ia:ib+1]]+[right[-1][0],left[0][1]])
 def flight(sections,y0,y1,name,level):
  count=len(sections)-1
  for k,(lo,hi) in enumerate(zip(sections,sections[1:])):
   q=poly([lo[0],lo[1],hi[1],hi[0]],2);a=y0+(y1-y0)*k/count;b=y0+(y1-y0)*(k+1)/count
   fixed_prism(q,max(y0,a-.18),b,group,name+f'_peldaño_{k+1:02}','floor',True,level,'A-03: vertices de huellas; NPT A-01..A-05','Distribucion de contrahuellas entre NPT; caja repetida registrada.')
   STEPS.append({'stair':name,'level':level,'index':k+1,'tread':q.wkt,'lower':a,'upper':b,'riser':b-a})
 for i in range(4):
  y0=NPT[i];y1=NPT[i+1];mid=y0+(y1-y0)*11/21
  current=right
  if i==0:
   source=[(114.84,571.92),(117.24,580.92),(116.28,588.84),(115.32,596.76),(114.36,604.68),(113.40,612.72),(112.44,620.64),(111.48,628.56),(110.40,636.48),(109.44,644.40),(108.48,652.32),(107.52,660.24)]
   current=[((x+REG[0][0],y+REG[0][1]),(156.72+REG[0][0],y+REG[0][1])) for x,y in source]
  flight(current,y0,mid,f'Oeste_{i}_tramo_1',i)
  flight(left,mid,y1,f'Oeste_{i}_tramo_2',i)
  fixed_prism(metric(landing,2),mid-.18,mid,group,f'Oeste_{i}_descanso_curvo','floor',True,i,'A-03 curva vectorial; R1.76')
  if i==0:
   transfer=poly([current[-1][0],current[-1][1],right[-1][1],right[-1][0]],2).difference(metric(landing,2))
   fixed_prism(transfer,mid-.18,mid,group,'Oeste_sotano_empalme_inferido','floor',True,0,'A-01 huellas visibles / A-02 proyeccion','Empalme sin seccion de escalera: observacion arquitectonica pendiente.')
   EVIDENCE.append({'element':'Escalera 03 sotano','sheet':'A-01/A-02','confirmed':'Primeras diez huellas rectas trazadas en A-01','estimated':'Continuacion bajo proyeccion y empalme con retorno y descanso superior; requiere seccion o inspeccion','status':'Observado'})
  if ARCH_REVIEW.get('photoRevision'):
   from fotografias_h import stair_outer_guard
   # The street photographs show solid concrete outside the stair. Retain
   # metal rails at the well. Do not project the roof annotation onto the
   # intermediate curved landing, which would suspend a rail over the void.
   stair_rail(pt(*current[0][0],2),pt(*current[-1][0],2),y0,mid,group,f'Oeste_{i}_interior_derecho',i,'A-01/A-05')
   stair_rail(pt(*left[0][1],2),pt(*left[-1][1],2),mid,y1,group,f'Oeste_{i}_interior_izquierdo',i,'A-01/A-05')
   stair_outer_guard(sys.modules[__name__],current,y0,mid,1,group,f'Oeste_{i}_antepecho_subida',i)
   stair_outer_guard(sys.modules[__name__],left,mid,y1,0,group,f'Oeste_{i}_antepecho_retorno',i)
   strip=LineString([pt(x,y,2) for x,y in arc[ia:ib+1]]).buffer(.12,cap_style='flat').intersection(metric(landing,2))
   fixed_prism(strip,mid-.18,mid+1.10,group,f'Oeste_{i}_antepecho_curvo','wall',True,i,'Fotografias 21/11/2026; arco A-03','Antepecho exterior macizo confirmado visualmente; espesor 0.12 y altura 1.10 m estimados.')
  else:
   for edge in [0,1]:
    stair_rail(pt(*current[0][edge],2),pt(*current[-1][edge],2),y0,mid,group,f'Oeste_{i}_derecho',i,'A-01/A-05',height=1.20 if i==3 else 1.10)
    stair_rail(pt(*left[0][edge],2),pt(*left[-1][edge],2),mid,y1,group,f'Oeste_{i}_izquierdo',i,'A-03/A-05',height=1.20 if i==3 else 1.10)
   rail_path([pt(x,y,2) for x,y in arc[ia:ib+1]],mid,1.20 if i==3 else 1.10,group,f'Oeste_{i}_baranda_curva',i,'A-03 curva exterior; A-05 altura 1.20')
  platform=rect(96,637.68,194,658.80,2).difference(FLOORS[i+1])
  fixed_prism(platform,y1-.24,y1,group,f'Oeste_llegada_{i+1}','floor',True,i,'A-02..A-05')


def east_stair():
 if not EAST_CASES:raise ValueError('Falta trazado de escalera 02 registrado por nivel.')
 group='06_Escaleras_Rampas/Escalera_02_Diagonal'
 for c in EAST_CASES:
  i=c['fromLevel'];y0=NPT[i];y1=NPT[i+1];rise=(y1-y0)/c['riserCount'];mid=y0+c['upRisers']*rise
  for name,lines,start in [('tramo_1',c['up'],y0),('tramo_2',c['return'],mid)]:
   for k,(a,b) in enumerate(zip(lines,lines[1:])):
    q=Polygon([a[0],a[1],b[1],b[0]]);lo=start+k*rise;hi=lo+rise
    fixed_prism(q,max(start,lo-PARAMS['stairSlabThickness']),hi,group,f'Este_{i}_{name}_peldaño_{k+1}','floor',True,i,c['evidence'],c['verticalRule'])
    STEPS.append({'stair':f'Este_{i}_{name}','level':i,'index':k+1,'tread':q.wkt,'lower':lo,'upper':hi,'riser':rise})
   for side in [0,1]:
    a=np.array(lines[0][side]);z=np.array(lines[-1][side]);da=np.array(lines[0][1-side])-a;dz=np.array(lines[-1][1-side])-z
    a+=da/np.linalg.norm(da)*.045;z+=dz/np.linalg.norm(dz)*.045
    stair_rail(a,z,start+rise,start+(len(lines)-1)*rise,group,f'Este_{i}_{name}_baranda',i,c['evidence']+'; separacion de marco 45 mm estimada')
  fixed_prism(Polygon(c['landingOutline']),mid-PARAMS['stairSlabThickness'],mid,group,f'Este_{i}_descanso_curvo','floor',True,i,'DWG: arco R1.48 de planta de llegada; encaje con extremos reales de huellas','Altura de descanso derivada de numeracion de contrahuellas y NPT; intrados 0.20 m estimado.')
  rail_path(c['outerArc'],mid,1.10,group,f'Este_{i}_baranda_curva',i,'DWG A-02/A-03 R1.48; altura de baranda estimada')
  # Riser at the landing and at the next floor is supplied by the real slab
  # edge. There is no extra overlapping tread on either interface.
  a,b=np.array(c['return'][-1]);u=(np.mean(c['return'][-1],axis=0)-np.mean(c['return'][-2],axis=0));u/=np.linalg.norm(u)
  arrival=Polygon([a,b,b+u*.45,a+u*.45]).difference(FLOORS[i+1])
  fixed_prism(arrival,y1-.24,y1,group,f'Este_llegada_{i+1}','floor',True,i,c['evidence'],'Empalme de llegada 0.45 m hacia hall; continuidad con losa verificada por apoyo.')



def central_stairs():
 # Twenty treads + final arrival riser = 21 rises. Source drawings show
 # a real intermediate landing; it is not converted into oversized treads.
 for i,right,break_right,break_left,left,ytop,ybottom in [(1,1105.20,1027.20,1001.04,923.04,579.84,628.56),(2,620.40,542.40,508.32,430.32,591.72,634.20)]:
  group=f'06_Escaleras_Rampas/Escalera_01_Central_{i}'
  rise=(NPT[i+1]-NPT[i])/21;mid=NPT[i]+10*rise
  for which,x0,x1,first in [(1,right,break_right,0),(2,break_left,left,10)]:
   xs=np.linspace(x0,x1,11)
   for k in range(10):
    q=rect(xs[k+1],ytop,xs[k],ybottom,2);lo=NPT[i]+(first+k)*rise;hi=lo+rise
    fixed_prism(q,lo-.18,hi,group,f'Central_{i}_{which}_peldaño_{k+1:02}','floor',True,i,'A-03/A-04: huellas de 7.80 pt y descanso vectorial')
    STEPS.append({'stair':f'Central_{i}','level':i,'index':first+k+1,'tread':q.wkt,'lower':lo,'upper':hi,'riser':rise})
   for yy in [ytop,ybottom]:stair_rail(pt(x0,yy,2),pt(x1,yy,2),NPT[i]+first*rise,NPT[i]+(first+10)*rise,group,'Central_pasamanos',i,'A-03/A-04')
  fixed_prism(rect(break_left,ytop,break_right,ybottom,2),mid-.18,mid,group,'Central_descanso_intermedio','floor',True,i,'A-03/A-04: descanso entre tramos')
  arrival=rect(left-84.36,ytop,left,ybottom,2).difference(FLOORS[i+1])
  fixed_prism(arrival,NPT[i+1]-.24,NPT[i+1],group,'Central_descanso_llegada','floor',True,i,'A-03/A-04')
  # Last rise is the edge of the actual arrival floor, not a duplicated tread.
  # The arrival slab edge supplies rise 21. No extra overlapping riser solid.


def technical_access():
 group='06_Escaleras_Rampas/Acceso_Tecnico_Bombas'
 a=pt(1410.72,552,0);b=pt(1410.72,574.68,0);c=pt(1453.24,552,0);d=pt(1453.24,574.68,0)
 stair_flight(a,b,c,d,-3.55,-4.50,6,group,'Bombas',0,'A-01: NPT -3.55/-4.50; conexion de 6 contrahuellas inferida')


def exterior_access():
 group='06_Escaleras_Rampas/Acceso_Principal'
 # Seven original 45-degree riser lines, cropped by their actual straight
 # side boundaries. Their total rise is the explicit -1.17 -> +0.00.
 xs=[1114.80,1128.84,1142.88,1156.92,1170.96,1185.00,1199.04,1212.96]
 ys=[991.32,977.28,963.24,949.20,935.16,921.24,907.20,893.16]
 for k in range(7):
  q=poly([(xs[k],829.32),(1276.92,ys[k]),(1276.92,ys[k+1]),(xs[k+1],829.32)],1)
  low=-1.17+1.17*k/7;top=-1.17+1.17*(k+1)/7
  fixed_prism(q,low-.20,top,group,f'Ingreso_7_contrahuellas_{k+1}','floor',True,1,'A-02: huellas vectoriales, NPT -1.17 / +0.00')
  STEPS.append({'stair':'Ingreso_principal','level':1,'index':k+1,'tread':q.wkt,'lower':low,'upper':top,'riser':top-low})
 # Photographs show steel handrails beside the main entrance flight.
 # Their plan paths follow the real two side boundaries, not the riser diagonal.
 for side,a,z in [('izquierdo',(xs[0],829.32),(xs[-1],829.32)),('derecho',(1276.92,ys[0]),(1276.92,ys[-1]))]:
  stair_rail(pt(*a,1),pt(*z,1),-1.17,0,group,'Ingreso_pasamanos_'+side,1,'A-02: bordes de tramo + fotografias; altura 1.10 y secciones estimadas')
 # Exterior pavement remains at the plan's -1.17, not a second floating slab.
 bottom=poly([(1098,829.32),(1114.80,829.32),(1276.92,991.32),(1300,1015),(1276.92,1038),(1098,858)],1)
 fixed_prism(bottom,-1.33,-1.17,group,'Descanso_vereda_NPT_menos_1_17','floor',True,1,'A-02 NPT=-1.17')
 # North-west clinic access has its own seven source steps.
 for k,(a,b) in enumerate(zip(CLINIC_SECTIONS,CLINIC_SECTIONS[1:])):
  q=poly([a[0],a[1],b[1],b[0]],1);lo=-1.17+1.17*k/7;hi=-1.17+1.17*(k+1)/7
  geometry=q.difference(FLOORS[1]) if abs(hi-NPT[1])<1e-6 else q
  fixed_prism(geometry,lo-.18,hi,'06_Escaleras_Rampas/Acceso_Clinica',f'Clinica_peldaño_{k+1}','floor',True,1,'A-02: siete huellas vectoriales; vereda -1.17 a ingreso 0.00')
  STEPS.append({'stair':'Ingreso_clinica','level':1,'index':k+1,'tread':q.wkt,'lower':lo,'upper':hi,'riser':hi-lo})
 # A-02 native ramp footprint; the vertical anchor remains an estimate.
 review=ARCH_REVIEW.get('posteriorRamp')
 if review:
  points=np.array(review['outline']);ramp=Polygon(points);start=(points[1]+points[-2])/2;end=(points[0]+points[-1])/2;direction=end-start;length=np.linalg.norm(direction);direction/=length
  m=section(ramp,.18)
  for vertex in m.vertices:vertex[1]+=review['upperNPTEstimated']+review['slope']*((vertex[[0,2]]-end)@direction)-.18
  GROUND_PATCHES.append(ramp)
  add_mesh(m,'06_Escaleras_Rampas/Rampa_Posterior','Rampa_posterior_perfil_CAD_8_por_ciento','floor',True,source=review['source'],note=review['limitation'])
  EVIDENCE.append({'element':'Rampa posterior','sheet':'A-01/A-02','confirmed':'Huella A-PISO 45E57 y pendiente 8%','estimated':f"Anclaje superior -1.17 m; extremo inferior calculado {review['upperNPTEstimated']-review['slope']*length:.4f} m, sin enlace confirmado al sotano -3.55.",'status':'Observado; no certifica itinerario publico ni continuidad al sotano'})



def architecture_complements():
 # Beams follow the projected structural grid, not a uniform window pattern.
 grid=[277.80,426.48,576.24,723.72,845.76,994.56,1143.24,1291.92,1440.60]
 for i in range(4):
  group=LEVEL_NAMES[i]+'/Vigas'
  headers=[]
  for part in PARTS:
   if part['level']==i and part['role'] in ['windowLintel','doorLintel']:
    tris=np.array(part['vertices']).reshape(-1,3,3);norm=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);headers.extend(Polygon(t[:,[0,2]]) for t in tris[norm[:,1]>1e-9])
  beam_blockers=unary_union([WALLS[i]]+headers)
  if NATIVE_BEAMS:
   stair_footprints=[part_footprint(p) for p in PARTS if p['level']==i and p['material']=='floor' and p['group'].startswith('06_Escaleras_Rampas/Escalera')]
   shafts=unary_union(stair_footprints+[metric(WEST_SLAB,2),east_opening(i+1)]).buffer(.015)
   native=NATIVE_BEAMS[i].intersection(envelope(i+1)).difference(shafts).difference(beam_blockers)
   add_poly(native,group,'Vigas_caras_CAD_A_VIGAS','wall',True,'beam',i,source=f'DWG/A-0{i+1}/A- VIGAS; caras paralelas nativas',note='Se conserva separacion entre caras del CAD; peralte 0.40 m y elevacion al intrados estimados.')
  else:
   for y in [510.0,641.4]:
    for a,b in zip(grid,grid[1:]):
     if a>1292:continue
     pa=pt(a,y,2);pb=pt(b,y,2)
     add_poly(LineString([pa,pb]).buffer(.225,cap_style='flat').difference(east_opening(i+1)).difference(beam_blockers),group,'Viga_eje_'+str(round(a))+'_'+str(round(y)),'wall',True,'beam',i,source=f'A-0{i+1}: PROY. VIGA',note='Peralte 0.40 m estimado; posiciones del eje registradas entre plantas.')
  # Transparent hall partitions explicitly labelled VIDRIO TEMPLADO.
  for xa,xb,yy in [(729,840,717)]:
   if i==0:continue
   glass=LineString([pt(xa,yy,2),pt(xb,yy,2)]).buffer(.012,cap_style='flat')
   # Keep passage gaps of 0.95/1.40 m where the door arcs occur.
   doorcuts=unary_union([LineString([q['hinge'],q['closed']]).buffer(.10,cap_style='square') for q in DOORS[i]])
   add_poly(glass.difference(doorcuts),LEVEL_NAMES[i]+'/Cerramientos_Vidrio','Hall_vidrio_templado','glass',True,'wall',i,source=f'A-0{i+1}: VIDRIO TEMPLADO',note='Altura del vidrio hasta intrados estimada.')
 # Guardrails along upper void edges (separate from floor surfaces).
 for i in [2,3]:
  for j,pts in enumerate([[(430,516.24),(716,516.24)],[(430,516.24),(430,591)],[(716,516.24),(716,634.2)],[(848.64,516.24),(1142,516.24)],[(1142,516.24),(1142,634.2)]]):
   if i==2 and j<3:continue # A-03 corridor under the projected upper void.
   if j==4:continue # A-03 joins two voids; A-04 is the council-room wall/window, not a free guard edge.
   rail_path([pt(x,y,2) for x,y in pts],NPT[i],1.10,LEVEL_NAMES[i]+'/Barandas',f'Vacio_{j+1}',i,f'A-0{i+1} BARANDA; altura estimada')
 rail_path([pt(1171.32,514.50,2),pt(1291.08,634.20,2)],NPT[2],PARAMS['railingHeight'],LEVEL_NAMES[2]+'/Barandas','Baranda_diagonal_vacio_hall02_A03',2,'A-03: dos bordes vectoriales de baranda; altura 1.10 m estimada')
 if ROOF_NATIVE:return
 # Azotea parapets: actual stated varying heights, no duplicate full walls.
 outer=envelope(4).buffer(-.12)
 parapet=envelope(4).difference(outer)
 # Do not wall over the arrival of the west staircase.
 parapet=parapet.difference(metric(WEST_HALL.union(WEST_SLAB).buffer(2),2))
 fixed_prism(parapet,NPT[4],NPT[4]+.80,'05_Azotea/Parapetos','Parapeto_perimetral_0_80','wall',True,4,'A-05 h=0.80 m')
 for j,q in enumerate(HOLE_DATA[4]):
  g=poly(q,4)
  fixed_prism(g.buffer(.075).difference(g.buffer(-.075)),10.70,11.55,'05_Azotea/Parapetos',f'Parapeto_vacio_0_85_{j+1}','wall',True,4,'A-05 h=0.85 m; asignacion por borde a revisar')
 wall_line(pt(135,516.24,2),pt(96,658.8,2),.12,'05_Azotea/Parapetos','Parapeto_llegada_oeste_0_80',4,height=.80,source='A-05 PARAPETO h=0.80 m')
 # Comedor and three temporary architectural enclosures: no tables or equipment.
 for j,(x0,y0,x1,y1,mat) in enumerate([(223,243,425,444,'wall'),(474,270,620,415,'wall'),(886,270,1032,415,'wall'),(1139,300,1286,402,'wall')]):
  shell=rect(x0,y0,x1,y1,4).boundary.buffer(.055,join_style='mitre')
  # Door opening on the sheet's lower-facing edge.
  opening=unary_union([LineString([q['hinge'],q['closed']]).buffer(.50,cap_style='flat') for q in DOORS[4]])
  add_poly(shell.difference(opening),'05_Azotea/Comedor_y_Cerramientos',('Comedor' if j==0 else f'Estructura_temporal_{j}')+'_muros','wall',True,'wall',4,source='A-05: DRYWALL / MADERA PREFABRICADA',note='Altura de cerramiento de azotea 2.60 m estimada.')
  # The unified door lintel already spans this opening; do not add a duplicate.
  add_poly(rect(x0,y0,x1,y1,4),'05_Azotea/Cubiertas',f'Cubierta_comedor_temporal_{j}','floor',True,'roofCover',4,source='A-05',note='Altura configurable estimada; cubierta de 0.14 m estimada.')
 # Explicit taller rear parapet span, replaces rather than overlays base strip.
 # It is represented as the additional 0.50 m above the 0.80 m common body.
 extra=LineString([pt(430,220,4),pt(720,235,4)]).buffer(.075,cap_style='flat')
 fixed_prism(extra,11.50,12.00,'05_Azotea/Parapetos','Parapeto_1_30_tramo_posterior','wall',True,4,'A-05 h=1.30 m')


def union_railing_components():
 """Make a railing assembly, not overlapping posts/bars or one asset per rod."""
 import manifold3d as mf
 groups=collections.defaultdict(list);retained=[]
 for p in PARTS:
  if p['material']=='metal' and p['role']=='fixed' and p['collider'] and ('/Barandas' in p['group'] or p['group'].startswith('06_Escaleras_Rampas/')):groups[(p['group'],p['level'])].append(p)
  else:retained.append(p)
 for (group,level),pieces in groups.items():
  solids=[]
  for part in pieces:
   v=materialize_vertices(part);mesh=trimesh.Trimesh(vertices=v,faces=np.arange(len(v)).reshape(-1,3),process=True);mesh.fix_normals();body=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
   if body.status()!=mf.Error.NoError:raise ValueError('Baranda no cerrada antes de unir: '+part['id'])
   solids.append(body)
  result=mf.Manifold.batch_boolean(solids,mf.OpType.Add).simplify(.0001)
  if result.status()!=mf.Error.NoError:raise ValueError('Union de baranda no valida: '+group)
  out=result.to_mesh();mesh=trimesh.Trimesh(vertices=np.asarray(out.vert_properties[:,:3]),faces=np.asarray(out.tri_verts),process=False);vv=mesh.vertices[mesh.faces].reshape(-1,3);nn=np.repeat(mesh.face_normals,3,axis=0);part=dict(pieces[0]);part.update(name='Barandas_y_pasamanos_continuos',role='fixed',bottom=0,top=1,vertices=vv.flatten().tolist(),normals=nn.flatten().tolist(),uv=np.c_[vv[:,0]/3,vv[:,2]/3].flatten().tolist(),source=f'{len(pieces)} piezas de barandas del tramo; referencias originales CAD/PDF y parametros de seccion',note='Postes y travesanos unidos en una malla cerrada; alturas y secciones estimadas. Regenerar desde fuentes para cambiar sus parametros.')
  retained.append(part)
 PARTS[:]=retained


def repair_float32_topology():
 """Split zero-area T junctions after final float32 quantization.

 No architectural openings are filled: a boundary vertex is only inserted
 into a collinear existing edge (maximum residual 2 micrometres).
 """
 result=[];repairs=0;splits=0
 for part in PARTS:
  if part['hidden']:result.append(part);continue
  vertices=np.asarray(materialize_vertices(part),dtype=np.float32).astype(float);faces=np.arange(len(vertices)).reshape(-1,3);mesh=trimesh.Trimesh(vertices=vertices,faces=faces,process=True)
  triangles=mesh.vertices[mesh.faces];areas=np.linalg.norm(np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]),axis=1);removed_zero=bool(np.any(areas<=1e-18));original_mesh=mesh.copy()
  mesh.update_faces(areas>1e-18);mesh.remove_unreferenced_vertices()
  if mesh.is_watertight and not removed_zero:result.append(part);continue
  # Quantization may collapse a zero-width Boolean sliver onto an existing
  # edge. Re-regularize the serialized coordinates before joining T edges.
  if np.any(np.bincount(mesh.edges_unique_inverse)>2):
   import manifold3d as mf
   body=mf.Manifold(mf.Mesh(np.asarray(original_mesh.vertices,dtype=np.float32),np.asarray(original_mesh.faces,dtype=np.uint32)))
   if body.status()==mf.Error.NoError:
    out=body.simplify(.0001).to_mesh()
    candidate=trimesh.Trimesh(vertices=np.asarray(out.vert_properties[:,:3]),faces=np.asarray(out.tri_verts),process=True)
    if candidate.is_watertight and abs(candidate.volume-mesh.volume)<1e-6:mesh=candidate
  for _ in range(64):
   counts=np.bincount(mesh.edges_unique_inverse);boundary=mesh.edges_unique[counts==1]
   if not len(boundary):break
   candidates=np.unique(boundary);changed=False
   for a,c in boundary:
    delta=mesh.vertices[c]-mesh.vertices[a];den=float(delta@delta)
    if den<1e-16:continue
    for b in candidates:
     if b in (a,c):continue
     t=float((mesh.vertices[b]-mesh.vertices[a])@delta/den)
     if not 1e-6<t<1-1e-6 or np.linalg.norm(mesh.vertices[b]-(mesh.vertices[a]+t*delta))>2e-6:continue
     found=np.where(np.sum(np.isin(mesh.faces,[a,c]),axis=1)==2)[0]
     if len(found)!=1:continue
     face=mesh.faces[found[0]];aa,cc=int(a),int(c)
     if not any(face[k]==aa and face[(k+1)%3]==cc for k in range(3)):aa,cc=cc,aa
     d=next(int(v) for v in face if v not in (aa,cc));new=np.array([[aa,int(b),d],[int(b),cc,d]])
     mesh.faces=np.vstack([np.delete(mesh.faces,found[0],axis=0),new]);changed=True;repairs+=1;break
    if changed:break
   if not changed:break
  pieces=[mesh] if mesh.is_watertight else list(mesh.split(only_watertight=False,repair=False))
  if not pieces or any(not p.is_watertight for p in pieces):raise ValueError('Topologia float32 pendiente: '+part['id'])
  lo,hi=y_range(part['role'],part['level'],part['bottom'],part['top'])
  for k,piece in enumerate(pieces):
   if abs(piece.volume)<1e-9:continue
   piece.fix_normals();v=piece.vertices.copy();v[:,1]=(v[:,1]-lo)/(hi-lo);vv=v[piece.faces].reshape(-1,3);nn=np.repeat(trimesh.Trimesh(vertices=v,faces=piece.faces,process=False).face_normals,3,axis=0);p=dict(part)
   if k:p['id']=part['id']+f'_C{k+1:02}';p['name']=part['name']+f'_cuerpo_{k+1}';splits+=1
   p['vertices']=vv.flatten().tolist();p['normals']=nn.flatten().tolist();p['uv']=np.c_[vv[:,0]/3,vv[:,2]/3].flatten().tolist();result.append(p)
 PARTS[:]=result;EVIDENCE.append({'element':'Topologia serializada float32','collinearBoundaryRepairs':repairs,'separateClosedBodies':splits,'status':'Se conserva la superficie; no se rellenan huecos arquitectonicos'})


def resolve_solid_junctions():
 """Boolean differences give shared faces a single owner without hiding gaps.

 The offline preparation uses manifold3d; Unity receives ordinary closed mesh
 assets and needs no extra package. Parameters/roles remain on each part.
 """
 import manifold3d as mf
 from shapely.strtree import STRtree
 bounds=[];volumes={};cutters={};changed=0;removed=[]
 def solid(k):
  if k not in volumes:
   p=PARTS[k];v=materialize_vertices(p);faces=np.arange(len(v)).reshape(-1,3)
   if p['name'] in ['Marcos_puertas_consolidados','HV_Marcos_consolidados','Celosias_horizontales_concreto']:
    unique,inverse=np.unique(np.asarray(v,dtype=np.float32),axis=0,return_inverse=True);mesh=trimesh.Trimesh(vertices=unique,faces=inverse.reshape(-1,3),process=False)
   else:mesh=trimesh.Trimesh(vertices=v,faces=faces,process=True);mesh.fix_normals()
   result=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
   if result.status()!=mf.Error.NoError:raise ValueError(f"Malla no valida para resolver encuentros: {p['id']} / {result.status()}")
   result=mf.Manifold.batch_boolean(result.decompose(),mf.OpType.Add)
   volumes[k]=result
  return volumes[k]
 def cutter(k):
  if k not in cutters:
   p=PARTS[k];v=materialize_vertices(p);lo,hi=v[:,1].min(),v[:,1].max();eps=.00015
   if np.all((np.abs(v[:,1]-lo)<1e-6)|(np.abs(v[:,1]-hi)<1e-6)):
    g=part_footprint(p).buffer(eps,join_style='mitre');pieces=[]
    for q in polygons(g):
     mesh=section(q,hi-lo+2*eps);mesh.vertices[:,1]+=lo-eps;pieces.append(mesh)
    mesh=merge_meshes(pieces);mesh.merge_vertices();mesh.fix_normals();cutters[k]=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
   else:
    body=solid(k);center=(bounds[k][0]+bounds[k][1])/2;extent=np.maximum(bounds[k][1]-bounds[k][0],.001);cutters[k]=body.translate(-center).scale((1+2*eps/extent).tolist()).translate(center)
   if cutters[k].status()!=mf.Error.NoError:raise ValueError(f"Cortador no valido: {p['id']}")
  return cutters[k]
 def rank(k):
  p=PARTS[k]
  if p['hidden']:return 99
  if p['material']=='wall' and '/Escalera_03_Oeste' in p['group'] and '_antepecho_' in p['name']:return 5.75
  if p['material']=='glass':return 8
  if p['role']=='door':return 7
  if p['material']=='metal':return 6
  if p['role']=='slab':return 4
  if p['material']=='floor':return 5 if 'descanso' in p['name'].lower() else 5.5
  if p['role']=='wall':return 0 if '/Columnas' in p['group'] else 1
  if p['role'] in ['doorLintel','windowLintel','beam']:return 3
  return 2
 for p in PARTS:
  v=materialize_vertices(p);bounds.append(np.array([v.min(axis=0),v.max(axis=0)]))
 tree=STRtree([box(q[0,0],q[0,2],q[1,0],q[1,2]) for q in bounds]);done=set()
 for k in sorted(range(len(PARTS)),key=lambda k:(rank(k),k)):
  p=PARTS[k]
  if p['hidden']:continue
  q=bounds[k];near=[]
  for j in tree.query(box(q[0,0],q[0,2],q[1,0],q[1,2])):
   j=int(j)
   if j not in done or j in removed:continue
   if PARTS[j]['material']=='glass':continue
   if np.all(np.minimum(q[1],bounds[j][1])-np.maximum(q[0],bounds[j][0])>1e-6):near.append(j)
  if near:
   stair_guard=p['material']=='wall' and '/Escalera_03_Oeste' in p['group'] and '_antepecho_' in p['name']
   body=solid(k);result=mf.Manifold.batch_boolean([body]+[solid(j) if not stair_guard and (p['material']=='floor' or PARTS[j]['material']=='floor') else cutter(j) for j in near],mf.OpType.Subtract)
   if result.status()!=mf.Error.NoError:raise ValueError(f"Encuentro no valido: {p['id']} / {result.status()}")
   result=result.simplify(.00002 if p['material']=='floor' else .0001)
   if result.is_empty() or result.volume()<1e-9:removed.append(k);done.add(k);continue
   if abs(body.volume()-result.volume())>1e-9:
    out=result.to_mesh();vertices=np.array(out.vert_properties[:,:3],dtype=float);lo,hi=y_range(p['role'],p['level'],p['bottom'],p['top']);vertices[:,1]=(vertices[:,1]-lo)/(hi-lo)
    mesh=trimesh.Trimesh(vertices=vertices,faces=np.asarray(out.tri_verts),process=True);mesh.fix_normals();vv=mesh.vertices[mesh.faces].reshape(-1,3);nn=np.repeat(mesh.face_normals,3,axis=0)
    p['vertices']=vv.flatten().tolist();p['normals']=nn.flatten().tolist();p['uv']=np.round(np.c_[vv[:,0]/3,vv[:,2]/3],7).flatten().tolist()
    p['note']+=' Encuentros volumetricos regularizados; se conserva la referencia del perfil.';volumes.pop(k,None);changed+=1
  done.add(k)
 PARTS[:]=[p for k,p in enumerate(PARTS) if k not in removed]
 EVIDENCE.append({'element':'Encuentros volumetricos','sheet':'A-01 a A-05','changedParts':changed,'removedCoveredParts':len(removed),'confirmed':'Se evita superponer caras de las piezas construidas','estimated':'Criterio de propiedad de superficies: cerramientos, losas, circulaciones y carpinterias; no altera las cotas de referencia','status':'Validar mallas serializadas y recorrido despues de regularizar'})


def materialize_vertices(part):
 v=np.array(part['vertices'],float).reshape(-1,3).copy();lo,hi=y_range(part['role'],part['level'],part['bottom'],part['top']);v[:,1]=lo+(hi-lo)*v[:,1];return v

def write_mesh_asset(path,part):
 path.parent.mkdir(parents=True,exist_ok=True);v=np.asarray(materialize_vertices(part),dtype=np.float32).astype(float);n=np.array(part['normals']).reshape(-1,3);uv=np.array(part['uv']).reshape(-1,2)
 # Recompute normals after applying a vertical profile.
 ns=np.cross(v[1::3]-v[::3],v[2::3]-v[::3]);length=np.linalg.norm(ns,axis=1);valid=length>1e-18
 if not np.all(valid):
  v=v.reshape(-1,3,3)[valid].reshape(-1,3);uv=uv.reshape(-1,3,2)[valid].reshape(-1,2);ns=ns[valid];length=length[valid]
 n=np.repeat(ns/length[:,None],3,axis=0);count=len(v)
 arr=np.c_[v,n,uv].astype('<f4');indices=np.arange(count,dtype='<u4');subcounts=[count]
 if part.get('triangleMaterials') is not None:
  mask=np.array(part['triangleMaterials'])[valid];assert len(mask)==count//3
  groups=[indices.reshape(-1,3)[mask==k].flatten() for k in range(len(part['materialGuids']))];subcounts=[len(g) for g in groups];indices=np.concatenate(groups)
 mn=v.min(axis=0);mx=v.max(axis=0);center=(mn+mx)/2;extent=(mx-mn)/2
 template=(ROOT/'Assets/UPCH/Campus/Generated/Meshes/BuildingH.asset').read_text()
 template=template.replace('m_Name: BuildingH','m_Name: '+part['id'])
 template=re.sub(r'indexCount: \d+',f'indexCount: {count}',template)
 template=re.sub(r'vertexCount: \d+',f'vertexCount: {count}',template)
 template=re.sub(r'm_VertexCount: \d+',f'm_VertexCount: {count}',template)
 template=template.replace('m_IndexFormat: 0','m_IndexFormat: 1')
 template=re.sub(r'm_IndexBuffer: \w+','m_IndexBuffer: '+indices.tobytes().hex(),template)
 template=re.sub(r'm_DataSize: \d+',f'm_DataSize: {arr.nbytes}',template)
 template=re.sub(r'_typelessdata: \w+','_typelessdata: '+arr.tobytes().hex(),template)
 def vec(q):return '{x: '+format(q[0],'.9g')+', y: '+format(q[1],'.9g')+', z: '+format(q[2],'.9g')+'}'
 template=re.sub(r'm_Center: \{[^}]+\}','m_Center: '+vec(center),template)
 template=re.sub(r'm_Extent: \{[^}]+\}','m_Extent: '+vec(extent),template)
 if len(subcounts)>1:
  a=template.index('  m_SubMeshes:');z=template.index('  m_Shapes:',a);block=template[a:z].split('  m_SubMeshes:\n',1)[1];blocks=[];offset=0
  for amount in subcounts:
   entry=re.sub(r'firstByte: \d+',f'firstByte: {offset}',block);entry=re.sub(r'indexCount: \d+',f'indexCount: {amount}',entry);blocks.append(entry);offset+=amount*4
  template=template[:a]+'  m_SubMeshes:\n'+''.join(blocks)+template[z:]
 path.write_text(template);meta(path);return uid(path.relative_to(ROOT))


def read_mesh(path):
 s=path.read_text();rawdata=bytes.fromhex(re.search(r'_typelessdata: (\w+)',s)[1]);v=np.array([struct.unpack('<8f',rawdata[k:k+32]) for k in range(0,len(rawdata),32)])
 inds=bytes.fromhex(re.search(r'm_IndexBuffer: (\w+)',s)[1]);fmt='I' if 'm_IndexFormat: 1' in s else 'H';t=np.array(struct.unpack('<'+fmt*(len(inds)//struct.calcsize(fmt)),inds)).reshape(-1,3)
 return v[:,:3],t


def create_prefab(parts):
 template=(ROOT/'Assets/UPCH/Campus/Generated/Buildings/H.prefab').read_text();blocks=re.split(r'(?=^--- !u!)',template,flags=re.M)[1:]
 tpl={int(re.search(r'!u!(\d+)',b)[1]):b for b in blocks}
 tree={'':{'go':1001,'tr':1002,'children':[],'part':None,'name':'Pabellon_H_Veterinaria'}};seq=1004
 for p in parts:
  path=''
  for segment in p['group'].split('/'):
   parent=path;path=path+'/'+segment if path else segment
   if path not in tree:
    tree[path]={'go':seq,'tr':seq+1,'children':[],'part':None,'name':segment};seq+=2;tree[parent]['children'].append(path)
  key=path+'/'+p['id'];tree[key]={'go':seq,'tr':seq+1,'mf':seq+2,'mr':seq+3,'mc':seq+4 if p['collider'] else None,'part':p,'children':[],'name':p['id']+'_'+p['name']};seq+=5;tree[path]['children'].append(key)
 out=['%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n']
 for path,node in tree.items():
  p=node['part'];components=[node['tr']]+([1003] if path=='' else [])+([node['mf'],node['mr']]+([node['mc']] if p['collider'] else []) if p else [])
  go=f'''--- !u!1 &{node['go']}
GameObject:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  serializedVersion: 6
  m_Component:
'''+''.join(f'  - component: {{fileID: {c}}}\n' for c in components)+f'''  m_Layer: 0
  m_Name: {json.dumps(node['name'],ensure_ascii=False)}
  m_TagString: {'EditorOnly' if p and p['hidden'] else 'Untagged'}
  m_Icon: {{fileID: 0}}
  m_NavMeshLayer: 0
  m_StaticEditorFlags: 0
  m_IsActive: {1 if not p or p['active'] else 0}
'''
  parent=path.rsplit('/',1)[0] if '/' in path else ''
  father=0 if path=='' else tree[parent]['tr']
  children='\n'+''.join(f"  - {{fileID: {tree[c]['tr']}}}\n" for c in node['children']) if node['children'] else ' []\n'
  tr=f'''--- !u!4 &{node['tr']}
Transform:
  m_ObjectHideFlags: 0
  m_CorrespondingSourceObject: {{fileID: 0}}
  m_PrefabInstance: {{fileID: 0}}
  m_PrefabAsset: {{fileID: 0}}
  m_GameObject: {{fileID: {node['go']}}}
  serializedVersion: 2
  m_LocalRotation: {{x: 0, y: 0, z: 0, w: 1}}
  m_LocalPosition: {{x: 0, y: 0, z: 0}}
  m_LocalScale: {{x: 1, y: 1, z: 1}}
  m_ConstrainProportionsScale: 0
  m_Children:'''+children+f'''  m_Father: {{fileID: {father}}}
  m_LocalEulerAnglesHint: {{x: 0, y: 0, z: 0}}
'''
  out.extend([go,tr])
  if p:
   meshguid=meta(BASE/'Generado/Mallas'/f"{p['id']}.asset")
   for typ,num in [(33,node['mf']),(23,node['mr']),(64,node['mc'])]:
    if num is None:continue
    b=tpl[typ];old=re.search(r'&(\d+)',b)[1];b=b.replace('&'+old,'&'+str(num),1).replace('8276203377166504232',str(node['go'])).replace('e2ad8b7bc742f0745ae9ac0cfb901cd0',meshguid).replace('4429b74ef5a83f947acf9bd470d19a9b',p['materialGuid'])
    if typ==23 and p.get('materialGuids'):
     materialblock='  m_Materials:\n'+''.join('  - {fileID: 2100000, guid: '+g+', type: 2}\n' for g in p['materialGuids'])
     b=re.sub(r'  m_Materials:\n(?:  - [^\n]+\n)+',materialblock,b)
    if typ==23 and p['hidden']:b=b.replace('m_Enabled: 1','m_Enabled: 0',1)
    if typ==23 and p['material']=='glass':b=b.replace('m_CastShadows: 1','m_CastShadows: 0')
    out.append(b)
 # Reuse the campus's XR teleportation configuration on the new building.
 import subprocess
 scene_source=(ROOT/'Assets/UPCH/Scenes/Campus.unity').read_text()
 tele=re.search(r'--- !u!114 &357576546\n.*?(?=^--- !u!)',scene_source,re.M|re.S)[0]
 tele=tele.replace('&357576546','&1003',1).replace('m_GameObject: {fileID: 357576544}','m_GameObject: {fileID: 1001}')
 collider_ids=[n['mc'] for n in tree.values() if n.get('part') and n['part']['material']=='floor' and n.get('mc')]
 tele=tele.replace('  m_Colliders:\n  - {fileID: 357576547}','  m_Colliders:\n'+''.join('  - {fileID: '+str(c)+'}\n' for c in collider_ids).rstrip('\n'))
 out.append(tele)
 path=BASE/'Prefabs/Pabellon_H_Veterinaria.prefab';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(''.join(out));meta(path)
 return tree


def write_data(trace,excavation):
 model={'schema':1,'sourcePdfSha256':trace['sourceSha256'],'baseCommit':'98e8d8030f6ea5e9bee3360b28c86395f0abf28e','rootName':'Pabellon_H_Veterinaria','anchor':ANCHOR,'yaw':0,'npt':NPT,'nptPrecise':NPT,'expectedFloorCoverage':[g.wkt for g in FLOORS],'parameters':PARAMS,'items':PARTS,'excavationArea':excavation.area,'limitations':['Alturas libres, antepechos, dinteles y espesores no definidos en plantas: parametros estimados.','Rampa posterior: pendiente 8% explicita, extremos y continuidad vertical inferidos.','Geometria de escaleras requiere validacion de recorrido y cotejo en Unity.','No se ejecutaron Unity ni pruebas Play en el entorno de generacion.']}
 cad_path=Path(__file__).parent/'Fuentes/CAD_H.json'
 if cad_path.exists():
  cad=json.loads(cad_path.read_text());model['revision']=cad.get('reviewedArchitecture',{}).get('revision','R3_Escalera02_por_nivel');model['sourceDWG_SHA256']=cad['sourceSHA256'];model['horizontalSource']='Capas CAD registradas, cerramientos/parapetos/patios de azotea CAD y vacio oblicuo del hall02 A-03 cotejado con PDF. Resto de losas y circulaciones segun trazado PDF documentado.'
 if cad_path.exists():
  outline=cad.get('reviewedArchitecture',{}).get('exteriorAnnexRoof',{}).get('verificationOutline')
  if outline:
   q=np.array(outline[:4]);probes=[]
   for across in [.2,.5,.8]:
    for along in np.linspace(.15,.85,9):
     a=q[0]*(1-along)+q[1]*along;z=q[3]*(1-along)+q[2]*along;probes.extend((a*(1-across)+z*across).tolist())
   model['entryAnnexProbeXZ']=probes
 DATA.mkdir(parents=True,exist_ok=True);path=DATA/'Modelo_H.json';path.write_text(json.dumps(model,ensure_ascii=False,separators=(',',':')));meta(path)
 (DATA/'Parametros_H.json').write_text(json.dumps(PARAMS,indent=2));meta(DATA/'Parametros_H.json')
 (BASE/'Documentacion/Puertas_y_Niveles.json').write_text(json.dumps({'NPT':NPT,'doors':DOORS,'steps':STEPS,'observations':EVIDENCE},ensure_ascii=False,indent=2));meta(BASE/'Documentacion/Puertas_y_Niveles.json')


def terrain_mesh(excavation):
 path=ROOT/'Assets/UPCH/Campus/Generated/Meshes/Site.asset';v,t=read_mesh(path)
 surfaces=[]
 for face in t:
  tri=v[face]
  if np.cross(tri[1]-tri[0],tri[2]-tri[0])[1]>0 and np.ptp(tri[:,1])<1e-5:surfaces.append(Polygon(tri[:,[0,2]]))
 footprint=unary_union(surfaces)
 # Scene terrain and root are unrotated with unit scale in the inspected scene.
 cut=affinity.translate(excavation,xoff=ANCHOR[0]-41.190327,yoff=ANCHOR[2]-74.66189)
 result=footprint.difference(cut)
 mesh=merge_meshes([section(p,.16) for p in polygons(result)]);mesh.vertices[:,1]-=.16
 v=mesh.vertices[mesh.faces].reshape(-1,3);n=np.repeat(mesh.face_normals,3,axis=0);uv=v[:,[0,2]]/5
 p={'id':'Terreno_Recortado_H','vertices':v.flatten().tolist(),'normals':n.flatten().tolist(),'uv':uv.flatten().tolist(),'role':'fixed','level':0,'bottom':0,'top':1}
 output=BASE/'Generado/Terreno_Recortado_H.asset';write_mesh_asset(output,p)
 return {'sourceArea':footprint.area,'excavatedIntersectionArea':footprint.intersection(cut).area,'remainingArea':result.area,'sourceGuid':meta(path),'resultGuid':meta(output),'mesh':mesh,'cut':cut,'terrainFootprint':footprint}


def integrate_scene(terrain):
 path=ROOT/'Assets/UPCH/Scenes/Campus.unity'
 # Preserve all unrelated scene blocks, including changes made after this build.
 import subprocess
 source=path.read_text()
 chunks=re.split(r'(?=^--- !u!)',source,flags=re.M);head=chunks[0];blocks=chunks[1:]
 indexed={int(re.search(r'&(-?\d+)',b)[1]):k for k,b in enumerate(blocks)}
 for ident in [357576547,357576549]:
  k=indexed[ident]
  if terrain['sourceGuid'] not in blocks[k] and terrain['resultGuid'] not in blocks[k]:raise ValueError('Terreno modificado por otro trabajo; integrar desde Unity preservando esa base.')
  blocks[k]=blocks[k].replace(terrain['sourceGuid'],terrain['resultGuid'])
 # Preserve H as an inactive reference in the scene, without changing H.prefab.
 k=indexed[6118289441634658740];b=blocks[k];needle='    m_RemovedComponents: []'
 b=b if 'propertyPath: m_IsActive' in b else b.replace(needle,'''    - target: {fileID: 8276203377166504232, guid: 60f4547a70a5cf941b993934d2a70ea9, type: 3}
      propertyPath: m_IsActive
      value: 0
      objectReference: {fileID: 0}
'''+needle);blocks[k]=b
 pid=880018110001;tid=880018110002
 if pid in indexed:
  expected=meta(BASE/'Prefabs/Pabellon_H_Veterinaria.prefab')
  if expected not in blocks[indexed[pid]]:raise ValueError('ID de instancia ocupado por otro edificio.')
 k=indexed[1237960108]
 if f'fileID: {tid}' not in blocks[k]:blocks[k]=blocks[k].replace('  m_Father:',f'  - {{fileID: {tid}}}\n  m_Father:',1)
 guid=meta(BASE/'Prefabs/Pabellon_H_Veterinaria.prefab')
 mods=[]
 for prop,val in [('m_LocalPosition.x',ANCHOR[0]),('m_LocalPosition.y',ANCHOR[1]),('m_LocalPosition.z',ANCHOR[2]),('m_LocalRotation.w',1),('m_LocalRotation.x',0),('m_LocalRotation.y',0),('m_LocalRotation.z',0)]:
  mods.append(f'''    - target: {{fileID: 1002, guid: {guid}, type: 3}}
      propertyPath: {prop}
      value: {val}
      objectReference: {{fileID: 0}}
''')
 instance=f'''--- !u!1001 &{pid}
PrefabInstance:
  m_ObjectHideFlags: 0
  serializedVersion: 2
  m_Modification:
    serializedVersion: 3
    m_TransformParent: {{fileID: 1237960108}}
    m_Modifications:
'''+''.join(mods)+f'''    m_RemovedComponents: []
    m_RemovedGameObjects: []
    m_AddedGameObjects: []
    m_AddedComponents: []
  m_SourcePrefab: {{fileID: 100100000, guid: {guid}, type: 3}}
--- !u!4 &{tid} stripped
Transform:
  m_CorrespondingSourceObject: {{fileID: 1002, guid: {guid}, type: 3}}
  m_PrefabInstance: {{fileID: {pid}}}
  m_PrefabAsset: {{fileID: 0}}
'''
 blocks=[b for b in blocks if int(re.search(r'&(-?\d+)',b)[1]) not in [pid,tid]]
 path.write_text(head+''.join(blocks)+instance)
 return path


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--trace',type=Path,default=Path(__file__).parent/'Fuentes/Trazado_Vectorial.json');ap.add_argument('--doors',type=Path,default=Path(__file__).parent/'Fuentes');ap.add_argument('--no-scene',action='store_true');ap.add_argument('--building-only',action='store_true',help='Regenera solo H; conserva Campus y el terreno ya validado');args=ap.parse_args()
 trace=json.loads(args.trace.read_text())
 for i in range(5):DOORS.append(json.loads((args.doors/f'doors_{i+1}.json').read_text()))
 cad_path=Path(__file__).parent/'Fuentes/CAD_H.json'
 cad=json.loads(cad_path.read_text()) if cad_path.exists() else None
 if cad:
  from cad_h import merge_doors,build_sections,pair_beam_faces
  ARCH_REVIEW.update(cad.get('reviewedArchitecture',{}))
  NATIVE_BEAMS[:]=[pair_beam_faces(l.get('beamLines',[])) for l in cad['levels'][:4]]
  merge_doors(sys.modules[__name__],cad)
  EAST_CASES[:]=cad.get('eastStairs',[])
  review=cad.get('reviewedArchitecture',{})
  from cad_h import prepare_roof
  prepare_roof(sys.modules[__name__],cad)
 make_slabs()
 if cad:build_sections(sys.modules[__name__],cad,trace)
 else:load_sections(trace)
 make_doors();fit_slabs_to_enclosures();rear_containment();exterior_annex_roof();west_stair();east_stair();central_stairs();technical_access();exterior_access();architecture_complements()
 if cad:
  from cad_h import build_high_windows
  build_high_windows(sys.modules[__name__],cad)
  if ARCH_REVIEW.get('photoRevision'):
   from fotografias_h import street_screens
   street_screens(sys.modules[__name__],cad)
 excavation=unary_union([p for g in [envelope(0),envelope(1),metric(WEST_HALL.union(WEST_SLAB),2)]+GROUND_PATCHES for p in polygons(g)])
 # The actual excavation model excludes the adjacent campus and follows H only.
 add_mesh(merge_meshes([section(p) for p in polygons(excavation)]),'00_Estructura_General','Excavacion_H_Verificada','floor',False,'fixed',0,-3.57,-3.55,source='A-01/A-02: envolvente completa',note='Malla auxiliar solo Editor; no renderiza ni colisiona.',active=False,hidden=True)
 # Frames share height profiles and materials. Consolidate by level and role
 # so a separate asset is not created for every small frame component.
 frame_groups=collections.defaultdict(list);retained=[]
 for part in PARTS:
  if part['name'].startswith('CAD_Carpinteria_'):frame_groups[(part['level'],part['role'])].append(part)
  else:retained.append(part)
 for (level,role),pieces in frame_groups.items():
  merged=dict(pieces[0]);merged['name']=f'CAD_Carpinteria_{role}_nivel_{level}'
  for key in ['vertices','normals','uv']:merged[key]=[value for piece in pieces for value in piece[key]]
  merged['source']=f'DWG/A-0{level+1}: marcos de {len(pieces)} vanos consolidados'
  merged['note']='Geometria por vano conservada; una malla por nivel y perfil vertical para evitar archivos de componentes pequenos. Secciones estimadas.'
  retained.append(merged)
 PARTS[:]=retained
 union_railing_components()
 frame_parts=[p for p in PARTS if p['name'] in ['Marcos_puertas_consolidados','HV_Marcos_consolidados']]
 other_parts=[p for p in PARTS if p not in frame_parts]
 PARTS[:]=frame_parts
 repair_float32_topology()
 # Fixed door/transom frames can intersect. Union them before assigning
 # the surface to avoid two opaque skins at their shared sill/header.
 import manifold3d as mf
 joined_frames=[]
 for level in range(5):
  pieces=[p for p in PARTS if p['level']==level]
  if not pieces:continue
  bodies=[]
  for part in pieces:
   vv=materialize_vertices(part);mm=trimesh.Trimesh(vertices=vv,faces=np.arange(len(vv)).reshape(-1,3),process=True)
   bodies.append(mf.Manifold(mf.Mesh(np.asarray(mm.vertices,dtype=np.float32),np.asarray(mm.faces,dtype=np.uint32))))
  out=mf.Manifold.batch_boolean(bodies,mf.OpType.Add).simplify(.0001).to_mesh();mesh=trimesh.Trimesh(vertices=np.asarray(out.vert_properties[:,:3]),faces=np.asarray(out.tri_verts),process=False)
  part=dict(pieces[0]);vv=mesh.vertices[mesh.faces].reshape(-1,3)
  part.update(name='Marcos_carpinteria_fijos',vertices=vv.flatten().tolist(),normals=np.repeat(mesh.face_normals,3,axis=0).flatten().tolist(),uv=np.c_[vv[:,0]/3,vv[:,2]/3].flatten().tolist(),source='Marcos de puertas y ventanas altas del nivel; secciones estimadas')
  joined_frames.append(part)
 PARTS[:]=joined_frames
 repair_float32_topology()
 PARTS[:]=other_parts+PARTS
 resolve_solid_junctions()
 if __import__('os').environ.get('H_DEBUG_CHECKPOINT'):
  import pickle
  Path(__import__('os').environ['H_DEBUG_CHECKPOINT']).write_bytes(pickle.dumps(PARTS))
 repair_float32_topology()
 seen=set();unique=[]
 for p in PARTS:
  vv=np.round(materialize_vertices(p),6).reshape(-1,3,3)
  canonical=sorted(tuple(sorted(tuple(q) for q in tri)) for tri in vv)
  key=(p['materialGuid'],p['collider'],p['active'],hashlib.sha256(repr(canonical).encode()).hexdigest())
  if key not in seen:seen.add(key);unique.append(p)
 PARTS[:]=unique
 from acabados_h import material_assets,apply as apply_finishes
 finishes=material_assets(ROOT,BASE,uid);apply_finishes(PARTS,[envelope(i) for i in range(5)],materialize_vertices,finishes)
 # Planar UV per face orientation, in metres. Vertical faces use elevation.
 for part in PARTS:
  vv=materialize_vertices(part).reshape(-1,3,3);nn=np.cross(vv[:,1]-vv[:,0],vv[:,2]-vv[:,0]);axes=np.argmax(np.abs(nn),axis=1);uv=[]
  for face,axis in zip(vv,axes):
   plane=face[:,[0,2]] if axis==1 else face[:,[2,1]] if axis==0 else face[:,[0,1]]
   uv.extend((plane/3).flatten().tolist())
  part['uv']=uv
 active_ids={p['id'] for p in PARTS}
 for old in (BASE/'Generado/Mallas').glob('H_*.asset'):
  if old.stem not in active_ids:
   old.unlink();old.with_name(old.name+'.meta').unlink(missing_ok=True)
 for p in PARTS:write_mesh_asset(BASE/'Generado/Mallas'/f"{p['id']}.asset",p)
 create_prefab(PARTS);write_data(trace,excavation)
 if args.building_only:
  previous=BASE/'Documentacion/Construccion.json'
  terrain={'excavatedIntersectionArea':json.loads(previous.read_text())['terrainAreaRemoved'] if previous.exists() else None,'preservedExistingAsset':True}
 else:terrain=terrain_mesh(excavation)
 if not args.no_scene and not args.building_only:integrate_scene(terrain)
 for d in sorted([BASE]+[q for q in BASE.rglob('*') if q.is_dir()],key=lambda p:len(p.parts)):meta(d)
 summary={'parts':len(PARTS),'byGroup':dict(collections.Counter(p['group'] for p in PARTS)),'NPT':NPT,'anchor':ANCHOR,'excavationArea':excavation.area,'terrainAreaRemoved':terrain['excavatedIntersectionArea'],'roofVoidArea':OPENINGS[4].area,'stairRisers':len(STEPS)+2*len(EAST_CASES),'eastStairRisers':[c['riserCount'] for c in EAST_CASES],'doors':list(map(len,DOORS))}
 (BASE/'Documentacion/Construccion.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False));meta(BASE/'Documentacion/Construccion.json')
 # Geometry checkpoint for reproducible QA; not part of the Unity package.
 import pickle
 checkpoint=ROOT.parent/'tmp/h_geometry.pkl'
 checkpoint.parent.mkdir(parents=True,exist_ok=True)
 with checkpoint.open('wb') as f:pickle.dump({'parts':PARTS,'floors':FLOORS,'walls':WALLS,'openings':OPENINGS,'excavation':excavation,'terrain':terrain,'doors':DOORS,'steps':STEPS},f)
 print(json.dumps({k:v for k,v in summary.items() if k!='byGroup'},indent=2))

if __name__=='__main__':main()
