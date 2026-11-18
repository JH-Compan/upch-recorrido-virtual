# Pabellón H — Veterinaria

Implementación preparada sobre `develop` **98e8d8030f6ea5e9bee3360b28c86395f0abf28e**, Unity **6000.3.10f1**, escena existente `Assets/UPCH/Scenes/Campus.unity`. Fuente: las cinco láminas de `07. VETERINARIA 2025.pdf`, SHA256 `62d9c4020f69337efe58dc9378fc5729f3c63430d5f023301ac5f4b1c9478e22`.

El paquete incluye el prefab construido y sus mallas; no es necesario ejecutar el generador para obtener el edificio inicial. No contiene mobiliario. Los muros, vanos, pisos, columnas, cerramientos, cubiertas y circulaciones se agrupan por nivel. Incluye 3.000 aproximadamente piezas editables, no una caja exterior maciza.

## Instalar en el proyecto existente

1. Cierra Unity y extrae el ZIP en una carpeta externa al proyecto.
2. Ejecuta `Instalar_Veterinaria.ps1 -Proyecto "C:\ruta\upch-recorrido-virtual"`. El instalador copia únicamente los archivos listados, aplica cuatro modificaciones concretas y añade la instancia H a la escena existente. Conserva una copia anterior de Campus junto al instalador. Reconoce y actualiza los archivos sin editar de la entrega anterior de revisión del terreno, con respaldo. Si detecta otro archivo del paquete editado en destino, se detiene; si los bloques de la escena no coinciden, conserva la escena y permite usar la integración desde Unity.
3. Abre `Assets/UPCH/Scenes/Campus.unity` en Unity 6.3 LTS. Espera la importación y comprueba la consola. El edificio ya estará colocado si se pudo aplicar el parche.

Alternativa sin PowerShell: copia `Assets/UPCH/Veterinaria` con su archivo `.meta` y `Tools/Veterinaria` a las mismas rutas del proyecto. Abre Campus y ejecuta **Tools → UPCH → Veterinaria → 2 Integrar o actualizar en Campus**. Guarda la escena después de revisar los accesos. No arrastres el prefab a una posición aproximada.

El menú 1 regenera las mallas y el prefab desde los datos; no es necesario en la primera instalación. El menú 3 comprueba referencias y escala. La operación 2 desactiva la reserva H maciza, conserva el original y actualiza superficie y collider del terreno. Si otro trabajo cambió la malla del terreno, se detiene para no sustituirlo. No ejecutes la integración durante Play.

## Ubicación y niveles

Jerarquía: `Campus UPCH - Base exterior/Pabellon_H_Veterinaria`, con grupos `00_Estructura_General`, `01_Sotano` a `05_Azotea` y `06_Escaleras_Rampas`.

Posición global del objeto raíz: **(-8.720671, 1.17, 144.78705)**. Rotación **(0,0,0)**; escala **(1,1,1)**; una unidad = un metro. X/Z y orientación proceden de la reserva H existente. La elevación +1.17 es una inferencia de integración: hace coincidir la vereda NPT -1.17 de A-02 con Y=0 del campus; no procede de un levantamiento topográfico.

| Sector | NPT local | Y global |
| --- | ---: | ---: |
| Cuartos técnicos | -4.50 | -3.33 |
| Sótano | -3.55 | -2.38 |
| Vereda | -1.17 | 0.00 |
| Primer piso | 0.00 | 1.17 |
| Segundo piso | 3.55 | 4.72 |
| Tercer piso | 7.10 | 8.27 |
| Azotea | 10.70 | 11.87 |

La envolvente excavada tiene 981.80 m²; la intersección recortada en Site es 981.40 m². Se incluye el acceso exterior. `Site.asset` permanece intacto: el MeshFilter y el MeshCollider de Terreno utilizan `Terreno_Recortado_H.asset`. La reserva H original permanece desactivada. No se elimina todo el suelo del campus. El controlador del jugador conserva su altura real de cápsula 1.75 m, radio 0.25, escalón 0.20, pendiente 45° y velocidad existente.

## Fuente geométrica y cotas

Las plantas se registraron por columnas coincidentes; no se ajustaron a rectángulos ni se estiraron por planta. Origen arquitectónico: punto registrado del PDF (824.76,498.36). Conversión uniforme: 72/2.54 puntos PDF por metro. Registro A-01 (+36.12,+57.24), A-02 (+21.36,+0.60), A-03/A-04/A-05 (0,0). Los cerramientos se recuperaron de perfiles vectoriales, con revisión visual y distinción de mobiliario gris, proyecciones y simbología. El soldado de extremos de dibujo admite 0.22 puntos, unos 7.8 mm; la triangulación se prepara con precisión de 0.1 mm. Dos encuentros de anillos que se tocaban en un vértice se cerraron localmente en 0.6 mm para evitar aristas no manifold.

Las cadenas del plano muestran, entre otras, 43.73 m en el tramo posterior de A-01 y 49.07 m en A-02. La reconstrucción retiene los vectores registrados: no se ha ejecutado un ajuste completo de todas las cadenas a cotas numéricas. La envolvente completa incluye escaleras y salientes; su caja es mayor que esas cadenas. Consultar `Documentacion/Dimensiones.json` para las medidas obtenidas del modelo. No interpretar todas sus medidas como cotas confirmadas por el PDF.

## Parámetros estimados y observaciones abiertas

`Assets/UPCH/Veterinaria/Datos/Parametros_H.json`: losa 0.24 m; vano de puerta 2.15 m; antepecho 0.95 m; cabeza de ventana 2.50 m; cerramientos de azotea 2.60 m; peralte de viga 0.40 m; baranda general 1.10 m. Los muros terminan bajo las losas, no en el NPT superior. Las alturas explícitas de divisiones y parapetos se conservan en las piezas correspondientes. Las puertas se entregan abiertas, sin colisión de hoja; sus vanos sí están recortados. Alturas y materiales de fachada requieren elevaciones o inspección para confirmarse.

Conexiones construidas: escalera 03 occidental desde sótano hasta azotea; escalera 02 diagonal desde sótano hasta tercer piso; escalera 01 con tramo central primer-segundo y otro segundo-tercero. Los primeros peldaños rectos del sótano occidental se trazaron en A-01. Su continuación bajo la proyección y el empalme con el retorno se infirieron entre plantas; **esa conexión no se declara reproducción exacta**. Las contrahuellas se reparten entre NPT; los conteos y alzados necesitan sección o inspección. Las cajas/huellas no se deben certificar únicamente por la prueba de cápsula.

Rampa posterior: pendiente 8% indicada; extremos -3.55/-1.17, longitud 29.75 m y ancho 1.20 m son inferencias. Se construyó continuidad geométrica, pero falta comprobar el recorrido y correspondencia del arranque/desembarco. La conexión de seis escalones a bombas -4.50 es inferida. Los cuatro cerramientos de azotea siguen su posición en planta; altura y cobertura son estimaciones. No se modelaron equipos de cubierta.

## Archivos y regeneración

- `Assets/UPCH/Veterinaria/Prefabs/Pabellon_H_Veterinaria.prefab`: edificio construido reutilizable.
- `Generado/Mallas`: mallas cerradas de la arquitectura; `Generado/Terreno_Recortado_H.asset`: suelo derivado.
- `Datos/Modelo_H.json`: geometría, fuente y perfil vertical por pieza; `Parametros_H.json`: estimaciones editables.
- `Editor/GenerarVeterinaria.cs`: regeneración e integración, sin dependencias nuevas.
- `Editor/VeterinariaTerreno*.cs`: recorte, estado y pruebas de Editor.
- `Documentacion`: informes estáticos, matriz CSV y vistas de la geometría entregada. Las vistas no son capturas de Unity.
- `Tools/Veterinaria/Fuentes`: trazado vectorial y puertas, para reproducir la preparación.
- Único archivo previo modificado: `Assets/UPCH/Scenes/Campus.unity`. No se modificaron otros prefabs, materiales, meshes originales, ajustes globales ni jugador. Sin commits ni pushes.

En Unity: edita los parámetros estimados y usa el menú **1 Regenerar prefab del edificio**. Conserva los GUID de las mallas y el prefab, y las instancias mantienen su ancla. Usa el menú 2 si quieres restablecer el emplazamiento y el recorte. El recorte conserva su origen y no acumula vaciados. Para restaurar la plancha original existe la opción en **Revisar y recortar terreno**; no debe usarse mientras se pretenda acceder al sótano.

Preparación opcional en Python (no necesaria para abrir el edificio en Unity): instala `requirements.txt` en un entorno local y ejecuta `python Tools/Veterinaria/construir.py`. Para volver a extraer desde el PDF: `extraer_planos.py`, después `recuperar_perfiles.py`, después `extraer_puertas.py`, indicando la ruta del PDF. Los dos últimos usan los datos de Fuentes. `verificar.py` comprueba archivos serializados; `vistas_plantas.py` exporta plantas de la geometría. La nueva ejecución no duplica la instancia ni cambia bloques ajenos de la escena.

## Estado real de validación

Consulta `Assets/UPCH/Veterinaria/Documentacion/Verificacion_Estatica.json` y `Matriz_Verificacion.csv`. Se revisaron las cinco plantas y se ejecutaron controles matemáticos de índices, normales, cierre, duplicación exacta, NPT y referencias de mallas. Se comprobaron candidatos de obstáculo en los centros de huellas y vanos de puerta con dimensiones del jugador. En A-03 se conserva el corredor ante las aulas 203/204: la proyección del vacío superior no se convierte en un hueco de esa losa. Esto no garantiza todas las rutas ni la física del CharacterController. La comparación espacial con reservas generadas no sustituye revisar todas las ampliaciones de los vecinos en la escena ejecutada.

**No se pudo ejecutar Unity en este entorno. Compilación, importación, consola, pruebas EditMode y recorrido Play están pendientes.** El análisis sintáctico C# no equivale a compilación. No se declaran conformes esas pruebas ni la fidelidad de los elementos inferidos. Revisar primero ambos ingresos, las tres escaleras, la rampa y el acceso técnico, después las habitaciones, fachadas y bordes de vacíos. La matriz mantiene como Observado lo que no pudo contrastarse de forma suficiente.
