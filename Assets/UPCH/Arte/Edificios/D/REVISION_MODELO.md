# Pabellón D — revisión de distribución

Fuentes: láminas A-01 a A-07 de `04. ROGER GUERRA-ENFERMERIA 2026.pdf`, y fotografías locales de referencia IMG_1137 e IMG_1140 procedentes de la carpeta compartida.

El prefab conserva su GUID y emplazamiento en Campus. La entrada mira a +X. El trazado usa coordenadas digitalizadas de las imágenes de las plantas: no constituye una restitución métrica exacta ni un modelo BIM.

Se reemplazó el núcleo macizo por cerramientos, dos escaleras de doble tramo y dos pozos independientes de ascensor con puertas de piso y cabinas estáticas en planta baja. Los ascensores no incluyen movimiento ni interacción. Las losas dejan huecos en la circulación vertical. Se diferenciaron aulas (pisos 2/3), simulación (4) y oficinas (5/6).

El modelo todavía simplifica carpinterías, equipamiento, sanitarios, rampas de estacionamiento, geometría curva de las escaleras, contorno oblicuo del lado sur y detalles de fachada. La planta baja es una interpretación aproximada. Deben contrastarse estas partes antes de considerar la réplica terminada.

Generación: `UPCH.Enfermeria.Editor.ReconstruirEnfermeria.Run`. Reemplaza la geometría del prefab: guardar copia antes de ejecutarlo sobre ediciones manuales. La herramienta comprueba dimensiones positivas y sólidos idénticos duplicados; no sustituye una comprobación integral de intersecciones ni un recorrido VR.

Visualización: abrir Campus y usar Tools > UPCH > Ver pabellon D - Enfermeria.

## Corrección de descansos y cerramientos

La escalera 3 ahora desembarca por el extremo sur, junto al hall, con el descanso de piso de ancho completo incluido en la losa. Se quitaron las plataformas superpuestas. Se comprobaron por intersección de rayos con los colliders 108 puntos de apoyo en los descansos y 144 peldaños principales de los seis niveles.

Se añadieron cierres junto a las escaleras, al lateral de los ascensores y en los extremos de la fachada, además de un cerramiento con antepecho y ventana en el hall oeste. Esta ventana es un cierre provisional del encuentro con el puente al pabellón C; el puente entre pabellones requiere coordinación con la escena Campus. La fachada usa un material de vidrio nuevo (el material anterior se conserva), fijaciones, barandas interiores y una escalinata ancha con pasamanos. Se separaron los remates que compartían plano con losas y pilares para eliminar el parpadeo visible.

Las comprobaciones de apoyo no equivalen a una prueba de navegación con el controlador VR. Las cabinas continúan estáticas; la rampa curva y el paisajismo de las fotografías aún no están modelados.

## Corrección de puertas y fondo de planta baja

Se cerraron las aberturas indebidas del muro oeste de la escalera 3 y del muro este de los servicios higiénicos: estos cerramientos separan los núcleos de las aulas vecinas. Las hojas se colocan después de generar todos los tabiques. La herramienta prueba sentidos de apertura y bisagras, comprueba intersecciones de cada hoja contra todos los sólidos y contra las demás hojas, y exige que el centro de cada vano quede despejado. Las puertas de cabinas sanitarias priorizan la apertura hacia el interior de la cabina.

La zona posterior de A-01 se representa con una losa inclinada de rampa al 14,5 %, separada del pasillo y de la franja de servicios mediante cerramientos. Se completa el cerramiento exterior norte que había quedado abierto. La conexión completa con el estacionamiento subterráneo sigue fuera del alcance de este prefab.

Validaciones añadidas: hojas sin penetraciones, vanos despejados, antiguos pasos laterales sellados en cada planta, cerramientos del fondo de planta baja y soporte de suelo en la franja de servicios y el pasillo posterior.
