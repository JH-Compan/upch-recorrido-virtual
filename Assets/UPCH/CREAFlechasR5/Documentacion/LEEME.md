# CREA R5 — nuevas correcciones señaladas sobre R4

Base: CREA_R4_Correcciones_Flechas_Unity.zip entregado anteriormente. Se usan las nuevas capturas con flechas, fotos y las trazas registradas del DWG 08. CREA 2026, contrastadas con el PDF de plantas. No se aplica una reconstrucción global del pabellón.

## Instalar sin perder la R4
1. Guarda tu escena y cierra Unity. Extrae este ZIP fuera del proyecto.
2. Copia CREAFlechasR5 y CREAFlechasR5.meta a C:\Proyectos\upch-recorrido-virtual\Assets\UPCH\.
3. Abre Unity 6000.3.10f1, abre Campus y selecciona la raíz completa de CREA R4 en Hierarchy.
4. Usa UPCH > CREA R5 CAD > Comparar con CREA anterior seleccionado. La nueva instancia copia posición, rotación y escala; la anterior queda desactivada y conservada. Ctrl+Z revierte la comparación.
5. Revisa los mismos ángulos de tus capturas. Usa Revisar referencias del seleccionado y prueba las escaleras y sus llegadas en Play antes de guardar definitivamente.

No insertes de nuevo la conexión I–J: su geometría es idéntica a R4. No se reemplazan Campus.unity, FASPA, Medicina ni ProjectSettings. No copies Fuente_CREA_Flechas_R5 ni Fuentes_CAD_R5 dentro de Assets.

La base es la R4 entregada; cambios manuales que solo existan en tu escena no se transfieren automáticamente a la nueva instancia. La anterior se conserva para compararlos.

## Cambios de las nuevas flechas
| Zona | Corrección localizada |
| --- | --- |
| Dos balcones junto al ala derecha | Losas triangulares en las cotas originales N1/N2, antepecho de ladrillo, vidrio superior y baranda de tres travesaños. Se retiran las hojas abiertas hacia ese vacío. |
| Junta de viga y columna | Continuidad del pilar marcado a través de los 0.24 m de espesor de losa; no se desplaza la columna ni el ala. |
| Volumen curvo lateral, piso intermedio | Se retiran los ventanales grandes señalados y se reconstruye el paño ciego de ladrillo entre bandas de concreto. |
| Volumen curvo lateral, piso inferior | Se sustituyen las ventanas rectangulares señaladas por una franja alta de vidrio siguiendo el arco; ventanas del ingreso fuera de ese sector permanecen iguales. |
| Escalera lateral No2 | Cerramiento exterior continuo, frente de descanso con vidrio y cubierta, sin dos franjas cruzadas. Se completa el tramo inferior que aparece en la planta de sótano y su apoyo exterior; no se modelan otros interiores de sótano. |
| Base debajo del letrero | Cierre localizado para suprimir el corte/espacio señalado; el cartel y su fachada superior no cambian. |
| Escalera central No3 y acceso a azotea | Vuelos y anchos registrados en DWG; descansos, enlace N3, llegadas y huecos de losa/cubierta corregidos. Se retiran parapetos cruzados; se añade la vidriera frontal con pilares y vigas de borde. |
| Inicio y paso de No3 | Aperturas limitadas a dos paños que bloqueaban el recorrido. Los descansos de No2 se corrigen para que no queden sobre los últimos peldaños. La cubierta No2 se eleva localmente 0.20 m para liberar gálibo. |

Los balcones intervenidos son únicamente los del chaflán junto al ala derecha, identificados en tus nuevas fotos. No se repiten balcones nuevos en las otras caras del edificio.

## Conservación comprobada
De 1878 piezas de R4, **1682 son exactamente idénticas** en sus datos completos. 11 piezas se modifican localmente y 185 se sustituyen en las zonas indicadas; R5 incorpora 255 piezas nuevas. Edificio final: 1948 piezas / 154,888 triángulos. No hay diferencias sin motivo registrado.

Fachada posterior, rectángulos/óculos, letrero, pérgolas, caracol, marquesina y escalera principal de ingreso mantienen sus piezas exactamente iguales. La conexión I–J conserva su geometría completa. Ver Preservacion_R4_R5.json y Comparacion_Objetos_R4_R5.csv. Las losas compartidas se modifican solamente en el área de No3; no se rehacen los demás sectores de cubierta.

## Verificación geométrica
Auditoría offline: 0 bordes abiertos/no manifold al soldar posiciones, 0 sólidos invertidos, 0 caras degeneradas o repetidas dentro de una pieza y 0 fallos de booleana. Se comprueban los búferes, IDs y referencias de ambos prefabs.

Se probaron los centros de **80 peldaños de No2/No3** con un cilindro de radio 0.22 m que ocupa desde 0.25 hasta 1.85 m sobre la superficie del peldaño: **0 colisiones de volumen** en esa prueba. Se detectaron y corrigieron la invasión del descanso No2, el techo bajo No2 y dos paños que obstruían No3. Los resultados completos están en Control_Galibo_Escaleras_R5.json.

Esta prueba no simula la trayectoria entre muestras, el giro en los descansos, manos, puertas interactivas ni el controlador XR. No valida accesibilidad, evacuación o cálculo estructural. Hay 1232 contactos/intersecciones generales entre piezas, incluidos encuentros constructivos e interfaces heredadas; no se aprobaron individualmente todos. No se afirma ausencia global de interferencias.

**No se ejecutó Unity Editor ni Play aquí.** La importación URP, colisión real del controlador, llegada al terreno, giros y cambios de cota deben revisarse en tu proyecto. Las imágenes adjuntas son renders de la geometría entregada, no capturas de Unity.

## Interpretación y límites
- N1 +1.675 / +2.350; N2 +5.175 / +5.325; N3 +8.675 y cubierta general +12.175 m se conservan de la base. No se mueve el edificio en Campus ni se cambia el resto de cubiertas.
- No3 usa las líneas de peldaños y anchos del DWG de N3/azotea, completando los símbolos de corte a 10+10. El reparto de contrahuellas requiere cotejo con sección o medición.
- La planta de sótano sí contiene No2 bajo N1. Se completa solo su tramo inferior -1.475 a +1.675 con 10+10 sobre los ejes retenidos. Ese desarrollo vertical es reconstruido; los números dibujados de escalera no se presentan como una certificación de todas las contrahuellas.
- Alturas de barandas, antepechos, cerramientos, ventanas altas y vidriera, espesores, profundidad de balcones y gálibos se reconstruyen con las fotos. La fotografía no determina medidas ocultas ni sustituye un levantamiento.
- Los huecos No2/No3 se limitan a sus accesos y volúmenes de paso. No se vacía una fachada completa ni se alteran habitaciones fuera del área señalada.
- El material nuevo I_ladrillo_balcon usa el mismo patrón recreado que los sectores corregidos de R4; los materiales de piezas no intervenidas se mantienen. Vidrios y piezas se editan por separado. Materiales compartidos deben duplicarse si quieres cambiar una sola pieza.

## Editar
Abre la jerarquía del prefab por niveles/categorías. Cada peldaño, paño, vidrio, poste y marco tiene objeto y malla propios. Puedes desempaquetar la instancia desde el menú R5 para editarla. Para editar vértices usa la fuente Blender o una herramienta de mallas. Las puertas conservadas son estáticas y los colliders son de malla; no se añade NavMesh ni interacción.

## Contenido
CREAFlechasR5: carpeta Unity nativa. Documentacion: vistas de los puntos señalados, auditoría, gálibo y comparación R4/R5. Antecedentes_R4 contiene controles históricos, no la validación actual. Fuente_CREA_Flechas_R5: Blender opcional fuera de Assets. Fuentes_CAD_R5: DWG/PDF originales fuera de Assets.
