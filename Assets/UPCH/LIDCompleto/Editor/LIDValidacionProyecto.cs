using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace UPCH.LIDCompleto.Editor
{
    // Read-only checks. The prefab remains persistent and is not rebuilt in Play.
    public static class LIDValidacionProyecto
    {
        static readonly string[] Names = { "Sotano", "Piso_01", "Piso_02", "Piso_03", "Piso_04", "Azotea" };
        static readonly float[] Npt = { 0, 3.2f, 6.4f, 9.6f, 12.8f, 16.8f };

        [MenuItem("Tools/UPCH/LID completo/Validar niveles y superposiciones en Campus")]
        public static void Validate()
        {
            var scene = SceneManager.GetActiveScene();
            var buildings = new List<Transform>();
            foreach (var root in scene.GetRootGameObjects())
                foreach (var t in root.GetComponentsInChildren<Transform>(true))
                    if (t.name == "Edificio_LID") buildings.Add(t);
            if (buildings.Count != 1)
            {
                Debug.LogError("LID: se esperaba una instancia en la escena activa; encontradas " + buildings.Count);
                return;
            }
            var building = buildings[0];
            int errors = 0;
            if ((building.lossyScale - Vector3.one).sqrMagnitude > .000001f)
            { errors++; Debug.LogError("LID: escala mundial distinta de 1:1.", building); }
            for (int i = 0; i < Names.Length; i++)
            {
                var floor = building.Find(Names[i]);
                if (floor == null || Mathf.Abs(floor.localPosition.y-Npt[i]) > .001f ||
                    new Vector2(floor.localPosition.x, floor.localPosition.z).sqrMagnitude > .000001f ||
                    (floor.localScale-Vector3.one).sqrMagnitude > .000001f)
                { errors++; Debug.LogError("LID: falta o está desplazado/escalado el nivel " + Names[i], building); }
            }
            foreach (var t in building.GetComponentsInChildren<Transform>(true))
            {
                if (t.parent == null || t.parent.name != "Mobiliario") continue;
                string name = t.name;
                int split = name.IndexOf('_', 4);
                if (split >= 0) name = name.Substring(split+1);
                if (name.StartsWith("PC_", StringComparison.Ordinal) || name.Contains("Asiento_"))
                { errors++; Debug.LogError("LID: permanece una computadora o asiento: " + t.name, t); }
            }
            // Terrain crossing is tested against mesh triangles, not bounds:
            // the clipped terrain keeps its original overall campus bounds.
            var samples = new[] { new Vector3(-20, 1.2f, 8), new Vector3(20, 1.2f, 8),
                                  new Vector3(-20, 1.2f, -8), new Vector3(20, 1.2f, -8),
                                  new Vector3(0, 1.2f, 0) };
            Physics.SyncTransforms();
            foreach (var point in samples)
            {
                var origin = building.TransformPoint(point + Vector3.up * .2f);
                foreach (var hit in Physics.RaycastAll(origin, Vector3.down, .4f, ~0, QueryTriggerInteraction.Ignore))
                    if (!hit.transform.IsChildOf(building) && hit.transform.name == "Terreno")
                    { errors++; Debug.LogError("LID: el terreno cruza el volumen de sótano en " + point, hit.transform); }
            }
            Debug.Log("LID: " + errors + " incidencias de niveles, escala, instancias, terreno y mobiliario. " +
                "Esta validación no certifica la cota real de la explanada ni reemplaza recorrer puertas, accesos y escaleras en Play.", building);
        }
    }
}
