using UnityEngine;
using UnityEngine.InputSystem;
using UPCH.Tour;

namespace UPCH.ScaleTools
{
    public sealed class ScaleWalkBenchmark : MonoBehaviour
    {
        public TourDesktopController walker;
        private float started;
        private float elapsed;
        private bool running;
        private bool finished;
        private void Update()
        {
            if (walker == null) return;
            var keyboard = Keyboard.current;
            walker.speed = keyboard != null && keyboard.leftShiftKey.isPressed ? 2.8f : 1.4f;
            float distance = walker.transform.position.z;
            if (distance < .05f) { running = false; finished = false; elapsed = 0f; }
            if (!running && !finished && distance > .05f) { started = Time.time; running = true; }
            if (running)
            {
                elapsed = Time.time - started;
                if (distance >= 100f) { running = false; finished = true; }
            }
        }
        private void OnGUI()
        {
            if (walker == null) return;
            float distance = Mathf.Clamp(walker.transform.position.z, 0, 100);
            GUI.Box(new Rect(12, Screen.height - 112, Mathf.Min(680, Screen.width-24), 100),
                "REFERENCIA FISICA: 100 unidades = 100 m en este proyecto\n" +
                "Avance: " + distance.ToString("F1") + " m | Tiempo: " + elapsed.ToString("F1") + " s\n" +
                "Paso: 1.4 m/s (~71 s por 100 m) | Shift: 2.8 m/s (~36 s)\n" +
                (finished ? "Recorrido completado. R para repetir." : "W para avanzar. Las pausas tambien cuentan en el tiempo."));
        }
    }
}
