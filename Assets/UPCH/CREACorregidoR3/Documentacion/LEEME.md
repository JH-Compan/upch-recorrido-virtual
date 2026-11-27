# CREA corregido R3 — reparación de fachadas curvas y huecos


## Reparación solicitada en las capturas
- Se retiran las capas de paneles, paños y salientes que se superponían en la fachada posterior. Cada piso tiene un único muro curvo perforado, con su vidrio independiente por hueco. No hay un panel rectangular pegado sobre otro muro.
- Los 62 huecos usan ejes radiales y cilindros de 64 lados; su posición horizontal sigue los ejes de R2 contrastados con DWG. Diámetro y altura siguen siendo inferencias fotográficas.
- La superficie posterior se entrega uniforme de concreto, sin las falsas franjas salientes de ladrillo. Puedes asignarle otro material desde Unity.
- Los cerramientos circulares frontales y el zócalo se reconstruyen continuos; los bordes de losas y cubiertas se regularizan localmente para retirar los dientes de R2. Se cierran las bandas horizontales de los retranqueos y se adapta el borde alto frontal a las dos zonas de techo.
- Las superficies curvas siguen teseladas para el motor 3D, pero forman una malla continua por sector/piso, no bloques sucesivos. Puertas, ventanas, columnas fuera del sector reparado y escaleras siguen independientes.
- El radio frontal se regulariza a partir de caras ARC del DWG (7.00/7.10 m); el posterior se ajusta a los ejes de sus vanos (radios distintos por piso). No se sustituyó toda la planta por un círculo genérico.

## Instalar sin perder el CREA anterior
1. Guarda tu escena y cierra Unity. Extrae el ZIP fuera del proyecto.
2. Copia la carpeta CREACorregidoR3 y CREACorregidoR3.meta a C:\Proyectos\upch-recorrido-virtual\Assets\UPCH\.
3. Abre Unity 6000.3.10f1 y la escena que contiene tu CREA anterior. Si estás en la rama de LID, abre primero tu copia/rama de trabajo de CREA; este paquete no cambia ramas ni integra escenas.
4. Selecciona en Hierarchy la raíz completa de CREA y usa UPCH > CREA R3 CAD > Comparar con CREA anterior seleccionado. La nueva instancia copia posición, rotación y escala; la anterior queda desactivada, conservada. Ctrl+Z revierte la operación. Revisa antes de guardar.
5. Para una escena sin CREA usa Insertar edificio independiente; posición inicial de referencia histórica (28.24433,0,129.4139), rotación 0, escala 1. Esa posición no está verificada contra tu Campus actual.
6. Conserva tu conexión I-J existente. Solo si falta, usa Insertar conexion I-J alineada al CREA seleccionado. No dupliques las rampas.
7. Revisa referencias con el menú, consola, fachadas y recorridos en Play. Comprueba pasos, altura libre, colisiones y encuentro con terreno/FASPA antes de sustituir definitivamente la versión anterior.

No copies Fuente_CREA_R3 ni Fuentes_CAD dentro de Assets. No es necesario importar un unitypackage ni generar mallas. No se incluye Campus.unity ni ProjectSettings.

## Qué se corrigió
- Se decodificó 08. CREA 2026.dwg, incluidas entidades de bloques y su capa heredada. El primer lector omitía puertas insertadas; se descartó para construir la arquitectura. La segunda conversión y su inventario están adjuntos para trazabilidad.
- Muros y tabiques por caras, espesores y arcos de las plantas nativas: Trazas nativas de cerramientos conservadas como referencia; los sectores curvos se sustituyen en R3 por superficies continuas. Se reconstruyeron 69 puertas (23/21/25 por nivel), 86 conjuntos de ventana rectilínea y 31 módulos posteriores con dos ojos de buey cada uno (12/11/8 por nivel). La versión anterior repetía demasiados módulos posteriores.
- Vanos con recortes reales; paños de cierre, dinteles, jambas y alféizares separados. Columnas colocadas a partir de sus centros y radios en CAD. Se ajustaron encuentros numéricos sin fusionar el edificio.
- Azotea con alturas NTT distintas del DWG: +11.325, +11.475, +12.175 y +12.525 m. Se añadió el acceso No3 desde N3 a cubierta. Sus límites locales y desarrollo de escalera requieren la revisión indicada abajo.
- Materiales con texturas de la referencia Medicina K, adaptados a CREA: concreto, ladrillo, metal, vidrio y madera. GUID propios; no se depende de la carpeta de Medicina del proyecto.
- 1929 piezas y 153010 triángulos en el edificio. La conexión conserva 137 piezas y 7364 triángulos de R1.

## Editar
Cada pieza tiene GameObject, Transform y malla propios, organizada por nivel/categoría. Puedes mover, escalar, ocultar o sustituir piezas. Desempaquetar seleccionado para editar es opcional para editar la instancia. Duplica materiales cuando solo quieras cambiar una pieza. Para editar vértices usa Blender (fuente incluida fuera de Assets) o una herramienta de mallas.

Los archivos Meshes contienen múltiples mallas independientes, como la referencia Medicina; no son una sola malla fusionada. Los colliders son estáticos, incluidos vidrios. Las puertas se entregan abiertas en posición fija; no hay animación, NavMesh, controlador XR ni iluminación horneada.

## Cotas y registro
Metros, +Y arriba. Pivote fuente de CREA (-22,0,16), igual a R1. No aplicar giros correctivos de FBX a las mallas nativas.
N1 general +1.675 / Jefatura +2.350; N2 +5.175 / elevado +5.325; N3 +8.675; envolvente inferior -1.475. Las plantas DWG se registraron con la retícula común de columnas; las diferencias individuales alcanzan aproximadamente 0.10 m en plantas superiores. No es georreferenciación ni levantamiento.

## Comprobado y pendiente
La auditoría geométrica offline del edificio encuentra 0 bordes abiertos, 0 sólidos invertidos, 0 caras degeneradas y 0 caras repetidas dentro de una pieza. Se validaron identificadores, YAML y búferes de malla de ambos prefabs. Hay 1168 contactos/intersecciones entre piezas registrados: incluyen juntas constructivas y uniones de barandas, pero no se han aprobado individualmente todos. No equivale a ausencia de interferencias.

NO se ejecutó Unity Editor ni Play en este entorno. Se debe comprobar importación, shaders, navegación, altura libre y colisión con el controlador del proyecto.

Límites explícitos:
- Las plantas fijan posiciones horizontales; no todas las alturas de vanos, dinteles, diámetros ni posición vertical de los ojos de buey. Esos valores y algunos cierres verticales se reconstruyen por fotografía y criterio geométrico.
- Las losas parten de R1, con regularización local de bordes curvos y nuevas bandas de cierre de los retranqueos; la conexión exterior se conserva de R1; no se retrazaron completamente a partir del nuevo DWG. El retorno inclinado y la llegada a FASPA/terreno requieren comprobación en Campus. No se certifica accesibilidad normativa.
- Las cuatro alturas de cubierta proceden del DWG; los límites locales de cubierta, especialmente la zona central elevada y su borde curvo, son aproximados sobre el contorno anterior. La distancia de selección de vértices guardada en el JSON es una métrica de búsqueda, NO una tolerancia de fidelidad. Se necesita revisar el encuentro de esas cubiertas con las fachadas y secciones.
- No3 usa ejes/anchos nativos, pero el reparto de 10+10 peldaños y huella 0.25 m a través de los símbolos de corte sigue siendo supuesto. No2 y caracol conservan desarrollos verticales provisionales de R1. No afirmar rutas de evacuación verificadas.
- El rombo de Hemeroteca permanece como losa continua con baranda; no se abrió un vacío sin confirmación. No se modelaron interiores de sótano, instalaciones, mobiliario ni vegetación.
- Los renders son de Blender con la geometría entregada, no capturas de Unity ni representación certificada de obra real.

## Contenido
CREACorregidoR3: archivos nativos Unity, vistas, controles y JSON de geometría.
Fuentes_CAD: DWG/PDF originales, DXF derivado y datos de trazado/registro.
Fuente_CREA_R3: archivo Blender editable opcional.
La corrección es una revisión trazable que mejora R1; los límites anteriores impiden afirmar fidelidad completa al edificio construido.
