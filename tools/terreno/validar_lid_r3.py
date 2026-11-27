"""Validate serialized R3 terrain and preserve the published scene/building."""
from pathlib import Path
import sys,json,re,subprocess
import numpy as np
import trimesh
from shapely.geometry import Polygon,box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lid'))
from unity_text import read_mesh,asset_guids,UnityText,ref
from construir_lid_r3 import geometry_hash,field,masks,ROOT_Y,RX,RZ,WALLS,STAIR_WIDTH,CLEAR

def ray_heights(mesh,xz):
    xz=np.asarray(xz);hits,idx,_=mesh.ray.intersects_location(np.c_[xz[:,0],np.full(len(xz),10.),xz[:,1]],np.tile([0,-1,0],(len(xz),1)),multiple_hits=True)
    h=np.full(len(xz),-np.inf)
    if len(hits):np.maximum.at(h,idx,hits[:,1])
    return h

def main():
    data=json.loads((ROOT/'Assets/UPCH/LIDTerrenoR3/Datos/Aplicacion_LID_R3.json').read_text())
    path=ROOT/'docs/lid/Validacion_Terreno_R3.json';report=json.loads(path.read_text())
    g=asset_guids(ROOT/'Assets');old=read_mesh(g[data['oldGuid']]);new=read_mesh(g[data['newGuid']])
    assert geometry_hash(old)==data['oldHash'] and geometry_hash(new)==data['newHash']
    matrix=np.array(data['worldMatrix']).reshape(4,4);old.apply_transform(matrix);new.apply_transform(matrix)
    new.merge_vertices();assert new.is_watertight and new.volume>0
    samples=np.array([[p['x'],p['z']] for p in data['samples']]);expected=np.array([p['y'] for p in data['samples']])
    h=ray_heights(new,samples);assert np.isfinite(h).all()
    error=float(np.max(abs(h-expected)));assert error<.001,error
    stair_xz=np.array([[p['x'],p['z']] for p in data['stairs']]);walk=np.array([p['y'] for p in data['stairs']]);ground=ray_heights(new,stair_xz)
    assert len(walk)==38 and np.all(ground<walk-.02)
    # Dense samples outside both local work regions, including every R1 control.
    r1=json.loads((ROOT/'Assets/UPCH/TerrenoCampusR1/Datos/Aplicacion_Terreno_R1.json').read_text())
    r1xz=np.array([[p['x'],p['z']] for p in r1['samplesWorld']]);r1exp=np.array([p['y'] for p in r1['samplesWorld']])
    r1h=ray_heights(new,r1xz);assert np.max(abs(r1h-r1exp))<.001
    grid=np.array([(x,z) for x in np.linspace(-60,150,25) for z in np.linspace(0,150,23)])
    from shapely import contains_xy
    outside=~contains_xy(unary_union(masks()).buffer(.001),grid[:,0],grid[:,1]);grid=grid[outside]
    a,b=ray_heights(old,grid),ray_heights(new,grid);assert np.array_equal(np.isfinite(a),np.isfinite(b))
    good=np.isfinite(a);maxoutside=float(np.max(abs(a[good]-b[good])));assert maxoutside<.001
    # Both slabs keep their domains open in the terrain; no coplanar cover.
    for side,w,s in WALLS:
        mid=np.array([[RX-4.0,w+s*.65]])
        assert not np.isfinite(ray_heights(new,mid)[0])
        h=ray_heights(new,np.array([[RX-4.0,w+s*(STAIR_WIDTH+.75)]]))[0]
        assert abs(h-ROOT_Y)<.001
    prefab=UnityText(ROOT/'Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab')
    lower=[]
    for k,b in prefab.docs.values():
        if k!=33:continue
        go=ref(b,'m_GameObject')
        if prefab.names[go] not in ['LID_15654_Oeste_Llegada','LID_15714_Este_Llegada']:continue
        slab=read_mesh(g[re.search(r'guid: ([a-f0-9]{32})',b)[1]])
        slab.apply_transform(prefab.world(prefab.go_transforms[go]));v=slab.vertices.copy()
        slab.vertices=np.c_[RX+v[:,2],ROOT_Y+v[:,1],RZ-v[:,0]];slab.faces=slab.faces[:,[0,2,1]]
        lower.append(slab)
    assert len(lower)==2
    entries=np.array([[p['x'],p['z']] for p in data['entrySamples']]);expect_entry=np.array([p['y'] for p in data['entrySamples']])
    eh=ray_heights(trimesh.util.concatenate([new,*lower]),entries)
    assert len(entries)==74 and np.isfinite(eh).all() and np.max(abs(eh-expect_entry))<.001
    topmask=new.face_normals[:,1]>1e-8
    c=new.triangles_center[topmask];normals=new.face_normals[topmask]
    local=contains_xy(unary_union(masks()).buffer(.001),c[:,0],c[:,2])
    slopes=100*np.linalg.norm(normals[local][:,[0,2]],axis=1)/abs(normals[local,1])
    maxslope=float(slopes.max());assert maxslope<42,maxslope
    # Geometric plan grid is at 0.1 mm; horizontal boundary tolerance is 1 mm.
    def footprint(m):
        f=m.faces[m.face_normals[:,1]>.4]
        return unary_union([Polygon(t[:,[0,2]]) for t in m.vertices[f]])
    op,np_=footprint(old),footprint(new);work=unary_union(masks())
    outside_area=float(op.symmetric_difference(np_).difference(work.buffer(.001)).area)
    assert outside_area<.05,outside_area
    # Keep the site's exterior rim at its old elevation, including the more
    # constrained western side. Probe just inside the serialized boundary.
    rim=op.buffer(-.01).exterior
    rimxz=np.array([rim.interpolate(t,normalized=True).coords[0] for t in np.linspace(0,1,500,endpoint=False)])
    rim_old,rim_new=ray_heights(old,rimxz),ray_heights(new,rimxz)
    assert np.isfinite(rim_old).all() and np.isfinite(rim_new).all()
    rim_error=float(np.max(abs(rim_old-rim_new)));assert rim_error<.001
    protected=['Assets/UPCH/Scenes/Campus.unity','Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab',str(g[data['oldGuid']].relative_to(ROOT))]
    for protected_path in protected:
        baseline=subprocess.check_output(['git','show',data['sourceCommit']+':'+protected_path],cwd=ROOT)
        assert (ROOT/protected_path).read_bytes()==baseline
    scene=UnityText(ROOT/'Assets/UPCH/Scenes/Campus.unity');body=scene.docs[357576549][1]
    assert data['oldGuid'] in body
    # Only MeshFilter + MeshCollider references would change; restoring both
    # produces the original scene bytes. No scene is saved by this validator.
    changed=scene.text.replace(data['oldGuid'],data['newGuid'])
    assert changed.count(data['newGuid'])==2 and changed.replace(data['newGuid'],data['oldGuid'])==scene.text
    report.update({'serialized_watertight':True,'walkway_samples':len(samples),'walkway_max_height_error_m':error,
        'stair_samples':len(walk),'covered_stair_samples':0,'minimum_stair_top_to_ground_m':float(np.min(walk-ground)),
        'R1_controls_preserved':len(r1exp),'outside_work_samples':int(good.sum()),'outside_work_max_height_delta_m':maxoutside,
        'outside_work_plan_difference_m2':outside_area,'measured_max_combined_slope_percent':maxslope,
        'exterior_rim_samples':len(rimxz),'exterior_rim_max_height_delta_m':rim_error,
        'lower_slabs_uncovered':True,'protected_source_files_byte_identical':True,'apply_restore_reference_simulation':'PASS',
        'entry_samples_ground_or_original_landing':len(entries),'entry_max_height_error_m':float(np.max(abs(eh-expect_entry))),
        'errors':[]})
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['work_polygons','unchanged']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
