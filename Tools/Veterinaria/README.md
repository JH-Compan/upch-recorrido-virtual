# Pabellon H - R7_Fidelidad_Fotografica

Base: copia local R6 capturada el 19/11/2026 a las 22:40, HEAD e96563c5. Se corrigen fuentes del generador y Modelo_H.json; regenerar el prefab en Unity es obligatorio. Esta revision incorpora las fotografias reales del usuario del 21/11/2026 y conserva los perfiles horizontales CAD, NPT, ancla y escala.

Cambios actuales:
- 36 vanos altos recuperados de 74 trazos CAD agrupados; vidrio, marcos y corte del muro. No son 74 ventanas. Cotas 2.05/2.70 estimadas.
- Fachada hacia la calle: nueve modulos de celosia horizontal de concreto, sobre la alineacion CAD. La correspondencia entre modulos de A-02/A-03, cotas 0.15/3.05, paso aproximado 0.23 y secciones son interpretaciones de las fotos, no un levantamiento metrico.
- Modulo central de ventana antes oculto por el muro exterior: se corrige el plano de acristalamiento en segundo/tercer piso a partir de los modulos contiguos y fotos. La forma en L del simbolo ya no se extruye como vidrio interior.
- Escalera curva: antepechos exteriores macizos de concreto siguiendo huellas y arco CAD; pasamanos interiores conservados. Altura 1.10 y espesor 0.12 m estimados. No se cambia la numeracion ni las cotas de los escalones.
- Nucleo oriental: antepechos opacos sobre cuatro perfiles CAD, en lugar de barandales metalicos que no coincidian con las fotos. Las aberturas superiores siguen abiertas.
- Ventanas ordinarias: antepecho 0.70 y cabeza 2.90 m estimados para aproximar las proporciones observadas; reemplazan los antiguos valores estimados 0.95/2.50. Es una aproximacion visual pendiente de alzado medido.
- Puertas: 161 hojas cerradas en Edit, con marcos completos y material propio. En Unity, el regenerador anade VeterinariaDoor y collider convexo a cada hoja: abre al acercarse una camara de juego y cierra tras alejarse. El giro usa las bisagras y sentido CAD. La apertura automatica es una adaptacion del recorrido virtual, no una afirmacion sobre el mecanismo del edificio real.
- Asociacion de cotas: se incorpora 0.95 m como ancho valido y se corrige la cota del cuarto de maquinas de A-01 (5D71A), que antes se confundia con la del S.H. contiguo. No se declara revisado metrologicamente cada vano.
- Marcos fijos consolidados por nivel, UV de caras verticales corregidas y tono del concreto ajustado a las fotografias. Las mallas H_ obsoletas se eliminan solo despues de guardar el prefab.
- Validador de Unity: contrasta vertices y transformaciones de grupos contra el modelo, detecta colliders ausentes y comprueba componentes de puertas. Ejecutar menu 3 fuera de Play.

El instalador prepara datos y codigo; NO copia las mallas serializadas offline ni el prefab de inspeccion. En Unity: Tools / UPCH / Veterinaria / 1 Regenerar prefab del edificio; luego 3 Comprobar referencias y escala en Edit. No reintegrar ni recortar terreno. Scene Campus, terreno, jugadores y otros edificios se conservan.

Verificacion offline: cierre de mallas Float32, normales, indices/materiales, superficies coincidentes, cobertura declarada de pisos y trayectos con radio 0.25 / altura 1.75 m. Las rutas incluyen la colision de hojas en su pose abierta; dos pasos requieren giro alrededor de una hoja vecina. No se simula la transicion de apertura, CharacterController ni XR. Sintaxis C# no equivale a compilar en Unity. Las vistas externas usan iluminacion de inspeccion y no son capturas de Play.

Pendientes: importar/compilar y recorrer en Unity PC/XR; confirmar alturas y perfiles estimados; cotas de extremos y uso de rampa posterior; cubierta y continuacion superior de escalera cuando no sean visibles en las fotos. No se declara fidelidad del 100 por ciento.

## Fuentes

- PDF `07. VETERINARIA 2025(3).pdf`: SHA256 `62d9c4020f69337efe58dc9378fc5729f3c63430d5f023301ac5f4b1c9478e22`.
- DWG `07. VETERINARIA 2026(2).dwg`: SHA256 `d0693ddd0e2417eb647161808aa1f613e5b58272cfa1605fd8a86469d1bda46f`.
- Son idénticos a los archivos originales ya contrastados. El DWG AC1032 contiene ocho plantas enmarcadas: se usan las cinco superiores coincidentes con A-01 a A-05 del PDF; no las variantes inferiores. Las cartelas dicen OCTUBRE 2025: el nombre 2026 no demuestra una revisión posterior.
- `$INSUNITS=4` declara milímetros, pero las cotas y geometría corresponden a metros (0.80, 4.80, 49.067996). Se conserva una unidad = un metro, sin aplicar escala 0.001.
- Registro CAD/PDF por traslación y perfiles coincidentes, con residuos máximos por eje inferiores a 3.4 mm; no equivale a comprobar todas las cotas. Cadenas destacadas: A-01 43.732039; A-02 49.067996; A-03/A-04 46.253157 y 48.317826; A-05 46.229082 y 48.211912 m. No confundir esos segmentos con una caja envolvente común.

`Fuentes/CAD_H.json` conserva capas, cotas, puertas, registros y los tramos de escalera por planta. El DXF de lectura, conversores y cachés se mantienen fuera del repositorio. Unity no necesita AutoCAD, Python ni paquetes adicionales para abrir o regenerar el prefab desde Modelo_H.json.

## Cambios conservados de R2

Muros, drywall y cerramientos de sótano a tercero proceden de capas CAD y pares de caras recuperados, con exclusión de mobiliario/cartelas. Cuarenta y cuatro perfiles con antepecho y trazos de ventana se reconstruyen con vidrio, dintel y marcos; el marco intermedio usa divisiones dibujadas, no un patrón uniforme. Se concilian puertas con cotas y perfiles y se corrigen accesos dobles de sótano/Lavado. Las falsas puertas hacia el vacío posterior de SSHH A-03/A-04 se restituyen como ventanas, sin rellenar el vacío.

Se corrigen solapes parciales de vigas, dinteles y llegada central; se separan hojas abiertas de las caras del muro. Se añaden pasamanos al ingreso principal sustentados por fotografías. Se usan materiales locales beige, vidrio gris y carpintería oscura. Los marcos están consolidados por nivel y perfil vertical; el generador elimina mallas propias H_ obsoletas. No se modifican materiales compartidos, jugador u otros edificios.

## Corrección R3 de la escalera 02

La caja y las huellas no se repiten automáticamente desde A-03:

| Conexión | Fuente de subida / retorno | Contrahuellas por numeración | Altura calculada |
| --- | --- | --- | --- |
| Sótano - primero | A-01 1..10 / A-02 11..19 | 19 = 10 + 9 | 0.186842 m |
| Primero - segundo | A-02 20..29 / A-03 30..39 | 20 = 10 + 10 | 0.177500 m |
| Segundo - tercero | A-03 40..49 / A-04 50..59 | 20 = 10 + 10 | 0.177500 m |

El tramo del sótano conserva vectores de aproximadamente 1.719 m, consistentes con la cota redondeada 1.72 m; los superiores conservan sus aproximadamente 1.20 m. No se estira el modelo para uniformarlos. Las huellas nativas tienen paso longitudinal cercano a 0.275 m. La llegada y el primer borde del descanso aportan la última contrahuella, sin sólidos duplicados. Los huecos de losas se ajustan a las cajas correspondientes; las uniones con el hall mantienen apoyo.

Se usa el arco CAD R1.48 de las plantas relacionadas. Dos filas del sótano están ocultas tras el corte: se prolongan con el paso mediano de las ocho visibles. Cinco filas de subida A-02 están ocultas: se registran desde A-03 contra sus cinco filas visibles. **Esas siete filas son inferidas por continuidad entre plantas, no medidas directamente en su lámina.** El reparto uniforme de alturas sigue siendo una hipótesis constructiva entre NPT y numeración; falta sección para certificar el alzado.

Un perfil en C de A-01, situado junto al corte de la escalera, se estaba extruyendo como pared de habitación de altura completa. Se reclasifica como perfil de corte de la rampa/caja y se conserva su huella como borde/cerramiento bajo hasta el intradós calculado del descanso, junto a la geometría cerrada de escalera. Esa altura es inferida; no se elimina la delimitación en planta. **La clasificación es una inferencia geométrica**, documentada con su máscara y la superposición de detalle. No se desplaza el muro exterior paralelo de los ambientes. Espesor de escalera 0.20 m estimado: supera la contrahuella máxima y evita juntas suspendidas de la solución anterior de 0.18 m.

R3 encuentra ruta estática también en el descanso de sótano que R2 mantenía observado. No se elimina la observación histórica de la entrega R2: se sustituye su geometría y se ejecutan de nuevo las comprobaciones. La clasificación constructiva y los alzados conservan incertidumbre.

## Emplazamiento y parámetros

Jerarquía existente: `Campus UPCH - Base exterior/Pabellon_H_Veterinaria`. Escena `Assets/UPCH/Scenes/Campus.unity`; prefab `Assets/UPCH/Veterinaria/Prefabs/Pabellon_H_Veterinaria.prefab`.

Raíz (-8.720671, 1.17, 144.78705), giro (0,0,0), escala (1,1,1). X/Z provienen de la reserva; Y=1.17 es inferido para que vereda -1.17 coincida con suelo del campus 0. No se cambió el ancla.

NPT locales: -3.55, 0, +3.55, +7.10, +10.70; técnicos -4.50. Estimaciones: losa 0.24; puerta 2.15; antepecho 0.95; cabeza de ventana 2.50; cerramiento de azotea 2.60; viga 0.40; baranda general 1.10; escalera02 0.20 m. Vidrio 12 mm y marcos 45 x 56 mm estimados. Alturas generales editables en Parametros_H.json; espesores y perfiles fijos de preparación requieren reconstrucción Python o edición de mallas. No afirmar que cada detalle fijo se actualiza cambiando un parámetro de Editor.

Azotea y parte de contornos/accesos conservan trazado PDF e inferencias anteriores; la huella posterior de rampa se actualizó desde CAD. No se han convertido todas esas piezas en una reconstrucción exacta desde DWG. El empalme occidental del sótano, cubierta/altura de cerramientos de azotea y extremos de la rampa mantienen observaciones arquitectónicas.

## Regenerar y verificar

El prefab ya está construido. En Unity 6000.3.10f1: menú **Tools / UPCH / Veterinaria / 1 Regenerar prefab del edificio**. Conserva GUID y elimina únicamente mallas H_ obsoletas después de guardar. El menú 3 debe mostrar `R5_Envolvente_Exterior` en la consola. No volver a recortar el suelo ni integrar para aplicar esta revisión.

Preparación opcional (Python: instalar requirements.txt, incluida manifold3d; no añade dependencias a Unity): `python Tools/Veterinaria/construir.py --building-only`, conservando Campus y terreno. `verificar.py` inspecciona assets, NPT, referencias, cierre, normales, submallas y caras opacas coplanares en cualquier orientación. `validar_recorridos.py` ensaya puertas +/-0.45 m, tramos, accesos/desembarcos de escalera02, apoyo/intradós por rayos y rutas conservadoras en siete descansos con radio 0.25, altura 1.75 y grilla 0.05 m. No simula CharacterController ni todas las trayectorias por los ambientes.

Consultar Verificacion_Estatica.json, Verificacion_Recorridos.json y la matriz CSV. Las vistas se generan de la geometría y no son capturas de Unity. La superposición automática detecta candidatos, no un porcentaje de fidelidad: también señala símbolos y el perfil de corte reemplazado por la escalera.

**Unity no está instalado aquí. Compilación, importación, consola, iluminación y recorrido Play NO EJECUTADOS.** La sintaxis C# y los controles geométricos no sustituyen esas pruebas ni certifican el 100% arquitectónico. Mantener pendientes los detalles inferidos y el cotejo individual de cada ambiente/abertura.

## Archivos de la rama

Solo versionar los cambios de `Assets/UPCH/Veterinaria` y `Tools/Veterinaria`, con sus .meta y bajas de mallas obsoletas. Conservar ZIP, instalador, parches, sus listados y vistas de revisión fuera del repositorio. No subir DWG/DXF de trabajo, conversores, Auditoria, __pycache__, Library, Temp o Logs. No borrar manualmente archivos referenciados o fuentes JSON.
