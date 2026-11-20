"""Create the review PDF and plan overlay from completed native-mesh audits."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as Patch
from shapely.geometry import shape, Polygon
from shapely.ops import unary_union
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A3, landscape
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'docs/lid'
R = json.loads((OUT/'validacion_actual.json').read_text())
C = json.loads((Path(__file__).parent/'referencia_cad.json').read_text())
H = {(x['level'],x['category']):shape(x['geometry']) for x in json.loads((OUT/'huellas_nativas.json').read_text())}
assert not R['errors']
NAVY='#15354b'; BLUE='#14829a'; GRAY='#52636b'
names={'Sotano':'Sótano','Piso_01':'Primer piso','Piso_02':'Segundo piso','Piso_03':'Tercer piso','Piso_04':'Cuarto piso','Azotea':'Azotea'}


def polygons(g):
    if g.is_empty:return []
    return list(g.geoms) if hasattr(g,'geoms') else [g]


def edges(ax,g,color,width=.4):
    for p in polygons(g):
        if not isinstance(p,Polygon):continue
        for ring in [p.exterior,*p.interiors]:
            x,y=ring.xy;ax.plot(x,y,color=color,lw=width)


def draw_plan(ax,l):
    name=l['name']
    source=unary_union([shape(p) for p in l['walls']]+[shape(r['polygon']) for r in l['wallRepairs']]+[shape(p) for p in l['drywall']]+[shape(p) for p in l.get('low',[])])
    actual=unary_union([H.get((name,'Muros'),Polygon()),H.get((name,'Tabiques'),Polygon()),H.get((name,'Muros_Bajos'),Polygon())])
    floor=next(x for x in C['floors'] if x['name']==name)
    edges(ax,shape(floor['floorGeometry']),'#bfc7ca',.3)
    for p in polygons(actual):
        if isinstance(p,Polygon):ax.add_patch(Patch(list(p.exterior.coords),facecolor='#d1e9ef',edgecolor='none'))
    edges(ax,source,'#3d464a',.38);edges(ax,actual,BLUE,.35)
    if name=='Sotano':
        for q in C['entry_clips']:
            p=shape(q['polygon']);ax.add_patch(Patch(list(p.exterior.coords),facecolor='#e9e5d9',edgecolor='#bdaf85',lw=.3,alpha=.8))
    labels=[x for x in C['room_labels'] if x['level']==name]
    for t in labels:
        x,z=t['position'][0],t['position'][2]
        ax.plot(x+32.55,17.305-z,'.',color='#c27b2c',ms=1.7)
    ax.annotate('',xy=(65.1,-2),xytext=(0,-2),arrowprops={'arrowstyle':'|-|','lw':.7,'color':NAVY})
    ax.text(32.55,-2.5,'65,10 m',ha='center',va='bottom',fontsize=8,color=NAVY)
    ax.text(67,17.3,'34,61 m\n(rotulada)',ha='center',va='center',fontsize=7,color=NAVY)
    ax.set_xlim(-3,70);ax.set_ylim(39,-4.5);ax.set_aspect('equal');ax.axis('off')
    npt=l['elevation'];world=npt-1.2
    ax.set_title(f'{names[name]}  |  NPT {npt:+.2f} m  |  Campus Y {world:+.2f} m',loc='left',fontsize=10,fontweight='bold',color=NAVY,pad=2)


def paragraph(c,text,x,y,width,size=9,color=NAVY):
    style=ParagraphStyle('body',fontName='Helvetica',fontSize=size,leading=size*1.42,textColor=HexColor(color),alignment=TA_LEFT)
    p=Paragraph(text,style);_,h=p.wrap(width,1000);p.drawOn(c,x,y-h);return y-h-9


def main():
    plt.rcParams['font.family']='DejaVu Sans'
    fig,axs=plt.subplots(3,2,figsize=(14,12))
    for ax,l in zip(axs.flat,C['levels']):draw_plan(ax,l)
    fig.suptitle('LID | Contraste de plantas con mallas nativas de Unity',x=.045,ha='left',fontsize=17,color=NAVY,fontweight='bold')
    fig.text(.045,.028,'Gris: control CAD · Azul: sección nativa · Ocre: referencias de ambientes · Beige: zona de intradós excluida del contraste constante',fontsize=9,color=GRAY)
    fig.tight_layout(rect=(.025,.05,.99,.96));fig.savefig(OUT/'Control_Plantas_LID_Actual.png',dpi=180);plt.close(fig)
    pdf=OUT/'Validacion_LID_Actual.pdf';c=canvas.Canvas(str(pdf),pagesize=A4);w,h=A4
    c.setTitle('LID - validación y corrección de sótano, distribución y mobiliario')
    c.setAuthor('Proyecto de recorrido virtual UPCH')
    c.setFillColor(HexColor(NAVY));c.rect(0,h-107,w,107,fill=1,stroke=0);c.setFillColor(white);c.setFont('Helvetica-Bold',24);c.drawString(38,h-49,'LID: corrección y validación')
    c.setFont('Helvetica',10);c.drawString(38,h-74,'Revisión del 20 de noviembre de 2026 · Unity 6000.3.10f1')
    y=h-130
    y=paragraph(c,'<b>Resultado:</b> controles geométricos ejecutados sin errores. La entrega corrige la colocación del edificio en Campus y el cruce del terreno con el sótano. Mantiene la arquitectura y reduce el mobiliario.',38,y,w-76,10)
    for title,text in [
        ('Colocación','Raíz LID: Y +0,35 a -1,20 m. El pavimento exterior del modelo pasa de +1,55 m a Y 0 de Campus. Los NPT relativos permanecen iguales.'),
        ('Terreno','Nueva malla persistente para renderizado y colisión; recorte de 2.245,728988 m² para sótano y accesos. El asset del terreno original se conserva.'),
        ('Interiores','Retiradas 2.833 piezas simplificadas de computadoras, asientos y muebles mal clasificados. Permanecen 1.037 cuerpos de mueble y 1.037 encimeras.')]:
        y=paragraph(c,f'<b>{title}.</b> {text}',38,y,w-76,9)
    data=[['Planta','NPT del plano (m)','Y en Campus (m)']]+[[names[x['name']],f"{x['npt']:+.2f}",f"{x['world_y_campus']:+.2f}"] for x in R['levels']]
    t=Table(data,colWidths=[180,150,180]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor(NAVY)),('TEXTCOLOR',(0,0),(-1,0),white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),9),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#f0f5f6'),white]),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('ALIGN',(1,1),(-1,-1),'RIGHT')]));_,th=t.wrap(w-76,1000);t.drawOn(c,38,y-th);y-=th+15
    y=paragraph(c,'<b>Evidencia:</b> 22 secciones de muros/tabiques, 569 referencias de ambientes, 790 comparaciones de trazas de hojas de puerta y seis suelos. Los rótulos y trazas pueden repetirse: no son conteos de recintos o puertas únicos.',38,y,w-76,9)
    y=paragraph(c,'<b>Límite de precisión:</b> la cota exterior +1,20 m sigue siendo una hipótesis del modelo. Los planos adjuntos no aportan cortes para confirmar esa cota, alturas de todos los vanos, espesores o contrahuellas exteriores. No se ha ejecutado Unity Editor, Play ni visor. No se certifica fidelidad del 100 % a la obra real.',38,y,w-76,9,color='#7d4d20')
    y=paragraph(c,'Base: develop / 98e8d8030f6e. Detalles, tolerancias y catálogo: docs/lid/VALIDACION_ACTUAL.md, validacion_actual.json y ambientes_actuales.csv.',38,y,w-76,8,color=GRAY)
    c.setFont('Helvetica',8);c.drawString(38,24,'1 / 4 · Revisión técnica del modelo para el avance del grupo');c.showPage()
    for page in range(3):
        c.setPageSize(landscape(A3));w,h=landscape(A3)
        c.setFillColor(HexColor(NAVY));c.setFont('Helvetica-Bold',18);c.drawString(32,h-33,'LID | Control de plantas y referencias de ambientes')
        c.setFont('Helvetica',9);c.drawString(32,h-51,'Huella principal rotulada: 65,10 × 34,61 m. Las proyecciones y los accesos exteriores se controlan por separado.')
        fig,axs=plt.subplots(2,1,figsize=(14.7,9.1))
        for ax,l in zip(axs,C['levels'][page*2:page*2+2]):draw_plan(ax,l)
        fig.tight_layout(pad=1.2);path=OUT/f'.plan_{page}.png';fig.savefig(path,dpi=160);plt.close(fig)
        c.drawImage(ImageReader(path),45,45,width=w-90,height=h-115,preserveAspectRatio=True,anchor='c')
        c.setFillColor(HexColor(GRAY));c.setFont('Helvetica',8);c.drawString(32,27,'Gris: control CAD. Azul: sección de las mallas nativas. Ocre: posición de rótulos del plano. Beige: intradós del ingreso, excluido de sección constante.')
        c.drawRightString(w-32,14,f'{page+2} / 4 · Sin certificación de alturas no acotadas ni prueba en Play');c.showPage();path.unlink()
    c.save();print(pdf)


if __name__=='__main__':main()
