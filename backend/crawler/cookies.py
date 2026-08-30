"""Safely turn a browser cookie export into a request Cookie header."""

from __future__ import annotations

import json
from pathlib import Path


def load_cookie_header(value: str, domain_suffix: str) -> str:
    """Accept a normal Cookie header, JSON export, or a path to a JSON export."""
    raw_value = value.strip()
    candidate = Path(raw_value)
    if not raw_value.startswith("["):
        try:
            is_file = candidate.is_file()
        except OSError:
            is_file = False
        if is_file:
            raw_value = candidate.read_text(encoding="utf-8-sig").strip()
    if not raw_value.startswith("["):
        return raw_value
    exported = json.loads(raw_value)
    if not isinstance(exported, list):
        raise ValueError("Cookie JSON export must be an array")
    pairs = []
    for cookie in exported:
        if not isinstance(cookie, dict):
            continue
        domain, name, cookie_value = cookie.get("domain"), cookie.get("name"), cookie.get("value")
        if (
            isinstance(domain, str)
            and domain.removeprefix(".").endswith(domain_suffix.removeprefix("."))
            and isinstance(name, str)
            and isinstance(cookie_value, str)
        ):
            pairs.append(f"{name}={cookie_value}")
    if not pairs:
        raise ValueError(f"Cookie export contains no cookies for {domain_suffix}")
    return "; ".join(pairs)
