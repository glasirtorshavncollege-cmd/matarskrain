#!/usr/bin/env python3
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup, Tag

SOURCE = "https://www.glasir.fo/um-skulan/kantinan-a-glasi/"
DAYS = ["Mánadag", "Týsdag", "Mikudag", "Hósdag", "Fríggjadag"]
FAROE_TZ = ZoneInfo("Atlantic/Faroe")
FRIDAY_NEXT_HOUR = 13

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "menu.json"
NEXT = ROOT / "menu-next.json"


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def find_day_heading(soup: BeautifulSoup, day: str):
    for heading in soup.find_all(re.compile(r"^h[1-6]$")):
        if clean(heading.get_text(" ", strip=True)).casefold() == day.casefold():
            return heading
    return None


def extract_dish(heading: Tag) -> str:
    parts = []
    for node in heading.next_siblings:
        if isinstance(node, Tag) and re.fullmatch(r"h[1-6]", node.name or ""):
            break
        if isinstance(node, Tag) and node.name in {"script", "style", "noscript"}:
            continue
        text = clean(node.get_text(" ", strip=True) if isinstance(node, Tag) else str(node))
        if text:
            parts.append(text)

    text = clean(" ".join(parts))
    text = re.sub(r"\bDagsins rættur\b", "", text, flags=re.IGNORECASE)
    return clean(text)


def monday_of_week(value: datetime) -> date:
    return value.date() - timedelta(days=value.weekday())


def output_path_for_time(now_local: datetime, current: Path = CURRENT, next_path: Path = NEXT) -> Path:
    weekday = now_local.weekday()
    if weekday == 4 and now_local.hour >= FRIDAY_NEXT_HOUR:
        return next_path
    if weekday in (5, 6):
        return next_path
    return current


def target_week_start(now_local: datetime, output: Path, current: Path = CURRENT) -> str:
    start = monday_of_week(now_local)
    if output != current:
        start = start + timedelta(days=7)
    return start.isoformat()


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def promote_next_menu(now_local: datetime, current: Path = CURRENT, next_path: Path = NEXT) -> bool:
    if now_local.weekday() != 0 or not next_path.exists():
        return False

    expected_week = monday_of_week(now_local).isoformat()
    payload = read_json(next_path)

    if not payload or payload.get("week_start") != expected_week:
        print(
            "ÁVARING: menu-next.json hoyrir ikki til hesa vikuna; "
            "hon verður slett og ikki flutt."
        )
        try:
            next_path.unlink()
        except OSError:
            pass
        return False

    os.replace(next_path, current)
    print("Mánadagur: menu-next.json er atomiskt flutt til menu.json.")
    return True


def fetch_menu(week_start: str) -> dict:
    response = requests.get(
        SOURCE,
        timeout=30,
        headers={"User-Agent": "Glasir-Matskra-Skermur/2.0 (+https://www.glasir.fo/)"},
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    result = []

    for day in DAYS:
        heading = find_day_heading(soup, day)
        if heading is None:
            raise RuntimeError(f"Fann ikki yvirskriftina: {day}")

        dish = extract_dish(heading)
        if not dish:
            dish = "Eingin rættur er skrásettur"
        result.append({"day": day, "dish": dish})

    return {
        "source": SOURCE,
        "week_start": week_start,
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "days": result,
    }


def run_update(now_local: datetime | None = None, fetcher=fetch_menu,
               current: Path = CURRENT, next_path: Path = NEXT) -> Path:
    now_local = now_local or datetime.now(FAROE_TZ)
    print("Føroysk tíð:", now_local.isoformat(timespec="seconds"))

    promote_next_menu(now_local, current=current, next_path=next_path)

    output = output_path_for_time(now_local, current=current, next_path=next_path)
    week_start = target_week_start(now_local, output, current=current)
    payload = fetcher(week_start)

    # Safety invariant: after Friday 13 and during weekend CURRENT must never be touched.
    if output == current and (
        (now_local.weekday() == 4 and now_local.hour >= FRIDAY_NEXT_HOUR)
        or now_local.weekday() in (5, 6)
    ):
        raise RuntimeError("Safety invariant brotin: komandi vika var á veg í menu.json")

    atomic_write_json(output, payload)

    if output == next_path:
        print("Goymir matskránna sum KOMANDI viku:", next_path.name)
    else:
        print("Goymir matskránna sum VERANDI viku:", current.name)

    return output


def main() -> None:
    run_update()


if __name__ == "__main__":
    main()
