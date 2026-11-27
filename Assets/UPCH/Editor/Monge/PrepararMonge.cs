// Pabellon B - Integracion independiente para el campus UPCH.
// Reutiliza la estructura Plan/Level/Part y los materiales del edificio A.
#if UNITY_EDITOR
using System;
using System.IO;
using System.Collections.Generic;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace UPCH.Presentacion.Editable.Monge
{
    public static class PrepararMonge
    {
        private const string DataPath = "Assets/UPCH/Editor/Monge/EdificioBDatos.json";
        private const string OutputParent = "Assets/UPCH/Arte/Edificios/B";
        private const string RootName = "Edificio_B";
        private const string BaseMeshGuid = "f907311fb019a294d8089a847bffcb82";

        [Serializable] public class Level { public string name; public float elevation; }
        [Serializable] public class Part
        {
            public string id, name, group, kind, materialGuid, source, note;
            public float[] position, scale, rotation, vertices, normals, uv;
            public bool collider, active;
        }
        [Serializable] public class Plan
        {
            public int schema;
            public string building, status;
            public float[] origin;
            public Level[] levels;
            public Part[] items;
        }
        private static Vector3 V(float[] v) { return new Vector3(v[0], v[1], v[2]); }

        [MenuItem("Tools/UPCH/Monge/Preparar pabellon B en Campus")]
        public static void Create()
        {
            GameObject root = null;
            GameObject previous = null;
            string generatedFolder = null;
            bool previousActive = true;
            bool success = false;
            try
            {
                if (EditorApplication.isPlayingOrWillChangePlaymode)
                    throw new InvalidOperationException("Sal del modo Play antes de preparar el edificio.");
                if (PrefabStageUtility.GetCurrentPrefabStage() != null)
                    throw new InvalidOperationException("Vuelve a la escena Campus; no ejecutes esto dentro del editor de prefabs.");
                Scene scene = SceneManager.GetActiveScene();
                if (!scene.IsValid() || !scene.isLoaded || string.IsNullOrEmpty(scene.path))
                    throw new InvalidOperationException("Abre y guarda la escena Campus antes de continuar.");
                foreach (GameObject obj in scene.GetRootGameObjects())
                    foreach (Transform t in obj.GetComponentsInChildren<Transform>(true))
                        if (t.name == RootName)
                            throw new InvalidOperationException("Edificio_B ya existe. Edita sus piezas; no necesitas regenerarlo.");
                var candidates = new List<GameObject>();
                string meshPath = AssetDatabase.GUIDToAssetPath(BaseMeshGuid);
                Mesh expectedMesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
                if (expectedMesh == null)
                    throw new InvalidDataException("No se encontro BuildingB.asset del campus original. Revisa que estas en la rama del campus.");
                foreach (GameObject obj in scene.GetRootGameObjects())
                    foreach (MeshFilter filter in obj.GetComponentsInChildren<MeshFilter>(true))
                        if (filter.sharedMesh == expectedMesh) candidates.Add(filter.gameObject);
                if (candidates.Count != 1)
                    throw new InvalidDataException("Se esperaba un unico volumen base BuildingB en la escena. Encontrados: " + candidates.Count);
                previous = candidates[0];
                previousActive = previous.activeSelf;
                if (!previousActive)
                    throw new InvalidOperationException("El volumen base B ya esta desactivado. Revisa si ya existe otro modelo Monge antes de continuar.");
                if (Vector3.Distance(previous.transform.localScale, Vector3.one) > 0.001f)
                    throw new InvalidOperationException("El volumen base B no tiene escala 1,1,1. Revisa su Transform antes de integrar.");
                if (!File.Exists(DataPath)) throw new FileNotFoundException("Falta el archivo de geometria del Monge.", DataPath);
                Plan plan = JsonUtility.FromJson<Plan>(File.ReadAllText(DataPath));
                Dictionary<string, Material> materials = Validate(plan);

                // Snapshot on disk for reference; the current scene is saved only by the user.
                string backup = Path.Combine("Library", "UPCHRespaldoMonge", DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fff"));
                Directory.CreateDirectory(backup);
                File.Copy(scene.path, Path.Combine(backup, Path.GetFileName(scene.path)));
                EnsureFolder(OutputParent);
                generatedFolder = AssetDatabase.GenerateUniqueAssetPath(OutputParent + "/MongeEditable");
                AssetDatabase.CreateFolder(OutputParent, Path.GetFileName(generatedFolder));
                AssetDatabase.CreateFolder(generatedFolder, "Mallas");
                root = new GameObject(RootName);
                SceneManager.MoveGameObjectToScene(root, scene);
                root.transform.SetParent(previous.transform.parent, false);
                root.transform.localPosition = previous.transform.localPosition;
                root.transform.localRotation = previous.transform.localRotation;
                root.transform.localScale = previous.transform.localScale;
                var groups = new Dictionary<string, Transform>();
                foreach (Level level in plan.levels)
                    Group(root.transform, groups, level.name).localPosition = new Vector3(0, level.elevation, 0);
                AssetDatabase.StartAssetEditing();
                try
                {
                    for (int i = 0; i < plan.items.Length; i++)
                    {
                        Part item = plan.items[i];
                        if (i % 50 == 0) EditorUtility.DisplayProgressBar("UPCH - Pabellon B", item.group, (float)i / plan.items.Length);
                        Mesh mesh = MakeMesh(item);
                        AssetDatabase.CreateAsset(mesh, generatedFolder + "/Mallas/" + item.id + ".asset");
                        var obj = new GameObject(item.id + "_" + item.name);
                        obj.transform.SetParent(Group(root.transform, groups, item.group), false);
                        obj.transform.localPosition = V(item.position);
                        obj.transform.localScale = V(item.scale);
                        obj.transform.localRotation = new Quaternion(item.rotation[0], item.rotation[1], item.rotation[2], item.rotation[3]);
                        obj.AddComponent<MeshFilter>().sharedMesh = mesh;
                        obj.AddComponent<MeshRenderer>().sharedMaterial = materials[item.materialGuid];
                        if (item.collider)
                        {
                            MeshCollider collider = obj.AddComponent<MeshCollider>();
                            collider.sharedMesh = mesh;
                            collider.convex = false;
                        }
                        obj.SetActive(item.active);
                        GameObjectUtility.SetStaticEditorFlags(obj, StaticEditorFlags.BatchingStatic);
                    }
                }
                finally { AssetDatabase.StopAssetEditing(); }
                AssetDatabase.SaveAssets();
                foreach (Part item in plan.items)
                {
                    Mesh mesh = AssetDatabase.LoadAssetAtPath<Mesh>(generatedFolder + "/Mallas/" + item.id + ".asset");
                    if (mesh == null || mesh.vertexCount == 0)
                        throw new InvalidDataException("La malla no se importo correctamente: " + item.id);
                }
                bool prefabSaved;
                PrefabUtility.SaveAsPrefabAssetAndConnect(root, generatedFolder + "/Monge.prefab", InteractionMode.AutomatedAction, out prefabSaved);
                if (!prefabSaved) throw new IOException("No se pudo guardar Monge.prefab.");
                Undo.IncrementCurrentGroup();
                int undoGroup = Undo.GetCurrentGroup();
                Undo.SetCurrentGroupName("Integrar pabellon B Monge");
                Undo.RegisterCreatedObjectUndo(root, "Crear Edificio_B");
                Undo.RecordObject(previous, "Ocultar volumen base B");
                previous.SetActive(false);
                if (PrefabUtility.IsPartOfPrefabInstance(previous))
                    PrefabUtility.RecordPrefabInstancePropertyModifications(previous);
                Undo.CollapseUndoOperations(undoGroup);
                EditorSceneManager.MarkSceneDirty(scene);
                Selection.activeGameObject = root;
                if (SceneView.lastActiveSceneView != null) SceneView.lastActiveSceneView.FrameSelected();
                success = true;
                Debug.Log("UPCH Monge: " + plan.items.Length + " piezas integradas en " + root.transform.position + ". Prefab: " + generatedFolder + "/Monge.prefab. Niveles B: 0 / 3.35 / 6.70 m. Revisa el resultado y guarda con Ctrl+S.");
                EditorUtility.DisplayDialog("Monge integrado", "Edificio_B creado con materiales del campus. El volumen base B se ha desactivado y se conserva. Revisa posicion, accesos y colisiones; guarda la escena con Ctrl+S cuando termines.", "Aceptar");
            }
            catch (Exception error)
            {
                Debug.LogException(error);
                EditorUtility.DisplayDialog("No se pudo integrar Monge", error.Message, "Aceptar");
            }
            finally
            {
                EditorUtility.ClearProgressBar();
                if (!success)
                {
                    if (previous != null && previous.activeSelf != previousActive)
                    {
                        previous.SetActive(previousActive);
                        if (PrefabUtility.IsPartOfPrefabInstance(previous)) PrefabUtility.RecordPrefabInstancePropertyModifications(previous);
                    }
                    if (root != null) UnityEngine.Object.DestroyImmediate(root);
                    // Only this run's newly-created folder can be deleted on failure.
                    if (!string.IsNullOrEmpty(generatedFolder)) AssetDatabase.DeleteAsset(generatedFolder);
                }
            }
        }

        private static Dictionary<string, Material> Validate(Plan plan)
        {
            if (plan == null || plan.schema != 1 || plan.building != "B" || plan.items == null || plan.items.Length == 0 || plan.levels == null)
                throw new InvalidDataException("EdificioBDatos.json es incompleto o no corresponde al B.");
            var materials = new Dictionary<string, Material>();
            var ids = new HashSet<string>();
            var levels = new HashSet<string>();
            foreach (Level level in plan.levels)
            {
                if (!levels.Add(level.name) || !Finite(level.elevation)) throw new InvalidDataException("Nivel invalido.");
            }
            foreach (Part item in plan.items)
            {
                if (string.IsNullOrEmpty(item.id) || !ids.Add(item.id) || item.id.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0)
                    throw new InvalidDataException("ID de pieza repetido o invalido.");
                if (item.kind != "mesh" || item.vertices == null || item.vertices.Length == 0 || item.vertices.Length % 9 != 0 || item.normals == null || item.normals.Length != item.vertices.Length || item.uv == null || item.uv.Length != item.vertices.Length / 3 * 2)
                    throw new InvalidDataException("Geometria incompleta: " + item.id);
                if (item.position == null || item.position.Length != 3 || item.scale == null || item.scale.Length != 3 || item.rotation == null || item.rotation.Length != 4)
                    throw new InvalidDataException("Transform incompleto: " + item.id);
                if (string.IsNullOrEmpty(item.group) || !levels.Contains(item.group.Split('/')[0]))
                    throw new InvalidDataException("Grupo fuera de los niveles permitidos: " + item.id);
                foreach (float[] values in new[] { item.vertices, item.normals, item.uv, item.position, item.scale, item.rotation })
                    foreach (float value in values) if (!Finite(value)) throw new InvalidDataException("Coordenada no finita: " + item.id);
                if (string.IsNullOrEmpty(item.materialGuid)) throw new InvalidDataException("Falta el material: " + item.id);
                if (!materials.ContainsKey(item.materialGuid))
                {
                    Material material = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(item.materialGuid));
                    if (material == null) throw new InvalidDataException("Falta un material compartido del campus: " + item.materialGuid);
                    materials.Add(item.materialGuid, material);
                }
            }
            return materials;
        }
        private static bool Finite(float n) { return !float.IsNaN(n) && !float.IsInfinity(n); }
        private static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            int slash = path.LastIndexOf('/');
            string parent = path.Substring(0, slash);
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, path.Substring(slash + 1));
        }
        private static Transform Group(Transform root, Dictionary<string, Transform> groups, string path)
        {
            Transform result;
            if (groups.TryGetValue(path, out result)) return result;
            int slash = path.LastIndexOf('/');
            Transform parent = slash < 0 ? root : Group(root, groups, path.Substring(0, slash));
            result = new GameObject(slash < 0 ? path : path.Substring(slash + 1)).transform;
            result.SetParent(parent, false);
            groups.Add(path, result);
            return result;
        }
        private static Mesh MakeMesh(Part part)
        {
            int count = part.vertices.Length / 3;
            var vertices = new Vector3[count];
            var normals = new Vector3[count];
            var uv = new Vector2[count];
            var indices = new int[count];
            for (int i = 0; i < count; i++)
            {
                vertices[i] = new Vector3(part.vertices[3*i], part.vertices[3*i+1], part.vertices[3*i+2]);
                normals[i] = new Vector3(part.normals[3*i], part.normals[3*i+1], part.normals[3*i+2]);
                uv[i] = new Vector2(part.uv[2*i], part.uv[2*i+1]);
                indices[i] = i;
            }
            var mesh = new Mesh { name = part.id };
            if (count > 65535) mesh.indexFormat = IndexFormat.UInt32;
            mesh.vertices = vertices;
            mesh.normals = normals;
            mesh.uv = uv;
            mesh.SetIndices(indices, MeshTopology.Triangles, 0, true);
            mesh.RecalculateBounds();
            return mesh;
        }
    }
}
#endif
