"""R3: reversible local grading to the two LID lower landings.

The exterior profile is a reviewable adaptation, not surveyed CAD altimetry.
Does not edit the scene, prefab, existing assets, stairs or materials.
"""
from pathlib import Path
import sys, re, json, hashlib
import numpy as np
import trimesh
import triangle
from shapely.geometry import Polygon, LineString, box, mapping
from shapely.ops import unary_union
from shapely import set_precision
from scipy.interpolate import LinearNDInterpolator

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/lid'))
from unity_text import UnityText, ref, asset_guids, read_mesh, write_mesh
from construir_parque_r1 import geometry_hash

A = ROOT/'Assets/UPCH/LIDTerrenoR3'
RX, RZ, ROOT_Y = 113.91901, 108.57089, -1.2
# Work profiles: 15 m on each longitudinal approach, 1.5 m clear outer
# landing strip. Transverse runs differ with available space. R3 hypotheses.
U0, U1, U2, U3 = 93.91901, 108.91901, 110.81901, 125.81901
WALLS = [('Oeste', RZ+32.55, 1), ('Este', RZ-32.55, -1)]
STAIR_WIDTH, CLEAR = 1.32893, 1.5
BANKS = {'Oeste':3.0, 'Este':8.0}

def meta(path, folder=False):
    guid = hashlib.md5(('UPCH:LIDTerrenoR3:'+str(path.relative_to(A.parent))).encode()).hexdigest()
    content = 'fileFormatVersion: 2\nguid: '+guid+'\n'
    if folder: content += 'folderAsset: yes\n'
    if path.suffix == '.asset':
        content += 'NativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 4300000\n'
    path.with_suffix(path.suffix+'.meta').write_text(content)
    return guid

def field(xz):
    u = xz[:,0]
    values = np.zeros(len(xz))
    for side, wall, sign in WALLS:
        e = sign*(xz[:,1]-wall)
        # Planar facets, with explicit ridge constraints below. An inward
        # taper also closes the approach around the building's front corner.
        bank=BANKS[side]
        depth=np.maximum(0,np.minimum.reduce([np.full(len(u),1.2),
             .08*(u-U0),.08*(U3-u),(1.2/bank)*(STAIR_WIDTH+CLEAR+bank-e),.15*(e+8)]))
        values=np.minimum(values,-depth)
    return values

def masks():
    return [box(U0, min(w-s*8,w+s*(STAIR_WIDTH+CLEAR+BANKS[side])), U3,
                max(w-s*8,w+s*(STAIR_WIDTH+CLEAR+BANKS[side]))) for side,w,s in WALLS]

def constrained_surface(domain, lines, work):
    # Source triangles already define R1's relief. Do not apply minimum-angle
    # refinement to their tiny CAD boundary segments: it can grow unbounded.
    from shapely.ops import polygonize
    network=unary_union([LineString(domain.exterior.coords),
                        *[LineString(r.coords) for r in domain.interiors],
                        *[l.intersection(domain) for l in lines]])
    vertices=[];segments=[];lookup={}
    for line in getattr(network,'geoms',[network]):
        if line.geom_type!='LineString':continue
        for a,b in zip(list(line.coords),list(line.coords)[1:]):
            pair=[]
            for xy in [a,b]:
                key=tuple(np.round(xy,7))
                if key not in lookup:lookup[key]=len(vertices);vertices.append(key)
                pair.append(lookup[key])
            if pair[0]!=pair[1]:segments.append(pair)
    regions=[]
    for region in polygonize(network):
        p=region.representative_point()
        if domain.covers(p):regions.append([p.x,p.y,0,.65 if work.covers(p) else 500])
    data={'vertices':vertices,'segments':segments,'regions':regions}
    if domain.interiors:data['holes']=[Polygon(r).representative_point().coords[0] for r in domain.interiors]
    return triangle.triangulate(data,'pYa')

def main():
    print('Reading published terrain...', flush=True)
    for d in [A,A/'Datos',A/'Mallas',A/'Editor']:
        d.mkdir(exist_ok=True,parents=True); meta(d,True)
    scene=UnityText(ROOT/'Assets/UPCH/Scenes/Campus.unity'); guids=asset_guids(ROOT/'Assets')
    body=scene.docs[357576549][1]; old_guid=re.search(r'guid: ([a-f0-9]{32})',body)[1]
    assert old_guid=='950d9d19d25c1e6a2904da696a7f0328', 'Apply to the published R1 terrain only'
    source=guids[old_guid]; original=read_mesh(source); old_hash=geometry_hash(original)
    matrix=scene.world(357576545); original.apply_transform(matrix)
    # One 0.1 mm plan grid prevents microscopic disconnected strips where
    # serialized float32 terrain edges meet double-precision CAD coordinates.
    original.vertices[:,[0,2]]=np.round(original.vertices[:,[0,2]],4)
    original.merge_vertices()
    faces=original.faces[original.face_normals[:,1]>.5]
    top=original.vertices[faces]
    domain=set_precision(unary_union([Polygon(t[:,[0,2]]) for t in top]),.0001)
    print('Surface extracted:',len(faces),'triangles',flush=True)
    assert domain.geom_type=='Polygon'
    fill=[]; landings=[]
    for side,w,s in WALLS:
        zlo,zhi=sorted([w,w+s*STAIR_WIDTH])
        fill.append(set_precision(box(RX-4.89876,zlo,RX+4.9036,zhi),.0001))
        endpoint=RX-(3.11902 if side=='Oeste' else 3.12291)
        landings.append(set_precision(box(RX-4.89876,zlo,endpoint,zhi),.0001))
    # Keep the existing arrival slabs visible and unchanged (no coplanar cap).
    addition=unary_union(fill).difference(unary_union(landings)).difference(domain)
    new_domain=domain.union(addition)
    assert new_domain.geom_type=='Polygon' and new_domain.is_valid
    work=unary_union(masks())
    edges=np.unique(np.sort(np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0)
    extra=[LineString(original.vertices[e][:,[0,2]]) for e in edges]
    for mask in masks():
        extra.append(LineString(mask.exterior.coords))
        xmin,zmin,xmax,zmax=mask.bounds
        for x in [U0,U1,U2,U3]: extra.append(LineString([(x,zmin),(x,zmax)]))
    for side,w,s in WALLS:
        bank=BANKS[side];outer_slope=1.2/bank;emax=STAIR_WIDTH+CLEAR+bank
        for e in [0,STAIR_WIDTH+CLEAR,(outer_slope*emax-.15*8)/(outer_slope+.15)]:
            extra.append(LineString([(U0,w+s*e),(U3,w+s*e)]))
        extra.append(LineString([((U0+U3)/2,w-s*8),((U0+U3)/2,w+s*emax)]))
        # All equal-depth lines between longitudinal and transverse planes.
        for fn in [lambda u:emax-(.08/outer_slope)*(u-U0),lambda u:emax-(.08/outer_slope)*(U3-u),
                   lambda u:-8+(.08/.15)*(u-U0),lambda u:-8+(.08/.15)*(U3-u)]:
            extra.append(LineString([(U0,w+s*fn(U0)),(U3,w+s*fn(U3))]))
    print('Triangulating',len(extra),'constraints...',flush=True)
    tri=constrained_surface(new_domain,extra,work)
    print('Triangulated:',len(tri['triangles']),flush=True)
    v=np.asarray(tri['vertices']); f=np.asarray(tri['triangles']); n=len(v)
    heights=np.full(n,np.nan)
    hits,rays,_=original.ray.intersects_location(np.c_[v[:,0],np.full(n,10),v[:,1]],np.tile([0,-1,0],(n,1)),multiple_hits=True)
    # Surface rays may see the lower surface too: keep the highest hit.
    h=np.full(n,-np.inf);np.maximum.at(h,rays,hits[:,1]);heights=h
    missing=~np.isfinite(heights)
    if missing.any():
        # Added soil occupies the old exterior stair void, where R1 has no hit.
        interpolator=LinearNDInterpolator(original.vertices[np.unique(faces)][:,[0,2]], original.vertices[np.unique(faces),1])
        heights[missing]=interpolator(v[missing])
    assert np.all(np.isfinite(heights))
    delta=field(v)
    # This sector is flat in the published R1. Verify instead of assuming.
    assert np.max(abs(heights[np.abs(delta)>1e-5]))<1e-5
    heights+=delta
    vertices=np.vstack([np.c_[v[:,0],heights-.16,v[:,1]],np.c_[v[:,0],heights,v[:,1]]])
    all_faces=[f,f[:,[0,2,1]]+n]
    es=np.sort(np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1)
    unique,count=np.unique(es,axis=0,return_counts=True)
    for a,b in unique[count==1]:all_faces.append(np.array([[a,b,b+n],[a,b+n,a+n]]))
    mesh=trimesh.Trimesh(vertices,np.vstack(all_faces),process=False);mesh.fix_normals(multibody=True)
    assert mesh.is_watertight and mesh.volume>0
    mesh.apply_transform(np.linalg.inv(matrix))
    destination=A/'Mallas/Site_LID_Descansos_R3.asset'
    write_mesh(destination,mesh,source,'Site_LID_Descansos_R3');new_guid=meta(destination)
    serialized=read_mesh(destination);serialized.merge_vertices();assert serialized.is_watertight and serialized.volume>0
    prefab=UnityText(ROOT/'Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab')
    stair_checks=[]
    for k,b in prefab.docs.values():
        if k!=33:continue
        go=ref(b,'m_GameObject');name=prefab.names[go]
        if not any(name.startswith('LID_'+str(i)+'_') for i in list(range(15606,15615))+list(range(15630,15640))+list(range(15666,15675))+list(range(15690,15700))):continue
        m=read_mesh(guids[re.search(r'guid: ([a-f0-9]{32})',b)[1]]);m.apply_transform(prefab.world(prefab.go_transforms[go]));center=m.bounds.mean(0)
        world=[RX+center[2], ROOT_Y+m.bounds[1,1], RZ-center[0]]
        stair_checks.append({'name':name,'x':world[0],'y':world[1],'z':world[2]})
    samples=[]
    for side,w,s in WALLS:
        for x in np.linspace(U0+.1,U3-.1,81):
            z=w+s*(STAIR_WIDTH+.75);y=float(field(np.array([[x,z]]))[0]);samples.append({'x':float(x),'y':y,'z':float(z)})
    entries=[]
    for side,w,s in WALLS:
        # Turn before the existing outer guard rail, then enter the original
        # lower slab through its open end. No new steps or railing gaps.
        corner=RX-5.45
        points=[(corner,w+s*e) for e in np.linspace(STAIR_WIDTH+.75,.65,17)]
        points += [(x,w+s*.65) for x in np.linspace(corner,RX-4.0,21)[1:]]
        for x,z in points:
            entries.append({'x':float(x),'y':float(field(np.array([[x,z]]))[0]),'z':float(z)})
    data={'revision':'LID_Terreno_R3','sourceCommit':'ba4dc4cdbaf668856bf9a00fd9869dea78ed3ff9',
          'oldGuid':old_guid,'newGuid':new_guid,'oldHash':old_hash,'newHash':geometry_hash(read_mesh(destination)),
          'worldMatrix':matrix.flatten().tolist(),'rootPosition':[RX,ROOT_Y,RZ],
          'samples':samples,'stairs':stair_checks,'entrySamples':entries,
          'limits':'Perfiles provisionales: 8 % longitudinal; banco oeste 40 %, este 15 %, fuera de la franja exterior de 1,50 m. No son cotas levantadas ni certificación de accesibilidad.'}
    path=A/'Datos/Aplicacion_LID_R3.json';path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');meta(path)
    report={'revision':data['revision'],'base_commit':data['sourceCommit'],'ground_only':True,
            'unchanged':['Campus.unity','Edificio_LID.prefab','Existing terrain meshes','Stairs, doors, windows, materials and manual overrides'],
            'added_plan_area_m2':float(new_domain.area-domain.area),'work_polygons':[mapping(m) for m in masks()],
            'lower_landing_y':-1.2,'longitudinal_runs_m':[15,15],'longitudinal_slope_percent':8,
            'outer_clear_width_m':1.5,'transverse_bank_runs_m':BANKS,'max_transverse_slope_percent':{'Oeste':40,'Este':15},
            'max_combined_analytic_slope_percent':40,'faces':len(serialized.faces),'watertight':bool(serialized.is_watertight),
            'native_Unity_Play':'NOT_RUN','exterior_datum_surveyed':False}
    (ROOT/'docs/lid/Validacion_Terreno_R3.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
