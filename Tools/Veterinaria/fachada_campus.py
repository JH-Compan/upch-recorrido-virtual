"""Cerramiento hacia el campus: vanos CAD y materiales cotejados con fotos."""
import manifold3d as mf
import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon, box
from shapely import set_precision
from shapely.ops import unary_union


def solid(b, footprint, bottom, top):
    meshes = []
    for profile in b.polygons(footprint):
        if profile.area < 1e-8:
            continue
        mesh = b.section(profile, top - bottom)
        mesh.vertices[:, 1] += bottom
        meshes.append(mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, dtype=np.float32),
                                        np.asarray(mesh.faces, dtype=np.uint32))))
    return mf.Manifold.batch_boolean(meshes, mf.OpType.Add) if meshes else mf.Manifold()


def part_solid(b, part):
    vertices = b.materialize_vertices(part)
    mesh = trimesh.Trimesh(vertices=vertices, faces=np.arange(len(vertices)).reshape(-1, 3), process=True)
    mesh.fix_normals()
    result = mf.Manifold(mf.Mesh(np.asarray(mesh.vertices, dtype=np.float32),
                               np.asarray(mesh.faces, dtype=np.uint32)))
    if result.status() != mf.Error.NoError:
        raise ValueError("Cerramiento de campus no valido: " + part["id"])
    return result


def as_mesh(body):
    data = body.to_mesh()
    mesh = trimesh.Trimesh(vertices=np.asarray(data.vert_properties[:, :3]),
                           faces=np.asarray(data.tri_verts), process=False)
    mesh.fix_normals()
    return mesh


def replace_part(b, part, body):
    mesh = as_mesh(body)
    vertices = mesh.vertices[mesh.faces].reshape(-1, 3)
    bottom, top = b.y_range(part["role"], part["level"], part["bottom"], part["top"])
    vertices[:, 1] = (vertices[:, 1] - bottom) / (top - bottom)
    part.update(vertices=vertices.flatten().tolist(),
                normals=np.repeat(mesh.face_normals, 3, axis=0).flatten().tolist(),
                uv=np.c_[vertices[:, 0] / 3, vertices[:, 2] / 3].flatten().tolist())
    part.pop("materialGuids", None)
    part.pop("triangleMaterials", None)


def cut_parts(b, level, footprint, bottom, top, material):
    tool = solid(b, footprint, bottom, top)
    removed = []
    for part in b.PARTS:
        if part["level"] != level or part["material"] != material or part["hidden"]:
            continue
        vertices = b.materialize_vertices(part)
        if vertices[:, 1].max() <= bottom or vertices[:, 1].min() >= top:
            continue
        if not b.part_footprint(part).intersects(footprint):
            continue
        original = part_solid(b, part)
        result = original - tool
        if abs(original.volume() - result.volume()) < 1e-8:
            continue
        if result.is_empty():
            removed.append(part)
        else:
            replace_part(b, part, result)
    b.PARTS[:] = [part for part in b.PARTS if not any(part is old for old in removed)]


def louver(b, axis, bottom, top, pitch, group, name, level):
    """Celosia metalica con huecos reales; dimensiones verticales estimadas."""
    start, end = np.asarray(axis, dtype=float)
    along = (end - start) / np.linalg.norm(end - start)
    frame = .035
    pieces = []
    for point in [start + along * frame / 2, end - along * frame / 2]:
        profile = LineString([point - along * frame / 2, point + along * frame / 2]).buffer(.025, cap_style="flat")
        pieces.append(solid(b, profile, bottom, top))
    for height in np.linspace(bottom + .018, top - .018, max(2, round((top - bottom) / pitch) + 1)):
        profile = LineString([start, end]).buffer(.025, cap_style="flat")
        pieces.append(solid(b, profile, height - .018, height + .018))
    body = mf.Manifold.batch_boolean(pieces, mf.OpType.Add).simplify(.00001)
    if body.status() != mf.Error.NoError:
        raise ValueError("Celosia metalica de campus no valida")
    b.add_mesh(as_mesh(body), group, name, "metal", True, "fixed", level, 0, 1,
               "Fotografias del frente hacia campus; ejes de vanos CAD",
               "Metal oscuro, sin sustituirlo por concreto o vidrio. Paso y seccion estimados; comprobar alzado.")


def build(b, data):
    review = data["reviewedArchitecture"]["campusFacade"]
    for entry in review["levels"]:
        level = entry["level"]
        bottom = b.NPT[level]
        top = b.NPT[level + 1] - b.PARAMS["slabThickness"]
        host = box(*entry["frontBounds"])
        if entry.get("cornerOutline"):
            host = host.union(Polygon(entry["cornerOutline"]))
        # Native wall/window profiles supply the long facade. Only the missing
        # corner needs a new opaque volume; do not overlay the existing wall.
        closure = Polygon(entry.get("cornerOutline", []))
        closure = set_precision(closure, .0001).intersection(b.FLOORS[level]).intersection(b.FLOORS[level + 1])
        native = data["levels"][level]
        profiles = native.get("window", []) + native.get("windowBacking", [])
        openings = unary_union([Polygon(q["outline"], q["holes"]) for q in profiles]).intersection(host)
        opaque = unary_union([Polygon(q["outline"], q["holes"]) for q in native["wall"] + native["drywall"]])
        openings = openings.difference(opaque)
        sill, head = bottom + b.PARAMS["windowSill"], bottom + b.PARAMS["windowHead"]
        desired = solid(b, closure, bottom, top) - solid(b, openings, sill, head)
        for door in b.DOORS[level]:
            profile = LineString([door["hinge"], door["closed"]]).buffer(.32, cap_style="flat").intersection(host)
            desired = desired - solid(b, profile, bottom, bottom + b.PARAMS["doorHeight"])
        for window in data["reviewedArchitecture"].get("highWindows", []):
            if window["level"] != level:
                continue
            profile = LineString(window["axis"]).buffer(window["halfDepthEstimated"], cap_style="flat")
            desired = desired - solid(b, profile.intersection(host), bottom + window["sillEstimated"], bottom + window["headEstimated"])
        if entry.get("louverAxis"):
            axis = entry["louverAxis"]
            profile = LineString(axis).buffer(.18, cap_style="flat")
            cut_parts(b, level, profile, sill, head, "wall")
            desired = desired - solid(b, profile, sill, head)
            louver(b, axis, sill, head, review["louverPitchEstimated"], b.LEVEL_NAMES[level] + "/Celosias_Campus",
                   "Celosia_metalica_campus", level)
        # Existing columns and walls retain ownership of their surfaces.
        existing = []
        for part in b.PARTS:
            if part["level"] == level and part["material"] == "wall" and not part["hidden"]:
                if b.part_footprint(part).intersects(closure):
                    existing.append(part_solid(b, part))
        if existing:
            desired = desired - mf.Manifold.batch_boolean(existing, mf.OpType.Add)
        pieces = [q for q in desired.decompose() if q.volume() > 1e-5]
        if pieces:
            body = mf.Manifold.batch_boolean(pieces, mf.OpType.Add)
            b.add_mesh(as_mesh(body), b.LEVEL_NAMES[level] + "/Fachada_Campus", "Cierre_fachada_campus", "wall", True,
                       "fixed", level, 0, 1, entry["source"],
                       "Completa el cerramiento opaco fuera de los vanos CAD. Conserva el acceso de doble altura y las circulaciones.")
    b.EVIDENCE.append({"element": "Fachada interior y esquina del ingreso", "revision": "R8_Fachada_Campus",
                       "confirmed": "Cerramiento opaco, vidrio y celosias metalicas diferenciados en fotografias; vanos de plantas CAD",
                       "estimated": "Cierre de union en esquina A-04 inferido entre perfiles existentes; alturas, paso y secciones de celosias no medidos en alzado",
                       "status": "Comprobar fachada y circulacion en Unity; no es certificacion arquitectonica"})
