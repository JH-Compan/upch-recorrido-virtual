"""R12: cierre local de la base I-crea sobre la geometria aceptada R11.

No reconstruye las otras fachadas: conserva sus registros y assets. La cota
del remate se relaciona con el dintel fotografiado; no es una medicion nueva.
"""
import copy
import json
import re
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh
from shapely import wkt
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from fachada_campus import as_mesh, part_solid, replace_part, solid


REVISION = 'R12_Cierre_Local_Icrea'


def clip_face(poly, height, sign):
    out = []
    for a, z in zip(poly, poly[1:]+poly[:1]):
        aa, zz = sign*(a[1]-height)>=-1e-10, sign*(z[1]-height)>=-1e-10
        if aa:
            out.append(a)
        if aa != zz:
            p = a+(z-a)*((height-a[1])/(z[1]-a[1]))
            p[1] = height
            out.append(p)
    return out


def finish(b, p, materials, head):
    """Split the colour boundary on the actual head plane, not face centres."""
    vertices = b.materialize_vertices(p).reshape(-1,3,3)
    slots = p.get('materialGuids', [p['materialGuid']])
    masks = p.get('triangleMaterials', [0]*len(vertices))
    out, colours = [], []
    for triangle, mask in zip(vertices, masks):
        faces = [list(triangle)]
        if triangle[:,1].min()<head-1e-7 and triangle[:,1].max()>head+1e-7:
            faces = [clip_face(list(triangle),head,s) for s in [-1,1]]
        for face in faces:
            for k in range(1,len(face)-1):
                tri = np.asarray([face[0],face[k],face[k+1]],dtype=np.float32).astype(float)
                normal = np.cross(tri[1]-tri[0],tri[2]-tri[0])
                if np.linalg.norm(normal)<1e-18:
                    continue
                normal /= np.linalg.norm(normal)
                centre = tri.mean(0)
                guid = slots[mask]
                # Exterior faces and their end returns; stairs retain white
                # on the interior side of the two diagonal enclosure walls.
                outer = (normal[0]>.30 or
                         abs(normal[1])>.9 or
                         (centre[0]>21.68 and normal[2]<-.3))
                local = 16.2<centre[0]<22.05 and -10.2<centre[2]<-2.30
                if local and outer:
                    guid = materials['grey'] if centre[1]<head+1e-7 else materials['concrete']
                elif local and p['id'] in ['H_1_Muros_0055','H_2_Lateral_Icrea_0001','H_3_Muros_0018']:
                    guid = materials['white']
                out.append(tri)
                colours.append(guid)
    vertices = np.array(out).reshape(-1,3)
    normals = np.cross(vertices[1::3]-vertices[::3],vertices[2::3]-vertices[::3])
    normals /= np.linalg.norm(normals,axis=1,keepdims=True)
    uv = []
    for tri,normal in zip(np.array(out),normals):
        axis = int(np.argmax(abs(normal)))
        uv.extend((tri[:,[0,2] if axis==1 else [2,1] if axis==0 else [0,1]]/3).flatten())
    lo,hi = b.y_range(p['role'],p['level'],p['bottom'],p['top'])
    vertices[:,1] = (vertices[:,1]-lo)/(hi-lo)
    palette = list(dict.fromkeys(colours))
    p.update(vertices=vertices.flatten().tolist(), normals=np.repeat(normals,3,axis=0).flatten().tolist(),
             uv=np.array(uv).tolist(),materialGuids=palette,
             triangleMaterials=[palette.index(g) for g in colours])


def build(b, args=None):
    base = b.BASE
    path = base/'Datos/Modelo_H.json'
    model = json.loads(path.read_text())
    if model['revision']==REVISION:
        print('R12 ya aplicada; se conserva el modelo local y no se reconstruye el resto.')
        return
    if model['revision']!='R11_Retoques_Icrea':
        raise ValueError('El cierre local R12 necesita la geometria R11 aceptada.')
    cad = json.loads((Path(__file__).parent/'Fuentes/CAD_H.json').read_text())
    config = cad['reviewedArchitecture']['lateralIcrea']['localClosure']
    b.NPT[:] = model['npt']
    b.PARAMS.update(model['parameters'])
    b.PARTS[:] = copy.deepcopy(model['items'])
    original = {p['id']:copy.deepcopy(p) for p in b.PARTS}
    current = {p['id']:p for p in b.PARTS}
    materials = {}
    for key,name in [('concrete','H_Hormigon_Beige'),('grey','H_Zocalo_Gris')]:
        materials[key] = re.search(r'^guid: (\w+)',(base/'Materiales'/(name+'.mat.meta')).read_text(),re.M)[1]
    materials['white'] = b.MATS['wall']
    head = config['capNPT']
    scope = box(*config['scopeBounds'])
    canonical = b.part_footprint(current['H_1_Muros_0055'])
    removed = set(config['removeItems'])
    b.PARTS[:] = [p for p in b.PARTS if p['id'] not in removed]
    touched = set()
    solids = {}
    expanded = {}

    def body(p):
        if p['id'] not in solids:
            solids[p['id']] = part_solid(b,p)
        return solids[p['id']]

    def avoid_existing(desired, profile, bottom, top, skip, margin=.0003):
        tools = []
        for p in b.PARTS:
            if p['id'] in skip or p['hidden'] or p['material'] not in ['wall','floor','metal']:
                continue
            v = b.materialize_vertices(p)
            if v[:,1].max()<=bottom+1e-7 or v[:,1].min()>=top-1e-7:
                continue
            if not b.part_footprint(p).intersects(profile):
                continue
            key = (p['id'],margin)
            if key not in expanded:
                offset = mf.Manifold.cube((2*margin,2*margin,2*margin),center=True)
                expanded[key] = body(p).minkowski_sum(offset)
            tools.append(expanded[key])
        return desired-mf.Manifold.batch_boolean(tools,mf.OpType.Add) if tools else desired

    for ident in config.get('projectedSlabItems',[]):
        p = original[ident]
        level = p['level']
        model['expectedFloorCoverage'][level] = wkt.loads(model['expectedFloorCoverage'][level]).difference(b.part_footprint(p)).wkt

    # Repeated rear enclosure: both ends now reach the existing returns.
    for ident in config['repeatWallItems']:
        p = current[ident]
        v = b.materialize_vertices(p)
        bottom,top = float(v[:,1].min()),float(v[:,1].max())
        desired = avoid_existing(solid(b,canonical,bottom,top),canonical,bottom,top,{ident})
        replace_part(b,p,desired.simplify(.00005))
        solids.pop(ident,None)
        p['note'] += ' R12: caras repetidas continuas hasta ambos retornos de la caja de escalera.'
        touched.add(ident)

    # Align only the second-storey long face with the accepted lower face.
    p = current['H_2_Muros_0016']
    vertices = b.materialize_vertices(p)
    sums = vertices[:,0]+vertices[:,2]
    outer,inner = config['frontOuterSum'],config['frontInnerSum']
    source = float(sums.min())
    band = sums<inner
    delta = (outer-source)*np.clip((inner-sums[band])/(inner-source),0,1)/2
    vertices[band,0] += delta
    vertices[band,2] += delta
    mesh = trimesh.Trimesh(vertices=vertices,faces=np.arange(len(vertices)).reshape(-1,3),process=True)
    mesh.fix_normals()
    desired = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),np.asarray(mesh.faces,dtype=np.uint32)))
    if desired.status()!=mf.Error.NoError:
        raise ValueError('La alineacion local no forma un volumen cerrado.')
    desired = avoid_existing(desired,b.part_footprint(p),float(vertices[:,1].min()),float(vertices[:,1].max()),{p['id']})
    replace_part(b,p,desired)
    solids.pop(p['id'],None)
    touched.add(p['id'])

    # The exterior triangular service base stops at the photographed door head.
    # It is outside the diagonal stair wall, not a fill across the stairwell.
    profile = Polygon(config['capOutline']).difference(canonical.buffer(.0002,join_style='mitre')).union(box(*config['guardBounds']))
    desired = avoid_existing(solid(b,profile,config['capBottom'],head),profile,config['capBottom'],head,set())
    b.add_mesh(as_mesh(desired),'02_Primer_Piso/Cierre_Icrea_R12','Base_y_remate_continuo_a_dintel',
               'wall',True,'fixed',1,0,1,'Foto de acceso: remate gris alineado con dintel; limites de caja CAD A-02',
               'Altura inferida por relacion fotografica; conserva peldaños y el vano de acceso.')
    podium = b.PARTS[-1]
    replace_part(b,podium,desired.simplify(.00005))
    solids[podium['id']] = desired
    podium['materialGuid'] = materials['grey']
    touched.add(podium['id'])

    # The adjacent hall stays at its original NPT. Close the projected cut,
    # not the actual stair opening, and retain the low exterior guard above it.
    deck = box(*config['hallDeckBounds'])
    desired = avoid_existing(solid(b,deck,-.24,0),deck,-.24,0,set())
    if not desired.is_empty():
        b.add_mesh(as_mesh(desired),'02_Primer_Piso/Cierre_Icrea_R12','Piso_hall_contiguo_sin_corte_triangular',
                   'floor',True,'fixed',1,0,1,'A-02: hall exterior entre retorno de escalera y fachada de laboratorio',
                   'NPT 0 conservado; no eleva el corredor al nivel del remate exterior.')
        replace_part(b,b.PARTS[-1],desired.simplify(.00005))
        solids[b.PARTS[-1]['id']] = desired
        b.PARTS[-1]['materialGuid'] = b.MATS['floor']
        touched.add(b.PARTS[-1]['id'])
    model['expectedFloorCoverage'][1] = wkt.loads(model['expectedFloorCoverage'][1]).union(deck).wkt

    # Support only the enclosure's small changed perimeter, not its free void.
    for level in [1,2,3,4]:
        profiles = []
        for p in b.PARTS:
            if p['id'] not in touched or p['material']!='wall' or p is podium:
                continue
            v = b.materialize_vertices(p)
            if abs(v[:,1].min()-b.NPT[level])<1e-5 or abs(v[:,1].max()-(b.NPT[level]-.24))<1e-5:
                profiles.append(b.part_footprint(p))
        if not profiles:
            continue
        old_floor = wkt.loads(model['expectedFloorCoverage'][level])
        missing = unary_union(profiles).difference(old_floor.buffer(.00025,join_style='mitre'))
        for polygon in b.polygons(missing):
            if polygon.area<.0001:
                continue
            desired = avoid_existing(solid(b,polygon,b.NPT[level]-.24,b.NPT[level]),polygon,b.NPT[level]-.24,b.NPT[level],set())
            if desired.is_empty():
                continue
            b.add_mesh(as_mesh(desired),b.LEVEL_NAMES[level]+'/Cierre_Icrea_R12','Encuentro_local_losa_cerramiento',
                       'floor',True,'fixed',level,0,1,'Retornos de cerramiento local A-02/A-03/A-04',
                       'Solo franja bajo el muro; conserva el hueco libre de escalera.')
            replace_part(b,b.PARTS[-1],desired.simplify(.00005))
            solids[b.PARTS[-1]['id']] = desired
            b.PARTS[-1]['materialGuid'] = materials['concrete']
            touched.add(b.PARTS[-1]['id'])
        model['expectedFloorCoverage'][level] = old_floor.union(unary_union(profiles)).wkt

    # Repair only the new local booleans before assigning material submeshes.
    frozen = [p for p in b.PARTS if p['id'] not in touched]
    b.PARTS[:] = [p for p in b.PARTS if p['id'] in touched]
    b.repair_float32_topology()
    touched.update(p['id'] for p in b.PARTS)
    b.PARTS[:] = frozen+b.PARTS
    current.update({p['id']:p for p in b.PARTS})

    for ident in config['finishItems']:
        p = current[ident]
        finish(b,p,materials,head)
        touched.add(ident)
    # The original base and slab fascia remain geometrically identical. Change
    # only faces wholly contained in this section, so the rest of each large
    # combined mesh keeps both its surface and its original material.
    for ident in config.get('baseFinishItems',[]):
        p = current[ident]
        tris = b.materialize_vertices(p).reshape(-1,3,3)
        slots = p.get('materialGuids',[p['materialGuid']])
        colours = [slots[k] for k in p.get('triangleMaterials',[0]*len(tris))]
        for k,tri in enumerate(tris):
            normal = np.cross(tri[1]-tri[0],tri[2]-tri[0])
            normal /= max(np.linalg.norm(normal),1e-18)
            inside = all(scope.buffer(.00001).covers(Point(v[[0,2]])) for v in tri)
            if inside and (p['material']=='wall' or '/Retoques_Icrea' in p['group'] or abs(normal[1])<.1 and normal[0]>.3):
                colours[k] = materials['grey']
        palette = list(dict.fromkeys(colours))
        p.update(materialGuids=palette,triangleMaterials=[palette.index(g) for g in colours])
        touched.add(ident)


    # Scope is enforced before writing any asset.
    for p in b.PARTS:
        if p['id'] not in touched and p!=original.get(p['id']):
            raise AssertionError('Cambio fuera de la lista local: '+p['id'])
        if p['id'] in touched and p['id'] not in original:
            if b.part_footprint(p).difference(scope.buffer(.001)).area>1e-6:
                raise AssertionError('Complemento fuera de esta seccion: '+p['id'])
    for ident in touched:
        p = next(p for p in b.PARTS if p['id']==ident)
        b.write_mesh_asset(base/'Generado/Mallas'/(ident+'.asset'),p)
    for ident in removed:
        asset = base/'Generado/Mallas'/(ident+'.asset')
        asset.unlink(missing_ok=True)
        asset.with_name(asset.name+'.meta').unlink(missing_ok=True)
    b.create_prefab(b.PARTS)
    model.update(items=b.PARTS,revision=REVISION)
    path.write_text(json.dumps(model,ensure_ascii=False,separators=(',',':')))
    evidence = {'revision':REVISION,'scopeBounds':config['scopeBounds'],'changedItems':sorted(touched),
                'removedItems':sorted(removed),'capNPT':head,'capHeightAboveGrade':head+1.17,
                'estimated':'Cota del remate ligada al dintel 2.15 m estimado; foto, no corte acotado.',
                'preserved':'Resto de registros del modelo, NPT, puertas, peldaños, rampa 8%, escena y terreno',
                'UnityPlay':'NOT_RUN'}
    import collections
    summary_path = base/'Documentacion/Construccion.json'
    summary = json.loads(summary_path.read_text())
    summary.update(parts=len(b.PARTS),byGroup=dict(collections.Counter(p['group'] for p in b.PARTS)))
    summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    report = base/'Documentacion/Cierre_Local_Icrea_R12.json'
    report.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    b.meta(report)
    print(json.dumps(evidence,ensure_ascii=False,indent=2))


if __name__=='__main__':
    import construir
    build(construir)
