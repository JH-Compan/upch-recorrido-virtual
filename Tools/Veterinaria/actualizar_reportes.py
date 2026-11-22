"""Actualiza los reportes desde los assets actuales, sin regenerar geometria."""
import hashlib
import json
import numpy as np
import trimesh

from verificar import BASE, mesh


def write_report(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    model_path = BASE / "Datos/Modelo_H.json"
    model = json.loads(model_path.read_text(encoding="utf-8"))
    levels = []
    mesh_hash = hashlib.sha256()
    bounds = {}
    for part in model["items"]:
        path = BASE / "Generado/Mallas" / (part["id"] + ".asset")
        mesh_hash.update(part["id"].encode("utf-8") + b"\0")
        mesh_hash.update(hashlib.sha256(path.read_bytes()).digest())
        if part["hidden"]:
            continue
        vertices, _ = mesh(path)
        low, high = vertices[:, :3].min(axis=0), vertices[:, :3].max(axis=0)
        level = part["level"]
        if level in bounds:
            low = np.minimum(bounds[level][0], low)
            high = np.maximum(bounds[level][1], high)
        bounds[level] = (low, high)
    for level, npt in enumerate(model["npt"]):
        low, high = bounds[level]
        levels.append({
            "level": level,
            "NPT": npt,
            "boundsLocal": [np.round(low.astype(float), 6).tolist(),
                            np.round(high.astype(float), 6).tolist()],
            "source": "Limites de mallas visibles serializadas; no cadenas acotadas verificadas.",
        })
    dimensions = {
        "revision": model["revision"],
        "sourceModelSha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "sourceMeshSetSha256": mesh_hash.hexdigest(),
        "unityUnitsPerMetre": 1,
        "rootScale": [1, 1, 1],
        "rootPosition": model["anchor"],
        "levels": levels,
    }
    terrain_path = BASE / "Generado/Terreno_Recortado_H.asset"
    vertices, faces = mesh(terrain_path)
    terrain = trimesh.Trimesh(vertices=vertices[:, :3], faces=faces, process=True)
    edge_uses = np.bincount(terrain.edges_unique_inverse)
    terrain_report = {
        "asset": terrain_path.relative_to(BASE.parents[2]).as_posix(),
        "meshSha256": hashlib.sha256(terrain_path.read_bytes()).hexdigest(),
        "watertight": bool(terrain.is_watertight),
        "positiveVolume": bool(terrain.volume > 0),
        "signedVolume": float(terrain.volume),
        "windingConsistent": bool(terrain.is_winding_consistent),
        "thickness": float(np.ptp(vertices[:, 1])),
        "triangles": len(faces),
        "boundaryEdgesAfterWelding": int(np.count_nonzero(edge_uses == 1)),
        "nonManifoldEdgesAfterWelding": int(np.count_nonzero(edge_uses > 2)),
        "status": "CERRADO" if terrain.is_watertight else "REVISAR_TOPOLOGIA",
        "scope": "Topologia tras soldar vertices coincidentes. El volumen orientado no certifica un solido cerrado. No comprueba colisiones en Unity.",
        "UnityCollisionTest": "NOT_RUN",
    }
    folder = BASE / "Documentacion"
    write_report(folder / "Dimensiones.json", dimensions)
    write_report(folder / "Verificacion_Terreno.json", terrain_report)
    print(json.dumps({"revision": model["revision"], "reportesActualizados": 2,
                      "terrainStatus": terrain_report["status"],
                      "UnityCollisionTest": "NOT_RUN"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
