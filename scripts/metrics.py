# scripts/metrics.py
import json, time
from pathlib import Path
from typing import Dict

METRICS_PATH = Path("logs/metrics.json")


def _load() -> Dict:
    if METRICS_PATH.exists():
        try:
            return json.loads(METRICS_PATH.read_text())
        except Exception:
            return {}
    return {}


def incr(stage: str, key: str, by: int = 1):
    m = _load()
    m.setdefault(stage, {}).setdefault(key, 0)
    m[stage][key] += by
    m[stage]["updated_at"] = time.time()
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2))


def setval(stage: str, key: str, val):
    m = _load()
    m.setdefault(stage, {})[key] = val
    m[stage]["updated_at"] = time.time()
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2))
