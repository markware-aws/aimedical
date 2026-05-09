from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any


def _emit(level: str, msg: str, ctx: dict[str, Any] | None = None) -> None:
    line = {
        "level": level,
        "msg": msg,
        "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if ctx:
        line.update(ctx)
    out = json.dumps(line, ensure_ascii=False, default=str)
    print(out, file=sys.stderr if level in {"warn", "error"} else sys.stdout)


def info(msg: str, ctx: dict[str, Any] | None = None) -> None:
    _emit("info", msg, ctx)


def warn(msg: str, ctx: dict[str, Any] | None = None) -> None:
    _emit("warn", msg, ctx)


def error(msg: str, ctx: dict[str, Any] | None = None) -> None:
    _emit("error", msg, ctx)
