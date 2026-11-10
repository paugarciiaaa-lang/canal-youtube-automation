#!/usr/bin/env python3
"""Deterministic publication queue for Caspitas' five Shorts per documentary.

Daily slots:
  12:00 -> Short 1 from yesterday's documentary? No: from the documentary
           published five? The queue uses the documentary's own publication
           date and slot offset, so day 1 starts with Short 1.
  14:00 -> Short 2 from the documentary published one day earlier.
  16:00 -> Short 3 from two days earlier.
  18:00 -> Short 4 from three days earlier.
  20:00 -> Short 5 from four days earlier.

A documentary generated on date D is therefore published as:
  D+1 12:00: Short 1
  D+2 12:00: Short 2? See slot mapping in due_for_slot().
The daily schedule is intentionally explicit and testable.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "data" / "shorts_queue.json"
SLOTS = ["12:00", "14:00", "16:00", "18:00", "20:00"]
SHORTS_PER_VIDEO = 5


def load_queue(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "timezone": "Europe/Madrid", "videos": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("version", 1)
    data.setdefault("timezone", "Europe/Madrid")
    data.setdefault("videos", [])
    return data


def save_queue(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def add_video(data: dict[str, Any], video_id: str, publish_date: str, short_paths: list[str]) -> None:
    if len(short_paths) != SHORTS_PER_VIDEO:
        raise ValueError(f"Cada documental debe incluir exactamente {SHORTS_PER_VIDEO} Shorts.")
    date.fromisoformat(publish_date)
    if any(v["video_id"] == video_id for v in data["videos"]):
        raise ValueError(f"El documental {video_id} ya existe en la cola.")
    if any(v["publish_date"] == publish_date for v in data["videos"]):
        raise ValueError(f"Ya existe un documental programado para {publish_date}.")
    data["videos"].append({
        "video_id": video_id,
        "publish_date": publish_date,
        "shorts": [
            {"number": i + 1, "path": path, "status": "pending", "published_at": None}
            for i, path in enumerate(short_paths)
        ],
    })
    data["videos"].sort(key=lambda item: item["publish_date"])


def due_for_slot(data: dict[str, Any], run_date: str, slot: str) -> dict[str, Any] | None:
    """Return the exact Short due at a given daily slot, or None if not ready.

    The slot is the Short's sequence number. For example, on a given day:
    12:00 publishes Short 1 from yesterday's documentary;
    14:00 publishes Short 2 from the documentary from two days ago;
    ...
    20:00 publishes Short 5 from the documentary from five days ago.

    This yields the requested ramp-up: day 1 has one Short, day 2 has two,
    and from day 5 onward there are five Shorts per day.
    """
    if slot not in SLOTS:
        raise ValueError(f"Hora no válida: {slot}. Usa: {', '.join(SLOTS)}")
    today = date.fromisoformat(run_date)
    sequence = SLOTS.index(slot) + 1
    documentary_date = (today - timedelta(days=sequence - 1)).isoformat()
    for video in data["videos"]:
        if video["publish_date"] != documentary_date:
            continue
        short = video["shorts"][sequence - 1]
        if short["status"] != "pending":
            return None
        return {
            "video_id": video["video_id"],
            "documentary_date": documentary_date,
            "short_number": sequence,
            "path": short["path"],
            "slot": slot,
            "timezone": data.get("timezone", "Europe/Madrid"),
        }
    return None


def mark_published(data: dict[str, Any], video_id: str, short_number: int, published_at: str) -> None:
    for video in data["videos"]:
        if video["video_id"] == video_id:
            short = video["shorts"][short_number - 1]
            if short["status"] == "published":
                raise ValueError("Este Short ya figura como publicado.")
            short["status"] = "published"
            short["published_at"] = published_at
            return
    raise ValueError(f"No existe el documental {video_id}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestiona la cola de Shorts de Caspitas.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    add = sub.add_parser("add")
    add.add_argument("--video-id", required=True)
    add.add_argument("--publish-date", required=True)
    add.add_argument("--short-paths", nargs=5, required=True)

    due = sub.add_parser("due")
    due.add_argument("--date", required=True)
    due.add_argument("--slot", required=True, choices=SLOTS)

    mark = sub.add_parser("mark")
    mark.add_argument("--video-id", required=True)
    mark.add_argument("--short-number", type=int, required=True, choices=range(1, 6))
    mark.add_argument("--published-at", required=True)

    args = parser.parse_args()
    data = load_queue(args.queue)

    if args.command == "init":
        save_queue(data, args.queue)
        print(json.dumps({"status": "ok", "queue": str(args.queue)}))
    elif args.command == "add":
        add_video(data, args.video_id, args.publish_date, args.short_paths)
        save_queue(data, args.queue)
        print(json.dumps({"status": "added", "video_id": args.video_id}))
    elif args.command == "due":
        result = due_for_slot(data, args.date, args.slot)
        print(json.dumps(result or {"status": "not_ready"}, ensure_ascii=False))
    elif args.command == "mark":
        mark_published(data, args.video_id, args.short_number, args.published_at)
        save_queue(data, args.queue)
        print(json.dumps({"status": "published", "video_id": args.video_id, "short_number": args.short_number}))


if __name__ == "__main__":
    main()
