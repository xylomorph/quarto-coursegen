"""
quarto_coursegen.env — Jinja2 environment factory.
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, StrictUndefined


def _basename(path: str) -> str:
    return Path(path).name


def make_jinja_env(templates_dirs: list[Path]) -> Environment:
    """Create a Jinja2 Environment that searches *templates_dirs* in order.

    Custom filters available in all templates:
    - ``basename``   — return the filename component of a path string
    - ``dict2items`` — convert a dict to a list of {key, value} dicts
    - ``of_type``    — filter artifact list by type string
    - ``enabled``    — filter artifact list to enabled=True entries
    - ``by_id``      — return first artifact matching an id, or None
    """
    loaders = [FileSystemLoader(str(d)) for d in templates_dirs]
    env = Environment(
        loader=ChoiceLoader(loaders),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
    )
    env.filters["basename"] = _basename
    env.filters["dict2items"] = lambda d: [{"key": k, "value": v} for k, v in d.items()]
    env.filters["of_type"] = lambda arts, t: [a for a in (arts or []) if a.get("type") == t]
    env.filters["enabled"] = lambda arts: [a for a in (arts or []) if a.get("enabled", True)]
    env.filters["by_id"] = lambda arts, aid: next(
        (a for a in (arts or []) if a.get("id") == aid), None
    )
    return env
