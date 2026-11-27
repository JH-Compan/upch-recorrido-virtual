"""Compare native window placement anchors with registered CAD references; no height certification."""
import sys,json,re,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lid'));from unity_text import *
p=UnityText(ROOT/'Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab');r=json.load(open(ROOT/'tools/lid/referencia_cad.json'));levels={v['name']:v for v in r['levels']};rows=[]
for ident,(kind,body) in p.docs.items():
 if kind!=33:continue
 go=ref(body,'m_GameObject');tr=p.go_transforms[go];path=p.path_for(tr)
 if '/Ventanas/' not in path or not re.search(r'_Vidrio_\d+$',p.names[go]):continue
 lev=path.split('/')[1];pos=p.world(tr)[:3,3];plan=[pos[0]+32.55,17.305-pos[2]]
 ws=levels[lev]['windows'];dist=[np.linalg.norm(np.array(plan)-[w['x'],w['y']]) for w in ws];d=float(min(dist));rows.append({'name':p.names[go],'level':lev,'plan':plan,'nearest_cad_distance_m':d})
result={'windows_checked':len(rows),'maximum_anchor_deviation_m':max(x['nearest_cad_distance_m'] for x in rows),'issues':[x for x in rows if x['nearest_cad_distance_m']>.001],'horizontal_anchors':rows,'opening_heights_certified':False}
(ROOT/'Assets/UPCH/LIDCompleto/Documentacion/Validacion_Ventanas_R2.json').write_text(json.dumps(result,indent=2)+'\n')
print({k:v for k,v in result.items() if k!='horizontal_anchors'})
raise SystemExit(bool(result['issues']))
