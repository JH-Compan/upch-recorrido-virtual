"""Check saved R4 mesh, window exposure and preservation of accepted R3."""
from pathlib import Path
import sys,json,subprocess
import numpy as np
import trimesh
from shapely.geometry import Polygon,Point,shape
from shapely.ops import unary_union
from shapely import contains_xy
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lid'))
from unity_text import read_mesh,asset_guids,UnityText,ref
from construir_lid_r3 import geometry_hash,RX,RZ,ROOT_Y
from validar_lid_r3 import ray_heights

def main():
    a=ROOT/'Assets/UPCH/LIDContornoR4/Datos/Aplicacion_Contorno_R4.json'
    data=json.loads(a.read_text());rp=ROOT/'docs/lid/Validacion_Contorno_R4.json';report=json.loads(rp.read_text())
    r3=json.loads((ROOT/'Assets/UPCH/LIDTerrenoR3/Datos/Aplicacion_LID_R3.json').read_text())
    g=asset_guids(ROOT/'Assets');old=read_mesh(g[data['oldGuid']]);new=read_mesh(g[data['newGuid']])
    assert geometry_hash(old)==data['oldHash']==r3['newHash'] and geometry_hash(new)==data['newHash']
    matrix=np.array(data['worldMatrix']).reshape(4,4);old.apply_transform(matrix);new.apply_transform(matrix)
    new.merge_vertices();assert new.is_watertight and new.volume>0
    xz=lambda samples:np.array([[s['x'],s['z']] for s in samples])
    wp=xz(data['windows']);limit=np.array([p['y'] for p in data['windows']]);before=ray_heights(old,wp);after=ray_heights(new,wp)
    assert np.isfinite(after).all() and np.all(after<=limit+.001)
    perimeter=xz(data['perimeterSamples']);perimeter_h=ray_heights(new,perimeter)
    assert np.max(abs(perimeter_h-np.array([p['y'] for p in data['perimeterSamples']])))<.001
    protected=shape(report['protected_approaches']);unprotected=~contains_xy(protected.buffer(.03),perimeter[:,0],perimeter[:,1])
    old_perim=ray_heights(old,perimeter);target=np.minimum(old_perim,-.7)
    assert np.max(perimeter_h[unprotected]-target[unprotected])<.001
    probe=xz(data['samples']);h=ray_heights(new,probe);prev=ray_heights(old,probe)
    assert np.max(abs(h-np.array([p['y'] for p in data['samples']])))<.001
    assert np.all(h<=prev+.001)
    stair=ray_heights(new,xz(data['stairs']));tops=np.array([p['y'] for p in data['stairs']]);assert np.all(stair<tops-.02)
    # Join the unchanged lower slabs for the two original entry paths.
    prefab=UnityText(ROOT/'Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab');slabs=[]
    import re
    for kind,body in prefab.docs.values():
        if kind!=33:continue
        go=ref(body,'m_GameObject')
        if prefab.names[go] not in ['LID_15654_Oeste_Llegada','LID_15714_Este_Llegada']:continue
        m=read_mesh(g[re.search(r'guid: ([a-f0-9]{32})',body)[1]]);m.apply_transform(prefab.world(prefab.go_transforms[go]));v=m.vertices.copy()
        m.vertices=np.c_[RX+v[:,2],ROOT_Y+v[:,1],RZ-v[:,0]];m.faces=m.faces[:,[0,2,1]];slabs.append(m)
    entry=ray_heights(trimesh.util.concatenate([new,*slabs]),xz(r3['entrySamples']));entry_expected=np.array([p['y'] for p in r3['entrySamples']])
    entry_error=float(np.max(abs(entry-entry_expected)));assert entry_error<.001
    r1=json.loads((ROOT/'Assets/UPCH/TerrenoCampusR1/Datos/Aplicacion_Terreno_R1.json').read_text());r1h=ray_heights(new,xz(r1['samplesWorld']))
    r1_error=float(np.max(abs(r1h-np.array([p['y'] for p in r1['samplesWorld']]))));assert r1_error<.001
    grid=np.array([(x,z) for x in np.linspace(-60,150,25) for z in np.linspace(0,150,23)])
    outside=~contains_xy(shape(report['work_polygon']).buffer(.001),grid[:,0],grid[:,1]);grid=grid[outside]
    ho,hn=ray_heights(old,grid),ray_heights(new,grid);assert np.array_equal(np.isfinite(ho),np.isfinite(hn))
    valid=np.isfinite(ho);outside_error=float(np.max(abs(ho[valid]-hn[valid])));assert outside_error<.001
    def footprint(m):return unary_union([Polygon(t[:,[0,2]]) for t in m.vertices[m.faces[m.face_normals[:,1]>.001]]])
    op,np_=footprint(old),footprint(new);plan_error=float(op.symmetric_difference(np_).area);assert plan_error<.05
    rim=op.buffer(-.01).exterior;rimxz=np.array([rim.interpolate(t,normalized=True).coords[0] for t in np.linspace(0,1,500,endpoint=False)])
    rim_old,rim_new=ray_heights(old,rimxz),ray_heights(new,rimxz);assert np.isfinite(rim_old).all() and np.isfinite(rim_new).all()
    rim_error=float(np.max(abs(rim_old-rim_new)));assert rim_error<.001
    # Existing high approaches keep their elevations. Vertical faces at the
    # sides of these areas are explicit closed steps, not steep fake ramps.
    protected_points=[]
    for poly in protected.geoms:
        x0,z0,x1,z1=poly.bounds
        protected_points.extend((x,z) for x in np.linspace(x0+.08,x1-.08,9) for z in np.linspace(z0+.08,z1-.08,5))
    hp_old,hp_new=ray_heights(old,protected_points),ray_heights(new,protected_points);ok=np.isfinite(hp_old)
    assert np.isfinite(hp_new[ok]).all();protected_error=float(np.max(abs(hp_old[ok]-hp_new[ok])));assert protected_error<.001
    normals=new.face_normals;surface=normals[:,1]>1e-6
    slopes=100*np.linalg.norm(normals[surface][:,[0,2]],axis=1)/normals[surface,1]
    maxslope=float(slopes.max());assert maxslope<55,maxslope
    # No tracked file from the accepted R3 base is overwritten.
    protected_files=['Assets/UPCH/Scenes/Campus.unity','Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab',str(g[data['oldGuid']].relative_to(ROOT))]
    for p in protected_files:assert (ROOT/p).read_bytes()==subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
    scene=(ROOT/'Assets/UPCH/Scenes/Campus.unity').read_text();current=scene.replace(r3['oldGuid'],r3['newGuid'])
    assert current.count(data['oldGuid'])==2
    applied=current.replace(data['oldGuid'],data['newGuid']);assert applied.replace(data['newGuid'],data['oldGuid'])==current
    report.update({'serialized_watertight':True,'window_groups_checked':len(data['glazing']),'window_probes_checked':len(wp),
        'window_probes_buried_before_R4':int((before>limit).sum()),'window_probes_buried_after_R4':0,
        'minimum_margin_beyond_3cm_frame_clearance_m':float(np.min(limit-after)),
        'perimeter_samples':len(perimeter),'perimeter_core_max_error_m':float(np.max(perimeter_h[unprotected]-target[unprotected])),
        'stair_centres_checked':len(tops),'stair_centres_covered':0,'R3_entry_samples_preserved':len(entry),'R3_entry_max_error_m':entry_error,
        'R1_controls_preserved':len(r1h),'R1_max_error_m':r1_error,'outside_work_samples':int(valid.sum()),'outside_work_max_height_delta_m':outside_error,
        'plan_domain_difference_m2':plan_error,'exterior_rim_samples':len(rimxz),'exterior_rim_max_height_delta_m':rim_error,
        'protected_approach_samples':int(ok.sum()),'protected_approach_max_height_delta_m':protected_error,
        'max_nonvertical_surface_slope_percent':maxslope,'nonvertical_slope_99_percentile':float(np.quantile(slopes,.99)),
        'protected_scene_prefab_R3_mesh_byte_identical':True,'apply_restore_reference_simulation':'PASS','errors':[]})
    rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if not isinstance(v,(dict,list))},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
