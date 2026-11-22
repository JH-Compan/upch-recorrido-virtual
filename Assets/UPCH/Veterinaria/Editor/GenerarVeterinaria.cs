using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UnityEngine.XR.Interaction.Toolkit.Locomotion.Teleportation;

namespace UPCH.Veterinaria.Editor
{
    public static class GenerarVeterinaria
    {
        const string Root = "Assets/UPCH/Veterinaria";
        const string PrefabPath = Root + "/Prefabs/Pabellon_H_Veterinaria.prefab";
        const string ModelPath = Root + "/Datos/Modelo_H.json";
        [Serializable] public class Parameters
        {
            public double slabThickness = .24, doorHeight = 2.15, windowSill = .95,
                windowHead = 2.50, roofWallHeight = 2.60, beamDepth = .40, railingHeight = 1.10;
        }
        [Serializable] public class Part
        {
            public string id, name, group, materialGuid, material, role, source, note;
            public string[] materialGuids;
            public int[] triangleMaterials;
            public bool collider, active, hidden;
            public int level;
            public double bottom, top;
            public float[] doorHinge;
            public float doorOpenDegrees;
            public double[] vertices;
            public float[] normals, uv;
        }
        [Serializable] public class Model
        {
            public int schema;
            public string rootName, baseCommit, sourcePdfSha256, revision;
            public float[] anchor, npt;
            public double[] nptPrecise, entryAnnexProbeXZ;
            public float yaw;
            public Parameters parameters;
            public Part[] items;
        }
        static Model ReadModel()
        {
            var model = JsonUtility.FromJson<Model>(File.ReadAllText(ModelPath));
            if (model == null || model.schema != 1 || model.items == null || model.items.Length < 1 || model.npt.Length != 5)
                throw new InvalidDataException("Datos de Veterinaria incompletos.");
            string parameters = Root + "/Datos/Parametros_H.json";
            if (File.Exists(parameters)) model.parameters = JsonUtility.FromJson<Parameters>(File.ReadAllText(parameters));
            var p = model.parameters;
            if (p == null || p.slabThickness <= 0 || p.slabThickness >= 1 || p.doorHeight < 1.9f || p.windowSill < 0 || p.windowHead <= p.windowSill)
                throw new InvalidDataException("Revisa los parámetros estimados de losa, puerta y ventana.");
            var ids = new HashSet<string>();
            foreach (var part in model.items)
            {
                if (part.level < 0 || part.level > 4 || string.IsNullOrWhiteSpace(part.id) || !ids.Add(part.id))
                    throw new InvalidDataException("Pieza o nivel inválido: " + part.id);
                if (part.vertices == null || part.vertices.Length == 0 || part.vertices.Length % 9 != 0 || part.uv.Length * 3 != part.vertices.Length * 2)
                    throw new InvalidDataException("Malla incompleta: " + part.id);
            }
            return model;
        }
        static (double x, double y) Height(Model m, Part p)
        {
            double y = m.nptPrecise != null && m.nptPrecise.Length == 5 ? m.nptPrecise[p.level] : m.npt[p.level];
            double next = p.level < 4 ? (m.nptPrecise != null && m.nptPrecise.Length == 5 ? m.nptPrecise[p.level + 1] : m.npt[p.level + 1]) : y;
            double h = p.level < 4 ? next - y - m.parameters.slabThickness : m.parameters.roofWallHeight;
            switch (p.role)
            {
                case "wall": return (y, y + h);
                case "slab": return (y - m.parameters.slabThickness, y);
                case "sill": return (y, y + m.parameters.windowSill);
                case "glass": return (y + m.parameters.windowSill, y + m.parameters.windowHead);
                case "windowFrameVertical": return (y + m.parameters.windowSill + .045, y + m.parameters.windowHead - .045);
                case "windowFrameBottom": return (y + m.parameters.windowSill, y + m.parameters.windowSill + .045);
                case "windowFrameTop": return (y + m.parameters.windowHead - .045, y + m.parameters.windowHead);
                case "windowLintel": return (y + m.parameters.windowHead, y + h);
                case "doorLintel": return (y + m.parameters.doorHeight, y + h);
                case "door": return (y + .025, y + m.parameters.doorHeight - .025);
                case "beam": return (y + h - m.parameters.beamDepth, y + h);
                case "railing": return (y, y + m.parameters.railingHeight);
                case "roofCover": return (y + m.parameters.roofWallHeight, y + m.parameters.roofWallHeight + .14);
                default: return (p.bottom, p.top);
            }
        }
        static Mesh MakeMesh(Model model, Part part)
        {
            int count = part.vertices.Length / 3;
            var vertices = new Vector3[count]; var uv = new Vector2[count]; var triangles = new int[count];
            var y = Height(model, part);
            if (y.y <= y.x) throw new InvalidDataException("Perfil vertical inválido: " + part.id);
            for (int k = 0; k < count; k++)
            {
                vertices[k] = new Vector3((float)part.vertices[k * 3], (float)(y.x + (y.y - y.x) * part.vertices[k * 3 + 1]), (float)part.vertices[k * 3 + 2]);
                uv[k] = new Vector2(part.uv[k * 2], part.uv[k * 2 + 1]);
                triangles[k] = k;
            }
            var mesh = new Mesh { name = part.id, indexFormat = IndexFormat.UInt32 };
            mesh.vertices = vertices; mesh.uv = uv; mesh.triangles = triangles;
            if (part.materialGuids != null && part.materialGuids.Length > 0 && part.triangleMaterials != null)
            {
                if (part.triangleMaterials.Length != count / 3) throw new InvalidDataException("Submallas incompletas: " + part.id);
                mesh.subMeshCount = part.materialGuids.Length;
                var indices = new List<int>[mesh.subMeshCount];
                for (int k = 0; k < indices.Length; k++) indices[k] = new List<int>();
                for (int k = 0; k < count / 3; k++)
                {
                    int slot = part.triangleMaterials[k];
                    if (slot < 0 || slot >= indices.Length) throw new InvalidDataException("Material fuera de rango: " + part.id);
                    indices[slot].Add(k * 3); indices[slot].Add(k * 3 + 1); indices[slot].Add(k * 3 + 2);
                }
                for (int k = 0; k < indices.Length; k++) mesh.SetTriangles(indices[k], k);
            }
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            return mesh;
        }
        static Transform Group(Transform root, Dictionary<string, Transform> groups, string path)
        {
            if (groups.TryGetValue(path, out var found)) return found;
            int slash = path.LastIndexOf('/');
            Transform parent = slash < 0 ? root : Group(root, groups, path.Substring(0, slash));
            var group = new GameObject(slash < 0 ? path : path.Substring(slash + 1)).transform;
            group.SetParent(parent, false); groups.Add(path, group); return group;
        }
        [MenuItem("Tools/UPCH/Veterinaria/1 Regenerar prefab del edificio")]
        public static void BuildPrefab()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Sal de Play antes de regenerar.");
            Model model = ReadModel();
            Directory.CreateDirectory(Root + "/Generado/Mallas");
            Directory.CreateDirectory(Root + "/Prefabs");
            AssetDatabase.Refresh();
            var materials = new Dictionary<string, Material>();
            foreach (var part in model.items)
              foreach (var guid in part.materialGuids != null && part.materialGuids.Length > 0 ? part.materialGuids : new[] { part.materialGuid })
                if (!materials.ContainsKey(guid))
                {
                    var material = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
                    if (!material) throw new InvalidDataException("Material del proyecto ausente: " + guid);
                    materials.Add(guid, material);
                }
            // Existing root identity is retained, so scene instances keep their anchor.
            bool existing = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            GameObject root = existing ? PrefabUtility.LoadPrefabContents(PrefabPath) : new GameObject(model.rootName);
            try
            {
                root.name = model.rootName;
                while (root.transform.childCount > 0) UnityEngine.Object.DestroyImmediate(root.transform.GetChild(0).gameObject);
                root.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                root.transform.localScale = Vector3.one;
                var groups = new Dictionary<string, Transform>();
                var floorColliders = new List<Collider>();
                for (int k = 0; k < model.items.Length; k++)
                {
                    var part = model.items[k];
                    if (k % 80 == 0) EditorUtility.DisplayProgressBar("Veterinaria", part.group, (float)k / model.items.Length);
                    Mesh mesh = MakeMesh(model, part);
                    string path = Root + "/Generado/Mallas/" + part.id + ".asset";
                    var saved = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                    if (saved)
                    {
                        EditorUtility.CopySerialized(mesh, saved);
                        UnityEngine.Object.DestroyImmediate(mesh);
                        EditorUtility.SetDirty(saved);
                    }
                    else { saved = mesh; AssetDatabase.CreateAsset(saved, path); }
                    var obj = new GameObject(part.id + "_" + part.name);
                    obj.transform.SetParent(Group(root.transform, groups, part.group), false);
                    obj.AddComponent<MeshFilter>().sharedMesh = saved;
                    var renderer = obj.AddComponent<MeshRenderer>(); renderer.sharedMaterial = materials[part.materialGuids != null && part.materialGuids.Length > 0 ? part.materialGuids[0] : part.materialGuid];
                    if (part.materialGuids != null && part.materialGuids.Length > 0)
                        renderer.sharedMaterials = Array.ConvertAll(part.materialGuids, guid => materials[guid]);
                    renderer.enabled = !part.hidden;
                    if (part.hidden) obj.tag = "EditorOnly";
                    if (part.material == "glass") renderer.shadowCastingMode = ShadowCastingMode.Off;
                    if (part.role == "door" && part.doorHinge != null && part.doorHinge.Length == 3)
                    {
                        var collision = obj.AddComponent<MeshCollider>();
                        collision.sharedMesh = saved;
                        collision.convex = true;
                        var door = obj.AddComponent<UPCH.Veterinaria.VeterinariaDoor>();
                        door.hinge = new Vector3(part.doorHinge[0], part.doorHinge[1], part.doorHinge[2]);
                        door.openDegrees = part.doorOpenDegrees;
                    }
                    else if (part.collider)
                    {
                        var collider = obj.AddComponent<MeshCollider>(); collider.sharedMesh = saved;
                        if (part.material == "floor") floorColliders.Add(collider);
                    }
                    obj.SetActive(part.active);
                }
                var teleport = root.GetComponent<TeleportationArea>();
                if (!teleport) teleport = root.AddComponent<TeleportationArea>();
                teleport.colliders.Clear(); teleport.colliders.AddRange(floorColliders);
                var serializedTeleport = new SerializedObject(teleport);
                var layers = serializedTeleport.FindProperty("m_InteractionLayers.m_Bits");
                if (layers != null) layers.intValue = unchecked((int)0x80000000);
                serializedTeleport.ApplyModifiedPropertiesWithoutUndo();
                var savedPrefab = PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
                if (!savedPrefab) throw new InvalidOperationException("No se pudo guardar el prefab H; no se eliminan mallas.");
                var keepMeshes = new HashSet<string>();
                foreach (var part in model.items) keepMeshes.Add(Root + "/Generado/Mallas/" + part.id + ".asset");
                foreach (var meshGuid in AssetDatabase.FindAssets("t:Mesh", new[] { Root + "/Generado/Mallas" }))
                {
                    string meshPath = AssetDatabase.GUIDToAssetPath(meshGuid);
                    if (Path.GetFileName(meshPath).StartsWith("H_", StringComparison.Ordinal) && !keepMeshes.Contains(meshPath))
                        AssetDatabase.DeleteAsset(meshPath);
                }
                AssetDatabase.SaveAssets();
                Debug.Log("Veterinaria: prefab regenerado con " + model.items.Length + " piezas. Los NPT se conservaron; revisar los parámetros estimados y ejecutar las pruebas de recorrido.");
            }
            finally
            {
                EditorUtility.ClearProgressBar();
                if (existing) PrefabUtility.UnloadPrefabContents(root); else UnityEngine.Object.DestroyImmediate(root);
            }
        }
        [MenuItem("Tools/UPCH/Veterinaria/2 Integrar o actualizar en Campus")]
        public static void Integrate()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Sal de Play antes de integrar.");
            var scene = SceneManager.GetActiveScene();
            if (scene.path != "Assets/UPCH/Scenes/Campus.unity") throw new InvalidOperationException("Abre la escena Campus del proyecto antes de integrar.");
            var model = ReadModel(); var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
            if (!prefab) throw new FileNotFoundException("Falta el prefab de Veterinaria.");
            GameObject root = null, baseRoot = null, old = null; MeshFilter ground = null;
            foreach (var obj in scene.GetRootGameObjects())
            {
                if (obj.name == "Campus UPCH - Base exterior") baseRoot = obj;
                foreach (var t in obj.GetComponentsInChildren<Transform>(true))
                {
                    if (t.name == model.rootName) root = t.gameObject;
                    if (t.name == "Terreno") ground = t.GetComponent<MeshFilter>();
                    if (t.name == "H - Medicina Veterinaria y Zootecnia") old = t.gameObject;
                }
            }
            if (!baseRoot || !ground) throw new InvalidOperationException("No se encontraron la base exterior y su terreno en Campus.");
            if (!root)
            {
                root = (GameObject)PrefabUtility.InstantiatePrefab(prefab, baseRoot.transform);
                Undo.RegisterCreatedObjectUndo(root, "Integrar Veterinaria");
            }
            Undo.RecordObject(root.transform, "Anclar Veterinaria");
            root.transform.SetPositionAndRotation(new Vector3(model.anchor[0], model.anchor[1], model.anchor[2]), Quaternion.Euler(0, model.yaw, 0));
            root.transform.localScale = Vector3.one;
            if (old) { Undo.RecordObject(old, "Conservar reserva H desactivada"); old.SetActive(false); }
            MeshFilter cutter = null;
            foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
                if (filter.name.Contains("Excavacion_H_Verificada")) cutter = filter;
            if (!cutter) throw new InvalidOperationException("Falta la envolvente de excavación en el prefab H.");
            var source = AssetDatabase.LoadAssetAtPath<Mesh>("Assets/UPCH/Campus/Generated/Meshes/Site.asset");
            var cut = AssetDatabase.LoadAssetAtPath<Mesh>(Root + "/Generado/Terreno_Recortado_H.asset");
            VeterinariaTerreno.RegisterKnownMeshes(ground, source, cut);
            VeterinariaTerreno.Apply(ground, cutter);
            EditorSceneManager.MarkSceneDirty(scene);
            Selection.activeGameObject = root;
            Debug.Log("Veterinaria: ancla actualizada, reserva H conservada desactivada y terreno recortado en superficie y colisión. Guarda Campus tras revisar los accesos.", root);
        }
        [MenuItem("Tools/UPCH/Veterinaria/3 Comprobar referencias y escala")]
        public static void Validate()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Comprueba la geometria en Edit; las hojas cambian de pose durante Play.");
            var model = ReadModel();
            GameObject root = null; int roots = 0;
            foreach (var r in SceneManager.GetActiveScene().GetRootGameObjects())
                foreach (var t in r.GetComponentsInChildren<Transform>(true)) if (t.name == model.rootName) { root = t.gameObject; roots++; }
            if (!root) throw new InvalidOperationException("No está el edificio H en la escena activa.");
            int missing = 0, meshes = 0, colliders = 0;
            if (roots != 1) { missing++; Debug.LogError("Se encontraron " + roots + " raices H; revisar instancias duplicadas antes de corregir geometria."); }
            var expected = new HashSet<string>(); var actual = new HashSet<string>();
            var expectedParts = new Dictionary<string, Part>();
            foreach (var part in model.items) expectedParts[part.id] = part;
            foreach (var part in model.items) expected.Add(part.id);
            if ((root.transform.lossyScale - Vector3.one).sqrMagnitude > 1e-8f) { missing++; Debug.LogError("H no conserva escala unitaria."); }
            foreach (var f in root.GetComponentsInChildren<MeshFilter>(true))
            {
                meshes++;
                if (!f.sharedMesh) { missing++; continue; }
                if (!actual.Add(f.sharedMesh.name)) { missing++; Debug.LogWarning("Malla H repetida en la escena: " + f.sharedMesh.name, f); }
                if (f.transform.localPosition.sqrMagnitude > 1e-8f || Quaternion.Angle(f.transform.localRotation, Quaternion.identity) > .001f || (f.transform.localScale - Vector3.one).sqrMagnitude > 1e-8f)
                { missing++; Debug.LogWarning("Pieza con transformacion local distinta de la generada; revisar override: " + f.name, f); }
                if (expectedParts.TryGetValue(f.sharedMesh.name, out var source))
                {
                    var actualVertices = f.sharedMesh.vertices;
                    bool changedGeometry = actualVertices.Length != source.vertices.Length / 3;
                    var profile = Height(model, source);
                    var toBuilding = root.transform.worldToLocalMatrix * f.transform.localToWorldMatrix;
                    if (!changedGeometry) for (int vertex = 0; vertex < actualVertices.Length; vertex++)
                    {
                        var expectedVertex = new Vector3((float)source.vertices[vertex * 3], (float)(profile.x + (profile.y - profile.x) * source.vertices[vertex * 3 + 1]), (float)source.vertices[vertex * 3 + 2]);
                        if ((toBuilding.MultiplyPoint3x4(actualVertices[vertex]) - expectedVertex).sqrMagnitude > .000001f)
                        { changedGeometry = true; break; }
                    }
                    if (changedGeometry) { missing++; Debug.LogError("Geometria o grupo desplazado respecto al modelo: " + f.name, f); }
                }
                var collision = f.GetComponent<MeshCollider>();
                if (expectedParts.TryGetValue(f.sharedMesh.name, out var collisionSource) && collisionSource.collider && (!collision || !collision.enabled))
                { missing++; Debug.LogError("Falta colision prevista en el modelo: " + f.name, f); }
                if (collision && collision.sharedMesh != f.sharedMesh) { missing++; Debug.LogWarning("Collider y malla visual distintos: " + f.name, f); }
                if (expectedParts.TryGetValue(f.sharedMesh.name, out var expectedDoor) && expectedDoor.role == "door")
                {
                    var door = f.GetComponent<UPCH.Veterinaria.VeterinariaDoor>();
                    if (!door || !collision || !collision.enabled || !collision.convex || collision.isTrigger || collision.sharedMesh != f.sharedMesh)
                    { missing++; Debug.LogError("Puerta sin apertura o colision coherente: " + f.name, f); }
                }
            }
            foreach (var id in expected) if (!actual.Contains(id)) { missing++; Debug.LogWarning("Pieza del modelo ausente en la instancia: " + id, root); }
            foreach (var id in actual) if (!expected.Contains(id)) { missing++; Debug.LogWarning("Pieza ajena a esta revision dentro de H: " + id, root); }
            foreach (var c in root.GetComponentsInChildren<MeshCollider>(true)) { colliders++; if (!c.sharedMesh || c.isTrigger || (c.convex && !c.GetComponent<UPCH.Veterinaria.VeterinariaDoor>())) missing++; }
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
                foreach (var m in r.sharedMaterials) if (!m || !m.shader || !m.shader.isSupported) missing++;
            if (model.entryAnnexProbeXZ != null && model.entryAnnexProbeXZ.Length > 0)
            {
                Physics.SyncTransforms();
                var floorIds = new HashSet<string>();
                foreach (var part in model.items) if (part.collider && part.material == "floor") floorIds.Add(part.id);
                var surfaces = root.GetComponentsInChildren<MeshCollider>(false);
                int supported = 0, probes = model.entryAnnexProbeXZ.Length / 2;
                for (int k = 0; k < probes; k++)
                {
                    var local = new Vector3((float)model.entryAnnexProbeXZ[k * 2], .05f, (float)model.entryAnnexProbeXZ[k * 2 + 1]);
                    var ray = new Ray(root.transform.TransformPoint(local), root.transform.TransformDirection(Vector3.down));
                    bool found = false;
                    foreach (var surface in surfaces)
                        if (surface.enabled && surface.sharedMesh && floorIds.Contains(surface.sharedMesh.name) && surface.Raycast(ray, out var hit, .10f))
                        { found = true; break; }
                    if (found) supported++;
                    else { missing++; Debug.LogError("Cubierta del ingreso sin apoyo en la muestra " + (k + 1) + ": " + local, root); }
                }
                Debug.Log("Cubierta del ingreso: " + supported + "/" + probes + " muestras con collider en NPT +0.00. No sustituye el recorrido Play.", root);
            }
            Debug.Log($"Veterinaria {model.revision}: {meshes} mallas, {colliders} colisiones, {missing} referencias/configuraciones observadas. La revisión no sustituye comprobar accesos y recorrer las tres escaleras en Play.", root);
        }
    }
}
