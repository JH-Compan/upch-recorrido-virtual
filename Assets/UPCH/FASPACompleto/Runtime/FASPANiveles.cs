using UnityEngine;
namespace UPCH.FASPACompleto {
// Optional: add to Edificio_FASPA to hide levels for inspection.
public sealed class FASPANiveles:MonoBehaviour {
 [Range(0,3)] public int nivelVisible=0;
 [ContextMenu("Aplicar nivel visible (0 = todos)")]
 public void Aplicar(){
  foreach(Transform t in GetComponentsInChildren<Transform>(true)){
   if(t.name=="Nivel_01")t.gameObject.SetActive(nivelVisible==0 || nivelVisible==1);
   if(t.name=="Nivel_02")t.gameObject.SetActive(nivelVisible==0 || nivelVisible==2);
   if(t.name=="Nivel_03")t.gameObject.SetActive(nivelVisible==0 || nivelVisible==3);
  }
 }
}
}
