using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UPCH.TerrenoCampusR1.Editor
{
    public sealed class AplicarTerrenoParqueR1 : EditorWindow
    {
        const string DataPath = "Assets/UPCH/TerrenoCampusR1/Datos/Aplicacion_Terreno_R1.json";
        [Serializable] public class Binding
        {
            public string name, oldGuid, newGuid, oldHash;
            public float[] worldMatrix;
        }
        [Serializable] public class Sample { public float x, y, z; }
        [Serializable] public class Model { public string revision, datum, joins, reserved; public Binding[] bindings; public Sample[] samplesWorld; }
        sealed class Change
        {
            public MeshFilter filter;
            public MeshCollider collider;
            public Mesh mesh;
        }

        [MenuItem("Tools/UPCH/Terreno/Parque Central R1")]
        public static void Open()
        {
            var window = GetWindow<AplicarTerrenoParqueR1>("Terreno Parque R1");
            window.minSize = new Vector2(480, 430);
        }

        void OnGUI()
        {
            EditorGUILayout.LabelField("Parque Central: candidato de relieve R1", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Plataforma central +0,45 m y vereda -0,34 m en el datum de trabajo del parque. " +
                "Eje norte al 8 %. Los demás empalmes están interpolados; algunos superan el 8 % y requieren revisión. " +
                "La plataforma +1,40 m y los accesos propios de Medicina/CREA quedan pendientes.", MessageType.Warning);
            EditorGUILayout.LabelField("Abrir Campus. Aplicar sustituye mallas de suelo y jardines reconocidas, conservando objetos, " +
                "materiales, edificios y vacíos existentes. No guarda automáticamente la escena. Se puede deshacer.", EditorStyles.wordWrappedLabel);
            using (new EditorGUI.DisabledScope(EditorApplication.isPlayingOrWillChangePlaymode))
            {
                if (GUILayout.Button("Aplicar relieve R1 a la escena abierta")) Apply(false);
                if (GUILayout.Button("Restaurar las mallas anteriores")) Apply(true);
                if (GUILayout.Button("Comprobar asignaciones de suelo y colisión")) Check();
            }
            EditorGUILayout.Space();
            EditorGUILayout.LabelField("Después: comprobar vereda hacia H/I/J, conexiones con edificios, jardines y los accesos " +
                "al sótano. Recorrer en Play antes de guardar. Las alturas de edificios no se ajustan automáticamente.", EditorStyles.wordWrappedLabel);
        }

        static Model Read()
        {
            var model = JsonUtility.FromJson<Model>(File.ReadAllText(DataPath));
            if (model == null || model.bindings == null || model.bindings.Length != 9 || model.samplesWorld == null || model.samplesWorld.Length != 83)
                throw new InvalidDataException("Datos R1 incompletos.");
            return model;
        }

        static string MeshHash(Mesh mesh)
        {
            if (!mesh.isReadable) throw new InvalidOperationException("La malla no permite lectura: " + mesh.name);
            using (var stream = new MemoryStream())
            {
                using (var writer = new BinaryWriter(stream, System.Text.Encoding.UTF8, true))
                {
                    foreach (var p in mesh.vertices) { writer.Write(p.x); writer.Write(p.y); writer.Write(p.z); }
                    foreach (var index in mesh.triangles) writer.Write(index);
                }
                using (var sha = SHA256.Create())
                    return BitConverter.ToString(sha.ComputeHash(stream.ToArray())).Replace("-", "").ToLowerInvariant();
            }
        }

        static List<Change> Plan(Model model, bool restore)
        {
            var bindings = new Dictionary<string, Binding>();
            foreach (var b in model.bindings) bindings.Add(restore ? b.newGuid : b.oldGuid, b);
            var changes = new List<Change>();
            int terrainCount = 0;
            foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
            foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!filter.sharedMesh) continue;
                string guid = AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(filter.sharedMesh));
                if (!bindings.TryGetValue(guid, out var binding)) continue;
                if (binding.name.StartsWith("Site", StringComparison.Ordinal)) terrainCount++;
                if (!restore)
                {
                    if (MeshHash(filter.sharedMesh) != binding.oldHash)
                        throw new InvalidOperationException("La malla tiene cambios propios: " + filter.name +
                            ". Se conserva; no se ha aplicado R1. Comparte esa malla para adaptar la actualización.");
                    var matrix = filter.transform.localToWorldMatrix;
                    for (int row = 0; row < 4; row++)
                    for (int column = 0; column < 4; column++)
                        if (Mathf.Abs(matrix[row, column] - binding.worldMatrix[row * 4 + column]) > .002f)
                            throw new InvalidOperationException("La posición/escala del suelo difiere de la base: " + filter.name +
                                ". No se modifica la escena; hay que registrar esa copia.");
                }
                var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(AssetDatabase.GUIDToAssetPath(restore ? binding.oldGuid : binding.newGuid));
                if (!mesh) throw new InvalidDataException("No se encuentra una malla de " + binding.name);
                var collider = filter.GetComponent<MeshCollider>();
                foreach (var c in filter.GetComponents<Collider>())
                    if (!(c is MeshCollider)) throw new InvalidOperationException("Collider adicional por revisar: " + filter.name);
                if (binding.name.StartsWith("Site", StringComparison.Ordinal) && (!collider || !collider.enabled || collider.convex))
                    throw new InvalidOperationException("Terreno sin MeshCollider estático compatible.");
                if (collider && collider.sharedMesh != filter.sharedMesh)
                    throw new InvalidOperationException("Malla visual y colisión no coinciden: " + filter.name);
                changes.Add(new Change { filter = filter, collider = collider, mesh = mesh });
            }
            if (terrainCount != 1)
                throw new InvalidOperationException("Se esperaba un terreno compatible; encontrados " + terrainCount +
                    ". Abre Campus y conserva cualquier terreno personalizado para adaptar R1.");
            return changes;
        }

        static void Apply(bool restore)
        {
            int group = -1;
            try
            {
                var changes = Plan(Read(), restore); // Entire preflight before changing any component.
                var scene = SceneManager.GetActiveScene();
                if (!restore && !string.IsNullOrEmpty(scene.path) && File.Exists(scene.path))
                {
                    string project = Directory.GetParent(Application.dataPath).FullName;
                    string backup = Path.Combine(Directory.GetParent(project).FullName,
                        "UPCH_Respaldo_Terreno_R1_" + DateTime.Now.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N"));
                    Directory.CreateDirectory(backup);
                    File.Copy(scene.path, Path.Combine(backup, Path.GetFileName(scene.path)));
                    if (File.Exists(scene.path + ".meta")) File.Copy(scene.path + ".meta", Path.Combine(backup, Path.GetFileName(scene.path) + ".meta"));
                    Debug.Log("Respaldo del archivo de escena guardado: " + backup +
                        (scene.isDirty ? ". Los cambios sin guardar permanecen en la escena y en Undo." : ""));
                }
                Undo.IncrementCurrentGroup();
                group = Undo.GetCurrentGroup();
                Undo.SetCurrentGroupName(restore ? "Restaurar suelo anterior" : "Aplicar relieve Parque R1");
                foreach (var c in changes)
                {
                    Undo.RecordObject(c.filter, "Malla del suelo");
                    c.filter.sharedMesh = c.mesh;
                    PrefabUtility.RecordPrefabInstancePropertyModifications(c.filter);
                    if (c.collider)
                    {
                        Undo.RecordObject(c.collider, "Colisión del suelo");
                        c.collider.sharedMesh = null;
                        c.collider.sharedMesh = c.mesh;
                        PrefabUtility.RecordPrefabInstancePropertyModifications(c.collider);
                    }
                }
                Undo.CollapseUndoOperations(group);
                EditorSceneManager.MarkSceneDirty(SceneManager.GetActiveScene());
                SceneView.RepaintAll();
                Debug.Log((restore ? "Suelo anterior restaurado: " : "Terreno_Parque_R1 aplicado: ") + changes.Count +
                    " mallas. Escena pendiente de guardar y revisar en Play. No se movieron edificios.");
            }
            catch (Exception e)
            {
                if (group >= 0) Undo.RevertAllDownToGroup(group);
                Debug.LogError("Terreno R1: " + e.Message);
            }
        }

        static void Check()
        {
            var model = Read();
            var names = new Dictionary<string, string>();
            foreach (var b in model.bindings) names[b.newGuid] = b.name;
            int meshes = 0, terrain = 0, errors = 0;
            MeshCollider groundCollider = null;
            foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
            foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
            {
                if (!filter.sharedMesh) continue;
                string guid = AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(filter.sharedMesh));
                if (!names.TryGetValue(guid, out var name)) continue;
                meshes++;
                var collider = filter.GetComponent<MeshCollider>();
                if (name.StartsWith("Site", StringComparison.Ordinal))
                {
                    terrain++;
                    groundCollider = collider;
                    if (!collider || !collider.enabled || collider.sharedMesh != filter.sharedMesh) errors++;
                }
            }
            if (terrain != 1) errors++;
            int rays = 0;
            if (terrain == 1 && groundCollider && groundCollider.enabled)
            {
                Physics.SyncTransforms();
                foreach (var sample in model.samplesWorld)
                {
                    rays++;
                    var ray = new Ray(new Vector3(sample.x, 10, sample.z), Vector3.down);
                    if (!groundCollider.Raycast(ray, out var hit, 30) || Mathf.Abs(hit.point.y - sample.y) > .01f)
                    {
                        errors++;
                        Debug.LogWarning("Terreno R1: revisar altura de colisión en X=" + sample.x + ", Z=" + sample.z, groundCollider);
                    }
                }
            }
            Debug.Log("Terreno_Parque_R1: " + meshes + " mallas reconocidas; " + errors +
                " incidencias de asignación/colisión; " + rays + " muestras físicas. Este control no certifica accesos, pendientes o datums de edificios; recorrer en Play.");
        }
    }
}
