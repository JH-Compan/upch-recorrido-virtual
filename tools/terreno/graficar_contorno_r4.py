"""Computed perimeter comparison, not a Unity screenshot or surveyed section."""
from pathlib import Path
import sys,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lid'))
from unity_text import asset_guids,read_mesh
from validar_lid_r3 import ray_heights

d=json.loads((ROOT/'Assets/UPCH/LIDContornoR4/Datos/Aplicacion_Contorno_R4.json').read_text());g=asset_guids(ROOT/'Assets')
old=read_mesh(g[d['oldGuid']]);new=read_mesh(g[d['newGuid']]);matrix=np.array(d['worldMatrix']).reshape(4,4)
old.apply_transform(matrix);new.apply_transform(matrix)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig=plt.figure(figsize=(12,9));gs=fig.add_gridspec(2,2,height_ratios=[1.2,1]);axes=[fig.add_subplot(gs[0,i]) for i in [0,1]]
fig.suptitle('LID · R4: contorno bajo las ventanas inferiores',x=.06,ha='left',fontsize=17,fontweight='bold',y=.97)
x=np.linspace(90,137,170);z=np.linspace(70,147,220);xx,zz=np.meshgrid(x,z);points=np.c_[xx.ravel(),zz.ravel()]
for ax,m,title in zip(axes,[old,new],['Antes · R3 junto a las escaleras','Después · R4 alrededor del edificio']):
    h=ray_heights(m,points).reshape(xx.shape);h[~np.isfinite(h)]=np.nan
    im=ax.pcolormesh(xx,zz,h,shading='auto',vmin=-1.2,vmax=0,cmap='cividis')
    ax.text(113.9,108.6,'LID\nEstructura e interior\nsin modificar',ha='center',va='center',fontsize=10)
    probes=np.array([[p['x'],p['z']] for p in d['windows']]);ax.scatter(probes[:,0],probes[:,1],s=3,c='#ec5c42' if m is old else '#42ab78')
    ax.set(title=title,xlabel='X en Campus (m)',ylabel='Z en Campus (m)');ax.set_aspect('equal')
cax=fig.add_axes([.91,.54,.015,.32]);fig.colorbar(im,cax=cax,label='Altura del suelo Y (m)')
ax=fig.add_subplot(gs[1,:])
chosen=next((p for p in d['glazing'] if p['name']=='LID_00791_Vidrio_081'),d['glazing'][0])
b=np.array(chosen['worldBounds']);glass_x=b[:,0].mean();glass_z=b[:,2].mean();distance=np.linspace(0,5,400)
profile=np.c_[glass_x-distance,np.full(len(distance),glass_z)]
a,c=ray_heights(old,profile),ray_heights(new,profile);a[~np.isfinite(a)]=np.nan;c[~np.isfinite(c)]=np.nan
ax.plot(distance,a,color='#8c8c8c',ls='--',lw=2,label='Suelo R3')
ax.plot(distance,c,color='#217b5e',lw=2,label='Suelo R4')
frame=chosen['frameBaseY'];ax.add_patch(Rectangle((-.08,frame),.08,1.7,facecolor='#b9d8e8',edgecolor='#365162'))
ax.axhline(frame,color='#365162',ls=':',lw=1);ax.text(.2,frame+.055,'Base del marco',color='#365162',fontsize=9)
ax.annotate('Franja baja junto a la fachada',xy=(.45,-.70),xytext=(1,-1.1),arrowprops={'arrowstyle':'->'},ha='center')
ax.set(title='Sección representativa frente a una ventana de la fachada',xlabel='Distancia desde el vidrio hacia el exterior (m)',ylabel='Y en Campus (m)',xlim=(-.2,5),ylim=(-1.2,.3))
ax.grid(alpha=.18);ax.legend(loc='upper right',fontsize=9)
fig.subplots_adjust(left=.08,right=.88,top=.89,bottom=.16,hspace=.34,wspace=.3)
fig.text(.06,.075,'Franja provisional de 0,60 m, normalmente en Y=-0,70 m; los descansos más bajos y las plataformas existentes se conservan.',fontsize=9)
fig.text(.06,.045,'55 ventanas / 165 muestras de suelo: ninguna cubierta en el control geométrico. Cotas exteriores aún sin levantamiento confirmado.',fontsize=9)
fig.text(.06,.02,'Gráfico calculado de las mallas serializadas; no es una captura de Unity. Las caras verticales de plataformas no son rampas de paso.',fontsize=9,color='#555')
fig.savefig(ROOT/'docs/lid/Comparativa_Contorno_R4.png',dpi=150)
