using System;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace UPCH.Enfermeria.Editor
{
    // One-time authoring tool. The saved D.prefab is what the Campus scene displays;
    // this script does not create geometry at runtime on the Quest.
    public static class CrearPabellonD
    {
        private const string PrefabPath = "Assets/UPCH/Campus/Generated/Buildings/D.prefab";
        private const string MaterialFolder = "Assets/UPCH/Arte/Edificios/D/Materiales";
        private const float Width = 26.08f;
        private const float Depth = 19.72f;
        private const float Storey = 3.90f;
        private const int Storeys = 6;
        private const float CoreStart = 8.30f;

        private static Material white;
        private static Material glass;
        private static Material frame;
        private static Material darkGlass;
        private static Material stone;
        private static Material shadow;

        private static float Left => -Width / 2f;
        private static float Right => Width / 2f;
        private static float Front => -Depth / 2f;
        private static float Rear => Depth / 2f;
        private static float Height => Storeys * Storey;

        [MenuItem("Tools/UPCH/Ver pabellon D - Enfermeria")]
        public static void ViewInCampus()
        {
            var building = GameObject.Find("D - Enfermeria");
            if (building == null || SceneView.lastActiveSceneView == null)
            {
                Debug.LogError("UPCH D: abre la escena Campus antes de enfocar el pabellon.");
                return;
            }

            SceneView.lastActiveSceneView.LookAt(
                building.transform.position + Vector3.up * 12f,
                Quaternion.Euler(20f, -35f, 0f), 28f);
            Selection.activeGameObject = null;
        }

        [MenuItem("Tools/UPCH/Crear pabellon D - Enfermeria")]
        public static void Create()
        {
            var root = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                if (root.transform.childCount != 0)
                {
                    Debug.LogError("UPCH D: el prefab ya contiene el pabellon. No se regenera para conservar cualquier edicion manual.");
                    return;
                }

                EnsureFolder("Assets/UPCH/Arte/Edificios", "D");
                EnsureFolder("Assets/UPCH/Arte/Edificios/D", "Materiales");
                white = GetMaterial("PanelBlanco", new Color(0.83f, 0.83f, 0.79f));
                glass = GetMaterial("VidrioAzulado", new Color(0.25f, 0.44f, 0.53f, 0.76f), true);
                frame = GetMaterial("Aluminio", new Color(0.55f, 0.59f, 0.60f));
                darkGlass = GetMaterial("VidrioOscuro", new Color(0.24f, 0.37f, 0.42f, 0.60f), true);
                stone = GetMaterial("PiedraGris", new Color(0.55f, 0.54f, 0.50f));
                shadow = GetMaterial("Interior", new Color(0.29f, 0.33f, 0.34f));

                // Preserve the prefab GUID and the Campus scene instance at its existing coordinates.
                DestroyIfPresent<MeshCollider>(root);
                DestroyIfPresent<MeshRenderer>(root);
                DestroyIfPresent<MeshFilter>(root);

                var structure = Group(root.transform, "01_Estructura");
                var front = Group(root.transform, "02_Fachada_principal");
                var sides = Group(root.transform, "03_Fachadas_laterales");
                var interior = Group(root.transform, "04_Interiores");
                var access = Group(root.transform, "05_Acceso");
                var roof = Group(root.transform, "06_Azotea");

                Structure(structure);
                FrontFacade(front);
                SideFacades(sides);
                Interiors(interior);
                Entrance(access);
                Roof(roof);

                PrefabUtility.SaveAsPrefabAsset(root, PrefabPath);
                AssetDatabase.SaveAssets();
                Debug.Log("UPCH D: pabellon de Enfermeria guardado en D.prefab, seis niveles y 26.08 x 19.72 m.");
            }
            catch (Exception ex)
            {
                Debug.LogException(ex);
                throw;
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(root);
            }
        }

        private static void Structure(Transform parent)
        {
            // Floor levels in A-01..A-07: +0.70, +4.60, +8.50, +12.40, +16.30, +20.20.
            for (int level = 0; level < Storeys; level++)
            {
                float y = level * Storey;
                var floor = Group(parent, "Piso_" + (level + 1).ToString("00"));
                Box(floor, "Losa", new Vector3(Left + (CoreStart - Left) / 2f, y + 0.12f, 0),
                    new Vector3(CoreStart - Left, 0.24f, Depth), stone, true);
                // The eastern stair/lift core has its own opaque floors and envelope.
                Box(floor, "Losa_nucleo", new Vector3((CoreStart + Right) / 2f, y + 0.12f, 0),
                    new Vector3(Right - CoreStart, 0.24f, Depth), stone, true);
            }

            Box(parent, "Nucleo_escaleras_ascensores", new Vector3((CoreStart + Right) / 2f, Height / 2f, 0),
                new Vector3(Right - CoreStart, Height, Depth), white, true);
            for (int column = 0; column <= 5; column++)
            {
                float x = Mathf.Lerp(Left, CoreStart, column / 5f);
                Box(parent, "Columna_frontal_" + column, new Vector3(x, Height / 2f, Front + 0.28f),
                    new Vector3(0.34f, Height, 0.34f), white, true);
            }
            Box(parent, "Losa_azotea", new Vector3(0, Height + 0.14f, 0),
                new Vector3(Width, 0.28f, Depth), white, true);
        }

        private static void FrontFacade(Transform parent)
        {
            const int Bays = 15;
            float bay = (CoreStart - Left) / Bays;
            for (int level = 0; level < Storeys; level++)
            {
                float baseY = level * Storey;
                var row = Group(parent, "Nivel_" + (level + 1).ToString("00"));
                for (int i = 0; i < Bays; i++)
                {
                    float x = Left + (i + 0.5f) * bay;
                    bool doorway = level == 0 && x > 0.9f && x < 4.2f;
                    if (!doorway)
                    {
                        Box(row, "Vidrio_" + i, new Vector3(x, baseY + 2.02f, Front - 0.065f),
                            new Vector3(bay - 0.055f, 3.58f, 0.055f), glass, level == 0);
                    }
                    else
                    {
                        // Recessed, open entrance for the desktop / VR walking route.
                        Box(row, "Cabecero_acceso_" + i, new Vector3(x, baseY + 3.48f, Front - 0.06f),
                            new Vector3(bay - 0.04f, 0.42f, 0.12f), frame);
                    }
                    Box(row, "Montante_" + i, new Vector3(Left + i * bay, baseY + Storey / 2f, Front - 0.11f),
                        new Vector3(0.07f, Storey, 0.12f), frame);
                }
                Box(row, "Remate_montante", new Vector3(CoreStart, baseY + Storey / 2f, Front - 0.11f),
                    new Vector3(0.07f, Storey, 0.12f), frame);
                Box(row, "Imposta", new Vector3((Left + CoreStart) / 2f, baseY + Storey - 0.08f, Front - 0.12f),
                    new Vector3(CoreStart - Left, 0.16f, 0.14f), frame);
                Box(row, "Baranda_interior", new Vector3((Left + CoreStart) / 2f, baseY + 1.02f, Front + 0.65f),
                    new Vector3(CoreStart - Left, 0.055f, 0.05f), frame);
            }
            // Photo reference: a full-height glass screen beside a white tiled stair core.
            Box(parent, "Cornisa_vidrio", new Vector3((Left + CoreStart) / 2f, Height + 0.25f, Front - 0.08f),
                new Vector3(CoreStart - Left + 0.2f, 0.30f, 0.55f), white);
            PanelJoints(parent, Front - 0.035f, CoreStart, Right);
        }

        private static void SideFacades(Transform parent)
        {
            // Long west facade with the continuous horizontal window bands visible in IMG_1140/1143.
            for (int level = 0; level < Storeys; level++)
            {
                float y = level * Storey;
                float sill = level == 0 ? 0.55f : 1.35f;
                float head = level == 0 ? 3.24f : 2.58f;
                Box(parent, "Oeste_antepecho_" + level, new Vector3(Left + 0.03f, y + sill / 2f, 0),
                    new Vector3(0.16f, sill, Depth), white, true);
                Box(parent, "Oeste_dintel_" + level, new Vector3(Left + 0.03f, y + (head + Storey) / 2f, 0),
                    new Vector3(0.16f, Storey - head, Depth), white, true);
                Box(parent, "Oeste_vidrio_" + level, new Vector3(Left - 0.055f, y + (sill + head) / 2f, 0),
                    new Vector3(0.055f, head - sill, Depth - 0.3f), glass, true);
                for (int bay = 0; bay <= 10; bay++)
                {
                    float z = Mathf.Lerp(Front, Rear, bay / 10f);
                    Box(parent, "Oeste_montante_" + level + "_" + bay,
                        new Vector3(Left - 0.10f, y + (sill + head) / 2f, z),
                        new Vector3(0.10f, head - sill, 0.065f), frame);
                }
            }

            // Rear elevation: ribbon windows and opaque bands, matching the floor grid on the plans.
            for (int level = 0; level < Storeys; level++)
            {
                float y = level * Storey;
                Box(parent, "Norte_antepecho_" + level, new Vector3((Left + CoreStart) / 2f, y + 0.68f, Rear - 0.04f),
                    new Vector3(CoreStart - Left, 1.36f, 0.16f), white, true);
                Box(parent, "Norte_dintel_" + level, new Vector3((Left + CoreStart) / 2f, y + 3.32f, Rear - 0.04f),
                    new Vector3(CoreStart - Left, 1.16f, 0.16f), white, true);
                Box(parent, "Norte_vidrio_" + level, new Vector3((Left + CoreStart) / 2f, y + 2.06f, Rear + 0.05f),
                    new Vector3(CoreStart - Left - 0.15f, 1.36f, 0.055f), darkGlass, true);
                for (int bay = 0; bay <= 12; bay++)
                {
                    float x = Mathf.Lerp(Left, CoreStart, bay / 12f);
                    Box(parent, "Norte_montante_" + level + "_" + bay,
                        new Vector3(x, y + 2.06f, Rear + 0.10f), new Vector3(0.06f, 1.36f, 0.10f), frame);
                }
            }
            // The eastern side is the stair/lift core; the narrow windows indicate landings.
            for (int level = 1; level < Storeys; level++)
            {
                float y = level * Storey + 2.05f;
                Box(parent, "Nucleo_ventana_lateral_" + level, new Vector3(Right + 0.045f, y, 2.2f),
                    new Vector3(0.07f, 1.10f, 5.0f), darkGlass);
                for (int i = 0; i <= 4; i++)
                    Box(parent, "Nucleo_marco_lateral_" + level + "_" + i,
                        new Vector3(Right + 0.09f, y, -0.3f + 1.25f * i), new Vector3(0.08f, 1.12f, 0.05f), frame);
            }
            // Light cladding-panel grid on the solid front and east elevations.
            for (int level = 1; level < Storeys; level++)
                Box(parent, "Junta_este_horizontal_" + level, new Vector3(Right + 0.025f, level * Storey, 0),
                    new Vector3(0.015f, 0.018f, Depth), stone);
        }

        private static void Interiors(Transform parent)
        {
            // A continuous central corridor and room divisions follow the D block on A-02..A-06.
            for (int level = 0; level < Storeys; level++)
            {
                float y = level * Storey;
                var floor = Group(parent, "Piso_" + (level + 1).ToString("00"));
                if (level == 0)
                {
                    // Ground-floor lobby and reception remain open behind the entrance.
                    Box(floor, "Mostrador_recepcion", new Vector3(-1.0f, y + 0.65f, -4.2f),
                        new Vector3(3.5f, 1.15f, 0.72f), stone, true);
                    Box(floor, "Vestibulo_posterior", new Vector3(-1.0f, y + 1.8f, 2.2f),
                        new Vector3(12.0f, 3.3f, 0.18f), white, true);
                    continue;
                }

                // Corridor runs east-west through the middle of the teaching floors.
                foreach (float z in new[] { -1.35f, 1.35f })
                {
                    for (int part = 0; part < 4; part++)
                    {
                        float x0 = Left + part * (CoreStart - Left) / 4f;
                        float x1 = Left + (part + 1) * (CoreStart - Left) / 4f;
                        Box(floor, "Muro_pasillo_" + z + "_" + part,
                            new Vector3((x0 + x1) / 2f, y + 2.10f, z),
                            new Vector3(x1 - x0 - 0.95f, 3.22f, 0.12f), white, true);
                        Box(floor, "Puerta_pasillo_" + z + "_" + part,
                            new Vector3(x1 - 0.48f, y + 2.17f, z),
                            new Vector3(0.87f, 2.75f, 0.055f), darkGlass);
                    }
                }
                foreach (float x in new[] { -6.7f, -0.5f, 4.6f })
                {
                    Box(floor, "Division_norte_" + x, new Vector3(x, y + 2.05f, 5.60f),
                        new Vector3(0.13f, 3.30f, 8.05f), white, true);
                    Box(floor, "Division_sur_" + x, new Vector3(x, y + 2.05f, -5.60f),
                        new Vector3(0.13f, 3.30f, 8.05f), white, true);
                }
                Box(floor, "Techo_pasillo", new Vector3((Left + CoreStart) / 2f, y + 3.62f, 0),
                    new Vector3(CoreStart - Left, 0.12f, 2.72f), white);
            }
        }

        private static void Entrance(Transform parent)
        {
            // Small recessed lobby, the entrance steps and the accessible side ramp.
            Box(parent, "Umbral", new Vector3(2.5f, 0.20f, Front - 0.45f), new Vector3(4.5f, 0.25f, 1.1f), stone, true);
            for (int i = 0; i < 4; i++)
                Box(parent, "Escalon_" + i, new Vector3(2.5f, 0.08f + i * 0.12f, Front - 3.0f + i * 0.55f),
                    new Vector3(5.8f, 0.16f + i * 0.24f, 0.56f), stone, true);
            Box(parent, "Rampa_accesible", new Vector3(6.3f, 0.28f, Front - 2.2f),
                new Vector3(1.6f, 0.20f, 4.0f), stone, true);
            foreach (float x in new[] { 1.0f, 4.0f })
                Box(parent, "Jamba_acceso_" + x, new Vector3(x, 1.65f, Front - 0.16f),
                    new Vector3(0.10f, 3.15f, 0.18f), frame);
            // Doors are shown open so the lobby can be entered in the virtual tour.
            Box(parent, "Puerta_izquierda", new Vector3(1.35f, 1.56f, Front + 0.55f),
                new Vector3(0.08f, 2.72f, 1.25f), darkGlass);
            Box(parent, "Puerta_derecha", new Vector3(3.65f, 1.56f, Front + 0.55f),
                new Vector3(0.08f, 2.72f, 1.25f), darkGlass);

            Box(parent, "Letrero_base", new Vector3(10.55f, 1.15f, Front - 0.13f),
                new Vector3(3.80f, 1.0f, 0.10f), stone);
            var label = new GameObject("FACULTAD DE ENFERMERIA");
            label.transform.SetParent(parent, false);
            label.transform.localPosition = new Vector3(10.55f, 1.12f, Front - 0.205f);
            label.transform.localRotation = Quaternion.identity;
            var text = label.AddComponent<TextMesh>();
            text.text = "FACULTAD DE\nENFERMERIA";
            text.anchor = TextAnchor.MiddleCenter;
            text.alignment = TextAlignment.Center;
            text.fontSize = 72;
            text.characterSize = 0.10f;
            text.color = new Color(0.16f, 0.18f, 0.18f);
        }

        private static void Roof(Transform parent)
        {
            Box(parent, "Parapeto_norte", new Vector3(0, Height + 0.55f, Rear - 0.15f),
                new Vector3(Width, 0.85f, 0.30f), white, true);
            Box(parent, "Parapeto_oeste", new Vector3(Left + 0.15f, Height + 0.55f, 0),
                new Vector3(0.30f, 0.85f, Depth), white, true);
            Box(parent, "Parapeto_este", new Vector3(Right - 0.15f, Height + 0.55f, 0),
                new Vector3(0.30f, 0.85f, Depth), white, true);
            Box(parent, "Ducto_01", new Vector3(-6.4f, Height + 0.80f, 4.7f),
                new Vector3(1.3f, 1.3f, 1.4f), frame);
            Box(parent, "Ducto_02", new Vector3(8.7f, Height + 0.76f, 6.3f),
                new Vector3(1.5f, 1.2f, 1.2f), frame);
        }

        private static void PanelJoints(Transform parent, float z, float x0, float x1)
        {
            for (float x = x0 + 1.55f; x < x1; x += 1.55f)
                Box(parent, "Junta_vertical_" + x.ToString("F2"), new Vector3(x, Height / 2f, z),
                    new Vector3(0.015f, Height, 0.012f), stone);
            for (float y = 2.0f; y < Height; y += 2.0f)
                Box(parent, "Junta_horizontal_" + y.ToString("F2"), new Vector3((x0 + x1) / 2f, y, z),
                    new Vector3(x1 - x0, 0.015f, 0.012f), stone);
        }

        private static Material GetMaterial(string name, Color color, bool transparent = false)
        {
            string path = MaterialFolder + "/" + name + ".mat";
            var existing = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (existing != null) return existing;
            var shader = Shader.Find("Universal Render Pipeline/Lit");
            if (shader == null) throw new InvalidOperationException("URP/Lit no disponible.");
            var material = new Material(shader) { name = name };
            material.SetColor("_BaseColor", color);
            if (transparent)
            {
                material.SetFloat("_Surface", 1);
                material.SetFloat("_SrcBlend", (float)BlendMode.SrcAlpha);
                material.SetFloat("_DstBlend", (float)BlendMode.OneMinusSrcAlpha);
                material.SetFloat("_ZWrite", 0);
                material.renderQueue = (int)RenderQueue.Transparent;
                material.SetOverrideTag("RenderType", "Transparent");
                material.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");
            }
            AssetDatabase.CreateAsset(material, path);
            return material;
        }

        private static Transform Group(Transform parent, string name)
        {
            var group = new GameObject(name);
            group.transform.SetParent(parent, false);
            return group.transform;
        }

        private static void Box(Transform parent, string name, Vector3 position, Vector3 size,
            Material material, bool collision = false)
        {
            var box = GameObject.CreatePrimitive(PrimitiveType.Cube);
            box.name = name;
            box.transform.SetParent(parent, false);
            box.transform.localPosition = position;
            box.transform.localScale = size;
            var renderer = box.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = material;
            if (material == glass || material == darkGlass)
            {
                renderer.shadowCastingMode = ShadowCastingMode.Off;
                renderer.receiveShadows = false;
            }
            if (!collision) UnityEngine.Object.DestroyImmediate(box.GetComponent<BoxCollider>());
        }

        private static void DestroyIfPresent<T>(GameObject root) where T : Component
        {
            var component = root.GetComponent<T>();
            if (component != null) UnityEngine.Object.DestroyImmediate(component, true);
        }

        private static void EnsureFolder(string parent, string child)
        {
            if (!AssetDatabase.IsValidFolder(parent + "/" + child))
                AssetDatabase.CreateFolder(parent, child);
        }
    }
}
