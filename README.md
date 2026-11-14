# Caspitas — automatización de vídeos

Proyecto para producir documentales largos y preparar la futura distribución de Shorts del canal Caspitas.

## Calendario editorial previsto

- Un documental nuevo cada día, con objetivo de publicación a las 21:00 (Europe/Madrid).
- Cinco Shorts por documental.
- La cola prototipo actual utiliza cinco franjas (12:00, 14:00, 16:00, 18:00 y 20:00); no coincide con el horario final solicitado de 22:00 y debe rediseñarse antes de activarse.
- Rampa inicial: día 1 = 1 Short; día 2 = 2; día 3 = 3; día 4 = 4; desde el día 5 = 5 Shorts diarios.
- Zona horaria: Europe/Madrid.

## Fábrica continua de temas actuales
- Estrategia de generación continua, actualización diaria, efemérides, verificación de novedades y antirrepetición: `docs/topic_factory_currentness.md`.
- Los 31 temas iniciales son solo una semilla; la futura fábrica deberá generar nuevos candidatos y elegirlos según su relevancia comprobada para la fecha de publicación en `Europe/Madrid`.
- Antes de programar cada episodio, volverá a comprobar el estado del caso y las fuentes. Si no hay actualidad fiable, elegirá un tema evergreen sin inventar una conexión con el día.

## Generación actual

El workflow `.github/workflows/generar-video.yml`:

- Se ejecuta manualmente o mediante el horario diario de GitHub Actions.
- Comprueba la hora local para evitar ejecutar dos veces el mismo día por el cambio horario.
- Fija MoneyPrinterTurbo en la versión `v1.3.10` para evitar cambios inesperados de `main`.
- Usa caché de dependencias Python.
- Genera guiones en español de España con una estructura documental y una guía editorial que separa hechos, hipótesis y especulación.
- Intenta Gemini 3.5 Flash Lite y después Gemini 3.8 Flash; si ambos fallan o generan un vídeo demasiado corto, recurre a OpenRouter.
- Comprueba el MP4 y su duración tras cada intento antes de darlo por válido, evitando aceptar vídeos incompletos o de menos de 9 minutos.
- Da hasta 150 minutos a cada intento de proveedor y hasta 180 minutos al trabajo completo, con registro de errores.
- Usa Pixabay para materiales visuales y la voz española masculina `es-ES-AlvaroNeural` mediante Edge TTS.
- Aumenta el tiempo límite de concatenación de FFmpeg y permite procesar dos clips simultáneamente para reducir el cuello de botella del montaje.
- Comprueba que el MP4 exista y dure al menos 10 minutos; el objetivo editorial actual es de 14-17 minutos.
- Guarda el vídeo y los datos básicos como artefacto de GitHub Actions durante 14 días.
- Incluye un catálogo inicial de 31 temas y mantiene un historial para evitar repetirlos hasta agotar la lista.

Los secretos requeridos se configuran en GitHub Actions como `GEMINI_API_KEY` y `PIXABAY_API_KEY`. No deben guardarse en el repositorio ni compartirse en conversaciones.

## Estado de automatización

La generación del documental largo está configurada, pero debe superar pruebas reales de calidad y estabilidad antes de considerarse lista para producción.

La cola de Shorts está implementada como lógica de planificación, pero todavía no genera automáticamente los cinco clips, no conserva sus archivos de vídeo y no los publica. La publicación automática del documental largo en YouTube también permanece desactivada.

## Cola de Shorts

La lógica está en `scripts/shorts_queue.py`. Mantiene cada documental y sus cinco Shorts, consulta qué pieza corresponde a una franja y permite marcarla como publicada para evitar duplicados.

Ejemplos:

```bash
python scripts/shorts_queue.py init
python scripts/shorts_queue.py add --video-id doc-001 --publish-date 2026-11-10 --short-paths out/doc-001-short-1.mp4 out/doc-001-short-2.mp4 out/doc-001-short-3.mp4 out/doc-001-short-4.mp4 out/doc-001-short-5.mp4
python scripts/shorts_queue.py due --date 2026-11-12 --slot 12:00
python scripts/shorts_queue.py mark --video-id doc-001 --short-number 3 --published-at 2026-11-12T12:00:00+01:00
```

Los vídeos deben estar generados y disponibles antes de su hora de publicación. La cola solo decide qué archivo corresponde a cada franja; la integración de renderizado y publicación se añade en fases posteriores.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

El workflow de GitHub Actions ejecuta las pruebas de la cola cuando cambia ese código.

## Protección de monetización y calidad editorial

La política completa está en [MONETIZATION_POLICY.md](MONETIZATION_POLICY.md). El prompt de generación exige investigación contrastable, separación de hechos e hipótesis, referencias, análisis original, recursos visuales específicos y tratamiento documental respetuoso de tragedias. La música permanece desactivada.

**Riesgos pendientes:** el pipeline no verifica de forma independiente cada fuente; no crea todavía un inventario completo de licencias por clip; y la autorización comercial de Edge TTS no está confirmada. Por tanto, no puede certificar que un vídeo sea monetizable. Cada ejecución debe mostrar estos puntos como revisión pendiente.

Referencias oficiales: [políticas de monetización de YouTube](https://support.google.com/youtube/answer/1311392), [contenido adecuado para anunciantes](https://support.google.com/youtube/answer/6162278) y [licencia de Pixabay](https://pixabay.com/service/license-summary/).
