"""Native CAD layers; estimated heights remain explicit."""
import re
import numpy as np
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union

def geometry(records):return unary_union([Polygon(q['outline'],q['holes']) for q in records])
def merge_doors(b,data):
 for i,level in enumerate(data['levels']):
  native=level['doors'];result=[];used=set()
  for old in b.DOORS[i]:
   distance,j,q=min([(np.linalg.norm(np.array(q['hinge'])-old['hinge']),j,q) for j,q in enumerate(native)],default=(999,-1,None))
   if distance<.08:
    q=dict(q);used.add(j);a=np.array(old['closed'])-old['hinge'];v=np.array(q['closed'])-q['hinge']
    if abs(np.dot(a,v))/(np.linalg.norm(a)*np.linalg.norm(v))<.70:q['closed'],q['opened']=q['opened'],q['closed']
    result.append(q)
   else:
    old=dict(old);old['evidence']='PDF registrado contra DWG; arco no recuperado como entidad circular. Altura estimada.';result.append(old)
  for j,q in enumerate(native):
   if j not in used and not any(np.linalg.norm(np.array(q['hinge'])-x['hinge'])<.08 for x in result):result.append(q)
  b.DOORS[i]=result

def low_height(g,level,default):
 choices=[]
 for t in level['texts']:
  m=re.search(r'[Hh]\s*=\s*([0-9]+[.,][0-9]+)',t['text'])
  if m:
   dist=g.distance(Point(t['local']))
   if dist<1.5:choices.append((dist,float(m[1].replace(',','.'))))
 return min(choices)[1] if choices else default

def build_sections(b,data,trace):
 for i,level in enumerate(data['levels']):
  if i==4:b.WALLS.append(Polygon());continue
  W=geometry(level['wall']);D=geometry(level['drywall']).difference(W);L=geometry(level['low']).difference(W).difference(D);V=geometry(level['window']).difference(W).difference(D).difference(L)
  envelope=b.envelope(i).buffer(.012)
  W=W.intersection(envelope).difference(b.metric(b.WEST_SLAB,2).buffer(.005))
  D=D.intersection(envelope);L=L.intersection(envelope);V=V.intersection(envelope)
  # Explicit PDF annotations disambiguate heights absent from CAD layer names.
  # Keep native horizontal profiles; use the registered annotation regions only.
  if i in (2,3):
   supplemental=trace['levels'][i]['supplemental']
   low_indices=[30,40,44,47,55,37] if i==2 else []
   glass_indices=[36] if i==2 else [46,47,62,68]
   for tag,indices in [('Divisorios_1_60',low_indices),('Cerramientos_Vidrio',glass_indices)]:
    mask=unary_union([b.metric(Polygon(supplemental[j]['outline'],supplemental[j]['holes']),i) for j in indices]).buffer(.015)
    actual=unary_union([W,D,L,V]).intersection(mask)
    W=W.difference(mask);D=D.difference(mask);L=L.difference(mask);V=V.difference(mask)
    if tag=='Divisorios_1_60':b.fixed_prism(actual,b.NPT[i],b.NPT[i]+1.60,b.LEVEL_NAMES[i]+'/'+tag,'CAD_Divisorios_rotulados_1_60','wall',True,i,f'DWG + PDF/A-0{i+1}/DIVISORIO H=1.60')
    else:b.add_poly(actual,b.LEVEL_NAMES[i]+'/'+tag,'CAD_Vidrio_templado_rotulado','glass',True,'wall',i,source=f'DWG + PDF/A-0{i+1}/VIDRIO TEMPLADO',note='Altura hasta intrados estimada.')
  opening=unary_union([LineString([q['hinge'],q['closed']]).buffer(.50,cap_style='flat') for q in b.DOORS[i]])
  for kind,g in [('Muros',W),('Tabiques_Drywall',D)]:
   for j,p in enumerate(b.polygons(g)):
    short=max(p.bounds[2]-p.bounds[0],p.bounds[3]-p.bounds[1])<.72;group=b.LEVEL_NAMES[i]+('/Columnas' if short else '/'+kind)
    b.add_poly(p.difference(opening),group,f'CAD_{kind}_{j+1}','wall',True,'wall',i,source=f'DWG/A-0{i+1}/'+('A- MUROS' if kind=='Muros' else 'A-DRYWALL'),note='Contorno CAD nativo en metros; altura configurable estimada.');b.LINTELS[i].append(p.intersection(opening))
  for j,p in enumerate(b.polygons(L)):
   h=low_height(p,level,b.PARAMS['windowSill'] if p.distance(b.envelope(i).boundary)<.5 else 1.10)
   b.fixed_prism(p.difference(opening),b.NPT[i],b.NPT[i]+h,b.LEVEL_NAMES[i]+'/Muros_Bajos',f'CAD_Muro_bajo_{j+1}','wall',True,i,f'DWG/A-0{i+1}/A- MURO BAJO','Altura por rotulo proximo cuando existe; resto estimado. Revisar asignacion de cada tramo.')
  V=V.buffer(.018,join_style='mitre').buffer(-.018,join_style='mitre').difference(W).difference(D).difference(L).difference(opening)
  for j,p in enumerate(b.polygons(V)):
   if p.area<.03:continue
   if p.distance(b.envelope(i).boundary)>.60:
    b.add_poly(p,b.LEVEL_NAMES[i]+'/Cerramientos_Vidrio',f'CAD_Vidrio_interior_{j+1}','glass',True,'wall',i,source=f'DWG/A-0{i+1}/A- VENTANA',note='Altura interior no definida en planta: hasta intrados estimado.')
   else:
    for role,mat in [('sill','wall'),('glass','glass'),('windowLintel','wall')]:b.add_poly(p,b.LEVEL_NAMES[i]+'/Ventanas',f'CAD_Ventana_{j+1}_{role}',mat,True,role,i,source=f'DWG/A-0{i+1}/A- VENTANA',note='Posicion y perfil CAD; alturas de antepecho y dintel estimadas.')
  if i==0:
   tech=unary_union([b.poly(q,0) for q in b.HOLE_DATA[0]]).buffer(.30);lower=W.intersection(tech).difference(b.rect(1380,544,1420,579,0));b.fixed_prism(lower,-4.5,-3.55,b.LEVEL_NAMES[i]+'/Muros','CAD_Muros_tecnicos_hasta_menos_4_50','wall',True,i,'DWG/A-01/NPT=-4.50')
  b.WALLS.append(unary_union([W,D,L]))
