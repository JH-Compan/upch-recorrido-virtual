using UnityEngine;

namespace UPCH.Veterinaria
{
    [DisallowMultipleComponent]
    public sealed class VeterinariaDoor : MonoBehaviour
    {
        public Vector3 hinge;
        public float openDegrees = 90f;
        public float approachDistance = 2.5f;
        public float closeDistance = 3.2f;
        public float angularSpeed = 180f;
        float angle, lastNearby;
        static Camera[] cameras = new Camera[0];
        static float lastCameraScan = -1f;

        void Awake() { lastNearby = Time.time; }
        void Update()
        {
            float now = Time.time;
            if (lastCameraScan < 0f || now < lastCameraScan || now - lastCameraScan > .25f)
            { cameras = Camera.allCameras; lastCameraScan = now; }
            Vector3 worldHinge = transform.parent.TransformPoint(hinge);
            float nearest = float.PositiveInfinity;
            foreach (var camera in cameras)
            {
                if (!camera || !camera.isActiveAndEnabled || camera.cameraType != CameraType.Game) continue;
                Vector3 localCamera = transform.parent.InverseTransformPoint(camera.transform.position);
                // Cameras on another storey must not actuate this door.
                if (localCamera.y < hinge.y + .2f || localCamera.y > hinge.y + 2.5f) continue;
                nearest = Mathf.Min(nearest, Vector3.Distance(camera.transform.position, worldHinge));
            }
            if (nearest < closeDistance) lastNearby = now;
            bool opening = nearest < approachDistance || (Mathf.Abs(angle) > .01f && now - lastNearby < 2f);
            float next = Mathf.MoveTowards(angle, opening ? openDegrees : 0f, angularSpeed * Time.deltaTime);
            if (Mathf.Abs(next - angle) < .0001f) return;
            angle = next;
            Quaternion rotation = Quaternion.Euler(0f, angle, 0f);
            transform.localRotation = rotation;
            transform.localPosition = hinge - rotation * hinge;
        }
    }
}
