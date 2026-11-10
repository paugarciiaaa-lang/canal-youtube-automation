# Caspitas — automatización de vídeos

Proyecto para producir documentales largos y Shorts derivados para el canal Caspitas.

## Calendario editorial

- Un documental nuevo cada día, programado para las 21:00 (Europe/Madrid).
- Cinco Shorts por documental.
- Los Shorts se publican durante cinco días consecutivos, uno por franja:
  - 12:00: documental más antiguo de la tanda, Short 1/2/3/4/5 según el día.
  - 14:00, 16:00, 18:00 y 20:00: documentales progresivamente más recientes.
- Rampa inicial: día 1 = 1 Short; día 2 = 2; día 3 = 3; día 4 = 4; desde el día 5 = 5 Shorts diarios.
- Zona horaria: Europe/Madrid.

## Cola de Shorts

La lógica está en `scripts/shorts_queue.py`. Mantiene cada documental y sus cinco Shorts, consulta qué pieza corresponde a una franja y permite marcarla como publicada para evitar duplicados.

Ejemplos:

```bash
python scripts/shorts_queue.py init
python scripts/shorts_queue.py add --video-id doc-001 --publish-date 2026-11-10 --short-paths out/doc-001-short-1.mp4 out/doc-001-short-2.mp4 out/doc-001-short-3.mp4 out/doc-001-short-4.mp4 out/doc-001-short-5.mp4
python scripts/shorts_queue.py due --date 2026-11-12 --slot 12:00
python scripts/shorts_queue.py mark --video-id doc-001 --short-number 3 --published-at 2026-11-12T12:00:00+01:00
```

Los vídeos deben estar generados y disponibles antes de su hora de publicación. La cola solo decide qué archivo corresponde a cada franja; la integración de renderizado y publicación se añade en las siguientes fases.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

El workflow de GitHub Actions ejecuta estas pruebas cuando cambia la cola.
