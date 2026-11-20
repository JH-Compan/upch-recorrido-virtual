using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace UPCH.Campus.Editor
{
    /// <summary>
    /// Rebuilds the E (Víctor Alzamora) and F (Wu) prefab geometry against sheets
    /// A-01, A-02 and A-03. All dimensions in this file are metres in plan coordinates.
    /// Floors are single, non-moving static slabs; openings are actual gaps in walls.
    /// </summary>
    [InitializeOnLoad]
    public static class ReconstruirPabellonesEF
    {
        const string EPath = "Assets/UPCH/Campus/Generated/Buildings/E.prefab";
        const string FPath = "Assets/UPCH/Campus/Generated/Buildings/F.prefab";
        const string ClosedAngleRebuildKey = "UPCH.EF.ClosedAngleConnector.Rebuilt";
        const float Storey = 3.45f;
        const float Wall = .18f;
        const float DoorHeight = 2.12f;

        static Material creamE, creamF, glass, darkGlass, metal, paving;

        static ReconstruirPabellonesEF()
        {
            EditorApplication.delayCall += () =>
            {
                if (EditorPrefs.GetBool(ClosedAngleRebuildKey, false)) return;
                try
                {
                    Run();
                    EditorPrefs.SetBool(ClosedAngleRebuildKey, true);
                    Debug.Log("E/F closed-angle connector rebuilt once from the editor startup.");
                }
                catch (Exception e)
                {
                    Debug.LogException(e);
                }
            };
        }

        [MenuItem("Tools/UPCH/Rebuild Pabellones E y F - Alzamora y Wu")]
        public static void Run()
        {
            creamE = Load("Assets/UPCH/Campus/Generated/Materials/Pabellon E.mat");
            creamF = Load("Assets/UPCH/Campus/Generated/Materials/Pabellon F.mat");
            glass = Load("Assets/UPCH/Arte/Edificios/D/Materiales/VidrioFachadaClara.mat");
            darkGlass = Load("Assets/UPCH/Arte/Edificios/D/Materiales/VidrioOscuro.mat");
            metal = Load("Assets/UPCH/Arte/Edificios/D/Materiales/Aluminio.mat");
            paving = Load("Assets/UPCH/Arte/Edificios/D/Materiales/PiedraGris.mat");

            GameObject e = PrefabUtility.LoadPrefabContents(EPath);
            GameObject f = PrefabUtility.LoadPrefabContents(FPath);
            try
            {
                Vector3 fLocalInE = e.transform.InverseTransformPoint(f.transform.position);
                ClearGeneratedChildren(e.transform);
                ClearGeneratedChildren(f.transform);

                BuildAlzamora(e.transform);
                BuildWu(f.transform);
                BuildDiagonalWalk(e.transform, fLocalInE);

                PrefabUtility.SaveAsPrefabAsset(e, EPath);
                PrefabUtility.SaveAsPrefabAsset(f, FPath);
                AssetDatabase.SaveAssets();
                EditorSceneManager.MarkAllScenesDirty();
                Debug.Log("EF_REBUILT_FROM_A01_A03: Alzamora 24.30 x 9.76 m / 3 levels; Wu roof footprint 11.85 x 22.91 m / 2 levels; diagonal glazed connector and room doors added.");
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(e);
                PrefabUtility.UnloadPrefabContents(f);
            }
        }

        static Material Load(string path)
        {
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!material) throw new InvalidOperationException("Missing material: " + path);
            return material;
        }

        static void ClearGeneratedChildren(Transform root)
        {
            for (int i = root.childCount - 1; i >= 0; --i)
                UnityEngine.Object.DestroyImmediate(root.GetChild(i).gameObject);
            foreach (var component in root.GetComponents<Component>())
                if (!(component is Transform)) UnityEngine.Object.DestroyImmediate(component);
        }

        // A-01/A-02/A-03: the Alzamora wing is the 24.30 x 9.76 m bar at the
        // south of the sheet. The three occupied levels share the 3.45 m floor grid.
        static void BuildAlzamora(Transform root)
        {
            const float w = 24.30f, d = 9.76f;
            Transform body = Group(root, "E_Victor_Alzamora_24.30x9.76m");
            for (int level = 0; level < 3; level++)
            {
                float y = level * Storey;
                Transform floor = Group(body, "Nivel_" + (level + 1) + "_NPT_" + (y - .55f).ToString("F2"));
                Slab(floor, "Losa_unica_sin_solapes", Vector3.zero, w, d, y - .09f, .18f, paving);
                BuildAlzamoraFront(floor, y, level, w, d);
                BuildAlzamoraBack(floor, y, level, w, d);
                EndWall(floor, "Muro_lateral_izquierdo", -w / 2, y, d, creamE, true);
                EndWall(floor, "Muro_lateral_derecho", w / 2, y, d, creamE, true);
                AlzamoraPartitions(floor, y, level, w, d);
            }

            float roofY = 3 * Storey;
            Slab(body, "Azotea_E_losa_unica", Vector3.zero, w, d, roofY - .08f, .16f, creamE);
            Parapet(body, w, d, roofY, creamE);
        }

        static void BuildAlzamoraFront(Transform parent, float y, int floor, float w, float d)
        {
            // The photographed elevation is a continuous cream frame around broad,
            // dark horizontal glazing. Openings have glass only in the opening.
            const float z = -4.88f;
            float sill = floor == 0 ? .55f : .92f;
            float head = floor == 0 ? 2.75f : 2.62f;
            float entryX = -10.30f;
            int bays = 10;
            float bay = w / bays;
            for (int b = 0; b < bays; b++)
            {
                float x = -w / 2 + bay * (b + .5f);
                bool entry = floor == 0 && Mathf.Abs(x - entryX) < bay * .55f;
                float opening = bay - .38f;
                if (entry)
                {
                    DoorOpening(parent, "Puerta_principal_E", new Vector2(x, z), Vector2.right,
                        y, .98f, DoorHeight, Wall, creamE, glass, metal);
                    ContinueFacadeSides(parent, x, bay, z, y, sill, head, .98f, creamE);
                }
                else
                {
                    Box(parent, "Antepecho_fachada_E", new Vector3(x, y + sill / 2, z),
                        new Vector3(opening, sill, Wall), creamE, true);
                    Box(parent, "Ventanal_cinta_E", new Vector3(x, y + (sill + head) / 2, z - .025f),
                        new Vector3(opening, head - sill, .055f), darkGlass, false);
                    Box(parent, "Dintel_fachada_E", new Vector3(x, y + (head + Storey) / 2, z),
                        new Vector3(opening, Storey - head, Wall), creamE, true);
                }
                if (b > 0)
                    Box(parent, "Pilastra_fachada_E", new Vector3(-w / 2 + bay * b, y + Storey / 2, z),
                        new Vector3(.18f, Storey, .28f), creamE, true);
                Box(parent, "Perfil_horizontal_E", new Vector3(x, y + sill, z - .055f),
                    new Vector3(opening, .045f, .06f), metal, false);
                Box(parent, "Perfil_superior_E", new Vector3(x, y + head, z - .055f),
                    new Vector3(opening, .045f, .06f), metal, false);
            }
        }

        static void ContinueFacadeSides(Transform p, float x, float bay, float z, float y,
            float sill, float head, float paneWidth, Material wall)
        {
            float sideSpan = (bay - paneWidth) / 2;
            if (sideSpan <= .01f) return;
            foreach (float side in new[] { -1f, 1f })
                Box(p, "Machon_puerta_E", new Vector3(x + side * (paneWidth / 2 + sideSpan / 2), y + Storey / 2, z),
                    new Vector3(sideSpan, Storey, Wall), wall, true);
        }

        static void BuildAlzamoraBack(Transform parent, float y, int floor, float w, float d)
        {
            // Corridor and internal classroom doors follow the door rhythm in A-01..A-03.
            Vector2 a = new Vector2(-w / 2, d / 2), b = new Vector2(w / 2, d / 2);
            if (floor == 0)
                WallRun(parent, "Acceso_diagonal_E", a, b, y, Storey, Wall, creamE,
                    (-7.0f + w / 2) / w, .98f, DoorHeight, true, glass, metal);
            else
                WindowWall(parent, "Ventanas_traseras_E", a, b, y, w, floor, creamE, darkGlass, metal);
        }

        static void AlzamoraPartitions(Transform p, float y, int floor, float w, float d)
        {
            // Cross walls create the classrooms/offices and the corridor visible in
            // each plan. The angled end partition follows the diagonal hall/stair joint.
            float corridorZ = -1.15f;
            WallRun(p, "Tabique_pasillo_E", new Vector2(-w / 2 + .20f, corridorZ),
                new Vector2(w / 2 - .20f, corridorZ), y, Storey - .08f, .12f, creamE,
                    .18f, .95f, DoorHeight, true, darkGlass, metal);
            float[] divisions = floor == 2
                ? new[] { -8.85f, -4.65f, -.65f, 3.10f, 7.00f }
                : new[] { -8.85f, -4.65f, -.65f, 3.10f, 7.00f };
            for (int i = 0; i < divisions.Length; i++)
            {
                float x = divisions[i];
                float t = Mathf.Clamp01((corridorZ + d / 2) / d);
                WallRun(p, "Division_aula_E_" + (i + 1), new Vector2(x, -d / 2 + .10f),
                    new Vector2(x, d / 2 - .10f), y, Storey - .08f, .12f, creamE,
                    t, .90f, DoorHeight, true, darkGlass, metal);
            }
            if (floor == 1 || floor == 2)
                WallRun(p, "Muro_diagonal_de_circulacion_E", new Vector2(-1.1f, -d / 2 + .2f),
                    new Vector2(1.25f, d / 2 - .2f), y, Storey - .08f, .14f, creamE,
                    .72f, .95f, DoorHeight, true, darkGlass, metal);
        }

        // Wu's roof plan A-03 gives 11.85 x 22.91 m and +6.35 NPT. A-01/A-02
        // show two occupied levels at -0.55 and +2.90 with matching 3.45 m spacing.
        static void BuildWu(Transform root)
        {
            const float w = 11.85f, d = 22.91f;
            Transform body = Group(root, "F_Wu_planta_de_azotea_11.85x22.91m");
            for (int level = 0; level < 2; level++)
            {
                float y = level * Storey;
                Transform floor = Group(body, "Nivel_" + (level + 1) + "_NPT_" + (y - .55f).ToString("F2"));
                Slab(floor, "Losa_unica_sin_solapes", Vector3.zero, w, d, y - .09f, .18f, paving);
                WuSouthFacade(floor, y, level, w, d);
                WuNorthFacade(floor, y, level, w, d);
                WuSideFacade(floor, y, level, w, d, -1);
                WuSideFacade(floor, y, level, w, d, 1);
                WuPartitions(floor, y, level, w, d);
            }
            float roofY = 2 * Storey;
            Slab(body, "Azotea_Wu_losa_unica_11.85x22.91", Vector3.zero, w, d, roofY - .08f, .16f, creamF);
            Parapet(body, w, d, roofY, creamF);
            Box(body, "Pretil_escalonado_azotea_Wu", new Vector3(4.05f, roofY + .37f, 10.0f),
                new Vector3(3.75f, .74f, 2.9f), creamF, true);
        }

        static void WuSouthFacade(Transform p, float y, int level, float w, float d)
        {
            float z = -d / 2;
            float sill = level == 0 ? .55f : .88f;
            float head = level == 0 ? 2.78f : 2.68f;
            int bays = 5;
            float bay = w / bays;
            for (int i = 0; i < bays; i++)
            {
                float x = -w / 2 + bay * (i + .5f);
                float paneW = bay - .24f;
                bool entry = level == 0 && i == 2;
                bool diagonalAccess = level == 0 && i == 4;
                if (entry || diagonalAccess)
                {
                    DoorOpening(p, diagonalAccess ? "Puerta_diagonal_acceso_Wu" : "Puerta_principal_Wu",
                        new Vector2(x, z), Vector2.right, y, diagonalAccess ? 1.0f : paneW,
                        DoorHeight, Wall, creamF, glass, metal);
                }
                else
                {
                    Box(p, "Antepecho_vidriado_Wu", new Vector3(x, y + sill / 2, z),
                        new Vector3(paneW, sill, Wall), creamF, true);
                    Box(p, "Paño_traslucido_Wu", new Vector3(x, y + (sill + head) / 2, z - .025f),
                        new Vector3(paneW, head - sill, .055f), glass, false);
                    Box(p, "Dintel_vidriado_Wu", new Vector3(x, y + (head + Storey) / 2, z),
                        new Vector3(paneW, Storey - head, Wall), creamF, true);
                }
                if (i > 0)
                    Box(p, "Montante_fachada_Wu", new Vector3(-w / 2 + bay * i, y + Storey / 2, z),
                        new Vector3(.18f, Storey, .30f), creamF, true);
                Box(p, "Travesano_Wu", new Vector3(x, y + head, z - .06f),
                    new Vector3(paneW, .05f, .06f), metal, false);
            }
        }

        static void WuNorthFacade(Transform p, float y, int level, float w, float d)
        {
            float z = d / 2;
            if (level == 0)
            {
                // Service/access doorway is placed at the end shown on A-01.
                WallRun(p, "Muro_norte_con_acceso_Wu", new Vector2(-w / 2, z), new Vector2(w / 2, z),
                    y, Storey, Wall, creamF, .76f, .92f, DoorHeight, true, creamF, metal);
            }
            else
            {
                Box(p, "Muro_norte_Wu", new Vector3(0, y + Storey / 2, z), new Vector3(w, Storey, Wall), creamF, true);
                for (int i = -1; i <= 1; i++)
                    Box(p, "Ventana_hendida_Wu", new Vector3(i * 2.15f, y + 2.55f, z - .10f),
                        new Vector3(.68f, .18f, .045f), darkGlass, false);
            }
        }

        static void WuSideFacade(Transform p, float y, int floor, float w, float d, int side)
        {
            float x = side * w / 2;
            // The elevation uses cream end walls and narrow horizontal windows;
            // a broad upper band on the principal side is glazed like the photographs.
            bool glassSide = side < 0;
            if (glassSide)
            {
                Vector2 a = new Vector2(x, -d / 2), b = new Vector2(x, d / 2);
                WindowWall(p, "Fachada_lateral_ritmada_Wu", a, b, y, d, floor, creamF, darkGlass, metal);
            }
            else
            {
                SlitWall(p, "Muro_ciego_lateral_Wu", x, y, d, side, creamF, darkGlass,
                    new[] { -d * .34f, 0f, d * .34f });
                PanelJointsOnX(p, "Juntas_panel_lateral_Wu", x, y, d, side);
            }
        }

        static void WuPartitions(Transform p, float y, int level, float w, float d)
        {
            // A-01/A-02 show the central circulation spine, rooms on both sides,
            // toilets/service cores and the diagonal hall wall at the stair junction.
                WallRun(p, "Pasillo_longitudinal_Wu", new Vector2(-w / 2 + .15f, -2.65f),
                new Vector2(w / 2 - .15f, -2.65f), y, Storey - .08f, .14f, creamF,
                .24f, .95f, DoorHeight, true, darkGlass, metal);
            float[] cross = level == 0
                ? new[] { -7.2f, -3.0f, 1.2f, 5.6f, 9.0f }
                : new[] { -7.2f, -3.0f, 1.2f, 5.6f, 9.0f };
            for (int i = 0; i < cross.Length; i++)
            {
                float z = cross[i];
                WallRun(p, "Tabique_de_ambientes_Wu_" + (i + 1), new Vector2(-w / 2 + .1f, z),
                    new Vector2(w / 2 - .1f, z), y, Storey - .08f, .12f, creamF,
                    .40f, .90f, DoorHeight, true, darkGlass, metal);
            }
            WallRun(p, "Muro_diagonal_nucleo_Wu", new Vector2(-1.0f, -1.6f),
                new Vector2(1.8f, 4.2f), y, Storey - .08f, .14f, creamF,
                .43f, .95f, DoorHeight, true, darkGlass, metal);
        }

        // Separate covered route: its direction is set by the two prefab positions,
        // not an axis-aligned filler box. The glazed sides leave the circulation visible.
        static void BuildDiagonalWalk(Transform eRoot, Vector3 fInE)
        {
            const float eW = 24.30f, eD = 9.76f, fW = 11.85f, fD = 22.91f;
            // A-01 locates the stair/corridor in the closed inside angle between
            // the north face of E and the south face of F. Keep both buildings in place.
            Vector2 eDoor = new Vector2(-7.0f, eD / 2);
            Vector2 fDoor = new Vector2(fInE.x + 4.74f, fInE.z - fD / 2);
            Vector2 axis = fDoor - eDoor;
            float length = axis.magnitude;
            if (length < .15f || length > 6f)
            {
                Debug.LogWarning("E-F diagonal route skipped: endpoints are not adjacent (" + length.ToString("F2") + " m).");
                return;
            }
            Vector2 direction = axis / length;
            Vector2 normal = new Vector2(-direction.y, direction.x);
            Vector2 center = (eDoor + fDoor) * .5f;
            float angle = Mathf.Atan2(direction.x, direction.y) * Mathf.Rad2Deg;
            Transform link = Group(eRoot, "Union_diagonal_transitable_E_F");
            float width = 2.05f;
            float walkY = -.05f;
            Box(link, "Piso_diagonal_sin_solape", new Vector3(center.x, walkY, center.y),
                new Vector3(width, .12f, length + .06f), paving, true, angle);
            for (int side = -1; side <= 1; side += 2)
            {
                Vector2 rail = center + normal * side * (width / 2);
                Box(link, "Vidrio_lateral_ruta_diagonal", new Vector3(rail.x, 1.25f, rail.y),
                    new Vector3(.045f, 2.48f, length - .06f), glass, false, angle);
                Box(link, "Pasamanos_diagonal", new Vector3(rail.x, 2.56f, rail.y),
                    new Vector3(.075f, .08f, length - .06f), metal, false, angle);
            }
            Box(link, "Dintel_ligero_union_diagonal", new Vector3(center.x, 3.28f, center.y),
                new Vector3(width, .18f, length + .10f), creamF, false, angle);
            // The door leaves at both ends sit in the wall openings generated above.
            Debug.Log("Diagonal E-F route: " + length.ToString("F2") + " m at " + angle.ToString("F1") + " degrees.");
        }

        static void WindowWall(Transform p, string name, Vector2 a, Vector2 b, float y, float span,
            int level, Material wall, Material glazing, Material frame, bool connectorDoor = false)
        {
            const float sill = .94f, head = 2.55f;
            Vector2 fullDir = (b - a).normalized;
            float fullLength = Vector2.Distance(a, b);
            if (connectorDoor && level == 0 && fullLength > 2.2f)
            {
                const float centerFromStart = .755f, doorWidth = 1.0f;
                float leftLength = centerFromStart - doorWidth / 2;
                float rightStart = centerFromStart + doorWidth / 2;
                WindowWall(p, name + "_antes_puerta", a, a + fullDir * leftLength, y,
                    leftLength, level, wall, glazing, frame);
                WindowWall(p, name + "_despues_puerta", a + fullDir * rightStart, b, y,
                    fullLength - rightStart, level, wall, glazing, frame);
                DoorOpening(p, "Puerta_diagonal_acceso_Wu", a + fullDir * centerFromStart,
                    fullDir, y, doorWidth, DoorHeight, Wall, wall, glass, frame);
                return;
            }
            int bays = Mathf.Clamp(Mathf.RoundToInt(span / 2.3f), 4, 12);
            float len = Vector2.Distance(a, b);
            Vector2 direction = (b - a).normalized;
            float angle = Mathf.Atan2(direction.x, direction.y) * Mathf.Rad2Deg;
            if (len < .85f)
            {
                Vector2 c = (a + b) * .5f;
                Box(p, name + "_machon_extremo", new Vector3(c.x, y + Storey / 2, c.y),
                    new Vector3(Wall, Storey, len), wall, true, angle);
                return;
            }
            for (int i = 0; i < bays; i++)
            {
                float centerT = (i + .5f) / bays;
                Vector2 c = a + (b - a) * centerT;
                float opening = len / bays - .24f;
                Box(p, name + "_Antepecho", new Vector3(c.x, y + sill / 2, c.y),
                    new Vector3(Wall, sill, opening), wall, true, angle);
                Box(p, name + "_Vidrio", new Vector3(c.x, y + (sill + head) / 2, c.y),
                    new Vector3(.055f, head - sill, opening), glazing, false, angle);
                Box(p, name + "_Dintel", new Vector3(c.x, y + (head + Storey) / 2, c.y),
                    new Vector3(Wall, Storey - head, opening), wall, true, angle);
                if (i > 0)
                {
                    Vector2 mullion = a + (b - a) * (i / (float)bays);
                    Box(p, name + "_Pilastra", new Vector3(mullion.x, y + Storey / 2, mullion.y),
                        new Vector3(.24f, Storey, .16f), wall, true, angle);
                }
                Box(p, name + "_Travesano", new Vector3(c.x, y + head, c.y),
                    new Vector3(.06f, .045f, opening), frame, false, angle);
            }
        }

        static void EndWall(Transform p, string name, float x, float y, float d, Material mat, bool slots)
        {
            if (!slots)
            {
                Box(p, name, new Vector3(x, y + Storey / 2, 0), new Vector3(Wall, Storey, d), mat, true);
                PanelJointsOnX(p, name + "_juntas", x, y, d, (int)Mathf.Sign(x));
                return;
            }
            SlitWall(p, name, x, y, d, (int)Mathf.Sign(x), mat, darkGlass, new[] { -1.45f, 0f, 1.45f });
            PanelJointsOnX(p, name + "_juntas", x, y, d, (int)Mathf.Sign(x));
        }

        static void SlitWall(Transform p, string name, float x, float y, float span, int outward,
            Material wall, Material glazing, float[] centers)
        {
            const float slotW = .52f, slotBottom = 2.49f, slotTop = 2.67f;
            Box(p, name + "_Muro_inferior", new Vector3(x, y + slotBottom / 2, 0),
                new Vector3(Wall, slotBottom, span), wall, true);
            Box(p, name + "_Muro_superior", new Vector3(x, y + (slotTop + Storey) / 2, 0),
                new Vector3(Wall, Storey - slotTop, span), wall, true);
            float cursor = -span / 2;
            for (int i = 0; i < centers.Length; i++)
            {
                float left = centers[i] - slotW / 2;
                if (left > cursor + .01f)
                    Box(p, name + "_Machon", new Vector3(x, y + (slotBottom + (slotTop - slotBottom) / 2),
                        (cursor + left) / 2), new Vector3(Wall, slotTop - slotBottom, left - cursor), wall, true);
                Box(p, name + "_Ventana_hendida", new Vector3(x - outward * .012f,
                    y + (slotBottom + slotTop) / 2, centers[i]), new Vector3(.045f, slotTop - slotBottom, slotW), glazing, false);
                cursor = centers[i] + slotW / 2;
            }
            if (span / 2 > cursor + .01f)
                Box(p, name + "_Machon", new Vector3(x, y + (slotBottom + slotTop) / 2,
                    (cursor + span / 2) / 2), new Vector3(Wall, slotTop - slotBottom, span / 2 - cursor), wall, true);
        }

        static void PanelJointsOnX(Transform p, string name, float x, float y, float span, int outward)
        {
            float surface = x + outward * (Wall / 2 + .008f);
            for (float z = -span / 2 + 1.55f; z < span / 2; z += 2.45f)
                Box(p, name + "_vertical", new Vector3(surface, y + Storey / 2, z),
                    new Vector3(.012f, Storey - .08f, .012f), metal, false);
            for (float seamY = .92f; seamY < Storey; seamY += 1.18f)
                Box(p, name + "_horizontal", new Vector3(surface, y + seamY, 0),
                    new Vector3(.012f, .012f, span), metal, false);
        }

        static void WallRun(Transform p, string name, Vector2 a, Vector2 b, float y, float height,
            float thickness, Material wall, float doorT, float doorWidth, float doorHeight,
            bool hasDoor, Material doorMat, Material hardware)
        {
            Vector2 vector = b - a;
            float length = vector.magnitude;
            if (length <= .02f) return;
            Vector2 dir = vector / length;
            float angle = Mathf.Atan2(dir.x, dir.y) * Mathf.Rad2Deg;
            float openingCenter = Mathf.Clamp(doorT, 0, 1) * length;
            float openingStart = hasDoor ? Mathf.Clamp(openingCenter - doorWidth / 2, .08f, length - .08f) : length;
            float openingEnd = hasDoor ? Mathf.Clamp(openingCenter + doorWidth / 2, openingStart, length - .08f) : length;
            float leftLength = openingStart;
            float rightLength = length - openingEnd;
            if (leftLength > .03f)
                WallPiece(p, name + "_izquierda", a + dir * (leftLength / 2), leftLength, y, height, thickness, wall, angle);
            if (rightLength > .03f)
                WallPiece(p, name + "_derecha", a + dir * (openingEnd + rightLength / 2), rightLength, y, height, thickness, wall, angle);
            if (!hasDoor) return;
            float doorH = Mathf.Min(doorHeight, height - .06f);
            float lintelH = height - doorH;
            if (lintelH > .03f)
                Box(p, name + "_dintel", new Vector3((a + dir * openingCenter).x, y + doorH + lintelH / 2,
                    (a + dir * openingCenter).y), new Vector3(doorWidth, lintelH, thickness), wall, true, angle);
            Vector2 dc = a + dir * openingCenter;
            Box(p, name + "_marco_superior", new Vector3(dc.x, y + doorH + .015f, dc.y),
                new Vector3(doorWidth, .045f, .075f), hardware, false, angle);
            Vector2 normal = new Vector2(-dir.y, dir.x);
            foreach (int side in new[] { -1, 1 })
            {
                Vector2 jamb = dc + normal * side * (doorWidth / 2);
                Box(p, name + "_jamba_metalica", new Vector3(jamb.x, y + doorH / 2, jamb.y),
                    new Vector3(.045f, doorH, .075f), hardware, false, angle);
            }
            Box(p, name + "_hoja", new Vector3(dc.x, y + doorH / 2, dc.y),
                new Vector3(doorWidth - .07f, doorH - .04f, .045f), doorMat, false, angle);
            Box(p, name + "_manija", new Vector3(dc.x + dir.x * (doorWidth * .34f), y + 1.02f,
                dc.y + dir.y * (doorWidth * .34f)), new Vector3(.035f, .24f, .045f), hardware, false, angle);
        }

        static void WallPiece(Transform p, string name, Vector2 center, float length,
            float y, float height, float thickness, Material mat, float angle)
        {
            Box(p, name, new Vector3(center.x, y + height / 2, center.y),
                new Vector3(thickness, height, length), mat, true, angle);
        }

        static void DoorOpening(Transform p, string name, Vector2 center, Vector2 along,
            float y, float width, float height, float thickness, Material wall, Material door, Material hardware)
        {
            Vector2 direction = along.normalized;
            float angle = Mathf.Atan2(direction.x, direction.y) * Mathf.Rad2Deg;
            Vector2 side = new Vector2(-direction.y, direction.x);
            foreach (int s in new[] { -1, 1 })
            {
                Vector2 jamb = center + side * s * (width / 2 + thickness / 2);
                Box(p, name + "_jamba", new Vector3(jamb.x, y + height / 2, jamb.y),
                    new Vector3(thickness, height, thickness), wall, true, angle);
            }
            Box(p, name + "_dintel", new Vector3(center.x, y + Storey - (Storey - height) / 2, center.y),
                new Vector3(width + thickness * 2, Storey - height, thickness), wall, true, angle);
            Box(p, name + "_hoja_vidriada", new Vector3(center.x, y + height / 2, center.y),
                new Vector3(width, height, .055f), door, false, angle);
            Box(p, name + "_marco_superior", new Vector3(center.x, y + height, center.y),
                new Vector3(width + .08f, .045f, .08f), hardware, false, angle);
            foreach (int s in new[] { -1, 1 })
            {
                Vector2 jamb = center + side * s * (width / 2);
                Box(p, name + "_perfil_jamba", new Vector3(jamb.x, y + height / 2, jamb.y),
                    new Vector3(.045f, height, .08f), hardware, false, angle);
            }
        }

        static void Slab(Transform p, string name, Vector3 center, float w, float d,
            float y, float thickness, Material mat)
        {
            Box(p, name, new Vector3(center.x, y, center.z), new Vector3(w, thickness, d), mat, true);
        }

        static void Parapet(Transform p, float w, float d, float roofY, Material mat)
        {
            float h = .75f, t = .16f;
            Box(p, "Pretil_frontal", new Vector3(0, roofY + h / 2, -d / 2 + t / 2), new Vector3(w, h, t), mat, true);
            Box(p, "Pretil_trasero", new Vector3(0, roofY + h / 2, d / 2 - t / 2), new Vector3(w, h, t), mat, true);
            Box(p, "Pretil_izquierdo", new Vector3(-w / 2 + t / 2, roofY + h / 2, 0), new Vector3(t, h, d - 2 * t), mat, true);
            Box(p, "Pretil_derecho", new Vector3(w / 2 - t / 2, roofY + h / 2, 0), new Vector3(t, h, d - 2 * t), mat, true);
        }

        static Transform Group(Transform parent, string name)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            return go.transform;
        }

        static void Box(Transform parent, string name, Vector3 center, Vector3 size,
            Material material, bool collider, float yAngle = 0)
        {
            if (size.x <= .001f || size.y <= .001f || size.z <= .001f) return;
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.localPosition = center;
            go.transform.localRotation = Quaternion.Euler(0, yAngle, 0);
            go.transform.localScale = size;
            var renderer = go.GetComponent<Renderer>();
            renderer.sharedMaterial = material;
            if (material == glass || material == darkGlass)
            {
                renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                renderer.receiveShadows = false;
            }
            if (!collider) UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
        }
    }
}
