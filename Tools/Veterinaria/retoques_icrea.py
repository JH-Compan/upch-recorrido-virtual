"""Acabado local de fachada y paso inclinado CAD, sin cambiar sus cotas."""
import numpy as np
import trimesh
import manifold3d as mf
from shapely.geometry import Polygon
from shapely.ops import unary_union
from fachada_campus import part_solid, replace_part


def ramp_clearance(b, data):
    review = data['reviewedArchitecture']['posteriorRamp']
    points = np.asarray(review['outline'], dtype=float)
    start, end = (points[1]+points[-2])/2, (points[0]+points[-1])/2
    direction = end-start
    direction /= np.linalg.norm(direction)
    profile = Polygon(points).buffer(.015, join_style='mitre')
    mesh = b.section(profile, 1.85)
    for v in mesh.vertices:
        v[1] += review['upperNPTEstimated']+review['slope']*((v[[0,2]]-end)@direction)+.02
    tool = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),
                               np.asarray(mesh.faces,dtype=np.uint32)))
    retained, changed = [], []
    for p in b.PARTS:
        # A-01 projected beams were extruded below the A-02 ramp opening.
        # Upper beams remain at the real overhead elevation.
        candidate = p['role']=='beam' or p['name']=='Cierre_zocalo_bajo_celosia_lateral'
        if p['level']!=0 or not candidate or not b.part_footprint(p).intersects(profile):
            retained.append(p)
            continue
        original = part_solid(b,p)
        body = original-tool
        if abs(body.volume()-original.volume())<1e-8:
            retained.append(p)
            continue
        changed.append(p['id'])
        if not body.is_empty():
            replace_part(b,p,body)
            p['note'] += ' R11: proyeccion recortada en el espacio libre sobre la rampa CAD.'
            retained.append(p)
    b.PARTS[:] = retained
    b.EVIDENCE.append({'element':'Paso inclinado posterior', 'revision':'R11_Retoques_Icrea',
                       'confirmed':'Huella CAD A-PISO 45E57 y pendiente 8%; usuario confirma paso inclinado',
                       'changedObstructions':changed,
                       'preserved':'Superficie continua, pendiente y anclaje vertical R10; vigas superiores',
                       'estimated':'Cota superior -1.17; conexion del extremo inferior con sotano pendiente de corte',
                       'clearanceHeight':1.85,'status':'Validar apoyo y altura libre en las tres franjas de paso'})


def align_faces(b, data):
    review = data['reviewedArchitecture']['lateralIcrea']['finishReview']
    plane_x, plane_sum, tolerance = review['planeX'], review['diagonalSum'], review['maxSnap']
    result, changed, removed, max_move = [], [], [], 0.
    slab_joints = {i:[] for i in range(1,5)}
    for p in b.PARTS:
        if p['hidden'] or p['material']!='wall' or p['role']=='door' or p['level']==4:
            result.append(p)
            continue
        v = b.materialize_vertices(p)
        if v[:,1].max()<=.001:
            result.append(p)
            continue
        original_footprint = b.part_footprint(p)
        out = v.copy()
        region=(v[:,0]>16.2)&(v[:,0]<22.05)&(v[:,2]>-10.2)&(v[:,2]<-5.7)
        xs=region&(abs(v[:,0]-plane_x)<tolerance)
        if np.any(xs):
            source=float(v[xs,0].max())
            # A monotone local deformation keeps the wall thickness and its
            # closed topology; snapping both faces would collapse narrow returns.
            band=region&(v[:,0]>21.70)
            out[band,0]+=(plane_x-source)*np.clip((v[band,0]-21.70)/(source-21.70),0,1)
        sums=v[:,0]+v[:,2]
        ds=region&(abs(sums-plane_sum)<tolerance)
        if np.any(ds):
            source=float(sums[ds].max())
            band=region&(sums>11.25)&(sums<=source+.000001)&(~xs)
            delta=(plane_sum-source)*np.clip((sums[band]-11.25)/(source-11.25),0,1)/2
            out[band,0]+=delta
            out[band,2]+=delta
        move=np.linalg.norm(out-v,axis=1)
        if move.max()<1e-7:
            result.append(p)
            continue
        mesh=trimesh.Trimesh(vertices=out,faces=np.arange(len(out)).reshape(-1,3),process=True)
        area=np.linalg.norm(np.cross(mesh.triangles[:,1]-mesh.triangles[:,0],
                                     mesh.triangles[:,2]-mesh.triangles[:,0]),axis=1)
        mesh.update_faces(area>1e-12)
        mesh.remove_unreferenced_vertices()
        if not len(mesh.faces) or abs(mesh.volume)<1e-8:
            removed.append(p['id'])
            continue
        mesh.fix_normals()
        body=mf.Manifold(mf.Mesh(np.asarray(mesh.vertices,dtype=np.float32),
                                 np.asarray(mesh.faces,dtype=np.uint32)))
        if body.status()!=mf.Error.NoError:
            raise ValueError('Revisar alineacion de fachada: '+p['id'])
        replace_part(b,p,body)
        p['note'] += ' R11: alineacion local del plano exterior compartido.'
        max_move=max(max_move,float(move.max()))
        changed.append(p['id'])
        result.append(p)
        bottom,top=out[:,1].min(),out[:,1].max()
        for level in slab_joints:
            if abs(bottom-b.NPT[level])<.00002 or abs(top-(b.NPT[level]-.24))<.00002:
                slab_joints[level].append(b.part_footprint(p).difference(original_footprint))
    b.PARTS[:]=result
    for level,profiles in slab_joints.items():
        if not profiles:
            continue
        patch=unary_union(profiles).difference(b.FLOORS[level])
        b.fixed_prism(patch,b.NPT[level]-.24,b.NPT[level],b.LEVEL_NAMES[level]+'/Retoques_Icrea',
                      'Ajuste_encuentro_losa_fachada','floor',True,level,
                      'Encuentro con el plano exterior repetido de escalera',
                      'Solo tira de ajuste del cerramiento; no rellena vanos de escalera.')
        b.FLOORS[level]=b.FLOORS[level].union(patch)
    b.resolve_solid_junctions(set(changed) | {p['id'] for p in b.PARTS if '/Retoques_Icrea' in p['group']})
    # Discard sub-square-centimetre strips left by float32 boolean joins.
    # They fall within the existing junction tolerance and otherwise create slivers.
    b.PARTS[:]=[p for p in b.PARTS if '/Retoques_Icrea' not in p['group'] or b.part_footprint(p).area>=.0001]
    b.EVIDENCE.append({'element':'Encuentros de fachada I-crea','revision':'R11_Retoques_Icrea',
                       'changedParts':changed,'removedCollapsedRecoveryFragments':removed,
                       'maxDisplacementMetres':max_move,
                       'source':'Plano exterior repetido de escalera A-02/A-03/A-04 y fotos',
                       'estimated':'Alineacion visual comun dentro de 25 mm; no nueva medicion de cotas',
                       'status':'Comprobar ausencia de salientes y continuidad del material'})
