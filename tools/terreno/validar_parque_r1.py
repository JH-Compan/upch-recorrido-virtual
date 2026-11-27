"""Check the serialized terrain candidate, source preservation and scene bindings."""
from pathlib import Path
import sys
import json
import re
import subprocess
import numpy as np
from shapely.geometry import shape
from shapely import affinity

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/lid'))
from unity_text import UnityText, asset_guids, read_mesh, ref
from construir_parque_r1 import geometry_hash

A = ROOT/'Assets/UPCH/TerrenoCampusR1'
control = json.loads((A/'Datos/Control_Terreno_R1.json').read_text())
data = json.loads((A/'Datos/Aplicacion_Terreno_R1.json').read_text())
report_path = ROOT/'docs/terreno/Validacion_Terreno_R1.json'
report = json.loads(report_path.read_text())
guids = asset_guids(ROOT/'Assets')
scene = UnityText(ROOT/'Assets/UPCH/Scenes/Campus.unity')
bindings = {b['oldGuid']: b for b in data['bindings']}
assigned = []
terrain = None
for kind, body in scene.docs.values():
    if kind != 33:
        continue
    guid = re.search(r'm_Mesh: \{[^}]*guid: ([a-f0-9]{32})', body)
    if not guid or guid[1] not in bindings:
        continue
    binding = bindings[guid[1]]
    original = read_mesh(guids[guid[1]])
    assert geometry_hash(original) == binding['oldHash']
    go = ref(body, 'm_GameObject')
    matrix = scene.world(scene.go_transforms[go])
    assert np.allclose(matrix.flatten(), binding['worldMatrix'], atol=1e-7)
    new = read_mesh(guids[binding['newGuid']])
    new.merge_vertices()
    assert new.is_watertight and new.volume > 0
    new.apply_transform(matrix)
    original.apply_transform(matrix)
    assigned.append({'object': scene.names[go], 'source': binding['name'], 'compatible': True})
    if binding['name'].startswith('Site'):
        terrain = new
        old_terrain = original
        colliders = [b for k, b in scene.docs.values() if k == 64 and ref(b, 'm_GameObject') == go]
        assert len(colliders) == 1 and guid[1] in colliders[0]
assert len(assigned) == 8 and terrain is not None

offset = np.array(control['registration']['cad14_to_world_translation'])
axis = np.linspace(*np.array(control['north_ramp_axis_cad14']), 81)+offset
high = shape(control['fixed_high_control_polygon']).representative_point()
low = shape(control['fixed_low_polygon']).representative_point()
samples = np.vstack([axis, np.array([[high.x, high.y], [low.x, low.y]])+offset])
origins = np.c_[samples[:, 0], np.full(len(samples), 10.), samples[:, 1]]
hits, rays, _ = terrain.ray.intersects_location(origins, np.tile([0,-1,0], (len(samples),1)), multiple_hits=True)
heights = np.array([hits[rays == i, 1].max() if np.any(rays == i) else np.nan for i in range(len(samples))])
expected = np.r_[np.linspace(.45, -.34, len(axis)), .45, -.34]
assert np.all(np.isfinite(heights)) and np.max(abs(heights-expected)) < .001

domain = affinity.translate(shape({'type':'Polygon','coordinates':[[
    [control['work_domain_cad14'][0], control['work_domain_cad14'][1]],
    [control['work_domain_cad14'][2], control['work_domain_cad14'][1]],
    [control['work_domain_cad14'][2], control['work_domain_cad14'][3]],
    [control['work_domain_cad14'][0], control['work_domain_cad14'][3]],
    [control['work_domain_cad14'][0], control['work_domain_cad14'][1]]]]}), *offset)
centers = old_terrain.triangles_center[old_terrain.face_normals[:,1]>.9]
outside = np.array([p for p in centers if not domain.buffer(.1).contains(__import__('shapely').geometry.Point(p[0],p[2]))])
outside[:,1] = 10
hits, rays, _ = terrain.ray.intersects_location(outside, np.tile([0,-1,0], (len(outside),1)), multiple_hits=True)
outside_y = [hits[rays==i,1].max() for i in range(len(outside))]
assert max(abs(np.array(outside_y))) < .0001

normals = terrain.face_normals
top = normals[normals[:,1]>.1]
slopes = 100*np.linalg.norm(top[:,[0,2]],axis=1)/top[:,1]
report['physical_ray_samples'] = len(samples)
report['physical_ray_max_height_error_m'] = float(np.max(abs(heights-expected)))
report['outside_graded_sector_samples'] = len(outside)
report['outside_sector_max_height_change_m'] = float(max(abs(np.array(outside_y))))
report['compatible_scene_assignments'] = assigned
report['surface_slope_percentiles_90_95_99_max'] = np.quantile(slopes,[.9,.95,.99,1]).tolist()
report['unconstrained_slopes_status'] = 'Interpolated candidate; not all seven CAD ramp profiles are reconstructed or certified.'
paths = ['Assets/UPCH/Scenes/Campus.unity', 'Assets/UPCH/LIDCompleto/Prefabs/Edificio_LID.prefab',
         'Assets/UPCH/Campus/Generated/Meshes/Site.asset', 'Assets/UPCH/Campus/Generated/Meshes/Site_Recorte_LID.asset']
for path in paths:
    assert (ROOT/path).read_bytes() == subprocess.check_output(['git','show','5b47012f:'+path],cwd=ROOT)
report['baseline_scene_prefab_and_source_terrains_byte_identical'] = True
report['errors'] = []
report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['meshes','compatible_scene_assignments']},indent=2))
