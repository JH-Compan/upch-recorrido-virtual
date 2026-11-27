"""Read Unity Force Text assets without changing serialized IDs or GUIDs."""
from pathlib import Path
import json
import re
import yaml
import numpy as np
import trimesh


class UnityText:
    def __init__(self, path):
        self.path = Path(path)
        self.text = self.path.read_text(encoding="utf-8")
        chunks = re.split(r"(?m)^--- !u!(\d+) &(-?\d+)(?: stripped)?\n", self.text)
        self.header = chunks[0]
        self.docs = {int(chunks[i+1]): (int(chunks[i]), chunks[i+2])
                     for i in range(1, len(chunks), 3)}
        self.heads = {int(m[1]): m[0] for m in re.finditer(
            r'(?m)^--- !u!\d+ &(-?\d+)(?: stripped)?\n', self.text)}
        self.names = {}
        self.transforms = {}
        for ident, (kind, body) in self.docs.items():
            if kind == 1:
                value = re.search(r"(?m)^  m_Name: (.*)$", body)
                if value:
                    value = value[1]
                    self.names[ident] = yaml.safe_load(value) if value.startswith(('"', "'")) else value
            if kind == 4 and "m_LocalPosition:" in body:
                self.transforms[ident] = dict(
                    go=ref(body, "m_GameObject"), parent=ref(body, "m_Father"),
                    position=vector(body, "m_LocalPosition"),
                    rotation=vector(body, "m_LocalRotation", "xyzw"),
                    scale=vector(body, "m_LocalScale"))
        self.go_transforms = {t['go']: i for i, t in self.transforms.items()}

    def world(self, ident):
        t = self.transforms[ident]
        x, y, z, w = t['rotation']
        local = trimesh.transformations.quaternion_matrix([w, x, y, z]) @ np.diag([*t['scale'], 1.])
        local[:3, 3] = t['position']
        return self.world(t['parent']) @ local if t['parent'] in self.transforms else local

    def path_for(self, ident):
        t = self.transforms[ident]
        name = self.names[t['go']]
        return self.path_for(t['parent']) + '/' + name if t['parent'] in self.transforms else name

    def save(self):
        # Preserve the existing document order, IDs, and unrelated text.
        self.path.write_text(self.header + ''.join(self.heads.get(ident, f'--- !u!{kind} &{ident}\n')+body
                                                  for ident, (kind, body) in self.docs.items()), encoding='utf-8')


def ref(body, key):
    return int(re.search(r'(?m)^  ' + key + r': \{fileID: (-?\d+)', body)[1])


def vector(body, key, axes='xyz'):
    data = re.search(r'(?m)^  ' + key + r': \{([^}]+)\}', body)[1]
    values = {a: float(v) for a, v in re.findall(r'([xyzw]): ([^,}]+)', data)}
    return np.array([values[a] for a in axes])


def read_mesh(path):
    text = Path(path).read_text()
    n = int(re.search(r'm_VertexCount: (\d+)', text)[1])
    data = bytes.fromhex(re.search(r'_typelessdata: ([a-fA-F0-9]+)', text)[1])
    vertices = np.frombuffer(data, '<f4').reshape(n, -1)[:, :3].astype(float)
    index_format = int(re.search(r'm_IndexFormat: (\d+)', text)[1])
    faces = np.frombuffer(bytes.fromhex(re.search(r'm_IndexBuffer: ([a-fA-F0-9]+)', text)[1]),
                          '<u4' if index_format else '<u2').reshape(-1, 3).copy()
    return trimesh.Trimesh(vertices, faces, process=False)


def write_mesh(path, mesh, template, name):
    """Write the same Unity 6 vertex layout already used in this repository."""
    text = Path(template).read_text()
    points = mesh.vertices[mesh.faces].reshape(-1, 3).astype('<f4')
    normals = np.repeat(mesh.face_normals, 3, axis=0).astype('<f4')
    uv = points[:, [0, 2]] * .5
    raw = np.column_stack([points, normals, uv]).astype('<f4').tobytes().hex()
    indices = np.arange(len(points), dtype='<u4').tobytes().hex()
    center = mesh.bounds.mean(0)
    extent = np.ptp(mesh.bounds, axis=0) / 2
    def vec(v): return '{x: %.9g, y: %.9g, z: %.9g}' % tuple(v)
    text = re.sub(r'(?m)^  m_Name: .*$', '  m_Name: '+name, text)
    text = re.sub(r'(?m)^(    indexCount|    vertexCount|    m_VertexCount): \d+$',
                  lambda m: m[1]+': '+str(len(points)), text)
    text = re.sub(r'(?m)^  m_IndexFormat: \d+$', '  m_IndexFormat: 1', text)
    text = re.sub(r'(?m)^  m_IndexBuffer: .*$', '  m_IndexBuffer: '+indices, text)
    text = re.sub(r'(?m)^    m_DataSize: \d+$', '    m_DataSize: '+str(len(points)*32), text)
    text = re.sub(r'(?m)^    _typelessdata: .*$', '    _typelessdata: '+raw, text)
    text = re.sub(r'(m_Center: )\{[^}]+\}', lambda m: m[1]+vec(center), text)
    text = re.sub(r'(m_Extent: )\{[^}]+\}', lambda m: m[1]+vec(extent), text)
    Path(path).write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n')


def asset_guids(root):
    result = {}
    for meta in Path(root).rglob('*.meta'):
        match = re.search(r'(?m)^guid: ([a-f0-9]{32})$', meta.read_text())
        if match:
            assert match[1] not in result, ('Duplicate GUID', meta, result.get(match[1]))
            result[match[1]] = meta.with_suffix('')
    return result
