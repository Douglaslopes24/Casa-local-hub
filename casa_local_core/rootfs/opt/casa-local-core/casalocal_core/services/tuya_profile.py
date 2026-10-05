from __future__ import annotations

from typing import Any


def _dps_sort_key(value: str) -> tuple[int, str]:
    try:
        return (0, f"{int(value):05d}")
    except (TypeError, ValueError):
        return (1, str(value))


def analyze_tuya_dps(status: dict[str, Any]) -> dict[str, Any]:
    raw_dps = status.get("dps")
    dps = raw_dps if isinstance(raw_dps, dict) else {}
    normalized = {str(key): value for key, value in dps.items()}

    boolean_dps = sorted(
        [key for key, value in normalized.items() if isinstance(value, bool)],
        key=_dps_sort_key,
    )
    numeric_dps = sorted(
        [
            key
            for key, value in normalized.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ],
        key=_dps_sort_key,
    )
    string_dps = sorted(
        [key for key, value in normalized.items() if isinstance(value, str)],
        key=_dps_sort_key,
    )

    # Heuristics only. Identification never sends commands.
    if "20" in boolean_dps:
        kind = "light"
        primary_switch_dps = "20"
    elif "1" in boolean_dps:
        kind = "switch"
        primary_switch_dps = "1"
    elif boolean_dps:
        kind = "switch"
        primary_switch_dps = boolean_dps[0]
    else:
        kind = "unknown"
        primary_switch_dps = None

    brightness_dps = None
    if kind == "light":
        for candidate in ("22", "3"):
            if candidate in numeric_dps:
                brightness_dps = candidate
                break

    color_temp_dps = "23" if kind == "light" and "23" in numeric_dps else None
    work_mode_dps = "21" if kind == "light" and "21" in string_dps else None

    return {
        "kind": kind,
        "primary_switch_dps": primary_switch_dps,
        "boolean_dps": boolean_dps,
        "numeric_dps": numeric_dps,
        "string_dps": string_dps,
        "brightness_dps": brightness_dps,
        "color_temp_dps": color_temp_dps,
        "work_mode_dps": work_mode_dps,
        "dps": normalized,
    }
