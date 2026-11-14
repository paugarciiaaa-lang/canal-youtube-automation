# Fábrica continua de temas actuales — Caspitas

## Objetivo
Mantener una fuente renovable de temas para el canal de misterios, desapariciones, enigmas históricos y sucesos inexplicables. La fábrica no debe depender de una lista cerrada: genera candidatos nuevos bajo demanda y selecciona el que tenga mejor encaje para la fecha real de publicación.

La actualidad nunca justifica presentar rumores como hechos ni forzar una conexión temporal. Si no hay una novedad verificable, se elige un caso evergreen con un ángulo documental oportuno.

## Fuentes de actualidad que debe revisar antes de cada publicación
1. Novedades verificables de casos abiertos: comunicados policiales, judiciales, forenses, archivos oficiales y declaraciones identificables de familiares o representantes cuando proceda.
2. Hallazgos recientes: nuevas identificaciones, análisis científicos, documentos desclasificados, expediciones, descubrimientos arqueológicos o revisiones históricas.
3. Efemérides: aniversarios de desapariciones, hallazgos, investigaciones, expediciones, juicios, descubrimientos y acontecimientos históricos que caigan cerca de la fecha prevista de publicación.
4. Actualidad cultural o científica relacionada con el misterio: solo si aporta contexto real y no convierte una ficción o tendencia en evidencia.
5. Temporada y calendario: verano, invierno, vacaciones, Halloween u otras fechas solo cuando la conexión con el caso sea natural y no oportunista.

Priorizar fuentes primarias y medios reconocidos que enlacen a documentos o declaraciones originales. Registrar URL, fecha de publicación, fecha del hecho y fecha de consulta. No usar snippets o titulares aislados como prueba.

## Criterio de actualidad y adecuación diaria
Para cada fecha de publicación:
- Calcular la fecha local de publicación en Europe/Madrid, no la fecha UTC del runner.
- Buscar novedades publicadas recientemente y comprobar que siguen vigentes en la fecha prevista.
- Revisar efemérides en una ventana razonable alrededor del día de publicación (por defecto ±7 días).
- Diferenciar claramente la fecha de publicación de una noticia, la fecha del acontecimiento y la fecha en que se confirmó.
- Comprobar que el asunto sigue siendo relevante y que no hay una actualización posterior que cambie la historia.
- Si una noticia ha quedado desmentida, superada o corregida, no usarla como gancho.
- No fabricar urgencia: si no existe un vínculo sólido con el día, seleccionar un tema evergreen y explicar su relevancia por su valor histórico, documental o por una pregunta que siga abierta.
- Evitar temas que dependan de especulaciones recientes, rumores de redes, teorías conspirativas o contenido viral sin corroboración.

## Pilares temáticos
1. Desapariciones y personas no localizadas.
2. Casos criminales históricos y misterios sin resolver, tratados con respeto.
3. Expediciones perdidas, naufragios, accidentes y supervivencia.
4. Enigmas arqueológicos, históricos y documentos misteriosos.
5. Fenómenos naturales o científicos mal explicados en su momento.
6. Señales, transmisiones, tecnología y sucesos documentados.
7. Lugares, estructuras y objetos con historias verificables.
8. Nuevos hallazgos, reaperturas y avances de investigaciones.
9. Efemérides y aniversarios con documentación contrastable.
10. Mitos populares: qué está documentado y qué se ha exagerado.

## Generación continua y antirrepetición
- Generar lotes de propuestas nuevos cuando la cola baje del umbral configurado; la lista inicial de 31 temas es solo una semilla.
- Mantener un colchón recomendado de 30 temas investigables y generar nuevas propuestas cuando queden menos de 15.
- Cada propuesta debe incluir ID, título, caso/acontecimiento, pregunta central, pilar, ángulo original, relación con la fecha, consultas de investigación, fuentes candidatas, riesgos de desinformación y estado.
- Comparar el concepto, protagonistas, cronología y pregunta central con todos los temas usados y pendientes. No basta con comparar títulos.
- No repetir el mismo caso con un título distinto salvo que exista una novedad material o un enfoque claramente diferente, documentado y aprobado.
- Rotar pilares para evitar una sucesión monótona de desapariciones o crímenes.
- Guardar para siempre el historial de temas publicados, descartados y aplazados, junto con la razón.
- Si la actualidad ofrece una novedad sustancial de un caso ya tratado, crear una actualización identificada como tal y enlazarla con el episodio anterior; no fingir que es un caso nuevo.

## Puntuación editorial por tema
Valorar cada candidato en:
- Actualidad verificable para la fecha (novedad o efeméride).
- Calidad y proximidad de las fuentes.
- Interés narrativo y claridad de la pregunta central.
- Diferenciación frente a vídeos anteriores y competencia.
- Disponibilidad de imágenes, mapas, documentos y recursos visuales pertinentes con derechos revisables.
- Riesgo de especulación, daño, privacidad o tratamiento irrespetuoso.

La actualidad suma puntos, pero nunca compensa la falta de pruebas. Un caso evergreen bien documentado puede ganar a una noticia reciente débil.

## Flujo de estados
`candidate -> freshness_checked -> screened -> queued -> researching -> fact_checked -> scripted -> produced -> scheduled -> published`

Estados alternativos: `duplicate`, `stale`, `needs_primary_source`, `misleading_angle`, `on_hold`, `rejected`.

Un tema no puede pasar a guion si no existe una ficha de investigación con fuentes comprobadas. Un tema de actualidad debe volver a comprobarse antes de programar el vídeo, porque la información puede cambiar entre la selección y la publicación.

## Ficha mínima por candidato
- `id`
- `working_title`
- `case_or_event`
- `central_question`
- `pillar`
- `distinctive_angle`
- `publication_date_local`
- `timeliness_type` (breaking_update, recent_discovery, anniversary, seasonal, evergreen)
- `timeliness_reason`
- `event_date`
- `sources` (URL, publisher, published_at, event_date, checked_at, source_type)
- `related_topic_ids`
- `evidence_gaps`
- `status`
- `used_in_video_id`

## Revisión final previa a publicación
En el mismo día de programación:
1. Reabrir las fuentes clave y buscar actualizaciones o rectificaciones.
2. Verificar nombres, fechas, cifras, estado del caso y afirmaciones del guion.
3. Confirmar que el título y la miniatura no exageran lo que se sabe.
4. Separar hechos confirmados, hipótesis, testimonios y rumores.
5. Si una novedad cambia sustancialmente el relato, detener la programación y corregir el episodio.
6. Conservar las URLs y fechas de consulta en el paquete de producción.

## Regla de la fábrica
La fábrica debe tener siempre nuevas ideas, pero no tiene que publicar una novedad diaria a cualquier precio. La prioridad es: exactitud documental, relevancia para la fecha, originalidad y calidad narrativa. No inventar actualidad ni declarar que un caso está resuelto o abierto sin comprobar su estado a la fecha de publicación.
