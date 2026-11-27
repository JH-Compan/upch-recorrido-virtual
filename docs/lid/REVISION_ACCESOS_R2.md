# LID R2 - accesos y estructura

Base: `feature/actualizacion-lid`, commit `5b47012fe5c0c453c0872a78857123d8b4698bf8`. Se usa el modelo nativo existente, sin regenerar el edificio.

## Cambios aplicados

1. **Escalera interior junto al ingreso:** el noveno peldaño del primer tramo tenía siete puntos de control con solo 1,42 m de altura libre, por un saliente del muro `LID_00086_Muro_Recuperado_10BBF4`. Se recorta únicamente ese saliente sobre el apoyo de la escalera. Se retiran aproximadamente 0,376 m³; el muro permanece bajo el intradós. Las dos hojas de escalera, descansos, puertas y losas mantienen sus posiciones. La profundidad de apoyo de 0,22 m sigue siendo una hipótesis del modelo, no una medida de corte arquitectónico.
2. **Pavimento auxiliar de la escena independiente:** se retira un solapamiento de 0,159632 m² con el contorno del vacío del sótano registrado desde el CAD. Se actualiza su malla compartida por representación y colisión. El pavimento general de revisión y el terreno de Campus ya respetaban el vacío; no se modifican.
3. Se añade el menú **Tools > UPCH > LID completo > Comprobar accesos y escaleras R2**. Comprueba peldaños y obstáculos por encima con los colliders de la escena abierta; así puede revelar una interferencia con el terreno local que no pertenezca al prefab. No crea objetos ni modifica la escena.

## Escaleras, entrada y niveles

Se conservan los arranques laterales desde NPT 0 y las conexiones de los pisos a +3,20, +6,40, +9,60 y +12,80 m. El ingreso principal mantiene sus doce posiciones numeradas, retorno inferior en L y descanso de 1,20 m. También permanecen el acceso auxiliar oeste, la escalera norte y el tramo interior. No se extrapolan todas las escaleras hasta la azotea ni se hace un desplazamiento global del edificio.

En Campus el sótano está a Y=-1,20 m porque la cota exterior +1,20 m del modelo se registró sobre el terreno Y=0. Estar bajo esa cota no prueba por sí solo que una escalera esté mal situada: hay que comprobar que su vacío y su llegada inferior están libres. En esta base de GitHub el terreno ya tiene el recorte. Si en otra copia un pavimento atraviesa el arranque, el nuevo menú permite identificar el collider antes de tocar la posición de la escalera.

## Comprobaciones ejecutadas

- 292 peldaños, 2.920 puntos de control por rayos verticales contra la geometría arquitectónica: 7 puntos bajo el umbral de 2,00 m antes y 0 después. La menor altura libre encontrada después es 2,67 m entre los rayos con techo detectado. El umbral es de revisión geométrica; no es una certificación normativa. No incluye el barrido completo de una cápsula, todos los descansos, los retornos en L sin nombre de peldaño o todas las poses de puertas.
- 544 anclajes horizontales de ventanas coinciden con las referencias del CAD a la precisión numérica de la serialización. Sus alturas no se certifican con este control; no se desplazan ventanas ni se cambian sus materiales.
- 22 secciones de muros/tabiques y 790 referencias de trazas de puertas pasan la comparación geométrica. Las referencias pueden repetirse y no equivalen a ese número de puertas únicas.
- Se conserva la referencia CAD de muros. El auditor resta de la sección esperada exclusivamente el prisma de intradós documentado por R2 a las alturas que lo atraviesan; no se excluye un recinto completo del control.
- Las dos mallas modificadas son cerradas después de escribir y volver a leer sus assets Unity.
- El prefab completo, todos sus fileID y transformaciones, todas las mallas de peldaños y ventanas, las losas, la escena Campus, el terreno de Campus y los materiales originales mantienen su contenido. Solo cambian dos mallas existentes, metadatos/documentación y herramientas de revisión.

Los resultados están en `Assets/UPCH/LIDCompleto/Documentacion/Revision_Accesos_R2.json`, `Validacion_Accesos_R2.json`, `Validacion_Ventanas_R2.json` y `docs/lid/validacion_actual.json`.

## Fuentes y límites

Los adjuntos `11. PAB. LID 2026(4).pdf` y `.dwg` coinciden por hash con las fuentes registradas. Se inspeccionaron las cinco plantas del PDF y se convirtió el DWG para cotejar trazas del ingreso; la conversión puede omitir datos dinámicos de AutoCAD y no constituye certificación integral del DWG.

El PDF no contiene cortes arquitectónicos verticales. Permanecen provisionales el terreno exterior +1,20 m, las alturas de vanos no acotadas, espesores y el apoyo de 0,22 m. No se reconstruyeron retranqueos de fachada o geometría de muros sin evidencia dimensional suficiente. No se añadieron mobiliario, decoración, personas, vegetación ni equipos.

No se ejecutaron Unity Editor, compilación C#, PowerShell ni Play en este entorno. El control geométrico no sustituye recorrer todas las escaleras ni verificar el acceso con el jugador. El gráfico incluido es una sección técnica calculada de las mallas, no un corte del proyecto arquitectónico original.

## Revisión en Unity

Tras aplicar el paquete con Unity cerrado, abrir `Assets/UPCH/Scenes/Campus.unity`. Ejecutar el menú nuevo R2 fuera de Play. Revisar también la escena `Assets/UPCH/LIDCompleto/Scenes/LID_Revision_Completa.unity`. Recorrer entrada principal y auxiliar, interior, norte y ambas laterales hasta sus llegadas de sótano. Comprobar el nuevo intradós desde la escalera y desde el recinto contiguo. No regenerar ni integrar otra instancia del edificio para aplicar esta actualización.
