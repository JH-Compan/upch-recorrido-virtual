using UnityEngine;
using UnityEditor;
namespace UPCH.FASPACompleto {
public static class FASPARevisionSectorial {
 [MenuItem("UPCH/FASPA completo/Revisar piezas del objeto seleccionado")]
 public static void Revisar(){
  GameObject go=Selection.activeGameObject;if(go==null)return;
  int meshes=0,missing=0;long triangles=0;
  foreach(MeshFilter mf in go.GetComponentsInChildren<MeshFilter>(true)){
   if(mf.sharedMesh==null){missing++;continue;}meshes++;
   for(int i=0;i<mf.sharedMesh.subMeshCount;i++)triangles+=(long)mf.sharedMesh.GetIndexCount(i)/3;
  }
  EditorUtility.DisplayDialog("Revisión de "+go.name,"Mallas: "+meshes+"\nTriángulos: "+triangles+"\nMeshFilters sin malla: "+missing+"\nEste conteo no comprueba intersecciones ni seguridad arquitectónica.","Aceptar");
 }
}
}
