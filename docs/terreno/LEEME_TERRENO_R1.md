# Terreno Parque Central R1 - candidato revisable

## Qué actualiza

Esta primera versión incorpora al suelo una plataforma central a **+0,45 m**, la franja de vereda hacia H/I/J a **-0,34 m** y un eje de rampa norte al **8 %**. Se adopta como referencia de trabajo `0,00 del parque = Y 0 de Unity`. Se conserva la forma horizontal del terreno, incluidos sus vacíos existentes. Los edificios no se desplazan.

**Los otros empalmes se interpolan. Esta R1 no reproduce todavía los siete perfiles de rampa del plano ni todo el campus.** Las superficies ajardinadas mantienen su forma horizontal actual y su acabado; siguen siendo aproximaciones del modelo previo. La plataforma local a +1,40 m no se construye: su base queda dentro de la interpolación provisional, sin una losa elevada ni nuevas gradas. Los accesos propios de Medicina y CREA y la relación de sus datums requieren otra revisión.

## Procedencia y registro

- Fuente de niveles: `14. SOTANOS - 3ER SECTOR 2025.dwg`, planta Parque Central no incluida en las tres páginas del PDF homónimo.
- Se encontraron 549 coincidencias de vértices entre esa planta y el plano general. No son puntos topográficos únicos; varios pertenecen a las mismas entidades. El residuo máximo de esos emparejamientos es aproximadamente 0,00156 m.
- Traslación DWG 14 -> DWG general: X +234976,450445; Y +50270,233806.
- Registro del plano general con la malla de terreno existente: X -237832,701416; Z -51467,632531. La diferencia máxima de contorno es aproximadamente 0,028 m, coherente con la aproximación de la malla previa. Eso no certifica precisión topográfica del campus.
- El eje `B2E75` del plano general mide 9,875 m. Un descenso de 0,79 m en ese recorrido da 8 %. Ese perfil se impone como control; el resto no se anuncia como reconstruido exactamente.

`Control_Terreno_R1.json` conserva la trazabilidad del registro. Los anclajes de textos NPT no se han utilizado como una nube de puntos topográficos. La región alta de control es un rectángulo interior conservador entre límites de jardín/plaza del CAD, no el contorno completo definitivo del pavimento. Las máscaras de nivel cero conservan veredas y el enlace con el suelo anterior. Las fronteras restantes necesitan ajuste de líneas de quiebre.

## Aplicación en Unity

El instalador agrega archivos nuevos y no modifica las mallas originales ni la escena. Tras importarlos:

1. Abrir la escena **Campus** de la copia de trabajo actual.
2. Abrir **Tools > UPCH > Terreno > Parque Central R1**.
3. Leer el alcance y pulsar **Aplicar relieve R1 a la escena abierta**.
4. La herramienta comprueba geometría y transformaciones de los suelos antes de cambiar nada. Si encuentra una malla propia o una ubicación distinta, se detiene sin aplicar; esa copia requiere adaptar el registro. No regenerar terreno ni edificios para eludir esa comprobación.
5. Se actualizan las referencias de malla visual y de colisión del terreno. Los jardines, que antes no tenían collider propio, conservan esa condición; la colisión continúa en el suelo general. Los materiales y objetos se conservan.
6. Usar **Comprobar asignaciones de suelo y colisión**. En la base revisada se esperan ocho mallas reconocidas, cero incidencias y 83 muestras físicas de colisión. Ese resultado dentro de Unity está pendiente de ejecución.
7. Revisar visualmente y recorrer en Play la franja hacia H/I/J, los empalmes con el suelo anterior, el eje norte, los bordes de jardines y los accesos de sótano. **Guardar la escena solo después de revisarla.**

Se crea una copia del archivo de escena guardado en una carpeta de respaldo junto al proyecto. Si hay cambios sin guardar, permanecen en la escena y en Undo; no se afirma que estén incluidos en esa copia de disco. Se puede usar **Ctrl+Z** para deshacer la aplicación o **Restaurar las mallas anteriores** para volver a sus referencias originales. No se crean nuevos objetos de decoración o mobiliario ni se ajustan edificios automáticamente.

## Resultados y límites

- Nueve variantes de malla: dos alternativas del suelo general, con/sin recorte de LID, y siete superficies de jardín. Solo se asigna la alternativa que coincide con el suelo actual.
- Las nueve mallas son cerradas tras escribirlas y volver a leerlas como assets Unity. La triangulación cambia, pero sus dominios horizontales y los vacíos se conservan dentro de la tolerancia numérica documentada.
- Se verifica por rayos la superficie de colisión candidata sobre el eje norte y las dos zonas de control, además de muestras fuera del sector. Los resultados y las pendientes calculadas están en `Validacion_Terreno_R1.json`.
- El máximo de pendiente en zonas interpoladas puede superar el de las rampas rotuladas. Consultar `surface_slope_percentiles_90_95_99_max` en el informe. No es una validación de accesibilidad ni una certificación de que todos los recorridos cumplen esas pendientes.
- La escena, prefab de LID, terrenos originales, materiales y edificios se conservan. La aplicación en Unity cambia únicamente las referencias de las superficies reconocidas.
- No se ejecutaron Unity Editor, compilación C# ni Play en el entorno de preparación. Las comprobaciones estáticas no sustituyen ese recorrido.

## Reproducir el candidato

Se requieren las dependencias indicadas en `tools/terreno/requirements.txt` y el lector existente `tools/lid/unity_text.py`. Desde la raíz del repositorio:

```text
python tools/terreno/construir_parque_r1.py
python tools/terreno/validar_parque_r1.py
```

Los gráficos son controles numéricos del candidato; no son capturas del motor ni un levantamiento topográfico. Esta R1 es la primera fase del terreno, no el cierre de la reconstrucción altimétrica completa.
