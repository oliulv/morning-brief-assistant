from __future__ import annotations

from typing import Iterable, List


def truncate(text: str, max_len: int = 120) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def bulletize(lines: Iterable[str]) -> str:
    return "\n".join(f"• {line}" for line in lines if line)


def section(title: str, lines: List[str]) -> str:
    body = bulletize([truncate(l) for l in lines if l]) if lines else "(none)"
    return f"{title}\n{body}" if body else title


