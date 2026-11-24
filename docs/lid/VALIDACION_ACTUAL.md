> Actualización posterior: **LID R2 Accesos y estructura**, documentada en `REVISION_ACCESOS_R2.md`. Los resultados de este documento describen la corrección anterior; R2 añade un recorte local de intradós y del pavimento auxiliar de revisión.

# LID: corrección y validación del 20 de noviembre de 2026

Base revisada: `develop`, commit `98e8d8030f6ea5e9bee3360b28c86395f0abf28e`.
Unity del proyecto: **6000.3.10f1**. Rama de trabajo: `fix/lid-sotano-distribucion`.

## Hallazgos y correcciones

1. La raíz del edificio en Campus estaba en Y = **+0,35 m**. El pavimento exterior del modelo, que tiene cota local +1,20 m provisional, quedaba a **+1,55 m** sobre el terreno del Campus. La raíz se sitúa en **-1,20 m** para alinear ese pavimento con el terreno Y = 0. Las plantas conservan su separación y sus posiciones horizontales. Esta operación registra el modelo existente con Campus; **no confirma la cota real de la explanada**.
2. Se crea `Site_Recorte_LID.asset` a partir del terreno original y se asigna tanto al MeshFilter como al MeshCollider de Terreno. El recorte sigue el contorno de sótano y accesos, incluidas la proyección frontal, la rampa norte y las cajas laterales. El área retirada es **2.245,728988 m²**. No se modifica el terreno original `Site.asset`.
3. Se retiran **2.833 piezas** del mobiliario simplificado: pantallas/soportes de computadora, asientos genéricos, sillas y sofás que habían sido interpretados como mesones. También se retiran las falsas mesas procedentes del bloque sanitario `1P-TOPPIECE`; los recintos de baños permanecen. Se conservan **1.037 cuerpos de mueble y sus 1.037 encimeras**, con el detalle y alturas esquemáticos que ya tenía el modelo. Las piezas retiradas están inventariadas en `correccion_aplicada.json`.
4. No se regeneran muros, tabiques, ventanas, barandas ni escaleras. Se conservan los fileID de todos los objetos restantes, los GUID de los assets existentes y el ajuste de la azotea que ya tenía Campus. El proxy anterior L permanece desactivado.
5. La herramienta de integración detecta instancias anidadas del edificio. Su recorte de terreno usa ahora **56 rectángulos** que descomponen el contorno medido, en vez de dos rectángulos generales. El menú nuevo permite revisar niveles, escala y cruces con el terreno dentro de Unity.

## Niveles

| Planta | NPT del plano (m) | Y en Campus corregido (m) |
| --- | ---: | ---: |
| Sótano | 0,00 | -1,20 |
| Primer piso | +3,20 | +2,00 |
| Segundo piso | +6,40 | +5,20 |
| Tercer piso | +9,60 | +8,40 |
| Cuarto piso | +12,80 | +11,60 |
| Azotea | +16,80 | +15,60 |

La cámara fría conserva su desnivel local de +0,15 m respecto al primer piso. NPT y coordenada mundial de Unity son referencias distintas: desplazar la raíz no cambia los NPT relativos.

## Comprobaciones ejecutadas

Se leen los assets nativos del repositorio y se aplican todas las transformaciones de su jerarquía. No se usa la imagen de una vista previa como prueba dimensional.

- **22 secciones horizontales** de muros y tabiques coinciden con el control extraído del CAD. Máxima diferencia simétrica de área: **0,000098574 m²**. En el sótano se excluyen de ese contraste constante las zonas recortadas por los intradoses de las escaleras y por la cubierta baja frontal.
- **569 referencias de ambientes** mantienen nombre, planta y posición. Son rótulos del plano, algunos repetidos; **no equivalen a 569 recintos únicos**. `ambientes_actuales.csv` permite localizar cada referencia en planta.
- **790 comparaciones de trazas de hojas de puerta**, incluidas referencias repetidas del CAD. Máxima desviación horizontal: **0,000016731 m**. La hoja abierta no se utiliza como medida del ancho libre del vano.
- Los seis suelos se verifican en el hall mediante intersecciones con la geometría nativa. No hay niveles repetidos o desplazados en la jerarquía.
- Una sola instancia de LID en Campus; proxy anterior inactivo; sin referencias locales de prefab rotas ni GUID de malla ausentes.
- El terreno ya no cubre los espacios excavados. La intersección residual al serializar vértices float32 es **0,000058721 m²**, localizada en el borde del recorte. Fuera del contorno de recorte no se retira área adicional.
- En Campus cambian únicamente tres documentos serializados: la posición de la raíz LID y las dos referencias a la malla del terreno. No se cambian los demás objetos del equipo.

Los resultados completos y las tolerancias están en `validacion_actual.json`. Las intersecciones entre muros, losas y apoyos son contactos constructivos esperados; no se usa el criterio incorrecto de prohibir todo contacto entre piezas.

## Lo que falta para afirmar fidelidad total

Los adjuntos contienen plantas; no incluyen un corte que confirme el NPT de la explanada, las alturas de todos los vanos, los espesores de losas o las contrahuellas exteriores. El terreno +1,20 m del modelo sigue siendo provisional, igual que las hipótesis verticales documentadas en la revisión de entrada. La posición horizontal de esos elementos se conserva.

**No se ha ejecutado Unity Editor, Play ni la prueba en visor en este entorno.** Antes de aprobar el avance hay que abrir Campus, comprobar la consola y recorrer sótano, accesos, puertas, escaleras, pasarela oeste y cada planta. La concordancia de los controles geométricos no certifica por sí sola que todo el edificio sea 100 % idéntico a la obra real.

## Aplicación y revisión

El ZIP contiene una corrección para el repositorio existente, no un proyecto Unity vacío ni un segundo edificio para arrastrar a Campus.

1. Cerrar Unity y dejar limpio el árbol de trabajo del proyecto.
2. Partir del commit base indicado y crear una rama `fix/lid-sotano-distribucion`.
3. Ejecutar el instalador PowerShell incluido con la ruta del proyecto. Verifica los hashes previos y crea una copia de seguridad antes de copiar los archivos. Si el proyecto tiene otras ediciones en los archivos afectados, se detiene para no sobrescribirlas.
4. Abrir el proyecto con Unity 6000.3.10f1 y la escena `Assets/UPCH/Scenes/Campus.unity`. **No volver a generar ni a integrar otro LID.**
5. Ejecutar `Tools > UPCH > LID completo > Validar niveles y superposiciones en Campus` y realizar el recorrido en Play. Revisar también el prefab en la escena independiente.
6. Revisar el diff, guardar los cambios comprobados y abrir PR a `develop`, manteniendo un responsable por escena.

Para repetir la comprobación estática: instalar `tools/lid/requirements.txt` y ejecutar `python tools/lid/auditar_lid.py`. El script `corregir_lid.py` reproduce la corrección sobre la base y no es necesario para importar los assets ya corregidos.

Los documentos de validaciones anteriores incluidos en `Assets/UPCH/LIDCompleto/Documentacion` describen sus versiones históricas. Esta revisión y sus resultados prevalecen para el estado actual del modelo.

## Fuentes y alcance

- PDF adjunto: `11. PAB. LID 2026(2).pdf`, láminas A-01 a A-05.
- DWG adjunto: `11. PAB. LID 2026(2).dwg`, seis plantas, incluida la azotea.
- La referencia geométrica procede de la conversión del DWG a DXF, contrastada con el PDF. Las advertencias de conversión de datos dinámicos del DWG impiden certificar una conversión integral sin pérdida de todos los objetos de AutoCAD.
- Huella principal rotulada: **65,10 × 34,61 m**; profundidad geométrica de referencia **34,60513955 m**. La proyección frontal del sótano y las escaleras exteriores exceden esa envolvente principal y se controlan por separado.
- Los hashes SHA-256 de ambos adjuntos se conservan en `validacion_actual.json` y `tools/lid/referencia_cad.json`.
