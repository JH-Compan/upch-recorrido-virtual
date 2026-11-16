using System;
using UnityEngine;

namespace UPCH.Tour
{
    [Serializable] public class TourBox
    {
        public string name;
        public Vector3 center;
        public Vector3 size;
        public string material;
        public bool walkable;
    }
    [Serializable] public class TourStop
    {
        public string title;
        public string description;
        public Vector3 position;
    }
    [Serializable] public class TourLayout
    {
        public string status;
        public string source;
        public string assumptions;
        public Vector3 spawn;
        public float spawnYaw;
        public TourBox[] boxes;
        public TourStop[] stops;
    }
}
