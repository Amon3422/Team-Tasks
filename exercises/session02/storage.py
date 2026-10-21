import json
from pathlib import Path

def load_tasks(filepath: str | Path):
    path = Path(filepath)
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed JSON syntax at line {exc.lineno}: {exc.msg}") from exc

    return raw_data
