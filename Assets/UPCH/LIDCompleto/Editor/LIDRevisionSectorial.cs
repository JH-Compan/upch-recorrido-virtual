using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UPCH.LIDCompleto.Editor
{
    // Editor-only review, using the same persistent meshes and independent
    // Prefab workflow as Edificio_A. Does not rebuild or modify Campus.
    public sealed class LIDRevisionSectorial : EditorWindow
    {
        [MenuItem("Tools/UPCH/LID completo/Revisión por sectores")]
        public static void Open() { GetWindow<LIDRevisionSectorial>("Revisión LID"); }

        void OnGUI()
        {
            EditorGUILayout.LabelField("Revisión de cerramientos y accesos", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Abre la escena independiente del LID o selecciona su raíz en la escena que tiene asignada tu equipo. Estas acciones solo encuadran la vista y comprueban referencias; no regeneran piezas ni guardan Campus.", MessageType.Info);
            if (GUILayout.Button("1 · Ingreso y jardinera")) Frame(new Vector3(0, 3.8f, -15.5f), new Vector3(8, 6, -28), 10);
            if (GUILayout.Button("1b · Pasarela oeste del primer piso")) Frame(new Vector3(-3.5f, 3.2f, -15.8f), new Vector3(-12, 8, -26), 9);
            EditorGUILayout.LabelField("Ingreso A-02: peldaños 1-4 con retorno en L; descanso 5; tramo 6-12. Dos perfiles centrales de baranda, de 1,50 y 2,10 m en planta.", EditorStyles.wordWrappedLabel);
            if (GUILayout.Button("2 · Núcleo norte y jardines")) Frame(new Vector3(0, 8, 11), new Vector3(12, 15, 35), 18);
            if (GUILayout.Button("3 · Cerramiento lateral oeste")) Frame(new Vector3(-30.8f, 8, 0), new Vector3(-48, 14, 10), 18);
            if (GUILayout.Button("4 · Cerramiento lateral este")) Frame(new Vector3(30.8f, 8, 0), new Vector3(48, 14, -10), 18);
            EditorGUILayout.Space();
            if (GUILayout.Button("Comprobar mallas, materiales y colisiones de vidrio")) Check();
            EditorGUILayout.HelpBox("Después: revisar cada piso en Scene, recorrer puertas y escaleras en Play, guardar escena/Prefab y conservar .meta. Commit en feature/* y PR a develop; un responsable por escena. La compilación y el recorrido deben ejecutarse en Unity.", MessageType.None);
        }

        static Transform Building()
        {
            var t = Selection.activeTransform;
            while (t != null)
            {
                if (t.name == "Edificio_LID") return t;
                t = t.parent;
            }
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded) continue;
                foreach (var root in scene.GetRootGameObjects())
                    if (root.name == "Edificio_LID") return root.transform;
            }
            Debug.LogError("LID: abre su escena de revisión o selecciona Edificio_LID.");
            return null;
        }

        static void Frame(Vector3 pivot, Vector3 eye, float distance)
        {
            var root = Building(); if (root == null) return;
            var view = SceneView.lastActiveSceneView;
            if (view == null) view = GetWindow<SceneView>();
            Vector3 worldPivot = root.TransformPoint(pivot);
            Vector3 forward = root.TransformDirection((pivot-eye).normalized);
            view.LookAt(worldPivot, Quaternion.LookRotation(forward, root.up), distance, false);
            view.Repaint();
        }

        static void Check()
        {
            var root = Building(); if (root == null) return;
            int errors=0, meshes=0, glass=0;
            foreach (var filter in root.GetComponentsInChildren<MeshFilter>(true))
            {
                meshes++;
                if (filter.sharedMesh == null || !EditorUtility.IsPersistent(filter.sharedMesh))
                { errors++; Debug.LogError("LID: malla ausente o no guardada como asset: " + filter.name, filter); }
            }
            foreach (var renderer in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                bool isGlass=false;
                foreach (var material in renderer.sharedMaterials)
                {
                    if (material == null || material.shader == null || !material.shader.isSupported)
                    { errors++; Debug.LogError("LID: material ausente o incompatible: " + renderer.name, renderer); }
                    else if (material.name == "LID_Vidrio") isGlass=true;
                }
                if (!isGlass) continue;
                glass++;
                // U facade glass uses a separate persistent collision surface.
                var collider=renderer.GetComponent<Collider>();
                var parent=renderer.transform.parent;
                if (collider == null && parent != null)
                {
                    string siblingName=renderer.name.Replace("_Vidrio", "_Colision");
                    string suffix=siblingName.Substring(siblingName.IndexOf('_',4)+1);
                    foreach (Transform child in parent)
                        if (child.name.EndsWith(suffix))
                        { collider=child.GetComponent<Collider>(); if (collider != null) break; }
                }
                if (collider == null || !collider.enabled)
                { errors++; Debug.LogError("LID: vidrio sin colisión activa: " + renderer.name, renderer); }
            }
            Debug.Log("LID: " + meshes + " mallas; " + glass + " piezas de vidrio; " + errors + " incidencias. Completar recorrido en Play antes del PR.");
        }
    }
}
