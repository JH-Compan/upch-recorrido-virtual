using UnityEngine;

namespace UPCH.Tour
{
    // Desktop is the default in the Editor. Android builds use the template's XR rig.
    public sealed class TourPlayerMode : MonoBehaviour
    {
        public GameObject desktopPlayer;
        public GameObject xrPlayer;
        public bool useHeadsetInEditor;
        private void Awake()
        {
#if UNITY_EDITOR
            bool xr = useHeadsetInEditor;
#elif UNITY_ANDROID
            bool xr = true;
#else
            bool xr = false;
#endif
            desktopPlayer.SetActive(!xr);
            xrPlayer.SetActive(xr);
        }
    }
}
