# LID R4: continuidad del terreno y ventanas inferiores

Requiere la entrega **LID Terreno R3** instalada y aplicada en Campus. Se prepara una malla nueva; no se sobrescriben R3, la escena, el prefab, materiales ni configuraciones XR/ProBuilder.

## Qué corrige

R3 resolvía las cajas de las escaleras, pero el suelo seguía en su cota anterior frente a buena parte de las fachadas. La nueva variante extiende una franja baja por el contorno del modelo y deja libres las bases de los marcos inferiores. No se elevan las ventanas ni se altera el interior para conseguir ese resultado.

La franja adopta **0,60 m desde el contorno del vacío del edificio en el terreno**, no desde cada vidrio. Los retranqueos de ventanas y columnas hacen que la distancia efectiva al vidrio varíe. Esa anchura es una decisión provisional de la adaptación, no una medida extraída de la fotografía.

Su nivel normal es **Y=-0,70 m**, equivalente al NPT +0,50 del datum actual del LID. Los marcos inferiores del modelo arrancan aproximadamente en NPT +0,62, por lo que queda un margen geométrico de unos 12 cm bajo ellos. Los descansos de las escaleras, que están más bajos, conservan su conexión R3 a Y=-1,20 m.

Se mantienen las alturas de la aproximación principal, el conector norte y la huella del jardín de ingreso oeste existente. Donde el suelo bajo llega a esas plataformas altas se construyen caras cerradas de terreno: la diferencia puede alcanzar 0,70 m y no se representa como una rampa de paso. No se añaden mobiliario, vegetación, nuevas barandas o texturas.

Las caras del suelo en el límite del edificio se prolongan hasta Y=-1,36 m, por debajo del piso inferior, para evitar ver el reverso de un pavimento de solo 16 cm de espesor. El dominio horizontal del vacío se conserva, de modo que este volumen no se extiende dentro del sótano.

## Transiciones y límites

El empalme entre la franja y el terreno anterior usa 3 m de anchura de trabajo y una interpolación geométrica con restricciones. El suelo se conserva o baja; no se levanta sobre el estado R3. Se conservan los niveles de los accesos ya existentes y las zonas profundas de las llegadas R3.

Las pendientes no son uniformes ni equivalen todas al 8 % de las aproximaciones originales R3. El máximo calculado en caras no verticales de esta malla es aproximadamente **52,64 %**, en encuentros locales; el percentil 99 es aproximadamente 40 %. Los bordes verticales de las plataformas se contabilizan aparte. Esta franja de separación no constituye una nueva ruta peatonal continua certificada.

La altimetría exterior, el datum global y los perfiles definitivos del campus siguen pendientes de confirmación. Esta entrega continúa la adaptación provisional elegida para revisar el modelo; no afirma que la fotografía permita medir pendientes o reproducir una sección exacta del terreno real.

## Aplicación en Unity

1. Guardar Campus, cerrar Unity e instalar los archivos nuevos con el PowerShell del paquete.
2. Abrir `Assets/UPCH/Scenes/Campus.unity` con R3 aplicada.
3. Entrar en **Tools > UPCH > Terreno > LID - Contorno y ventanas R4**.
4. Pulsar **Aplicar terreno LID R4**. La instalación de archivos por sí sola no cambia la escena visible.
5. Usar **Enfocar ventanas de la fachada** y los botones de ambos laterales.
6. Ejecutar **Comprobar contorno, ventanas y accesos** y recorrer en Play las llegadas inferiores, puertas, plataformas de acceso y transiciones del suelo.
7. Guardar la escena después de revisarla.

La herramienta sustituye únicamente la malla del suelo y la referencia de su MeshCollider. Antes comprueba geometría, posición del terreno y posición/giro/escala del LID. Si hay una malla propia diferente se detiene antes de cambiar componentes. Los objetos del edificio y sus ajustes manuales permanecen en la escena.

El control nativo revisa 162 muestras de recorrido, 38 peldaños, 74 muestras de entrada, 165 muestras delante de ventanas y 399 muestras del contorno. Se esperan cero diferencias de altura, peldaños cubiertos, obstáculos de paso, discontinuidades de entrada e incidencias de ventanas. Las consultas con cápsula son discretas; no sustituyen el recorrido real del jugador.

## Restauración

**Restaurar terreno R3** vuelve a la malla aceptada previamente. También puede usarse Ctrl+Z. R4 no guarda automáticamente la escena. Antes de aplicar/restaurar se copia el archivo de escena ya guardado a una carpeta de respaldo junto al proyecto; las ediciones sin guardar permanecen en la escena y Undo.

Mientras R4 esté aplicada, usar su propio menú. Para operar otra vez con la herramienta R3, restaurar primero R3 desde R4. No hace falta restaurar R3 a R1 para instalar esta entrega.

## Evidencia

`Validacion_Contorno_R4.json` contiene los resultados de la malla escrita y releída:

- Malla cerrada y con volumen positivo, incluidas las caras de las plataformas.
- 55 grupos de vidrio exterior del nivel inferior, con tres muestras por grupo: 165 controles bajo el margen mínimo de los marcos.
- 399 muestras del contorno y 95 muestras de las aproximaciones protegidas.
- Las 74 muestras de entrada R3 permanecen a sus alturas y ninguno de los 38 centros de peldaño queda cubierto.
- Los 83 controles de R1 y 500 muestras del borde exterior conservan sus alturas dentro de la tolerancia de 1 mm.
- Escena, prefab y malla R3 de origen idénticos byte a byte. Simulación de aplicar/restaurar dos referencias del suelo sin modificar otros documentos.

Los grupos de vidrio son elementos identificados del modelo; no se extrapola ese conteo a todas las ventanas reales del campus. El gráfico se calcula de las mallas serializadas y no es una captura de Unity.

No se ejecutaron compilación C#, PowerShell ni Unity/Play en el entorno de preparación. Para reproducir la geometría se usan las dependencias de `tools/terreno/requirements_r3.txt` y los scripts nuevos `construir_contorno_r4.py`, `validar_contorno_r4.py` y `graficar_contorno_r4.py`. Python no es necesario para instalar ni aplicar R4 en Unity.
