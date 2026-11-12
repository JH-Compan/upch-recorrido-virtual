using UnityEditor;
using UnityEngine;
namespace UPCH.Enfermeria.Editor
{
    public static class CrearPabellonD
    {
        [MenuItem("Tools/UPCH/Ver pabellon D - Enfermeria")]
        public static void ViewInCampus()
        {
            var building = GameObject.Find("D - Enfermeria");
            if (building == null || SceneView.lastActiveSceneView == null) {
                Debug.LogError("Abre la escena Campus para ver Enfermeria."); return;
            }
            SceneView.lastActiveSceneView.LookAt(building.transform.position + Vector3.up * 12,
                Quaternion.Euler(20, 225, 0), 28);
            Selection.activeGameObject = null;
        }
        // Deliberately not a menu action: regenerating replaces manual prefab edits.
        public static void Create() { ReconstruirEnfermeria.Run(); }
        public static void ValidateOrientation()
        {
            var p = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/UPCH/Campus/Generated/Buildings/D.prefab");
            if (p == null || p.transform.Find("Acceso_este") == null)
                throw new System.InvalidOperationException("Falta el acceso este de Enfermeria.");
        }
    }
}
