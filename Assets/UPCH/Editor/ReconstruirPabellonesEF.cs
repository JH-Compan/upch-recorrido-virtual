using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace UPCH.Campus.Editor
{
    /// <summary>
    /// Reconstruye el volumen exterior de E (Víctor Alzamora) y F (Wu) a partir
    /// de las cotas indicadas en las láminas A-01..A-03. Los dos prefabs conservan
    /// su ubicación georreferenciada; un corredor acristalado salva el intervalo.
    /// </summary>
    public static class ReconstruirPabellonesEF
    {
        const string EPath = "Assets/UPCH/Campus/Generated/Buildings/E.prefab";
        const string FPath = "Assets/UPCH/Campus/Generated/Buildings/F.prefab";
        const float Storey = 3.45f;

        static Material cream, glass, darkGlass, metal, paving;

        [MenuItem("Tools/UPCH/Rebuild Pabellones E y F - Alzamora y Wu")]
        public static void Run()
        {
            cream = AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Campus/Generated/Materials/Pabellon E.mat");
            var creamF = AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Campus/Generated/Materials/Pabellon F.mat");
            glass = AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Arte/Edificios/D/Materiales/VidrioFachadaClara.mat");
            darkGlass = AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Arte/Edificios/D/Materiales/VidrioOscuro.mat");
            metal = AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Arte/Edificios/D/Materiales/Aluminio.mat");
            paving = AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Arte/Edificios/D/Materiales/PiedraGris.mat");
            if (!cream || !creamF || !glass || !darkGlass || !metal || !paving)
                throw new InvalidOperationException("Falta un material requerido para reconstruir E y F.");

            var e = PrefabUtility.LoadPrefabContents(EPath);
            var f = PrefabUtility.LoadPrefabContents(FPath);
            try
            {
                var ePosition = e.transform.position;
                var fPosition = f.transform.position;
                ClearRoot(e);
                ClearRoot(f);

                float dx = fPosition.x - ePosition.x;
                float sharedLeft = Mathf.Max(-24.30f / 2, dx - 11.85f / 2);
                float sharedRight = Mathf.Min(24.30f / 2, dx + 11.85f / 2);
                float sharedCenterX = (sharedLeft + sharedRight) / 2;
                float eBay = 24.30f / Mathf.Clamp(Mathf.RoundToInt(24.30f / 2.25f), 5, 12);
                int eBayIndex = Mathf.Clamp(Mathf.RoundToInt((sharedCenterX + 24.30f / 2) / eBay - .5f), 0,
                    Mathf.Clamp(Mathf.RoundToInt(24.30f / 2.25f), 5, 12) - 1);
                float corridorCenterX = -24.30f / 2 + eBay * (eBayIndex + .5f);

                // Cotas de planta: E = 24.30 x 9.76 m; F/Wu = 11.85 x 22.91 m.
                BuildPavilion(e.transform, "E - Víctor Alzamora", 24.30f, 9.76f, 3, cream,
                    facadeLongitudinal: true, connectorDoorX: corridorCenterX);
                BuildPavilion(f.transform, "F - Wu", 11.85f, 22.91f, 2, creamF,
                    facadeLongitudinal: false, connectorDoorX: corridorCenterX - dx);
                BuildConnector(e.transform, ePosition, fPosition);

                PrefabUtility.SaveAsPrefabAsset(e, EPath);
                PrefabUtility.SaveAsPrefabAsset(f, FPath);
                AssetDatabase.SaveAssets();
                EditorSceneManager.MarkAllScenesDirty();
                Debug.Log("PABELLONES_EF_RECONSTRUIDOS: E 24.30x9.76 m / 3 niveles; F 11.85x22.91 m / 2 niveles; corredor acristalado E-F.");
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(e);
                PrefabUtility.UnloadPrefabContents(f);
            }
        }

        static void ClearRoot(GameObject root)
        {
            for (int i = root.transform.childCount - 1; i >= 0; --i)
                UnityEngine.Object.DestroyImmediate(root.transform.GetChild(i).gameObject);
            foreach (var c in root.GetComponents<Component>())
                if (!(c is Transform)) UnityEngine.Object.DestroyImmediate(c);
        }

        static void BuildPavilion(Transform root, string label, float width, float depth, int floors,
            Material wallMaterial, bool facadeLongitudinal, float connectorDoorX)
        {
            var mass = Group(root, label);
            for (int floor = 0; floor < floors; floor++)
            {
                float y = floor * Storey;
                var level = Group(mass, "Nivel_" + (floor + 1) + "_NPT_" + (floor * Storey).ToString("F2"));
                // Interior slab stops at the inner face of the exterior wall.
                Box(level, "Losa_de_piso", new Vector3(0, y - .09f, 0),
                    new Vector3(width - .28f, .18f, depth - .28f), paving, true);
                var facade = Group(level, "Fachada");
                LongFacade(facade, width, depth, y, floor, wallMaterial,
                    facadeLongitudinal ? connectorDoorX : float.NaN, facadeLongitudinal);
                ShortFacade(facade, width, depth, y, floor, wallMaterial,
                    facadeLongitudinal ? float.NaN : connectorDoorX, facadeLongitudinal);
            }

            float roofY = floors * Storey;
            Box(mass, "Azotea", new Vector3(0, roofY - .09f, 0),
                new Vector3(width, .18f, depth), wallMaterial, true);
            // Continuous parapet on the roof, with a restrained fascia matching the photos.
            Box(mass, "Pretil_frontal", new Vector3(0, roofY + .375f, -depth / 2 + .10f),
                new Vector3(width, .75f, .20f), wallMaterial, true);
            Box(mass, "Pretil_trasero", new Vector3(0, roofY + .375f, depth / 2 - .10f),
                new Vector3(width, .75f, .20f), wallMaterial, true);
            Box(mass, "Pretil_izquierdo", new Vector3(-width / 2 + .10f, roofY + .375f, 0),
                new Vector3(.20f, .75f, depth - .4f), wallMaterial, true);
            Box(mass, "Pretil_derecho", new Vector3(width / 2 - .10f, roofY + .375f, 0),
                new Vector3(.20f, .75f, depth - .4f), wallMaterial, true);
        }

        // The main photo shows continuous horizontal glazing; the opaque wall bands
        // and slim piers are separate pieces, so no solid wall sits behind a window.
        static void LongFacade(Transform p, float width, float depth, float y, int floor,
            Material wallMaterial, float doorX, bool alongX)
        {
            float span = alongX ? width : depth;
            float facadeZ = alongX ? depth / 2 : width / 2;
            float pane = .055f;
            float bottom = floor == 0 ? .25f : .88f;
            float top = floor == 0 ? Storey - .14f : Storey - .62f;
            float openingHeight = top - bottom;
            int bays = Mathf.Clamp(Mathf.RoundToInt(span / 2.25f), 5, 12);
            float bay = span / bays;
            foreach (int side in new[] { -1, 1 })
            {
                float z = side * facadeZ;
                for (int b = 0; b < bays; b++)
                {
                    float center = -span / 2 + bay * (b + .5f);
                    bool doorBay = side > 0 && floor == 0 && !float.IsNaN(doorX) && Mathf.Abs(center - doorX) < bay * .58f;
                    float paneWidth = bay - .28f;
                    if (doorBay)
                    {
                        // Door opening is an explicit void with glass leaves, no wall behind it.
                        Box(p, "Montante_entrada", LocalAlong(center - paneWidth / 2 - .09f, y, z, alongX),
                            LocalAlongSize(.12f, Storey, .13f, alongX), metal, true);
                        Box(p, "Vidrio_puerta", LocalAlong(center, y + Storey / 2, z, alongX),
                            LocalAlongSize(paneWidth, Storey - .12f, pane, alongX), glass, false);
                        Box(p, "Tirador_puerta", LocalAlong(center, y + 1.05f, z - side * .08f, alongX),
                            LocalAlongSize(.035f, .8f, .035f, alongX), metal, false);
                    }
                    else
                    {
                        Box(p, "Muro_bajo_ventana", LocalAlong(center, y + bottom / 2, z, alongX),
                            LocalAlongSize(paneWidth, bottom, .16f, alongX), wallMaterial, true);
                        Box(p, "Ventana_cinta", LocalAlong(center, y + bottom + openingHeight / 2, z - side * .015f, alongX),
                            LocalAlongSize(paneWidth, openingHeight, pane, alongX), darkGlass, false);
                        Box(p, "Muro_sobre_ventana", LocalAlong(center, y + (top + Storey) / 2, z, alongX),
                            LocalAlongSize(paneWidth, Storey - top, .16f, alongX), wallMaterial, true);
                    }
                    Box(p, "Pilastrilla", LocalAlong(-span / 2 + bay * (b + 1), y + Storey / 2, z, alongX),
                        LocalAlongSize(.17f, Storey, .24f, alongX), wallMaterial, true);
                    Box(p, "Travesano_inferior", LocalAlong(center, y + bottom, z - side * .045f, alongX),
                        LocalAlongSize(paneWidth, .045f, .07f, alongX), metal, false);
                    Box(p, "Travesano_superior", LocalAlong(center, y + top, z - side * .045f, alongX),
                        LocalAlongSize(paneWidth, .045f, .07f, alongX), metal, false);
                }
            }
        }

        static Vector3 LocalAlong(float along, float y, float side) => new Vector3(along, y, side);
        static Vector3 LocalAlong(float along, float y, float side, bool alongX) =>
            alongX ? new Vector3(along, y, side) : new Vector3(side, y, along);
        static Vector3 LocalAlongSize(float along, float vertical, float thickness, bool alongX) =>
            alongX ? new Vector3(along, vertical, thickness) : new Vector3(thickness, vertical, along);

        // End faces are mostly solid cream panels with the small dark slit windows visible in the reference.
        static void ShortFacade(Transform p, float width, float depth, float y, int floor,
            Material wallMaterial, float doorX, bool eBuilding)
        {
            float endSpan = eBuilding ? depth : width;
            foreach (int side in new[] { -1, 1 })
            {
                float zSide = eBuilding ? side * width / 2 : side * depth / 2;
                // Unbroken end wall as seen on the Víctor Alzamora photo; three slit windows.
                bool connectorOpening = !eBuilding && side < 0 && Mathf.Approximately(y, 0) && !float.IsNaN(doorX);
                if (connectorOpening)
                {
                    float openingWidth = 2.6f;
                    float left = -width / 2, right = width / 2;
                    float a = Mathf.Clamp(doorX - openingWidth / 2, left, right);
                    float b = Mathf.Clamp(doorX + openingWidth / 2, left, right);
                    Box(p, "Muro_terminal_izquierdo", new Vector3((left + a) / 2, y + Storey / 2, zSide),
                        new Vector3(a - left, Storey, .16f), wallMaterial, true);
                    Box(p, "Muro_terminal_derecho", new Vector3((b + right) / 2, y + Storey / 2, zSide),
                        new Vector3(right - b, Storey, .16f), wallMaterial, true);
                    Box(p, "Dintel_acceso_corredor", new Vector3((a + b) / 2, y + Storey - .18f, zSide),
                        new Vector3(b - a, .36f, .16f), wallMaterial, true);
                    Box(p, "Puerta_vidriada_corredor", new Vector3((a + b) / 2, y + (Storey - .36f) / 2, zSide + .015f),
                        new Vector3(b - a, Storey - .36f, .045f), glass, false);
                }
                else
                    Box(p, "Muro_terminal", eBuilding ? new Vector3(zSide, y + Storey / 2, 0) : new Vector3(0, y + Storey / 2, zSide),
                        eBuilding ? new Vector3(.16f, Storey, depth) : new Vector3(width, Storey, .16f), wallMaterial, true);
                for (int slot = 0; slot < 3 && !connectorOpening; slot++)
                {
                    float s = (slot - 1) * endSpan * .19f;
                    Vector3 c = eBuilding ? new Vector3(zSide - side * .095f, y + 2.55f, s) : new Vector3(s, y + 2.55f, zSide - side * .095f);
                    Vector3 size = eBuilding ? new Vector3(.04f, .20f, .42f) : new Vector3(.42f, .20f, .04f);
                    Box(p, "Ventana_hendidura", c, size, darkGlass, false);
                }
            }
        }

        static void BuildConnector(Transform eRoot, Vector3 ePosition, Vector3 fPosition)
        {
            float dx = fPosition.x - ePosition.x;
            float dz = fPosition.z - ePosition.z;
            float eDepth = 9.76f, fDepth = 22.91f;
            float gap = dz - eDepth / 2 - fDepth / 2;
            if (gap <= .15f || gap > 5f)
            {
                Debug.LogWarning("No se añadió el corredor E-F: revisa la separación de los prefabs (" + gap.ToString("F2") + " m).");
                return;
            }
            // The footprints overlap in X; center the 4.4 m glazed hall on their shared area.
            float left = Mathf.Max(-24.30f / 2, dx - 11.85f / 2);
            float right = Mathf.Min(24.30f / 2, dx + 11.85f / 2);
            float sharedCenter = (left + right) / 2;
            float eBay = 24.30f / Mathf.Clamp(Mathf.RoundToInt(24.30f / 2.25f), 5, 12);
            int eBayIndex = Mathf.Clamp(Mathf.RoundToInt((sharedCenter + 24.30f / 2) / eBay - .5f), 0,
                Mathf.Clamp(Mathf.RoundToInt(24.30f / 2.25f), 5, 12) - 1);
            float cx = -24.30f / 2 + eBay * (eBayIndex + .5f);
            float corridorWidth = Mathf.Min(1.8f, right - left - .4f);
            if (corridorWidth < 1.5f) return;
            var hall = Group(eRoot, "Corredor_acristalado_E-F");
            float z0 = eDepth / 2, z1 = dz - fDepth / 2;
            float len = z1 - z0;
            Box(hall, "Piso_pasaje", new Vector3(cx, .06f, (z0 + z1) / 2), new Vector3(corridorWidth, .12f, len), paving, true);
            Box(hall, "Techo_pasaje", new Vector3(cx, Storey - .10f, (z0 + z1) / 2), new Vector3(corridorWidth, .20f, len), cream, true);
            foreach (int s in new[] { -1, 1 })
            {
                Box(hall, "Paño_vidriado_pasaje", new Vector3(cx + s * corridorWidth / 2, Storey / 2, (z0 + z1) / 2),
                    new Vector3(.06f, Storey - .2f, len), glass, false);
                int frames = Mathf.Max(1, Mathf.RoundToInt(len / 1.1f));
                for (int i = 0; i <= frames; i++)
                {
                    float z = Mathf.Lerp(z0, z1, (float)i / frames);
                    Box(hall, "Montante_pasaje", new Vector3(cx + s * corridorWidth / 2, Storey / 2, z),
                        new Vector3(.09f, Storey, .06f), metal, false);
                }
            }
        }

        static Transform Group(Transform parent, string name)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            return go.transform;
        }

        static void Box(Transform parent, string name, Vector3 center, Vector3 size, Material material, bool collider)
        {
            if (size.x <= 0 || size.y <= 0 || size.z <= 0) return;
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.SetParent(parent, false);
            go.transform.localPosition = center;
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
