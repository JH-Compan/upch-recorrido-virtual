using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace UPCH.Presentacion.Editable
{
    public static class UPCHCreateEditable
    {
        const string Base = "Assets/UPCH/Edificio/";
        const string RootName = "Edificio_A";
        [Serializable] public class Level { public string name; public float elevation; }
        [Serializable] public class Pivot { public string path; public float[] position; }
        [Serializable] public class Part
        {
            public string id, name, group, kind, materialGuid, source, note;
            public float[] position, scale, rotation, vertices, normals, uv;
            public bool collider, active;
        }
        [Serializable] public class Plan
        {
            public int schema;
            public float[] origin;
            public Level[] levels;
            public Pivot[] pivots;
            public Part[] items;
        }
        static Vector3 V(float[] a) { return new Vector3(a[0], a[1], a[2]); }

        [MenuItem("Tools/UPCH/Preparar edificio")]
        public static void Create()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) { Debug.LogError("UPCH: sal de Play."); return; }
            var scene = SceneManager.GetActiveScene();
            GameObject previous = null;
            foreach (var obj in scene.GetRootGameObjects())
            {
                if (obj.name == RootName) { Debug.LogError("UPCH: el modelo editable ya existe. Editalo directamente; no es necesario regenerarlo."); return; }
                if (obj.name == "Edificio_A_Pendiente") previous = obj;
            }
            if (previous == null) { Debug.LogError("UPCH: abre Campus con su edificio actual antes de crear el editable."); return; }
            var plan = JsonUtility.FromJson<Plan>(File.ReadAllText("Assets/UPCH/Editor/EdificioDatos.json"));
            if (plan == null || plan.schema != 1 || plan.items == null || plan.items.Length == 0)
                throw new InvalidDataException("Datos editables incompletos.");
            var materials = new Dictionary<string, Material>();
            var ids = new HashSet<string>();
            foreach (var item in plan.items)
            {
                if (!ids.Add(item.id)) throw new InvalidDataException("ID repetido: " + item.id);
                if (!materials.ContainsKey(item.materialGuid))
                {
                    var material = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(item.materialGuid));
                    if (material == null) throw new InvalidDataException("Material del proyecto no encontrado: " + item.materialGuid);
                    materials.Add(item.materialGuid, material);
                }
            }
            string backup = Path.Combine("Library", "UPCHRespaldoInicial", DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));
            Directory.CreateDirectory(backup);
            if (!string.IsNullOrEmpty(scene.path)) File.Copy(scene.path, Path.Combine(backup, "Campus.unity"));
            if (!AssetDatabase.IsValidFolder(Base + "MallasEditables")) AssetDatabase.CreateFolder("Assets/UPCH/Edificio", "MallasEditables");
            var root = new GameObject(RootName);
            SceneManager.MoveGameObjectToScene(root, scene);
            root.transform.position = previous.transform.position;
            root.transform.rotation = previous.transform.rotation;
            root.transform.localScale = previous.transform.localScale;
            var groups = new Dictionary<string, Transform>();
            var meshPaths = new List<string>();
            bool success = false;
            try
            {
                foreach (var level in plan.levels) Group(root.transform, groups, level.name).localPosition = new Vector3(0, level.elevation, 0);
                foreach (var pivot in plan.pivots) Group(root.transform, groups, pivot.path).localPosition = V(pivot.position);
                AssetDatabase.StartAssetEditing();
                try
                {
                    for (int k = 0; k < plan.items.Length; k++)
                    {
                        var item = plan.items[k];
                        if (k % 100 == 0) EditorUtility.DisplayProgressBar("UPCH - Modelo editable", item.group, (float)k / plan.items.Length);
                        GameObject obj;
                        if (item.kind == "cube") obj = GameObject.CreatePrimitive(PrimitiveType.Cube);
                        else
                        {
                            obj = new GameObject();
                            var mesh = MakeMesh(item);
                            string path = Base + "MallasEditables/" + item.id + ".asset";
                            AssetDatabase.CreateAsset(mesh, path);
                            meshPaths.Add(path);
                            obj.AddComponent<MeshFilter>().sharedMesh = mesh;
                            obj.AddComponent<MeshRenderer>();
                            if (item.collider) obj.AddComponent<MeshCollider>().sharedMesh = mesh;
                        }
                        obj.name = item.id + "_" + item.name;
                        obj.transform.SetParent(Group(root.transform, groups, item.group), false);
                        obj.transform.localPosition = V(item.position);
                        obj.transform.localScale = V(item.scale);
                        obj.transform.localRotation = new Quaternion(item.rotation[0], item.rotation[1], item.rotation[2], item.rotation[3]);
                        obj.GetComponent<MeshRenderer>().sharedMaterial = materials[item.materialGuid];
                        if (item.kind == "cube" && !item.collider) UnityEngine.Object.DestroyImmediate(obj.GetComponent<BoxCollider>());
                        obj.SetActive(item.active || item.group == "Nivel_02/Barandillas_Descartadas");
                    }
                }
                finally { AssetDatabase.StopAssetEditing(); }
                if (groups.TryGetValue("Nivel_02/Barandillas_Descartadas", out var discardedRails)) discardedRails.gameObject.SetActive(false);
                AssetDatabase.SaveAssets();
                // Check the custom meshes after Unity imports its own assets.
                foreach (var path in meshPaths)
                {
                    var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                    if (mesh == null || !mesh.isReadable || mesh.vertices.Length == 0)
                        throw new InvalidDataException("Malla editable no legible: " + path);
                }
                Undo.RegisterCreatedObjectUndo(root, "Preparar edificio UPCH");
                Undo.DestroyObjectImmediate(previous);
                EditorSceneManager.MarkSceneDirty(scene);
                Selection.activeGameObject = root;
                if (SceneView.lastActiveSceneView != null) SceneView.lastActiveSceneView.FrameSelected();
                success = true;
                Debug.Log("UPCH: edificio preparado con " + plan.items.Length + " piezas. Guarda la escena con Ctrl+S. Las piezas son editables desde Inspector.");
                EditorUtility.DisplayDialog("Modelo editable", plan.items.Length + " piezas independientes creadas. Guarda con Ctrl+S. Edita los hijos de Edificio_A en Inspector. No vuelvas a ejecutar el generador para aplicar cambios.", "Aceptar");
            }
            catch (Exception error)
            {
                Debug.LogException(error);
                EditorUtility.DisplayDialog("Modelo editable", "No se completo la creacion. La escena original se conserva en el respaldo automatico. Comparte el error de Console: " + error.Message, "Aceptar");
            }
            finally
            {
                EditorUtility.ClearProgressBar();
                if (!success && root != null) UnityEngine.Object.DestroyImmediate(root);
            }
        }

        static Transform Group(Transform root, Dictionary<string, Transform> groups, string path)
        {
            if (groups.TryGetValue(path, out var result)) return result;
            int slash = path.LastIndexOf('/');
            var parent = slash < 0 ? root : Group(root, groups, path.Substring(0, slash));
            result = new GameObject(slash < 0 ? path : path.Substring(slash + 1)).transform;
            result.SetParent(parent, false);
            groups.Add(path, result);
            return result;
        }

        static Mesh MakeMesh(Part part)
        {
            int n = part.vertices.Length / 3;
            if (n == 0 || n % 3 != 0 || part.normals.Length != n * 3 || part.uv.Length != n * 2)
                throw new InvalidDataException("Datos de pieza incorrectos: " + part.id);
            var vertices = new Vector3[n];
            var normals = new Vector3[n];
            var uv = new Vector2[n];
            var indices = new int[n];
            for (int i = 0; i < n; i++)
            {
                vertices[i] = new Vector3(part.vertices[i*3], part.vertices[i*3+1], part.vertices[i*3+2]);
                normals[i] = new Vector3(part.normals[i*3], part.normals[i*3+1], part.normals[i*3+2]);
                uv[i] = new Vector2(part.uv[i*2], part.uv[i*2+1]);
                indices[i] = i;
            }
            var mesh = new Mesh { name = part.id, indexFormat = IndexFormat.UInt32 };
            mesh.vertices = vertices;
            mesh.normals = normals;
            mesh.uv = uv;
            mesh.SetIndices(indices, MeshTopology.Triangles, 0, true);
            mesh.RecalculateBounds();
            return mesh;
        }
    }
}
