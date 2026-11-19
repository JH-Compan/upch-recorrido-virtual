# Pabellón H — revisión DWG, 18/11/2026

Actualización de la rama `feature/pabellon-h-veterinaria`, base `38a6b895e22e6a94eefedf66065cd0cd7260e70c`. Se modifica el edificio existente y su generador. Campus, el terreno recortado y su estado se conservan byte por byte. Sin commits ni pushes.

## Fuentes y decisiones

- DWG `07. VETERINARIA 2026.dwg`: SHA256 `d0693ddd0e2417eb647161808aa1f613e5b58272cfa1605fd8a86469d1bda46f`, AutoCAD AC1032.
- PDF `07. VETERINARIA 2025.pdf`: SHA256 `62d9c4020f69337efe58dc9378fc5729f3c63430d5f023301ac5f4b1c9478e22`.
- El DWG contiene ocho plantas enmarcadas, incluidas variantes inferiores. Se seleccionan las cinco de la fila superior que coinciden con A-01 a A-05 del PDF. Sus cartelas dicen OCTUBRE 2025; el nombre 2026 no demuestra una revisión arquitectónica posterior.
- `$INSUNITS=4` declara milímetros, pero puertas, crujías y cotas numéricas corresponden a metros: 0.80, 4.80, 49.067996. Se usa **1 unidad de dibujo = 1 metro**, sin escalar a 0.001.
- Registro CAD/PDF por perfiles coincidentes, solo traslación: residuos máximos por eje inferiores a 3.4 mm. Esto verifica el registro, no todas las dimensiones construidas ni cada cadena.
- Cotas CAD destacadas: A-01 43.732039 m; A-02 49.067996 m; A-03/A-04 46.253157 y 48.317826 m; A-05 46.229082 y 48.211912 m. Son segmentos acotados, no cajas envolventes intercambiables.

`Fuentes/CAD_H.json` conserva perfiles, cotas, rótulos, puertas y registro de las cinco plantas seleccionadas. No requiere AutoCAD para regenerar el edificio. El DWG se convirtió a DXF para leer entidades; el conversor, DXF y cachés no forman parte del repositorio.

## Reparaciones realizadas

Se reemplaza la extracción de cerramientos por capas CAD de muros, drywall, muros bajos y ventanas en sótano a tercer piso. Los perfiles abiertos se recuperan mediante pares de caras paralelas de su misma capa; no se importan mobiliario, cartelas ni símbolos exteriores a la envolvente. Se excluyen las marcas de corte de las escaleras de esa recuperación. Se conservan anotaciones verificables del PDF para distinguir divisiones H=1.60 y vidrio templado cuando la capa CAD no expresa su altura.

Las puertas recuperadas de CAD se concilian con los arcos PDF registrados; se recortan vanos y se conservan hojas abiertas sin collider. Hay puertas mantenidas desde PDF que requieren cotejo individual; la conciliación no es una aprobación de cada giro.

La escalera N.º 02 tenía invertidos ascenso y retorno: se corrige el sentido conforme a la numeración de huellas entre plantas. La llegada al tercer piso usa el tramo inferior izquierdo y conserva el tabique drywall del tramo superior derecho. El reparto vertical de contrahuellas sigue siendo una estimación entre NPT.

Se eliminan las falsas columnas de mobiliario en aulas. Se conserva el corredor ante aulas 203/204 bajo la proyección del vacío superior. Se añaden materiales exclusivos de H: hormigón beige, vidrio gris, carpintería oscura y zócalo rojizo, orientados por las fotografías; colores no medidos. Las caras exteriores se asignan por submallas, sin fachadas duplicadas. No se modifican materiales compartidos ni se añaden texturas o paquetes.

Azotea, contornos de losas, vacíos, accesos y geometría de circulación conservan trazado PDF documentado. **No se ha sustituido toda la geometría por una reconstrucción exacta desde DWG.** Los cuatro cerramientos de azotea mantienen geometría y alturas estimadas de la entrega anterior.

## Integración y regeneración

Jerarquía: `Campus UPCH - Base exterior/Pabellon_H_Veterinaria`. Escena: `Assets/UPCH/Scenes/Campus.unity`. Prefab: `Assets/UPCH/Veterinaria/Prefabs/Pabellon_H_Veterinaria.prefab`.

Raíz global **(-8.720671, 1.17, 144.78705)**, rotación (0,0,0), escala (1,1,1). X/Z provienen de la reserva existente. Y=1.17 es inferido para alinear vereda -1.17 con suelo del campus 0. No se ha desplazado el ancla.

NPT locales: sótano -3.55, primero 0, segundo +3.55, tercero +7.10, azotea +10.70; sectores técnicos -4.50. Unidades Unity en metros.

En Unity 6000.3.10f1, el prefab ya está construido. El menú **Tools → UPCH → Veterinaria → 1 Regenerar prefab del edificio** usa Modelo_H.json y conserva GUID. No es necesario volver a integrar o recortar el suelo para aplicar esta revisión. Parámetros estimados: losa 0.24 m; puerta 2.15; antepecho 0.95; cabeza de ventana 2.50; cubierta de cerramientos 2.60; viga 0.40; baranda general 1.10.

Preparación opcional: `python Tools/Veterinaria/construir.py --building-only`. Este modo conserva tanto Campus como el terreno probado; elimina exclusivamente mallas propias H_*.asset que ya no están referenciadas por el nuevo modelo. `verificar.py` revisa los assets serializados. `auditar_planos.py RUTA_PDF` genera superposición en Auditoria, excluida de Git. Las fuentes PDF y CAD JSON son necesarias para repetir la preparación; no borrarlas como si fueran temporales.

## Estado de validación

`Documentacion/Verificacion_Estatica.json` registra índices, cierre, normales, duplicados exactos, GUID, submallas/materiales, NPT y candidatos de obstáculo en centros de huellas y puertas. También comprueba que Campus y ambos assets del terreno coinciden con la base de esta actualización. La matriz CSV distingue Conforme de Observado.

Las vistas se generan desde la geometría entregada; **no son capturas de Unity**. La superposición es un detector de candidatos, no un porcentaje de fidelidad: sus puntos pendientes incluyen simbología, proyecciones, barandas y tramos que requieren cotejo. No se certifican todos los ambientes con una prueba de cobertura.

**Pendientes para cerrar al 100%:** cotejo individual de cadenas, muros bajos H=2.20 y asignación de alturas, puertas/vidrios; azotea; alzados de ventanas/fachada; conteos y secciones de las tres escaleras; empalme occidental del sótano bajo proyección; extremos de la rampa posterior y conexión técnica. Secciones o mediciones son necesarias para confirmar alzados. Unity no está instalado aquí: compilación, importación, consola, iluminación y recorrido con el jugador NO EJECUTADOS. No se ajustó el controlador para ocultar errores de geometría.

## Qué versionar

Solo los cambios de `Assets/UPCH/Veterinaria` y `Tools/Veterinaria`, incluidos sus .meta existentes/nuevos y las eliminaciones de mallas obsoletas. No subir el ZIP, el parche, el DWG/DXF de trabajo, conversores, cachés Python, Auditoria, Library, Temp ni Logs. No borrar manualmente mallas referenciadas ni sus .meta. El paquete de actualización se aplica desde fuera del repositorio; el parche decide altas, modificaciones y bajas.
