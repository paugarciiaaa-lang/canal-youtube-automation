#!/usr/bin/env python3
"""Deterministic daily Shorts queue for Caspitas.

For each documentary published on launch date D, publish:
  D at 12:00: Short 1
  D+1 at 12:00: Short 2 (and the new documentary's Short 1 at 14:00)
  ...
Once the queue is mature, five Shorts are published daily, oldest documentary
first (12:00) through newest documentary last (20:00).

The long documentary is scheduled at 21:00. Shorts and their source videos must
be generated in advance so the 12:00 Short can be published on the same date.
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
    """Return the Short due at this slot, preserving the user's ramp-up sequence.

    Day 1: 12:00 -> documentary 1 / Short 1.
    Day 2: 12:00 -> documentary 1 / Short 2; 14:00 -> documentary 2 / Short 1.
    Day 3: 12:00 -> documentary 1 / Short 3; 14:00 -> documentary 2 / Short 2;
           16:00 -> documentary 3 / Short 1.
    After day 5, five daily slots continue in the same oldest-to-newest order.
    """
    if slot not in SLOTS:
        raise ValueError(f"Hora no válida: {slot}. Usa: {', '.join(SLOTS)}")
    if not data["videos"]:
        return None

    today = date.fromisoformat(run_date)
    first_date = min(date.fromisoformat(v["publish_date"]) for v in data["videos"])
    day_number = (today - first_date).days + 1
    if day_number < 1:
        return None

    slots_today = min(SHORTS_PER_VIDEO, day_number)
    slot_index = SLOTS.index(slot)
    if slot_index >= slots_today:
        return None

    age_days = slots_today - 1 - slot_index
    documentary_date = (today - timedelta(days=age_days)).isoformat()
    short_number = age_days + 1

    for video in data["videos"]:
        if video["publish_date"] != documentary_date:
            continue
        short = video["shorts"][short_number - 1]
        if short["status"] != "pending":
            return None
        return {
            "video_id": video["video_id"],
            "documentary_date": documentary_date,
            "short_number": short_number,
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

    sub.add_parser("init")
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
