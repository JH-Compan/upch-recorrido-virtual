using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

namespace UPCH.LIDCompleto
{
    [RequireComponent(typeof(CharacterController))]
    public sealed class LIDDemoController : MonoBehaviour
    {
        public Transform cameraPivot;
        public float walkingSpeed = 1.4f;
        public float fastSpeed = 2.8f;
        public float mouseSensitivity = 0.12f;
        readonly string[] levelNames = { "Sotano", "Piso_01", "Piso_02", "Piso_03", "Piso_04", "Azotea" };
        readonly float[] heights = { 0, 3.2f, 6.4f, 9.6f, 12.8f, 16.8f };
        CharacterController capsule;
        Transform building;
        float pitch, vertical;
        bool cutaway;
        int floor;

        void Awake()
        {
            capsule = GetComponent<CharacterController>();
            if (cameraPivot == null && Camera.main != null) cameraPivot = Camera.main.transform;
            var model = GameObject.Find("Edificio_LID");
            if (model != null) building = model.transform;
        }
        void OnDisable() { Cursor.lockState = CursorLockMode.None; Cursor.visible = true; }
        void Update()
        {
            Vector2 move = Vector2.zero, look = Vector2.zero;
            bool fast = false, unlock = false, capture = false, changeCut = false, outside = false;
            int target = -1;
#if ENABLE_INPUT_SYSTEM
            var k = Keyboard.current; var m = Mouse.current;
            if (k != null)
            {
                move.x = (k.dKey.isPressed ? 1 : 0) - (k.aKey.isPressed ? 1 : 0);
                move.y = (k.wKey.isPressed ? 1 : 0) - (k.sKey.isPressed ? 1 : 0);
                fast = k.leftShiftKey.isPressed; unlock = k.escapeKey.wasPressedThisFrame;
                changeCut = k.f7Key.wasPressedThisFrame; outside = k.f8Key.wasPressedThisFrame;
                if (k.f1Key.wasPressedThisFrame) target = 0;
                if (k.f2Key.wasPressedThisFrame) target = 1;
                if (k.f3Key.wasPressedThisFrame) target = 2;
                if (k.f4Key.wasPressedThisFrame) target = 3;
                if (k.f5Key.wasPressedThisFrame) target = 4;
                if (k.f6Key.wasPressedThisFrame) target = 5;
            }
            if (m != null) { capture = m.leftButton.wasPressedThisFrame; look = m.delta.ReadValue(); }
#elif ENABLE_LEGACY_INPUT_MANAGER
            move = new Vector2(Input.GetAxisRaw("Horizontal"), Input.GetAxisRaw("Vertical"));
            look = new Vector2(Input.GetAxis("Mouse X") * 15, Input.GetAxis("Mouse Y") * 15);
            fast = Input.GetKey(KeyCode.LeftShift); unlock = Input.GetKeyDown(KeyCode.Escape);
            capture = Input.GetMouseButtonDown(0); changeCut = Input.GetKeyDown(KeyCode.F7); outside = Input.GetKeyDown(KeyCode.F8);
            for (int i = 0; i < 6; i++) if (Input.GetKeyDown((KeyCode)((int)KeyCode.F1 + i))) target = i;
#endif
            if (unlock) { Cursor.lockState = CursorLockMode.None; Cursor.visible = true; }
            if (capture) { Cursor.lockState = CursorLockMode.Locked; Cursor.visible = false; }
            if (Cursor.lockState == CursorLockMode.Locked)
            {
                transform.Rotate(0, look.x * mouseSensitivity, 0);
                pitch = Mathf.Clamp(pitch - look.y * mouseSensitivity, -82, 82);
                if (cameraPivot != null) cameraPivot.localRotation = Quaternion.Euler(pitch, 0, 0);
                Vector3 direction = transform.right * move.x + transform.forward * move.y;
                direction = Vector3.ClampMagnitude(direction, 1) * (fast ? fastSpeed : walkingSpeed);
                if (capsule.isGrounded && vertical < 0) vertical = -2;
                vertical += Physics.gravity.y * Time.deltaTime;
                capsule.Move((direction + Vector3.up * vertical) * Time.deltaTime);
            }
            if (target >= 0) GoToFloor(target);
            if (changeCut)
            {
                if (!cutaway)
                {
                    float y = building != null ? building.InverseTransformPoint(transform.position).y : transform.position.y;
                    floor = heights.Length - 1;
                    for (int i = 0; i < heights.Length; i++) if (heights[i] >= y - .3f) { floor = i; break; }
                }
                cutaway = !cutaway; ApplyCut();
            }
            if (outside)
            {
                cutaway = false; ApplyCut();
                Teleport(new Vector3(1.253f, 1.26f, -23.195f));
                transform.rotation = Quaternion.identity; pitch = 0;
            }
            if (transform.position.y < -8) Teleport(new Vector3(1.253f, 1.26f, -23.195f));
        }
        void Teleport(Vector3 localPosition)
        {
            capsule.enabled = false;
            transform.position = building != null ? building.TransformPoint(localPosition) : localPosition;
            capsule.enabled = true; vertical = 0;
        }
        void GoToFloor(int index)
        {
            floor = index;
            ApplyCut(); Teleport(new Vector3(0, heights[index] + .08f, 0));
        }
        void ApplyCut()
        {
            if (building == null) return;
            for (int i = 0; i < levelNames.Length; i++)
            {
                var level = building.Find(levelNames[i]);
                if (level != null) level.gameObject.SetActive(!cutaway || i <= floor);
            }
        }
        void OnGUI()
        {
            GUI.Box(new Rect(12, Screen.height - 72, Mathf.Min(790, Screen.width - 24), 58),
                "LID UPCH | Clic: mirar · WASD: caminar · Shift: rápido · Esc: liberar cursor\n" +
                "F1–F6: elegir planta · F7: vista interior por niveles · F8: volver al ingreso");
        }
    }
}
