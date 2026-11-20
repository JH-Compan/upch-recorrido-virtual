using System;
using System.Linq;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace UPCH.Enfermeria.Editor
{
    // Coordinates digitised from the right-hand D block of sheets A-02..A-06.
    // Raster tracing is approximate; retain source coordinates to permit survey corrections.
    public static class ReconstruirEnfermeria
    {
        const string Path = "Assets/UPCH/Campus/Generated/Buildings/D.prefab";
        const float H = 3.9f;
        static Material wall, metal, glass, floor;
        static Transform root;
        sealed class Door { public Transform parent; public float center,y,width,height; public BoxCollider leaf; }
        static readonly System.Collections.Generic.List<Door> doors=new System.Collections.Generic.List<Door>();
        static float X(float p) => (p-750f)*26.08f/787f-13.04f;
        static float Z(float p) => 9.86f-(p-143f)*19.72f/596f;
        static Transform Group(Transform p,string n) { var g=new GameObject(n); g.transform.SetParent(p,false); return g.transform; }
        static void Box(Transform p,string n,Vector3 c,Vector3 s,Material m,bool collider=true)
        {
            if(s.x<=0 || s.y<=0 || s.z<=0) throw new Exception("Invalid dimensions: "+n);
            var g=GameObject.CreatePrimitive(PrimitiveType.Cube); g.name=n; g.transform.SetParent(p,false);
            g.transform.localPosition=c; g.transform.localScale=s; g.GetComponent<Renderer>().sharedMaterial=m;
            if(m==glass) { g.GetComponent<Renderer>().shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off; g.GetComponent<Renderer>().receiveShadows=false; }
            if(!collider) UnityEngine.Object.DestroyImmediate(g.GetComponent<Collider>());
        }
        static void Rect(Transform p,string n,float x0,float z0,float x1,float z1,float y,float height,Material m)
        { Box(p,n,new Vector3((X(x0)+X(x1))/2,y+height/2,(Z(z0)+Z(z1))/2),new Vector3(Mathf.Abs(X(x1)-X(x0)),height,Mathf.Abs(Z(z1)-Z(z0))),m); }
        static float SideWallZ(float x) => Mathf.Lerp(704f,639f,Mathf.InverseLerp(877f,1400f,x));
        static void SidePassageSlab(Transform p,float y)
        {
            var g=new GameObject("Losa_pasillo_lateral_recortada_en_diagonal");g.transform.SetParent(p,false);
            var mesh=new Mesh {name="Losa_pasillo_diagonal"};
            float x0=X(877),x1=X(1400),t=.24f,bottom=y-t;
            var outer0=new Vector3(x0,y,Z(739));var outer1=new Vector3(x1,y,Z(674));
            var inner1=new Vector3(x1,y,Z(639));var inner0=new Vector3(x0,y,Z(704));
            mesh.vertices=new[] {outer0,outer1,inner1,inner0,
                new Vector3(outer0.x,bottom,outer0.z),new Vector3(outer1.x,bottom,outer1.z),
                new Vector3(inner1.x,bottom,inner1.z),new Vector3(inner0.x,bottom,inner0.z)};
            mesh.triangles=new[] {0,1,2,0,2,3, 4,6,5,4,7,6,
                0,4,5,0,5,1, 1,5,6,1,6,2, 2,6,7,2,7,3, 3,7,4,3,4,0};
            mesh.RecalculateNormals();mesh.RecalculateBounds();
            g.AddComponent<MeshFilter>().sharedMesh=mesh;g.AddComponent<MeshRenderer>().sharedMaterial=floor;g.AddComponent<MeshCollider>().sharedMesh=mesh;
        }
        // Wall with a real opening; door fraction measured along the segment. No hidden wall behind doors.
        static void Wall(Transform p,string n,float x0,float z0,float x1,float z1,float y,float door=-1,float width=1.0f,float height=H-.25f,Material mat=null)
        {
            var a=new Vector3(X(x0),0,Z(z0)); var b=new Vector3(X(x1),0,Z(z1)); var delta=b-a; float length=delta.magnitude;
            var g=Group(p,n); g.localPosition=a; g.localRotation=Quaternion.LookRotation(Vector3.Cross(delta.normalized,Vector3.up));
            Action<float,float,float,float,string> part=(start,len,bottom,h,suffix)=> {if(len>.001f)Box(g,n+suffix,new Vector3(start+len/2,y+bottom+h/2,0),new Vector3(len,h,.14f),mat??wall);};
            if(door<0) part(0,length,0,height,"");
            else {
                float center=Mathf.Clamp(door*length,width/2+.08f,length-width/2-.08f);
                part(0,center-width/2,0,height,"_izquierda"); part(center+width/2,length-center-width/2,0,height,"_derecha");
                float openingHeight=Mathf.Min(2.25f,height-.15f);
                part(center-width/2,width,openingHeight,height-openingHeight,"_dintel");
                // Choose the handing after ALL adjacent partitions exist.
                doors.Add(new Door {parent=g,center=center,y=y,width=width,height=openingHeight});
            }
        }
        [MenuItem("Tools/UPCH/Reconstruir pabellon D - Enfermeria")]
        public static void Run()
        {
            wall=AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Arte/Edificios/D/Materiales/PanelBlanco.mat");
            metal=AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Arte/Edificios/D/Materiales/Aluminio.mat");
            glass=AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Arte/Edificios/D/Materiales/VidrioAzulado.mat");
            floor=AssetDatabase.LoadAssetAtPath<Material>("Assets/UPCH/Arte/Edificios/D/Materiales/PiedraGris.mat");
            if(!wall||!metal||!glass||!floor)throw new Exception("Missing materials");
            const string clearPath="Assets/UPCH/Arte/Edificios/D/Materiales/VidrioFachadaClara.mat";
            var clear=AssetDatabase.LoadAssetAtPath<Material>(clearPath);
            if(clear==null) { clear=new Material(glass);clear.name="VidrioFachadaClara";AssetDatabase.CreateAsset(clear,clearPath); }
            clear.SetColor("_BaseColor",new Color(.61f,.73f,.69f,.27f));
            clear.SetFloat("_Smoothness",.85f);EditorUtility.SetDirty(clear);glass=clear;
            var prefab=PrefabUtility.LoadPrefabContents(Path);
            try {
                root=prefab.transform;
                doors.Clear();
                while(root.childCount>0)UnityEngine.Object.DestroyImmediate(root.GetChild(0).gameObject);
                foreach(var c in prefab.GetComponents<Component>())if(!(c is Transform))UnityEngine.Object.DestroyImmediate(c);
                for(int i=0;i<6;i++) BuildFloor(i);
                Roof(); Access(); PlaceDoors(); Validate(prefab);
                PrefabUtility.SaveAsPrefabAsset(prefab,Path); AssetDatabase.SaveAssets();
                Debug.Log("ENFERMERIA_RECONSTRUIDA: seis plantas, dos escaleras y dos huecos de ascensor; validacion OK");
            } finally { PrefabUtility.UnloadPrefabContents(prefab); }
        }
        static bool Void(float x,float z,int level)
        {
            if(level>0&&x>1407&&x<1530&&z>584&&z<674)return true; // lift wells above ground level
            if(level>0&&x>1407&&x<1530&&z>177&&z<343)return true;
            if(level>0&&x>770&&x<870&&z>548&&z<730)return true;
            if(level>1&&x>1400&&z>676)return true; // void south of lifts, A-03 onwards
            if(level==0&&x<1010&&z<400)return true; // vehicular ramp west of the occupied building
            return false;
        }
        static void Slab(Transform p,int i,float y)
        {
            float[] xs={750,770,870,1010,1040,1400,1407,1530,1537};
            float[] zs={143,177,343,400,416,426,436,446,456,466,476,486,496,506,510,548,584,674,676,730,739};
            for(int a=0;a<xs.Length-1;a++)for(int b=0;b<zs.Length-1;b++)
                if(!Void((xs[a]+xs[a+1])/2,(zs[b]+zs[b+1])/2,i)&&!(i<2&&xs[a]>=870&&xs[a+1]<=1400&&zs[b]>=674)) {
                    // End inside the 14 cm wall thickness, not short of its inner
                    // face. Follow the rear wall setback instead of exposing slab.
                    float midZ=(zs[b]+zs[b+1])/2;
                    float west=Mathf.Lerp(750,761,Mathf.InverseLerp(416,510,midZ));
                    float left=xs[a]==750?west+1:xs[a];
                    float right=xs[a+1]==1537?xs[a+1]-1:xs[a+1];
                    float north=zs[b]==143?zs[b]+1:zs[b];
                    float south=zs[b+1]==739?zs[b+1]-1:zs[b+1];
                    Rect(p,"Losa_"+a+"_"+b,left,north,right,south,y-.24f,.24f,floor);
                }
            if(i<2)SidePassageSlab(p,y);
        }
        static void BuildFloor(int i)
        {
            float y=.7f+i*H; var p=Group(root,"Planta_"+(i+1)+"_NPT_"+y.ToString("F2",System.Globalization.CultureInfo.InvariantCulture));
            Slab(Group(p,"Losas_con_huecos"),i,y);
            var envelope=Group(p,"Fachadas");
            // North and south window ribbons, split into sill, glass and lintel.
            foreach(float z in new[]{143f,739f}) {
                if(i<2&&z==739f) {
                    // The south edge is a glazed passage on levels 1 and 2.
                    // Its inner opaque wall follows the diagonal shown on A-01/A-02.
                    Wall(envelope,"Muro_cortina_pasillo_lateral_"+i,877,739,1400,674,y,-1,1,H,glass);
                    Wall(envelope,"Pared_fondo_pasillo_diagonal_"+i,877,SideWallZ(877),1400,SideWallZ(1400),y,-1,1,H,wall);
                    continue;
                }
                float start=i==0&&z==143?1040:877;
                Wall(envelope,"Antepecho_"+z,start,z,1400,z,y,-1,1,i<2?.25f:1.15f);
                Wall(envelope,"Ventana_"+z,start,z,1400,z,y+(i<2?.25f:1.15f),-1,1,i<2?2.8f:1.45f,glass);
                Wall(envelope,"Dintel_"+z,start,z,1400,z,y+(i<2?3.05f:2.6f),-1,1,i<2?.85f:1.3f);
            }
            Wall(envelope,"Oeste_servicios",750,143,750,416,y,-1,1,H);
            Wall(envelope,"Oeste_escalera",761,510,761,739,y,-1,1,H);
            Wall(envelope,"Antepecho_hall_puente",750,416,761,510,y,-1,1,.9f);
            Wall(envelope,"Ventana_hall_puente",750,416,761,510,y+.9f,-1,1,1.9f,glass);
            Wall(envelope,"Dintel_hall_puente",750,416,761,510,y+2.8f,-1,1,1.1f);
            Rect(envelope,"Marco_hall_puente",754,462,757,464,y+.9f,1.9f,metal);
            Wall(envelope,"Testero_norte",750,143,877,143,y,-1,1,H);
            Wall(envelope,"Testero_sur",761,739,877,739,y,-1,1,H);
            if(i==0) Wall(envelope,"Retorno_acristalado_planta_baja",1400,739,1537,739,y,-1,1,H,glass);
            else Wall(envelope,"Cierre_sur_ascensores",1400,739,1537,739,y,-1,1,H);
            // Close the missing end of the ribbon facade at its junction with the east curtain.
            if(i>1) Wall(envelope,"Retorno_vacio_sur",1400,674,1400,739,y,-1,1,H);
            // East stair enclosure is hollow, with a separate curtain wall over the hall.
            Wall(envelope,"Nucleo_norte",1400,143,1537,143,y,-1,1,H);
            // The stair-side bay is opaque in the surveyed front photographs.
            Wall(envelope,"Nucleo_este",1537,143,1537,400,y,-1,1,H);
            Rect(envelope,"Revestimiento_nucleo_este",1539,143,1541,400,y,H,wall);
            for(int bay=0;bay<8;bay++) {
                float a=350+bay*389f/8,b=350+(bay+1)*389f/8;
                bool entrance=i==0&&b>440&&a<550;
                float clearStart=Mathf.Max(a,400f);
                if(entrance) {
                    if(clearStart<440)Rect(envelope,"Fijo_ingreso_norte",1539,clearStart+1,1541,440,y+.08f,3.5f,glass);
                    if(b>550)Rect(envelope,"Fijo_ingreso_sur",1539,550,1541,b-1,y+.08f,3.5f,glass);
                    Rect(envelope,"Sobrepuerta_"+bay,1539,Mathf.Max(clearStart,440),1541,Mathf.Min(b,550),y+2.85f,.65f,glass);
                }
                if(!entrance&&b>clearStart)Rect(envelope,"Vidrio_este_"+bay,1539,clearStart+1,1541,b-1,y+.08f,3.5f,glass);
                if(!entrance&&b>clearStart)Rect(envelope,"Montante_este_"+bay,1542,clearStart,1543,clearStart+1,y,H,metal);
                if(!entrance&&b>clearStart&&!(i==0&&clearStart>=674))Rect(envelope,"Pilar_tras_vidrio_"+bay,1528,clearStart,1537,clearStart+8,y,H,wall);
                if(b>clearStart)Rect(envelope,"Viga_entre_pilares_"+bay,1528,entrance?clearStart:clearStart+8,1537,b,y+3.2f,.46f,wall);
                // Stainless fixing points on the outer glass screen, as seen in the photographs.
                if(b>clearStart)for(int fixing=0;fixing<2;fixing++)
                    Rect(envelope,"Fijacion_"+bay+"_"+fixing,1543,clearStart-1,1545,clearStart+2,y+.25f+fixing*2.9f,.045f,metal);
            }
            Rect(envelope,"Travesano_este",1542,400,1544,739,y+3.55f,.08f,metal);
            // Cladding joints stand clear of the panel surface (no coplanar overlays).
            for(int j=1;j<6;j++)Rect(envelope,"Junta_panel_"+j,1541.1f,143+j*42.8f,1541.35f,143.45f+j*42.8f,y,H,metal);
            for(int j=1;j<3;j++)Rect(envelope,"Junta_horizontal_panel_"+j,1541.1f,143,1541.35f,400,y+j*1.3f,.012f,metal);
            if(i>0) {
                for(int j=0;j<3;j++)Rect(envelope,"Baranda_hall_"+j,1520,400,1522,580,y+.4f+j*.32f,.035f,metal);
                for(int j=0;j<5;j++)Rect(envelope,"Poste_baranda_hall_"+j,1520,400+j*44,1522,402+j*44,y,1.1f,metal);
            }
            // The slab ends inside the continuous facade; projecting bands created
            // the grey stacked blocks visible from the sides and rear.
            var services=Group(p,"Servicios_y_circulacion");
            Stairs(services,i,y,1407,177,1530,343,"Escalera_3");
            Stairs(services,i,y,770,548,870,730,"Escalera_2");
            Wall(services,"Caja_escalera_3_oeste",1400,143,1400,400,y);
            Wall(services,"Caja_escalera_3_sur",1400,395,1537,395,y,.5f,1.5f);
            Wall(services,"Caja_escalera_2_este",877,510,877,739,y);
            Wall(services,"Caja_escalera_2_norte",761,510,877,510,y,.5f,1.4f);
            Wall(services,"Cierre_aula_escalera",877,493,877,510,y);
            Wall(services,"Cierre_aula_ascensor",1400,493,1400,674,y);
            Wall(services,"Retorno_ascensor_izquierdo",1400,584,1407,584,y);
            Wall(services,"Retorno_ascensor_derecho",1530,584,1537,584,y);
            Lifts(services,i,y);
            if(i==0) GroundRamp(services,y);
            if(i>0) Toilets(services,y);
            Layout(Group(p,"Distribucion_segun_A0"+(i+1)),i,y);
        }
        static void Lifts(Transform p,int level,float y)
        {
            var g=Group(p,"Dos_ascensores");
            Wall(g,"Pozo_oeste",1407,584,1407,674,y);
            Wall(g,"Pozo_este",1530,584,1530,674,y);
            Wall(g,"Pozo_fondo",1407,674,1530,674,y);
            Wall(g,"Separacion_pozos",1468.5f,584,1468.5f,674,y);
            for(int i=0;i<2;i++) {
                float a=1407+i*61.5f,b=a+61.5f;
                // Front wall split around closed landing doors; shafts remain empty above the cabin.
                float c=(a+b)/2,half=17;
                Wall(g,"Jamba_ascensor_"+i,a,584,c-half,584,y);
                Wall(g,"Jamba_derecha_"+i,c+half,584,b,584,y);
                Wall(g,"Cabecero_ascensor_"+i,c-half,584,c+half,584,y+2.25f,-1,1,1.41f);
                Rect(g,"Puerta_ascensor_"+i+"_A",c-half,583,c-.4f,584,y,2.24f,metal);
                Rect(g,"Puerta_ascensor_"+i+"_B",c+.4f,583,c+half,584,y,2.24f,metal);
                Rect(g,"Botonera_"+i,c+half+2,580,c+half+5,582,y+1.05f,.25f,metal);
                if(level==0) {
                    Rect(g,"Cabina_piso_"+i,a+3,587,b-3,671,y,.08f,metal);
                    Rect(g,"Cabina_fondo_"+i,a+3,668,b-3,671,y,2.35f,metal);
                    Rect(g,"Cabina_techo_"+i,a+3,587,b-3,671,y+2.35f,.08f,metal);
                }
            }
        }
        static void Stairs(Transform p,int level,float y,float x0,float z0,float x1,float z1,string name)
        {
            var g=Group(p,name); float mid=(x0+x1)/2, landing=38,run=(z1-z0-landing)/12;
            // Stair 3 opens to the SOUTH hall. Its landing must be at the door end,
            // not stranded at the north wall. Stair 2 opens to the north bridge hall.
            bool southDoor=name=="Escalera_3";
            Func<float,float> at=t=>southDoor?z1-t:z0+t;
            float runEnd=12*run;
            for(int n=0;n<12;n++) {
                Rect(g,"Ida_"+n,x0,at(n*run),mid-3,at((n+1)*run),y+n*H/24,H/24,floor);
                Rect(g,"Vuelta_"+n,mid+3,at(runEnd-(n+1)*run),x1,at(runEnd-n*run),y+H/2+n*H/24,H/24,floor);
            }
            Rect(g,"Descanso_intermedio",x0,at(runEnd),x1,at(runEnd+landing),y+H/2-.18f,.18f,floor);
            // Storey landings are part of the slab outside the stair opening, across
            // the full width of both flights; no extra coplanar landing is overlaid.
            // Continuous pitched handrails and balusters inside the central stair opening.
            for(int f=0;f<2;f++) {
                float xx=f==0?mid-3:mid+3;
                for(int n=0;n<12;n++) {
                    float zz=f==0?at(n*run):at(runEnd-n*run);
                    Rect(g,"Pasamanos_poste_"+f+"_"+n,xx-1,zz,xx+1,zz+1,y+(f==0?n*H/24:H/2+n*H/24),1f,metal);
                }
                var a=new Vector3(X(xx),y+1+(f==0?0:H),Z(at(0)));
                var b=new Vector3(X(xx),y+1+H/2,Z(at(runEnd)));
                var rail=Group(g,"Pasamanos_"+f);rail.localPosition=(a+b)/2;rail.localRotation=Quaternion.FromToRotation(Vector3.up,(b-a).normalized);
                Box(rail,"Barra",Vector3.zero,new Vector3(.045f,(b-a).magnitude,.045f),metal);
            }
        }
        static void Toilets(Transform p,float y)
        {
            var g=Group(p,"Servicios_higienicos");
            Wall(g,"Limite_este",877,143,877,416,y);
            Wall(g,"Limite_sur",750,416,877,416,y,.75f);
            Wall(g,"Division_H_M",750,300,840,300,y);
            Wall(g,"Division_accesible",750,358,877,358,y,.8f);
            Wall(g,"Pasillo_SS_HH",837,175,837,358,y,.75f);
            for(int n=0;n<4;n++) {
                Wall(g,"Cabina_"+n,750,190+n*28,800,190+n*28,y,-1,1,2.1f);
                Wall(g,"Puerta_cabina_"+n,800,190+n*28,800,218+n*28,y,.5f,.65f,2.1f);
                Rect(g,"Sanitario_"+n,763,195+n*28,776,211+n*28,y,.42f,wall);
            }
            Rect(g,"Lavamanos",805,150,867,167,y+.75f,.12f,wall);
        }
        static void Layout(Transform p,int i,float y)
        {
            Action<string,float,float,float,float,float> w=(n,a,b,c,d,door)=>Wall(p,n,a,b,c,d,y,door);
            if(i==1||i==2) {
                w("Aulas_norte_oeste",877,400,1138,400,.08f);
                w("Aulas_norte_este",1138,400,1400,400,.94f);
                w("Aulas_sur_oeste",877,493,1138,493,.08f);
                w("Aulas_sur_este",1138,493,1400,493,.94f);
                w("Division_aulas_norte",1138,143,1138,400,-1);
                w("Division_aulas_sur",1138,493,1138,739,-1);
            } else if(i==0) {
                w("Aula_101_sur",1040,400,1400,400,.92f);
                w("Aula_101_oeste",1040,143,1040,400,-1);
                w("Oficinas_frente",877,493,1400,493,.9f);
                foreach(float x in new[]{970f,1080f,1215f})w("Oficina_"+x,x,493,x,SideWallZ(x),.12f);
                w("Jefatura",877,580,970,580,.7f);
            } else if(i==3) {
                foreach(float z in new[]{416f,480f}) {
                    w("Pasillo_oeste_"+z,877,z,990,z,.5f);
                    w("Pasillo_centro_"+z,1090,z,1190,z,.5f);
                    w("Pasillo_este_"+z,1280,z,1400,z,.7f);
                }
                foreach(float x in new[]{1048f,1138f,1228f}) {
                    w("Simulacion_norte_"+x,x,143,x,332,-1);
                    w("Simulacion_sur_"+x,x,550,x,739,-1);
                }
                w("UCI_adultos",877,332,1048,332,.85f);
                w("Debriefing_1",1048,332,1138,332,.3f);
                w("Debriefing_2",1138,332,1228,332,.7f);
                w("Centro_quirurgico",1228,332,1400,332,.7f);
                w("Emergencia",877,550,1048,550,.8f);
                w("Debriefing_3",1048,550,1138,550,.3f);
                w("Debriefing_4",1138,550,1228,550,.7f);
                w("UCI_neonatal",1228,550,1400,550,.4f);
                foreach(float x in new[]{990f,1090f,1190f,1280f}) {
                    w("Apoyo_norte_"+x,x,332,x,416,.5f);
                    w("Apoyo_sur_"+x,x,480,x,550,.5f);
                }
            } else if(i==4) {
                w("Consejeria_pasillo",877,416,1218,416,.15f);
                w("Departamento_pasillo",1218,416,1400,416,.5f);
                w("Administracion_pasillo",877,493,1400,493,.5f);
                w("Departamento",1218,143,1218,416,-1);
                w("Oficinas_norte",1218,270,1400,270,.7f);
                w("Oficinas_division",1310,143,1310,270,-1);
                w("Reuniones",935,263,1055,263,.5f);
                w("Direccion",935,143,935,416,.5f);
                w("Reuniones_este",1055,143,1055,263,-1);
                foreach(float x in new[]{1008f,1138f,1270f})w("Despacho_"+x,x,606,x,739,-1);
                float[] a={877,1008,1138,1270,1400};for(int n=0;n<4;n++)w("Despacho_puerta_"+n,a[n],606,a[n+1],606,.8f);
            } else {
                float[] a={877,984,1138,1226,1311,1400};
                for(int n=0;n<5;n++) {w("Oficina_norte_"+n,a[n],257,a[n+1],257,.8f);if(n>0)w("Division_norte_"+n,a[n],143,a[n],257,-1);}
                w("Comedor",877,400,935,400,.5f);w("Comedor_este",935,257,935,400,-1);
                float[] b={877,1048,1138,1298,1400};
                for(int n=0;n<4;n++){w("Despacho_sur_"+n,b[n],580,b[n+1],580,.8f);if(n>0)w("Division_sur_"+n,b[n],580,b[n],739,-1);}
            }
        }
        static void GroundRamp(Transform p,float y)
        {
            var g=Group(p,"Rampa_estacionamiento_A01");
            // A-01: the rear area is a ramp, separated from the public corridor.
            Wall(g,"Cierre_rampa_pasillo",750,400,1010,400,y,-1,1,H);
            Wall(g,"Cierre_rampa_servicios",1010,143,1010,400,y,-1,1,H);
            Wall(g,"Cierre_fondo_planta_baja",877,143,1040,143,y,-1,1,H);
            float length=X(1010)-X(750),rise=length*.145f;
            // Retaining walls continue below ground to meet the inclined slab;
            // otherwise the ramp would expose a gap beneath the storey walls.
            float baseY=y-rise-.22f,retainingHeight=rise+.22f;
            Wall(g,"Contencion_norte",750,143,1010,143,baseY,-1,1,retainingHeight);
            Wall(g,"Contencion_sur",750,400,1010,400,baseY,-1,1,retainingHeight);
            Wall(g,"Contencion_oeste",750,143,750,400,baseY,-1,1,retainingHeight);
            Wall(g,"Contencion_este",1010,143,1010,400,baseY,-1,1,retainingHeight);
            var ramp=Group(g,"Losa_rampa_14_5_por_ciento");
            ramp.localPosition=new Vector3((X(750)+X(1010))/2,y-rise/2-.11f,(Z(143)+Z(400))/2);
            ramp.localRotation=Quaternion.Euler(0,0,-Mathf.Atan(.145f)*Mathf.Rad2Deg);
            Box(ramp,"Hormigon",Vector3.zero,new Vector3(Mathf.Sqrt(length*length+rise*rise),.22f,Mathf.Abs(Z(400)-Z(143))),floor);
        }
        static bool Intersects(BoxCollider a,BoxCollider b)
        {
            return Physics.ComputePenetration(a,a.transform.position,a.transform.rotation,
                b,b.transform.position,b.transform.rotation,out var direction,out var distance)&&distance>.003f;
        }
        static void PlaceDoors()
        {
            var obstacles=root.GetComponentsInChildren<BoxCollider>().ToList();
            foreach(var d in doors) {
                Box(d.parent,"Hoja",Vector3.zero,Vector3.one,metal);
                d.leaf=d.parent.GetChild(d.parent.childCount-1).GetComponent<BoxCollider>();
                var t=d.leaf.transform; bool fitted=false;
                // WC leaves open INTO the cubicle, not across the common passage.
                float preferred=d.parent.name.StartsWith("Puerta_cabina_")?-1:1;
                foreach(bool folded in new[]{false,true}) {
                    foreach(float side in new[]{preferred,-preferred}) {
                        foreach(float hingeSide in new[]{-1f,1f}) {
                            float hinge=d.center+hingeSide*d.width/2,leafWidth=d.width-.08f;
                            t.localScale=folded?new Vector3(leafWidth,d.height-.04f,.045f):new Vector3(.045f,d.height-.04f,leafWidth);
                            t.localPosition=folded?
                                new Vector3(hinge+hingeSide*leafWidth/2,d.y+d.height/2,side*.13f):
                                new Vector3(hinge-hingeSide*.04f,d.y+d.height/2,side*(leafWidth/2+.10f));
                            if(obstacles.Any(c=>Intersects(d.leaf,c)))continue;
                            fitted=true;break;
                        }
                        if(fitted)break;
                    }
                    if(fitted)break;
                }
                if(!fitted)throw new Exception("No hay espacio para abrir la puerta: "+d.parent.parent.name+"/"+d.parent.name);
                obstacles.Add(d.leaf);
            }
            // Check the finished model, including leaves created after each preceding leaf.
            foreach(var d in doors) {
                foreach(var c in obstacles)if(c!=d.leaf&&Intersects(d.leaf,c))
                    throw new Exception("Puerta atraviesa geometria: "+d.parent.name+" / "+c.name);
                var origin=d.parent.TransformPoint(new Vector3(d.center,d.y+1.1f,-.2f));
                var ray=new Ray(origin,d.parent.forward);
                foreach(var c in obstacles)if(c.Raycast(ray,out var hit,.4f))
                    throw new Exception("Vano bloqueado: "+d.parent.name+" / "+c.name);
            }
            Debug.Log("D_PUERTAS_OK: "+doors.Count+" hojas sin intersecciones y vanos despejados.");
        }
        static void Roof()
        {
            var p=Group(root,"Azotea");float y=.7f+6*H;
            // A closed roof deck, independent of the stair and lift openings below.
            Rect(p,"Cubierta_continua",750,143,1537,739,y-.24f,.24f,floor);
            Wall(p,"Parapeto_norte",750,143,1537,143,y,-1,1,.9f);
            Wall(p,"Parapeto_sur",761,739,1400,739,y,-1,1,.9f);
            Wall(p,"Parapeto_este",1537,143,1537,739,y,-1,1,.9f);
            Wall(p,"Parapeto_oeste",750,143,750,739,y,-1,1,.9f);
        }
        static void Access()
        {
            var p=Group(root,"Acceso_este");
            float center=Z(540);
            Box(p,"Plataforma_ingreso",new Vector3(13.79f,.58f,center),new Vector3(1.5f,.24f,12.6f),floor);
            for(int n=0;n<7;n++) {
                float xx=14.54f+(6-n)*.36f+.18f,top=(n+1)*.1f;
                Box(p,"Escalon_"+n,new Vector3(xx,top/2,center),new Vector3(.36f,top,12.6f),floor);
                Box(p,"Banda_antideslizante_"+n,new Vector3(xx+.13f,top+.003f,center),new Vector3(.04f,.006f,12.4f),metal,false);
            }
            // Double recessed door, with jambs and lintel, clear of the curtain wall.
            foreach(float z in new[]{440f,550f})
                Rect(p,"Jamba_ingreso_"+z,1538,z-1,1542,z+1,.7f,2.85f,metal);
            Rect(p,"Dintel_ingreso",1538,439,1542,551,3.55f,.10f,metal);
            // Two glass leaves opened outward onto the entrance landing.
            foreach(float z in new[]{442f,548f}) {
                Rect(p,"Hoja_vidrio_ingreso_"+z,1542,z,1589,z+1,.72f,2.72f,glass);
                Rect(p,"Marco_hoja_ingreso_"+z,1588,z-.3f,1590,z+1.3f,.72f,2.72f,metal);
                Rect(p,"Tirador_ingreso_"+z,1582,z-1,1583,z+2,1.55f,.5f,metal);
            }
            var rail=Group(p,"Pasamanos_acceso");
            foreach(float zz in new[]{center-6.35f,center+6.35f}) {
                for(int n=0;n<4;n++)Box(rail,"Poste_"+zz+"_"+n,new Vector3(14.5f+n*.75f,1.2f-n*.21f,zz),new Vector3(.05f,1.0f,.05f),metal);
                var a=new Vector3(14.5f,1.7f,zz);var b=new Vector3(16.75f,1.07f,zz);
                var bar=Group(rail,"Barra_"+zz);bar.localPosition=(a+b)/2;bar.localRotation=Quaternion.FromToRotation(Vector3.up,(b-a).normalized);
                Box(bar,"Tubo",Vector3.zero,new Vector3(.055f,(b-a).magnitude,.055f),metal);
            }
        }
        static void Validate(GameObject p)
        {
            if(p.transform.childCount!=8)throw new Exception("Missing floors");
            foreach(Transform level in p.transform) {
                var seen=new System.Collections.Generic.HashSet<string>();
                foreach(var c in level.GetComponentsInChildren<BoxCollider>()) {
                    string key=c.transform.position.ToString("F3")+c.transform.lossyScale.ToString("F3")+c.transform.rotation.ToString("F3");
                    if(!seen.Add(key))throw new Exception("Duplicate solid: "+c.name);
                }
            }
            var solids=p.GetComponentsInChildren<BoxCollider>();
            Action<float,float,float,Vector3,string> closed=(px,pz,y,normal,label)=> {
                var middle=p.transform.TransformPoint(new Vector3(X(px),y,Z(pz)));
                var ray=new Ray(middle-normal*.3f,normal);
                if(!solids.Any(c=>c.Raycast(ray,out var hit,.6f)))throw new Exception("Falta cerramiento: "+label);
            };
            Action<float,float,float,string> support=(px,pz,top,label)=> {
                var origin=p.transform.TransformPoint(new Vector3(X(px),top+.35f,Z(pz)));
                var ray=new Ray(origin,Vector3.down);bool found=false;
                foreach(var c in solids)if(c.Raycast(ray,out var hit,.7f)&&Mathf.Abs(hit.distance-.35f)<.025f)found=true;
                if(!found)throw new Exception("Suelo discontinuo: "+label);
            };
            for(int i=0;i<6;i++) {
                float y=.7f+i*H;
                closed(1400,374,y+1.1f,Vector3.right,"puerta lateral indebida de escalera nivel "+i);
                if(i>0)closed(877,389,y+1.1f,Vector3.right,"puerta lateral indebida de bano nivel "+i);
                // Both lanes of each storey landing, including the path to the door.
                foreach(float x in new[]{1425f,1468f,1510f})foreach(float z in new[]{346f,370f,392f})support(x,z,y,"hall principal nivel "+i);
                foreach(float x in new[]{785f,820f,855f})foreach(float z in new[]{515f,530f,545f})support(x,z,y,"hall secundario nivel "+i);
                for(int n=0;n<12;n++) {
                    float t=(n+.5f)*128f/12;
                    support(1435,343-t,y+(n+1)*H/24,"ida principal "+i+"/"+n);
                    support(1500,215+t,y+H/2+(n+1)*H/24,"vuelta principal "+i+"/"+n);
                }
            }
            closed(950,143,1.8f,Vector3.forward,"fondo exterior planta baja");
            closed(900,400,1.8f,Vector3.forward,"separacion pasillo y rampa");
            support(1025,300,.7f,"franja de servicios planta baja");
            support(900,425,.7f,"pasillo posterior planta baja");
            foreach(float x in new[]{1420f,1460f,1510f})
                support(x,705,.7f,"suelo detras de ascensores planta baja");
            foreach(float z in new[]{365f,385f})
                closed(1537,z,1.8f,Vector3.right,"fachada opaca junto a escalera planta baja");
            Debug.Log("D_CIERRES_OK: aberturas indebidas selladas y separacion de rampa verificada.");
            Debug.Log("D_VERIFICADO: 108 muestras de descansos y 144 peldaños principales con suelo continuo en seis niveles.");
        }
    }
}
