using System;
using UnityEditor;
using UnityEngine;

namespace UPCH.Campus.Editor
{
    /// <summary>
    /// Rebuilds the E (Víctor Alzamora) and F (Wu) prefab geometry against sheets
    /// A-01, A-02 and A-03. All dimensions in this file are metres in plan coordinates.
    /// Floors are single, non-moving static slabs; openings are actual gaps in walls.
    /// </summary>
    public static class ReconstruirPabellonesEF
    {
        const string EPath = "Assets/UPCH/Campus/Generated/Buildings/E.prefab";
        const string FPath = "Assets/UPCH/Campus/Generated/Buildings/F.prefab";
        const float Storey = 3.45f;
        const float Wall = .18f;
        const float DoorHeight = 2.12f;

        static Material creamE, creamF, glass, darkGlass, metal, paving;

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
                BuildAlzamoraLobby(e.transform, fLocalInE);

                PrefabUtility.SaveAsPrefabAsset(e, EPath);
                PrefabUtility.SaveAsPrefabAsset(f, FPath);
                AssetDatabase.SaveAssets();
                Debug.Log("EF_INTEGRATED_LOBBY: E entrance belongs to its oblique two-storey vestibule; recessed ground floor, aligned doors, independent Wu courtyard entrance and furnished interiors saved.");
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
                if (level == 0)
                    Slab(floor, "Losa_unica_sin_solapes", Vector3.zero, w, d, y - .09f, .18f, paving);
                else
                    SlabWithOpening(floor, "Losa_E_hueco_escalera", w, d, y - .09f, .18f,
                        -1.55f, 3.0f, 2.65f, 3.10f, paving);
                BuildAlzamoraFront(floor, y, level, w, d);
                BuildAlzamoraBack(floor, y, level, w, d);
                EndWall(floor, "Muro_lateral_izquierdo", -w / 2, y, d, creamE, true);
                EndWall(floor, "Muro_lateral_derecho", w / 2, y, d, creamE, true);
                AlzamoraPartitions(floor, y, level, w, d);
                AddStairCore(floor, "Escalera_interior_E", -1.55f, 3.0f, y, creamE, metal);
            }

            float roofY = 3 * Storey;
            SlabWithOpening(body, "Azotea_E_hueco_escalera", w, d, roofY - .08f, .16f,
                -1.55f, 3.0f, 2.65f, 3.10f, creamE);
            Parapet(body, w, d, roofY, creamE);
        }

        static void BuildAlzamoraFront(Transform parent, float y, int floor, float w, float d)
        {
            // The photographed elevation is a continuous cream frame around broad,
            // dark horizontal glazing. Openings have glass only in the opening.
            float z = floor == 0 ? -4.18f : -4.88f;
            float sill = floor == 0 ? .55f : .92f;
            float head = floor == 0 ? 2.75f : 2.62f;
            int bays = 10;
            float bay = w / bays;
            for (int b = 0; b < bays; b++)
            {
                float x = -w / 2 + bay * (b + .5f);
                // The open hall connects directly to E's integrated oblique vestibule.
                if (floor < 2 && b >= 5 && b <= 7) continue;
                bool entry = false;
                bool diagonalAccess = false;
                float opening = bay - .38f;
                if (entry || diagonalAccess)
                {
                    const float doorWidth = .98f;
                    DoorOpening(parent, diagonalAccess ? "Puerta_diagonal_E" : "Puerta_principal_E",
                        new Vector2(x, z), Vector2.right, y, doorWidth, DoorHeight, Wall, creamE, glass, metal);
                    ContinueFacadeSides(parent, x, bay, z, y, sill, head, doorWidth, creamE);
                }
                else
                {
                    Box(parent, "Antepecho_fachada_E", new Vector3(x, y + sill / 2, z),
                        new Vector3(bay, sill, Wall), creamE, true);
                    Box(parent, "Ventanal_cinta_E", new Vector3(x, y + (sill + head) / 2, z - .025f),
                        new Vector3(opening, head - sill, .055f), darkGlass, false);
                    Box(parent, "Dintel_fachada_E", new Vector3(x, y + (head + Storey) / 2, z),
                        new Vector3(bay, Storey - head, Wall), creamE, true);
                }
                if (b > 0)
                    Box(parent, "Pilastra_fachada_E", new Vector3(-w / 2 + bay * b, y + Storey / 2, z),
                        new Vector3(.38f, Storey, Wall), creamE, true);
                if (!entry && !diagonalAccess)
                {
                    Box(parent, "Perfil_horizontal_E", new Vector3(x, y + sill, z - .055f),
                        new Vector3(opening, .045f, .06f), metal, false);
                    Box(parent, "Perfil_superior_E", new Vector3(x, y + head, z - .055f),
                        new Vector3(opening, .045f, .06f), metal, false);
                }
                if (!entry && !diagonalAccess)
                    Box(parent, "Marco_vertical_ventana_E", new Vector3(x, y + (sill + head) / 2, z - .06f),
                        new Vector3(.04f, head - sill, .065f), metal, false);
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
            // The rear elevation remains continuous; access to the diagonal link is
            // placed on the front inner corner after orienting the two pavilion roots.
            Vector2 a = new Vector2(-w / 2, d / 2), b = new Vector2(w / 2, d / 2);
            WindowWall(parent, "Ventanas_traseras_E", a, b, y, w, floor, creamE, darkGlass, metal);
        }

        static void AlzamoraPartitions(Transform p, float y, int floor, float w, float d)
        {
            BuildPlanWalls(p, "E", floor, y, creamE);
            // A-01/A-02 classrooms are on the left of the public hall.
            if (floor < 2)
            {
                for (int r = 0; r < 4; r++)
                    for (int c = 0; c < 3; c++)
                        Desk(p, "E_Aula_" + (floor + 1) + "01", -10.9f + c * 1.5f, .65f + r * .90f, y);
            }
            else
            {
                Desk(p, "E_Sala_NGS", -9.8f, 2.6f, y);
                for (int i = 0; i < 3; i++) Desk(p, "E_Laboratorio_trabajo", 5.8f + i * 1.8f, -2.9f, y);
            }
            Fixtures(p, "E_SH_caballeros", -4.8f, 3.4f, y);
            Fixtures(p, "E_SH_damas", 1.25f, 3.4f, y);
        }

        // Wu's roof plan A-03 gives 11.85 x 22.91 m and +6.35 NPT. A-01/A-02
        // show two occupied levels at -0.55 and +2.90 with matching 3.45 m spacing.
        static void BuildWu(Transform root)
        {
            const float w = 11.85f, d = 24.86f;
            Transform body = Group(root, "F_Wu_planta_completa_11.85x24.86m");
            // A-03: 24.86 m overall, 22.91 m to the start of the stepped roof edge.
            // Extend away from the courtyard so the E/F junction stays at the same datum.
            body.localPosition = new Vector3(0, 0, -.975f);
            for (int level = 0; level < 2; level++)
            {
                float y = level * Storey;
                Transform floor = Group(body, "Nivel_" + (level + 1) + "_NPT_" + (y - .55f).ToString("F2"));
                if (level == 0)
                    Slab(floor, "Losa_unica_sin_solapes", Vector3.zero, w, d, y - .09f, .18f, paving);
                else
                    SlabWithOpening(floor, "Losa_Wu_hueco_escalera", w, d, y - .09f, .18f,
                        -4.20f, -2.7f, 2.65f, 3.10f, paving);
                WuSouthFacade(floor, y, level, w, d);
                WuNorthFacade(floor, y, level, w, d);
                WuSideFacade(floor, y, level, w, d, -1);
                WuSideFacade(floor, y, level, w, d, 1);
                WuPartitions(floor, y, level, w, d);
                AddStairCore(floor, "Escalera_interior_Wu", -4.20f, -2.7f, y, creamF, metal);
            }
            float roofY = 2 * Storey;
            SlabWithOpening(body, "Azotea_Wu_hueco_escalera", w, d, roofY - .08f, .16f,
                -4.20f, -2.7f, 2.65f, 3.10f, creamF);
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
                if (entry)
                {
                    DoorOpening(p, "Puerta_principal_Wu", new Vector2(x, z), Vector2.right,
                        y, paneW, DoorHeight, Wall, creamF, glass, metal);
                    Box(p, "Portal_principal_Wu_pilastra_izquierda", new Vector3(x - 1.30f, y + 1.38f, z - .16f),
                        new Vector3(.16f, 2.76f, .18f), creamF, true);
                    Box(p, "Portal_principal_Wu_pilastra_derecha", new Vector3(x + 1.30f, y + 1.38f, z - .16f),
                        new Vector3(.16f, 2.76f, .18f), creamF, true);
                    Box(p, "Portal_principal_Wu_dintel", new Vector3(x, y + 2.82f, z - .16f),
                        new Vector3(2.78f, .16f, .32f), creamF, true);
                    Box(p, "Umbral_principal_Wu", new Vector3(x, y + .025f, z - .24f),
                        new Vector3(2.40f, .05f, .42f), paving, true);
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
                        new Vector3(.24f, Storey, Wall), creamF, true);
                Box(p, "Travesano_Wu", new Vector3(x, y + head, z - .06f),
                    new Vector3(paneW, .05f, .06f), metal, false);
            }
        }

        static void WuNorthFacade(Transform p, float y, int level, float w, float d)
        {
            float z = d / 2;
            if (level == 0)
            {
                // Door for the glass diagonal connector at the facing end of Wu.
                WallRun(p, "Muro_norte_con_acceso_Wu", new Vector2(-w / 2, z), new Vector2(w / 2, z),
                    y, Storey, Wall, creamF, .10f, .92f, DoorHeight, false, creamF, metal);
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
                WindowWall(p, "Fachada_lateral_ritmada_Wu", a, b, y, d, floor, creamF, darkGlass, metal, connectorDoor: floor == 0);
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
            BuildPlanWalls(p, "F", level, y, creamF);
            // The long hall remains free at level 2; the ground floor has study tables.
            if (level == 0)
                for (int r = 0; r < 3; r++)
                    for (int c = 0; c < 2; c++)
                        Desk(p, "Wu_Sala_estudio", -3.0f + c * 5.4f, 3.5f + r * 2.05f, y);
            for (int i = 0; i < 3; i++) Desk(p, "Wu_Centros_estudiantes", 3.3f, -9.7f + i * 3.4f, y);
            Fixtures(p, "Wu_SH_damas", -4.65f, -5.0f, y);
            Fixtures(p, "Wu_SH_caballeros", -4.65f, .1f, y);
            // A-02's sloping corridor wall is explicit, with three separate entrances.
            if (level == 1)
            {
                Vector2 a = new Vector2(-.3f, -9.6f), b = new Vector2(1.25f, .1f);
                for (int i = 0; i < 3; i++)
                    WallRun(p, "Wu_Pasillo_diagonal_A02", Vector2.Lerp(a,b,i/3f), Vector2.Lerp(a,b,(i+1)/3f),
                        y, Storey-.10f, .12f, creamF, .68f, 1.0f, DoorHeight, true, creamF, metal);
            }
        }

        [Serializable] class PlanFile { public PlanFloor[] floors; }
        [Serializable] class PlanFloor { public string pavilion; public int level; public PlanWall[] walls; public PlanDoor[] doors; }
        [Serializable] class PlanWall { public float x, z, width, depth; }
        [Serializable] class PlanDoor { public float hx, hz, ax, az, bx, bz; }

        static void BuildPlanWalls(Transform p, string pavilion, int level, float y, Material mat)
        {
            var asset = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/UPCH/Editor/AlzamoraWuPlanData.json");
            if (!asset) throw new InvalidOperationException("Missing traced A-01/A-02/A-03 wall data");
            var plan = JsonUtility.FromJson<PlanFile>(asset.text);
            foreach (var floor in plan.floors)
            {
                if (floor.pavilion != pavilion || floor.level != level) continue;
                int index = 0;
                foreach (var wall in floor.walls)
                {
                    // Tread linework is not a partition. Stair voids stay completely open.
                    float sx = pavilion == "E" ? -1.55f : -4.2f;
                    float sz = pavilion == "E" ? 3.0f : -2.7f;
                    if (Mathf.Abs(wall.x-sx) < 1.40f && Mathf.Abs(wall.z-sz) < 1.65f) continue;
                    Box(p, pavilion + "_A0" + (level+1) + "_Tabique_" + (++index),
                        new Vector3(wall.x, y + (Storey-.10f)/2, wall.z),
                        new Vector3(wall.width, Storey-.10f, wall.depth), mat, true);
                }
                foreach (var door in floor.doors)
                {
                    Vector2 hinge = new Vector2(door.hx,door.hz), leaf = new Vector2(door.ax,door.az);
                    Vector2 jamb = new Vector2(door.bx,door.bz), axis = (leaf-hinge).normalized;
                    float width = Vector2.Distance(hinge,leaf);
                    Vector2 center = (hinge+leaf)/2;
                    float yaw = Mathf.Atan2(axis.x,axis.y)*Mathf.Rad2Deg;
                    Box(p,pavilion+"_Puerta_plano_A0"+(level+1),new Vector3(center.x,y+DoorHeight/2,center.y),
                        new Vector3(.045f,DoorHeight,width-.045f),mat,false,yaw);
                    foreach(Vector2 post in new[]{hinge,jamb})
                        Box(p,pavilion+"_Marco_puerta",new Vector3(post.x,y+DoorHeight/2,post.y),
                            new Vector3(.055f,DoorHeight,.055f),metal,false);
                }
            }
        }

        static void Fixtures(Transform p, string name, float x, float z, float y)
        {
            Box(p, name+"_inodoro", new Vector3(x,y+.24f,z), new Vector3(.42f,.48f,.65f), creamE,true);
            Box(p, name+"_tanque", new Vector3(x,y+.58f,z+.3f), new Vector3(.40f,.70f,.15f), creamE,true);
            Box(p, name+"_lavatorio", new Vector3(x+.75f,y+.84f,z), new Vector3(.48f,.16f,.40f), creamE,true);
        }

        static void Desk(Transform p, string name, float x, float z, float y)
        {
            Box(p, name + "_tablero", new Vector3(x, y + .76f, z), new Vector3(1.25f, .06f, .65f), paving, true);
            foreach (int sx in new[] { -1, 1 })
                foreach (int sz in new[] { -1, 1 })
                    Box(p, name + "_pata", new Vector3(x + sx * .51f, y + .36f, z + sz * .23f),
                        new Vector3(.045f, .72f, .045f), metal, false);
            Box(p, name + "_silla_asiento", new Vector3(x, y + .45f, z + .68f),
                new Vector3(.43f, .06f, .43f), creamE, true);
            Box(p, name + "_silla_respaldo", new Vector3(x, y + .72f, z + .87f),
                new Vector3(.43f, .54f, .055f), creamE, false);
        }

        // This entrance is part of E, not a passage with a door at either end.
        // The shallow polygon closes the inside angle and stops at Wu's facing wall.
        static void BuildAlzamoraLobby(Transform root, Vector3 fInE)
        {
            Transform lobby = Group(root, "E_Vestibulo_integrado_entrada_oblicua");
            float junctionZ = -fInE.z + 11.455f;
            float junctionX = -fInE.x - 5.925f;
            Vector2 a = new Vector2(0, -4.88f);
            Vector2 b = new Vector2(junctionX, junctionZ);
            Vector2 c = new Vector2(7.29f, junctionZ);
            Vector2 d = new Vector2(7.29f, -4.88f);
            Vector2[] footprint = { a, b, c, d };
            PolygonSlab(lobby, "Piso_vestibulo_E", footprint, -.135f, .045f, paving);
            PolygonSlab(lobby, "Entrepiso_vestibulo_E", footprint, Storey - .18f, Storey, creamE);
            PolygonSlab(lobby, "Cubierta_vestibulo_E", footprint, 2 * Storey - .18f, 2 * Storey, creamE);
            // The stone-clad entrance pier and glazed double leaf lie on the oblique face.
            WallRun(lobby, "E_Entrada_principal_diagonal", a, b, 0, Storey, .22f,
                creamE, .53f, 1.60f, 2.45f, true, darkGlass, metal);
            WindowWall(lobby, "E_Ventanal_superior_oblicuo", a, b, Storey,
                Vector2.Distance(a, b), 1, creamE, darkGlass, metal);
            WindowWall(lobby, "E_Retorno_superior_ventanal", b, c, Storey,
                Vector2.Distance(b, c), 1, creamE, darkGlass, metal);
            // Ground-level return is recessed to leave the entrance under the upper volume.
            WallRun(lobby, "E_Retorno_inferior", b, c, 0, Storey, Wall,
                creamE, .5f, 1.0f, DoorHeight, false, creamE, metal);
            WallRun(lobby, "E_Cierre_lateral_vestibulo", c, d, 0, Storey * 2, Wall,
                creamE, .5f, 1.0f, DoorHeight, false, creamE, metal);
            Vector2 dir = (b - a).normalized;
            Vector2 normal = new Vector2(-dir.y, dir.x);
            Vector2 dc = Vector2.Lerp(a, b, .53f);
            AddEntranceGarden(lobby, a, b);
            // Two pull handles and a threshold make the entrance readable from the court.
            for (int side = -1; side <= 1; side += 2)
            {
                Vector2 h = dc + dir * side * .16f + normal * .15f;
                Box(lobby, "E_Tirador_puerta_principal", new Vector3(h.x, 1.10f, h.y),
                    new Vector3(.045f, .55f, .045f), metal, false);
            }
            Box(lobby, "E_Mostrador_recepcion", new Vector3(4.8f, .52f, -4.85f),
                new Vector3(1.6f, 1.04f, .58f), creamE, true);
        }

        static void PolygonSlab(Transform parent, string name, Vector2[] points,
            float bottom, float top, Material material)
        {
            int n = points.Length;
            var vertices = new Vector3[n * 2];
            for (int i = 0; i < n; i++)
            {
                vertices[i] = new Vector3(points[i].x, bottom, points[i].y);
                vertices[i + n] = new Vector3(points[i].x, top, points[i].y);
            }
            var indices = new System.Collections.Generic.List<int>();
            for (int i = 1; i < n - 1; i++)
            {
                indices.AddRange(new[] { 0, i, i + 1, n, n + i + 1, n + i });
            }
            for (int i = 0; i < n; i++)
            {
                int j = (i + 1) % n;
                indices.AddRange(new[] { i, n + i, j, j, n + i, n + j });
            }
            var mesh = new Mesh { name = name };
            mesh.vertices = vertices;
            mesh.triangles = indices.ToArray();
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            const string folder = "Assets/UPCH/Campus/Generated/Buildings";
            string path = folder + "/" + name + ".asset";
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (existing) { EditorUtility.CopySerialized(mesh, existing); UnityEngine.Object.DestroyImmediate(mesh); mesh = existing; }
            else AssetDatabase.CreateAsset(mesh, path);
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer), typeof(MeshCollider));
            go.transform.SetParent(parent, false);
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            go.GetComponent<MeshRenderer>().sharedMaterial = material;
            go.GetComponent<MeshCollider>().sharedMesh = mesh;
        }

        static Material GardenMaterial(string name, Color color)
        {
            string path = "Assets/UPCH/Campus/Generated/Materials/" + name + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!mat)
            {
                mat = new Material(creamE) { name = name };
                mat.SetColor("_BaseColor", color);
                mat.color = color;
                AssetDatabase.CreateAsset(mat, path);
            }
            return mat;
        }

        static void AddEntranceGarden(Transform lobby, Vector2 a, Vector2 b)
        {
            Material foliage = GardenMaterial("E_Follaje_entrada", new Color(.16f,.28f,.07f));
            Material soil = GardenMaterial("E_Tierra_jardinera", new Color(.13f,.10f,.065f));
            Material bark = GardenMaterial("E_Troncos_entrada", new Color(.28f,.20f,.12f));
            Material stone = GardenMaterial("E_Piedra_acceso", new Color(.72f,.70f,.60f));
            Transform garden = Group(lobby, "E_Jardinera_de_la_fotografia");
            const float cx = -1.9f, cz = -5.67f, width = 3.35f, depth = 1.55f;
            Box(garden,"Frente_blanco",new Vector3(cx,.34f,cz-depth/2),new Vector3(width,.60f,.12f),creamE,true);
            Box(garden,"Trasera_blanca",new Vector3(cx,.34f,cz+depth/2),new Vector3(width,.60f,.12f),creamE,true);
            foreach(int side in new[]{-1,1})
                Box(garden,"Costado_blanco",new Vector3(cx+side*width/2,.34f,cz),new Vector3(.12f,.60f,depth-.12f),creamE,true);
            Box(garden,"Tierra",new Vector3(cx,.49f,cz),new Vector3(width-.12f,.10f,depth-.12f),soil,false);
            for(int i=0;i<3;i++)
            {
                float x=cx-1.05f+i*1.04f;
                Box(garden,"Tronco_arbusto",new Vector3(x,1.18f,cz),new Vector3(.10f,1.30f,.10f),bark,false);
                for(int j=0;j<7;j++)
                {
                    float angle=j*2.39996f;
                    var leaf=GameObject.CreatePrimitive(PrimitiveType.Sphere);
                    leaf.name="Copa_arbusto_"+i+"_"+j;
                    leaf.transform.SetParent(garden,false);
                    leaf.transform.localPosition=new Vector3(x+Mathf.Cos(angle)*.22f,1.7f+j*.075f,cz+Mathf.Sin(angle)*.20f);
                    leaf.transform.localScale=new Vector3(.72f,.80f,.68f);
                    leaf.GetComponent<Renderer>().sharedMaterial=foliage;
                    UnityEngine.Object.DestroyImmediate(leaf.GetComponent<Collider>());
                }
            }
            for(int i=0;i<14;i++)
                BoxRotated(garden,"Hojas_bajas",new Vector3(cx-width*.42f+i*.21f,.75f,cz-.36f),
                    new Vector3(.055f,.50f,.09f),foliage,false,Quaternion.Euler(0,i*41,22));
            Vector2 dir=(b-a).normalized, outward=new Vector2(dir.y,-dir.x);
            float length=Vector2.Distance(a,b), panelWidth=Mathf.Max(.35f,length*.47f-.88f);
            Vector2 center=b-dir*panelWidth/2+outward*.13f;
            float yaw=Mathf.Atan2(dir.x,dir.y)*Mathf.Rad2Deg;
            Box(lobby,"E_Revestimiento_piedra_derecha_entrada",new Vector3(center.x,1.55f,center.y),
                new Vector3(.045f,3.0f,panelWidth),stone,false,yaw);
        }

        static void WindowWall(Transform p, string name, Vector2 a, Vector2 b, float y, float span,
            int level, Material wall, Material glazing, Material frame, bool connectorDoor = false)
        {
            const float sill = .94f, head = 2.55f;
            Vector2 fullDir = (b - a).normalized;
            float fullLength = Vector2.Distance(a, b);
            if (connectorDoor && level == 0 && fullLength > 2.2f)
            {
                float centerFromStart = fullLength * .52f; const float doorWidth = 1.40f;
                float leftLength = centerFromStart - doorWidth / 2;
                float rightStart = centerFromStart + doorWidth / 2;
                WindowWall(p, name + "_antes_puerta", a, a + fullDir * leftLength, y,
                    leftLength, level, wall, glazing, frame);
                WindowWall(p, name + "_despues_puerta", a + fullDir * rightStart, b, y,
                    fullLength - rightStart, level, wall, glazing, frame);
                DoorOpening(p, "Puerta_principal_Wu_hacia_patio", a + fullDir * centerFromStart,
                    fullDir, y, doorWidth, DoorHeight, Wall, wall, glass, frame);
                return;
            }
            int bays = Mathf.Clamp(Mathf.RoundToInt(span / 2.3f), 1, 12);
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
                        new Vector3(Wall, Storey, .24f), wall, true, angle);
                }
                Box(p, name + "_Travesano", new Vector3(c.x, y + head, c.y),
                    new Vector3(.06f, .045f, opening), frame, false, angle);
            }
            foreach (Vector2 end in new[] { a + direction * .06f, b - direction * .06f })
                Box(p, name + "_Cierre_extremo", new Vector3(end.x,y+Storey/2,end.y),
                    new Vector3(Wall,Storey,.12f),wall,true,angle);
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
                    (a + dir * openingCenter).y), new Vector3(thickness, lintelH, doorWidth), wall, true, angle);
            Vector2 dc = a + dir * openingCenter;
            Box(p, name + "_marco_superior", new Vector3(dc.x, y + doorH + .015f, dc.y),
                new Vector3(.075f, .045f, doorWidth), hardware, false, angle);
            Vector2 normal = new Vector2(-dir.y, dir.x);
            foreach (int side in new[] { -1, 1 })
            {
                Vector2 jamb = dc + dir * side * (doorWidth / 2);
                Box(p, name + "_jamba_metalica", new Vector3(jamb.x, y + doorH / 2, jamb.y),
                    new Vector3(.045f, doorH, .075f), hardware, false, angle);
            }
            Box(p, name + "_hoja", new Vector3(dc.x, y + doorH / 2, dc.y),
                new Vector3(.045f, doorH - .04f, doorWidth - .07f), doorMat, false, angle);
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
                Vector2 jamb = center + direction * s * (width / 2 + thickness / 2);
                Box(p, name + "_jamba", new Vector3(jamb.x, y + height / 2, jamb.y),
                    new Vector3(thickness, height, thickness), wall, true, angle);
            }
            Box(p, name + "_dintel", new Vector3(center.x, y + Storey - (Storey - height) / 2, center.y),
                new Vector3(thickness, Storey - height, width + thickness * 2), wall, true, angle);
            Box(p, name + "_hoja_vidriada", new Vector3(center.x, y + height / 2, center.y),
                new Vector3(.055f, height, width), door, false, angle);
            Box(p, name + "_marco_superior", new Vector3(center.x, y + height, center.y),
                new Vector3(.08f, .045f, width + .08f), hardware, false, angle);
            foreach (int s in new[] { -1, 1 })
            {
                Vector2 jamb = center + direction * s * (width / 2);
                Box(p, name + "_perfil_jamba", new Vector3(jamb.x, y + height / 2, jamb.y),
                    new Vector3(.045f, height, .08f), hardware, false, angle);
            }
        }

        static void Slab(Transform p, string name, Vector3 center, float w, float d,
            float y, float thickness, Material mat)
        {
            if (Mathf.Abs(y + thickness / 2) < .001f) y += .045f;
            Box(p, name, new Vector3(center.x, y, center.z), new Vector3(w, thickness, d), mat, true);
        }

        static void SlabWithOpening(Transform p, string name, float w, float d, float y,
            float thickness, float cx, float cz, float openingW, float openingD, Material mat)
        {
            float x0 = cx - openingW / 2, x1 = cx + openingW / 2;
            float z0 = cz - openingD / 2, z1 = cz + openingD / 2;
            if (x0 <= -w / 2 || x1 >= w / 2 || z0 <= -d / 2 || z1 >= d / 2)
            {
                Slab(p, name + "_continua", Vector3.zero, w, d, y, thickness, mat);
                return;
            }
            Box(p, name + "_sur", new Vector3(0, y, (-d / 2 + z0) / 2),
                new Vector3(w, thickness, z0 + d / 2), mat, true);
            Box(p, name + "_norte", new Vector3(0, y, (z1 + d / 2) / 2),
                new Vector3(w, thickness, d / 2 - z1), mat, true);
            Box(p, name + "_oeste", new Vector3((-w / 2 + x0) / 2, y, (z0 + z1) / 2),
                new Vector3(x0 + w / 2, thickness, openingD), mat, true);
            Box(p, name + "_este", new Vector3((x1 + w / 2) / 2, y, (z0 + z1) / 2),
                new Vector3(w / 2 - x1, thickness, openingD), mat, true);
        }

        static void AddStairCore(Transform p, string name, float cx, float cz, float y,
            Material treadMaterial, Material railMaterial)
        {
            const int risersPerFlight = 10;
            const float run = 2.80f, tread = run / risersPerFlight, lane = 1.08f, gap = .18f;
            float riser = Storey / (risersPerFlight * 2);
            float zStart = cz - run / 2;
            float xA = cx - (lane + gap) / 2, xB = cx + (lane + gap) / 2;

            for (int i = 0; i < risersPerFlight; i++)
            {
                float h = riser * (i + 1);
                float z = zStart + tread * (i + .5f);
                Box(p, name + "_tramo1_peldaño_" + (i + 1), new Vector3(xA, y + h / 2, z),
                    new Vector3(lane, h, tread), treadMaterial, true);

                h = riser * (i + 1);
                z = cz + run / 2 - tread * (i + .5f);
                Box(p, name + "_tramo2_peldaño_" + (i + 1),
                    new Vector3(xB, y + Storey / 2 + h / 2, z),
                    new Vector3(lane, h, tread), treadMaterial, true);
            }

            Box(p, name + "_descanso_intermedio", new Vector3(cx, y + Storey / 2 - .06f, cz + run / 2 + .075f),
                new Vector3(lane * 2 + gap, .12f, .15f), treadMaterial, true);
            Box(p, name + "_descanso_superior", new Vector3(cx, y + Storey - .06f, cz - run / 2 - .075f),
                new Vector3(lane * 2 + gap, .12f, .15f), treadMaterial, true);

            AddStairRail(p, name + "_pasamanos_tramo1", xA - lane / 2, y, zStart,
                y + Storey / 2, cz + run / 2, railMaterial);
            AddStairRail(p, name + "_pasamanos_tramo1", xA + lane / 2, y, zStart,
                y + Storey / 2, cz + run / 2, railMaterial);
            AddStairRail(p, name + "_pasamanos_tramo2", xB - lane / 2, y + Storey / 2,
                cz + run / 2, y + Storey, zStart, railMaterial);
            AddStairRail(p, name + "_pasamanos_tramo2", xB + lane / 2, y + Storey / 2,
                cz + run / 2, y + Storey, zStart, railMaterial);
        }

        static void AddStairRail(Transform p, string name, float x, float lowY, float lowZ,
            float highY, float highZ, Material material)
        {
            Vector3 start = new Vector3(x, lowY + .88f, lowZ);
            Vector3 end = new Vector3(x, highY + .88f, highZ);
            Vector3 delta = end - start;
            Quaternion rotation = Quaternion.LookRotation(delta.normalized, Vector3.up);
            BoxRotated(p, name, (start + end) / 2, new Vector3(.055f, .055f, delta.magnitude),
                material, false, rotation);
            for (int i = 0; i <= 5; i++)
            {
                float t = i / 5f;
                Vector3 foot = Vector3.Lerp(new Vector3(x, lowY, lowZ), new Vector3(x, highY, highZ), t);
                Box(p, name + "_poste_" + i, foot + Vector3.up * .45f,
                    new Vector3(.045f, .90f, .045f), material, false);
            }
        }

        static void AddSanitaryCore(Transform p, string name, float cx, float cz, float y,
            Material wall, Material ceramic, Material hardware, Material mirror)
        {
            const float width = 3.60f, depth = 2.30f, height = 2.25f, door = .90f;
            float sideW = (width - door) / 2;
            float frontZ = cz - depth / 2, backZ = cz + depth / 2;
            Box(p, name + "_muro_fondo", new Vector3(cx, y + height / 2, backZ),
                new Vector3(width, height, .10f), wall, true);
            Box(p, name + "_muro_lateral_izquierdo", new Vector3(cx - width / 2, y + height / 2, cz),
                new Vector3(.10f, height, depth), wall, true);
            Box(p, name + "_muro_lateral_derecho", new Vector3(cx + width / 2, y + height / 2, cz),
                new Vector3(.10f, height, depth), wall, true);
            foreach (int side in new[] { -1, 1 })
                Box(p, name + "_muro_frontal_machón", new Vector3(cx + side * (door / 2 + sideW / 2),
                    y + height / 2, frontZ), new Vector3(sideW, height, .10f), wall, true);
            Box(p, name + "_dintel_puerta", new Vector3(cx, y + height - .10f, frontZ),
                new Vector3(door, .20f, .10f), wall, true);

            Box(p, name + "_tabique_privacidad", new Vector3(cx, y + 1.0f, cz + .55f),
                new Vector3(.08f, 2.0f, 1.15f), wall, true);
            foreach (int side in new[] { -1, 1 })
            {
                float x = cx + side * .88f;
                Box(p, name + "_inodoro_base", new Vector3(x, y + .20f, cz + .57f),
                    new Vector3(.48f, .36f, .62f), ceramic, true);
                Box(p, name + "_inodoro_asiento", new Vector3(x, y + .40f, cz + .38f),
                    new Vector3(.46f, .055f, .48f), wall, false);
                Box(p, name + "_tanque", new Vector3(x, y + .58f, cz + .91f),
                    new Vector3(.40f, .68f, .18f), ceramic, true);
            }
            Box(p, name + "_lavatorio", new Vector3(cx, y + .88f, cz - .60f),
                new Vector3(.74f, .16f, .42f), ceramic, true);
            Box(p, name + "_pedestal_lavatorio", new Vector3(cx, y + .42f, cz - .60f),
                new Vector3(.14f, .76f, .14f), ceramic, true);
            Box(p, name + "_griferia", new Vector3(cx, y + 1.02f, cz - .80f),
                new Vector3(.10f, .18f, .08f), hardware, false);
            Box(p, name + "_espejo", new Vector3(cx, y + 1.62f, cz - depth / 2 + .12f),
                new Vector3(.85f, .78f, .035f), mirror, false);
        }

        static void BoxRotated(Transform parent, string name, Vector3 center, Vector3 size,
            Material material, bool collider, Quaternion rotation)
        {
            if (size.x <= .001f || size.y <= .001f || size.z <= .001f) return;
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.localPosition = center;
            go.transform.localRotation = rotation;
            go.transform.localScale = size;
            go.GetComponent<Renderer>().sharedMaterial = material;
            if (!collider) UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
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
