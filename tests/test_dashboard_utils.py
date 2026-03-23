from datetime import datetime
from types import SimpleNamespace

from founder_agent.dashboard_utils import (
    compute_next_brief_label,
    export_briefs_as_markdown,
    filter_briefs_by_query,
    normalize_csv_list,
    user_should_receive_brief_on,
)


def test_normalize_csv_list_dedupes_and_limits():
    assert normalize_csv_list("Linear, Notion, linear, Asana", limit=3) == ["Linear", "Notion", "Asana"]


def test_compute_next_brief_label_skips_weekends_for_weekday_mode():
    friday_evening = datetime(2026, 3, 27, 20, 30)
    assert compute_next_brief_label(friday_evening, "weekdays", "07:00") == "Monday, March 30 at 7:00 AM"


def test_user_should_receive_brief_on_respects_daily_mode():
    saturday = datetime(2026, 3, 28, 7, 0)
    assert user_should_receive_brief_on(saturday, "daily") is True
    assert user_should_receive_brief_on(saturday, "weekdays") is False


def test_filter_briefs_by_query_matches_text_and_date():
    briefs = [
        SimpleNamespace(date="2026-03-20", brief_text="Revenue improved after enterprise upsell."),
        SimpleNamespace(date="2026-03-21", brief_text="Inbox priorities focused on investor follow-up."),
    ]

    assert [brief.date for brief in filter_briefs_by_query(briefs, "investor")] == ["2026-03-21"]
    assert [brief.date for brief in filter_briefs_by_query(briefs, "2026-03-20")] == ["2026-03-20"]


def test_export_briefs_as_markdown_includes_user_and_sections():
    briefs = [
        SimpleNamespace(date="2026-03-20", brief_text="GOOD MORNING BRIEF — Friday"),
        SimpleNamespace(date="2026-03-21", brief_text="GOOD MORNING BRIEF — Saturday"),
    ]

    exported = export_briefs_as_markdown("founder@example.com", briefs)

    assert "# Foundtel Brief Archive" in exported
    assert "User: founder@example.com" in exported
    assert "## 2026-03-20" in exported
    assert "GOOD MORNING BRIEF — Saturday" in exported
