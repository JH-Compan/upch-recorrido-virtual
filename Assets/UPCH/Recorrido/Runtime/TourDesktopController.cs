using UnityEngine;
using UnityEngine.InputSystem;

namespace UPCH.Tour
{
    [RequireComponent(typeof(CharacterController))]
    public sealed class TourDesktopController : MonoBehaviour
    {
        public Camera viewCamera;
        public Vector3 spawn;
        public float spawnYaw;
        public float speed = 2.2f;
        public float lookSensitivity = .10f;
        private CharacterController controller;
        private float pitch;
        private float verticalSpeed;
        private TourInfoPoint target;
        private bool captured;

        private void Awake() { controller = GetComponent<CharacterController>(); }
        private void Capture(bool value)
        {
            captured = value;
            Cursor.lockState = value ? CursorLockMode.Locked : CursorLockMode.None;
            Cursor.visible = !value;
        }
        private void OnDisable() { Capture(false); }
        private void Update()
        {
            var keyboard = Keyboard.current;
            var mouse = Mouse.current;
            if (keyboard == null || mouse == null || viewCamera == null) return;
            bool release = keyboard.escapeKey.wasPressedThisFrame;
            if (release) Capture(false);
            if (!release && !captured && mouse.leftButton.wasPressedThisFrame) Capture(true);
            if (captured)
            {
                Vector2 delta = mouse.delta.ReadValue() * lookSensitivity;
                transform.Rotate(0f, delta.x, 0f);
                pitch = Mathf.Clamp(pitch - delta.y, -75f, 75f);
                viewCamera.transform.localRotation = Quaternion.Euler(pitch, 0f, 0f);
            }
            Vector2 move = Vector2.zero;
            if (captured)
            {
                if (keyboard.wKey.isPressed || keyboard.upArrowKey.isPressed) move.y += 1;
                if (keyboard.sKey.isPressed || keyboard.downArrowKey.isPressed) move.y -= 1;
                if (keyboard.dKey.isPressed || keyboard.rightArrowKey.isPressed) move.x += 1;
                if (keyboard.aKey.isPressed || keyboard.leftArrowKey.isPressed) move.x -= 1;
            }
            move = Vector2.ClampMagnitude(move, 1f);
            if (controller.isGrounded && verticalSpeed < 0f) verticalSpeed = -2f;
            verticalSpeed += Physics.gravity.y * Time.deltaTime;
            Vector3 velocity = (transform.right * move.x + transform.forward * move.y) * speed;
            velocity.y = verticalSpeed;
            controller.Move(velocity * Time.deltaTime);
            target = null;
            if (Physics.Raycast(viewCamera.ViewportPointToRay(new Vector3(.5f, .5f, 0f)),
                out RaycastHit hit, 3f)) target = hit.collider.GetComponentInParent<TourInfoPoint>();
            if (captured && keyboard.eKey.wasPressedThisFrame && target != null) target.Toggle();
            if (transform.position.y < -5f || keyboard.rKey.wasPressedThisFrame) ResetPosition();
        }
        private void ResetPosition()
        {
            controller.enabled = false;
            transform.SetPositionAndRotation(spawn, Quaternion.Euler(0f, spawnYaw, 0f));
            controller.enabled = true;
            pitch = 0f;
            verticalSpeed = 0f;
            viewCamera.transform.localRotation = Quaternion.identity;
        }
        private void OnGUI()
        {
            GUI.Box(new Rect(12, 12, 510, 78),
                "UPCH | Maqueta de prueba\nClic: mirar | WASD: caminar | E: informacion\nEsc: liberar raton | R: volver al inicio");
            GUI.Label(new Rect(Screen.width / 2f - 8, Screen.height / 2f - 12, 24, 24), "+");
            if (target != null)
                GUI.Box(new Rect(Screen.width / 2f - 200, Screen.height - 65, 400, 38),
                    "E - " + target.title);
        }
    }
}
