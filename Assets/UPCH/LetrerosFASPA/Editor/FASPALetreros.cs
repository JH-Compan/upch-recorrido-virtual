using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace UPCH.FASPA.Rotulos3D {
public static class FASPALetreros {
 [MenuItem("UPCH/FASPA letreros/Colocar en FASPA R3 seleccionado")]
 public static void Colocar(){
  GameObject edificio=Selection.activeGameObject;
  if(edificio==null || !edificio.name.StartsWith("Edificio_FASPA_R3")){EditorUtility.DisplayDialog("Selecciona FASPA R3","Selecciona la raíz Edificio_FASPA_R3 de Hierarchy. También puedes arrastrar los dos prefabs y colocarlos manualmente.","Aceptar");return;}
  if(edificio.transform.Find("Letreros_FASPA")!=null){Selection.activeGameObject=edificio.transform.Find("Letreros_FASPA").gameObject;return;}
  string basePath="Assets/UPCH/LetrerosFASPA/";
  GameObject a=AssetDatabase.LoadAssetAtPath<GameObject>(basePath+"Mural/Prefabs/Letrero_Mural_FASPA.prefab");
  GameObject b=AssetDatabase.LoadAssetAtPath<GameObject>(basePath+"Jardin/Prefabs/Letrero_Administracion_Salud.prefab");
  if(a==null || b==null){EditorUtility.DisplayDialog("Faltan prefabs","Copia la carpeta LetrerosFASPA completa dentro de Assets/UPCH.","Aceptar");return;}
  GameObject root=new GameObject("Letreros_FASPA");Undo.RegisterCreatedObjectUndo(root,"Colocar letreros FASPA");root.transform.SetParent(edificio.transform,false);
  GameObject mural=(GameObject)PrefabUtility.InstantiatePrefab(a);mural.transform.SetParent(root.transform,false);mural.transform.localPosition=new Vector3(-8.431f,1.20f,-14.022f);mural.transform.localRotation=Quaternion.Euler(0,196.2f,0);
  GameObject jardin=(GameObject)PrefabUtility.InstantiatePrefab(b);jardin.transform.SetParent(root.transform,false);jardin.transform.localPosition=new Vector3(3.225f,0,-19.05f);jardin.transform.localRotation=Quaternion.Euler(0,180,0);
  Selection.activeGameObject=root;EditorSceneManager.MarkSceneDirty(edificio.scene);
  EditorUtility.DisplayDialog("Letreros colocados","Ubicación inicial aproximada por foto. Ajusta cada raíz a tu muro y jardín y guarda la escena. Para mover letras individualmente, desempaqueta su prefab desde Hierarchy.","Aceptar");
 }
}
}
