# LID Terreno R3: conexión provisional con las llegadas inferiores

Base: `ba4dc4cdbaf668856bf9a00fd9869dea78ed3ff9`, rama publicada `feature/actualizacion-lid`.

## Resultado

Se prepara una malla alternativa del terreno general. La herramienta de Unity cambia únicamente su MeshFilter y el MeshCollider coincidente. No se desplazan el LID, sus escaleras, puertas, ventanas, descansos ni el muro ajustado a mano en la escena. Se conservan los materiales actuales: esta entrega resuelve geometría, no añade vegetación, mobiliario o nuevas texturas.

Ambas llegadas inferiores existentes están en Y=-1,20 m. Las aproximaciones nuevas llegan a ese nivel y vuelven al terreno anterior mediante dos desarrollos longitudinales de 15 m por lateral, al 8 %. Junto a cada caja de escalera se deja una franja exterior de 1,50 m. El acceso al piso inferior gira antes de la baranda existente y entra por el extremo abierto de la llegada: no se tapa el descanso ni se inventa otra escalera.

Se añaden aproximadamente 21,33 m² de suelo en las proyecciones exteriores que antes estaban completamente recortadas. Se conserva el espacio ocupado por las losas inferiores, evitando superponer terreno coplanar encima de ellas. La malla tiene fondo y caras laterales cerradas.

El espacio disponible difiere entre los lados. El empalme lateral este ocupa 8 m de desarrollo, con pendiente nominal del 15 %. Al oeste se limita a 3 m para conservar el borde exterior existente; allí la transición alcanza aproximadamente el 40 %, fuera de la franja exterior de 1,50 m. Ese banco más inclinado es una limitación explícita de la solución provisional y debe contrastarse con las cotas reales antes de considerarla definitiva. También se incorpora una transición hacia dentro alrededor de la esquina frontal, donde hay terreno fuera de la huella del edificio, para evitar un escalón en el límite de la modificación. Las facetas se triangulan siguiendo sus líneas de quiebre. El máximo calculado de la malla serializada está registrado en `Validacion_Terreno_R3.json`; los pequeños triángulos de borde pueden introducir diferencias numéricas respecto a esos valores nominales. No se anuncia todo el sector como una rampa al 8 %.

## Alcance y procedencia

Las posiciones de los núcleos, losas y peldaños proceden del modelo existente y su referencia horizontal al plano del LID. El perfil exterior de R3 es una **adaptación provisional elegida para revisar las conexiones**. No representa una cota topográfica recuperada del DWG ni una certificación de accesibilidad. La raíz del LID conserva Y=-1,20 m y el datum exterior continúa pendiente de confirmación.

Los perfiles se calculan por separado en los dos lados con el mismo criterio provisional. No se afirma que el campus real tenga dos laterales simétricos. Cuando se confirme la altimetría exterior deberán adaptarse esos perfiles.

El replanteo horizontal de la triangulación usa una cuadrícula de 0,1 mm para evitar tiras microscópicas entre los bordes CAD y los float32 de Unity. Fuera del ámbito local se conservan las alturas dentro de 1 mm de tolerancia y se comprueban las 83 muestras de R1. Las mallas originales no se sobrescriben. La triangulación nueva contiene unas 32.800 caras, frente a unas 29.200 de la alternativa R1 original.

## Instalación y aplicación

1. Guardar la escena y cerrar Unity. Instalar los archivos nuevos con `Instalar_LID_Terreno_R3.ps1` incluido en el paquete.
2. Abrir `Assets/UPCH/Scenes/Campus.unity`, esperar la importación y entrar en **Tools > UPCH > Terreno > LID - Descansos R3**.
3. Pulsar **Aplicar terreno LID R3**. Instalar archivos por sí solo no modifica la escena visible.
4. Usar los botones para enfocar ambos laterales y **Comprobar terreno, peldaños y espacio del jugador**.
5. Recorrer en Play ambas aproximaciones, los giros hacia las llegadas inferiores, las puertas y las escaleras. Guardar la escena después de revisarla.

El control nativo incluye 162 muestras de la franja exterior, 38 centros de peldaños y 74 muestras de entrada a las losas inferiores. Se esperan cero diferencias de altura, cero peldaños cubiertos, cero discontinuidades de entrada y cero muestras con obstáculos. La comprobación con cápsula consulta también los colliders ajenos al terreno; esos resultados están pendientes de ejecutar en Unity.

La cápsula de revisión tiene radio 0,30 m, altura 1,61 m y su base queda 0,04 m por encima del suelo. Su parte superior llega a 1,65 m sobre el pavimento. Es una comprobación discreta, no el barrido completo del controlador real ni una certificación del recorrido.

## Reversión y cambios manuales

El menú permite **Restaurar terreno R1** y la aplicación queda en Undo. No se guarda automáticamente la escena. Antes del cambio se copia el archivo de escena ya guardado a una carpeta de respaldo junto al proyecto; las ediciones sin guardar permanecen en la escena y Undo.

La herramienta comprueba el hash geométrico y la transformación del terreno, además de la posición, giro y escala del LID. Si no coinciden, se detiene antes de cambiar componentes. Cualquier edición manual del terreno debe registrarse para adaptar esta actualización. Los ajustes manuales del edificio no se reescriben.

Mientras R3 esté aplicada, usar su propio botón de restauración. Para operar de nuevo con la herramienta del Parque Central R1, restaurar primero R1 desde este menú.

## Comprobaciones y límites

`Validacion_Terreno_R3.json` registra la validación de la malla escrita y releída: cierre, rayos de suelo, continuidad hacia las losas existentes, conservación de R1, ausencia de suelo sobre los peldaños muestreados y coincidencia byte a byte de la escena, prefab y malla R1 de origen.

Se simula el cambio y la restauración de las dos referencias del terreno sin modificar otros documentos de la escena. No se han ejecutado Unity Editor, compilación C#, PowerShell ni Play en el entorno de preparación. El gráfico adjunto se calcula de las mallas; no es una captura del motor.

## Reproducción

Desde la raíz del proyecto, con NumPy, SciPy, Shapely, Triangle, Trimesh, Rtree, NetworkX, PyYAML y Matplotlib instalados:

```text
python tools/terreno/construir_lid_r3.py
python tools/terreno/validar_lid_r3.py
python tools/terreno/graficar_lid_r3.py
```

No es necesario ejecutar Python para instalar o aplicar la actualización en Unity.
