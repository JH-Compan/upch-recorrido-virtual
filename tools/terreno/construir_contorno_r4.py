"""R4: lower perimeter strip, with window and entrance constraints.

Extends the accepted R3 grading without editing the LID or its interiors.
All exterior levels/strip widths are explicitly provisional model choices.
"""
from pathlib import Path
import sys,re,json,hashlib
import numpy as np
import trimesh
from shapely.geometry import Polygon,LineString,Point,box,mapping
from shapely.ops import unary_union
from shapely import contains_xy,set_precision
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/lid'))
from unity_text import UnityText,asset_guids,read_mesh,write_mesh,ref
from construir_lid_r3 import constrained_surface,geometry_hash,RX,RZ,ROOT_Y
from validar_lid_r3 import ray_heights

A=ROOT/'Assets/UPCH/LIDContornoR4'
STRIP=.6
EXTENT=3.6
LEVEL=-.70 # NPT +0.50 in the existing LID datum; 0.12 m below NPT .62 frames.

def meta(path,folder=False):
    guid=hashlib.md5(('UPCH:LIDContornoR4:'+str(path.relative_to(A.parent))).encode()).hexdigest()
    text='fileFormatVersion: 2\nguid: '+guid+'\n'
    if folder:text+='folderAsset: yes\n'
    if path.suffix=='.asset':text+='NativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 4300000\n'
    path.with_suffix(path.suffix+'.meta').write_text(text);return guid

def geometries(geom):
    return list(getattr(geom,'geoms',[geom]))

def main():
    for p in [A,A/'Datos',A/'Mallas',A/'Editor']:
        p.mkdir(parents=True,exist_ok=True);meta(p,True)
    r3=json.loads((ROOT/'Assets/UPCH/LIDTerrenoR3/Datos/Aplicacion_LID_R3.json').read_text())
    guids=asset_guids(ROOT/'Assets');source=guids[r3['newGuid']]
    old=read_mesh(source);old_hash=geometry_hash(old)
    assert old_hash==r3['newHash'],'R3 has custom mesh edits; register them first.'
    matrix=np.array(r3['worldMatrix']).reshape(4,4);old.apply_transform(matrix)
    old.vertices[:,[0,2]]=np.round(old.vertices[:,[0,2]],4);old.merge_vertices()
    f=old.faces[old.face_normals[:,1]>.5]
    domain=set_precision(unary_union([Polygon(t[:,[0,2]]) for t in old.vertices[f]]),.0001)
    holes=[Polygon(r) for r in domain.interiors]
    building=[h for h in holes if h.covers(Point(RX,RZ))]
    assert len(building)==1
    building=building[0]
    outer=building.buffer(EXTENT,join_style=2)
    near=building.buffer(STRIP,join_style=2)
    work=outer.intersection(domain)
    # Preserve approaches to the existing entry plate and north connector,
    # plus the already modelled west entry bed footprint. No floor is moved.
    prefab=UnityText(ROOT/'Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab')
    existing={}
    names=['LID_16488_Aproximacion_Ingreso_Este','LID_16417_Conexion_Exterior_Norte','LID_16535_Jardin_Retranqueo_Oeste']
    for kind,body in prefab.docs.values():
        if kind!=33:continue
        go=ref(body,'m_GameObject');name=prefab.names[go]
        if name not in names:continue
        m=read_mesh(guids[re.search(r'guid: ([a-f0-9]{32})',body)[1]]);m.apply_transform(prefab.world(prefab.go_transforms[go]))
        q=m.vertices.copy();m.vertices=np.c_[RX+q[:,2],ROOT_Y+q[:,1],RZ-q[:,0]];existing[name]=m.bounds
    assert len(existing)==3
    entry=existing[names[0]];north=existing[names[1]];bed=existing[names[2]]
    protected=set_precision(unary_union([box(90.0,entry[0,2],entry[1,0],entry[1,2]),
                           box(north[0,0],north[0,2],136.0,north[1,2]),
                           box(bed[0,0],bed[0,2],bed[1,0],bed[1,2])]),.0001)
    lines=[]
    edges=np.unique(np.sort(np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1),axis=0)
    # Keep source R3 constraints outside the new strip and in its deep core.
    # Avoid dragging old skinny flat triangles into the new interpolation.
    for a,b in edges:
        edge=LineString(old.vertices[[a,b]][:,[0,2]])
        if max(old.vertices[a,1],old.vertices[b,1])<LEVEL-1e-5:lines.append(edge)
        else:lines.extend(g for g in geometries(edge.difference(outer)) if g.geom_type=='LineString')
    for poly in [outer,near,protected]:
        for g in geometries(poly):
            if g.geom_type=='Polygon':
                lines.append(LineString(g.exterior.coords))
                lines.extend(LineString(r.coords) for r in g.interiors)
    # Intermediate offsets regularise the interpolation mesh around setbacks.
    for d in [1.2,1.8,2.4,3.0]:lines.append(LineString(building.buffer(d,join_style=2).exterior.coords))
    print('R4 triangulating perimeter...',flush=True)
    tri=constrained_surface(domain,lines,work)
    v=np.asarray(tri['vertices']);faces=np.asarray(tri['triangles']);n=len(v)
    prior=ray_heights(old,v)
    missing=~np.isfinite(prior)
    if missing.any():
        # Round-off at a source boundary: retry within 0.1 mm toward an
        # already valid domain interior. No source void is filled by R4.
        from scipy.spatial import cKDTree
        vv=old.vertices[np.unique(f)]
        distance,index=cKDTree(vv[:,[0,2]]).query(v[missing]);assert distance.max()<.001
        prior[missing]=vv[index,1]
    inside=contains_xy(outer.buffer(-.0002),v[:,0],v[:,1])
    in_near=contains_xy(near.buffer(.0002),v[:,0],v[:,1])
    centroids=v[faces].mean(axis=1)
    high_faces=contains_xy(protected,centroids[:,0],centroids[:,1])
    low_faces=~high_faces
    used_low=np.zeros(n,dtype=bool);used_low[np.unique(faces[low_faces])]=True
    core=inside & in_near & used_low
    deep=prior<LEVEL-1e-5
    fixed=(~inside)|core|deep|(~used_low)
    heights=prior.copy();heights[core]=np.minimum(prior[core],LEVEL)
    # Linear-triangle finite-element energy handles narrow triangles at CAD
    # setbacks without turning them into arbitrary steep interpolation spikes.
    lf=faces[low_faces];q=v[lf]
    twice=(q[:,1,0]-q[:,0,0])*(q[:,2,1]-q[:,0,1])-(q[:,1,1]-q[:,0,1])*(q[:,2,0]-q[:,0,0])
    gradients=np.stack([np.c_[q[:,1,1]-q[:,2,1],q[:,2,0]-q[:,1,0]],
                        np.c_[q[:,2,1]-q[:,0,1],q[:,0,0]-q[:,2,0]],
                        np.c_[q[:,0,1]-q[:,1,1],q[:,1,0]-q[:,0,0]]],axis=1)/twice[:,None,None]
    stiffness=np.einsum('fik,fjk->fij',gradients,gradients)*(abs(twice)/2)[:,None,None]
    rows=np.repeat(lf,3,axis=1).ravel();cols=np.tile(lf,(1,3)).ravel()
    lap=coo_matrix((stiffness.ravel(),(rows,cols)),shape=(n,n)).tocsr()
    # Constrained harmonic interpolation: preserve or lower source R3. Nodes
    # that would rise above R3 become fixed obstacles on the next iteration.
    for iteration in range(50):
        free=~fixed
        heights[free]=spsolve(lap[free][:,free],-lap[free][:,fixed]@heights[fixed])
        high=free & (heights>prior+1e-8)
        low=free & (heights<np.minimum(prior,LEVEL)-1e-8)
        if not high.any() and not low.any():break
        fixed[high]=True;heights[high]=prior[high]
        fixed[low]=True;heights[low]=np.minimum(prior[low],LEVEL)
    else:raise RuntimeError('R4 constrained interpolation did not converge')
    assert np.max(heights-prior)<1e-7 and np.min(heights)>-1.201
    heights=np.round(heights,6);prior=np.round(prior,6)
    bottom=np.minimum(heights,prior)-.16
    # Close the soil at the building boundary down past its existing basement
    # floor, rather than exposing the underside of a thin floating pavement.
    from shapely import distance,points
    at_building=distance(points(v),building.boundary)<.0002
    bottom[at_building]=np.minimum(bottom[at_building],ROOT_Y-.16)
    vv=list(np.vstack([np.c_[v[:,0],bottom,v[:,1]],np.c_[v[:,0],heights,v[:,1]],np.c_[v[:,0],prior,v[:,1]]]))
    ff=[faces,faces[low_faces][:,[0,2,1]]+n,faces[high_faces][:,[0,2,1]]+2*n]
    edge_faces={}
    for fi,face in enumerate(faces):
        for a,b in [face[[0,1]],face[[1,2]],face[[2,0]]]:edge_faces.setdefault(tuple(sorted([a,b])),[]).append(fi)
    step_segments=0;max_step=0.
    for (a,b),adj in edge_faces.items():
        if len(adj)==1:
            top_offset=2*n if high_faces[adj[0]] else n
            split_a=top_offset==2*n and used_low[a] and prior[a]-heights[a]>1e-7
            split_b=top_offset==2*n and used_low[b] and prior[b]-heights[b]>1e-7
            if split_a or split_b:
                # Split the tall boundary side at the lower adjoining top.
                # Otherwise a collinear T-junction remains at a step endpoint.
                poly=[a,b]+([b+n] if split_b else [])+[b+top_offset,a+top_offset]+([a+n] if split_a else [])
                center=len(vv);vv.append(np.mean([vv[i] for i in poly],axis=0))
                ff.append(np.array([[poly[i],poly[(i+1)%len(poly)],center] for i in range(len(poly))]))
            else:ff.append(np.array([[a,b,b+top_offset],[a,b+top_offset,a+top_offset]]))
        elif high_faces[adj[0]]!=high_faces[adj[1]]:
            # The already raised approaches remain at R3 elevation. The
            # difference is a closed vertical soil face, never a fake ramp.
            ff.append(np.array([[a+n,b+n,b+2*n],[a+n,b+2*n,a+2*n]]))
            max_step=max(max_step,float(max(prior[a]-heights[a],prior[b]-heights[b])))
            if max(prior[a]-heights[a],prior[b]-heights[b])>.005:step_segments+=1
    mesh=trimesh.Trimesh(np.asarray(vv),np.vstack(ff),process=False)
    mesh.merge_vertices(digits_vertex=7);mesh.update_faces(mesh.nondegenerate_faces(height=1e-10));mesh.remove_unreferenced_vertices();mesh.fix_normals(multibody=True)
    assert mesh.is_watertight and mesh.volume>0
    mesh.apply_transform(np.linalg.inv(matrix))
    dest=A/'Mallas/Site_LID_Contorno_R4.asset';write_mesh(dest,mesh,source,'Site_LID_Contorno_R4');new_guid=meta(dest)
    written=read_mesh(dest);written.merge_vertices();assert written.is_watertight and written.volume>0
    world=written.copy();world.apply_transform(matrix)
    windows=[];glazing=[]
    for kind,body in prefab.docs.values():
        if kind!=33:continue
        go=ref(body,'m_GameObject');name=prefab.names[go];tid=prefab.go_transforms[go]
        if '/Sotano/Ventanas/' not in prefab.path_for(tid) or '_Vidrio_' not in name:continue
        m=read_mesh(guids[re.search(r'guid: ([a-f0-9]{32})',body)[1]]);m.apply_transform(prefab.world(tid))
        q=m.vertices.copy();m.vertices=np.c_[RX+q[:,2],ROOT_Y+q[:,1],RZ-q[:,0]]
        lo,hi=m.bounds;span=hi-lo;normal=0 if span[0]<span[2] else 2;along=2 if normal==0 else 0
        center=(lo+hi)/2; probes=[];choices=[]
        for sign in [-1,1]:
            for offset in [.18,.3,.45,.65,.85,1.1]:
                pp=[]
                for t in [.1,.5,.9]:
                    pt=center.copy();pt[normal]+=sign*offset;pt[along]=lo[along]+t*span[along]
                    pp.append(pt[[0,2]])
                if all(domain.buffer(-.0001).covers(Point(xz)) for xz in pp):
                    choices.append((offset,pp));break
        if choices:probes=min(choices,key=lambda p:p[0])[1]
        if not probes:continue # Interior glazing or an existing covered patio.
        frame_y=float(lo[1]-.04)
        glazing.append({'name':name,'frameBaseY':frame_y,'worldBounds':m.bounds.tolist()})
        for x,z in probes:windows.append({'name':name,'x':float(x),'z':float(z),'y':frame_y-.03})
    # Mesh expectations are taken from the written geometry, not a formula.
    samplexz=np.array([[p['x'],p['z']] for p in r3['samples']])
    sampleh=ray_heights(world,samplexz);assert np.isfinite(sampleh).all()
    perimeter=building.buffer(.2,join_style=2).exterior
    perimeter_xz=np.array([perimeter.interpolate(t,normalized=True).coords[0] for t in np.linspace(0,1,400,endpoint=False)])
    keep_points=np.array([domain.buffer(-.0002).covers(Point(p)) and protected.boundary.distance(Point(p))>.03 for p in perimeter_xz])
    perimeter_xz=perimeter_xz[keep_points]
    perimeter_y=ray_heights(world,perimeter_xz);assert np.isfinite(perimeter_y).all()
    data={k:r3[k] for k in ['worldMatrix','rootPosition','stairs','entrySamples']}
    data.update({'revision':'LID_Contorno_R4','oldGuid':r3['newGuid'],'newGuid':new_guid,
                 'oldHash':old_hash,'newHash':geometry_hash(read_mesh(dest)),
                 'samples':[{'x':float(x),'y':float(y),'z':float(z)} for (x,z),y in zip(samplexz,sampleh)],
                 'perimeterSamples':[{'x':float(x),'y':float(y),'z':float(z)} for (x,z),y in zip(perimeter_xz,perimeter_y)],
                 'windows':windows,'glazing':glazing,
                 'limits':'Franja y niveles provisionales. Se conservan escaleras y accesos existentes; no es altimetría levantada.'})
    dp=A/'Datos/Aplicacion_Contorno_R4.json';dp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');meta(dp)
    report={'revision':data['revision'],'base':'ba4dc4cd + LID Terreno R3 package SHA256 3260f7ea2589feaae957a8772ad149295f255880e8ba79d53cb38986e829b468',
            'near_strip_m':STRIP,'normal_strip_level_y':LEVEL,'model_npt_of_normal_strip':LEVEL-ROOT_Y,
            'work_polygon':mapping(outer),'core_polygon':mapping(near),'protected_approaches':mapping(protected),
            'transition_width_m':3,'exterior_window_groups':len(glazing),'window_probes':len(windows),
            'raised_approach_closed_step_segments':step_segments,'maximum_closed_step_height_m':max_step,
            'soil_side_faces_at_building_extend_to_y':ROOT_Y-.16,
            'protected_existing_objects':names,
            'source_building_hole':mapping(building),'faces':len(written.faces),'watertight':bool(written.is_watertight),
            'interpolation_iterations':iteration+1,'native_Unity_Play':'NOT_RUN','CSharpCompilation':'NOT_RUN',
            'exterior_levels_surveyed':False,'building_and_interiors_modified':False}
    rp=ROOT/'docs/lid/Validacion_Contorno_R4.json';rp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:x for k,x in report.items() if not k.endswith('polygon') and k not in ['source_building_hole','protected_approaches']},indent=2),flush=True)

if __name__=='__main__':main()
