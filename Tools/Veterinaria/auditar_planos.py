"""Independent PDF/serialized-mesh checks. Architectural candidates require review."""
from pathlib import Path
import argparse,json,re,hashlib,subprocess
import fitz,numpy as np
from shapely.geometry import Polygon,Point,LineString
from shapely.ops import unary_union
from shapely import affinity
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'Assets/UPCH/Veterinaria'
REG=[(36.12,57.24),(21.36,.60),(0,0),(0,0),(0,0)];S=72/2.54;O=(824.76,498.36)
def mesh(p):
 text=p.read_text();v=np.frombuffer(bytes.fromhex(re.search(r'_typelessdata: (\w+)',text)[1]),dtype='<f4').reshape(-1,8)
 dtype='<u4' if 'm_IndexFormat: 1' in text else '<u2';t=np.frombuffer(bytes.fromhex(re.search(r'm_IndexBuffer: (\w+)',text)[1]),dtype=dtype).reshape(-1,3)
 return v[t,:3]
def raw(points,i):
 a=np.array(points);return np.c_[a[:,0]*S+O[0]-REG[i][0],O[1]-REG[i][1]-a[:,1]*S]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('pdf',type=Path);args=ap.parse_args();source=fitz.open(args.pdf);model=json.loads((BASE/'Datos/Modelo_H.json').read_text());out=Path(__file__).parent/'Auditoria';out.mkdir(exist_ok=True)
 result={'commitAudited':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'sourceSha256':hashlib.sha256(args.pdf.read_bytes()).hexdigest(),'sourceMatchesModel':False,'levels':[],'status':'NO_APROBADO_ARQUITECTONICAMENTE','UnityPlay':'NO_EJECUTADO','limits':['La cobertura de trazos es un detector de candidatos, no certificacion de muros ni de ambientes.','Alturas estimadas, alzados y conexiones inferidas no se validan por cerrar una malla.']};result['sourceMatchesModel']=result['sourceSha256']==model['sourcePdfSha256'];pdf=fitz.open()
 for i,page in enumerate(source):
  target=pdf.new_page(width=page.rect.width,height=page.rect.height);target.insert_image(target.rect,stream=page.get_pixmap(matrix=fitz.Matrix(1,1)).tobytes('png'));geoms=[];slabTops=[];shape=target.new_shape()
  for p in model['items']:
   if p['level']!=i or p['hidden'] or p['group'].startswith('06_'):continue
   triangles=mesh(BASE/'Generado/Mallas'/f"{p['id']}.asset");norm=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0]);cap=triangles[norm[:,1]>1e-9];polys=[Polygon(t[:,[0,2]]) for t in cap]
   if p['role']=='slab':slabTops.append(float(triangles[:,:,1].max()));continue
   if p['material']=='floor' or p['role'] in ['beam','door','doorLintel','windowLintel']:continue
   if p['collider']:geoms.extend(polys)
   color=(.05,.45,.9) if p['material']=='glass' else ((.85,.5,0) if p['role']=='door' else (.9,.08,.15))
   for tri in cap:
    points=raw(tri[:,[0,2]],i);shape.draw_polyline([fitz.Point(*q) for q in points]+[fitz.Point(*points[0])]);shape.finish(color=None,fill=color,fill_opacity=.22)
  shape.commit();coverage=unary_union(geoms);area=coverage.bounds;missing=[];total=0
  # Independent thick black linework: sample every 0.20 m, not extracted faces.
  if i<4:
   for d in page.get_drawings():
    if d['width']<1.60 or d['color']!=(0,0,0) or d['dashes']!='[] 0':continue
    for it in d['items']:
     if it[0]!='l':continue
     a,b=[q*page.rotation_matrix for q in it[1:]];pts=np.array([[q.x,q.y] for q in [a,b]]);pts[:,0]=(pts[:,0]+REG[i][0]-O[0])/S;pts[:,1]=(O[1]-pts[:,1]-REG[i][1])/S;line=LineString(pts)
     if line.length<.25:continue
     for distance in np.linspace(0,line.length,max(2,int(line.length/.2)+1)):
      q=line.interpolate(distance)
      if not(area[0]-1<q.x<area[2]+1 and area[1]-1<q.y<area[3]+1):continue
      total+=1
      if coverage.distance(q)>.055:missing.append([q.x,q.y])
   for q in missing:
    xy=raw([q],i)[0];target.draw_circle(fitz.Point(*xy),1.5,color=(1,0,.6),width=.6)
  npt=model['npt'][i];texts=page.get_text();sourceNpt=[float(v) for v in re.findall(r'NPT\s*=\s*([+−-]?\d+\.\d+)',texts.replace('−','-'))]
  result['levels'].append({'sheet':f'A-0{i+1}','sourceHasExpectedNPT':any(abs(x-npt)<1e-4 for x in sourceNpt),'modelNPT':npt,'slabTopsSerialized':slabTops,'NPTMatches':bool(slabTops) and all(abs(x-npt)<1e-5 for x in slabTops),'sourceLineSamples':total,'lineSamplesToReview':len(missing),'candidateLocationsXZ':missing})
  target.insert_text((30,40),f"A-0{i+1}: SUPERPOSICION DE MALLAS / PDF. Rojo: cerramientos. Azul: vidrio. Magenta: candidatos a revisar.",fontsize=10,color=(.7,0,0))
 pdf.save(out/'Superposicion_5_Plantas.pdf',garbage=4,deflate=True);(out/'Resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({**result,'levels':[{k:v for k,v in l.items() if k!='candidateLocationsXZ'} for l in result['levels']]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
