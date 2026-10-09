#!/usr/bin/env python3

import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests


API_URL = "https://www.glasir.fo/wp-json/tribe/events/v1/events"

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "closures.json"

# Bert heiti, sum vit hava staðfest.
# Fleiri kunnu leggjast afturat seinni, tá tey eru váttað.
CLOSURE_TITLES = {
    "Heystferia",
}

LOOKAHEAD_DAYS = 400
REQUEST_TIMEOUT = 30
PER_PAGE = 50


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    tmp = path.with_name(path.name + ".tmp")

    tmp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )

    os.replace(tmp, path)


def parse_date(value: str) -> date:
    return datetime.strptime(
        value[:10],
        "%Y-%m-%d"
    ).date()


def fetch_events(start: date, end: date) -> list:
    events = []
    page = 1

    while True:
        response = requests.get(
            API_URL,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent":
                    "Glasir-Matskra-Skermur/2.0 (+https://www.glasir.fo/)"
            },
            params={
                "start_date":
                    start.isoformat() + " 00:00:00",
                "end_date":
                    end.isoformat() + " 23:59:59",
                "status":
                    "publish",
                "per_page":
                    PER_PAGE,
                "page":
                    page,
            },
        )

        response.raise_for_status()

        data = response.json()

        page_events = data.get("events", [])

        if not isinstance(page_events, list):
            raise RuntimeError(
                "Óvæntað svar frá kalendara-API"
            )

        events.extend(page_events)

        total_pages = int(
            data.get("total_pages", 1)
        )

        if page >= total_pages:
            break

        page += 1

    return events


def build_closures(events: list) -> dict:
    dates = {}

    for event in events:
        title = str(
            event.get("title", "")
        ).strip()

        if title not in CLOSURE_TITLES:
            continue

        start_value = event.get("start_date")
        end_value = event.get("end_date")

        if not start_value or not end_value:
            continue

        start_day = parse_date(start_value)
        end_day = parse_date(end_value)

        if end_day < start_day:
            raise RuntimeError(
                "Ógildugt dato-intervall fyri: " +
                title
            )

        current = start_day

        while current <= end_day:
            dates[current.isoformat()] = {
                "title": title
            }

            current += timedelta(days=1)

    return {
        "source": API_URL,
        "updated_at":
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z"),
        "dates": dict(
            sorted(dates.items())
        ),
    }


def main() -> None:
    today = date.today()

    end = today + timedelta(
        days=LOOKAHEAD_DAYS
    )

    events = fetch_events(
        today,
        end
    )

    payload = build_closures(
        events
    )

    atomic_write_json(
        OUTPUT,
        payload
    )

    print(
        "Dagførdi closures.json:"
    )

    print(
        len(payload["dates"]),
        "stongdir dagar funnir."
    )


if __name__ == "__main__":
    main()
