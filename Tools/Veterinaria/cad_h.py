"""Native CAD layers; estimated heights remain explicit."""
import re
from shapely import set_precision,make_valid
import numpy as np
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union

def geometry(records):return set_precision(unary_union([Polygon(q['outline'],q['holes']) for q in records]),.00001)
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
   if j not in used and not any(np.linalg.norm(np.array(q['hinge'])-x['hinge'])<.08 for x in result):
    q=dict(q);q['nativeOnly']=True;result.append(q)
  result=[q for q in result if not any(np.linalg.norm(np.array(q['hinge'])-r['center'])<r['radius'] for r in level.get('excludedDoorSymbols',[]))]
  # Dimension extension endpoints locate the actual jambs. The centre of a
  # stylised swing arc is not necessarily the hinge (up to 0.20 m discrepancy).
  revised=[];offset=np.array(level['offsetDWG'])
  for q in result:
   a=np.array(q['hinge']);width=np.linalg.norm(np.array(q['closed'])-a);candidates=[]
   for dim in level['dimensions']:
    if not all(k in dim['points'] for k in ['defpoint2','defpoint3']):continue
    ends=[np.array(dim['points'][k])[:2]-offset for k in ['defpoint2','defpoint3']];length=np.linalg.norm(ends[1]-ends[0]);distance=min(np.linalg.norm(v-a) for v in ends);ratio=length/width
    standards=[.55,.6,.7,.8,.9,.95,1.,1.2,1.4,1.5,1.6,1.8]
    preferred=next((r['handle'] for r in level.get('preferredDoorDimensions',[]) if np.linalg.norm(a-r['hinge'])<r['radius']),None)
    if (preferred is None or dim.get('handle')==preferred) and .5<=length<=1.82 and distance<.30 and (.65<ratio<1.4 or 1.8<ratio<2.7) and min(abs(length-v) for v in standards)<.025 and abs(float(dim['value'])-length)<.004:
     candidates.append((distance,length,ratio,ends,dim))
   if not candidates:revised.append(q);continue
   distance,length,ratio,ends,dim=min(candidates,key=lambda x:x[0]);ends.sort(key=lambda v:np.linalg.norm(v-a));double=ratio>1.8
   pairs=[(ends[0],(ends[0]+ends[1])/2),(ends[1],(ends[0]+ends[1])/2)] if double else [(ends[0],ends[1])]
   for hinge,closed in pairs:
    direction=closed-hinge;n=np.array([-direction[1],direction[0]])
    swing=max([np.array(q['opened'])-a,np.array(q['closed'])-a],key=lambda v:abs(np.dot(n,v)))
    if np.dot(n,swing)<0:n=-n
    record=dict(q);record.update(hinge=hinge.tolist(),closed=closed.tolist(),opened=(hinge+n).tolist(),width=float(np.linalg.norm(direction)),confirmedOpeningDimension=float(length),dimensionHandle=dim.get('handle'),evidence=f"DWG A-0{i+1}: extremos de cota {length:.3f} m; {'dos hojas' if double else 'una hoja'}; altura estimada.")
    revised.append(record)
  result=[]
  for q in revised:
   if not any(np.linalg.norm(np.array(q['hinge'])-x['hinge'])<.08 and np.linalg.norm(np.array(q['closed'])-x['closed'])<.12 for x in result):result.append(q)
  for override in level.get('doorOverrides',[]):
   result=[q for q in result if np.linalg.norm(np.array(q['hinge'])-override['center'])>override['replaceRadius']]
   result.extend(override['doors'])
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
  if i==4:
   build_roof(b,data);continue
  W=geometry(level['wall']);D=geometry(level['drywall']).difference(W);L=geometry(level['low']).difference(W).difference(D);V=geometry(level['window']).difference(W).difference(D).difference(L)
  # The old PDF outline used some inner faces. Keep complete native CAD
  # profiles within the building vicinity instead of shaving off their ends.
  envelope=b.envelope(i).buffer(.60)
  W=W.intersection(envelope).difference(b.metric(b.WEST_SLAB,2).buffer(.005))
  if i==0:
   section=W.intersection(Polygon(data['eastStairSectionMask']));W=W.difference(section)
   case=b.EAST_CASES[0];mid=case.get('midHeightOverride',b.NPT[0]+(b.NPT[1]-b.NPT[0])*case['upRisers']/case['riserCount'])
   b.fixed_prism(section,b.NPT[0],mid-b.PARAMS['stairSlabThickness'],b.LEVEL_NAMES[0]+'/Muros_Bajos','Borde_corte_escalera02_bajo_descanso','wall',True,0,'A-01: perfil en C conservado en planta','Clasificacion como borde/cerramiento bajo inferida; coronacion al intrados del descanso calculado, no altura explicita de plano.')
  D=D.intersection(envelope);L=L.intersection(envelope);V=V.intersection(envelope)
  backing=geometry(level.get('windowBacking',[])).difference(W).difference(D)
  L=L.difference(backing);V=V.union(backing)
  # Explicit PDF annotations disambiguate heights absent from CAD layer names.
  # Keep native horizontal profiles; use the registered annotation regions only.
  if i in (2,3):
   supplemental=trace['levels'][i]['supplemental']
   low_indices=[30,40,44,47,55,37] if i==2 else []
   glass_indices=[36] if i==2 else [46,47,62,68]
   for tag,indices in [('Divisorios_1_60',low_indices),('Cerramientos_Vidrio',glass_indices)]:
    mask=unary_union([b.metric(Polygon(supplemental[j]['outline'],supplemental[j]['holes']),i) for j in indices]).buffer(.015)
    if tag=='Cerramientos_Vidrio' and data.get('reviewedArchitecture',{}).get('campusFacade'):
     # These annotations describe glazed room partitions, not an entirely
     # glazed exterior. Retain the native sill/window/lintel at the campus edge.
     mask=mask.difference(box(-22.2,-10.2,21.4,-9.77))
    actual=unary_union([W,D,L,V]).intersection(mask)
    W=W.difference(mask);D=D.difference(mask);L=L.difference(mask);V=V.difference(mask)
    if tag=='Divisorios_1_60':b.fixed_prism(actual,b.NPT[i],b.NPT[i]+1.60,b.LEVEL_NAMES[i]+'/'+tag,'CAD_Divisorios_rotulados_1_60','wall',True,i,f'DWG + PDF/A-0{i+1}/DIVISORIO H=1.60')
    else:b.add_poly(actual,b.LEVEL_NAMES[i]+'/'+tag,'CAD_Vidrio_templado_rotulado','glass',True,'wall',i,source=f'DWG + PDF/A-0{i+1}/VIDRIO TEMPLADO',note='Altura hasta intrados estimada.')
  opening=unary_union([LineString([q['hinge'],q['closed']]).buffer(.32,cap_style='flat') for q in b.DOORS[i]])
  for review in data.get('reviewedArchitecture',{}).get('heightOverrides',[]):
   if review['level']!=i:continue
   mask=geometry([level[review['kind']][k] for k in review['indices']]).buffer(.00001)
   actual=unary_union([W,D,L,V]).intersection(mask)
   W=W.difference(mask);D=D.difference(mask);L=L.difference(mask);V=V.difference(mask)
   b.fixed_prism(actual.difference(opening),b.NPT[i],b.NPT[i]+review['height'],b.LEVEL_NAMES[i]+'/Divisorios_1_60','Drywall_H_1_60_A02_verificado','wall',True,i,review['evidence'],'Altura explicita del rotulo; no se rebajan los muros perimetrales ni columnas.')
  for kind,g in [('Muros',W),('Tabiques_Drywall',D)]:
   for j,p in enumerate(b.polygons(g)):
    short=max(p.bounds[2]-p.bounds[0],p.bounds[3]-p.bounds[1])<.72;group=b.LEVEL_NAMES[i]+('/Columnas' if short else '/'+kind)
    b.add_poly(p.difference(opening),group,f'CAD_{kind}_{j+1}','wall',True,'wall',i,source=f'DWG/A-0{i+1}/'+('A- MUROS' if kind=='Muros' else 'A-DRYWALL'),note='Contorno CAD nativo en metros; altura configurable estimada.');b.LINTELS[i].append(p.intersection(opening))
  for review in data.get('reviewedArchitecture',{}).get('guardProfiles',[]):
   if review['level']!=i:continue
   mask=geometry([level['low'][k] for k in review['indices']])
   selected=L.intersection(mask.buffer(.00001));L=L.difference(mask.buffer(.00001))
   for k,profile in enumerate(b.polygons(selected)):
    if data.get('reviewedArchitecture',{}).get('photoRevision'):
     b.fixed_prism(profile,b.NPT[i],b.NPT[i]+1.10,b.LEVEL_NAMES[i]+'/Antepechos_Exteriores',f'Antepecho_oriental_fotografia_{k+1}','wall',True,i,'Perfiles CAD A-MURO BAJO; fotos del nucleo oriental del 21/11/2026','Cerramiento macizo confirmado visualmente; altura 1.10 m estimada. El vano superior permanece abierto.')
     continue
    rr=np.array(profile.minimum_rotated_rectangle.exterior.coords)[:4];edges=np.roll(rr,-1,axis=0)-rr;jj=int(np.argmax(np.linalg.norm(edges,axis=1)));u=edges[jj]/np.linalg.norm(edges[jj]);center=rr.mean(axis=0);along=(np.array(profile.exterior.coords)-center)@u
    a=center+u*(along.min()+.025);z=center+u*(along.max()-.025)
    b.rail_path([a,z],b.NPT[i],b.PARAMS['railingHeight'],b.LEVEL_NAMES[i]+'/Barandas',f'Baranda_CAD_oriental_{k+1}',i,review['evidence']+'; altura 1.10 y perfiles metalicos estimados')
  for j,p in enumerate(b.polygons(L)):
   h=low_height(p,level,b.PARAMS['windowSill'] if p.distance(b.envelope(i).boundary)<.5 else 1.10)
   b.fixed_prism(p.difference(opening),b.NPT[i],b.NPT[i]+h,b.LEVEL_NAMES[i]+'/Muros_Bajos',f'CAD_Muro_bajo_{j+1}','wall',True,i,f'DWG/A-0{i+1}/A- MURO BAJO','Altura por rotulo proximo cuando existe; resto estimado. Revisar asignacion de cada tramo.')
  V=set_precision(make_valid(V.buffer(.018,join_style='mitre').buffer(-.018,join_style='mitre')),.00001).difference(set_precision(W,.00001)).difference(set_precision(D,.00001)).difference(set_precision(L,.00001)).difference(set_precision(opening,.00001))
  for j,p in enumerate(b.polygons(V)):
   if p.area<.03:continue
   if p.distance(b.envelope(i).boundary)>.60 and p.intersection(backing).area<.01:
    b.add_poly(p,b.LEVEL_NAMES[i]+'/Cerramientos_Vidrio',f'CAD_Vidrio_interior_{j+1}','glass',True,'wall',i,source=f'DWG/A-0{i+1}/A- VENTANA',note='Altura interior no definida en planta: hasta intrados estimado.')
   else:
    for role in ['sill','windowLintel']:b.add_poly(p,b.LEVEL_NAMES[i]+'/Ventanas',f'CAD_Ventana_{j+1}_{role}','wall',True,role,i,source=f'DWG/A-0{i+1}/A- VENTANA',note='Perfil CAD; alturas de antepecho y dintel estimadas.')
    window_frame(b,p,i,j,level.get('windowLines',[]))
  if i==0:
   tech=unary_union([b.poly(q,0) for q in b.HOLE_DATA[0]]).buffer(.30);lower=W.intersection(tech).difference(b.rect(1380,544,1420,579,0));b.fixed_prism(lower,-4.5,-3.55,b.LEVEL_NAMES[i]+'/Muros','CAD_Muros_tecnicos_hasta_menos_4_50','wall',True,i,'DWG/A-01/NPT=-4.50')
  if i in (2,3):b.wall_line(b.pt(135,516.24,2),b.pt(96,658.8,2),.12,b.LEVEL_NAMES[i]+'/Parapetos','Parapeto_hall_oeste_1_25',i,height=1.25,source=f'A-0{i+1} PARAPETO h=1.25m')
  b.WALLS.append(unary_union([W,D]))


def window_frame(b,p,i,j,source_lines):
 # Frames follow each recovered opening. Intermediate posts only occur where
 # native transverse window lines exist; no regular spacing is invented.
 rr=np.array(p.minimum_rotated_rectangle.exterior.coords)[:4];edges=np.roll(rr,-1,axis=0)-rr;k=np.argmax(np.linalg.norm(edges,axis=1));u=edges[k]/np.linalg.norm(edges[k]);n=np.array([-u[1],u[0]]);center=rr.mean(axis=0)
 coords=np.array(p.exterior.coords);along=(coords-center)@u;lo,hi=along.min(),along.max()
 if hi-lo<.14:return
 a=center+u*lo;z=center+u*hi;axis=LineString([a,z]);group=b.LEVEL_NAMES[i]+'/Ventanas'
 pane=LineString([a+u*.045,z-u*.045]).buffer(.006,cap_style='flat').intersection(p)
 b.add_poly(pane,group,f'CAD_Ventana_{j+1}_vidrio_12mm','glass',True,'glass',i,source=f'DWG/A-0{i+1}/A- VENTANA',note='Centro del vano CAD; espesor de vidrio 12 mm y altura estimados.')
 stations=[lo+.0225,hi-.0225]
 for line in source_lines:
  for x,y in zip(line,line[1:]):
   x,y=np.array(x),np.array(y);v=y-x;length=np.linalg.norm(v)
   if not .025<length<.65 or abs(v@u)/length>.15:continue
   m=(x+y)/2;t=(m-center)@u
   if lo+.12<t<hi-.12 and axis.distance(Point(m))<.17 and not any(abs(t-v)<.085 for v in stations):stations.append(t)
 posts=[]
 for t in stations:
  c=center+u*t;posts.append(Polygon([c-u*.0225-n*.028,c+u*.0225-n*.028,c+u*.0225+n*.028,c-u*.0225+n*.028]))
 b.add_poly(unary_union(posts),group,f'CAD_Carpinteria_{j+1}_vertical','metal',False,'windowFrameVertical',i,source=f'DWG/A-0{i+1}/montantes',note='Extremos y divisiones nativas; seccion de marco 45 x 56 mm estimada.')
 horizontal=axis.buffer(.028,cap_style='flat')
 for role in ['windowFrameBottom','windowFrameTop']:b.add_poly(horizontal,group,f'CAD_Carpinteria_{j+1}_{role}','metal',False,role,i,source=f'DWG/A-0{i+1}/vano',note='Seccion y altura de marcos estimadas; sin collider adicional.')


def build_roof(b,data):
 """A-05 architectural enclosures and parapets, not rooftop equipment."""
 review=data.get('reviewedArchitecture')
 if not review:
  b.WALLS.append(Polygon());return
 level=data['levels'][4];group=b.LEVEL_NAMES[4];b.ROOF_NATIVE=True
 opening=unary_union([LineString([q['hinge'],q['closed']]).buffer(.16,cap_style='flat') for q in b.DOORS[4]])
 sources=unary_union([geometry(level[k]) for k in ['drywall','low','window']]);shells=[]
 for j,c in enumerate(review['roofEnclosures']):
  extent=box(*c['bounds']);g=sources.intersection(extent.buffer(.0001)).intersection(extent)
  shells.append(g);b.add_poly(g.difference(opening),group+'/Comedor_y_Cerramientos',c['name']+'_perfil_CAD','wall',True,'wall',4,source=c['source'],note='Perfil nativo con vanos; altura y cubierta configurables estimadas. Sin mobiliario ni equipos.')
  b.LINTELS[4].append(g.intersection(opening))
  b.add_poly(extent,group+'/Cubiertas',c['name']+'_cubierta','floor',True,'roofCover',4,source=c['source'],note='Contorno CAD del cerramiento; existencia/altura 2.60 m y espesor 0.14 m de cubierta estimados, pendientes de alzado.')
 # Stand-alone equipment pads are not parapets. Only the perimeter and two
 # complete patio rings are architectural profiles confirmed by A-05.
 ring_ids=[5]+review['roofVoidsFromLowProfiles'];parapets=geometry([level['low'][k] for k in ring_ids]).difference(unary_union(shells).buffer(.0001))
 # The curved stair boundary carries the explicitly labelled metal rail, not
 # an extra solid wall at roof level. Keep the existing open arrival width.
 west=b.metric(b.WEST_HALL.union(b.WEST_SLAB).buffer(2),2).buffer(.35)
 parapets=parapets.difference(west)
 base_h=review['roofParapetBase'];high=review['roofRearHighParapet'];high_g=parapets.intersection(box(*high['maskBounds']))
 top_edges=[]
 for k in review['roofVoidsFromLowProfiles']:
  p=geometry([level['low'][k]]);hole=Polygon(level['low'][k]['holes'][0]);x0,z0,x1,z1=hole.bounds
  top_edges.append(p.intersection(box(x0,z1-.0001,x1,z1+.1505)))
 top=unary_union(top_edges).difference(high_g);normal=parapets.difference(high_g).difference(top)
 for name,g,h,evidence in [('Parapetos_CAD_h_0_80',normal,base_h,'A-05 PARAPETO h=0.80m; perfiles CAD'),('Parapetos_patio_borde_h_0_85',top,review['roofParapetTopEdge'],'A-05 PARAPETO h=0.85m, solo borde indicado de cada patio'),('Parapeto_posterior_h_1_30',high_g,high['height'],high['evidence'])]:
  b.fixed_prism(g,b.NPT[4],b.NPT[4]+h,group+'/Parapetos',name,'wall',True,4,evidence,'Alturas rotuladas; extension del tramo posterior interpretada y documentada.')
 b.wall_line(b.pt(135,516.24,2),b.pt(96,658.8,2),.12,group+'/Parapetos','Parapeto_llegada_oeste_0_80',4,height=.8,source='A-05 PARAPETO h=0.80m')
 b.WALLS.append(unary_union(shells))


def prepare_roof(b,data):
 review=data.get('reviewedArchitecture',{})
 if not review:return
 level=data['levels'][4];big=level['low'][5];b.ROOF_VOID_PROFILES[:]=[Polygon(level['low'][k]['holes'][0]) for k in review['roofVoidsFromLowProfiles']]+[Polygon(big['holes'][k]) for k in [2,4]]
 west=b.metric(b.WEST_HALL.union(b.WEST_SLAB).buffer(2),2).buffer(.35)
 parapets=geometry([level['low'][k] for k in [5]+review['roofVoidsFromLowProfiles']]).difference(west)
 arrival=LineString([b.pt(135,516.24,2),b.pt(96,658.8,2)]).buffer(.06,cap_style='flat')
 b.ROOF_SUPPORT_PROFILE=parapets.union(arrival)


def pair_beam_faces(records):
 """Pair native A- VIGAS faces; retain measured offsets and overlaps."""
 strips=[]
 for j,record in enumerate(records):
  a,z=np.array(record['points']);u=z-a;length=np.linalg.norm(u)
  if length<.3:continue
  u/=length;n=np.array([-u[1],u[0]])
  for other in records[j+1:]:
   c,d=np.array(other['points']);v=d-c;size=np.linalg.norm(v)
   if size<.3 or abs(u[0]*v[1]/size-u[1]*v[0]/size)>.002:continue
   offset=float((c-a)@n);width=abs(offset)
   if not .10<width<.601:continue
   c0,d0=sorted([(c-a)@u,(d-a)@u]);lo=max(0,c0);hi=min(length,d0)
   if hi-lo<.30:continue
   strips.append(Polygon([a+u*lo,a+u*hi,a+u*hi+n*offset,a+u*lo+n*offset]))
 return set_precision(unary_union(strips),.0001)


def build_high_windows(b,data):
 """Recover explicit A-VENTANA ALTA spans. Vertical dimensions are estimates."""
 import manifold3d as mf
 import trimesh
 frames={}
 original_walls={i:unary_union([b.part_footprint(p) for p in b.PARTS if p['level']==i and p['material']=='wall' and p['role']!='door']) for i in range(4)}
 for j,q in enumerate(data.get('reviewedArchitecture',{}).get('highWindows',[])):
  i=q['level'];y0=b.NPT[i]+q['sillEstimated'];y1=b.NPT[i]+q['headEstimated'];a,z=np.array(q['axis']);u=(z-a)/np.linalg.norm(z-a)
  footprint=LineString([a,z]).buffer(q['halfDepthEstimated'],cap_style='flat')
  cutter=b.section(footprint,y1-y0);cutter.vertices[:,1]+=y0
  tool=mf.Manifold(mf.Mesh(np.asarray(cutter.vertices,dtype=np.float32),np.asarray(cutter.faces,dtype=np.uint32)))
  for p in b.PARTS:
   if p['level']!=i or p['material']!='wall' or '/Columnas' in p['group'] or p['role']=='door':continue
   v=b.materialize_vertices(p)
   if v[:,1].max()<=y0 or v[:,1].min()>=y1 or not b.part_footprint(p).intersects(footprint):continue
   mesh=trimesh.Trimesh(vertices=v,faces=np.arange(len(v)).reshape(-1,3),process=True);mesh.fix_normals()
   body=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
   if body.status()!=mf.Error.NoError:raise ValueError('Host HV no valido: '+p['id'])
   result=(body-tool)
   if abs(result.volume()-body.volume())<1e-8:continue
   out=result.to_mesh();v=np.asarray(out.vert_properties[:,:3],dtype=float);lo,hi=b.y_range(p['role'],i,p['bottom'],p['top']);v[:,1]=(v[:,1]-lo)/(hi-lo)
   mesh=trimesh.Trimesh(vertices=v,faces=np.asarray(out.tri_verts),process=True);mesh.fix_normals();vv=mesh.vertices[mesh.faces].reshape(-1,3)
   p['vertices']=vv.flatten().tolist();p['normals']=np.repeat(mesh.face_normals,3,axis=0).flatten().tolist();p['uv']=np.c_[vv[:,0]/3,vv[:,2]/3].flatten().tolist();p['note']+=' Vano alto recuperado de capa CAD; altura estimada.'
  # A high window needs an opaque wall below and above; preserve door transoms.
  door_axes=[LineString([v['hinge'],v['closed']]) for v in b.DOORS[i]]
  transom=any(footprint.intersection(axis.buffer(.08)).area>.02 for axis in door_axes)
  host=LineString([a,z]).buffer(.075,cap_style='flat')
  # Existing hosts already contain the sill and head. Adding overlays here
  # creates microscopic opaque skins and z-fighting after Boolean cleanup.
  if host.intersection(original_walls[i]).area < host.area*.5:
   if not transom:b.fixed_prism(host,b.NPT[i],y0,b.LEVEL_NAMES[i]+'/Ventanas_Altas',f'HV_{j+1}_antepecho','wall',True,i,'A-VENTANA ALTA','Espesor 0.15 y antepecho 2.05 m estimados; no se rellena vano de puerta.')
   b.fixed_prism(host,y1,b.NPT[i+1]-b.PARAMS['slabThickness'],b.LEVEL_NAMES[i]+'/Ventanas_Altas',f'HV_{j+1}_dintel','wall',True,i,'A-VENTANA ALTA','Cabeza 2.70 m estimada.')
  source=f"A-0{i+1} A-VENTANA ALTA: "+','.join(q['handles'])
  glass=LineString([a+u*.04,z-u*.04]).buffer(.006,cap_style='flat')
  b.fixed_prism(glass,y0+.04,y1-.04,b.LEVEL_NAMES[i]+'/Ventanas_Altas',f'HV_{j+1}_vidrio','glass',True,i,source,'Antepecho 2.05 y cabeza 2.70 m estimados; ancho y posicion de trazos CAD. Revisar alzado.')
  # Frames are consolidated per floor, avoiding a file for each bar.
  for footprint,lo,hi in [(LineString([a,z]).buffer(.02,cap_style='flat'),y0,y0+.04),(LineString([a,z]).buffer(.02,cap_style='flat'),y1-.04,y1),(LineString([a,a+u*.04]).buffer(.02,cap_style='flat'),y0+.04,y1-.04),(LineString([z-u*.04,z]).buffer(.02,cap_style='flat'),y0+.04,y1-.04)]:
   mesh=b.section(footprint,hi-lo);mesh.vertices[:,1]+=lo;frames.setdefault(i,[]).append(mesh)
 for i,meshes in frames.items():
  bodies=[mf.Manifold(mf.Mesh(np.asarray(x.vertices,dtype=np.float32),np.asarray(x.faces,dtype=np.uint32))) for x in meshes];out=mf.Manifold.batch_boolean(bodies,mf.OpType.Add).simplify(.0001).to_mesh();mesh=trimesh.Trimesh(vertices=np.asarray(out.vert_properties[:,:3]),faces=np.asarray(out.tri_verts),process=False);mesh.fix_normals()
  b.add_mesh(mesh,b.LEVEL_NAMES[i]+'/Ventanas_Altas','HV_Marcos_consolidados','metal',False,'fixed',i,0,1,'A-VENTANA ALTA; marcos estimados','Una malla de carpinteria por nivel; no modifica columnas.')
 b.EVIDENCE.append({'element':'Ventanas altas','sheet':'A-01 a A-04','count':len(data['reviewedArchitecture'].get('highWindows',[])),'confirmed':'Posicion y ancho de segmentos de A-VENTANA ALTA agrupados por extremos y paralelismo','estimated':'Cotas 2.05/2.70, vidrio 12 mm y marco 40 mm; cortador 0.36 m de profundidad','status':'Pendiente alzado e inspeccion Unity; no equivale a 74 ventanas'})
