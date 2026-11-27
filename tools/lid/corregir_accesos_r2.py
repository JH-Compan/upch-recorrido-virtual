"""R2: local soffit clearance and review-pavement relief, preserving CAD placement."""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import Polygon, shape, mapping
from shapely.ops import unary_union
from unity_text import UnityText, asset_guids, read_mesh, write_mesh, ref

ROOT = Path(__file__).resolve().parents[2]
A = ROOT / 'Assets/UPCH/LIDCompleto'


def prism(poly, bottom, top):
    m = trimesh.creation.extrude_polygon(poly, top-bottom, engine='earcut')
    v = m.vertices.copy()
    m.vertices = np.column_stack([v[:, 0], v[:, 2]+bottom, v[:, 1]])
    m.faces = m.faces[:, [0, 2, 1]]
    return m


def meta(path):
    path.with_suffix(path.suffix+'.meta').write_text('fileFormatVersion: 2\nguid: '+hashlib.md5(('LID:R2:'+path.name).encode()).hexdigest()+'\n')


def main():
    report_path = A/'Documentacion/Revision_Accesos_R2.json'
    if report_path.exists():
        print('R2 ya aplicada. No se repiten los recortes.')
        return
    p = UnityText(A/'Prefabs/Edificio_LID.prefab')
    guids = asset_guids(ROOT/'Assets')
    reference = json.loads((ROOT/'tools/lid/referencia_cad.json').read_text())
    first_flight = []
    target = None
    for kind, body in p.docs.values():
        if kind != 33:
            continue
        go = ref(body, 'm_GameObject')
        name = p.names[go]
        if not ('Interior_Tramo01_Peldano' in name or name == 'LID_00086_Muro_Recuperado_10BBF4'):
            continue
        tr = p.go_transforms[go]
        path = guids[re.search(r'm_Mesh: \{[^}]*guid: ([a-f0-9]{32})', body)[1]]
        mesh = read_mesh(path)
        matrix = p.world(tr)
        mesh.apply_transform(matrix)
        if 'Peldano' in name:
            first_flight.append((name, mesh))
        else:
            target = (path, mesh, matrix)
    assert len(first_flight) == 9 and target
    path, wall, matrix = target
    wall.merge_vertices()
    assert wall.is_watertight and wall.volume > 0
    clips, cutters = [], []
    for name, tread in first_flight:
        ts = tread.vertices[tread.faces]
        upper = tread.bounds[1, 1]
        top = ts[np.all(np.abs(ts[:, :, 1]-upper)<1e-5, axis=1)]
        poly = unary_union([Polygon(t[:, [0, 2]]) for t in top])
        # Keep 22 cm beneath the walking surface as the existing estimated
        # stair support depth; remove only the wall protruding above it.
        bottom, ceiling = float(upper-.22), 3.2
        cutter = prism(poly, bottom, ceiling)
        intersection = trimesh.boolean.intersection([wall, cutter], engine='manifold')
        if intersection.volume > 1e-7:
            cutters.append(cutter)
            plan = affinity.affine_transform(poly, [1, 0, 0, -1, 32.55, 17.305])
            clips.append({'tread': name, 'bottom_npt': bottom, 'top_npt': ceiling,
                          'plan_polygon': mapping(plan), 'removed_volume_m3': float(intersection.volume)})
    assert cutters, 'Expected the verified wall/flight overlap'
    corrected = trimesh.boolean.difference([wall, *cutters], engine='manifold')
    assert corrected.is_watertight and corrected.volume > 0
    removed = wall.volume-corrected.volume
    assert 0 < removed < 2, 'Unexpectedly broad wall cut'
    corrected.apply_transform(np.linalg.inv(matrix))

    scene = UnityText(A/'Scenes/LID_Revision_Completa.unity')
    body = scene.docs[1014][1]
    pavement = guids[re.search(r'm_Mesh: \{[^}]*guid: ([a-f0-9]{32})', body)[1]]
    tr = scene.go_transforms[ref(body, 'm_GameObject')]
    matrix = scene.world(tr)
    ground = read_mesh(pavement)
    ground.apply_transform(matrix)
    ts = ground.vertices[ground.faces]
    y = ground.bounds[1, 1]
    surface = unary_union([Polygon(t[:, [0, 2]]) for t in ts if np.all(np.abs(t[:, 1]-y)<1e-5)])
    void = affinity.affine_transform(shape(reference['terrain_void_plan']), [1, 0, 0, -1, -32.55, 17.305])
    overlap = surface.intersection(void).area
    assert .15 < overlap < .17
    relief = surface.difference(void)
    pieces = [prism(poly, float(ground.bounds[0, 1]), float(y)) for poly in getattr(relief, 'geoms', [relief])]
    new_ground = trimesh.util.concatenate(pieces)
    assert new_ground.is_watertight
    new_ground.apply_transform(np.linalg.inv(matrix))
    write_mesh(path, corrected, path, re.search(r'm_Name: (.*)', path.read_text())[1])
    write_mesh(pavement, new_ground, pavement, re.search(r'm_Name: (.*)', pavement.read_text())[1])
    report = {'revision': 'LID_R2_Accesos_Estructura', 'base_commit': '5b47012fe5c0c453c0872a78857123d8b4698bf8',
              'source_hashes': reference['sources'], 'wall_mesh': str(path.relative_to(ROOT)),
              'wall_clearance_cuts': clips, 'wall_removed_volume_m3': float(removed),
              'review_pavement_mesh': str(pavement.relative_to(ROOT)), 'review_pavement_relief_m2': float(overlap),
              'unchanged': ['All stair transforms and tread meshes', 'All windows and doors', 'All floor slabs',
                            'Campus scene and Campus terrain', 'Prefab serialized IDs and transforms'],
              'estimated': ['Exterior grade +1.20', 'Stair support depth 0.22 m', 'Unspecified opening heights'],
              'unity_play_tested': False}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    meta(report_path)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
