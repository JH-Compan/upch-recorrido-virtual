using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UPCH.LIDCompleto.Editor
{
    public static class LIDAccesosR2
    {
        [MenuItem("Tools/UPCH/LID completo/Comprobar accesos y escaleras R2")]
        public static void Check()
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode)
                throw new InvalidOperationException("LID: comprueba en Edit y después recorre las escaleras en Play.");
            Transform building = null;
            int roots = 0;
            foreach (var root in SceneManager.GetActiveScene().GetRootGameObjects())
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (t.name == "Edificio_LID") { building = t; roots++; }
            if (roots != 1) { Debug.LogError("LID R2: se esperaba una instancia; encontradas " + roots); return; }
            Physics.SyncTransforms();
            int checkedSteps = 0, incidents = 0;
            foreach (var filter in building.GetComponentsInChildren<MeshFilter>())
            {
                if (!filter.name.Contains("Peldano")) continue;
                var renderer = filter.GetComponent<Renderer>();
                var collider = filter.GetComponent<Collider>();
                if (!renderer || !filter.sharedMesh || !collider || !collider.enabled)
                { incidents++; Debug.LogWarning("LID R2: peldaño sin malla, renderer o collider activo: " + filter.name, filter); continue; }
                checkedSteps++;
                var bounds = renderer.bounds;
                var origin = new Vector3(bounds.center.x, bounds.max.y + .025f, bounds.center.z);
                foreach (var hit in Physics.RaycastAll(origin, Vector3.up, 1.975f, ~0, QueryTriggerInteraction.Ignore))
                {
                    if (hit.collider == collider || hit.distance < .001f) continue;
                    incidents++;
                    Debug.LogWarning("LID R2: revisar altura libre sobre " + filter.name + ": " +
                        (hit.distance + .025f).ToString("F3") + " m; obstáculo " + hit.collider.name, hit.collider);
                    break;
                }
            }
            Debug.Log("LID_R2_Accesos_Estructura: " + checkedSteps + " peldaños comprobados; " + incidents +
                " observaciones. Umbral de revisión: 2,00 m; no es una certificación normativa. " +
                "Comprobar sótano, dos escaleras laterales, norte, interior y entrada en Play. " +
                "La cota exterior +1,20 m permanece provisional.", building);
        }
    }
}
