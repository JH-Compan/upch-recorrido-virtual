"""Build a reversible R1 terrain candidate with fixed CAD levels and interpolated joins.

No scene or building is modified. Unity applies the new mesh variants explicitly.
"""
from pathlib import Path
import sys
import json
import hashlib
import re
import numpy as np
import triangle
import trimesh
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve
from scipy.interpolate import LinearNDInterpolator
from shapely.geometry import Polygon, LineString, box, shape
from shapely.ops import unary_union, polygonize
from shapely import contains_xy, affinity

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools/lid'))
from unity_text import UnityText, asset_guids, read_mesh, write_mesh, ref

A = ROOT/'Assets/UPCH/TerrenoCampusR1'
CONTROL = json.loads((A/'Datos/Control_Terreno_R1.json').read_text())
OFFSET = np.array(CONTROL['registration']['cad14_to_world_translation'])
ORIGIN = np.array(CONTROL['work_domain_cad14'][:2])


def meta(path):
    guid = hashlib.md5(('UPCH:TerrenoCampusR1:'+str(path.relative_to(A))).encode()).hexdigest()
    text = 'fileFormatVersion: 2\nguid: '+guid+'\n'
    if path.suffix == '.asset':
        text += ('NativeFormatImporter:\n  externalObjects: {}\n  mainObjectFileID: 4300000\n'
                 '  userData:\n  assetBundleName:\n  assetBundleVariant:\n')
    path.with_suffix(path.suffix+'.meta').write_text(text)
    return guid


def pslg(domain, extra=(), max_area=1.2, refine_region=None):
    lines = [LineString(domain.exterior.coords)]
    lines.extend(LineString(r.coords) for r in domain.interiors)
    lines.extend(line.intersection(domain) for line in extra)
    network = unary_union(lines)
    vertices, segments, lookup = [], [], {}
    for line in getattr(network, 'geoms', [network]):
        if line.geom_type != 'LineString':
            continue
        coordinates = list(line.coords)
        for first, second in zip(coordinates, coordinates[1:]):
            pair = []
            for xy in (first, second):
                key = tuple(np.round(xy, 7))
                if key not in lookup:
                    lookup[key] = len(vertices)
                    vertices.append(key)
                pair.append(lookup[key])
            if pair[0] != pair[1]:
                segments.append(pair)
    data = {'vertices': vertices, 'segments': segments}
    if domain.interiors:
        data['holes'] = [Polygon(r).representative_point().coords[0] for r in domain.interiors]
    if refine_region is None:
        options = 'pq20a'+str(max_area)
    else:
        # Avoid spending VR triangles on the unchanged, flat rest of Campus.
        regions = []
        for region in polygonize(network):
            point = region.representative_point()
            if domain.covers(point):
                area = max_area if refine_region.covers(point) else 500.0
                regions.append([point.x, point.y, 0, area])
        data['regions'] = regions
        options = 'pq20a'
    result = triangle.triangulate(data, options)
    return result


def height_field():
    to_local = lambda p: affinity.translate(p, *(-ORIGIN))
    domain = to_local(box(*CONTROL['work_domain_cad14']))
    high = to_local(shape(CONTROL['fixed_high_control_polygon']))
    low = to_local(shape(CONTROL['fixed_low_polygon']))
    reserved = to_local(shape(CONTROL['reserved_platform']).buffer(1.0))
    zeros = [to_local(shape(p)) for p in CONTROL['fixed_zero_control_polygons']]
    axis = np.array(CONTROL['north_ramp_axis_cad14'])-ORIGIN
    # Subdivide the measured 9.875 m axis so the profile is represented directly.
    points = np.linspace(axis[0], axis[1], 25)
    lines = [LineString(p.exterior.coords) for p in (high, low, reserved, *zeros)]
    lines.append(LineString(points))
    result = pslg(domain, lines, .4)
    v = result['vertices']
    f = result['triangles']
    fixed = np.zeros(len(v), dtype=bool)
    values = np.zeros(len(v))
    # Do not impose a fictitious zero-level pit inside the future +1.40
    # platform. Its base remains interpolated; its slab/steps are not built R1.
    for poly, height in [(high, .45), (low, -.34), *((p, 0) for p in zeros)]:
        mask = contains_xy(poly.buffer(2e-6), v[:, 0], v[:, 1])
        fixed[mask] = True
        values[mask] = height
    bounds = domain.bounds
    outer = np.minimum.reduce([abs(v[:, 0]-bounds[0]), abs(v[:, 0]-bounds[2]),
                               abs(v[:, 1]-bounds[1]), abs(v[:, 1]-bounds[3])]) < 1e-6
    fixed[outer] = True
    values[outer] = 0
    on_axis = ((abs(v[:, 0]-axis[0, 0]) < 2e-6) &
               (v[:, 1] >= axis[0, 1]-1e-6) & (v[:, 1] <= axis[1, 1]+1e-6))
    fixed[on_axis] = True
    values[on_axis] = .45-.79*(v[on_axis, 1]-axis[0, 1])/(axis[1, 1]-axis[0, 1])
    edges = np.unique(np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1), axis=0)
    weights = 1/np.maximum(np.linalg.norm(v[edges[:, 0]]-v[edges[:, 1]], axis=1), 1e-8)
    i, j = edges.T
    rows = np.r_[i, j, i, j]
    cols = np.r_[j, i, i, j]
    data = np.r_[-weights, -weights, weights, weights]
    laplacian = coo_matrix((data, (rows, cols)), shape=(len(v), len(v))).tocsr()
    free = ~fixed
    values[free] = spsolve(laplacian[free][:, free], -laplacian[free][:, fixed]@values[fixed])
    assert values.min() >= -.340001 and values.max() <= .450001
    interpolation = LinearNDInterpolator(v, values, fill_value=0)
    axis_world = points+ORIGIN+OFFSET
    extra_world = [affinity.translate(line, *(ORIGIN+OFFSET))
                   for line in [*lines, LineString(domain.exterior.coords)]]

    def sample(world_xz):
        return np.asarray(interpolation(np.asarray(world_xz)-OFFSET-ORIGIN))

    np.savez_compressed(ROOT/'tools/terreno/campo_parque_r1.npz',
                        vertices_cad14=v+ORIGIN, triangles=f, heights=values)
    return sample, extra_world, axis_world


def extrude_surface(domain, bottom, top, sample, extra):
    refine = affinity.translate(box(*CONTROL['work_domain_cad14']), *OFFSET)
    result = pslg(domain, extra, 1.2, refine)
    v = result['vertices']
    height = sample(v)
    count = len(v)
    vertices = np.vstack([np.c_[v[:, 0], bottom+height, v[:, 1]],
                          np.c_[v[:, 0], top+height, v[:, 1]]])
    faces = [result['triangles'], result['triangles'][:, [0, 2, 1]]+count]
    # Only exterior/interior boundary edges, not internal grading constraints.
    tri = result['triangles']
    edges = np.sort(np.vstack([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
    unique, occurrences = np.unique(edges, axis=0, return_counts=True)
    for a, b in unique[occurrences == 1]:
        faces.append(np.array([[a, b, b+count], [a, b+count, a+count]]))
    mesh = trimesh.Trimesh(vertices=vertices, faces=np.vstack(faces), process=False)
    mesh.fix_normals(multibody=True)
    assert mesh.is_watertight and mesh.volume > 0
    return mesh


def geometry_hash(mesh):
    return hashlib.sha256(mesh.vertices.astype('<f4').tobytes()+mesh.faces.astype('<i4').tobytes()).hexdigest()


def main():
    sample, extra, axis = height_field()
    scene = UnityText(ROOT/'Assets/UPCH/Scenes/Campus.unity')
    guids = asset_guids(ROOT/'Assets')
    bindings = []
    checks = []
    for kind, body in scene.docs.values():
        if kind != 33:
            continue
        go = ref(body, 'm_GameObject')
        guid = re.search(r'm_Mesh: \{[^}]*guid: ([a-f0-9]{32})', body)
        if not guid:
            continue
        source = guids.get(guid[1])
        if not source:
            continue
        if source.name not in ['Site_Recorte_LID.asset', *('Region%d.asset' % i for i in range(7))]:
            continue
        variants = [source]
        if source.name == 'Site_Recorte_LID.asset':
            variants.append(source.with_name('Site.asset'))
        transform = scene.world(scene.go_transforms[go])
        assert np.allclose(transform[:3, :3], np.eye(3)), 'Ground transform needs separate review'
        for source in variants:
            original = read_mesh(source)
            old_world = original.copy()
            old_world.apply_transform(transform)
            ts = old_world.vertices[old_world.faces]
            top, bottom = old_world.bounds[1, 1], old_world.bounds[0, 1]
            surface = unary_union([Polygon(t[:, [0, 2]]) for t in ts if np.all(abs(t[:, 1]-top)<1e-6)])
            assert surface.geom_type == 'Polygon'
            graded = extrude_surface(surface, bottom, top, sample, extra)
            graded.apply_transform(np.linalg.inv(transform))
            # Resolve collapsed sub-micrometre triangles in float32 BEFORE
            # writing Unity's triangle soup, preserving a closed solid.
            graded.vertices = graded.vertices.astype('<f4').astype(float)
            graded.merge_vertices(digits_vertex=8)
            graded.update_faces(graded.nondegenerate_faces(height=1e-7))
            graded.update_faces(graded.unique_faces())
            graded.remove_unreferenced_vertices()
            graded.fix_normals(multibody=True)
            assert graded.is_watertight and graded.volume > 0
            destination = A/'Mallas'/(source.stem+'_Relieve_R1.asset')
            write_mesh(destination, graded, source, destination.stem)
            new_guid = meta(destination)
            decoded = read_mesh(destination)
            decoded.merge_vertices()
            assert decoded.is_watertight and decoded.volume > 0
            reread = decoded.copy()
            reread.apply_transform(transform)
            project = unary_union([Polygon(t[:, [0, 2]]) for t in reread.vertices[reread.faces]
                                   if abs(np.cross(t[1]-t[0], t[2]-t[0])[1]) > 1e-8])
            area_error = project.symmetric_difference(surface).area
            assert area_error < .015, (source.name, area_error)
            source_guid = re.search(r'guid: ([a-f0-9]{32})', source.with_suffix('.asset.meta').read_text())[1]
            bindings.append({'name': source.name, 'oldGuid': source_guid, 'newGuid': new_guid,
                             'oldHash': geometry_hash(original),
                             'worldMatrix': transform.flatten().tolist()})
            checks.append({'source': source.name, 'faces': len(graded.faces), 'closed_after_serialization': True,
                           'footprint_error_m2': float(area_error), 'old_horizontal_domain_preserved': True})
    assert len(bindings) == 9
    profile = sample(axis)
    expected = np.linspace(.45, -.34, len(axis))
    assert np.max(abs(profile-expected)) < 1e-6
    data = {'revision': 'Terreno_Parque_R1', 'bindings': bindings,
            'datum': '0.00 del parque -> Y=0 de trabajo; no certifica datums de edificios',
            'joins': 'interpolados, requieren revision; solo eje norte 8% impuesto directamente',
            'reserved': '+1.40 y accesos propios de Medicina/CREA no reconstruidos en R1'}
    world_axis = np.linspace(axis[0], axis[-1], 81)
    data['samplesWorld'] = [{'x': float(p[0]), 'z': float(p[1]), 'y': float(y)}
                            for p, y in zip(world_axis, np.linspace(.45, -.34, 81))]
    for polygon, height in [('fixed_high_control_polygon', .45), ('fixed_low_polygon', -.34)]:
        point = shape(CONTROL[polygon]).representative_point()
        data['samplesWorld'].append({'x': point.x+OFFSET[0], 'z': point.y+OFFSET[1], 'y': height})
    path = A/'Datos/Aplicacion_Terreno_R1.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    meta(path)
    report = {'revision': data['revision'], 'meshes': checks, 'north_profile_length_m': float(np.linalg.norm(axis[-1]-axis[0])),
              'north_profile_slope_percent': float((profile[0]-profile[-1])/np.linalg.norm(axis[-1]-axis[0])*100),
              'north_profile_max_error_m': float(np.max(abs(profile-expected))), 'min_npt': -.34, 'max_npt': .45,
              'high_platform_1_40_reserved': True, 'buildings_moved': False, 'original_assets_changed': False,
              'scene_changed': False, 'UnityPlay': 'NOT_RUN', 'CSharpCompilation': 'NOT_RUN'}
    (ROOT/'docs/terreno/Validacion_Terreno_R1.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
