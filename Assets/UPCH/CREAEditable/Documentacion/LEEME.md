# Pabellón I CREA editable R1

Modelo independiente a partir de A-01 a A-04 de CREA y las fotografías adjuntas. Las plantas se registran mediante columna común y escala gráfica. El PDF readjuntado es idéntico al usado para las trazas anteriores (SHA256 9f0b62bcd62d2c409ef9c2f2578e0178be936fc85efebce1b822f75c0d2d0734). No es un levantamiento topográfico ni un expediente constructivo.

## Importar

1. Descomprime el ZIP fuera del proyecto. Abre **CREA_Editable_R1.unitypackage** con Unity, o usa Assets > Import Package > Custom Package. Importa la carpeta completa.
2. Quedará en **Assets/UPCH/CREAEditable**. No hay que generar mallas ni seleccionar un pabellón eliminado.
3. En Prefabs arrastra **Edificio_CREA_R1.prefab** a Hierarchy. Para la conexión exterior usa además **Conexion_I_J_R1.prefab**. Pon ambos con la MISMA posición, rotación y escala: comparten pivote y registro.
4. Si tu FASPA es el nativo R3 con sus ejes y pivote originales, selecciona su raíz completa y usa **UPCH > CREA editable R1 > 3. Colocar conjunto junto a FASPA R3 seleccionado**. Esto inserta dos objetos nuevos y mantiene FASPA. Usa esta opción una sola vez para evitar duplicados.
5. Comprueba desde arriba el terreno y los umbrales. El registro relativo proviene de los planos; no se ha cotejado con tu Campus actual. Desactiva el bloque simple de CREA si todavía está presente. Guarda la escena.

No copies la carpeta Fuente_CREA ni archivos .blend dentro de Assets. Es una fuente opcional para Blender. La alternativa manual al unitypackage es copiar **CREAEditable** y su .meta dentro de Assets/UPCH; utiliza solo uno de los dos métodos.

## Editar

Abre la flecha de Edificio_CREA_R1: Nivel_00, Nivel_01, Nivel_02, Nivel_03 y sus categorías. Cada paño, hoja, marco, columna, peldaño y tubo tiene su propio GameObject, Transform y malla. Puedes mover, escalar, ocultar o sustituir una pieza desde Hierarchy. Los conjuntos agrupan partes relacionadas, sin fusionarlas en un bloque único.

Para romper el vínculo de prefab puedes usar UPCH > CREA editable R1 > Desempaquetar seleccionado para editar. No es necesario para modificar propiedades de una instancia. Los materiales se comparten: duplica un material si quieres cambiar solo una pieza. Para editar vértices de un paño irregular utiliza una herramienta de mallas o el archivo Blender.

Oculta Cubiertas en Nivel_03 al trabajar dentro. Las vistas Planta_N1/N2/N3 son revisiones de cada nivel aislado, no nuevas plantas de proyecto.

## Construcción del archivo

- Edificio: **1930 piezas / 111,186 triángulos**. Conexión: **137 piezas / 7,364 triángulos**.
- 203 ejes/conjuntos de muro; 68 conjuntos de ventana recta y 69 de puerta procedentes de CAD. Los ojos de buey se representan aparte.
- Método por paños y recortes locales: jambas, alféizares, dinteles, hojas abiertas, columnas y losas. Las posiciones de puertas corresponden a sus arcos de apertura; no se confunden con símbolos de otros edificios del plano de ubicación.
- Contornos diferentes en cada piso, sectores elevados y terrazas separadas; la curva posterior no se sustituye por un único semicírculo igual para los tres niveles.
- Ladrillo posterior, concreto gris claro, carpintería oscura, vidrio y pérgolas de madera según fotos. Se reutilizan las texturas incrustadas y shader URP del material de Medicina K `K_20261119_153747_f8ccb9`, con GUID propios. No se trasladó la planta de Medicina sobre CREA.
- Dos vuelos rectos de rampa y giro con pendiente conservan el perfil reconstruido R7. El giro inclinado es una confirmación fotográfica; su distribución exacta es un supuesto. Tramos rectos: 7.75%; pendiente media del eje del retorno: aproximadamente 5.55%. No equivalen a una validación normativa de accesibilidad.
- Barandas: pasamanos Ø45 mm, postes Ø40 mm, separación de estaciones <=1.20 m. No se colocaron balaustres adicionales. Altura CREA 1.05 m; rampa exterior 1.00 m. La cantidad de segmentos del pasamanos curvo no multiplica los postes.
- Colliders estáticos de malla también en vidrios, para evitar cruzar ventanas. Puertas abiertas en posición fija, sin interacción de apertura. No hay NavMesh, controlador XR ni iluminación horneada.

## Niveles y escaleras

| Sector | Cota superior de piso (m) |
| --- | --- |
| Exterior de acceso principal | 0.000 |
| Primer piso general / Jefatura | +1.675 / +2.350 |
| Segundo piso general / sector elevado | +5.175 / +5.325 |
| Tercer piso | +8.675 |
| Cubierta asumida | +12.175 |
| Envolvente exterior inferior | −1.475 |

Ingreso principal: 11 subidas de 0.152273 m hasta +1.675, excepción autorizada previamente. La huella se conserva del contorno del plano. Las bases inferiores no se presentan como habitaciones de sótano.

| Escalera | Cotas (m) | Contrahuellas | Altura (m) |
| --- | --- | --- | --- |
| Escalera1_N2_D | 1.675 → 3.425 | 10 | 0.175000 |
| Escalera1_N2_I | 3.425 → 5.175 | 10 | 0.175000 |
| Escalera1_N3_D | 5.175 → 6.925 | 10 | 0.175000 |
| Escalera1_N3_I | 6.925 → 8.675 | 10 | 0.175000 |
| Escalera2_N2_-1 | 1.675 → 3.425 | 10 | 0.175000 |
| Escalera2_N2_1 | 3.425 → 5.175 | 10 | 0.175000 |
| Escalera3_TramoA | 5.325 → 7.000 | 10 | 0.167500 |
| Escalera3_TramoB | 7.000 → 8.675 | 10 | 0.167500 |
| CambioNivel_Puerta_N1_07 | 1.675 → 2.350 | 4 | 0.168750 |
| Escalera1_Exterior_Inferior | -0.420 → 1.675 | 12 | 0.174583 |

No1 usa las líneas y el reparto 10+10 de la revisión de planos; el tramo inferior exterior tiene 12. No3 usa 10+10 y la diferencia de cota +5.325 a +8.675. **No2 se reconstruye con 10+10; su conteo y conexión fina son supuestos a comprobar.** El caracol central aparece dibujado en las tres plantas: aquí tiene radio exterior aproximado 0.94 m, giro 330° y 20 subidas entre niveles; ese desarrollo no está confirmado por una sección. No se presenta como vía de evacuación validada.

El rombo de Hemeroteca permanece sobre losa continua con baranda. No se abrió un vacío sin confirmación. El acceso marcado HACIA AZOTEA no está resuelto: falta confirmar planta de cubierta, cota superior y desarrollo de esa escalera.

## Qué se comprobó

Mallas del edificio: **0 bordes abiertos/no manifold al soldar posiciones**, 0 sólidos invertidos, 0 caras degeneradas y 0 caras repetidas dentro de una pieza. Recortes de pasos de puerta, encuentros con columnas y duplicidades de paños se corrigieron localmente. Los alivios numéricos en dos contactos son de 0.2 mm; no son cambios de proyecto.

Se comprueban también identificadores, sintaxis YAML, búferes y referencias de ambos prefabs. Los resultados están en Verificacion_Archivos.json y los controles de geometría.

Hay **1042 contactos/intersecciones de volumen** entre piezas, registrados por nombre. Incluyen apoyos, peldaños/descansos, columnas, carpinterías y uniones de postes/pasamanos; no todos se han clasificado individualmente como junta correcta. No se afirma ausencia de solapes ni recorrido perfecto. El formato nativo se basa en la malla de Medicina, pero **no se ha ejecutado este paquete en un editor Unity en este entorno**. Importación, shaders del proyecto, altura libre, navegación y colisión del controlador deben comprobarse en tu instalación.

## Supuestos y límites que debes conocer

- Espesores gráficos, alturas de ventanas/dinteles, juntas y vuelos de marquesina; pérgolas y modulación de fachadas aproximados por foto. La foto no permite determinar dimensiones ocultas.
- Cantidad, diámetro y colocación vertical de ojos de buey: reconstrucción visual, no cota medida. Hay huecos reales a través del paño, no círculos pegados sobre un muro cerrado.
- Perfil del retorno, encuentro del pasillo con FASPA y terreno de tu Campus: requieren ajuste y prueba en escena. Se entregan separados precisamente para hacerlo sin deshacer J.
- Sector elevado de N2 y pasos entre cotas deben cotejarse con el recorrido presencial. Los peldaños por sí solos no acreditan circulación accesible.
- No incluye interiores de sótano, instalaciones, equipamiento, vegetación ni mobiliario exterior. El cerramiento inferior se limita a la envolvente visible.
- No modifica FASPA, Medicina ni Campus.unity. No contiene scripts duplicados de FASPANiveles ni depende del paquete antiguo FASPAEditable.

## Ejes y colocación

Metros, +Y arriba, raíz sin giro y escala 1. Ambos prefabs usan pivote fuente I=(-22,0,16). FASPA R3 usaba J=(7.075,0,15.35), de donde sale la traslación relativa **(-29.075,0,+0.650)** en los ejes de J. No apliques la antigua corrección FBX de −90°/180° a estas mallas nativas.

## Archivos

Prefabs: dos conjuntos listos. Meshes: Mallas_CREA.asset y Mallas_Conexion.asset contienen submallas independientes referenciadas por cada pieza, como el archivo de Medicina. Materials: materiales URP con texturas. Editor: menú de inserción y revisión. Referencias: PDF, JSON de geometría y contacto fotográfico. Documentacion: vistas, superposición de contorno/puertas sobre planos y controles.
