using UnityEngine;

namespace UPCH.Veterinaria.Editor
{
    // Asset-only record: no runtime component is added to the campus terrain.
    public sealed class VeterinariaTerrenoEstado : ScriptableObject
    {
        public Mesh source;
        public Mesh result;
        public string targetGlobalId;
    }
}
