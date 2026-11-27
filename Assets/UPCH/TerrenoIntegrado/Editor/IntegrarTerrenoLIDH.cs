using System;
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;
using UPCH.Veterinaria.Editor;

namespace UPCH.TerrenoIntegrado.Editor
{
    // Run once on the merged scene, with LID R4 assigned to both components.
    public static class IntegrarTerrenoLIDH
    {
        const string R4 = "Assets/UPCH/LIDContornoR4/Mallas/Site_LID_Contorno_R4.asset";
        const string Original = "Assets/UPCH/Campus/Generated/Meshes/Site.asset";
        const string OutDir = "Assets/UPCH/TerrenoIntegrado/Mallas";
        const string OutPath = OutDir + "/Site_LID_H_Integrado.asset";
        const float Eps = .0001f;

        [MenuItem("Tools/UPCH/Terreno/Integrar LID R4 y Veterinaria H")]
        public static void Run()
        {
            Mesh local = null, cut = null, result = null;
            try
            {
                Require(!EditorApplication.isPlayingOrWillChangePlaymode, "Sal de Play Mode.");
                var scene = SceneManager.GetActiveScene();
                Require(scene.path == "Assets/UPCH/Scenes/Campus.unity", "Abre Campus.unity.");
                var source = AssetDatabase.LoadAssetAtPath<Mesh>(R4);
                var original = AssetDatabase.LoadAssetAtPath<Mesh>(Original);
                Require(source && original && source.isReadable && original.isReadable, "Falta la malla R4 o la original legible.");
                Require(source.subMeshCount == 1 && source.GetTopology(0) == MeshTopology.Triangles, "R4 no es una malla de una submalla triangular.");
                Require(!AssetDatabase.LoadMainAssetAtPath(OutPath), "Ya existe la malla integrada; no se sobrescribira.");
                var filters = scene.GetRootGameObjects().SelectMany(r => r.GetComponentsInChildren<MeshFilter>(true)).ToArray();
                var grounds = filters.Where(f => f.name == "Terreno" && f.sharedMesh == source).ToArray();
                Require(grounds.Length == 1, "Debe existir un unico Terreno con R4 asignada.");
                var ground = grounds[0];
                var colliders = ground.GetComponents<Collider>();
                var mc = ground.GetComponent<MeshCollider>();
                Require(colliders.Length == 1 && mc && mc.enabled && !mc.convex && !mc.isTrigger && mc.sharedMesh == source,
                    "MeshFilter y MeshCollider deben usar R4 y el collider debe estar activo.");
                Require(Vector3.Dot(ground.transform.up, Vector3.up) > .99999f && (ground.transform.lossyScale - Vector3.one).sqrMagnitude < 1e-6f,
                    "Transformacion del terreno no compatible.");
                var cutters = filters.Where(f => f.name.IndexOf("Excavacion_H_Verificada", StringComparison.OrdinalIgnoreCase) >= 0).ToArray();
                Require(cutters.Length == 1 && cutters[0].sharedMesh && cutters[0].sharedMesh.isReadable, "Debe existir una unica Excavacion_H_Verificada legible (incluso inactiva).");
                var cutter = cutters[0];
                var cv = cutter.sharedMesh.vertices;
                var ci = cutter.sharedMesh.triangles;
                var polys = new List<Vector2[]>();
                float minX = float.PositiveInfinity, minZ = float.PositiveInfinity, maxX = float.NegativeInfinity, maxZ = float.NegativeInfinity;
                double cutterArea = 0;
                for (int i = 0; i < ci.Length; i += 3)
                {
                    Vector3 a = ground.transform.InverseTransformPoint(cutter.transform.TransformPoint(cv[ci[i]]));
                    Vector3 b = ground.transform.InverseTransformPoint(cutter.transform.TransformPoint(cv[ci[i+1]]));
                    Vector3 c = ground.transform.InverseTransformPoint(cutter.transform.TransformPoint(cv[ci[i+2]]));
                    Vector3 normal = Vector3.Cross(b-a,c-a);
                    if (normal.sqrMagnitude < 1e-12f || normal.normalized.y < .9999f) continue;
                    var p = new[]{new Vector2(a.x,a.z),new Vector2(b.x,b.z),new Vector2(c.x,c.z)};
                    float sign = (p[1].x-p[0].x)*(p[2].y-p[0].y)-(p[1].y-p[0].y)*(p[2].x-p[0].x);
                    if (sign < 0) { var tmp=p[1]; p[1]=p[2]; p[2]=tmp; }
                    cutterArea += Math.Abs(sign)*.5;
                    foreach(var q in p) { minX=Mathf.Min(minX,q.x); maxX=Mathf.Max(maxX,q.x); minZ=Mathf.Min(minZ,q.y); maxZ=Mathf.Max(maxZ,q.y); }
                    polys.Add(p);
                }
                Require(polys.Count > 0 && Math.Abs(cutterArea-981.8014) < 10, "Huella de excavacion distinta de la documentada (~981.8 m2). Area: " + cutterArea);
                var v = source.vertices; var uv = source.uv; var normals = source.normals; var t = source.triangles;
                Require(uv.Length == v.Length && normals.Length == v.Length, "R4 necesita UV0 y normales por vertice.");
                // Refuse meshes with additional attributes instead of silently dropping them.
                Require(source.colors.Length == 0 && source.tangents.Length == 0 && source.blendShapeCount == 0 && source.boneWeights.Length == 0,
                    "R4 posee atributos adicionales; se requiere adaptar el integrador.");
                for (int channel=1; channel<8; channel++) { var extra=new List<Vector4>(); source.GetUVs(channel,extra); Require(extra.Count==0,"R4 posee canales UV adicionales."); }
                float top = original.bounds.max.y, bottom = original.bounds.min.y;
                Require(top-bottom > Eps && top-bottom <= .30f, "La plancha original no tiene el espesor esperado.");
                var lv = new List<Vector3>(); var lu = new List<Vector2>(); var lt = new List<int>(); var keep = new List<int>();
                for(int i=0;i<t.Length;i+=3)
                {
                    Vector3 a=v[t[i]], b=v[t[i+1]], c=v[t[i+2]];
                    bool near = Mathf.Max(a.x,b.x,c.x)>=minX-Eps && Mathf.Min(a.x,b.x,c.x)<=maxX+Eps &&
                                Mathf.Max(a.z,b.z,c.z)>=minZ-Eps && Mathf.Min(a.z,b.z,c.z)<=maxZ+Eps;
                    if (!near) { keep.Add(t[i]); keep.Add(t[i+1]); keep.Add(t[i+2]); continue; }
                    for(int j=0;j<3;j++)
                    {
                        int n=t[i+j]; var q=v[n];
                        Require(Mathf.Abs(q.y-top)<=Eps || Mathf.Abs(q.y-bottom)<=Eps,
                            "La zona H contiene triangulos con desniveles o triangulos extensos que alcanzan otras zonas. No se aplico nada.");
                        lt.Add(lv.Count); lv.Add(q); lu.Add(uv[n]);
                    }
                }
                Require(lt.Count>0 && keep.Count>0,"No se pudo aislar la zona H.");
                local=new Mesh { name="Zona_H_Temporal",indexFormat=IndexFormat.UInt32 };
                local.SetVertices(lv); local.SetUVs(0,lu); local.SetTriangles(lt,0); local.RecalculateBounds();
                Require(Mathf.Abs(local.bounds.max.y-top)<=Eps && Mathf.Abs(local.bounds.min.y-bottom)<=Eps,"La zona local no contiene las dos caras de la plancha original.");
                cut=VeterinariaTerreno.BuildCutMesh(local,polys);
                double removed=TopArea(local,top)-TopArea(cut,top);
                Require(Math.Abs(removed-981.39919)<10,"Area de recorte inesperada: " + removed + " m2. No se aplico nada.");
                // Keep original vertex data and triangle indices outside the local region.
                var ov=new List<Vector3>(v); var ou=new List<Vector2>(uv); var on=new List<Vector3>(normals);
                int offset=ov.Count; ov.AddRange(cut.vertices); ou.AddRange(cut.uv); on.AddRange(cut.normals);
                foreach(int i in cut.triangles) keep.Add(offset+i);
                result=new Mesh { name="Site_LID_H_Integrado",indexFormat=IndexFormat.UInt32 };
                result.SetVertices(ov); result.SetUVs(0,ou); result.SetNormals(on); result.SetTriangles(keep,0); result.RecalculateBounds();
                Require(result.vertexCount>0 && result.triangles.Length>0,"Resultado vacio.");
                if (!EditorUtility.DisplayDialog("Integrar terreno",$"Recorte H: {removed:F2} m2. Se conservaron los triangulos fuera de la zona local. Se creara un asset nuevo sin sobrescribir las mallas originales. La escena no se guardara automaticamente.","Aplicar","Cancelar")) return;
                EnsureFolder("Assets/UPCH","TerrenoIntegrado"); EnsureFolder("Assets/UPCH/TerrenoIntegrado","Mallas");
                AssetDatabase.CreateAsset(result,OutPath);
                Undo.RecordObjects(new UnityEngine.Object[]{ground,mc},"Integrar terreno LID y H");
                ground.sharedMesh=result; mc.sharedMesh=null; mc.sharedMesh=result;
                PrefabUtility.RecordPrefabInstancePropertyModifications(ground); PrefabUtility.RecordPrefabInstancePropertyModifications(mc);
                EditorSceneManager.MarkSceneDirty(scene); AssetDatabase.SaveAssets();
                Debug.Log($"Terreno integrado: area H retirada {removed:F2} m2; malla visual y collider coinciden. Revisa el LID, H, Parque Central y las colisiones antes de guardar Campus.",ground);
            }
            catch(Exception e) { Debug.LogError("Integracion LID/H: " + e.Message); }
            finally
            {
                if(local) UnityEngine.Object.DestroyImmediate(local);
                if(cut) UnityEngine.Object.DestroyImmediate(cut);
                if(result && !AssetDatabase.Contains(result)) UnityEngine.Object.DestroyImmediate(result);
            }
        }
        static void Require(bool condition,string message) { if(!condition) throw new InvalidOperationException(message); }
        static void EnsureFolder(string parent,string child) { if(!AssetDatabase.IsValidFolder(parent+"/"+child)) AssetDatabase.CreateFolder(parent,child); }
        static double TopArea(Mesh mesh,float top)
        {
            var v=mesh.vertices; var t=mesh.triangles; double total=0;
            for(int i=0;i<t.Length;i+=3)
            {
                var a=v[t[i]];var b=v[t[i+1]];var c=v[t[i+2]];
                if(Mathf.Abs(a.y-top)<=Eps && Mathf.Abs(b.y-top)<=Eps && Mathf.Abs(c.y-top)<=Eps)
                    total+=Math.Max(0,Vector3.Cross(b-a,c-a).y)*.5;
            }
            return total;
        }
    }
}
