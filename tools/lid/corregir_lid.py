"""Reproducible, local correction for the LID imported in Campus.

Run from the repository root: python tools/lid/corregir_lid.py
Does not regenerate architecture or renumber any retained Unity objects.
"""
from pathlib import Path
import hashlib
import json
import re
import numpy as np
import trimesh
from shapely import affinity
from shapely.geometry import Polygon, shape, mapping
from shapely.ops import unary_union
from unity_text import UnityText, read_mesh, write_mesh, asset_guids

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'Assets/UPCH/LIDCompleto'
PREFAB_GUID = 'feddea9206ce8abc5e23031e26161927'


def main():
    reference = json.loads((Path(__file__).parent/'referencia_cad.json').read_text())
    prefab = UnityText(ASSETS/'Prefabs/Edificio_LID.prefab')
    removed = []
    removal = set()
    # The old importer used generic stools for small footprints, and also
    # converted certain explicitly named seats and sanitary blocks into desks.
    unwanted_numbers = set()
    inventory = json.loads((Path(__file__).parent/'mobiliario_origen.json').read_text())
    for go, name in prefab.names.items():
        n = re.sub(r'^LID_\d+_', '', name)
        if not n.startswith('Mueble_'):
            continue
        # Source provenance is kept in the checked-in furniture inventory.
        source = inventory.get(name, '')
        if any(s in source.upper() for s in ['S-22', 'SOFA', 'SILLA', 'SF-12', 'SF-012', '1P-TOPPIECE']):
            tr = prefab.go_transforms[go]
            unwanted_numbers.add((prefab.transforms[tr]['parent'], n.split('_')[-1]))
    for go, name in prefab.names.items():
        tr = prefab.go_transforms.get(go)
        if tr is None or '/Mobiliario/' not in prefab.path_for(tr):
            continue
        n = re.sub(r'^LID_\d+_', '', name)
        if (n.startswith(('PC_', 'Asiento_', 'Apoyo_Asiento_', 'Base_Asiento_'))
                or (n.startswith(('Mueble_', 'Encimera_'))
                    and (prefab.transforms[tr]['parent'], n.split('_')[-1]) in unwanted_numbers)):
            body = prefab.docs[go][1]
            components = set(map(int, re.findall(r'component: \{fileID: (\d+)\}', body)))
            removal.update([go, *components])
            removed.append({'gameObject': go, 'name': name, 'path': prefab.path_for(tr)})
    for ident in removal:
        del prefab.docs[ident]
    for ident, (kind, body) in list(prefab.docs.items()):
        if kind == 4:
            body = re.sub(r'(?m)^  - \{fileID: (\d+)\}\n',
                          lambda m: '' if int(m[1]) in removal else m[0], body)
            body = body.replace('  m_Children:\n  m_Father:', '  m_Children: []\n  m_Father:')
            prefab.docs[ident] = kind, body
    prefab.save()

    scene = UnityText(ROOT/'Assets/UPCH/Scenes/Campus.unity')
    instance_ids = [i for i, (k, b) in scene.docs.items()
                    if k == 1001 and re.search(r'm_SourcePrefab: \{[^}]*guid: '+PREFAB_GUID, b)]
    assert len(instance_ids) == 1, 'Expected exactly one LID in Campus; inspect duplicates before editing.'
    ident = instance_ids[0]
    kind, body = scene.docs[ident]
    pattern = r'(target: \{fileID: 1002, guid: '+PREFAB_GUID+r', type: 3\}\n      propertyPath: m_LocalPosition.y\n      value: )([^\n]+)'
    old_y = float(re.search(pattern, body)[2])
    # Align the EXISTING model entrance pavement (+1.20 in its own datum) to
    # Campus terrain Y=0. This is model registration, not a surveyed ground NPT.
    body, count = re.subn(pattern, lambda m: m[1]+'-1.2', body)
    assert count == 1
    scene.docs[ident] = kind, body

    original = ROOT/'Assets/UPCH/Campus/Generated/Meshes/Site.asset'
    terrain = read_mesh(original)
    tris = terrain.vertices[terrain.faces]
    top = tris[np.all(abs(tris[:, :, 1]) < 1e-6, axis=1)]
    site = unary_union([Polygon(t[:, [0, 2]]) for t in top])
    # Campus has LID rotated 90 degrees about Y. Map plan to world, then to the
    # terrain mesh's existing local origin. Root X/Z and terrain transform are
    # measured from Campus, not inferred from the architectural plan.
    mods = dict(re.findall(r'propertyPath: (m_LocalPosition\.[xz])\n      value: ([^\n]+)', body))
    x, z = float(mods['m_LocalPosition.x']), float(mods['m_LocalPosition.z'])
    terrain_transform = scene.world(357576545)
    assert np.allclose(terrain_transform[:3, :3], np.eye(3))
    assert abs(terrain_transform[1, 3]) < 1e-6
    # x_world = rootX + (17.305-planY); z_world = rootZ-(planX-32.55).
    void = affinity.affine_transform(shape(reference['terrain_void_plan']),
        [0, -1, -1, 0, x+17.305-terrain_transform[0, 3], z+32.55-terrain_transform[2, 3]])
    footprint = site.difference(void).simplify(1e-7, preserve_topology=True)
    meshes = []
    for polygon in getattr(footprint, 'geoms', [footprint]):
        mesh = trimesh.creation.extrude_polygon(polygon, .16, engine='earcut')
        v = mesh.vertices.copy()
        mesh.vertices = np.column_stack([v[:, 0], v[:, 2]-.16, v[:, 1]])
        mesh.faces = mesh.faces[:, [0, 2, 1]]
        assert mesh.is_watertight and mesh.volume > 0
        meshes.append(mesh)
    cut = trimesh.util.concatenate(meshes)
    destination = original.with_name('Site_Recorte_LID.asset')
    write_mesh(destination, cut, original, 'Site_Recorte_LID')
    guid = hashlib.md5(b'UPCH-LID:Site_Recorte_LID-20261120').hexdigest()
    destination.with_suffix('.asset.meta').write_text(
        'fileFormatVersion: 2\nguid: '+guid+'\nNativeFormatImporter:\n  externalObjects: {}\n'
        '  mainObjectFileID: 4300000\n  userData:\n  assetBundleName:\n  assetBundleVariant:\n')
    for ident in (357576547, 357576549):
        kind, terrain_body = scene.docs[ident]
        assert 'm_Mesh:' in terrain_body
        terrain_body = re.sub(r'(m_Mesh: \{fileID: 4300000, guid: )[a-f0-9]{32}',
                              lambda m: m[1]+guid, terrain_body)
        scene.docs[ident] = kind, terrain_body
    scene.save()

    report = {
        'base_commit': '98e8d8030f6ea5e9bee3360b28c86395f0abf28e',
        'scene_root_y_before': old_y, 'scene_root_y_after': -1.2,
        'external_model_pavement_npt': 1.2, 'campus_ground_y': 0,
        'surveyed_external_npt': None,
        'terrain_removed_m2': site.intersection(void).area,
        'terrain_retained_m2': footprint.area,
        'terrain_outside_void_difference_m2': site.difference(void).symmetric_difference(footprint).area,
        'removed_parts': removed,
        'architecture_regenerated': False,
        'unity_play_tested': False,
    }
    output = ROOT/'docs/lid/correccion_aplicada.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    # Do not erase the original before/after inventory when rerunning the fix.
    if not output.exists():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != 'removed_parts'}, indent=2))
    print('Removed furniture parts:', len(removed))


if __name__ == '__main__':
    main()
