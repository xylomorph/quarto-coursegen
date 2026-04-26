"""
quarto_coursegen.cli — Typer CLI for quarto-coursegen.

Entry point: quarto-coursegen (mapped to `app` in pyproject.toml)

Commands:
  init      — bootstrap a new course project from bundled skeleton files
  generate  — scaffold Quarto course stubs from course.yaml
"""
from __future__ import annotations

from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="quarto-coursegen",
    help="Scaffold Quarto course websites from a course.yaml definition.",
    add_completion=False,
    no_args_is_help=True,
)

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        from quarto_coursegen import __version__
        console.print(f"quarto-coursegen {__version__}")
        raise typer.Exit()


@app.callback()
def _root(
    version: Annotated[
        Optional[bool],
        typer.Option("--version", "-V", callback=_version_callback, is_eager=True, help="Show version and exit."),
    ] = None,
) -> None:
    """quarto-coursegen — scaffold Quarto course websites from course.yaml."""


@app.command()
def init(
    course_dir: Annotated[
        Optional[Path],
        typer.Argument(
            help="Directory to initialise. Created if it does not exist. "
                 "Defaults to the current directory.",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing files."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print what would be copied without writing files."),
    ] = False,
) -> None:
    """Initialise a new Quarto course project.

    Copies the bundled skeleton files (course.yaml, Makefile, styles/, .gitignore)
    into the target directory. Existing files are not overwritten unless --force
    is given.

    \b
    Examples:
      quarto-coursegen init                  # initialise current directory
      quarto-coursegen init my-course        # create and initialise my-course/
      quarto-coursegen init my-course -f     # overwrite existing files
      quarto-coursegen init --dry-run        # preview without writing
    """
    from quarto_coursegen.initializer import init_project

    target = (Path.cwd() / course_dir).resolve() if course_dir else Path.cwd()
    init_project(target, force=force, dry_run=dry_run)


@app.command()
def generate(
    course_yaml: Annotated[
        Optional[Path],
        typer.Argument(help="Path to course.yaml (default: course.yaml in cwd)"),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing content stubs."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Print what would be generated without writing files."),
    ] = False,
    config: Annotated[
        Optional[Path],
        typer.Option(
            "--config", "-c",
            help="Path to a coursegen.yaml config file. If omitted, the tool looks for "
                 "coursegen.yaml / .coursegen.yaml in the current directory.",
        ),
    ] = None,
    templates_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--templates-dir",
            help="Custom Jinja2 templates directory. Searched before built-in templates.",
        ),
    ] = None,
    lang_dir: Annotated[
        Optional[Path],
        typer.Option(
            "--lang-dir",
            help="Custom i18n lang directory. Searched before built-in lang files.",
        ),
    ] = None,
    output_root: Annotated[
        Optional[Path],
        typer.Option(
            "--output-root",
            help="Root directory where content/, index.qmd, _quarto*.yml are written "
                 "(default: current directory).",
        ),
    ] = None,
) -> None:
    """Generate Quarto course content stubs from course.yaml.

    Running without arguments uses course.yaml in the current directory and
    writes all output there, mirroring the default course-template layout.

    \b
    Examples:
      quarto-coursegen generate
      quarto-coursegen generate --force
      quarto-coursegen generate path/to/course.yaml --output-root /my/course
      quarto-coursegen generate --config coursegen.yaml
    """
    from quarto_coursegen.config import resolve_config
    from quarto_coursegen.generators import generate as _generate

    cfg = resolve_config(
        course_yaml=course_yaml,
        config_file=config,
        templates_dir=templates_dir,
        lang_dir=lang_dir,
        output_root=output_root,
        force=force,
        dry_run=dry_run,
    )

    if not cfg.course_yaml.exists():
        console.print(f"[red]ERROR:[/red] course.yaml not found at {cfg.course_yaml}")
        raise typer.Exit(1)

    _generate(cfg)
