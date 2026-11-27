# FASPA reconstruido R3

Paquete independiente, rehecho con construcción por paños y conjuntos. No es la fragmentación del modelo anterior. Contiene el prefab y las mallas nativas ya escritos: no tienes que generar miles de archivos desde otro edificio.

## Instalación

1. Copia **FASPAReconstruido** del ZIP en `C:\Proyectos\upch-recorrido-virtual\Assets\UPCH`.
2. Conserva la carpeta completa y todos sus `.meta`. No sobrescribas FASPACompleto ni FASPAEditable.
3. Espera la importación. En Project abre `Assets/UPCH/FASPAReconstruido/Prefabs`.
4. Arrastra **Edificio_FASPA_R3.prefab** a Hierarchy; también puedes usar **UPCH > FASPA R3 > Insertar prefab independiente**.
5. Para editar libremente, selecciona su raíz y usa **UPCH > FASPA R3 > Desempaquetar seleccionado para editar**.
6. Guarda la escena con Ctrl+S. Los materiales se comparten; duplica un material para recolorear una sola pieza.

## Comparar con tu versión anterior

Selecciona exactamente **Edificio_FASPA** y ejecuta **UPCH > FASPA R3 > Comparar en lugar del FASPA anterior seleccionado**. La versión vieja se conserva desactivada; Undo permite volver atrás. Este comando compensa la conversión FBX de aquella versión, suponiendo que no alteraste sus ejes internos. Comprueba el contorno desde arriba antes de guardar.

Este prefab nuevo es **Y arriba**, X/Z positivos del plano, metros, escala 1 y raíz sin giro. No copies automáticamente la rotación 180° que necesitaba el FBX anterior. La posición histórica aproximada del pivote era `(57.31933, 0, 128.7639)`; para esta versión nativa el giro de partida sería `(0,0,0)`. Es referencia de colocación, no validación topográfica del campus.

## Qué cambió

- 1147 piezas con nombres y pivotes propios; 23,124 triángulos. La versión fragmentada tenía 577.308. El foco es que cada corrección afecte un elemento reconocible.
- 88 conjuntos de paños: jambas, dinteles y alféizares por tramos, en lugar de triangulación fragmentada de todo el volumen. Los paños personalizados se escalan con Transform; editar vértices requiere una herramienta de mallas o Blender.
- 56 conjuntos de ventana/vidrio y 54 de puerta/acceso. Los elementos fuente paralelos repetidos se consolidaron. Las hojas de puerta están en la posición abierta dibujada, sin mecanismo interactivo.
- Columnas separadas y recortes locales de paños, vidrios y marcos en sus encuentros. Se eliminaron los muros altos espurios sobre las diagonales de circulación.
- Piso por sector a su cota; terraza abierta y vacío de doble altura sin añadir otra losa. Cubiertas planas a +11.18 y +9.64 m, cotas superiores asumidas previamente.
- Ingreso principal recolocado en el borde oblicuo del plano, con cinco subidas de 0.18 m a +0.90; la escalera lateral inventada en el otro borde se retiró.
- Acabados grises, azul en el sector fotografiado, marco de aluminio claro y acabado amarillo junto al núcleo. No se pinta toda la planta baja de azul.
- Materiales basados en los archivos reales del paquete de Medicina `K_20261119_153747_f8ccb9`: mismo shader URP y texturas incrustadas de concreto/madera/metal/vidrio; identificadores independientes y tintes adaptados a FASPA. No se copiaron muros de Medicina a otra planta.

## Planos y fotos

A-01, A-02 y A-03 del PDF adjunto. El nuevo PDF es idéntico en bytes al anterior; la reconstrucción cambia el método y corrige la infraestructura, no una versión diferente del plano. Se usan líneas de las capas arquitectónicas y los contornos corregidos de la revisión anterior. La foto define el aspecto; no sustituye las cotas de planta.

Las trazas de doble cara permiten reconstruir paños de muros y drywall. Su calibración es gráfica: no se declara precisión topográfica. El ancho nominal del cuerpo es 14.15 m. El primer nivel tiene borde oblicuo que amplía la envolvente; no se debe reescalar todo el edificio para forzar 14.15 m de extremo a extremo incluyendo salientes.

## Escaleras

- Esc_N2_Conector: 5 contrahuellas de 0.180000 m; PLANO: 5/8 líneas; alturas exactas.
- Esc_N3_Conector: 8 contrahuellas de 0.180000 m; PLANO: 5/8 líneas; alturas exactas.
- Esc_N1_Diagonal_0: 7 contrahuellas de 0.172000 m; SUPUESTO: reparto de peldaños; revisar trazas superpuestas.
- Esc_N1_Diagonal_1: 8 contrahuellas de 0.172000 m; SUPUESTO: reparto de peldaños; revisar trazas superpuestas.
- Esc_N2_Diagonal_0: 6 contrahuellas de 0.166154 m; SUPUESTO: reparto de peldaños; revisar trazas superpuestas.
- Esc_N2_Diagonal_1: 7 contrahuellas de 0.166154 m; SUPUESTO: reparto de peldaños; revisar trazas superpuestas.

La suma de alturas coincide exactamente con las cotas de destino. Los tramos largos ya tienen peldaños geométricos, **pero el conteo sigue siendo una decisión de reconstrucción**, no una lectura definitivamente validada: debe confirmarse con una toma cercana de las escaleras. No se presenta una rampa provisional como escalera aprobada.

## Validación automática y límites

- Bordes abiertos: 0; sólidos invertidos: 0; caras degeneradas: 0; caras repetidas dentro de una misma pieza: 0.
- Tolerancia lineal: 0.0001 m. Umbral volumétrico: 0.0000001 m³. Se revisaron 1079 pares con cajas superpuestas: 531 intersecciones de volumen permanecen, registradas por nombre en Control_Geometrico.json. Incluyen juntas de columnas/losas, postes/pasamanos, hojas/marcos y apoyos de escalera. No se afirma ausencia de intersecciones ni transitabilidad perfecta.
- Se verifican búferes de malla, identificadores nativos y enlaces entre prefab, Meshes y Materials. El formato de malla se tomó del archivo de Medicina suministrado.
- **No se ha ejecutado este prefab en un editor Unity aquí.** La importación, materiales de tu proyecto, colliders y navegación requieren la prueba en tu instalación. El menú Revisar referencias ayuda a detectar mallas o shaders no resueltos.
- Los colliders son de malla no convexa para arquitectura estática; vidrios sin collider, hojas opacas abiertas con collider. No se incluyen controlador de puertas, NavMesh, iluminación horneada ni optimización final para Meta Quest.

## Pendientes / supuestos

- Confirmar número y reparto de contrahuellas de las dos escaleras diagonales; se proponen 15 y 13 entre sus cotas exactas.
- Altura de ventanas, dinteles, espesores no acotados, modulación de carpintería y detalle de encuentros de la fachada: aproximaciones por fotos. Ajustables por conjunto.
- Acceso corredizo azul lateral: tipo por foto; posición longitudinal y ancho aproximados. No se atribuyen al plano si no están claramente acotados.
- Terminación exacta del núcleo amarillo y sus paños vidriados altos: referencia fotográfica parcial; este modelo no es un levantamiento de fachada completo.
- Baños/archivos/divisiones se representan mediante trazas de muro y puertas; no se incluyen sanitarios, casilleros, muebles ni instalaciones.
- No se rehacen CREA, el edificio K, el pasillo compartido, jardines ni la rampa de CREA. Este paquete es solo FASPA; esas piezas del campus deben conservarse por separado.
- No aplicar el antiguo generador de planos sobre esta nueva raíz: utilizaba los ejes del FBX anterior.

## Carpetas

Prefabs: prefab listo para arrastrar. Meshes: `Mallas_FASPA.asset` con mallas independientes referenciadas por cada objeto, como en Medicina. Materials: materiales URP con texturas incrustadas. Editor: herramientas de inserción/revisión. Referencias: geometría fuente y PDF. Documentacion: informe, controles y vistas.

La carpeta **Fuente_Blender_FASPA_R3** del ZIP es opcional y debe quedarse FUERA de Assets para que Unity no intente importar Blender automáticamente. Las vistas son renders de revisión de la misma geometría, no capturas del editor Unity ni certificación constructiva.
