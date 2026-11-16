using UnityEngine;
using UnityEngine.XR.Interaction.Toolkit;
using UnityEngine.XR.Interaction.Toolkit.Interactables;

namespace UPCH.Tour
{
    [RequireComponent(typeof(XRSimpleInteractable))]
    public sealed class TourInfoPoint : MonoBehaviour
    {
        public string title;
        [TextArea] public string description;
        public GameObject panel;
        private XRSimpleInteractable interactable;

        private void Awake()
        {
            interactable = GetComponent<XRSimpleInteractable>();
            if (panel != null) panel.SetActive(false);
        }
        private void OnEnable()
        {
            if (interactable == null) interactable = GetComponent<XRSimpleInteractable>();
            interactable.selectEntered.AddListener(OnSelect);
        }
        private void OnDisable()
        {
            if (interactable != null) interactable.selectEntered.RemoveListener(OnSelect);
        }
        private void OnSelect(SelectEnterEventArgs args) { Toggle(); }
        public void Toggle()
        {
            if (panel != null) panel.SetActive(!panel.activeSelf);
        }
        private void LateUpdate()
        {
            var camera = Camera.main;
            if (panel == null || !panel.activeSelf || camera == null) return;
            Vector3 direction = panel.transform.position - camera.transform.position;
            direction.y = 0f;
            if (direction.sqrMagnitude > .001f)
                panel.transform.rotation = Quaternion.LookRotation(direction);
        }
    }
}
