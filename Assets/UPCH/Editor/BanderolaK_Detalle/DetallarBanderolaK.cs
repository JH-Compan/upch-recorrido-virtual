#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace UPCH.MedicinaK.Banderola
{
    [Serializable] public sealed class TrazoK { public string name; public Vector3[] vertices; public int[] triangles; }
    [Serializable] public sealed class ArteK { public string schema; public TrazoK[] parts; }

    public sealed class DetallarBanderolaK : EditorWindow
    {
        const string DataPath="Assets/UPCH/Editor/BanderolaK_Detalle/BanderolaK_Detalle.json";
        const string DetailName="Detalle_Banderola_K";
        GameObject banderola;
        bool invertirCara;
        float separacion=.002f;
        Color tinta=new Color(.98f,.976f,.953f,1);
        string estado="Añade palabras y curvas sobre la lona existente. No regenera el edificio.";

        [MenuItem("Tools/UPCH/Medicina/Detallar banderola roja")]
        public static void Abrir(){GetWindow<DetallarBanderolaK>("Banderola K");}
        void OnGUI()
        {
            EditorGUILayout.LabelField("Detalle de la banderola",EditorStyles.boldLabel);
            banderola=(GameObject)EditorGUILayout.ObjectField("Banderola roja",banderola,typeof(GameObject),true);
            invertirCara=EditorGUILayout.Toggle("Invertir cara",invertirCara);
            separacion=EditorGUILayout.FloatField("Separación de la lona (m locales)",separacion);
            tinta=EditorGUILayout.ColorField("Color de letras y curvas",tinta);
            if(GUILayout.Button("Detectar banderola del pabellón K"))
            {
                try{banderola=Detectar();Selection.activeGameObject=banderola;estado="Banderola detectada: "+banderola.name;}
                catch(Exception e){estado=e.Message;}
            }
            if(GUILayout.Button("Añadir palabras y curvas"))Crear();
            if(GUILayout.Button("Quitar sólo este detalle"))Quitar();
            EditorGUILayout.HelpBox(estado,MessageType.Info);
        }
        static IEnumerable<GameObject> Recorrer(GameObject g)
        {
            yield return g;
            foreach(Transform t in g.transform)foreach(var obj in Recorrer(t.gameObject))yield return obj;
        }
        static GameObject Detectar()
        {
            var scene=SceneManager.GetActiveScene();
            var matches=scene.GetRootGameObjects().SelectMany(Recorrer)
                .Where(o=>o.activeInHierarchy && o.name.EndsWith("_Lona_Roja",StringComparison.Ordinal) && o.GetComponent<MeshFilter>()!=null).ToArray();
            if(matches.Length!=1)throw new InvalidOperationException("Arrastra al campo el objeto de la lona roja en Hierarchy. Se encontraron "+matches.Length+" coincidencias activas.");
            return matches[0];
        }
        GameObject Obtener()
        {
            if(banderola==null)banderola=Detectar();
            if(EditorUtility.IsPersistent(banderola) || !banderola.scene.IsValid())throw new InvalidOperationException("Selecciona la lona de la escena, no un asset.");
            return banderola;
        }
        static void Carpeta(string path)
        {
            var pieces=path.Split('/');string at=pieces[0];
            for(int i=1;i<pieces.Length;i++){string next=at+"/"+pieces[i];if(!AssetDatabase.IsValidFolder(next))AssetDatabase.CreateFolder(at,pieces[i]);at=next;}
        }
        void Crear()
        {
            GameObject root=null;var meshes=new List<Mesh>();
            try
            {
                if(EditorApplication.isPlayingOrWillChangePlaymode)throw new InvalidOperationException("Detén Play antes de añadir el detalle.");
                var board=Obtener();
                if(board.transform.Find(DetailName)!=null)throw new InvalidOperationException("Esta lona ya tiene el detalle. No se creará encima otra copia.");
                var filter=board.GetComponent<MeshFilter>();
                if(filter==null || filter.sharedMesh==null)throw new InvalidOperationException("Selecciona el objeto de la lona que contiene Mesh Filter.");
                Bounds bounds=filter.sharedMesh.bounds;
                bool thinX=bounds.size.x<bounds.size.z;
                float width=thinX?bounds.size.z:bounds.size.x;float height=bounds.size.y;
                if(width<=0 || height<=width || bounds.size.y<.01f)throw new InvalidOperationException("La malla seleccionada no parece una banderola vertical.");
                if(float.IsNaN(separacion) || float.IsInfinity(separacion) || separacion<.0001f || separacion>.10f)throw new InvalidOperationException("Usa una separación entre 0.0001 y 0.10 metros locales. Recomendada: 0.002.");
                var art=JsonUtility.FromJson<ArteK>(File.ReadAllText(DataPath,Encoding.UTF8));
                if(art==null || art.schema!="UPCH_K_BANDEROLA_1" || art.parts==null || art.parts.Length==0)throw new InvalidDataException("Falta el JSON del complemento o es incompatible.");
                Vector3 normal=thinX?Vector3.left:Vector3.back;
                Vector3 right=thinX?Vector3.back:Vector3.right;
                if(invertirCara){normal=-normal;right=-right;}
                Vector3 center=new Vector3(bounds.center.x,bounds.min.y,bounds.center.z);
                center+=normal*((thinX?bounds.size.x:bounds.size.z)/2+separacion);
                Vector3 origin=center-right*(width/2);
                bool flip=Vector3.Dot(Vector3.Cross(right,Vector3.up),normal)<0;
                foreach(var part in art.parts)
                {
                    if(part.vertices==null || part.triangles==null || part.triangles.Length%3!=0 || part.triangles.Any(i=>i<0 || i>=part.vertices.Length))throw new InvalidDataException("Índices inválidos en "+part.name);
                    var points=new Vector3[part.vertices.Length];
                    for(int i=0;i<points.Length;i++)
                    {
                        var v=part.vertices[i];points[i]=origin+right*(v.x*width)+Vector3.up*(v.y*height)+normal*(v.z*width);
                    }
                    var triangles=(int[])part.triangles.Clone();
                    if(flip)for(int i=0;i<triangles.Length;i+=3){int t=triangles[i+1];triangles[i+1]=triangles[i+2];triangles[i+2]=t;}
                    var mesh=new Mesh{name="Banderola_"+part.name,indexFormat=IndexFormat.UInt32};
                    mesh.vertices=points;mesh.triangles=triangles;mesh.RecalculateNormals();mesh.RecalculateBounds();meshes.Add(mesh);
                }
                Shader shader=Shader.Find("Universal Render Pipeline/Unlit");
                if(shader==null)shader=Shader.Find("Unlit/Color");
                if(shader==null)throw new InvalidOperationException("No se encuentra un shader Unlit compatible.");
                string folder="Assets/UPCH/BanderolaK_Generado/Detalle_"+Guid.NewGuid().ToString("N");Carpeta(folder);
                var material=new Material(shader){name="K_Banderola_Letras_Blancas"};tinta.a=1;
                if(material.HasProperty("_BaseColor"))material.SetColor("_BaseColor",tinta);
                if(material.HasProperty("_Color"))material.SetColor("_Color",tinta);
                if(material.HasProperty("_Surface"))material.SetFloat("_Surface",0);
                if(material.HasProperty("_ZWrite"))material.SetFloat("_ZWrite",1);
                if(material.HasProperty("_SrcBlend"))material.SetFloat("_SrcBlend",(float)BlendMode.One);
                if(material.HasProperty("_DstBlend"))material.SetFloat("_DstBlend",(float)BlendMode.Zero);
                material.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");material.DisableKeyword("_ALPHABLEND_ON");
                material.SetOverrideTag("RenderType","Opaque");material.renderQueue=(int)RenderQueue.Geometry;
                AssetDatabase.CreateAsset(material,folder+"/Tinta_Blanca.mat");
                AssetDatabase.StartAssetEditing();
                try
                {
                    AssetDatabase.CreateAsset(meshes[0],folder+"/Letras_y_Curvas.asset");
                    for(int i=1;i<meshes.Count;i++)AssetDatabase.AddObjectToAsset(meshes[i],meshes[0]);
                }
                finally{AssetDatabase.StopAssetEditing();}
                root=new GameObject(DetailName);root.transform.SetParent(board.transform,false);
                for(int i=0;i<meshes.Count;i++)
                {
                    var obj=new GameObject(art.parts[i].name);obj.transform.SetParent(root.transform,false);
                    obj.AddComponent<MeshFilter>().sharedMesh=meshes[i];var renderer=obj.AddComponent<MeshRenderer>();renderer.sharedMaterial=material;
                    renderer.shadowCastingMode=ShadowCastingMode.Off;renderer.receiveShadows=false;
                    GameObjectUtility.SetStaticEditorFlags(obj,StaticEditorFlags.BatchingStatic);
                }
                Undo.RegisterCreatedObjectUndo(root,"Añadir detalle de banderola K");
                AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(board.scene);Selection.activeGameObject=root;
                estado="Palabras y curvas añadidas. Guarda Campus con Ctrl+S. El edificio y la lona original no se regeneraron. Si quedó en el reverso, quita sólo el detalle, activa Invertir cara y vuelve a añadirlo.";
            }
            catch(Exception e)
            {
                if(root!=null)DestroyImmediate(root);
                foreach(var mesh in meshes)if(mesh!=null && !EditorUtility.IsPersistent(mesh))DestroyImmediate(mesh);
                estado=e.Message;Debug.LogException(e);
            }
        }
        void Quitar()
        {
            try
            {
                if(EditorApplication.isPlayingOrWillChangePlaymode)throw new InvalidOperationException("Detén Play antes de quitar el detalle.");
                var board=Obtener();var detail=board.transform.Find(DetailName);
                if(detail==null){estado="Esta lona no tiene el detalle de este complemento.";return;}
                Undo.DestroyObjectImmediate(detail.gameObject);EditorSceneManager.MarkSceneDirty(board.scene);
                estado="Se quitó sólo el detalle. La lona y el edificio permanecen. Los assets se conservan; puedes deshacer con Ctrl+Z.";
            }
            catch(Exception e){estado=e.Message;}
        }
    }
}
#endif
