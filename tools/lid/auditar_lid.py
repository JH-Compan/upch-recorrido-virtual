"""Audit the actual native Unity meshes against the CAD control reference.

python tools/lid/auditar_lid.py
Output: docs/lid/validacion_actual.json and ambientes_actuales.csv.
This is a geometric/static check, not a Unity Editor or VR execution test.
"""
from pathlib import Path
import collections
import csv
import json
import re
import subprocess
import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import Polygon, Point, shape, LineString, box, mapping
from shapely.ops import unary_union
from unity_text import UnityText, ref, read_mesh, asset_guids

ROOT = Path(__file__).resolve().parents[2]
A = ROOT/'Assets/UPCH/LIDCompleto'
GUID = 'feddea9206ce8abc5e23031e26161927'


def main():
    reference = json.loads((Path(__file__).parent/'referencia_cad.json').read_text())
    revision_path = A/'Documentacion/Revision_Accesos_R2.json'
    clearance_cuts = json.loads(revision_path.read_text())['wall_clearance_cuts'] if revision_path.exists() else []
    prefab = UnityText(A/'Prefabs/Edificio_LID.prefab')
    scene = UnityText(ROOT/'Assets/UPCH/Scenes/Campus.unity')
    guids = asset_guids(ROOT/'Assets')
    meshes = {}
    geometry = []
    rendered_go = {ref(b,'m_GameObject') for k,b in prefab.docs.values() if k == 33}
    errors = []
    def require(condition, message):
        if not condition: errors.append(message)
    # Every component, parent, child and mesh reference in the persistent prefab.
    ids = re.findall(r'(?m)^--- !u!\d+ &(-?\d+)', prefab.text)
    require(len(ids) == len(set(ids)), 'Duplicate serialized prefab IDs')
    for ident, (kind, body) in prefab.docs.items():
        for r in re.findall(r'\{fileID: (-?\d+)\}', body):
            require(int(r) == 0 or int(r) in prefab.docs, f'Broken local reference {ident} -> {r}')
        for g in re.findall(r'guid: ([a-f0-9]{32})', body):
            require(g in guids, 'Missing asset GUID '+g)
        if kind not in (33,64,65):
            continue
        go = ref(body, 'm_GameObject')
        if kind != 33 and go in rendered_go: continue
        if kind == 65:
            g = next(g for g,p in guids.items() if p == A/'Meshes/Cubo.asset')
        else:
            g = re.search(r'm_Mesh: \{[^}]*guid: ([a-f0-9]{32})', body)[1]
        if g not in meshes:
            meshes[g] = read_mesh(guids[g])
        mesh = meshes[g].copy()
        tr = prefab.go_transforms[go]
        mesh.apply_transform(prefab.world(tr))
        geometry.append(dict(go=go, name=prefab.names[go], path=prefab.path_for(tr), mesh=mesh, rendered=kind==33))
    levels = []
    for level in reference['levels']:
        ts = [i for i, t in prefab.transforms.items() if prefab.names[t['go']] == level['name']]
        require(len(ts) == 1, 'Missing or repeated floor '+level['name'])
        if len(ts) != 1: continue
        t = prefab.transforms[ts[0]]
        require(np.allclose(t['position'], [0, level['elevation'], 0], atol=1e-6), 'Shifted level '+level['name'])
        require(np.allclose(t['scale'], [1,1,1]) and np.allclose(t['rotation'], [0,0,0,1]), 'Scaled/rotated floor '+level['name'])
        levels.append({'name': level['name'], 'npt': level['elevation'], 'world_y_campus': level['elevation']-1.2})

    sections = []
    # The source plan below the entrance continues under the steps. Exclude
    # those intentionally sloping soffits from a constant-height wall comparison.
    exclusion = unary_union([shape(r['polygon']) for r in reference['entry_clips']]
                            + [box(29.99504,34.60514,32.59998,36.00463)])
    section_cache = {}
    for level in reference['levels']:
        name, npt = level['name'], level['elevation']
        for category, key, fractions in [('Muros', 'walls', [.25,.65,.9] if name != 'Azotea' else [.15]),
                                         ('Tabiques', 'drywall', [.25])]:
            target = unary_union([shape(p) for p in level[key]] +
                ([shape(r['polygon']) for r in level['wallRepairs']] if key == 'walls' else []))
            parts = [g['mesh'] for g in geometry if g['path'].split('/')[1:3] == [name, category]]
            for fraction in fractions:
                height = npt + (level['top']-npt-.18)*fraction
                polygons = []
                # Project the horizontal section into the exact plan basis.
                matrix = np.array([[1,0,0,32.55],[0,0,-1,17.305],[0,1,0,-height],[0,0,0,1]])
                for mesh in parts:
                    section = mesh.section(plane_normal=[0,1,0], plane_origin=[0,height,0])
                    if section is None: continue
                    planar, _ = section.to_2D(to_2D=matrix)
                    polygons.extend(planar.polygons_full)
                actual = unary_union(polygons)
                expected = target
                # The explicit R2 soffit cut retains the native CAD wall footprint
                # beneath the stair support. Compare the exact removed prism only
                # at heights intersecting it; do not exempt an entire room/level.
                if name == 'Sotano' and key == 'walls':
                    for cut in clearance_cuts:
                        if cut['bottom_npt'] < height < cut['top_npt']:
                            expected = expected.difference(shape(cut['plan_polygon']))
                if name == 'Sotano':
                    expected = expected.difference(exclusion)
                    actual = actual.difference(exclusion)
                error = expected.symmetric_difference(actual).area
                require(error < .0005, f'CAD footprint mismatch {name}/{category} height {height}: {error}')
                sections.append(dict(level=name, category=category, height_npt=height,
                                     difference_m2=error, expected_m2=expected.area))
                if fraction == fractions[0]: section_cache[(name, category)] = actual

        # Low-wall sections provide context in the review drawings. They are
        # separate from the 22 primary-wall/partition source comparisons above.
        low_parts = [g['mesh'] for g in geometry if g['path'].split('/')[1:3] == [name, 'Muros_Bajos']
                     or (name == 'Azotea' and g['path'].split('/')[1:3] == [name, 'Fachada_Voladizo'])
                     or (name == 'Piso_01' and g['path'].split('/')[1:3] == ['Exterior', 'Ingreso']
                         and g['name'].endswith('_Borde_Jardin'))]
        low_polygons = []
        height = npt+.1
        matrix = np.array([[1,0,0,32.55],[0,0,-1,17.305],[0,1,0,-height],[0,0,0,1]])
        for mesh in low_parts:
            section = mesh.section(plane_normal=[0,1,0],plane_origin=[0,height,0])
            if section is not None:
                planar,_ = section.to_2D(to_2D=matrix);low_polygons.extend(planar.polygons_full)
        section_cache[(name,'Muros_Bajos')] = unary_union(low_polygons)

    # Read the real room-reference transforms, not a count copied from metadata.
    labels = []
    for ident, t in prefab.transforms.items():
        path = prefab.path_for(ident).split('/')
        if len(path) < 4 or path[2] != 'Rotulos_Referencia': continue
        p = prefab.world(ident)[:3,3]
        labels.append((path[1], prefab.names[t['go']], p))
    room_checks = []
    for i, label in enumerate(reference['room_labels'], 1):
        text = label['text'].replace('\n', ' ')
        p = np.array(label['position'])
        matching = [x for x in labels if x[0] == label['level'] and x[1] == text]
        distance = min((np.linalg.norm(x[2][[0,2]]-p[[0,2]]) for x in matching), default=1e9)
        require(distance < .001, 'Missing/moved room label '+label['level']+'/'+text)
        room_checks.append(dict(id=f'LID-REF-{i:03d}', level=label['level'], name=text,
                               plan_x=p[0]+32.55, plan_y=17.305-p[2], npt=p[1],
                               position_difference_m=float(distance)))
    require(len(labels) == len(reference['room_labels']), 'Room-reference count changed')

    # Check CAD opening/leaf footprints at their source location. Do not infer
    # that an open leaf's bounding box is the clear width of a doorway.
    opening_checks = []
    for level in reference['levels']:
        for j, door in enumerate(level['doors'], 1):
            features = door.get('cadFeatures')
            if not features or not features.get('leaf') or not features.get('opening'): continue
            candidates = [g for g in geometry if g['path'].split('/')[1:3] == [level['name'], 'Puertas']
                          and g['name'] in door.get('native_leaf_names', [])]
            expected = shape(features['leaf']['polygon'])
            actual = [Polygon(np.column_stack([g['mesh'].vertices[:,0]+32.55,
                                               17.305-g['mesh'].vertices[:,2]])).convex_hull for g in candidates]
            deviation = min((expected.hausdorff_distance(a) for a in actual), default=1e9)
            require(deviation < .002, 'Door leaf CAD mismatch '+level['name']+'/'+features['handle'])
            opening_checks.append({'level':level['name'], 'handle':features['handle'],
                                   'clear_width_source_m':features['opening']['width'],
                                   'leaf_plan_deviation_m':deviation})

    instances = [b for k,b in scene.docs.values() if k == 1001
                 and re.search(r'm_SourcePrefab: \{[^}]*guid: '+GUID, b)]
    require(len(instances) == 1, 'Expected exactly one LID instance in Campus')
    instance = instances[0]
    def component(axis):
        return float(re.search(r'propertyPath: m_LocalPosition\.'+axis+r'\n      value: ([^\n]+)', instance)[1])
    require(abs(component('y')+1.2) < 1e-6, 'Campus root no longer aligns model entrance pavement')
    old_guid = '57e7d07b1633e884483630cf973699ec'
    for k,b in scene.docs.values():
        if k == 1001 and re.search(r'm_SourcePrefab: \{[^}]*guid: '+old_guid, b):
            require('propertyPath: m_IsActive\n      value: 0' in b, 'Old L proxy still active')

    terrain = read_mesh(guids[re.search(r'm_Mesh: \{[^}]*guid: ([a-f0-9]{32})', scene.docs[357576549][1])[1]])
    collider_guid = re.search(r'm_Mesh: \{[^}]*guid: ([a-f0-9]{32})', scene.docs[357576547][1])[1]
    require(guids[collider_guid].name == 'Site_Recorte_LID.asset', 'Terrain collider was not updated')
    points = terrain.vertices[terrain.faces]
    top = points[np.all(abs(points[:,:,1]) < 1e-6, axis=1)]
    surface = unary_union([Polygon(t[:,[0,2]]) for t in top])
    transform = scene.world(357576545)
    void = affinity.affine_transform(shape(reference['terrain_void_plan']),
        [0,-1,-1,0,component('x')+17.305-transform[0,3],component('z')+32.55-transform[2,3]])
    intersection = surface.intersection(void).area
    # Unity serializes mesh positions as float32: use a small AREA tolerance,
    # and also check each interior sample, away from perimeter rounding.
    require(intersection < .002, f'Terrain still covers basement: {intersection} m2')
    floor_samples = []
    floor_meshes = [g['mesh'] for g in geometry if g['path'].split('/')[2] == 'Losas'
                    and 'Losa_Con_Vacios' in g['name']]
    for level in reference['levels']:
        hits = []
        for mesh in floor_meshes:
            p, _, _ = mesh.ray.intersects_location([[0,level['elevation']+.04,0]], [[0,-1,0]], multiple_hits=True)
            if len(p): hits.extend(p[:,1])
        actual = max(hits) if hits else None
        require(actual is not None and abs(actual-level['elevation']) < .001, 'Incorrect floor '+level['name'])
        floor_samples.append({'level':level['name'], 'expected_npt':level['elevation'], 'actual_npt':actual})

    unwanted = [name for name in prefab.names.values() if re.search(r'^LID_\d+_(PC_|Asiento_|Apoyo_Asiento_|Base_Asiento_)', name)]
    require(not unwanted, 'Computers/seats remain in prefab')
    # Confirm edits did not move, resize, remove, or rewrite any architectural
    # piece or the team's unrelated Campus objects.
    base = '98e8d8030f6ea5e9bee3360b28c86395f0abf28e'
    preserved = {}
    for file, current, allowed in [
        ('Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab',prefab,None),
        ('Assets/UPCH/Scenes/Campus.unity',scene,{116461175,357576547,357576549})]:
        raw = subprocess.check_output(['git','show',base+':'+file], cwd=ROOT).decode()
        temp = ROOT/'docs/lid/.baseline.tmp'
        temp.write_text(raw)
        original = UnityText(temp)
        temp.unlink()
        changes = []
        deleted = []
        for ident,(kind,body) in original.docs.items():
            if ident not in current.docs:
                deleted.append(ident)
                continue
            if (kind,body) != current.docs[ident]: changes.append(ident)
        if allowed is not None:
            require(set(changes) <= allowed and not deleted, 'Unrelated Campus objects changed')
        else:
            removed_go = set(original.names)-set(current.names)
            for go in removed_go:
                tr = original.go_transforms[go]
                require('/Mobiliario/' in original.path_for(tr), 'Architectural object removed: '+original.names[go])
            require(all(original.docs[i][0] == 4 for i in changes), 'Retained component/geometry modified')
            for i in changes:
                b = current.docs[i][1]
                old = original.docs[i][1]
                # Only child references to removed furniture may differ.
                scrub = lambda text: re.sub(r'(?m)^  - \{fileID: \d+\}\n','',text)
                require(scrub(b) == scrub(old), 'Retained transform moved: '+str(i))
        preserved[file] = dict(changed_documents=changes, deleted_documents=len(deleted))

    report = {'base_commit':base, 'source_hashes':reference['sources'],
              'levels':levels, 'native_meshes_read':len(meshes), 'native_rendered_parts':sum(g['rendered'] for g in geometry),
              'room_references_checked':len(room_checks), 'room_references_are_unique_rooms':False,
              'wall_sections':sections, 'door_leaves':opening_checks, 'floor_samples':floor_samples,
              'terrain_overlap_m2':intersection, 'unwanted_computer_or_seat_parts':unwanted,
              'preservation':preserved, 'errors':errors, 'unity_editor_executed':False,
              'unity_play_tested':False, 'external_grade_surveyed':False,
              'limits':['No architectural sections or exterior ground NPT in the supplied plans.',
                        'Opening heights, slab thickness and exterior stair risers remain provisional.',
                        'Wall intersections and floor-bearing contacts are intentional structural contacts; this is not a no-contact test.',
                        'Room labels may repeat within one space; they are not a count of unique rooms.']}
    out = ROOT/'docs/lid'
    (out/'validacion_actual.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (out/'huellas_nativas.json').write_text(json.dumps([
        {'level':name,'category':category,'geometry':mapping(geometry)}
        for (name,category),geometry in section_cache.items()],separators=(',',':')))
    with (out/'ambientes_actuales.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(room_checks[0]),lineterminator='\n');writer.writeheader();writer.writerows(room_checks)
    print(json.dumps({k:v for k,v in report.items() if k not in ['wall_sections','door_leaves','preservation']},ensure_ascii=False,indent=2))
    if errors: raise SystemExit(1)


if __name__ == '__main__':
    main()
