# Caspitas — automatización de vídeos

Proyecto para producir documentales largos y preparar la futura distribución de Shorts del canal Caspitas.

## Calendario editorial previsto

- Un documental nuevo cada día, con objetivo de publicación a las 21:00 (Europe/Madrid).
- Cinco Shorts por documental.
- Los Shorts se distribuyen durante cinco días consecutivos, en las franjas de 12:00, 14:00, 16:00, 18:00 y 20:00.
- Rampa inicial: día 1 = 1 Short; día 2 = 2; día 3 = 3; día 4 = 4; desde el día 5 = 5 Shorts diarios.
- Zona horaria: Europe/Madrid.

## Generación actual

El workflow `.github/workflows/generar-video.yml`:

- Se ejecuta manualmente o mediante el horario diario de GitHub Actions.
- Comprueba la hora local para evitar ejecutar dos veces el mismo día por el cambio horario.
- Fija MoneyPrinterTurbo en la versión `v1.3.10` para evitar cambios inesperados de `main`.
- Usa caché de dependencias Python.
- Genera guiones en español de España con una estructura documental y una guía editorial que separa hechos, hipótesis y especulación.
- Intenta Gemini 3.8 Flash y recurre a Gemini 3.7 Flash si el primer modelo falla.
- Aplica límite de tiempo a cada intento y registra el resultado.
- Usa Pixabay para materiales visuales y la voz española masculina `es-ES-AlvaroNeural` mediante Edge TTS.
- Comprueba que el MP4 exista y que dure al menos 8 minutos; avisa si se aleja del objetivo de 9-15 minutos.
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
