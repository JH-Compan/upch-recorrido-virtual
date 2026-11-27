# CREA R4 — correcciones localizadas de las flechas

Base: CREA_Editable_R1_Unity(3).zip adjunto por el usuario. Se contrastó con 08. CREA 2026(1).dwg, 08. CREA 2025(5).pdf y las fotos/capturas señaladas. El DWG y PDF son idénticos en bytes a los entregados previamente. R4 parte de R1, no de las versiones R2/R3 que cambiaban otras zonas.

## Instalar y comparar
1. Guarda la escena y cierra Unity. Extrae el ZIP fuera del proyecto.
2. Copia CREAFlechasR4 y CREAFlechasR4.meta dentro de C:\Proyectos\upch-recorrido-virtual\Assets\UPCH\.
3. Abre Unity 6000.3.10f1 y la escena que contiene CREA. En Hierarchy selecciona la raíz completa de tu CREA anterior.
4. Usa UPCH > CREA R4 CAD > Comparar con CREA anterior seleccionado. Se copia el Transform de la raíz y se conserva el anterior desactivado. Ctrl+Z revierte la comparación. No selecciones Campus ni una ventana ni un asset de Project.
5. Revisa las mismas vistas de las flechas, los vanos, escaleras y descansos. Usa Revisar referencias del seleccionado y después prueba el recorrido en Play. Guarda al finalizar la revisión.

Conserva la conexión I–J existente. Su geometría es idéntica a la del ZIP base y no se necesita insertar otra. El prefab Conexion_I_J_Flechas_R4 se incluye solamente para una escena donde falte. No se incluye ni reemplaza Campus.unity, FASPA, Medicina ni ProjectSettings.

La comparación conserva posición, rotación y escala de la raíz, pero no transfiere modificaciones manuales de piezas que solo existan en una escena y no estén en el ZIP. La instancia anterior queda conservada para revisarlas. No copies Fuente_CREA_Flechas_R4 ni Fuentes_CAD_R4 dentro de Assets.

## Qué corresponde a cada flecha
| Zona indicada | Corrección |
| --- | --- |
| Frente circular y base estriada | Cerramiento curvo regularizado, paños de ladrillo y bandas de concreto; zócalo continuo únicamente en el sector marcado. Ventanas y columnas existentes se conservan. |
| Bordes del volumen circular | Se retiran dientes solo en las bandas perimetrales señaladas. Se completa localmente la cubierta del volumen bajo de ingreso. |
| Fachada posterior y huecos entre plantas | Capas superpuestas sustituidas por un muro de ladrillo continuo por piso. Bandas horizontales cierran los retranqueos indicados. |
| Rectángulos y ojos de buey | Rectángulos iguales dentro de cada nivel; dos círculos centrados por panel, con perforación real y vidrio independiente. Márgenes laterales de 0.11 m y separación vertical de centros 0.65 m. |
| Escalera lateral de concreto y tramo inferior | Se conservan los ejes, huellas y cotas superiores de los peldaños; se reconstruyen intradoses y parapetos de concreto y se abren las bocas de los descansos. |
| Escalera junto al volumen circular | Cerramientos laterales de concreto con franjas de vidrio y dinteles inclinados, según la foto. Encuentros recortados contra piezas existentes. |
| Acceso superior señalado | Continuación de No3 hacia azotea en sus mismos ejes y hueco localizado en la cubierta original. |
| Entrada principal | Columna rectangular y ménsula escalonada bajo la marquesina existente. |
| Letrero | Panel azul con texto 3D editable que reproduce la composición principal. Es una recreación simplificada, sin QR funcional ni reproducción de las fotografías pequeñas del cartel. |

## Qué se conservó y cómo se comprobó
De 1930 piezas originales, **1406 permanecen exactamente iguales** en sus datos completos de geometría/material/Transform fuente. 113 piezas originales se modifican localmente y 411 se sustituyen dentro de las zonas indicadas. R4 contiene 1878 piezas y 151,076 triángulos. Los cambios y sus motivos se registran por nombre en Comparacion_Objetos_R1_R4.csv y Preservacion_R1_R4.json; no hay cambios sin motivo registrado.

La conexión I–J permanece idéntica a R1. Se conserva el caracol, pérgolas, carpinterías originales, escaleras principales de ingreso y arquitectura fuera de las zonas señaladas. Las cotas superiores de los 92 peldaños originales reconstruidos coinciden con R1 con error máximo de 8.88e-16 m; el intradós sí cambia para seguir la pendiente.

No se actualiza el resto del edificio al DWG 2026: eso habría excedido el alcance. Se mantienen las cotas R1: N1 +1.675 / +2.350, N2 +5.175 / +5.325, N3 +8.675 y cubierta general +12.175 m. No se trasladan a otras zonas las alturas de otras cubiertas del DWG. La colocación en Campus no se recalculó.

## Materiales y edición
Piezas separadas por nivel y categoría. Paños curvos continuos por sector; paneles, vidrios, peldaños, parapetos y letras editables por separado. Las mallas viven en Meshes y se referencian desde cada GameObject, como la referencia de Medicina.

Solo los sectores corregidos usan el material nuevo I_ladrillo_foto: textura de aparejo recreada, no color rojo plano. Su UV sigue el desarrollo angular de los paños curvos. El patrón es aproximado a la fotografía; no es una textura medida de obra. Los materiales previos siguen en las piezas no intervenidas. Duplica materiales para cambiar una sola pieza. Para editar vértices usa Blender (fuente opcional) o una herramienta de mallas.

## Verificación y límites
Auditoría offline: 0 bordes abiertos/no manifold al soldar posiciones, 0 sólidos invertidos, 0 caras degeneradas, 0 caras repetidas por pieza y 0 fallos de booleana. Los rectángulos posteriores tienen **0 intersecciones de volumen con otras piezas** a tolerancia de 0.1 mm y umbral de 1e-7 m³. Se verifican también YAML, identificadores, búferes y referencias de los prefabs.

Quedan 951 contactos/intersecciones generales entre piezas, incluyendo encuentros constructivos heredados y nuevas juntas; no se aprobaron individualmente todos. No se afirma ausencia global de interferencias.

**No se ejecutó Unity Editor ni Play en este entorno.** Las vistas son renders Blender de la geometría entregada. Verificar importación URP, altura libre, colisiones del controlador, pasos entre cotas, conexión al terreno y recorrido en tu instalación. Los colliders son de malla estáticos; puertas abiertas fijas, sin NavMesh ni interacción nueva.

Las plantas no fijan todas las secciones. Espesores y alturas de parapetos, vidrios inclinados, paneles, diámetro/altura de los círculos, ménsula y cartel se reconstruyen por foto. Los paneles se distribuyen simétricamente sobre los arcos del DWG conservando 19/19/17 módulos de R1, con ajuste local en el nivel superior para evitar las columnas. No equivalen a dimensiones certificadas de obra.

No3 hacia azotea usa 10+10 subidas hasta +12.175; ese reparto vertical y el de No2 requieren cotejo con sección o medición. La cota exterior inferior -0.420 de R1 se conserva; no se cambia terreno ni se certifica accesibilidad normativa. No se añaden interiores de sótano ni instalaciones.

## Archivos
Prefabs: Edificio_CREA_Flechas_R4 y conexión opcional. Referencias: geometría editable y referencias R1. Documentacion: vistas, auditoría y comparación por pieza. Fuente_CREA_Flechas_R4: Blender fuera de Assets. Fuentes_CAD_R4: DWG/PDF originales fuera de Assets.
