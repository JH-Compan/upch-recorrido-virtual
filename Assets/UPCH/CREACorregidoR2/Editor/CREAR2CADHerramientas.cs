using System;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace UPCH.CREA.CorreccionCADR2.Editor {
public static class CREAR2CADHerramientas {
 const string Folder="Assets/UPCH/CREACorregidoR2/Prefabs/";
 static GameObject Insert(string file){var asset=AssetDatabase.LoadAssetAtPath<GameObject>(Folder+file+".prefab");if(!asset){Debug.LogError("Falta "+Folder+file+".prefab. Copia el paquete completo conservando sus .meta.");return null;}var go=(GameObject)PrefabUtility.InstantiatePrefab(asset);Undo.RegisterCreatedObjectUndo(go,"Insertar CREA R2");Selection.activeGameObject=go;EditorSceneManager.MarkSceneDirty(go.scene);return go;}
 [MenuItem("UPCH/CREA R2 CAD/Insertar edificio independiente")]
 static void Building(){Insert("Edificio_CREA_R2");}
 [MenuItem("UPCH/CREA R2 CAD/Comparar con CREA anterior seleccionado")]
 static void Replace(){
 var old=Selection.activeGameObject;
 if(!old||EditorUtility.IsPersistent(old)||old.name.IndexOf("CREA",StringComparison.OrdinalIgnoreCase)<0||old.GetComponentsInChildren<MeshFilter>(true).Length<100){EditorUtility.DisplayDialog("Selecciona CREA","En Hierarchy selecciona la raíz completa de tu CREA anterior. No selecciones un asset de Project, una pieza, Campus ni la conexión.","Aceptar");return;}
 Undo.IncrementCurrentGroup();var group=Undo.GetCurrentGroup();Undo.SetCurrentGroupName("Comparar CREA R2");var go=Insert("Edificio_CREA_R2");if(!go)return;go.transform.SetParent(old.transform.parent,false);go.transform.SetPositionAndRotation(old.transform.position,old.transform.rotation);go.transform.localScale=old.transform.localScale;Undo.RecordObject(old,"Conservar CREA anterior desactivado");old.SetActive(false);Undo.CollapseUndoOperations(group);EditorSceneManager.MarkSceneDirty(go.scene);Debug.Log("CREA R2 colocado con la transformación de la raíz anterior. La versión anterior queda conservada desactivada. Revisa cotas y recorridos antes de guardar; Ctrl+Z revierte la comparación.",go);
 }
 [MenuItem("UPCH/CREA R2 CAD/Insertar conexion I-J alineada al CREA seleccionado")]
 static void Connection(){var root=Selection.activeGameObject;if(!root||EditorUtility.IsPersistent(root)||root.GetComponentsInChildren<MeshFilter>(true).Length<100||root.name.IndexOf("CREA",StringComparison.OrdinalIgnoreCase)<0){Debug.LogError("Selecciona la raíz del CREA de la escena.");return;}var go=Insert("Conexion_I_J_R2");if(!go)return;go.transform.SetParent(root.transform.parent,false);go.transform.SetPositionAndRotation(root.transform.position,root.transform.rotation);go.transform.localScale=root.transform.localScale;Debug.Log("La conexión conserva el perfil R1. Si ya tienes una conexión I-J, conserva esa instancia o desactívala antes de insertar otra.",go);}
 [MenuItem("UPCH/CREA R2 CAD/Desempaquetar seleccionado para editar")]
 static void Unpack(){var go=Selection.activeGameObject;if(!go||EditorUtility.IsPersistent(go))return;var root=PrefabUtility.GetOutermostPrefabInstanceRoot(go);if(root)PrefabUtility.UnpackPrefabInstance(root,PrefabUnpackMode.Completely,InteractionMode.UserAction);}
 [MenuItem("UPCH/CREA R2 CAD/Revisar referencias del seleccionado")]
 static void Validate(){var root=Selection.activeGameObject;if(!root)return;int missing=0;foreach(var mf in root.GetComponentsInChildren<MeshFilter>(true))if(!mf.sharedMesh){Debug.LogError("Malla ausente: "+mf.name,mf);missing++;}foreach(var r in root.GetComponentsInChildren<Renderer>(true))foreach(var m in r.sharedMaterials)if(!m||!m.shader||m.shader.name=="Hidden/InternalErrorShader"){Debug.LogError("Material/shader no resuelto: "+r.name,r);missing++;}Debug.Log("Referencias no resueltas: "+missing+". Esta comprobación no valida altura libre, accesibilidad ni el controlador XR.",root);}
}}
