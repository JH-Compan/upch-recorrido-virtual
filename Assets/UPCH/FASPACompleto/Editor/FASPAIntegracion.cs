using System;
using System.IO;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace UPCH.FASPACompleto {
public static class FASPAIntegracion {
 const string Base="Assets/UPCH/FASPACompleto";
 const string PrefabPath=Base+"/Prefabs/Edificio_FASPA.prefab";
 static string Safe(string s){foreach(char c in Path.GetInvalidFileNameChars())s=s.Replace(c,'_');return s.Replace('/','_').Replace('\\','_');}
 [MenuItem("UPCH/FASPA completo/1. Generar Meshes Materials y Prefab")]
 public static void Generar(){
  if(EditorApplication.isPlayingOrWillChangePlaymode){EditorUtility.DisplayDialog("FASPA","Sal del modo Play antes de generar archivos.","Aceptar");return;}
  if(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath)!=null){
   EditorGUIUtility.PingObject(AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath));
   EditorUtility.DisplayDialog("Prefab existente","Se conserva tu prefab actual y sus modificaciones. Usa la opción 2 para insertarlo o ábrelo para editarlo.","Aceptar");return;
  }
  GameObject fuente=AssetDatabase.LoadAssetAtPath<GameObject>(Base+"/Referencias/FASPA_Piezas.fbx");
  if(fuente==null){EditorUtility.DisplayDialog("Falta el modelo","Copia FASPACompleto en Assets/UPCH. Debe existir Referencias/FASPA_Piezas.fbx.","Aceptar");return;}
  Shader shader=Shader.Find("Universal Render Pipeline/Lit");if(shader==null)shader=Shader.Find("Standard");
  if(shader==null){EditorUtility.DisplayDialog("Shader no disponible","No se encontró URP/Lit ni Standard en este proyecto.","Aceptar");return;}
  foreach(string d in new[]{"Meshes","Materials","Prefabs","Scenes"})Directory.CreateDirectory(Base+"/"+d);
  AssetDatabase.Refresh();GameObject root=null;
  try{
   root=new GameObject("Edificio_FASPA");
   GameObject modelo=(GameObject)PrefabUtility.InstantiatePrefab(fuente);
   PrefabUtility.UnpackPrefabInstance(modelo,PrefabUnpackMode.Completely,InteractionMode.AutomatedAction);
   modelo.transform.SetParent(root.transform,false);
   // Recenter only translation; preserve the FBX axis conversion rotation and scale.
   modelo.transform.localPosition=Vector3.zero;modelo.name="FASPA_Geometria";
   MeshFilter[] filtros=modelo.GetComponentsInChildren<MeshFilter>(true);int n=0;
   foreach(MeshFilter filtro in filtros){
    EditorUtility.DisplayProgressBar("FASPA completo","Extrayendo "+filtro.name,(float)n/Math.Max(1,filtros.Length));n++;
    if(filtro.sharedMesh==null)continue;
    string ruta=Base+"/Meshes/"+Safe(filtro.name)+".asset";
    Mesh mesh=AssetDatabase.LoadAssetAtPath<Mesh>(ruta);
    if(mesh==null){mesh=UnityEngine.Object.Instantiate(filtro.sharedMesh);mesh.name=filtro.name;AssetDatabase.CreateAsset(mesh,ruta);}filtro.sharedMesh=mesh;
    MeshRenderer render=filtro.GetComponent<MeshRenderer>();
    if(render!=null){Material[] materiales=render.sharedMaterials;
     for(int i=0;i<materiales.Length;i++){
      Material original=materiales[i];if(original==null)continue;
      string mr=Base+"/Materials/"+Safe(original.name)+".mat";
      Material mat=AssetDatabase.LoadAssetAtPath<Material>(mr);
      if(mat==null){mat=new Material(shader);mat.name=original.name;
       Color col=original.HasProperty("_BaseColor")?original.GetColor("_BaseColor"):(original.HasProperty("_Color")?original.GetColor("_Color"):Color.gray);
       if(mat.HasProperty("_BaseColor"))mat.SetColor("_BaseColor",col);if(mat.HasProperty("_Color"))mat.SetColor("_Color",col);
       if(mat.HasProperty("_Smoothness"))mat.SetFloat("_Smoothness",original.name.Contains("vidrio") ? .45f : .15f);
       AssetDatabase.CreateAsset(mat,mr);
      }materiales[i]=mat;
     }render.sharedMaterials=materiales;
    }
    if(!filtro.name.Contains("puerta")){MeshCollider mc=filtro.gameObject.GetComponent<MeshCollider>();if(mc==null)mc=filtro.gameObject.AddComponent<MeshCollider>();mc.sharedMesh=mesh;mc.convex=false;}
   }
   GameObject prefab=PrefabUtility.SaveAsPrefabAsset(root,PrefabPath);if(prefab==null)throw new Exception("Unity no pudo guardar el prefab.");
   AssetDatabase.SaveAssets();Selection.activeObject=prefab;EditorGUIUtility.PingObject(prefab);
   EditorUtility.DisplayDialog("FASPA listo",n+" piezas procesadas. Meshes, Materials y Prefabs están generados. Usa UPCH > FASPA completo > 2. Insertar prefab en escena.","Aceptar");
  }catch(Exception ex){Debug.LogException(ex);EditorUtility.DisplayDialog("No se completó la generación",ex.Message+" Consulta Console. Los archivos ya creados se conservan para reintentar.","Aceptar");}
  finally{EditorUtility.ClearProgressBar();if(root!=null)UnityEngine.Object.DestroyImmediate(root);}
 }
 [MenuItem("UPCH/FASPA completo/2. Insertar prefab en escena")]
 public static void Insertar(){
  GameObject asset=AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);if(asset==null){EditorUtility.DisplayDialog("Genera primero el prefab","Ejecuta la opción 1 del mismo menú.","Aceptar");return;}
  GameObject nuevo=(GameObject)PrefabUtility.InstantiatePrefab(asset);Undo.RegisterCreatedObjectUndo(nuevo,"Insertar FASPA");Selection.activeGameObject=nuevo;EditorSceneManager.MarkSceneDirty(nuevo.scene);
 }
 [MenuItem("UPCH/FASPA completo/3. Desempaquetar FASPA seleccionado")]
 public static void Desempaquetar(){
  GameObject go=Selection.activeGameObject;if(go==null){EditorUtility.DisplayDialog("Selecciona FASPA","Selecciona la raíz Edificio_FASPA de Hierarchy.","Aceptar");return;}
  GameObject root=PrefabUtility.GetOutermostPrefabInstanceRoot(go);
  if(root==null || !root.name.StartsWith("Edificio_FASPA")){EditorUtility.DisplayDialog("Selecciona FASPA","Selecciona una instancia del prefab Edificio_FASPA.","Aceptar");return;}
  PrefabUtility.UnpackPrefabInstance(root,PrefabUnpackMode.Completely,InteractionMode.UserAction);Selection.activeGameObject=root;
 }
}
}
