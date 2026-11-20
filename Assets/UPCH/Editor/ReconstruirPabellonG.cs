using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace UPCH.Campus.Editor
{
    // Dimensions and room programme: 06. AULAS AUDITORIO 2025, A-01..A-04.
    // Model coordinates follow the drawing: classroom wing east, auditorium west.
    public static class ReconstruirPabellonG
    {
        const string PathG = "Assets/UPCH/Campus/Generated/Buildings/G.prefab";
        const string Art = "Assets/UPCH/Arte/Edificios/G/";
        const float ClassroomWidth = 19.56f, Depth = 20.76f, H = 3.55f;
        static Material concrete, brick, glass, dark, metal, wood, floor, leaf;

        [MenuItem("Tools/UPCH/Construir G - aulas y auditorio")]
        public static void Run()
        {
            concrete = Material("G_Concreto", new Color(.76f,.73f,.66f), "Concreto_G.png");
            brick = Material("G_Ladrillo", Color.white, "Ladrillo_G.png");
            glass = Material("G_Vidrio",new Color(.25f,.36f,.39f));
            dark = Material("G_Vidrio_oscuro",new Color(.075f,.11f,.12f));
            metal = Material("G_Acero",new Color(.48f,.50f,.49f));
            wood = Material("G_Carpinteria",new Color(.37f,.17f,.075f));
            floor = Material("G_Pavimento",new Color(.53f,.53f,.49f));
            leaf = Material("G_Setos",new Color(.14f,.25f,.09f));
            GameObject asset = PrefabUtility.LoadPrefabContents(PathG);
            try
            {
                for(int i=asset.transform.childCount-1;i>=0;i--) UnityEngine.Object.DestroyImmediate(asset.transform.GetChild(i).gameObject);
                foreach(var c in asset.GetComponents<Component>()) if(!(c is Transform)) UnityEngine.Object.DestroyImmediate(c);
                Transform root = Group(asset.transform,"G_Aulas_Auditorio_A01_A04");
                // Original mass: rectangular classrooms at positive campus Z,
                // polygonal auditorium at negative Z. Reflect the paper's downward
                // page axis in the primitive helpers, then rotate into survey axes.
                // The south approach still faces +X, toward Parque central.
                root.localRotation = Quaternion.Euler(0,-90,0);
                root.localPosition = new Vector3(0,.90f,3.5f);
                BuildClassrooms(root);
                BuildCirculation(root);
                BuildAuditorium(root);
                BuildExterior(root);
                PrefabUtility.SaveAsPrefabAsset(asset,PathG);
                AssetDatabase.SaveAssets();
                Debug.Log("G_SAVED_A01_A04: basement -2.88, classrooms 0/3.55/7.10, polygonal auditorium, independent stairs/lifts, entrance facing campus centre (+X).");
                var inst=GameObject.Find("G - Aulas y auditorio");
                if(inst && SceneView.lastActiveSceneView)
                {
                    SceneView.lastActiveSceneView.in2DMode=false;
                    SceneView.lastActiveSceneView.orthographic=false;
                    SceneView.lastActiveSceneView.LookAt(inst.transform.position+new Vector3(4,4,0),Quaternion.Euler(18,-90,0),37);
                }
            }
            finally { PrefabUtility.UnloadPrefabContents(asset); }
        }

        static Material Material(string name,Color color,string texture=null)
        {
            string path=Art+name+".mat";
            var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!m)
            {
                m=new Material(Shader.Find("Universal Render Pipeline/Lit")){name=name};
                m.SetColor("_BaseColor",color);
                m.SetFloat("_Smoothness",name.Contains("Vidrio")?.74f:.13f);
                if(texture!=null)
                {
                    m.SetTexture("_BaseMap",AssetDatabase.LoadAssetAtPath<Texture2D>(Art+texture));
                    m.SetTextureScale("_BaseMap",texture.Contains("Ladrillo")?new Vector2(4,2):new Vector2(2,2));
                }
                AssetDatabase.CreateAsset(m,path);
            }
            return m;
        }

        static void BuildClassrooms(Transform root)
        {
            float[] levels={-2.88f,0,H,2*H};
            for(int n=0;n<levels.Length;n++)
            {
                float y=levels[n], height=n==0?2.88f:H;
                Transform p=Group(root,n==0?"Sotano_A01":"Piso_"+n+"_NPT_"+y.ToString("F2"));
                // Three non-overlapping strips form the slab and leave the stair/lift core open.
                if(n==0) Box(p,"Losa_sotano",new Vector3(ClassroomWidth/2,y-.10f,0),new Vector3(ClassroomWidth,.20f,Depth),floor,true);
                else FloorWithCore(p,y);
                Facade(p,y,height,-Depth/2,n);
                Facade(p,y,height,Depth/2,n);
                EndElevation(p,y,height,n);
                if(n==0) BasementRooms(p,y);
                else ClassroomRooms(p,y,n);
            }
            Box(root,"Cubierta_aulas_cerrada",new Vector3(ClassroomWidth/2,3*H-.10f,0),new Vector3(ClassroomWidth,.20f,Depth),concrete,true);
            RoofRails(root,new Vector2(0,-Depth/2),new Vector2(ClassroomWidth,-Depth/2),3*H);
            RoofRails(root,new Vector2(0,Depth/2),new Vector2(ClassroomWidth,Depth/2),3*H);
            RoofRails(root,new Vector2(ClassroomWidth,-Depth/2),new Vector2(ClassroomWidth,Depth/2),3*H);
        }

        static void FloorWithCore(Transform p,float y)
        {
            const float x0=15.15f,z0=-1.78f,z1=1.78f;
            Box(p,"Losa_norte",new Vector3(ClassroomWidth/2,y-.10f,(-Depth/2-3.35f)/2),new Vector3(ClassroomWidth,.20f,Depth/2-3.35f),floor,true);
            Box(p,"Losa_norte_borde_ascensor",new Vector3(9.0f,y-.10f,(-3.35f+z0)/2),new Vector3(18.0f,.20f,z0+3.35f),floor,true);
            Box(p,"Losa_norte_borde_testero",new Vector3(19.505f,y-.10f,(-3.35f+z0)/2),new Vector3(.11f,.20f,z0+3.35f),floor,true);
            Box(p,"Losa_sur",new Vector3(ClassroomWidth/2,y-.10f,(Depth/2+z1)/2),new Vector3(ClassroomWidth,.20f,Depth/2-z1),floor,true);
            Box(p,"Losa_corredor",new Vector3(x0/2,y-.10f,0),new Vector3(x0,.20f,z1-z0),floor,true);
        }

        static void Facade(Transform p,float y,float height,float z,int level)
        {
            float bay=ClassroomWidth/4;
            for(int i=0;i<4;i++)
            {
                float x=bay*(i+.5f), width=bay-.25f;
                Band(p,"Antepecho_ladrillo",x,z,y,.76f,width,brick);
                Band(p,"Ventana_principal",x,z,y+.76f,.88f,width,glass);
                Band(p,"Franja_ladrillo",x,z,y+1.64f,height-2.45f,width,brick);
                Band(p,"Ventana_alta",x,z,y+height-.81f,.56f,width,glass);
                Band(p,"Dintel_concreto",x,z,y+height-.25f,.25f,width,concrete);
                foreach(float v in new[]{.76f,1.64f,height-.81f,height-.25f})
                    Box(p,"Marco_horizontal",new Vector3(x,y+v,z),new Vector3(width,.035f,.23f),metal,false);
                for(int j=1;j<5;j++)
                    Box(p,"Montante_ventanas",new Vector3(bay*i+.125f+width*j/5,y+1.20f,z),new Vector3(.035f,.88f,.24f),metal,false);
            }
            for(int i=0;i<=4;i++)
                Box(p,"Pilar_concreto_visto",new Vector3(i*bay,y+height/2,z),new Vector3(.25f,height,.44f),concrete,true);
        }

        static void Band(Transform p,string name,float x,float z,float y,float h,float width,Material m)
        { Box(p,name,new Vector3(x,y+h/2,z),new Vector3(width,h,.20f),m,m!=glass); }

        static void EndElevation(Transform p,float y,float height,int level)
        {
            float bay=Depth/6;
            for(int i=0;i<6;i++)
            {
                float z=-Depth/2+bay*(i+.5f);
                Box(p,"Testero_ladrillo_inferior",new Vector3(ClassroomWidth,y+.45f,z),new Vector3(.20f,.90f,bay-.20f),brick,true);
                Box(p,"Testero_ventana",new Vector3(ClassroomWidth,y+1.35f,z),new Vector3(.20f,.90f,bay-.20f),glass,false);
                Box(p,"Testero_ladrillo_superior",new Vector3(ClassroomWidth,y+(1.80f+height)/2,z),new Vector3(.20f,height-1.80f,bay-.20f),brick,true);
            }
            for(int i=0;i<=6;i++)
                Box(p,"Aleta_vertical_testero",new Vector3(ClassroomWidth,y+height/2,-Depth/2+bay*i),new Vector3(.55f,height,.20f),concrete,true);
        }

        static void ClassroomRooms(Transform p,float y,int level)
        {
            // A-02: 104/106 north, 103/105 south. A-03: three rooms on each side.
            // A-04: 302/304/306 north, 303/305/307 south, plus 301 in the hall return.
            float[] north=level==1?new[]{0f,8.86f,19.56f}:level==3?new[]{0f,4.9f,12.05f,19.56f}:new[]{0f,6.0f,12.0f,19.56f};
            float[] south=level==1?new[]{0f,9.9f,19.56f}:new[]{0f,4.89f,9.78f,19.56f};
            Rooms(p,y,level,north,-10.25f,-2.0f,true);
            Rooms(p,y,level,south,2.0f,10.25f,false);
            if(level<3) Stair(p,"Escalera_1_aulas",17.2f,0,y,H,1.08f,2.90f);
            else RoofRails(p,new Vector2(15.15f,-1.78f),new Vector2(19.40f,-1.78f),y);
            Lift(p,"Ascensor_aulas",18.72f,-2.65f,y,H);
            CeilingLights(p,y,0,19.56f,0);
        }

        static void Rooms(Transform p,float y,int level,float[] xs,float za,float zb,bool north)
        {
            float corridor=north?zb:za;
            for(int r=0;r<xs.Length-1;r++)
            {
                float a=xs[r],b=xs[r+1];
                Wall(p,"Tabique_corredor_puerta_aula",new Vector2(a,corridor),new Vector2(b,corridor),y,H,concrete,.18f,1.35f);
                if(r>0) Wall(p,"Division_aulas",new Vector2(a,za),new Vector2(a,zb),y,H,concrete);
                Transform room=Group(p,"Aula_G"+level+"_"+(north?"norte_":"sur_")+r);
                for(int row=0;row<5;row++)
                    for(int col=0;col<Mathf.FloorToInt((b-a-1.4f)/.80f);col++)
                        Seat(room,new Vector3(a+.75f+col*.80f,y,za+1.0f+row*1.23f),true);
                Box(room,"Mesa_docente",new Vector3(north&&r==xs.Length-2?b-2.7f:b-.80f,y+.76f,zb-.75f),new Vector3(1.2f,.07f,.65f),wood,true);
                Box(room,"Pizarra",new Vector3((a+b)/2,y+1.65f,north?za+.13f:zb-.13f),new Vector3(Mathf.Min(3,b-a-.5f),1.1f,.045f),concrete,false);
            }
        }

        static void BasementRooms(Transform p,float y)
        {
            float[] north={0,4.90f,16.10f,19.56f};
            for(int i=1;i<north.Length-1;i++) Wall(p,"Almacen_patrimonio",new Vector2(north[i],-10.25f),new Vector2(north[i],-2),y,2.88f,concrete);
            Wall(p,"Corredor_almacen",new Vector2(0,-2),new Vector2(19.56f,-2),y,2.88f,concrete,.63f,1.80f);
            float[] south={0,4.90f,16.35f,19.56f};
            for(int i=1;i<south.Length-1;i++) Wall(p,"Oficinas_sotano",new Vector2(south[i],2),new Vector2(south[i],10.25f),y,2.88f,concrete);
            Wall(p,"Acceso_coworking",new Vector2(0,2),new Vector2(19.56f,2),y,2.88f,concrete,.50f,1.80f);
            for(int i=0;i<7;i++)
                Box(p,"Estanteria_almacen",new Vector3(1.5f+i*2.15f,y+1.0f,-6.3f),new Vector3(.55f,2.0f,5.8f),metal,true);
            for(int i=0;i<5;i++)
                Box(p,"Mesa_coworking",new Vector3(6.6f+i*1.7f,y+.75f,5.5f),new Vector3(1.25f,.07f,.65f),wood,true);
            Stair(p,"Escalera_1_sotano",17.2f,0,y,2.88f,1.08f,2.90f);
            Lift(p,"Ascensor_sotano",18.72f,-2.65f,y,2.88f);
        }

        static void BuildCirculation(Transform root)
        {
            for(int l=0;l<4;l++)
            {
                float y=l==0?-2.88f:(l-1)*H,h=l==0?2.88f:H;
                Transform p=Group(root,"Nucleo_hall_nivel_"+l);
                // Continuous circulation around a single stair opening. The upper
                // landing at z=-6.43 joins this slab along its edge.
                Box(p,"Suelo_hall",new Vector3(-2.825f,y-.10f,(-2.07f+7.40f)/2),new Vector3(5.65f,.20f,9.47f),floor,true);
                Box(p,"Suelo_descanso_norte",new Vector3(-2.825f,y-.10f,(-8.975f-6.43f)/2),new Vector3(5.65f,.20f,2.545f),floor,true);
                Box(p,"Suelo_lateral_oeste_escalera",new Vector3(-5.54f,y-.10f,-4.25f),new Vector3(.22f,.20f,4.36f),floor,true);
                Box(p,"Suelo_lateral_este_escalera",new Vector3(-.385f,y-.10f,-4.25f),new Vector3(.77f,.20f,4.36f),floor,true);
                Box(p,"Suelo_servicios",new Vector3(-2.825f,y-.10f,-11.8f),new Vector3(5.65f,.20f,5.65f),floor,true);
                Wall(p,"Fondo_servicios",new Vector2(-5.65f,-14.625f),new Vector2(0,-14.625f),y,h,concrete);
                Wall(p,"Lateral_servicios",new Vector2(0,-14.625f),new Vector2(0,-4.8f),y,h,concrete);
                Wall(p,"Cierre_nucleo",new Vector2(-5.65f,-14.625f),new Vector2(-5.65f,-4.8f),y,h,concrete);
                if(l<3) Stair(p,"Escalera_2_hall",-3.1f,-4.25f,y,l==0?2.88f:H,2.20f,3.8f);
                Toilets(p,y,h);
                if(l>0)
                {
                    // Tall glazing of the principal hall above the recessed entry.
                    if(l==1)
                    {
                        Wall(p,"Frente_entrada_principal_G",new Vector2(-5.65f,7.40f),new Vector2(0,7.40f),y,h,concrete,.50f,2.0f);
                        Box(p,"Marquesina_entrada",new Vector3(-2.825f,y+3.15f,8.05f),new Vector3(5.65f,.25f,1.30f),concrete,true);
                    }
                    else Box(p,"Vidrio_hall_doble_altura",new Vector3(-2.825f,y+h/2,7.4f),new Vector3(5.2f,h-.22f,.12f),dark,false);
                    foreach(float x in new[]{-5.65f,0}) Box(p,"Pilar_hall",new Vector3(x,y+h/2,7.4f),new Vector3(.30f,h,.45f),concrete,true);
                }
            }
            Box(root,"Cubierta_hall",new Vector3(-2.825f,3*H-.10f,3.3f),new Vector3(5.65f,.20f,8.20f),concrete,true);
            Box(root,"Techo_servicios_NTT_7.10",new Vector3(-2.825f,7.0f,-11.8f),new Vector3(5.65f,.20f,5.65f),concrete,true);
            RoofRails(root,new Vector2(-5.65f,7.4f),new Vector2(0,7.4f),3*H);
        }

        static void Toilets(Transform p,float y,float h)
        {
            Wall(p,"Division_SSHH",new Vector2(-5.5f,-11.8f),new Vector2(-.15f,-11.8f),y,h,concrete);
            Wall(p,"Acceso_SSHH",new Vector2(-5.5f,-8.98f),new Vector2(-.15f,-8.98f),y,h,concrete,.8f,.95f);
            for(int i=0;i<4;i++)
            {
                float z=-13.9f+i*.95f;
                Box(p,"Cabina_SSHH",new Vector3(-4.0f,y+1.05f,z),new Vector3(1.25f,2.10f,.065f),concrete,true);
                Box(p,"Inodoro",new Vector3(-4.8f,y+.24f,z+.35f),new Vector3(.42f,.48f,.63f),concrete,true);
                Box(p,"Lavatorio",new Vector3(-.6f,y+.85f,z+.35f),new Vector3(.42f,.16f,.45f),concrete,true);
            }
        }

        static readonly Vector2[] Theatre={new Vector2(-26.9f,-4.1f),new Vector2(-23.3f,-5.5f),new Vector2(-23.3f,-8.0f),new Vector2(-10.9f,-12.7f),new Vector2(-7.9f,-5.9f),new Vector2(-7.9f,5.9f),new Vector2(-10.9f,12.7f),new Vector2(-23.3f,8),new Vector2(-23.3f,5.5f),new Vector2(-26.9f,4.1f)};
        static void BuildAuditorium(Transform root)
        {
            Transform p=Group(root,"Auditorio_y_anfiteatros_poligonales");
            Polygon(p,"Suelo_anfiteatros",Theatre,-1.62f,-1.44f,floor);
            Polygon(p,"Entrepiso_auditorio",Theatre,3.35f,3.55f,floor);
            Polygon(p,"Cubierta_auditorio",Theatre,10.45f,10.65f,concrete);
            for(int i=0;i<Theatre.Length;i++)
            {
                Vector2 a=Theatre[i],b=Theatre[(i+1)%Theatre.Length];
                bool entry=i==4;
                Wall(p,"Cerramiento_concreto_auditorio",a,b,-1.44f,entry?4.99f:12.09f,concrete,entry?.5f:-1,2.0f);
                if(entry) Wall(p,"Acceso_auditorio_segundo",a,b,3.55f,7.10f,concrete,.5f,2.0f);
                if(!entry) ConcreteJoints(p,a,b,-1.44f,12.09f);
                RoofRails(p,a,b,10.65f);
            }
            Wall(p,"Separacion_anfiteatros_1_2",new Vector2(-23.3f,0),new Vector2(-7.9f,0),-1.44f,4.99f,concrete);
            for(int half=-1;half<=1;half+=2)
            {
                for(int row=0;row<7;row++)
                {
                    float x=-19.8f+row*1.55f,top=-1.44f+row*.12f;
                    if(row>0)Box(p,"Grada_anfiteatro",new Vector3(x,top-.10f,half*3.4f),new Vector3(1.55f,.20f,5.5f),floor,true);
                    for(int col=0;col<6;col++) Seat(p,new Vector3(x,top,half*3.4f-2.15f+col*.85f),false,90);
                }
            }
            Box(p,"Estrado_anfiteatros",new Vector3(-22.6f,-1.26f,0),new Vector3(2.0f,.36f,7.2f),wood,true);
            Box(p,"Estrado_auditorio_NPT_4.27",new Vector3(-24.3f,3.91f,0),new Vector3(4.5f,.72f,7.9f),wood,true);
            for(int row=0;row<9;row++)
                for(int col=0;col<12;col++) Seat(p,new Vector3(-20.9f+row*1.25f,3.55f,-4.9f+col*.88f),false,90);
            Box(p,"Pantalla_auditorio",new Vector3(-26.72f,6.55f,0),new Vector3(.06f,3.2f,5.6f),concrete,false);
            // Short enclosed passages attach auditorium entrances to the public hall.
            foreach(float y in new[]{0f,H})
            {
                Box(p,"Paso_auditorio_hall",new Vector3(-6.775f,y-.10f,0),new Vector3(2.25f,.20f,4.0f),floor,true);
                foreach(int side in new[]{-1,1}) Wall(p,"Muro_paso",new Vector2(-7.9f,side*2),new Vector2(-5.65f,side*2),y,H,concrete);
            }
        }

        static void BuildExterior(Transform root)
        {
            // Main approach: the drawing's public level is 0.90 m above the court.
            Transform p=Group(root,"Accesos_exteriores_hacia_parque_central");
            int steps=6;float run=.32f;
            for(int i=0;i<steps;i++)
            {
                float top=-.9f+(i+1)*.15f,z=9.32f-(i+.5f)*run;
                Box(p,"Escalinata_entrada_G",new Vector3(-2.825f,top-.10f,z),new Vector3(5.2f,.20f,run),concrete,true);
                Box(p,"Banda_antideslizante_amarilla",new Vector3(-2.825f,top+.003f,z+run/2-.025f),new Vector3(5.1f,.006f,.035f),wood,false);
            }
            Ramp(p,new Vector3(-6.275f,-.90f,13.7f),new Vector3(-6.275f,0,7.4f),1.25f);
            Box(p,"Descanso_rampa_acceso",new Vector3(-6.275f,-.10f,6.775f),new Vector3(1.25f,.20f,1.25f),concrete,true);
            // External stairs visible on the auditorium side in photographs 2 and 3.
            StraightStair(p,"Escalera_exterior_auditorio",new Vector3(-9.9f,0,12.7f),new Vector3(-6.9f,H,5.9f),1.25f,21);
            Lift(p,"Ascensor_exterior_accesible",-10.35f,11.0f,-.9f,11.55f);
            foreach(float x in new[]{3,8,13,18})
                Box(p,"Seto_frente_aulas",new Vector3(x,-.48f,11.8f),new Vector3(3.6f,.72f,.70f),leaf,false);
            Sign(p,"PABELLON G",new Vector3(-.30f,1.9f,7.66f),.18f);
            Sign(p,"AUDITORIO\nHERNAN SILVA DIAZ",new Vector3(-4.8f,.65f,8.1f),.105f);
        }

        static void ConcreteJoints(Transform p,Vector2 a,Vector2 b,float y,float height)
        {
            Vector2 delta=b-a,dir=delta.normalized,outward=new Vector2(dir.y,-dir.x);
            Material seam=Material("G_Juntas_concreto",new Color(.43f,.42f,.38f));
            for(float t=1.2f;t<delta.magnitude;t+=1.2f)
            {
                Vector2 q=a+dir*t+outward*.105f;
                Box(p,"Junta_vertical_encofrado",new Vector3(q.x,y+height/2,q.y),new Vector3(.008f,height,.008f),seam,false);
            }
            for(float h=1.2f;h<height;h+=1.2f)
                Piece(p,"Junta_horizontal_encofrado",(a+b)/2+outward*.105f,y+h,.008f,delta.magnitude,.008f,seam,Mathf.Atan2(dir.x,dir.y)*Mathf.Rad2Deg,false);
        }

        static void Wall(Transform p,string name,Vector2 a,Vector2 b,float y,float height,Material mat,float doorT=-1,float doorWidth=1.0f)
        {
            Vector2 v=b-a;float length=v.magnitude;Vector2 dir=v/length;float yaw=Mathf.Atan2(dir.x,dir.y)*Mathf.Rad2Deg;
            if(doorT<0){Piece(p,name,(a+b)/2,y,height,length,.20f,mat,yaw);return;}
            float center=length*doorT,left=Mathf.Max(0,center-doorWidth/2),right=Mathf.Min(length,center+doorWidth/2);
            if(left>.01f)Piece(p,name+"_izq",a+dir*left/2,y,height,left,.20f,mat,yaw);
            if(right<length-.01f)Piece(p,name+"_der",a+dir*(right+(length-right)/2),y,height,length-right,.20f,mat,yaw);
            float dh=Mathf.Min(2.30f,height-.15f);Vector2 c=a+dir*center;
            Piece(p,name+"_dintel",c,y+dh,height-dh,doorWidth,.20f,mat,yaw);
            Piece(p,name+"_hoja",c,y,dh,doorWidth-.04f,.045f,wood,yaw,false);
            foreach(int s in new[]{-1,1})
            {
                Vector2 post=c+dir*s*doorWidth/2;
                Box(p,name+"_marco",new Vector3(post.x,y+dh/2,post.y),new Vector3(.05f,dh,.05f),metal,false);
            }
        }

        static void Piece(Transform p,string name,Vector2 c,float y,float h,float length,float thick,Material mat,float yaw,bool collision=true)
        { Box(p,name,new Vector3(c.x,y+h/2,c.y),new Vector3(thick,h,length),mat,collision,yaw); }

        static void Stair(Transform p,string name,float cx,float cz,float y,float rise,float lane,float run)
        {
            int count=Mathf.CeilToInt(rise/.18f);if(count%2!=0)count++;int half=count/2;
            for(int i=0;i<half;i++)
            {
                float h=(i+1)*rise/count,t=run/half;
                Box(p,name+"_ida",new Vector3(cx-lane*.55f,y+h/2,cz-run/2+t*(i+.5f)),new Vector3(lane,h,t),concrete,true);
                Box(p,name+"_vuelta",new Vector3(cx+lane*.55f,y+rise/2+h/2,cz+run/2-t*(i+.5f)),new Vector3(lane,h,t),concrete,true);
            }
            Box(p,name+"_descanso",new Vector3(cx,y+rise/2-.08f,cz+run/2+.14f),new Vector3(lane*2.1f,.16f,.28f),concrete,true);
            Box(p,name+"_llegada",new Vector3(cx,y+rise-.08f,cz-run/2-.14f),new Vector3(lane*2.1f,.16f,.28f),concrete,true);
            Rail(p,new Vector3(cx-lane*1.05f,y,cz-run/2),new Vector3(cx-lane*1.05f,y+rise/2,cz+run/2));
            Rail(p,new Vector3(cx+lane*1.05f,y+rise/2,cz+run/2),new Vector3(cx+lane*1.05f,y+rise,cz-run/2));
        }

        static void StraightStair(Transform p,string name,Vector3 start,Vector3 end,float width,int count)
        {
            Vector3 delta=end-start,flat=new Vector3(delta.x,0,delta.z);float run=flat.magnitude/count;
            for(int i=0;i<count;i++)
            {
                Vector3 c=start+flat*((i+.5f)/count);float h=delta.y*(i+1)/count;
                Box(p,name+"_peldaño",new Vector3(c.x,start.y+h-.10f,c.z),new Vector3(width,.20f,run),concrete,true,Mathf.Atan2(flat.x,flat.z)*Mathf.Rad2Deg);
            }
            Rail(p,start+Vector3.right*(width/2),end+Vector3.right*(width/2));
            Rail(p,start-Vector3.right*(width/2),end-Vector3.right*(width/2));
        }

        static void Lift(Transform p,string name,float x,float z,float y,float height)
        {
            foreach(int sx in new[]{-1,1}) foreach(int sz in new[]{-1,1})
                Box(p,name+"_pilar",new Vector3(x+sx*.64f,y+height/2,z+sz*.66f),new Vector3(.075f,height,.075f),metal,true);
            foreach(int sx in new[]{-1,1})
                Box(p,name+"_cerramiento_vidrio",new Vector3(x+sx*.64f,y+height/2,z),new Vector3(.045f,height,1.25f),glass,false);
            Box(p,name+"_puerta",new Vector3(x,y+1.1f,z+.66f),new Vector3(1.2f,2.2f,.045f),metal,true);
        }

        static void Ramp(Transform p,Vector3 a,Vector3 b,float width)
        {
            Vector3 delta=b-a;
            RotatedBox(p,"Rampa_accesible",(a+b)/2-Vector3.up*.08f,new Vector3(width,.16f,delta.magnitude),concrete,true,Quaternion.LookRotation(delta));
            Rail(p,a+Vector3.right*width/2,b+Vector3.right*width/2);
            Rail(p,a-Vector3.right*width/2,b-Vector3.right*width/2);
        }

        static void RoofRails(Transform p,Vector2 a,Vector2 b,float y)
        { Rail(p,new Vector3(a.x,y,a.y),new Vector3(b.x,y,b.y)); }
        static void Rail(Transform p,Vector3 a,Vector3 b)
        {
            Vector3 delta=b-a;int posts=Mathf.Max(1,Mathf.CeilToInt(delta.magnitude/1.25f));
            for(int i=0;i<=posts;i++) Box(p,"Baranda_poste",Vector3.Lerp(a,b,i/(float)posts)+Vector3.up*.48f,new Vector3(.045f,.96f,.045f),metal,false);
            foreach(float h in new[]{.48f,.96f}) RotatedBox(p,"Baranda_horizontal",(a+b)/2+Vector3.up*h,new Vector3(.04f,.04f,delta.magnitude),metal,false,Quaternion.LookRotation(delta));
        }

        static void Seat(Transform p,Vector3 at,bool desk,float yaw=0)
        {
            Transform seat=Group(p,desk?"Pupitre_aula":"Butaca_auditorio");seat.localPosition=new Vector3(at.x,at.y,-at.z);seat.localRotation=Quaternion.Euler(0,-yaw,0);
            Box(seat,"Asiento",new Vector3(0,.45f,0),new Vector3(.46f,.09f,.45f),wood,true);
            Box(seat,"Respaldo",new Vector3(0,.74f,.20f),new Vector3(.46f,.56f,.07f),wood,false);
            foreach(float x in new[]{-.18f,.18f}) Box(seat,"Soporte",new Vector3(x,.24f,0),new Vector3(.035f,.45f,.30f),metal,false);
            if(desk)Box(seat,"Tablero",new Vector3(.16f,.76f,-.20f),new Vector3(.42f,.045f,.34f),wood,true);
        }
        static void CeilingLights(Transform p,float y,float x0,float x1,float z)
        { for(float x=x0+2;x<x1;x+=3.5f) Box(p,"Luminaria_corredor",new Vector3(x,y+H-.23f,z),new Vector3(.24f,.05f,1.1f),concrete,false); }
        static void Sign(Transform p,string text,Vector3 at,float size)
        {
            var go=new GameObject(text);go.transform.SetParent(p,false);go.transform.localPosition=new Vector3(at.x,at.y,-at.z);go.transform.localRotation=Quaternion.Euler(0,180,0);
            var t=go.AddComponent<TextMesh>();t.text=text;t.characterSize=size;t.fontSize=48;t.anchor=TextAnchor.MiddleCenter;t.color=new Color(.1f,.12f,.10f);
            t.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");go.GetComponent<Renderer>().sharedMaterial=t.font.material;
        }

        static void Polygon(Transform p,string name,Vector2[] poly,float bottom,float top,Material mat)
        {
            // Ear clipping supports the concave auditorium footprint without a fan across the recesses.
            int n=poly.Length;var v=new List<Vector3>();foreach(var q in poly)v.Add(new Vector3(q.x,bottom,-q.y));foreach(var q in poly)v.Add(new Vector3(q.x,top,-q.y));
            var tri=new List<int>();var ids=new List<int>();float area=0;for(int i=0;i<n;i++){ids.Add(i);Vector2 a=poly[i],b=poly[(i+1)%n];area+=a.x*b.y-a.y*b.x;}
            if(area<0)ids.Reverse();int guard=0;
            while(ids.Count>2 && guard++<1000)
            {
                bool found=false;
                for(int j=0;j<ids.Count;j++)
                {
                    int a=ids[(j+ids.Count-1)%ids.Count],b=ids[j],c=ids[(j+1)%ids.Count];
                    if(Cross(poly[b]-poly[a],poly[c]-poly[b])<=.0001f)continue;
                    bool inside=false;foreach(int k in ids) if(k!=a&&k!=b&&k!=c&&Inside(poly[k],poly[a],poly[b],poly[c])){inside=true;break;}
                    if(inside)continue;tri.AddRange(new[]{a,b,c,a+n,c+n,b+n});ids.RemoveAt(j);found=true;break;
                }
                if(!found)throw new InvalidOperationException("Cannot triangulate G auditorium");
            }
            for(int i=0;i<n;i++){int j=(i+1)%n;tri.AddRange(new[]{i,i+n,j,j,i+n,j+n});}
            for(int i=0;i<tri.Count;i+=3){int t=tri[i+1];tri[i+1]=tri[i+2];tri[i+2]=t;}
            var mesh=new Mesh{name=name};mesh.SetVertices(v);mesh.SetTriangles(tri,0);mesh.RecalculateNormals();mesh.RecalculateBounds();
            string path=Art+name+".asset";var saved=AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if(saved){EditorUtility.CopySerialized(mesh,saved);UnityEngine.Object.DestroyImmediate(mesh);mesh=saved;}else AssetDatabase.CreateAsset(mesh,path);
            var go=new GameObject(name,typeof(MeshFilter),typeof(MeshRenderer),typeof(MeshCollider));go.transform.SetParent(p,false);go.GetComponent<MeshFilter>().sharedMesh=mesh;go.GetComponent<MeshRenderer>().sharedMaterial=mat;go.GetComponent<MeshCollider>().sharedMesh=mesh;
        }
        static float Cross(Vector2 a,Vector2 b){return a.x*b.y-a.y*b.x;}
        static bool Inside(Vector2 p,Vector2 a,Vector2 b,Vector2 c){return Cross(b-a,p-a)>=0&&Cross(c-b,p-b)>=0&&Cross(a-c,p-c)>=0;}
        static Transform Group(Transform p,string name){var go=new GameObject(name);go.transform.SetParent(p,false);return go.transform;}
        static void Box(Transform p,string name,Vector3 at,Vector3 size,Material mat,bool collision,float yaw=0)
        { RotatedBox(p,name,at,size,mat,collision,Quaternion.Euler(0,yaw,0)); }
        static void RotatedBox(Transform p,string name,Vector3 at,Vector3 size,Material mat,bool collision,Quaternion q)
        {
            if(size.x<=0||size.y<=0||size.z<=0)return;
            var go=GameObject.CreatePrimitive(PrimitiveType.Cube);go.name=name;go.transform.SetParent(p,false);go.transform.localPosition=new Vector3(at.x,at.y,-at.z);go.transform.localRotation=new Quaternion(-q.x,-q.y,q.z,q.w);go.transform.localScale=size;go.GetComponent<Renderer>().sharedMaterial=mat;
            if(!collision)UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
        }
    }
}
