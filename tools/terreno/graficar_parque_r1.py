"""Numerical previews of the R1 candidate, not Unity screenshots."""
from pathlib import Path
import json
import numpy as np
from scipy.interpolate import LinearNDInterpolator
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PlotPolygon
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
control = json.loads((ROOT/'Assets/UPCH/TerrenoCampusR1/Datos/Control_Terreno_R1.json').read_text())
field = np.load(ROOT/'tools/terreno/campo_parque_r1.npz')
fn = LinearNDInterpolator(field['vertices_cad14'], field['heights'], fill_value=0)
offset = np.array(control['registration']['cad14_to_world_translation'])
bounds = control['work_domain_cad14']
x = np.linspace(bounds[0], bounds[2], 420)
y = np.linspace(bounds[1], bounds[3], 290)
xx, yy = np.meshgrid(x, y)
zz = fn(xx, yy)
extent = [x[0]+offset[0], x[-1]+offset[0], y[0]+offset[1], y[-1]+offset[1]]
fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), sharex=True, sharey=True)
for ax, data, title in zip(axes, [np.zeros_like(zz), zz], ['Antes: suelo horizontal', 'R1: plataformas y empalmes interpolados']):
    image = ax.imshow(data, origin='lower', extent=extent, cmap='coolwarm', vmin=-.34, vmax=.45)
    for key in ['fixed_high_control_polygon','fixed_low_polygon']:
        polygon = shape(control[key])
        points = np.array(polygon.exterior.coords)+offset
        ax.plot(points[:, 0], points[:, 1], color='#303030', lw=.8, ls='--')
    polygon = np.array(shape(control['reserved_platform']).exterior.coords)+offset
    ax.add_patch(PlotPolygon(polygon, facecolor='#eeeeee', edgecolor='#555555', hatch='///', lw=.7))
    ax.text(83, 81, '+1,40 m\npendiente de\nreconstruir', fontsize=8, ha='center', bbox=dict(facecolor='white', alpha=.9, edgecolor='none'))
    ax.set_title(title, fontsize=11)
    ax.set_xlabel('X de Unity (m)')
    ax.grid(alpha=.12)
axes[0].set_ylabel('Z de Unity (m)')
cax = fig.add_axes([.885,.24,.018,.57])
fig.colorbar(image, cax=cax, label='Cota del candidato (m), datum de trabajo del parque')
fig.suptitle('Parque Central - primera fase del relieve', fontsize=15)
fig.text(.08,.035,'Contornos discontinuos: zonas de control. Trama: plataforma todavía no modelada.\nLos empalmes no equivalen a los siete perfiles CAD; los edificios permanecen en su posición.', fontsize=10)
fig.subplots_adjust(bottom=.18, top=.86, wspace=.12, right=.82)
fig.savefig(ROOT/'docs/terreno/Comparativa_Alturas_R1.png', dpi=160, facecolor='white')
plt.close(fig)
axis = np.linspace(*np.array(control['north_ramp_axis_cad14']), 81)
distance = np.linalg.norm(axis-axis[0],axis=1)
fig, ax = plt.subplots(figsize=(9,4.6))
ax.plot(distance,np.zeros_like(distance),ls='--',color='#7d7d7d',label='Suelo anterior: Y=0')
ax.plot(distance,fn(axis),lw=2.5,color='#236a8d',label='Perfil R1 controlado al 8 %')
ax.scatter([0,distance[-1]],[.45,-.34],color='#236a8d')
ax.annotate('+0,45 m',(0,.45),xytext=(8,-17),textcoords='offset points')
ax.annotate('-0,34 m',(distance[-1],-.34),xytext=(-60,10),textcoords='offset points')
ax.set(xlabel='Distancia horizontal sobre el eje (m)',ylabel='NPT del parque (m)',title='Eje norte B2E75: 0,79 m / 9,875 m = 8 %')
ax.grid(alpha=.2);ax.legend();fig.tight_layout();fig.savefig(ROOT/'docs/terreno/Perfil_Norte_R1.png',dpi=160,facecolor='white')
