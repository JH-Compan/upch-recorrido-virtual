using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace UPCH.Veterinaria.Editor
{
    // Execute inside Unity; these checks do not substitute a player walkthrough.
    public static class VeterinariaTerrenoPruebas
    {
        [MenuItem("Tools/UPCH/Veterinaria/Probar recorte (EditMode)")]
        public static void Run()
        {
            Mesh source = Plate();
            try
            {
                Check(source, Rect(1, 1, 2, 2), 15f, 3f, "hueco interior");
                Check(source, Rect(-1, 1, 1, 3), 14f, 2.8f, "hueco en borde");
                Check(source, Rect(-1, 1, 0, 3), 16f, 3.2f, "borde coincidente exterior");
                Check(source, Rect(0, 1, 1, 3), 14f, 2.8f, "borde coincidente interior");
                Check(source, Rect(6, 6, 7, 7), 16f, 3.2f, "cortador exterior");
                var concave = Rect(1, 1, 2, 3);
                concave.AddRange(Rect(2, 1, 3, 2));
                Check(source, concave, 13f, 2.6f, "hueco en L");
                bool rejected = false;
                try
                {
                    var empty = VeterinariaTerreno.BuildCutMesh(source, Rect(-1, -1, 5, 5));
                    UnityEngine.Object.DestroyImmediate(empty);
                }
                catch (InvalidOperationException) { rejected = true; }
                if (!rejected) throw new Exception("No se rechazó un recorte que elimina todo el terreno.");
                Debug.Log("Veterinaria: 7 casos geométricos de recorte conformes (área, volumen orientado y rechazo de vaciado total). Falta revisar integración y recorrido en Campus.");
            }
            finally { UnityEngine.Object.DestroyImmediate(source); }
        }
        static List<Vector2[]> Rect(float x0, float z0, float x1, float z1) => new List<Vector2[]>
        {
            new [] {new Vector2(x0,z0),new Vector2(x1,z0),new Vector2(x1,z1)},
            new [] {new Vector2(x0,z0),new Vector2(x1,z1),new Vector2(x0,z1)}
        };
        static Mesh Plate()
        {
            var mesh = new Mesh();
            mesh.vertices = new[] {
                new Vector3(0,0,0),new Vector3(4,0,0),new Vector3(4,0,4),new Vector3(0,0,4),
                new Vector3(0,-.2f,0),new Vector3(4,-.2f,0),new Vector3(4,-.2f,4),new Vector3(0,-.2f,4)
            };
            mesh.triangles = new[] {0,2,1,0,3,2,4,5,6,4,6,7,0,1,5,0,5,4,1,2,6,1,6,5,2,3,7,2,7,6,3,0,4,3,4,7};
            mesh.RecalculateNormals(); mesh.RecalculateBounds();
            return mesh;
        }
        static void Check(Mesh source, List<Vector2[]> cutters, float expectedArea, float expectedVolume, string label)
        {
            var mesh = VeterinariaTerreno.BuildCutMesh(source, cutters);
            try
            {
                var v = mesh.vertices; var t = mesh.triangles;
                double area = 0, volume = 0;
                for (int k = 0; k < t.Length; k += 3)
                {
                    Vector3 a = v[t[k]], b = v[t[k + 1]], c = v[t[k + 2]];
                    var n = Vector3.Cross(b - a, c - a);
                    if (n.sqrMagnitude < 1e-12f) throw new Exception("Triángulo degenerado en " + label);
                    if (Mathf.Abs(a.y) < 1e-5f && Mathf.Abs(b.y) < 1e-5f && Mathf.Abs(c.y) < 1e-5f)
                    { if (n.y <= 0) throw new Exception("Normal superior invertida: " + label); area += n.magnitude * .5; }
                    volume += Vector3.Dot(a, Vector3.Cross(b, c)) / 6.0;
                }
                if (Math.Abs(area - expectedArea) > .001 || Math.Abs(volume - expectedVolume) > .001)
                    throw new Exception($"{label}: área {area:F5}/{expectedArea}; volumen {volume:F5}/{expectedVolume}");
            }
            finally { UnityEngine.Object.DestroyImmediate(mesh); }
        }
    }
}
