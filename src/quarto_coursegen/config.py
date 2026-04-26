"""
quarto_coursegen.config — Configuration loading and i18n support.

Handles:
- course.yaml parsing
- i18n string resolution (built-in defaults → lang file → inline overrides)
- coursegen.yaml config file parsing
- Path resolution with CLI > config file > defaults precedence
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

# ---------------------------------------------------------------------------
# Built-in package data locations
# ---------------------------------------------------------------------------

_PACKAGE_DIR = Path(__file__).parent
BUILTIN_TEMPLATES_DIR = _PACKAGE_DIR / "templates"
BUILTIN_LANG_DIR = _PACKAGE_DIR / "lang"

# ---------------------------------------------------------------------------
# Built-in English i18n defaults — base for all languages
# ---------------------------------------------------------------------------

_DEFAULT_I18N: dict = {
    "artifact_labels": {
        "slides": "Slides",
        "handout": "Handout",
        "notes": "Notes",
        "assignment": "Assignment",
        "syllabus": "Syllabus",
    },
    "nav": {
        "home": "Home",
        "syllabus": "Syllabus",
        "materials": "Materials",
    },
    "module_page": {
        "overview": "Overview",
        "learning_objectives": "Learning Objectives",
        "slides": "Slides",
        "handout": "Handout",
        "content": "Content",
        "materials": "Materials",
        "coming_soon": "Coming soon.",
    },
    "handout": {
        "learning_objectives": "Learning Objectives",
        "content": "Content",
        "exercises": "Exercises",
    },
    "notes": {
        "notes": "Notes",
        "key_concepts": "Key Concepts",
        "references": "References",
    },
    "assignment": {
        "title_suffix": "Assignment",
        "instructions": "Instructions",
        "tasks": "Tasks",
        "submission": "Submission",
    },
    "syllabus": {
        "title": "Syllabus",
        "course_information": "Course Information",
        "labels": {
            "course": "Course",
            "subtitle": "Subtitle",
            "semester": "Semester",
            "ects": "ECTS",
            "language": "Language",
            "institution": "Institution",
            "department": "Department",
            "start": "Start",
            "end": "End",
            "weekly_day": "Weekly day",
        },
        "instructors": "Instructors",
        "schedule": "Schedule",
        "modules": "Modules",
        "table_headers": {
            "num": "#",
            "date": "Date",
            "title": "Title",
            "status": "Status",
        },
        "tbd": "TBD",
        "learning_objectives": "Learning Objectives",
        "todo": "TODO",
    },
    "index": {
        "welcome": "Welcome",
        "course_information": "Course Information",
        "labels": {
            "semester": "Semester",
            "ects": "ECTS",
            "language": "Language",
            "institution": "Institution",
            "department": "Department",
            "start": "Start",
            "end": "End",
            "weekly_day": "Weekly day",
        },
        "instructors": "Instructors",
        "schedule": "Schedule",
        "modules": "Modules",
    },
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_course(path: Path) -> dict:
    """Load and return the parsed course.yaml."""
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep-merge *override* into *base* in-place and return *base*."""
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def load_i18n(course: dict, lang_dirs: list[Path]) -> dict:
    """Return the i18n string dict for the course language.

    Resolution order (highest priority first):
    1. Inline ``course.i18n`` overrides from course.yaml
    2. First matching ``{lang}.yaml`` found across *lang_dirs*
    3. Built-in English defaults — always the base
    """
    i18n: dict = copy.deepcopy(_DEFAULT_I18N)

    lang = course.get("language", "en")
    for lang_dir in lang_dirs:
        lang_file = lang_dir / f"{lang}.yaml"
        if lang_file.exists():
            with lang_file.open(encoding="utf-8") as fh:
                lang_data = yaml.safe_load(fh) or {}
            _deep_merge(i18n, lang_data)
            break  # first match wins

    inline = course.get("i18n")
    if isinstance(inline, dict):
        _deep_merge(i18n, inline)

    return i18n


def load_config_file(path: Path) -> dict:
    """Load a coursegen.yaml config file; return empty dict if missing."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


# ---------------------------------------------------------------------------
# Resolved configuration
# ---------------------------------------------------------------------------

@dataclass
class CoursegenConfig:
    """All paths and flags resolved for a generate run."""

    course_yaml: Path
    output_root: Path           # where content/, index.qmd, _quarto*.yml go
    templates_dirs: list[Path]  # search order: first match wins (local overlay → built-in)
    lang_dirs: list[Path]       # search order: first match wins
    force: bool = False
    dry_run: bool = False

    @property
    def content_dir(self) -> Path:
        return self.output_root / "content"


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_config(
    *,
    course_yaml: Optional[Path] = None,
    config_file: Optional[Path] = None,
    templates_dir: Optional[Path] = None,
    lang_dir: Optional[Path] = None,
    output_root: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
) -> CoursegenConfig:
    """Resolve all paths with precedence: CLI args > config file > defaults.

    Default behaviour (all args None) mirrors the original course-template layout:
    - course.yaml in cwd
    - output root = cwd
    - templates: local cwd/templates/ overlay (if it exists) + built-in package templates
    - lang: local cwd/lang/ overlay (if it exists) + built-in package lang files
    """
    cwd = Path.cwd()

    # --- locate and load config file ---
    cfg: dict = {}
    config_base = cwd  # relative paths in config file are resolved from here
    if config_file is not None:
        cfg = load_config_file(config_file)
        config_base = config_file.parent
    else:
        for name in ("coursegen.yaml", ".coursegen.yaml", "coursegen.yml", ".coursegen.yml"):
            candidate = cwd / name
            if candidate.exists():
                cfg = load_config_file(candidate)
                config_base = cwd
                break

    # --- course.yaml ---
    if course_yaml is None:
        raw = cfg.get("course", "course.yaml")
        course_yaml = (config_base / raw).resolve()

    # --- output root ---
    if output_root is None:
        raw = cfg.get("output_root", ".")
        output_root = (config_base / raw).resolve()

    # --- templates dirs (local overlay → built-in) ---
    t_dirs: list[Path] = []
    if templates_dir is not None:
        t_dirs.append(templates_dir.resolve())
    elif "templates" in cfg:
        t_dirs.append((config_base / cfg["templates"]).resolve())
    else:
        local = output_root / "templates"
        if local.is_dir():
            t_dirs.append(local)
    t_dirs.append(BUILTIN_TEMPLATES_DIR)

    # --- lang dirs (local overlay → built-in) ---
    l_dirs: list[Path] = []
    if lang_dir is not None:
        l_dirs.append(lang_dir.resolve())
    elif "lang" in cfg:
        l_dirs.append((config_base / cfg["lang"]).resolve())
    else:
        local = output_root / "lang"
        if local.is_dir():
            l_dirs.append(local)
    l_dirs.append(BUILTIN_LANG_DIR)

    return CoursegenConfig(
        course_yaml=course_yaml,
        output_root=output_root,
        templates_dirs=t_dirs,
        lang_dirs=l_dirs,
        force=force,
        dry_run=dry_run,
    )
