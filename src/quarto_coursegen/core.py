"""
quarto_coursegen.core — Pure logic helpers.

All functions here are side-effect free (no I/O, no Jinja2 dependency)
and map directly to the original tools/generate.py logic.
"""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Type → content/ subdirectory mapping
# ---------------------------------------------------------------------------

_TYPE_SUBDIR: dict[str, str] = {
    "slides": "slides",
    "handout": "handouts",
    "notes": "notes",
    "assignment": "assignments",
    "syllabus": "",  # directly under content/
}

# Sub-project configs: logical key → content/ subdir
SUBPROJECT_MAP: dict[str, str] = {
    "slides": "slides",
    "handouts": "handouts",
    "assignments": "assignments",
}

# Output-format routing for sub-project configs
_SLIDE_FORMATS: frozenset[str] = frozenset({"revealjs", "beamer"})
_PDF_ARTIFACT_TO_SUBPROJECT: dict[str, str] = {
    "handout": "handouts",
    "notes": "handouts",
    "assignment": "assignments",
}


# ---------------------------------------------------------------------------
# Artifact helpers
# ---------------------------------------------------------------------------

def normalize_artifact(artifact: dict, index: int) -> dict:
    """Fill in defaults for id, enabled, and status on an artifact dict (in-place)."""
    if "id" not in artifact:
        art_type = artifact.get("type")
        artifact["id"] = f"{art_type}-{index}" if art_type else f"artifact-{index}"
    if "enabled" not in artifact:
        artifact["enabled"] = True
    if "status" not in artifact:
        artifact["status"] = "planned"
    return artifact


def apply_defaults(modules: list[dict], defaults: dict) -> list[dict]:
    """Merge course-level defaults into each module where keys are absent."""
    for module in modules:
        for key, value in defaults.items():
            if key not in module:
                module[key] = value
    return modules


def subdir_for_type(artifact_type: str | None) -> str:
    """Return the content/ subdirectory for a given artifact type."""
    if artifact_type is None:
        return ""
    return _TYPE_SUBDIR.get(artifact_type, artifact_type)


def default_artifact_path(artifact: dict, scope_id: str | None = None) -> str:
    """Return the default content-relative path for an artifact.

    For module-level artifacts (scope_id set): content/<subdir>/<scope_id>-<type>.qmd
    For course-level artifacts (scope_id None): content/<subdir>/<type>.qmd
    """
    art_type = artifact.get("type")
    art_id = artifact.get("id", "artifact")
    subdir = subdir_for_type(art_type)

    if scope_id and art_type:
        filename = f"{scope_id}-{art_type}.qmd"
    elif scope_id:
        filename = f"{scope_id}.qmd"
    elif art_type:
        filename = f"{art_type}.qmd"
    else:
        filename = f"{art_id}.qmd"

    if subdir:
        return f"content/{subdir}/{filename}"
    return f"content/{filename}"


def resolve_stub_template(artifact: dict, templates_dirs: list[Path]) -> str:
    """Resolve the Jinja2 stub template name for an artifact.

    Resolution order when stub_template is not set:
      1. <artifact_id>.<output_format>.qmd.j2  (per format in output_formats order)
      2. <artifact_id>.qmd.j2
      3. <artifact_type>.<output_format>.qmd.j2
      4. <artifact_type>.qmd.j2
      5. default_template.qmd.j2

    When stub_template is a string, it is used directly.
    When stub_template is a dict, format-specific keys are tried first, then 'default'.
    Templates are searched across all template dirs in order.
    """
    stub_template = artifact.get("stub_template")
    output_formats: list[str] = artifact.get("output_formats") or []

    if stub_template is not None:
        if isinstance(stub_template, str):
            return stub_template
        if isinstance(stub_template, dict):
            for fmt in output_formats:
                if fmt in stub_template:
                    return stub_template[fmt]
            if "default" in stub_template:
                return stub_template["default"]
            # Fall through to auto-resolution if dict had no match

    artifact_id = artifact.get("id")
    artifact_type = artifact.get("type")

    candidates: list[str] = []
    if artifact_id:
        for fmt in output_formats:
            candidates.append(f"{artifact_id}.{fmt}.qmd.j2")
        candidates.append(f"{artifact_id}.qmd.j2")
    if artifact_type:
        for fmt in output_formats:
            candidates.append(f"{artifact_type}.{fmt}.qmd.j2")
        candidates.append(f"{artifact_type}.qmd.j2")
    candidates.append("default_template.qmd.j2")

    for candidate in candidates:
        for tdir in templates_dirs:
            if (tdir / candidate).exists():
                return candidate

    return "default_template.qmd.j2"


def has_website_artifacts(modules: list[dict]) -> bool:
    """Return True if any enabled module artifact has 'website' in output_formats."""
    for module in modules:
        for artifact in (module.get("artifacts") or []):
            if artifact.get("enabled", True) and "website" in (artifact.get("output_formats") or []):
                return True
    return False


def collect_subproject_files(
    modules: list[dict],
    course_artifacts: list[dict] | None = None,
) -> dict[str, list[str]]:
    """Return sub-project key → list of basenames to render.

    Sub-project keys: 'slides', 'handouts', 'assignments'.
    Only enabled artifacts whose output_formats include a non-website format are listed.
    """
    result: dict[str, list[str]] = {key: [] for key in SUBPROJECT_MAP}

    def _route(artifact: dict, scope_id: str | None) -> None:
        if not artifact.get("enabled", True):
            return
        formats = set(artifact.get("output_formats") or [])
        file_path = artifact.get("file") or default_artifact_path(artifact, scope_id)
        basename = Path(file_path).name
        atype = artifact.get("type", "")
        if formats & _SLIDE_FORMATS:
            result["slides"].append(basename)
        if "pdf" in formats and atype in _PDF_ARTIFACT_TO_SUBPROJECT:
            result[_PDF_ARTIFACT_TO_SUBPROJECT[atype]].append(basename)

    for module in modules:
        for artifact in (module.get("artifacts") or []):
            _route(artifact, module.get("id"))

    for artifact in (course_artifacts or []):
        _route(artifact, None)

    return result
