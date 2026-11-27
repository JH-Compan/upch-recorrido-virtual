from pathlib import Path
import json,pickle,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from PIL import Image
sys.path.insert(0,str(Path(__file__).parent))
import construir as b
BASE=b.BASE;OUT=BASE/'Documentacion/Vistas';OUT.mkdir(parents=True,exist_ok=True)
D=json.loads((BASE/'Datos/Modelo_H.json').read_text());parts=D['items'];trace=json.loads(Path(__file__).parent.joinpath('Fuentes/Trazado_Vectorial.json').read_text())
colors={'wall':'#e8e2d2','floor':'#a3b2b9','glass':'#467f97','metal':'#445967'}
for i in range(5):
 fig,ax=plt.subplots(figsize=(16,9));fig.patch.set_facecolor('#f7f7f3');ax.set_facecolor('#f7f7f3')
 drawn=[]
 for p in parts:
  if p['hidden'] or p['level']!=i:continue
  v=b.materialize_vertices(p).reshape(-1,3,3)
  if p['group'].startswith('06_'):
   if p['material']!='floor':continue
   c='#cba66d';z=3;alpha=.95
  else:
   if p['role']=='slab':c='#e2e3de';z=1;alpha=1
   elif p['material']=='glass':c='#5595a3';z=5;alpha=.7
   elif p['material']=='floor':continue
   else:
    if v[:,:,1].min()>b.NPT[i]+1.20 or v[:,:,1].max()<b.NPT[i]+.4:continue
    c='#303e45';z=4;alpha=1
  n=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);mask=n[:,1]>.000001
  ps=[q[:,[0,2]] for q in v[mask]]
  if ps:ax.add_collection(PolyCollection(ps,facecolors=c,edgecolors='none',alpha=alpha,zorder=z));drawn.extend(ps)
 for q in trace['levels'][i]['labels']:
  text=q['text']
  if any(x in text for x in ['PROY','NPT=','MURO','PARAPETO','VACIO','RAMPA']):continue
  x,y=b.pt(*q['pdfCentre'],i)
  if len(text)>36:text=text[:33]+'…'
  ax.text(x,y,text,fontsize=5.1,ha='center',va='center',zorder=6,color='#263d43')
 allv=np.concatenate(drawn);mn=allv.min(axis=0)-1;mx=allv.max(axis=0)+1
 ax.set_xlim(mn[0],mx[0]);ax.set_ylim(mn[1],mx[1]);ax.set_aspect('equal');ax.set_xlabel('X local (m)');ax.set_ylabel('Z local (m)');ax.grid(alpha=.15)
 ax.set_title(f'PABELLÓN H · {b.LEVEL_NAMES[i][3:].replace("_"," ").upper()} · NPT {b.NPT[i]:+.2f} m',loc='left',fontsize=15,fontweight='bold',pad=18)
 fig.text(.06,.035,'Geometría construida · alturas configurables · comprobación en Unity pendiente',color='#52676e',fontsize=10)
 fig.savefig(OUT/f'Planta_{i+1}.png',dpi=150,bbox_inches='tight');plt.close(fig)
print('Plantas exportadas en',OUT)
