"""Container healthcheck for the Obsidian LLM-Wiki Agent."""

import os
import sys
import time
from pathlib import Path


DEFAULT_HEARTBEAT = Path(__file__).parent / "data" / "health" / "heartbeat"
HEARTBEAT_PATH = Path(os.getenv("HEARTBEAT_PATH", str(DEFAULT_HEARTBEAT)))
STALE_SECONDS = int(os.getenv("HEALTHCHECK_STALE_SECONDS", "120"))


def main() -> int:
    if not HEARTBEAT_PATH.exists():
        print(f"heartbeat file missing: {HEARTBEAT_PATH}")
        return 1

    try:
        raw_value = HEARTBEAT_PATH.read_text(encoding="utf-8").strip()
        last_seen = float(raw_value)
    except Exception:
        last_seen = HEARTBEAT_PATH.stat().st_mtime

    age_seconds = time.time() - last_seen
    if age_seconds > STALE_SECONDS:
        print(
            f"heartbeat stale: age={age_seconds:.1f}s threshold={STALE_SECONDS}s"
        )
        return 1

    print(f"healthy: heartbeat age={age_seconds:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
