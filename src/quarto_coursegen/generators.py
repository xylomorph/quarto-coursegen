"""
quarto_coursegen.generators — All generate_* functions and the top-level generate().

Each function takes a CoursegenConfig (paths + flags) and a pre-built Jinja2
Environment so they can be called individually or composed by generate().
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment
from rich.console import Console

from quarto_coursegen.config import CoursegenConfig, load_course, load_i18n
from quarto_coursegen.core import (
    SUBPROJECT_MAP,
    _SLIDE_FORMATS,
    apply_defaults,
    collect_subproject_files,
    default_artifact_path,
    has_website_artifacts,
    normalize_artifact,
    resolve_stub_template,
)
from quarto_coursegen.env import make_jinja_env
from quarto_coursegen.writer import write_file

console = Console()


# ---------------------------------------------------------------------------
# Individual generators
# ---------------------------------------------------------------------------

def generate_module_page(
    env: Environment,
    module: dict,
    config: CoursegenConfig,
    course: dict | None = None,
) -> None:
    tmpl = env.get_template("module.qmd.j2")
    content = tmpl.render(module=module, course=course or {})
    out = config.content_dir / "modules" / f"{module['id']}.qmd"
    write_file(
        out, content,
        overwrite=config.force,
        always_overwrite=False,
        dry_run=config.dry_run,
        root=config.output_root,
    )


def generate_artifact_stubs(
    env: Environment,
    module: dict,
    config: CoursegenConfig,
    course: dict | None = None,
) -> None:
    """Generate stub .qmd files for each enabled artifact in a module."""
    for artifact in (module.get("artifacts") or []):
        if not artifact.get("enabled", True):
            continue

        tmpl_name = resolve_stub_template(artifact, config.templates_dirs)
        try:
            tmpl = env.get_template(tmpl_name)
        except Exception:
            console.print(
                f"  [red]WARN[/red]  Template '{tmpl_name}' not found for artifact "
                f"'{artifact.get('id')}' in module '{module['id']}' — skipped"
            )
            continue

        rendered = tmpl.render(module=module, artifact=artifact, course=course or {})
        file_path = artifact.get("file") or default_artifact_path(artifact, module["id"])
        out = config.output_root / file_path
        write_file(
            out, rendered,
            overwrite=config.force,
            always_overwrite=False,
            dry_run=config.dry_run,
            root=config.output_root,
        )


def generate_course_artifacts(
    env: Environment,
    course: dict,
    modules: list[dict],
    course_artifacts: list[dict],
    config: CoursegenConfig,
) -> None:
    """Generate stub .qmd files for course-level artifacts (e.g. syllabus)."""
    for artifact in course_artifacts:
        if not artifact.get("enabled", True):
            continue

        tmpl_name = resolve_stub_template(artifact, config.templates_dirs)
        try:
            tmpl = env.get_template(tmpl_name)
        except Exception:
            console.print(
                f"  [red]WARN[/red]  Template '{tmpl_name}' not found for course artifact "
                f"'{artifact.get('id')}' — skipped"
            )
            continue

        rendered = tmpl.render(course=course, modules=modules, artifact=artifact)
        file_path = artifact.get("file") or default_artifact_path(artifact, None)
        out = config.output_root / file_path
        write_file(
            out, rendered,
            overwrite=config.force,
            always_overwrite=False,
            dry_run=config.dry_run,
            root=config.output_root,
        )


def generate_index(
    env: Environment,
    course: dict,
    modules: list[dict],
    config: CoursegenConfig,
) -> None:
    tmpl = env.get_template("index.qmd.j2")
    rendered = tmpl.render(course=course, modules=modules)
    out = config.output_root / "index.qmd"
    write_file(
        out, rendered,
        overwrite=config.force,
        always_overwrite=False,
        dry_run=config.dry_run,
        root=config.output_root,
    )


def generate_quarto_yml(
    env: Environment,
    course: dict,
    config: CoursegenConfig,
) -> None:
    tmpl = env.get_template("_quarto.yml.j2")
    rendered = tmpl.render(course=course)
    out = config.output_root / "_quarto.yml"
    write_file(
        out, rendered,
        overwrite=config.force,
        always_overwrite=False,
        dry_run=config.dry_run,
        root=config.output_root,
    )


def generate_nav_config(
    env: Environment,
    course: dict,
    modules: list[dict],
    course_artifacts: list[dict],
    config: CoursegenConfig,
) -> None:
    """Generate _quarto-nav.yml (always overwritten — owned by generator)."""
    tmpl = env.get_template("_quarto-nav.yml.j2")
    rendered = tmpl.render(
        course=course,
        modules=modules,
        course_artifacts=course_artifacts,
        website_artifacts=has_website_artifacts(modules),
    )
    out = config.output_root / "_quarto-nav.yml"
    write_file(
        out, rendered,
        overwrite=True,
        always_overwrite=True,
        dry_run=config.dry_run,
        root=config.output_root,
    )


def generate_subproject_configs(
    env: Environment,
    course: dict,
    modules: list[dict],
    course_artifacts: list[dict],
    config: CoursegenConfig,
) -> None:
    """Generate _quarto.yml for each artifact sub-project (always overwritten)."""
    file_map = collect_subproject_files(modules, course_artifacts)

    # Collect all slide output formats across enabled artifacts
    slide_formats: set[str] = set()
    for module in modules:
        for artifact in (module.get("artifacts") or []):
            if artifact.get("enabled", True):
                fmts = set(artifact.get("output_formats") or [])
                slide_formats |= fmts & _SLIDE_FORMATS
    for artifact in course_artifacts:
        if artifact.get("enabled", True):
            fmts = set(artifact.get("output_formats") or [])
            slide_formats |= fmts & _SLIDE_FORMATS

    for subproject, files in file_map.items():
        if not files:
            continue
        tmpl = env.get_template(f"{subproject}-project.yml.j2")
        render_kwargs: dict = {"course": course, "files": files}
        if subproject == "slides":
            render_kwargs["slide_formats"] = slide_formats
        rendered = tmpl.render(**render_kwargs)
        out = config.content_dir / SUBPROJECT_MAP[subproject] / "_quarto.yml"
        write_file(
            out, rendered,
            overwrite=True,
            always_overwrite=True,
            dry_run=config.dry_run,
            root=config.output_root,
        )


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def generate(config: CoursegenConfig) -> None:
    """Run the full generation pipeline for the given configuration."""
    data = load_course(config.course_yaml)
    course: dict = data.get("course", {})
    modules: list[dict] = data.get("modules", [])
    course_artifacts: list[dict] = data.get("artifacts", [])

    apply_defaults(modules, course.get("defaults", {}))

    # Normalize artifact lists: fill in default id, enabled, status, file path
    for module in modules:
        normalized = []
        for i, a in enumerate(module.get("artifacts") or []):
            a = normalize_artifact(a, i)
            if "file" not in a:
                a["file"] = default_artifact_path(a, module["id"])
            normalized.append(a)
        module["artifacts"] = normalized

    normalized_course_artifacts = []
    for i, a in enumerate(course_artifacts):
        a = normalize_artifact(a, i)
        if "file" not in a:
            a["file"] = default_artifact_path(a, None)
        normalized_course_artifacts.append(a)
    course_artifacts = normalized_course_artifacts

    env = make_jinja_env(config.templates_dirs)
    env.globals["i18n"] = load_i18n(course, config.lang_dirs)

    console.print(f"Generating course: [bold]{course.get('title', '(untitled)')}[/bold]")
    if config.dry_run:
        console.print("[yellow](dry-run — no files will be written)[/yellow]\n")

    for module in modules:
        generate_module_page(env, module, config, course=course)
        generate_artifact_stubs(env, module, config, course=course)

    generate_course_artifacts(env, course, modules, course_artifacts, config)
    generate_index(env, course, modules, config)
    generate_quarto_yml(env, course, config)
    generate_nav_config(env, course, modules, course_artifacts, config)
    generate_subproject_configs(env, course, modules, course_artifacts, config)

    console.print("\n[bold green]Done.[/bold green]")
