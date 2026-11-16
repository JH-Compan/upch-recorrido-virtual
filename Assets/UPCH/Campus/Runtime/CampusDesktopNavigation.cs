using System;
using UnityEngine;
using UnityEngine.InputSystem;
using UPCH.Tour;

namespace UPCH.Campus
{
    [Serializable] public class CampusDestination
    {
        public string title;
        public Vector3 position;
    }
    public sealed class CampusDesktopNavigation : MonoBehaviour
    {
        public TourDesktopController walker;
        public CampusDestination[] destinations;
        [Min(.1f)] public float walkingSpeed = 1.4f;
        [Min(.1f)] public float inspectionSpeed = 2.8f;
        private bool menu;
        private Vector2 scroll;
        private void Update()
        {
            var keys = Keyboard.current;
            if (keys == null || walker == null) return;
            if (keys.mKey.wasPressedThisFrame) SetMenu(!menu);
            if (menu && keys.escapeKey.wasPressedThisFrame) SetMenu(false);
            walker.speed = keys.leftShiftKey.isPressed ? inspectionSpeed : walkingSpeed;
        }
        private void SetMenu(bool value)
        {
            menu = value;
            walker.enabled = !menu;
            if (menu)
            {
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
            }
        }
        private void MoveTo(Vector3 position)
        {
            var capsule = walker.GetComponent<CharacterController>();
            capsule.enabled = false;
            walker.transform.position = position;
            capsule.enabled = true;
            SetMenu(false);
        }
        private void OnGUI()
        {
            if (GUI.Button(new Rect(12, 100, 260, 32), "M - Destinos del campus / Shift - rapido")) SetMenu(!menu);
            if (!menu) return;
            GUILayout.BeginArea(new Rect(12, 140, Mathf.Min(470, Screen.width - 24), Mathf.Max(180, Screen.height - 170)), GUI.skin.box);
            GUILayout.Label("CAMPUS UPCH - BASE EXTERIOR");
            GUILayout.Label("Elige un pabellon. Luego haz clic en Game para mirar.");
            scroll = GUILayout.BeginScrollView(scroll);
            if (destinations != null)
                foreach (var item in destinations)
                    if (GUILayout.Button(item.title, GUILayout.Height(35))) MoveTo(item.position);
            GUILayout.EndScrollView();
            if (GUILayout.Button("Cerrar")) SetMenu(false);
            GUILayout.EndArea();
        }
    }
}
