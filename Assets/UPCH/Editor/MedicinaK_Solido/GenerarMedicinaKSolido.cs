#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace UPCH.MedicinaK.Solido
{
    [Serializable] public sealed class MaterialK
    {
        public string id; public Color color; public bool transparent; public float roughness;
    }
    [Serializable] public sealed class PiezaK
    {
        public string id; public int level; public string category; public string material;
        public string source; public string status; public bool collider; public bool visible;
        public Vector3 position; public Vector3 rotation; public Vector3 scale;
        public Vector3[] vertices; public int[] triangles; public Vector3 expectedSize;
    }
    [Serializable] public sealed class DatosK
    {
        public string schema; public string rootName; public string description;
        public Vector3 referenceCenter; public MaterialK[] materials; public PiezaK[] parts;
    }

    public sealed class GenerarMedicinaKSolido : EditorWindow
    {
        const string DataPath = "Assets/UPCH/Editor/MedicinaK_Solido/MedicinaK_Solido.json";
        const string GeneratedFolder = "Assets/UPCH/MedicinaK_Solido_Generado";
        GameObject referencia;
        Vector3 ajustePosicion;
        float ajusteGiro;
        string informe = "Modelo aproximado de seis niveles. Las cotas documentadas y las estimaciones se distinguen en el inventario incluido.";
        Vector2 scroll;

        [MenuItem("Tools/UPCH/Medicina/Generar pabellon K solido")]
        public static void Abrir() { GetWindow<GenerarMedicinaKSolido>("Pabellón K sólido"); }

        void OnGUI()
        {
            EditorGUILayout.LabelField("Pabellón K - seis niveles", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Muros, pisos y cubierta: material opaco y mallas cerradas. Sólo Vidrios usa transparencia. Incluye estimaciones editables; no es un levantamiento exacto.", MessageType.Info);
            referencia = (GameObject)EditorGUILayout.ObjectField("Bloque K original", referencia, typeof(GameObject), true);
            ajustePosicion = EditorGUILayout.Vector3Field("Ajuste en metros", ajustePosicion);
            ajusteGiro = EditorGUILayout.FloatField("Ajuste giro Y (grados)", ajusteGiro);
            if (GUILayout.Button("1. Validar el archivo")) ValidarArchivo();
            if (GUILayout.Button("2. Crear vista previa en escena aparte")) Generar(true);
            if (GUILayout.Button("3. Generar dentro de Campus")) Generar(false);
            if (GUILayout.Button("4. Validar modelo creado")) Comparar();
            EditorGUILayout.Space();
            scroll = EditorGUILayout.BeginScrollView(scroll);
            EditorGUILayout.TextArea(informe, GUILayout.ExpandHeight(true));
            EditorGUILayout.EndScrollView();
        }

        static DatosK Leer()
        {
            if (!File.Exists(DataPath)) throw new FileNotFoundException("No encuentro " + DataPath + ". Copia la carpeta MedicinaK_Solido completa dentro de Assets/UPCH/Editor.");
            var d = JsonUtility.FromJson<DatosK>(File.ReadAllText(DataPath, Encoding.UTF8));
            if (d == null || d.schema != "UPCH_K_SOLID_1" || d.parts == null || d.parts.Length == 0) throw new InvalidDataException("JSON vacío o de otra versión.");
            return d;
        }
        static bool Finito(float v) { return !float.IsNaN(v) && !float.IsInfinity(v); }
        static bool Finito(Vector3 v) { return Finito(v.x) && Finito(v.y) && Finito(v.z); }
        static List<string> Revisar(DatosK d)
        {
            var errores = new List<string>(); var ids = new HashSet<string>(StringComparer.Ordinal);
            if (string.IsNullOrWhiteSpace(d.rootName)) errores.Add("Raíz sin nombre.");
            if (d.materials == null) { errores.Add("Faltan materiales."); return errores; }
            var mats = new HashSet<string>(StringComparer.Ordinal);
            foreach (var m in d.materials)
            {
                if (m == null || string.IsNullOrWhiteSpace(m.id) || !mats.Add(m.id)) errores.Add("Material nulo o ID repetido.");
                else if (m.id != "vidrio" && (m.transparent || m.color.a < .999f)) errores.Add(m.id + ": sólo vidrio puede ser transparente.");
            }
            foreach (var p in d.parts)
            {
                if (p == null) { errores.Add("Pieza nula."); continue; }
                if (string.IsNullOrWhiteSpace(p.id) || !ids.Add(p.id)) errores.Add("ID duplicado o vacío: " + p.id);
                if (p.level < 1 || p.level > 6) errores.Add(p.id + ": nivel incorrecto.");
                if (!mats.Contains(p.material)) errores.Add(p.id + ": material inexistente.");
                if (!Finito(p.position) || !Finito(p.rotation) || !Finito(p.scale) || p.scale.x <= 0 || p.scale.y <= 0 || p.scale.z <= 0) errores.Add(p.id + ": Transform inválido.");
                if (p.vertices == null || p.vertices.Length < 4 || p.vertices.Any(v => !Finito(v))) { errores.Add(p.id + ": vértices inválidos."); continue; }
                if (p.triangles == null || p.triangles.Length < 12 || p.triangles.Length % 3 != 0 || p.triangles.Any(i => i < 0 || i >= p.vertices.Length)) { errores.Add(p.id + ": índices inválidos."); continue; }
                double volumen = 0;
                for (int i = 0; i < p.triangles.Length; i += 3)
                {
                    Vector3 a = p.vertices[p.triangles[i]], b = p.vertices[p.triangles[i+1]], c = p.vertices[p.triangles[i+2]];
                    if (Vector3.Cross(b-a,c-a).sqrMagnitude < 1e-16f) { errores.Add(p.id + ": triángulo degenerado."); break; }
                    volumen += Vector3.Dot(a,Vector3.Cross(b,c)) / 6.0;
                }
                if (volumen <= 0) errores.Add(p.id + ": normales invertidas o volumen nulo.");
            }
            for (int n=1; n<=6; n++)
                if (!d.parts.Any(p => p != null && p.level == n && p.category == "Pisos")) errores.Add("Falta piso " + n);
            return errores;
        }

        void ValidarArchivo()
        {
            try
            {
                var d=Leer();var errores=Revisar(d);
                informe=errores.Count==0 ? d.parts.Length + " piezas, seis niveles y cubierta. Archivo listo para generar. Las estimaciones arquitectónicas figuran en el documento incluido." : string.Join("\n",errores);
            }
            catch(Exception e) { informe=e.Message; }
        }

        static IEnumerable<GameObject> Recorrer(GameObject g)
        {
            yield return g;
            foreach (Transform child in g.transform) foreach (var obj in Recorrer(child.gameObject)) yield return obj;
        }
        static IEnumerable<GameObject> ObjetosEscena(Scene scene)
        { return scene.GetRootGameObjects().SelectMany(Recorrer); }

        GameObject EncontrarReferencia(Scene scene)
        {
            if (referencia != null)
            {
                if (referencia.scene != scene || EditorUtility.IsPersistent(referencia)) throw new InvalidOperationException("La referencia debe ser una instancia de Campus, no un asset.");
                if (referencia.name != "K - Facultad de Medicina") throw new InvalidOperationException("Usa el bloque original K - Facultad de Medicina. No uses Edificio_K_Modelo.");
                return referencia;
            }
            var matches=ObjetosEscena(scene).Where(g=>g.name=="K - Facultad de Medicina").ToArray();
            if (matches.Length != 1) throw new InvalidOperationException("Arrastra el bloque original K - Facultad de Medicina al campo de la ventana.");
            return matches[0];
        }
        static Bounds LimitesReferencia(GameObject source)
        {
            bool init=false;Bounds b=new Bounds();
            foreach(var mf in source.GetComponentsInChildren<MeshFilter>(true))
            {
                if(mf.sharedMesh==null)continue;Bounds local=mf.sharedMesh.bounds;
                for(int ix=0;ix<2;ix++)for(int iy=0;iy<2;iy++)for(int iz=0;iz<2;iz++)
                {
                    var v=new Vector3(ix==0?local.min.x:local.max.x,iy==0?local.min.y:local.max.y,iz==0?local.min.z:local.max.z);
                    v=source.transform.InverseTransformPoint(mf.transform.TransformPoint(v));
                    if(!init){b=new Bounds(v,Vector3.zero);init=true;}else b.Encapsulate(v);
                }
            }
            if(!init)throw new InvalidOperationException("El bloque original no tiene malla para calcular su colocación.");
            return b;
        }

        void Generar(bool previa)
        {
            if(EditorApplication.isPlayingOrWillChangePlaymode){informe="Detén Play antes de generar.";return;}
            DatosK d;GameObject source=null;Scene scene=SceneManager.GetActiveScene();
            string rootName;
            try
            {
                d=Leer();var errors=Revisar(d);if(errors.Count!=0){informe=string.Join("\n",errors);return;}
                rootName=d.rootName+(previa?"_VistaPrevia":"");
                if(previa)
                {
                    for(int i=0;i<SceneManager.sceneCount;i++)
                    {
                        var s=SceneManager.GetSceneAt(i);
                        if(s.isLoaded && ObjetosEscena(s).Any(g=>g.name==rootName)) {informe="Ya existe una vista previa abierta. Ciérrala antes de crear otra.";return;}
                    }
                }
                else
                {
                    if(!scene.IsValid() || scene.name!="Campus")throw new InvalidOperationException("Abre Campus y déjala como escena activa.");
                    source=EncontrarReferencia(scene);
                    if(ObjetosEscena(scene).Any(g=>g.name==rootName))throw new InvalidOperationException("Este modelo ya existe, incluso si está desactivado. No se generará una copia encima.");
                }
            }
            catch(Exception e){informe=e.Message;return;}

            var meshes=new List<Mesh>();GameObject root=null;bool registered=false;
            int undoGroup=-1;Scene previousActive=SceneManager.GetActiveScene();
            string folder=GeneratedFolder+"/K_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss",CultureInfo.InvariantCulture)+"_"+Guid.NewGuid().ToString("N").Substring(0,6);
            try
            {
                for(int i=0;i<d.parts.Length;i++)
                {
                    if(i%50==0)EditorUtility.DisplayProgressBar("Medicina K","Preparando mallas cerradas",(float)i/d.parts.Length*.45f);
                    meshes.Add(CrearMalla(d.parts[i]));
                }
                if(previa)
                {
                    scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Additive);
                    SceneManager.SetActiveScene(scene);
                }
                AsegurarCarpeta(folder);
                var materiales=CrearMateriales(d,folder);
                AssetDatabase.StartAssetEditing();
                try
                {
                    AssetDatabase.CreateAsset(meshes[0],folder+"/Mallas_K.asset");
                    for(int i=1;i<meshes.Count;i++)AssetDatabase.AddObjectToAsset(meshes[i],meshes[0]);
                }
                finally{AssetDatabase.StopAssetEditing();}
                root=new GameObject(rootName);
                if(root.scene!=scene)SceneManager.MoveGameObjectToScene(root,scene);
                if(source!=null)
                {
                    Bounds bounds=LimitesReferencia(source);
                    float yaw=bounds.size.z>bounds.size.x?-90:0;
                    var rotation=source.transform.rotation*Quaternion.Euler(0,yaw+ajusteGiro,0);
                    Vector3 anchor=source.transform.TransformPoint(new Vector3(bounds.center.x,bounds.min.y,bounds.center.z));
                    root.transform.SetPositionAndRotation(anchor-rotation*d.referenceCenter+ajustePosicion,rotation);
                }
                var grupos=new Dictionary<string,Transform>();
                foreach(var n in Enumerable.Range(1,6))grupos["Nivel_"+n.ToString("00")]=Hijo(root.transform,"Nivel_"+n.ToString("00"));
                for(int i=0;i<d.parts.Length;i++)
                {
                    if(i%50==0)EditorUtility.DisplayProgressBar("Medicina K","Creando muros, pisos y detalles",.45f+(float)i/d.parts.Length*.50f);
                    var p=d.parts[i];string level="Nivel_"+p.level.ToString("00");string key=level+"/"+p.category;
                    if(!grupos.ContainsKey(key))grupos[key]=Hijo(grupos[level],p.category);
                    var obj=new GameObject(p.id);obj.transform.SetParent(grupos[key],false);
                    obj.transform.localPosition=p.position;obj.transform.localRotation=Quaternion.Euler(p.rotation);obj.transform.localScale=p.scale;
                    obj.AddComponent<MeshFilter>().sharedMesh=meshes[i];
                    var renderer=obj.AddComponent<MeshRenderer>();renderer.sharedMaterial=materiales[p.material];renderer.enabled=p.visible;
                    renderer.shadowCastingMode=ShadowCastingMode.On;renderer.receiveShadows=true;
                    if(p.category!="Puertas")GameObjectUtility.SetStaticEditorFlags(obj,StaticEditorFlags.BatchingStatic);
                    if(p.collider){var collider=obj.AddComponent<MeshCollider>();collider.sharedMesh=meshes[i];collider.convex=false;}
                }
                Undo.IncrementCurrentGroup();undoGroup=Undo.GetCurrentGroup();Undo.SetCurrentGroupName("Crear pabellón K sólido");
                Undo.RegisterCreatedObjectUndo(root,"Crear pabellón K sólido");registered=true;
                if(source!=null){Undo.RecordObject(source,"Conservar bloque original desactivado");source.SetActive(false);}
                Undo.CollapseUndoOperations(undoGroup);
                AssetDatabase.SaveAssets();EditorSceneManager.MarkSceneDirty(scene);
                Selection.activeGameObject=root;
                if(SceneView.lastActiveSceneView!=null)
                {
                    if(previa)SceneView.lastActiveSceneView.sceneLighting=false;
                    SceneView.lastActiveSceneView.FrameSelected();
                }
                informe=d.parts.Length+" piezas creadas.\n"+(previa?"Vista previa en escena aparte; Campus no se modificó.":"Bloque original conservado desactivado; guarda Campus después de revisar.")+"\nMallas y materiales: "+folder+"\nComprueba la colocación frente a los edificios J y L; puedes mover y girar la raíz sin deformar las piezas.";
            }
            catch(Exception e)
            {
                if(registered && undoGroup>=0)Undo.RevertAllDownToGroup(undoGroup);
                else if(root!=null)DestroyImmediate(root);
                foreach(var mesh in meshes)if(mesh!=null && !EditorUtility.IsPersistent(mesh))DestroyImmediate(mesh);
                if(previa && scene.IsValid() && scene!=previousActive)EditorSceneManager.CloseScene(scene,true);
                if(previousActive.IsValid() && previousActive.isLoaded)SceneManager.SetActiveScene(previousActive);
                informe="No se completó la generación: "+e.Message+"\nEl bloque original se conserva. Pueden quedar assets nuevos sin usar en "+folder;
                Debug.LogException(e);
            }
            finally{EditorUtility.ClearProgressBar();}
        }

        static Transform Hijo(Transform parent,string name)
        {var child=new GameObject(name);child.transform.SetParent(parent,false);return child.transform;}
        static void AsegurarCarpeta(string path)
        {
            var segments=path.Split('/');string at=segments[0];
            for(int i=1;i<segments.Length;i++){string next=at+"/"+segments[i];if(!AssetDatabase.IsValidFolder(next))AssetDatabase.CreateFolder(at,segments[i]);at=next;}
        }
        static Mesh CrearMalla(PiezaK p)
        {
            // Each face owns its vertices: sharp concrete edges, correct face normals and no dependence on back-face rendering.
            var vertices=new Vector3[p.triangles.Length];var uv=new Vector2[vertices.Length];var indices=new int[vertices.Length];
            for(int i=0;i<p.triangles.Length;i+=3)
            {
                Vector3 a=p.vertices[p.triangles[i]],b=p.vertices[p.triangles[i+1]],c=p.vertices[p.triangles[i+2]];
                Vector3 normal=Vector3.Cross(b-a,c-a).normalized;
                for(int j=0;j<3;j++)
                {
                    int at=i+j;Vector3 v=p.vertices[p.triangles[at]];vertices[at]=v;indices[at]=at;
                    uv[at]=Mathf.Abs(normal.y)>.5f?new Vector2(v.x,v.z):Mathf.Abs(normal.x)>.5f?new Vector2(v.z,v.y):new Vector2(v.x,v.y);
                }
            }
            var mesh=new Mesh{name=p.id,indexFormat=IndexFormat.UInt32};mesh.vertices=vertices;mesh.triangles=indices;mesh.uv=uv;
            mesh.RecalculateNormals();mesh.RecalculateBounds();return mesh;
        }

        static Dictionary<string,Material> CrearMateriales(DatosK d,string folder)
        {
            Shader shader=Shader.Find("Universal Render Pipeline/Lit");
            if(shader==null)shader=Shader.Find("Standard");
            if(shader==null)throw new InvalidOperationException("No se encuentra URP/Lit ni Standard.");
            var map=new Dictionary<string,Material>();
            foreach(var entry in d.materials)
            {
                bool glass=entry.id=="vidrio";Color color=entry.color;if(!glass)color.a=1;
                var mat=new Material(shader){name="K_"+entry.id,doubleSidedGI=true};
                if(mat.HasProperty("_BaseColor"))mat.SetColor("_BaseColor",color);if(mat.HasProperty("_Color"))mat.SetColor("_Color",color);
                if(mat.HasProperty("_Metallic"))mat.SetFloat("_Metallic",entry.id=="metal"?.65f:0);
                if(mat.HasProperty("_Smoothness"))mat.SetFloat("_Smoothness",1-Mathf.Clamp01(entry.roughness));
                if(mat.HasProperty("_Glossiness"))mat.SetFloat("_Glossiness",1-Mathf.Clamp01(entry.roughness));
                if(mat.HasProperty("_Cull"))mat.SetFloat("_Cull",(float)CullMode.Back);
                if(mat.HasProperty("_Surface"))mat.SetFloat("_Surface",glass?1:0);
                if(mat.HasProperty("_Mode"))mat.SetFloat("_Mode",glass?3:0);
                if(mat.HasProperty("_SrcBlend"))mat.SetInt("_SrcBlend",glass?(int)BlendMode.SrcAlpha:(int)BlendMode.One);
                if(mat.HasProperty("_DstBlend"))mat.SetInt("_DstBlend",glass?(int)BlendMode.OneMinusSrcAlpha:(int)BlendMode.Zero);
                if(mat.HasProperty("_ZWrite"))mat.SetInt("_ZWrite",glass?0:1);
                mat.DisableKeyword("_ALPHATEST_ON");mat.DisableKeyword("_ALPHAPREMULTIPLY_ON");
                if(glass){mat.EnableKeyword("_SURFACE_TYPE_TRANSPARENT");mat.EnableKeyword("_ALPHABLEND_ON");}
                else{mat.DisableKeyword("_SURFACE_TYPE_TRANSPARENT");mat.DisableKeyword("_ALPHABLEND_ON");}
                mat.SetOverrideTag("RenderType",glass?"Transparent":"Opaque");mat.renderQueue=glass?(int)RenderQueue.Transparent:(int)RenderQueue.Geometry;
                AssetDatabase.CreateAsset(mat,folder+"/K_"+entry.id+".mat");map.Add(entry.id,mat);
                if(entry.id=="concreto")
                {
                    var texture=new Texture2D(128,128,TextureFormat.RGBA32,true){name="K_Concreto_Sutil",wrapMode=TextureWrapMode.Repeat};
                    var pixels=new Color[128*128];
                    for(int y=0;y<128;y++)for(int x=0;x<128;x++)
                    {
                        float n=Mathf.PerlinNoise(x*.19f+13.7f,y*.19f+7.2f)*.08f+Mathf.PerlinNoise(x*.65f,y*.65f)*.035f;
                        float shade=.94f+n;pixels[y*128+x]=new Color(shade,shade,shade,1);
                    }
                    texture.SetPixels(pixels);texture.Apply(true,false);AssetDatabase.AddObjectToAsset(texture,mat);
                    if(mat.HasProperty("_BaseMap")){mat.SetTexture("_BaseMap",texture);mat.SetTextureScale("_BaseMap",new Vector2(3,3));}
                    if(mat.HasProperty("_MainTex")){mat.SetTexture("_MainTex",texture);mat.SetTextureScale("_MainTex",new Vector2(3,3));}
                }
            }
            return map;
        }

        void Comparar()
        {
            try
            {
                var d=Leer();GameObject root=null;
                for(int i=0;i<SceneManager.sceneCount;i++)
                {
                    var s=SceneManager.GetSceneAt(i);if(!s.isLoaded)continue;
                    root=s.GetRootGameObjects().FirstOrDefault(g=>g.name==d.rootName || g.name==d.rootName+"_VistaPrevia");if(root!=null)break;
                }
                if(root==null)throw new InvalidOperationException("No encuentro un modelo creado por este generador.");
                var objects=Recorrer(root).GroupBy(o=>o.name).ToDictionary(g=>g.Key,g=>g.ToArray());
                var sb=new StringBuilder();int issues=0;
                foreach(var p in d.parts)
                {
                    if(!objects.TryGetValue(p.id,out var matches) || matches.Length!=1){sb.AppendLine(p.id+": falta o duplicada.");issues++;continue;}
                    var go=matches[0];var mf=go.GetComponent<MeshFilter>();var renderer=go.GetComponent<MeshRenderer>();
                    if(mf==null || mf.sharedMesh==null){sb.AppendLine(p.id+": falta malla.");issues++;continue;}
                    Bounds expected=new Bounds(p.vertices[0],Vector3.zero);foreach(var v in p.vertices)expected.Encapsulate(v);
                    var actual=mf.sharedMesh.bounds;
                    if((actual.center-expected.center).magnitude>.001f || (actual.size-expected.size).magnitude>.001f){sb.AppendLine(p.id+": malla alterada.");issues++;}
                    if((go.transform.localPosition-p.position).magnitude>.001f || Quaternion.Angle(go.transform.localRotation,Quaternion.Euler(p.rotation))>.01f || (go.transform.localScale-p.scale).magnitude>.001f){sb.AppendLine(p.id+": Transform modificado.");issues++;}
                    if(p.collider && go.GetComponent<Collider>()==null){sb.AppendLine(p.id+": falta collider.");issues++;}
                    if(renderer==null || renderer.sharedMaterial==null){sb.AppendLine(p.id+": falta material.");issues++;continue;}
                    var material=renderer.sharedMaterial;
                    if(p.material!="vidrio")
                    {
                        bool transparent=material.renderQueue>2500 || material.HasProperty("_Surface") && material.GetFloat("_Surface")>.5f;
                        Color color=material.HasProperty("_BaseColor")?material.GetColor("_BaseColor"):material.color;
                        if(transparent || color.a<.999f){sb.AppendLine(p.id+": material opaco cambiado a transparente.");issues++;}
                    }
                }
                informe=issues+" discrepancias respecto al JSON.\n"+sb+"\nEste control no certifica medidas reales ni sustituye el recorrido manual por puertas, escaleras y rampas.";
            }
            catch(Exception e){informe=e.Message;}
        }
    }
}
#endif
