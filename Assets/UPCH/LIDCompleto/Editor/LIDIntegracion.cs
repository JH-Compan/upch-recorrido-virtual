using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace UPCH.LIDCompleto.Editor
{
    public sealed class LIDIntegracion : EditorWindow
    {
        const string Root = "Assets/UPCH/LIDCompleto";
        float grade = 1.2f;
        Vector2 scroll;

        [MenuItem("Tools/UPCH/LID completo/Integración y revisión")]
        public static void Open() { GetWindow<LIDIntegracion>("LID completo"); }
        void OnGUI()
        {
            scroll = EditorGUILayout.BeginScrollView(scroll);
            EditorGUILayout.LabelField("LID · edificio editable", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Primero abre la escena de revisión para comprobar materiales, accesos y recorridos. El Prefab contiene sótano, cuatro pisos, azotea y acceso exterior.", MessageType.Info);
            if (GUILayout.Button("Abrir escena de revisión"))
            {
                if (EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())
                    EditorSceneManager.OpenScene(Root + "/Scenes/LID_Revision_Completa.unity");
            }
            if (GUILayout.Button("Seleccionar Prefab del edificio"))
                Selection.activeObject = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Edificio_LID.prefab");
            EditorGUILayout.Space();
            EditorGUILayout.LabelField("Integrar en la escena Campus", EditorStyles.boldLabel);
            EditorGUILayout.LabelField("Selecciona en Hierarchy el volumen L que servirá de ancla.", EditorStyles.wordWrappedLabel);
            grade = EditorGUILayout.FloatField("Terreno respecto a NPT 0", grade);
            EditorGUILayout.HelpBox("+1,20 m es una cota provisional del terreno para la demo. El desplazamiento vertical del edificio será el negativo de ese valor; sus NPT relativos se conservan.", MessageType.Info);
            if (GUILayout.Button("Integrar en el ancla seleccionada")) Integrate(grade);
            EditorGUILayout.Space();
            EditorGUILayout.LabelField("Sótano y terreno", EditorStyles.boldLabel);
            EditorGUILayout.LabelField("Si el suelo del Campus atraviesa el sótano, selecciona exclusivamente la malla horizontal de terreno y usa el recorte. Se crea una copia de su malla y la acción se puede deshacer.", EditorStyles.wordWrappedLabel);
            if (GUILayout.Button("Recortar terreno seleccionado bajo el LID")) ClipGround();
            EditorGUILayout.Space();
            if (GUILayout.Button("Comprobar referencias del LID seleccionado")) Validate();
            EditorGUILayout.EndScrollView();
        }

        static void Integrate(float grade)
        {
            if (EditorApplication.isPlaying) { Debug.LogError("LID: sal del modo Play."); return; }
            var anchor = Selection.activeGameObject;
            if (anchor == null || !(anchor.name == "L" || anchor.name.StartsWith("L -", StringComparison.Ordinal)))
            { Debug.LogError("LID: selecciona el volumen de referencia llamado L en la escena Campus."); return; }
            foreach (var candidate in anchor.scene.GetRootGameObjects())
                foreach (var child in candidate.GetComponentsInChildren<Transform>(true))
                    if (child.name == "Edificio_LID") { Debug.LogError("LID: ya hay un edificio LID en esta escena, incluso dentro de otro objeto. Selecciona la instancia existente."); return; }
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(Root + "/Prefabs/Edificio_LID.prefab");
            if (prefab == null) throw new FileNotFoundException("No se encuentra el Prefab del LID.");
            int undo = Undo.GetCurrentGroup(); Undo.SetCurrentGroupName("Integrar LID");
            var obj = (GameObject)PrefabUtility.InstantiatePrefab(prefab, anchor.scene);
            Undo.RegisterCreatedObjectUndo(obj, "Integrar LID");
            obj.transform.position = anchor.transform.position - Vector3.up * grade;
            obj.transform.rotation = anchor.transform.rotation * Quaternion.Euler(0, 90, 0);
            obj.transform.localScale = Vector3.one;
            Undo.RecordObject(anchor, "Desactivar volumen L de referencia"); anchor.SetActive(false);
            Undo.CollapseUndoOperations(undo);
            Selection.activeGameObject = obj; EditorSceneManager.MarkSceneDirty(anchor.scene);
            Debug.Log("LID integrado. El volumen L anterior se conserva desactivado. Revisa terreno y conexiones exteriores antes de guardar Campus.");
        }
        static Transform FindBuilding()
        {
            foreach (var r in SceneManager.GetActiveScene().GetRootGameObjects())
                foreach (var child in r.GetComponentsInChildren<Transform>(true))
                    if (child.name == "Edificio_LID") return child;
            return null;
        }
        static void Validate()
        {
            var root = FindBuilding();
            if (root == null) { Debug.LogError("LID: abre una escena que contenga Edificio_LID."); return; }
            int errors = 0, meshes = 0;
            foreach (var f in root.GetComponentsInChildren<MeshFilter>(true))
            { meshes++; if (f.sharedMesh == null) { errors++; Debug.LogError("Malla ausente: " + f.name, f); } }
            foreach (var r in root.GetComponentsInChildren<MeshRenderer>(true))
                foreach (var m in r.sharedMaterials)
                    if (m == null || m.shader == null || !m.shader.isSupported) { errors++; Debug.LogError("Material incompatible: " + r.name, r); }
            Debug.Log("LID: " + meshes + " MeshFilters; " + errors + " referencias ausentes o incompatibles. Esta comprobación no reemplaza recorrer accesos y escaleras en Play.");
        }

        struct V
        {
            public Vector3 local;
            public Vector3 building;
            public Vector2 uv;
            public V(Vector3 local, Vector3 building, Vector2 uv) { this.local = local; this.building = building; this.uv = uv; }
            public static V Lerp(V a, V b, float t) { return new V(Vector3.Lerp(a.local,b.local,t), Vector3.Lerp(a.building,b.building,t), Vector2.Lerp(a.uv,b.uv,t)); }
        }
        // Exact rectangular decomposition of the CAD basement/access outline.
        static readonly Rect[] GroundVoids = {
            Rect.MinMaxRect(-8.2529f,-13.89549f,-8.25f,17.305f),
            Rect.MinMaxRect(0.04998f,-13.89549f,8.24702f,17.305f),
            Rect.MinMaxRect(-32.25599f,-16.80032f,-31.57976f,17.305f),
            Rect.MinMaxRect(-29.22767f,-16.80032f,-28.48088f,17.305f),
            Rect.MinMaxRect(-28.328f,-16.80032f,-27.57533f,17.305f),
            Rect.MinMaxRect(-25.22912f,-16.80032f,-24.47645f,17.305f),
            Rect.MinMaxRect(-24.32944f,-16.80032f,-23.57677f,17.305f),
            Rect.MinMaxRect(-21.22468f,-16.80032f,-20.47789f,17.305f),
            Rect.MinMaxRect(-20.33089f,-16.80032f,-19.57822f,17.305f),
            Rect.MinMaxRect(-17.22613f,-16.80032f,-16.47934f,17.305f),
            Rect.MinMaxRect(-16.32645f,-16.80032f,-15.57966f,17.305f),
            Rect.MinMaxRect(-13.22757f,-16.80032f,-12.4749f,17.305f),
            Rect.MinMaxRect(-12.3279f,-16.80032f,-11.58111f,17.305f),
            Rect.MinMaxRect(-9.22902f,-16.80032f,-8.55279f,17.305f),
            Rect.MinMaxRect(8.54691f,-16.80032f,9.22314f,17.305f),
            Rect.MinMaxRect(11.57523f,-16.80032f,12.3279f,17.305f),
            Rect.MinMaxRect(12.4749f,-16.80032f,13.22169f,17.305f),
            Rect.MinMaxRect(15.57378f,-16.80032f,16.32645f,17.305f),
            Rect.MinMaxRect(16.47346f,-16.80032f,17.22613f,17.305f),
            Rect.MinMaxRect(19.57234f,-16.80032f,20.32501f,17.305f),
            Rect.MinMaxRect(20.47789f,-16.80032f,21.22468f,17.305f),
            Rect.MinMaxRect(23.57677f,-16.80032f,24.32356f,17.305f),
            Rect.MinMaxRect(24.47645f,-16.80032f,25.22324f,17.305f),
            Rect.MinMaxRect(27.57533f,-16.80032f,28.32212f,17.305f),
            Rect.MinMaxRect(28.475f,-16.80032f,29.22767f,17.305f),
            Rect.MinMaxRect(31.57388f,-16.80032f,32.25011f,17.305f),
            Rect.MinMaxRect(-32.55f,-17.30013955f,-32.25599f,17.305f),
            Rect.MinMaxRect(-31.57976f,-17.30013955f,-29.22767f,17.305f),
            Rect.MinMaxRect(-28.48088f,-17.30013955f,-28.328f,17.305f),
            Rect.MinMaxRect(-27.57533f,-17.30013955f,-25.22912f,17.305f),
            Rect.MinMaxRect(-24.47645f,-17.30013955f,-24.32944f,17.305f),
            Rect.MinMaxRect(-23.57677f,-17.30013955f,-21.22468f,17.305f),
            Rect.MinMaxRect(-20.47789f,-17.30013955f,-20.33089f,17.305f),
            Rect.MinMaxRect(-19.57822f,-17.30013955f,-17.22613f,17.305f),
            Rect.MinMaxRect(-16.47934f,-17.30013955f,-16.32645f,17.305f),
            Rect.MinMaxRect(-15.57966f,-17.30013955f,-13.22757f,17.305f),
            Rect.MinMaxRect(-12.4749f,-17.30013955f,-12.3279f,17.305f),
            Rect.MinMaxRect(-11.58111f,-17.30013955f,-9.22902f,17.305f),
            Rect.MinMaxRect(-8.55279f,-17.30013955f,-8.2529f,17.305f),
            Rect.MinMaxRect(8.24702f,-17.30013955f,8.54691f,17.305f),
            Rect.MinMaxRect(9.22314f,-17.30013955f,11.57523f,17.305f),
            Rect.MinMaxRect(12.3279f,-17.30013955f,12.4749f,17.305f),
            Rect.MinMaxRect(13.22169f,-17.30013955f,15.57378f,17.305f),
            Rect.MinMaxRect(16.32645f,-17.30013955f,16.47346f,17.305f),
            Rect.MinMaxRect(17.22613f,-17.30013955f,19.57234f,17.305f),
            Rect.MinMaxRect(20.32501f,-17.30013955f,20.47789f,17.305f),
            Rect.MinMaxRect(21.22468f,-17.30013955f,23.57677f,17.305f),
            Rect.MinMaxRect(24.32356f,-17.30013955f,24.47645f,17.305f),
            Rect.MinMaxRect(25.22324f,-17.30013955f,27.57533f,17.305f),
            Rect.MinMaxRect(28.32212f,-17.30013955f,28.475f,17.305f),
            Rect.MinMaxRect(29.22767f,-17.30013955f,31.57388f,17.305f),
            Rect.MinMaxRect(32.25011f,-17.30013955f,32.55f,17.305f),
            Rect.MinMaxRect(-8.25f,-17.30014f,-2.55496f,17.305f),
            Rect.MinMaxRect(-2.55496f,-18.69963f,0.04998f,17.305f),
            Rect.MinMaxRect(-33.87893f,-4.89876f,-32.55f,4.9036f),
            Rect.MinMaxRect(32.55f,-4.89876f,33.87893f,4.9036f),
        };
        static float Distance(V v,int plane,Rect area)
        {
            switch (plane) { case 0: return v.building.x-area.xMin; case 1: return area.xMax-v.building.x; case 2: return v.building.z-area.yMin; default: return area.yMax-v.building.z; }
        }
        static List<V> Clip(List<V> input,int plane,bool inside,Rect area)
        {
            var result = new List<V>(); if (input.Count == 0) return result;
            V previous = input[input.Count-1]; float da = Distance(previous,plane,area); bool pa = inside ? da >= 0 : da <= 0;
            foreach (V current in input)
            {
                float db=Distance(current,plane,area); bool pb=inside ? db>=0 : db<=0;
                if (pa != pb) result.Add(V.Lerp(previous,current,da/(da-db)));
                if (pb) result.Add(current);
                previous=current; da=db; pa=pb;
            }
            return result;
        }
        static List<List<V>> SubtractArea(List<V> polygon,Rect area)
        {
            var outside=new List<List<V>>(); var remainder=polygon;
            for(int plane=0;plane<4 && remainder.Count>0;plane++)
            {
                var piece=Clip(remainder,plane,false,area);
                if(piece.Count>=3)outside.Add(piece);
                remainder=Clip(remainder,plane,true,area);
            }
            return outside;
        }
        static void ClipGround()
        {
            var building=FindBuilding();var selected=Selection.activeGameObject;
            var filter=selected != null ? selected.GetComponent<MeshFilter>() : null;
            if (building==null || filter==null || filter.sharedMesh==null || !filter.sharedMesh.isReadable)
            { Debug.LogError("LID: selecciona una malla de terreno legible y comprueba que Edificio_LID esté en la escena activa."); return; }
            if (selected.transform.IsChildOf(building)) { Debug.LogError("LID: selecciona el terreno del Campus, no una pieza del edificio."); return; }
            Mesh source=filter.sharedMesh;
            if (source.bounds.size.y > .5f || source.subMeshCount != 1)
            { Debug.LogError("LID: el recorte está preparado para una malla de terreno horizontal de una submalla. Revisa esta selección manualmente."); return; }
            Vector3[] vertices=source.vertices; Vector2[] uv=source.uv; int[] indices=source.triangles;
            var resultV=new List<Vector3>();var resultUV=new List<Vector2>();var resultT=new List<int>();
            Action<List<V>> emit = polygon =>
            {
                if (polygon.Count<3) return;
                for(int k=1;k<polygon.Count-1;k++)
                {
                    if(Vector3.Cross(polygon[k].local-polygon[0].local,polygon[k+1].local-polygon[0].local).sqrMagnitude<1e-12f)continue;
                    int n=resultV.Count; foreach(int j in new[]{0,k,k+1}) { resultV.Add(polygon[j].local);resultUV.Add(polygon[j].uv); }
                    resultT.Add(n);resultT.Add(n+1);resultT.Add(n+2);
                }
            };
            for(int t=0;t<indices.Length;t+=3)
            {
                var remainder=new List<V>();
                for(int j=0;j<3;j++)
                {
                    int i=indices[t+j];Vector3 p=vertices[i];
                    remainder.Add(new V(p,building.InverseTransformPoint(selected.transform.TransformPoint(p)),uv.Length==vertices.Length?uv[i]:Vector2.zero));
                }
                var polygons=new List<List<V>> {remainder};
                foreach(Rect area in GroundVoids)
                {
                    var next=new List<List<V>>();
                    foreach(var polygon in polygons)next.AddRange(SubtractArea(polygon,area));
                    polygons=next;
                }
                foreach(var polygon in polygons)emit(polygon);
            }
            if(!AssetDatabase.IsValidFolder(Root+"/Generado"))AssetDatabase.CreateFolder(Root,"Generado");
            Mesh mesh=new Mesh{name="Terreno_Recorte_LID",indexFormat=IndexFormat.UInt32};
            mesh.SetVertices(resultV);mesh.SetUVs(0,resultUV);mesh.SetTriangles(resultT,0);mesh.RecalculateNormals();mesh.RecalculateBounds();
            string path=AssetDatabase.GenerateUniqueAssetPath(Root+"/Generado/Terreno_Recorte_LID.asset");AssetDatabase.CreateAsset(mesh,path);
            Undo.RecordObject(filter,"Recortar terreno bajo LID");filter.sharedMesh=mesh;
            var collider=selected.GetComponent<MeshCollider>(); if(collider!=null){Undo.RecordObject(collider,"Recortar colisión del terreno");collider.sharedMesh=mesh;}
            EditorSceneManager.MarkSceneDirty(selected.scene);AssetDatabase.SaveAssets();
            Debug.Log("LID: copia del terreno recortada bajo el edificio. Recorre el sótano y las conexiones exteriores antes de guardar.");
        }
    }
}
