using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace UPCH.CREAEditableR1.Editor {
public static class CREAR1Herramientas {
 const string Dir="Assets/UPCH/CREAEditable/Prefabs/";
 static GameObject Insert(string file) {
  var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Dir+file+".prefab");
  if(!prefab){Debug.LogError("No se encuentra "+Dir+file+".prefab. Conserva la carpeta CREAEditable completa dentro de Assets/UPCH.");return null;}
  var root=(GameObject)PrefabUtility.InstantiatePrefab(prefab);Undo.RegisterCreatedObjectUndo(root,"Insertar CREA");Selection.activeGameObject=root;EditorSceneManager.MarkSceneDirty(root.scene);return root;
 }
 [MenuItem("UPCH/CREA editable R1/1. Insertar edificio independiente")]
 static void Edificio(){Insert("Edificio_CREA_R1");}
 [MenuItem("UPCH/CREA editable R1/2. Insertar rampas y paso I-J")]
 static void Conexion(){Insert("Conexion_I_J_R1");}
 [MenuItem("UPCH/CREA editable R1/3. Colocar conjunto junto a FASPA R3 seleccionado")]
 static void Colocar(){
  var j=Selection.activeGameObject;
  if(!j||!j.name.ToUpperInvariant().Contains("FASPA")||j.GetComponentsInChildren<MeshFilter>(true).Length<100){EditorUtility.DisplayDialog("Selecciona FASPA R3","Selecciona la raíz completa del FASPA nativo R3. Este ajuste presupone sus ejes y su pivote originales. No sirve para el FBX antiguo ni para una pieza suelta.","Aceptar");return;}
  var pos=j.transform.TransformPoint(new Vector3(-29.075f,0f,.65f));
  foreach(var file in new[]{"Edificio_CREA_R1","Conexion_I_J_R1"}){var go=Insert(file);if(!go)continue;go.transform.SetPositionAndRotation(pos,j.transform.rotation);go.transform.localScale=j.transform.lossyScale;}
  Debug.Log("CREA y conexión colocados con el registro relativo I/J. Comprueba desde arriba los umbrales y el terreno del Campus antes de guardar. FASPA no se ha modificado.");
 }
 [MenuItem("UPCH/CREA editable R1/Desempaquetar seleccionado para editar")]
 static void Unpack(){var go=Selection.activeGameObject;if(!go)return;var root=PrefabUtility.GetOutermostPrefabInstanceRoot(go);if(!root){Debug.Log("El objeto ya permite edición directa.");return;}PrefabUtility.UnpackPrefabInstance(root,PrefabUnpackMode.Completely,InteractionMode.UserAction);}
 [MenuItem("UPCH/CREA editable R1/Revisar referencias del seleccionado")]
 static void Revisar(){var go=Selection.activeGameObject;if(!go)return;int errors=0;foreach(var f in go.GetComponentsInChildren<MeshFilter>(true))if(!f.sharedMesh){Debug.LogError("Malla ausente: "+f.name,f);errors++;}foreach(var r in go.GetComponentsInChildren<Renderer>(true))foreach(var m in r.sharedMaterials)if(!m||!m.shader||m.shader.name=="Hidden/InternalErrorShader"){Debug.LogError("Material o shader sin resolver: "+r.name,r);errors++;}Debug.Log("CREA: "+errors+" referencias ausentes. Esta revisión no valida el recorrido ni la compatibilidad del controlador XR.",go);}
}}
