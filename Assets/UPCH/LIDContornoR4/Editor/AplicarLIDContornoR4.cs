using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UPCH.LIDContornoR4.Editor
{
    public sealed class AplicarLIDContornoR4 : EditorWindow
    {
        const string DataPath = "Assets/UPCH/LIDContornoR4/Datos/Aplicacion_Contorno_R4.json";
        [Serializable] public class Sample { public string name; public float x, y, z; }
        [Serializable] public class Model
        {
            public string revision, oldGuid, newGuid, oldHash, newHash, limits;
            public float[] worldMatrix, rootPosition;
            public Sample[] samples, stairs, entrySamples, windows, perimeterSamples;
        }
        [MenuItem("Tools/UPCH/Terreno/LID - Contorno y ventanas R4")]
        public static void Open()
        {
            var w = GetWindow<AplicarLIDContornoR4>("LID Terreno R4");
            w.minSize = new Vector2(490, 360);
        }
        void OnGUI()
        {
            EditorGUILayout.LabelField("LID: contorno y ventanas inferiores", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Franja provisional de 0,60 m junto al LID, normalmente a Y=-0,70 m, " +
                "para liberar los marcos inferiores. Se mantienen los descansos más bajos de R3 y las plataformas de entrada. " +
                "Las diferencias junto a estas plataformas tienen caras cerradas, no son rampas de paso.", MessageType.Warning);
            EditorGUILayout.LabelField("Abrir Campus con R3 aplicada. Solo se sustituye la malla de suelo y su MeshCollider. " +
                "No se cambian ventanas, materiales, edificio ni interiores. Revisar antes de guardar.", EditorStyles.wordWrappedLabel);
            using (new EditorGUI.DisabledScope(EditorApplication.isPlayingOrWillChangePlaymode))
            {
                if (GUILayout.Button("Aplicar terreno LID R4")) Apply(false);
                if (GUILayout.Button("Restaurar terreno R3")) Apply(true);
                if (GUILayout.Button("Comprobar contorno, ventanas y accesos")) Check();
            }
            EditorGUILayout.Space();
            if (GUILayout.Button("Enfocar lateral oeste")) Focus(141.12089f, 1);
            if (GUILayout.Button("Enfocar lateral este")) Focus(76.02089f, -1);
            if (GUILayout.Button("Enfocar ventanas de la fachada"))
            {
                var view = SceneView.lastActiveSceneView;
                if (view) view.LookAt(new Vector3(96,-.3f,100), Quaternion.Euler(20,90,0),15);
            }
            EditorGUILayout.LabelField("Aplicar no guarda la escena. Ctrl+Z o Restaurar permite volver atrás. " +
                "El respaldo de disco corresponde a la última escena guardada.", EditorStyles.wordWrappedLabel);
        }
        static Model Read()
        {
            var m = JsonUtility.FromJson<Model>(File.ReadAllText(DataPath));
            if (m == null || m.samples == null || m.samples.Length != 162 || m.windows == null || m.windows.Length != 165 || m.perimeterSamples == null || m.perimeterSamples.Length != 399 || m.entrySamples == null || m.entrySamples.Length != 74 || m.stairs == null || m.stairs.Length != 38 || m.rootPosition == null || m.rootPosition.Length != 3 || m.worldMatrix == null || m.worldMatrix.Length != 16)
                throw new InvalidDataException("Datos R4 incompletos.");
            return m;
        }
        static string Hash(Mesh mesh)
        {
            if (!mesh.isReadable) throw new InvalidOperationException("Malla sin lectura: " + mesh.name);
            using (var stream = new MemoryStream())
            {
                using (var writer = new BinaryWriter(stream, System.Text.Encoding.UTF8, true))
                {
                    foreach (var p in mesh.vertices) { writer.Write(p.x); writer.Write(p.y); writer.Write(p.z); }
                    foreach (var i in mesh.triangles) writer.Write(i);
                }
                using (var sha = SHA256.Create())
                    return BitConverter.ToString(sha.ComputeHash(stream.ToArray())).Replace("-", "").ToLowerInvariant();
            }
        }
        static MeshFilter Ground(Model m, bool currentR4)
        {
            MeshFilter selected = null; int buildings = 0;
            foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
            {
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (t.name == "Edificio_LID")
                    {
                        buildings++;
                        var expected = new Vector3(m.rootPosition[0], m.rootPosition[1], m.rootPosition[2]);
                        if (Vector3.Distance(t.position, expected) > .002f ||
                            Quaternion.Angle(t.rotation, Quaternion.Euler(0, 90, 0)) > .01f ||
                            Vector3.Distance(t.lossyScale, Vector3.one) > .001f)
                            throw new InvalidOperationException("El LID cambió de posición, giro o escala; hay que registrar esa copia.");
                    }
                foreach (var f in root.GetComponentsInChildren<MeshFilter>(true))
                {
                    if (!f.sharedMesh) continue;
                    string guid = AssetDatabase.AssetPathToGUID(AssetDatabase.GetAssetPath(f.sharedMesh));
                    if (guid != (currentR4 ? m.newGuid : m.oldGuid)) continue;
                    if (selected) throw new InvalidOperationException("Se encontró más de un terreno compatible.");
                    selected = f;
                }
            }
            if (buildings != 1 || !selected) throw new InvalidOperationException("Abre Campus con un LID y el terreno " + (currentR4 ? "R4" : "R3") + " aplicado.");
            var matrix = selected.transform.localToWorldMatrix;
            for (int r = 0; r < 4; r++) for (int c = 0; c < 4; c++)
                if (Mathf.Abs(matrix[r,c] - m.worldMatrix[r*4+c]) > .002f)
                    throw new InvalidOperationException("La transformación del terreno cambió; se conserva esa copia.");
            if (Hash(selected.sharedMesh) != (currentR4 ? m.newHash : m.oldHash))
                throw new InvalidOperationException("La malla tiene cambios propios; no se sustituye.");
            var mc = selected.GetComponent<MeshCollider>();
            if (!mc || !mc.enabled || mc.convex || mc.isTrigger || mc.sharedMesh != selected.sharedMesh)
                throw new InvalidOperationException("El terreno necesita su MeshCollider estático activo y coincidente con la malla visual.");
            if (selected.GetComponents<Collider>().Length != 1)
                throw new InvalidOperationException("Hay colliders adicionales en el terreno; deben revisarse.");
            return selected;
        }
        static void Apply(bool restore)
        {
            int group = -1;
            try
            {
                var m = Read(); var f = Ground(m, restore); var mc = f.GetComponent<MeshCollider>();
                var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(AssetDatabase.GUIDToAssetPath(restore ? m.oldGuid : m.newGuid));
                if (!mesh || Hash(mesh) != (restore ? m.oldHash : m.newHash)) throw new InvalidDataException("La malla de destino no coincide con R4.");
                var scene = SceneManager.GetActiveScene();
                if (!string.IsNullOrEmpty(scene.path) && File.Exists(scene.path))
                {
                    string project = Directory.GetParent(Application.dataPath).FullName;
                    string backup = Path.Combine(Directory.GetParent(project).FullName, "UPCH_Respaldo_LID_Terreno_R4_" +
                        DateTime.Now.ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N"));
                    Directory.CreateDirectory(backup); File.Copy(scene.path, Path.Combine(backup, Path.GetFileName(scene.path)));
                    if (File.Exists(scene.path + ".meta")) File.Copy(scene.path + ".meta", Path.Combine(backup, Path.GetFileName(scene.path) + ".meta"));
                    Debug.Log("Respaldo de la escena guardada: " + backup + ". Las ediciones sin guardar permanecen en escena y Undo.");
                }
                Undo.IncrementCurrentGroup(); group = Undo.GetCurrentGroup(); Undo.SetCurrentGroupName("Terreno LID R4");
                Undo.RecordObject(f, "Malla del terreno LID"); Undo.RecordObject(mc, "Colisión del terreno LID");
                f.sharedMesh = mesh; mc.sharedMesh = null; mc.sharedMesh = mesh;
                PrefabUtility.RecordPrefabInstancePropertyModifications(f); PrefabUtility.RecordPrefabInstancePropertyModifications(mc);
                Undo.CollapseUndoOperations(group); EditorSceneManager.MarkSceneDirty(scene); SceneView.RepaintAll();
                Debug.Log(restore ? "LID R4: terreno R3 restaurado. Escena pendiente de guardar." :
                    "LID R4 aplicado: una malla visual y su colisión. Comprobar el contorno y las ventanas; recorrer los accesos en Play antes de guardar.");
            }
            catch (Exception e) { if (group >= 0) Undo.RevertAllDownToGroup(group); Debug.LogError("LID R4: " + e.Message); }
        }
        static void Check()
        {
            try
            {
                var m = Read(); var f = Ground(m, true); var mc = f.GetComponent<MeshCollider>(); Physics.SyncTransforms();
                int heights = 0, steps = 0, obstacles = 0;
                foreach (var p in m.samples)
                {
                    var ray = new Ray(new Vector3(p.x,10,p.z),Vector3.down);
                    if (!mc.Raycast(ray,out var h,30) || Mathf.Abs(h.point.y-p.y) > .01f) heights++;
                    var bottom = new Vector3(p.x,p.y+.34f,p.z); var top = new Vector3(p.x,p.y+1.35f,p.z);
                    foreach (var c in Physics.OverlapCapsule(bottom,top,.30f,~0,QueryTriggerInteraction.Ignore))
                        if (c != mc) { obstacles++; Debug.LogWarning("R4: obstáculo en el recorrido: " + c.name,c); break; }
                }
                foreach (var p in m.stairs)
                {
                    if (mc.Raycast(new Ray(new Vector3(p.x,10,p.z),Vector3.down),out var stairHit,30) && stairHit.point.y > p.y+.005f)
                    { steps++; Debug.LogWarning("R4: terreno sobre el peldaño " + p.name,f); }
                }
                int entries = 0;
                foreach (var p in m.entrySamples)
                {
                    if (!Physics.Raycast(new Ray(new Vector3(p.x,p.y+.3f,p.z),Vector3.down),out var entryHit,.65f,~0,QueryTriggerInteraction.Ignore) ||
                        Mathf.Abs(entryHit.point.y-p.y) > .015f) entries++;
                    foreach (var c in Physics.OverlapCapsule(new Vector3(p.x,p.y+.34f,p.z),new Vector3(p.x,p.y+1.35f,p.z),.30f,~0,QueryTriggerInteraction.Ignore))
                        if (c != mc) { obstacles++; Debug.LogWarning("R4: obstáculo al entrar al descanso: " + c.name,c); break; }
                }
                int coveredWindows = 0, perimeterErrors = 0;
                foreach (var p in m.windows)
                    if (!mc.Raycast(new Ray(new Vector3(p.x,10,p.z),Vector3.down),out var windowHit,30) || windowHit.point.y > p.y+.005f)
                    { coveredWindows++; Debug.LogWarning("R4: revisar suelo delante de " + p.name,f); }
                foreach (var p in m.perimeterSamples)
                    if (!mc.Raycast(new Ray(new Vector3(p.x,10,p.z),Vector3.down),out var perimeterHit,30) || Mathf.Abs(perimeterHit.point.y-p.y) > .01f)
                        perimeterErrors++;
                Debug.Log("LID_Terreno_R4: " + m.samples.Length + " muestras; " + heights + " diferencias de altura; " +
                    steps + " peldaños cubiertos; " + obstacles + " muestras con obstáculos; " + entries + " discontinuidades en " + m.entrySamples.Length + " muestras de entrada. " +
                    "Ventanas: " + coveredWindows + " incidencias en " + m.windows.Length + " muestras; contorno: " + perimeterErrors + " diferencias en " + m.perimeterSamples.Length + " muestras. " +
                    "Cápsula de revisión: radio 0,30 m, altura 1,61 m, margen 0,04 m. No sustituye recorrer en Play ni confirma las cotas exteriores.");
            }
            catch (Exception e) { Debug.LogError("LID R4: " + e.Message); }
        }
        static void Focus(float wall, int sign)
        {
            var view = SceneView.lastActiveSceneView;
            if (view) view.LookAt(new Vector3(110,-.4f,wall+sign*2.5f), Quaternion.Euler(35,sign==1?180:0,0),13);
        }
    }
}
