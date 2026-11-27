"""Measured mesh profiles, not Unity screenshots or surveyed CAD sections."""
from pathlib import Path
import sys,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lid'))
from unity_text import read_mesh
from construir_lid_r3 import RX,RZ,WALLS,STAIR_WIDTH,U0,U1,U2,U3,CLEAR
from validar_lid_r3 import ray_heights

data=json.loads((ROOT/'Assets/UPCH/LIDTerrenoR3/Datos/Aplicacion_LID_R3.json').read_text())
new=read_mesh(ROOT/'Assets/UPCH/LIDTerrenoR3/Mallas/Site_LID_Descansos_R3.asset')
new.apply_transform(np.array(data['worldMatrix']).reshape(4,4))
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(12,8),gridspec_kw={'height_ratios':[1.35,1]})
fig.suptitle('LID · Terreno R3 adaptado a los descansos',x=.06,ha='left',fontsize=17,fontweight='bold',y=.97)
for ax,(name,wall,sign) in zip(axes[0],WALLS):
    x=np.linspace(U0,U3,100);e=np.linspace(-8,STAIR_WIDTH+CLEAR+8,75);xx,ee=np.meshgrid(x,e);zz=wall+sign*ee
    h=ray_heights(new,np.c_[xx.ravel(),zz.ravel()]).reshape(xx.shape);h[~np.isfinite(h)]=np.nan
    im=ax.pcolormesh(xx-RX,ee,h,shading='auto',vmin=-1.2,vmax=0,cmap='cividis')
    ax.axhline(0,color='white',ls='--',lw=1);ax.text(4,-6,'Huella del LID\n(sin modificar)',color='#333',ha='center')
    ax.plot([U0-RX,U1-RX,U2-RX,U3-RX],[STAIR_WIDTH+.75]*4,color='#ee5d28',lw=2,label='Aproximación exterior')
    ax.plot([RX-5.45-RX]*2+[-4],[STAIR_WIDTH+.75,.65,.65],color='#d9f236',lw=2,label='Entrada al descanso')
    ax.set(title='Lateral '+name.lower(),xlabel='Distancia longitudinal respecto a la raíz LID (m)',ylabel='Distancia hacia el exterior (m)')
    ax.set_xlim(U0-RX,U3-RX);ax.set_ylim(-8,STAIR_WIDTH+CLEAR+8)
    ax.legend(loc='upper right',fontsize=8)
cax=fig.add_axes([.925,.55,.013,.31])
fig.colorbar(im,cax=cax,label='Y del terreno en Campus (m)')
ax=axes[1,0];u=np.linspace(U0,U3,200);z=np.full(len(u),WALLS[0][1]+STAIR_WIDTH+.75);h=ray_heights(new,np.c_[u,z])
ax.plot(u-U0,np.zeros(len(u)),color='#777',ls='--',label='Antes: terreno R1')
ax.plot(u-U0,h,color='#216e57',lw=2,label='Después: R3')
ax.axhline(-1.2,color='#d1812c',ls=':',lw=1);ax.text(15.95,-1.05,'Nivel de las llegadas',ha='center',fontsize=9)
ax.set(title='Perfil de la aproximación exterior',xlabel='Recorrido longitudinal (m)',ylabel='Y del suelo (m)',ylim=(-1.4,.2))
ax.legend(fontsize=8);ax.grid(alpha=.2)
ax=axes[1,1];e=np.linspace(0,6.5,200);u=np.full(len(e),(U1+U2)/2);z=WALLS[0][1]+e;h=ray_heights(new,np.c_[u,z]);h[~np.isfinite(h)]=np.nan
ax.plot(e,h,color='#216e57',lw=2,label='Suelo R3')
ax.plot([0,STAIR_WIDTH],[-1.2,-1.2],color='#d1812c',lw=3,label='Losa original de llegada')
ax.plot([STAIR_WIDTH,6.5],[0,0],color='#777',ls='--')
ax.set(title='Sección transversal oeste · empalme al 40 %',xlabel='Distancia hacia el exterior desde la fachada (m)',ylabel='Y del suelo (m)',ylim=(-1.4,.2))
ax.legend(fontsize=8);ax.grid(alpha=.2)
fig.subplots_adjust(left=.07,right=.89,top=.88,bottom=.17,hspace=.43,wspace=.28)
fig.text(.06,.065,'Perfiles provisionales: 15 m al 8 % por aproximación; franja exterior de 1,50 m; banco oeste ≈40 %, este ≈15 %.',fontsize=9)
fig.text(.06,.035,'Gráfico de las mallas calculadas. No es una captura de Unity ni una certificación de las cotas del campus.',fontsize=9,color='#555')
fig.savefig(ROOT/'docs/lid/Comparativa_Terreno_R3.png',dpi=150)
