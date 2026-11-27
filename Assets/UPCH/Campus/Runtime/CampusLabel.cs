using UnityEngine;

namespace UPCH.Campus
{
    public sealed class CampusLabel : MonoBehaviour
    {
        public float visibleDistance = 100f;
        private Renderer labelRenderer;
        private void Awake() { labelRenderer = GetComponent<Renderer>(); }
        private void LateUpdate()
        {
            var camera = Camera.main;
            if (camera == null) return;
            Vector3 direction = transform.position - camera.transform.position;
            if (labelRenderer != null) labelRenderer.enabled = direction.sqrMagnitude < visibleDistance * visibleDistance;
            direction.y = 0f;
            if (direction.sqrMagnitude > .001f) transform.rotation = Quaternion.LookRotation(direction);
        }
    }
}
