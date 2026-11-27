"""Reparacion local del acceso oriental, cotejado con plantas y fotos.

La cota de calle -1.17 es documental. La relacion entre esa calle y el
descanso lateral es una interpretacion fotografica, no un corte levantado.
"""
import copy
import numpy as np
import manifold3d as mf
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from fachada_campus import solid, part_solid, as_mesh, replace_part


def preserve_other_sections(b, previous):
    """Keep accepted geometry outside this section during a local revision."""
    if not previous:
        return
    old = {p['id']: p for p in previous['items'] if '/Retoques_Icrea' not in p['group']}
    scope = box(16, -10, 28, 8.5)
    ramp=Polygon(b.ARCH_REVIEW['posteriorRamp']['outline']).buffer(.02) if b.ARCH_REVIEW.get('lateralIcrea',{}).get('finishReview') else Polygon()
    def ramp_part(p):
        return p['role']=='beam' and p['level']==0 and b.part_footprint(p).intersects(ramp)
    result = []
    used = set()
    for p in b.PARTS:
        frames = '/Marcos_Puertas' in p['group']
        local = not frames and ((p['level']!=4 and b.part_footprint(p).intersects(scope)) or ramp_part(p))
        if p['id'] in old:
            result.append(p if local else copy.deepcopy(old[p['id']]))
            used.add(p['id'])
        elif local:
            result.append(p)
    for ident, p in old.items():
        if ident not in used and not ramp_part(p) and (p['level']==4 or '/Marcos_Puertas' in p['group'] or
                                  not b.part_footprint(p).intersects(scope)):
            result.append(copy.deepcopy(p))
    b.PARTS[:] = result


def stair_cases(data):
    cases = copy.deepcopy(data['eastStairs'])
    review = data.get('reviewedArchitecture', {}).get('lateralIcrea')
    if not review:
        return cases
    case = cases[0]
    # Preserve each flight's boundary and the original total of 19 rises.
    # Redistribution around the photographic entry elevation is estimated.
    for key, count in [('up', 12), ('return', 7)]:
        rows = np.asarray(case[key], dtype=float)
        positions = np.r_[0, np.cumsum(np.linalg.norm(np.diff(rows.mean(axis=1), axis=0), axis=1))]
        stations = np.linspace(0, positions[-1], count)
        case[key] = np.stack([np.column_stack([np.interp(stations, positions, rows[:, side, axis])
                                              for axis in range(2)]) for side in range(2)], axis=1).tolist()
    case['upRisers'] = 12
    case['midHeightOverride'] = review['gradeNPT']
    case['evidence'] += '; acceso lateral fotografiado en rasante de vereda'
    case['verticalRule'] = ('R9: descanso lateral a -1.17 inferido de fotografias. Total 19 contrahuellas conservado; '
                            'reparto 12/7 y huellas interpoladas dentro de los bordes CAD, pendientes de corte o medicion.')
    return cases


def subtract(b, footprint, bottom, top, materials=('wall', 'floor', 'metal')):
    tool = solid(b, footprint, bottom, top)
    retained = []
    for part in b.PARTS:
        if part['hidden'] or part['material'] not in materials or part['role'] == 'door':
            retained.append(part)
            continue
        v = b.materialize_vertices(part)
        if v[:, 1].max() <= bottom or v[:, 1].min() >= top or not b.part_footprint(part).intersects(footprint):
            retained.append(part)
            continue
        original = part_solid(b, part)
        result = original - tool
        if abs(original.volume() - result.volume()) < 1e-8:
            retained.append(part)
        elif not result.is_empty():
            replace_part(b, part, result)
            retained.append(part)
    b.PARTS[:] = retained


def add_missing(b, profile, bottom, top, name, level, material='wall'):
    desired = solid(b, profile, bottom, top)
    existing = []
    for p in b.PARTS:
        if p['hidden'] or p['material'] not in (('wall','floor') if material=='wall' else (material,)):
            continue
        v = b.materialize_vertices(p)
        if v[:, 1].max() <= bottom or v[:, 1].min() >= top or not b.part_footprint(p).intersects(profile):
            continue
        existing.append(part_solid(b, p))
    if existing:
        desired -= mf.Manifold.batch_boolean(existing, mf.OpType.Add)
    if not desired.is_empty():
        b.add_mesh(as_mesh(desired), b.LEVEL_NAMES[level]+'/Lateral_Icrea', name, material, True,
                   'fixed', level, 0, 1, 'Perfiles CAD A-01..A-04 y fotografias del lateral junto a I-crea',
                   'Complemento local; alturas de vanos y union al acceso inferidas, pendientes de cotejo en Unity.')


def build(b, data):
    review = data['reviewedArchitecture']['lateralIcrea']
    grade = review['gradeNPT']
    if review.get('shellRevision'):
        # The A-03 wall is continuous in the PDF. Native face recovery split
        # it at stair-section intersections, adding jagged wedges to the edge.
        shell = Polygon(review['shellRevision']['outlineA03'])
        b.PARTS[:] = [p for p in b.PARTS if p['id'] not in review['shellRevision']['replacedItems']]
        # A-02 window[30] polygonizes two crossed projection lines as a glass
        # wedge. PDF linework shows an open hall behind the low solid guard.
        b.PARTS[:] = [p for p in b.PARTS if p['id'] not in review['shellRevision']['excludedProjectionItems']]
        add_missing(b, shell, b.NPT[2], b.NPT[3]-.24, 'Muro_diagonal_escalera_A03_continuo', 2)
        for level in [2,3]:
            patch = shell.difference(b.FLOORS[level])
            b.fixed_prism(patch, b.NPT[level]-.24, b.NPT[level],
                          b.LEVEL_NAMES[level]+'/Lateral_Icrea', 'Encuentro_losa_muro_diagonal_CAD',
                          'floor', True, level, 'A-03/A-04: dos caras rectas del muro de escalera',
                          'Completa solo el apoyo del cerramiento, sin rellenar el hueco de escalera.')
            b.FLOORS[level] = b.FLOORS[level].union(patch)
    # Replace the inferred +0 roof over the cistern/service forecourt by
    # pavement at street elevation, preserving all underground technical rooms.
    apron_mask = box(*review['forecourtBounds'])
    subtract(b, apron_mask, grade, .001, ('floor', 'wall'))
    b.FLOORS[1] = b.FLOORS[1].difference(apron_mask)
    excavation = unary_union([b.envelope(0), b.envelope(1)] + b.GROUND_PATCHES)
    apron = excavation.intersection(apron_mask)
    # Entry bridge lies inside the already excavated stair enclosure.
    bridge = box(*review['entryBridgeBounds'])
    pavement = apron.union(bridge)
    if review.get('shellRevision'):
        # The original campus already provides most of the threshold. Adding
        # a second face at precisely the same elevation produces black flicker.
        from verificar import terrain_local
        tv,tf = terrain_local({'anchor':b.ANCHOR})
        triangles = tv[tf]
        normals = np.cross(triangles[:,1]-triangles[:,0], triangles[:,2]-triangles[:,0])
        caps = triangles[(normals[:,1]>1e-9) & np.all(np.abs(triangles[:,:,1]-grade)<.00002,axis=1)]
        campus_ground = unary_union([Polygon(t[:,[0,2]]) for t in caps])
        pavement = pavement.difference(campus_ground)
        # Some existing foundation walls were truncated to grade by the apron
        # cutter. Where the campus already covers them, bury their crowns
        # below its 16 cm thickness rather than leaving a second ground face.
        crowns = []
        for p in b.PARTS:
            if p['hidden'] or p['material']!='wall':
                continue
            vertices = b.materialize_vertices(p).reshape(-1,3,3)
            normals = np.cross(vertices[:,1]-vertices[:,0],vertices[:,2]-vertices[:,0])
            selected = vertices[(normals[:,1]>1e-9) & np.all(np.abs(vertices[:,:,1]-grade)<.00002,axis=1)]
            crowns.extend(Polygon(t[:,[0,2]]) for t in selected)
        buried = unary_union(crowns).intersection(campus_ground).intersection(apron_mask.union(bridge))
        if not buried.is_empty:
            subtract(b, buried, grade-.161, grade+.0001, ('wall',))
    b.fixed_prism(pavement, grade-.24, grade, '06_Escaleras_Rampas/Acceso_Lateral_Icrea',
                  'Piso_acceso_lateral_rasante_vereda', 'floor', True, 0,
                  'A-02 vereda NPT=-1.17; fotos de entrada lateral junto al vehiculo',
                  'Rasante de acceso inferida por continuidad fotografica; cubre localmente el recorte sin modificar el terreno del campus.')
    if review.get('shellRevision'):
        # A visible closed edge, not a thin surface across an open excavation.
        skirt = pavement.boundary.buffer(.10, cap_style='flat', join_style='mitre').intersection(pavement)
        from shapely import wkt
        passages = [wkt.loads(s['tread']).buffer(.32) for s in b.STEPS if s['upper']<grade+.001]
        passages += [LineString([d['hinge'],d['closed']]).buffer(.35,cap_style='flat') for d in b.DOORS[0]]
        skirt = skirt.difference(unary_union(passages))
        add_missing(b, skirt, b.NPT[0], grade-.24, 'Cierre_vertical_borde_piso_lateral', 0)
        # Complete the plinth below the end bay of the street screen. The ramp
        # remains inside its own CAD outline, beside this exterior edge.
        region = box(16.3,7.2,27.35,8.35)
        base_edge = b.FLOORS[1].boundary.buffer(.11, cap_style='flat', join_style='mitre').intersection(region)
        exposed = [b.part_footprint(p).intersection(region) for p in b.PARTS
                   if p['level']==1 and p['material']=='wall' and not p['hidden']]
        base_edge = base_edge.union(unary_union(exposed))
        add_missing(b, base_edge, b.NPT[0], .15, 'Cierre_zocalo_bajo_celosia_lateral', 0)
    # The stair portal is open at street level, not a full-height missing wall.
    portal = box(*review['portalBounds'])
    subtract(b, portal, grade, grade+review['doorHeadEstimated'])
    b.FLOORS[1] = b.FLOORS[1].difference(portal)
    side = data['levels'][1]
    native = unary_union([Polygon(side['wall'][k]['outline'], side['wall'][k]['holes']) for k in [19,25]])
    # Photographs show a continuous grey base beneath the recessed hall.
    # Subtract existing slabs/walls so their fascia has a single owner.
    native = native.union(box(21.70464, -6.045, 21.9543, 6.18))
    add_missing(b, native.difference(portal), grade, 0, 'Zocalo_continuo_escalera_lateral', 1)
    add_missing(b, box(*review['portalWallBounds']), grade+review['doorHeadEstimated'], b.NPT[2]-.24, 'Dintel_ingreso_lateral', 1)
    # Stop the basement landing guard at the side entrance; retain its other edges.
    # Top openings retain the native 1.20 m width; add the absent head so the
    # stair opening reads as a square rather than a slit extending to the slab.
    for level, index in [(2,7),(3,28)]:
        record = data['levels'][level]['low'][index]
        profile = Polygon(record['outline'], record['holes'])
        bottom = b.NPT[level]
        add_missing(b, profile, bottom, bottom+review['stairWindowSillEstimated'],
                    'Antepecho_vano_escalera_lateral', level)
        add_missing(b, profile, bottom+review['stairWindowHeadEstimated'], b.NPT[level+1]-.24,
                    'Dintel_vano_escalera_lateral', level)
        # Close the small recovered-CAD gap between the square opening and
        # the end of the diagonal wall; photos show continuous concrete here.
        add_missing(b, box(21.723, -6.045, 21.974, -5.82), bottom, b.NPT[level+1]-.24,
                    'Empalme_esquina_vano_lateral', level)
    b.EVIDENCE.append({'element':'Lateral junto a I-crea', 'revision':'R9_Lateral_Icrea',
                       'confirmed':'Huellas exteriores CAD, voladizo A-03/A-04, vanos y vereda rotulada -1.17; fotos confirman entrada y concreto visto',
                       'estimated':'Descanso a rasante; reparto 12/7 de 19 contrahuellas del sotano; alturas de puerta 2.15 y vano 1.10/2.30',
                       'status':'Interpretacion geometrica revisable; no medicion ni prueba Play'})
