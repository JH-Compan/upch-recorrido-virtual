using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace UPCH.Arquitectura.FASPAR3 {
public static class FASPAR3Integracion {
 const string Ruta="Assets/UPCH/FASPAReconstruido/Prefabs/Edificio_FASPA_R3.prefab";
 static GameObject Instanciar(){
  GameObject asset=AssetDatabase.LoadAssetAtPath<GameObject>(Ruta);
  if(asset==null){EditorUtility.DisplayDialog("FASPA R3","No se pudo cargar el prefab. Revisa Console y copia FASPAReconstruido dentro de Assets/UPCH.","Aceptar");return null;}
  GameObject go=(GameObject)PrefabUtility.InstantiatePrefab(asset);Undo.RegisterCreatedObjectUndo(go,"Insertar FASPA R3");Selection.activeGameObject=go;EditorSceneManager.MarkSceneDirty(go.scene);return go;
 }
 [MenuItem("UPCH/FASPA R3/Insertar prefab independiente")]
 public static void Insertar(){Instanciar();}
 [MenuItem("UPCH/FASPA R3/Comparar en lugar del FASPA anterior seleccionado")]
 public static void Comparar(){
  GameObject anterior=Selection.activeGameObject;
  if(anterior==null || anterior.name!="Edificio_FASPA"){
   EditorUtility.DisplayDialog("Selecciona el anterior","Selecciona exactamente la raíz Edificio_FASPA del paquete anterior. Esta opción compensa sus ejes FBX; para otra raíz, inserta el prefab independiente y colócalo manualmente.","Aceptar");return;}
  Vector3 pos=anterior.transform.position;Quaternion rot=anterior.transform.rotation*Quaternion.Euler(0,180,0);Vector3 scale=anterior.transform.lossyScale;
  GameObject nuevo=Instanciar();if(nuevo==null)return;nuevo.transform.SetPositionAndRotation(pos,rot);nuevo.transform.localScale=scale;
  Undo.RecordObject(anterior,"Ocultar FASPA anterior");anterior.SetActive(false);Selection.activeGameObject=nuevo;
  EditorUtility.DisplayDialog("Copia para comparar","El anterior se conserva desactivado. Revisa desde arriba el contorno y la posición antes de guardar. La compensación supone que conservaste los ejes internos del paquete anterior.","Aceptar");
 }
 [MenuItem("UPCH/FASPA R3/Desempaquetar seleccionado para editar")]
 public static void Desempaquetar(){
  GameObject go=Selection.activeGameObject;if(go==null)return;
  GameObject root=PrefabUtility.GetOutermostPrefabInstanceRoot(go);
  if(root==null || !root.name.StartsWith("Edificio_FASPA_R3")){EditorUtility.DisplayDialog("FASPA R3","Selecciona una instancia de Edificio_FASPA_R3. Si ya está desempaquetada, puedes editar sus hijos directamente.","Aceptar");return;}
  PrefabUtility.UnpackPrefabInstance(root,PrefabUnpackMode.Completely,InteractionMode.UserAction);Selection.activeGameObject=root;
 }
 [MenuItem("UPCH/FASPA R3/Revisar referencias y colliders del seleccionado")]
 public static void Revisar(){
  GameObject go=Selection.activeGameObject;if(go==null)return;int total=0,missing=0,materials=0;long tris=0;
  foreach(MeshFilter f in go.GetComponentsInChildren<MeshFilter>(true)){
   total++;if(f.sharedMesh==null){missing++;continue;}
   for(int i=0;i<f.sharedMesh.subMeshCount;i++)tris+=(long)f.sharedMesh.GetIndexCount(i)/3;
   MeshRenderer mr=f.GetComponent<MeshRenderer>();if(mr!=null)foreach(Material m in mr.sharedMaterials)if(m==null || m.shader==null || !m.shader.isSupported)materials++;
  }
  EditorUtility.DisplayDialog("Control FASPA R3","Mallas: "+total+"\nTriángulos: "+tris+"\nMallas faltantes: "+missing+"\nMateriales/shaders no disponibles: "+materials+"\nColliders: "+go.GetComponentsInChildren<Collider>(true).Length+"\nNo comprueba transitabilidad ni cálculo estructural.","Aceptar");
 }
}
}
