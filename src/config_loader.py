import os
import re
import yaml
from dotenv import load_dotenv


_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


def _expand_env(value):
    if isinstance(value, str):
        def replace(match):
            key = match.group(1)
            return os.getenv(key, match.group(0))

        expanded = _ENV_PATTERN.sub(replace, value)

        if expanded.isdigit():
            return int(expanded)

        return expanded

    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_expand_env(v) for v in value]

    return value


def load_config(path: str) -> dict:
    load_dotenv()

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return _expand_env(raw)