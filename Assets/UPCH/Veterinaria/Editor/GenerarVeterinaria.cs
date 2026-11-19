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
            public float slabThickness = .24f, doorHeight = 2.15f, windowSill = .95f,
                windowHead = 2.50f, roofWallHeight = 2.60f, beamDepth = .40f, railingHeight = 1.10f;
        }
        [Serializable] public class Part
        {
            public string id, name, group, materialGuid, material, role, source, note;
            public string[] materialGuids;
            public int[] triangleMaterials;
            public bool collider, active, hidden;
            public int level;
            public float bottom, top;
            public float[] vertices, normals, uv;
        }
        [Serializable] public class Model
        {
            public int schema;
            public string rootName, baseCommit, sourcePdfSha256;
            public float[] anchor, npt;
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
        static Vector2 Height(Model m, Part p)
        {
            float y = m.npt[p.level];
            float h = p.level < 4 ? m.npt[p.level + 1] - y - m.parameters.slabThickness : m.parameters.roofWallHeight;
            switch (p.role)
            {
                case "wall": return new Vector2(y, y + h);
                case "slab": return new Vector2(y - m.parameters.slabThickness, y);
                case "sill": return new Vector2(y, y + m.parameters.windowSill);
                case "glass": return new Vector2(y + m.parameters.windowSill, y + m.parameters.windowHead);
                case "windowLintel": return new Vector2(y + m.parameters.windowHead, y + h);
                case "doorLintel": return new Vector2(y + m.parameters.doorHeight, y + h);
                case "door": return new Vector2(y + .025f, y + m.parameters.doorHeight - .025f);
                case "beam": return new Vector2(y + h - m.parameters.beamDepth, y + h);
                case "railing": return new Vector2(y, y + m.parameters.railingHeight);
                case "roofCover": return new Vector2(y + m.parameters.roofWallHeight, y + m.parameters.roofWallHeight + .14f);
                default: return new Vector2(p.bottom, p.top);
            }
        }
        static Mesh MakeMesh(Model model, Part part)
        {
            int count = part.vertices.Length / 3;
            var vertices = new Vector3[count]; var uv = new Vector2[count]; var triangles = new int[count];
            Vector2 y = Height(model, part);
            if (y.y <= y.x) throw new InvalidDataException("Perfil vertical inválido: " + part.id);
            for (int k = 0; k < count; k++)
            {
                vertices[k] = new Vector3(part.vertices[k * 3], Mathf.LerpUnclamped(y.x, y.y, part.vertices[k * 3 + 1]), part.vertices[k * 3 + 2]);
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
                    if (part.collider)
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
                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
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
            var model = ReadModel();
            GameObject root = null;
            foreach (var r in SceneManager.GetActiveScene().GetRootGameObjects())
                foreach (var t in r.GetComponentsInChildren<Transform>(true)) if (t.name == model.rootName) root = t.gameObject;
            if (!root) throw new InvalidOperationException("No está el edificio H en la escena activa.");
            int missing = 0, meshes = 0, colliders = 0;
            if ((root.transform.lossyScale - Vector3.one).sqrMagnitude > 1e-8f) { missing++; Debug.LogError("H no conserva escala unitaria."); }
            foreach (var f in root.GetComponentsInChildren<MeshFilter>(true)) { meshes++; if (!f.sharedMesh) missing++; }
            foreach (var c in root.GetComponentsInChildren<MeshCollider>(true)) { colliders++; if (!c.sharedMesh || c.convex || c.isTrigger) missing++; }
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
                foreach (var m in r.sharedMaterials) if (!m || !m.shader || !m.shader.isSupported) missing++;
            Debug.Log($"Veterinaria: {meshes} mallas, {colliders} colisiones, {missing} referencias/configuraciones observadas. La revisión no sustituye comprobar accesos y recorrer las tres escaleras en Play.", root);
        }
    }
}
