from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List, Sequence, Tuple

WEEKDAY_MODE = "weekdays"
DAILY_MODE = "daily"
DIGEST_CONCISE = "concise"
DIGEST_DEEP = "deep"


def normalize_csv_list(raw_value: str, *, dedupe_casefold: bool = True, limit: int | None = None) -> List[str]:
    items: List[str] = []
    seen = set()

    for raw_item in (raw_value or "").split(","):
        item = raw_item.strip()
        if not item:
            continue
        key = item.casefold() if dedupe_casefold else item
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
        if limit is not None and len(items) >= limit:
            break

    return items


def compute_next_brief_label(now: datetime, briefing_days: str = WEEKDAY_MODE, briefing_time: str = "07:00") -> str:
    hour, minute = parse_briefing_time(briefing_time)
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if now >= next_run:
        next_run += timedelta(days=1)

    if briefing_days == WEEKDAY_MODE:
        while next_run.weekday() >= 5:
            next_run += timedelta(days=1)

    time_label = next_run.strftime("%I:%M %p").lstrip("0")
    if next_run.date() == now.date():
        return f"Today, {time_label}"
    if next_run.date() == (now + timedelta(days=1)).date():
        return f"Tomorrow, {time_label}"
    return next_run.strftime(f"%A, %B %d at {time_label}")


def parse_briefing_time(briefing_time: str) -> Tuple[int, int]:
    try:
        hour_str, minute_str = (briefing_time or "07:00").split(":", 1)
        hour = max(0, min(23, int(hour_str)))
        minute = max(0, min(59, int(minute_str)))
        return hour, minute
    except (TypeError, ValueError):
        return 7, 0


def user_should_receive_brief_on(now: datetime, briefing_days: str = WEEKDAY_MODE) -> bool:
    if briefing_days == DAILY_MODE:
        return True
    return now.weekday() < 5


def filter_briefs_by_query(briefs: Sequence, query: str):
    trimmed = (query or "").strip().lower()
    if not trimmed:
        return list(briefs)

    return [
        brief for brief in briefs
        if trimmed in (brief.brief_text or "").lower() or trimmed in (brief.date or "").lower()
    ]


def export_briefs_as_markdown(user_email: str, briefs: Iterable) -> str:
    lines = [f"# Foundtel Brief Archive", "", f"User: {user_email}", ""]
    for brief in briefs:
        lines.extend([
            f"## {brief.date}",
            "",
            (brief.brief_text or "").strip(),
            "",
        ])
    return "\n".join(lines).strip() + "\n"
