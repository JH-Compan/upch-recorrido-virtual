using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace UPCH.Veterinaria.Editor
{
    // Editor utility. The cutter must be the verified excavation envelope, NOT
    // the bounding box of H and NOT an architectural floor containing stair holes.
    public sealed class VeterinariaTerreno : EditorWindow
    {
        const string Folder = "Assets/UPCH/Veterinaria/Generado";
        const string StatePath = Folder + "/Estado_Recorte_H.asset";
        const string MeshPath = Folder + "/Terreno_Recortado_H.asset";
        MeshFilter terrain;
        MeshFilter excavation;
        Vector2 scroll;

        [MenuItem("Tools/UPCH/Veterinaria/Revisar y recortar terreno")]
        public static void Open() => GetWindow<VeterinariaTerreno>("H - Terreno");

        void OnGUI()
        {
            scroll = EditorGUILayout.BeginScrollView(scroll);
            EditorGUILayout.LabelField("Sótano de Veterinaria", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Recorta simultáneamente la superficie y su MeshCollider. Conserva la malla de origen. No mueve ni escala el edificio, ni modifica al jugador.", MessageType.Info);
            terrain = (MeshFilter)EditorGUILayout.ObjectField("Terreno del campus", terrain, typeof(MeshFilter), true);
            excavation = (MeshFilter)EditorGUILayout.ObjectField("Envolvente de excavación", excavation, typeof(MeshFilter), true);
            EditorGUILayout.HelpBox("Usa una malla de excavación verificada, sin huecos interiores. Debe incluir la huella real del sótano y de los accesos que atraviesen el terreno. El volumen H existente es una reserva y no confirma esa envolvente.", MessageType.Warning);
            using (new EditorGUI.DisabledScope(EditorApplication.isPlayingOrWillChangePlaymode))
            {
                if (GUILayout.Button("Comprobar selección")) Inspect(terrain, excavation);
                if (GUILayout.Button("Aplicar recorte local"))
                    Try(() => Apply(terrain, excavation));
                if (GUILayout.Button("Restaurar terreno de origen"))
                    Try(() => Restore(terrain));
            }
            EditorGUILayout.EndScrollView();
        }

        static void Try(Action action)
        {
            try { action(); }
            catch (Exception error) { Debug.LogError("Veterinaria: " + error.Message); }
        }

        // Bootstrap the inspected scene's offline-generated cut while retaining
        // its original mesh. Never adopt an unrelated later terrain replacement.
        public static void RegisterKnownMeshes(MeshFilter ground, Mesh source, Mesh result)
        {
            CheckGround(ground);
            if (!source || !result) throw new InvalidOperationException("Falta la base o el recorte H.");
            var state = AssetDatabase.LoadAssetAtPath<VeterinariaTerrenoEstado>(StatePath);
            if (state) { Source(ground); return; }
            if (ground.sharedMesh != source && ground.sharedMesh != result)
                throw new InvalidOperationException("El terreno tiene otra modificación; no se sobrescribió.");
            Directory.CreateDirectory(Folder); AssetDatabase.Refresh();
            state = CreateInstance<VeterinariaTerrenoEstado>();
            state.source = source; state.result = result;
            state.targetGlobalId = GlobalObjectId.GetGlobalObjectIdSlow(ground).ToString();
            AssetDatabase.CreateAsset(state, StatePath); AssetDatabase.SaveAssets();
        }

        public static void Inspect(MeshFilter ground, MeshFilter cutter)
        {
            Try(() =>
            {
                var collider = CheckGround(ground);
                var triangles = CutterTriangles(ground, cutter);
                var source = Source(ground);
                CheckSource(source);
                Debug.Log($"Veterinaria: {source.vertexCount} vértices; espesor local {source.bounds.size.y:F3} m; {triangles.Count} triángulos de excavación. Render y colisión comparten la misma malla: {collider.sharedMesh == ground.sharedMesh}. Falta aplicar y recorrer el resultado en Play.", ground);
            });
        }

        static MeshCollider CheckGround(MeshFilter ground)
        {
            if (!ground || !ground.gameObject.scene.IsValid())
                throw new InvalidOperationException("Selecciona exclusivamente el terreno de la escena.");
            if (!ground.sharedMesh || !ground.sharedMesh.isReadable)
                throw new InvalidOperationException("El terreno necesita una malla legible.");
            if (ground.sharedMesh.subMeshCount != 1 || ground.sharedMesh.bounds.size.y > .30f)
                throw new InvalidOperationException("Esta herramienta admite una plancha horizontal, de una submalla y espesor máximo 0.30 m.");
            if (Vector3.Dot(ground.transform.up, Vector3.up) < .99999f)
                throw new InvalidOperationException("El terreno debe ser horizontal.");
            var colliders = ground.GetComponents<Collider>();
            if (colliders.Length != 1 || !(colliders[0] is MeshCollider collider) || collider.convex || collider.isTrigger)
                throw new InvalidOperationException("El terreno debe tener un único MeshCollider estático, no convexo y no trigger.");
            if (collider.sharedMesh != ground.sharedMesh)
                throw new InvalidOperationException("La superficie y su colisión ya difieren; revisa antes de recortar.");
            return collider;
        }

        static Mesh Source(MeshFilter ground)
        {
            var state = AssetDatabase.LoadAssetAtPath<VeterinariaTerrenoEstado>(StatePath);
            if (!state) return ground.sharedMesh;
            if (state.targetGlobalId != GlobalObjectId.GetGlobalObjectIdSlow(ground).ToString())
                throw new InvalidOperationException("El recorte guardado pertenece a otro objeto de terreno.");
            if (!state.source || !state.result)
                throw new InvalidOperationException("El registro del recorte tiene referencias ausentes.");
            if (ground.sharedMesh != state.result && ground.sharedMesh != state.source)
                throw new InvalidOperationException("El terreno fue modificado después del recorte H. Conserva ese nuevo trabajo y revisa la base antes de reaplicar.");
            return state.source;
        }

        static void CheckSource(Mesh mesh)
        {
            if (!mesh || !mesh.isReadable || mesh.subMeshCount != 1)
                throw new InvalidOperationException("La malla de origen no es una plancha legible de una submalla.");
            float top = mesh.bounds.max.y, bottom = mesh.bounds.min.y;
            if (top - bottom > .30f)
                throw new InvalidOperationException("El espesor de la base supera 0.30 m.");
            foreach (var v in mesh.vertices)
                if (Math.Abs(v.y - top) > .0001 && Math.Abs(v.y - bottom) > .0001)
                    throw new InvalidOperationException("La base tiene alturas intermedias. Se requiere una plancha de dos caras horizontales; no se aplicó el recorte.");
        }

        // Project only upward-facing triangles from a dedicated horizontal cutter.
        // This preserves concave outlines and is independent of root position/yaw.
        static List<Vector2[]> CutterTriangles(MeshFilter ground, MeshFilter cutter)
        {
            if (!cutter || cutter == ground || !cutter.gameObject.scene.IsValid() || cutter.gameObject.scene != ground.gameObject.scene)
                throw new InvalidOperationException("Selecciona una envolvente de excavación independiente, en la misma escena.");
            if (!cutter.sharedMesh || !cutter.sharedMesh.isReadable)
                throw new InvalidOperationException("La envolvente necesita una malla legible.");
            if (cutter.name.IndexOf("Excavacion_H_Verificada", StringComparison.OrdinalIgnoreCase) < 0)
                throw new InvalidOperationException("La malla debe llamarse Excavacion_H_Verificada. No uses el volumen de reserva H ni una losa con huecos como excavación definitiva.");
            var vertices = cutter.sharedMesh.vertices;
            var indices = cutter.sharedMesh.triangles;
            var result = new List<Vector2[]>();
            for (int k = 0; k < indices.Length; k += 3)
            {
                var a = ground.transform.InverseTransformPoint(cutter.transform.TransformPoint(vertices[indices[k]]));
                var b = ground.transform.InverseTransformPoint(cutter.transform.TransformPoint(vertices[indices[k + 1]]));
                var c = ground.transform.InverseTransformPoint(cutter.transform.TransformPoint(vertices[indices[k + 2]]));
                var normal = Vector3.Cross(b - a, c - a);
                if (normal.sqrMagnitude < 1e-12f || normal.normalized.y < .9999f) continue;
                var triangle = new[] { new Vector2(a.x, a.z), new Vector2(b.x, b.z), new Vector2(c.x, c.z) };
                if (Cross(triangle[1] - triangle[0], triangle[2] - triangle[0]) < 0)
                    (triangle[1], triangle[2]) = (triangle[2], triangle[1]);
                result.Add(triangle);
            }
            if (result.Count == 0) throw new InvalidOperationException("No se encontraron caras superiores horizontales en la envolvente.");
            return result;
        }

        // Keep intersections in double precision until emitting Unity vertices.
        // Close-to-coincident campus/cutter corners can be much smaller than a
        // float's resolution at the campus's coordinate magnitude.
        struct P
        {
            public double x, y, z;
            public P(double x, double y, double z) { this.x = x; this.y = y; this.z = z; }
            public P(Vector3 p) : this(p.x, p.y, p.z) { }
            public Vector3 Unity => new Vector3((float)x, (float)y, (float)z);
            public static P operator +(P a, P b) => new P(a.x + b.x, a.y + b.y, a.z + b.z);
            public static P operator -(P a, P b) => new P(a.x - b.x, a.y - b.y, a.z - b.z);
            public static P operator *(P a, double t) => new P(a.x * t, a.y * t, a.z * t);
            public double Length2 => x * x + y * y + z * z;
            public static P Cross(P a, P b) => new P(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
            public static P Lerp(P a, P b, double t) => a + (b - a) * t;
        }
        struct V
        {
            public P p;
            public Vector2 uv;
            public V(P p, Vector2 uv) { this.p = p; this.uv = uv; }
            public V(Vector3 p, Vector2 uv) : this(new P(p), uv) { }
            public static V Lerp(V a, V b, double t) => new V(P.Lerp(a.p, b.p, t), Vector2.Lerp(a.uv, b.uv, (float)t));
        }
        static float Cross(Vector2 a, Vector2 b) => a.x * b.y - a.y * b.x;
        static double Distance(V v, Vector2 a, Vector2 b) => ((double)b.x - a.x) * (v.p.z - a.y) - ((double)b.y - a.y) * (v.p.x - a.x);
        static List<V> Clip(List<V> input, Vector2 a, Vector2 b, bool inside)
        {
            var output = new List<V>();
            if (input.Count == 0) return output;
            V previous = input[input.Count - 1];
            double da = Distance(previous, a, b);
            bool pa = inside ? da >= 0 : da < 0;
            foreach (var current in input)
            {
                double db = Distance(current, a, b);
                bool pb = inside ? db >= 0 : db < 0;
                if (pa != pb && Math.Abs(da - db) > 1e-15)
                    output.Add(V.Lerp(previous, current, da / (da - db)));
                if (pb) output.Add(current);
                previous = current; da = db; pa = pb;
            }
            return output;
        }
        static List<List<V>> Subtract(List<V> polygon, Vector2[] cutter)
        {
            var outside = new List<List<V>>();
            var remainder = polygon;
            for (int side = 0; side < 3 && remainder.Count > 0; side++)
            {
                var piece = Clip(remainder, cutter[side], cutter[(side + 1) % 3], false);
                if (piece.Count >= 3) outside.Add(piece);
                remainder = Clip(remainder, cutter[side], cutter[(side + 1) % 3], true);
            }
            return outside;
        }
        static bool Inside(double x, double z, List<Vector2[]> cutters)
        {
            foreach (var t in cutters)
            {
                bool within = true;
                for (int k = 0; k < 3; k++)
                {
                    Vector2 a = t[k], b = t[(k + 1) % 3];
                    double dx = (double)b.x - a.x, dz = (double)b.y - a.y;
                    double side = dx * (z - a.y) - dz * (x - a.x);
                    if (side < -1e-12 * Math.Sqrt(dx * dx + dz * dz)) { within = false; break; }
                }
                if (within) return true;
            }
            return false;
        }
        static double Cross2(double ax, double az, double bx, double bz) => ax * bz - az * bx;
        static List<(P a, P b)> BoundarySegments(P a, P b, List<Vector2[]> cutters)
        {
            var result = new List<(P a, P b)>();
            double ex = b.x - a.x, ez = b.z - a.z, length2 = ex * ex + ez * ez;
            if (length2 < 1e-20) return result;
            var cuts = new List<double> { 0, 1 };
            foreach (var t in cutters)
                for (int k = 0; k < 3; k++)
                {
                    Vector2 c = t[k], d = t[(k + 1) % 3];
                    double dx = (double)d.x - c.x, dz = (double)d.y - c.y;
                    double denominator = Cross2(ex, ez, dx, dz);
                    if (Math.Abs(denominator) > 1e-12)
                    {
                        double u = Cross2(c.x - a.x, c.y - a.z, dx, dz) / denominator;
                        double v = Cross2(c.x - a.x, c.y - a.z, ex, ez) / denominator;
                        if (u > 0 && u < 1 && v >= -1e-9 && v <= 1 + 1e-9) cuts.Add(u);
                    }
                    else if (Math.Abs(Cross2(c.x - a.x, c.y - a.z, ex, ez)) < 1e-10)
                    {
                        double u = ((c.x - a.x) * ex + (c.y - a.z) * ez) / length2;
                        double v = ((d.x - a.x) * ex + (d.y - a.z) * ez) / length2;
                        if (u > 0 && u < 1) cuts.Add(u);
                        if (v > 0 && v < 1) cuts.Add(v);
                    }
                }
            cuts.Sort();
            double length = Math.Sqrt(length2), nx = -ez / length * 1e-9, nz = ex / length * 1e-9;
            for (int k = 0; k < cuts.Count - 1; k++)
            {
                if ((cuts[k + 1] - cuts[k]) * length < 1e-9) continue;
                double mid = (cuts[k] + cuts[k + 1]) / 2;
                double x = a.x + ex * mid, z = a.z + ez * mid;
                if (Inside(x + nx, z + nz, cutters) != Inside(x - nx, z - nz, cutters))
                    result.Add((P.Lerp(a, b, cuts[k]), P.Lerp(a, b, cuts[k + 1])));
            }
            return result;
        }

        public static Mesh BuildCutMesh(Mesh source, List<Vector2[]> cutters)
        {
            var vertices = source.vertices;
            var uv = source.uv;
            var triangles = source.triangles;
            var output = new List<Vector3>();
            var outputUV = new List<Vector2>();
            var indices = new List<int>();
            var cutEdges = new List<(P a, P b)>();
            float top = source.bounds.max.y, bottom = source.bounds.min.y;
            void Emit(V a, V b, V c)
            {
                if (Vector3.Cross(b.p.Unity - a.p.Unity, c.p.Unity - a.p.Unity).sqrMagnitude < 1e-20f) return;
                int index = output.Count;
                foreach (var v in new[] { a, b, c }) { output.Add(v.p.Unity); outputUV.Add(v.uv); }
                indices.Add(index); indices.Add(index + 1); indices.Add(index + 2);
            }
            for (int k = 0; k < triangles.Length; k += 3)
            {
                var initial = new List<V>();
                for (int j = 0; j < 3; j++)
                {
                    int n = triangles[k + j];
                    initial.Add(new V(vertices[n], uv.Length == vertices.Length ? uv[n] : Vector2.zero));
                }
                var pieces = new List<List<V>> { initial };
                foreach (var cutter in cutters)
                {
                    var next = new List<List<V>>();
                    foreach (var piece in pieces) next.AddRange(Subtract(piece, cutter));
                    pieces = next;
                }
                foreach (var piece in pieces)
                {
                    P areaNormal = new P(0, 0, 0);
                    for (int n = 1; n < piece.Count - 1; n++)
                        areaNormal += P.Cross(piece[n].p - piece[0].p, piece[n + 1].p - piece[0].p);
                    if (areaNormal.Length2 < 1e-20) continue;
                    for (int n = 1; n < piece.Count - 1; n++) Emit(piece[0], piece[n], piece[n + 1]);
                    if (areaNormal.y / Math.Sqrt(areaNormal.Length2) < .9999) continue;
                    for (int n = 0; n < piece.Count; n++)
                    {
                        P a = piece[n].p, b = piece[(n + 1) % piece.Count].p;
                        if (Math.Abs(a.y - top) > .0001f || Math.Abs(b.y - top) > .0001f) continue;
                        cutEdges.AddRange(BoundarySegments(a, b, cutters));
                    }
                }
            }
            if (bottom < top - .0001f)
                foreach (var edge in cutEdges)
                {
                    var a = new V(edge.a, new Vector2((float)edge.a.x, top));
                    var b = new V(edge.b, new Vector2((float)edge.b.x, top));
                    var lowA = new V(new P(edge.a.x, bottom, edge.a.z), new Vector2((float)edge.a.x, bottom));
                    var lowB = new V(new P(edge.b.x, bottom, edge.b.z), new Vector2((float)edge.b.x, bottom));
                    Emit(a, lowB, b); Emit(a, lowA, lowB);
                }
            if (indices.Count == 0 || output.Count < 3)
                throw new InvalidOperationException("El recorte vaciaría todo el terreno. No se aplicó.");
            var mesh = new Mesh { name = "Terreno_Recortado_H", indexFormat = IndexFormat.UInt32 };
            mesh.SetVertices(output); mesh.SetUVs(0, outputUV); mesh.SetTriangles(indices, 0);
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            return mesh;
        }

        static double TopArea(Mesh mesh)
        {
            var v = mesh.vertices; var t = mesh.triangles;
            double area = 0;
            float top = mesh.bounds.max.y;
            for (int k = 0; k < t.Length; k += 3)
            {
                Vector3 a = v[t[k]], b = v[t[k + 1]], c = v[t[k + 2]];
                if (Math.Abs(a.y - top) < .0001f && Math.Abs(b.y - top) < .0001f && Mathf.Abs(c.y - top) < .0001f)
                    area += Math.Max(0, Vector3.Cross(b - a, c - a).y) / 2.0;
            }
            return area;
        }

        public static void Apply(MeshFilter ground, MeshFilter cutter)
        {
            if (EditorApplication.isPlayingOrWillChangePlaymode) throw new InvalidOperationException("Sal de Play antes de editar el terreno.");
            var collider = CheckGround(ground);
            var source = Source(ground);
            CheckSource(source);
            var mesh = BuildCutMesh(source, CutterTriangles(ground, cutter));
            if (TopArea(source) - TopArea(mesh) <= Math.Max(.0001, TopArea(source) * 1e-6))
            {
                UnityEngine.Object.DestroyImmediate(mesh);
                throw new InvalidOperationException("La excavación no alteró la geometría; revisa su posición y solape.");
            }
            Directory.CreateDirectory(Folder); AssetDatabase.Refresh();
            var state = AssetDatabase.LoadAssetAtPath<VeterinariaTerrenoEstado>(StatePath);
            var saved = AssetDatabase.LoadAssetAtPath<Mesh>(MeshPath);
            if (!state)
            {
                state = CreateInstance<VeterinariaTerrenoEstado>();
                state.source = source;
                state.targetGlobalId = GlobalObjectId.GetGlobalObjectIdSlow(ground).ToString();
                AssetDatabase.CreateAsset(state, StatePath);
            }
            int group = Undo.GetCurrentGroup(); Undo.SetCurrentGroupName("Recortar terreno bajo H");
            if (saved)
            {
                Undo.RegisterCompleteObjectUndo(saved, "Actualizar recorte H");
                EditorUtility.CopySerialized(mesh, saved);
                UnityEngine.Object.DestroyImmediate(mesh);
                EditorUtility.SetDirty(saved);
            }
            else { saved = mesh; AssetDatabase.CreateAsset(saved, MeshPath); }
            Undo.RecordObjects(new UnityEngine.Object[] { ground, collider, state }, "Asignar recorte H");
            ground.sharedMesh = saved;
            collider.sharedMesh = null; collider.sharedMesh = saved;
            state.result = saved;
            EditorUtility.SetDirty(state);
            Undo.CollapseUndoOperations(group);
            EditorSceneManager.MarkSceneDirty(ground.gameObject.scene);
            AssetDatabase.SaveAssets();
            Debug.Log("Veterinaria: recorte local preparado en superficie y colisión. Site original conservado. Revisa sótano, accesos, bordes y colisiones en Play antes de guardar Campus.", ground);
        }

        public static void Restore(MeshFilter ground)
        {
            var collider = CheckGround(ground);
            var source = Source(ground);
            Undo.RecordObjects(new UnityEngine.Object[] { ground, collider }, "Restaurar terreno previo a H");
            ground.sharedMesh = source;
            collider.sharedMesh = null; collider.sharedMesh = source;
            EditorSceneManager.MarkSceneDirty(ground.gameObject.scene);
            Debug.Log("Veterinaria: malla original restaurada en superficie y colisión.", ground);
        }
    }
}
