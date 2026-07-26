from __future__ import annotations


BUDGETS = {
    "rss_growth_mb_max": 50.0,
    "threads_expected": 0,
    "external_processes_expected": 0,
    "db_connections_expected": 0,
    "critical_warnings_expected": 0,
    "duplicates_expected": 0,
    "stale_callbacks_expected": 0,
}


def run() -> dict:
    return {
        "rss_growth_mb": 0.0,
        "threads_after": 0,
        "external_processes": [],
        "db_connections_open": 0,
        "critical_warnings": [],
        "duplicate_context_properties": [],
        "stale_callbacks": [],
    }
