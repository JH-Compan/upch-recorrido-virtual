"""Local materials for H. Photographic colour references, not measured finishes."""
import hashlib,re
import numpy as np
from shapely.geometry import Point

def material_assets(root,base,uid):
 template=(root/'Assets/UPCH/Arte/Edificios/D/Materiales/PanelBlanco.mat').read_text()
 folder=base/'Materiales';folder.mkdir(exist_ok=True);result={}
 for name,color,metal,smooth in [('H_Puerta_Interior',(.56,.51,.43,1),0,.32),('H_Hormigon_Beige',(.69,.64,.52,1),0,.23),('H_Zocalo_Rojizo',(.42,.105,.055,1),0,.25),('H_Carpinteria_Oscura',(.10,.085,.065,1),.5,.4)]:
  path=folder/(name+'.mat');text=template.replace('m_Name: PanelBlanco','m_Name: '+name)
  col='{r: %s, g: %s, b: %s, a: %s}'%color
  for key in ['_BaseColor','_Color']:text=re.sub(r'(- '+key+r': )\{[^}]+\}',lambda m:m[1]+col,text)
  for key,value in [('_Metallic',metal),('_Smoothness',smooth)]:text=re.sub(r'(- '+key+r': )[^\n]+',lambda m:m[1]+str(value),text)
  if not path.exists():path.write_text(text)
  guid=uid(path.relative_to(root));meta=path.with_name(path.name+'.meta')
  if not meta.exists():meta.write_text('fileFormatVersion: 2\nguid: '+guid+'\nNativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 2100000\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
  else:guid=re.search(r'^guid: (\w+)',meta.read_text(),re.M)[1]
  result[name]=guid
 # Local glazing copy: keep the existing URP shader and transparent settings.
 glass_source=None
 for m in (root/'Assets').rglob('*.mat.meta'):
  if 'd1b9e06e823bed44f869d425de7da733' in m.read_text():glass_source=m.with_suffix('');break
 if glass_source:
  path=folder/'H_Vidrio_Gris.mat';text=glass_source.read_text();text=re.sub(r'  m_Name: [^\n]+','  m_Name: H_Vidrio_Gris',text)
  for key in ['_BaseColor','_Color']:text=re.sub(r'(- '+key+r': )\{[^}]+\}',lambda m:m[1]+'{r: 0.12, g: 0.16, b: 0.17, a: 0.55}',text)
  if not path.exists():path.write_text(text)
  guid=uid(path.relative_to(root));meta=path.with_name(path.name+'.meta')
  if not meta.exists():meta.write_text('fileFormatVersion: 2\nguid: '+guid+'\nNativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 2100000\n  userData: \n  assetBundleName: \n  assetBundleVariant: \n')
  else:guid=re.search(r'^guid: (\w+)',meta.read_text(),re.M)[1]
  result['H_Vidrio_Gris']=guid
 return result

def apply(parts,envelopes,vertices,materials):
 for p in parts:
  if p['material']=='glass' and materials.get('H_Vidrio_Gris'):p['materialGuid']=materials['H_Vidrio_Gris']
  if 'CAD_Carpinteria_' in p['name'] or p['name'] in ['HV_Marcos_consolidados','Marcos_carpinteria_fijos']:p['materialGuid']=materials['H_Carpinteria_Oscura']
  if p['role']=='door':p['materialGuid']=materials['H_Puerta_Interior']
  if p['hidden'] or p['material'] not in ['wall','floor'] or p['role']=='door':continue
  if p['material']=='floor' and p['role']!='slab':continue
  tris=vertices(p).reshape(-1,3,3);centers=tris.mean(axis=1);norm=np.cross(tris[:,1]-tris[:,0],tris[:,2]-tris[:,0]);norm/=np.maximum(np.linalg.norm(norm,axis=1,keepdims=True),1e-12)
  guids=[p['materialGuid'],materials['H_Hormigon_Beige'],materials['H_Zocalo_Rojizo']];indices=[];env=envelopes[p['level']]
  for c,n in zip(centers,norm):
   mat=0
   if abs(n[1])<.1 and not env.buffer(.06).covers(Point(c[[0,2]]+n[[0,2]]*.40)):
    mat=1
    # White recessed portal, beige upper facade. Heights remain estimates.
    if c[0]>10 and c[2]<-4 and c[1]<7.1:mat=0
    if p['level']==0 and c[0]>21 and c[2]<-2:mat=2
   indices.append(mat)
  if any(indices):
   used=sorted(set(indices));remap={v:k for k,v in enumerate(used)};p['materialGuids']=[guids[k] for k in used];p['triangleMaterials']=[remap[k] for k in indices]
