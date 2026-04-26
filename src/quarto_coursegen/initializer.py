"""
quarto_coursegen.initializer — Project scaffold for `quarto-coursegen init`.

Copies skeleton files (course.yaml, Makefile, styles/, .gitignore) from the
bundled package data into a target directory, mirroring the course-template
project layout.  Existing files are never overwritten unless force=True.
"""
from __future__ import annotations

from importlib.abc import Traversable
from importlib.resources import files as _pkg_files
from pathlib import Path

from rich.console import Console

from quarto_coursegen.config import BUILTIN_LANG_DIR, BUILTIN_TEMPLATES_DIR

console = Console()

# Skeleton directory shipped with the package — accessed via importlib.resources
# so it works correctly across all packaging formats (wheel, editable, etc.).
_PKG_DATA: Traversable = _pkg_files("quarto_coursegen").joinpath("package_data")
SKELETON_DIR: Path = Path(_PKG_DATA / "skeleton")


def _write_file(
    src: Traversable,
    dst: Path,
    *,
    force: bool,
    dry_run: bool,
    root: Path,
) -> None:
    """Write resource *src* to *dst*, respecting overwrite rules."""
    exists = dst.exists()

    if exists and not force:
        console.print(f"  [dim]SKIP  {dst.relative_to(root)}  (already exists)[/dim]")
        return

    if dry_run:
        action = "OVERWRITE" if exists else "CREATE"
        console.print(f"  [yellow]{action} (dry-run)[/yellow]  {dst.relative_to(root)}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    action = "[yellow]OVERWRITE[/yellow]" if exists else "[green]CREATE[/green]"
    console.print(f"  {action}  {dst.relative_to(root)}")


def _copy_traversable_tree(
    src: Traversable,
    dst_dir: Path,
    *,
    force: bool,
    dry_run: bool,
    root: Path,
) -> None:
    """Recursively copy a ``Traversable`` resource tree into *dst_dir*.

    Using the ``Traversable`` API (``iterdir`` / ``read_bytes``) instead of
    ``Path.__file__`` means this works correctly from any packaging format —
    a regular wheel install, an editable install, or a zip-based import.
    """
    for child in sorted(src.iterdir(), key=lambda c: c.name):
        dst = dst_dir / child.name
        if child.is_dir():
            _copy_traversable_tree(child, dst, force=force, dry_run=dry_run, root=root)
        else:
            _write_file(child, dst, force=force, dry_run=dry_run, root=root)


def init_project(
    target: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> None:
    """Initialise a Quarto course project in *target*.

    Copies the following bundled files into *target*:
      - course.yaml            (starter course definition — edit this)
      - Makefile               (rendering targets only)
      - styles/custom.scss     (website SCSS theme stub)
      - styles/slides.scss     (reveal.js SCSS theme stub)
      - .gitignore
      - templates/*.j2         (all built-in Jinja2 templates — customise freely)
      - lang/*.yaml            (built-in i18n files — customise or extend)

    Files that already exist are skipped unless *force* is True.
    With *dry_run* nothing is written — only planned actions are printed.
    """
    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    console.print(f"Initialising course project in [bold]{target}[/bold]")
    if dry_run:
        console.print("[yellow](dry-run — no files will be written)[/yellow]\n")

    _copy_traversable_tree(_PKG_DATA / "skeleton", target, force=force, dry_run=dry_run, root=target)
    _copy_traversable_tree(_PKG_DATA / "templates", target / "templates", force=force, dry_run=dry_run, root=target)
    _copy_traversable_tree(_PKG_DATA / "lang", target / "lang", force=force, dry_run=dry_run, root=target)

    if not dry_run:
        console.print(
            "\n[bold green]Done.[/bold green]  "
            "Next: edit [cyan]course.yaml[/cyan], then run "
            "[cyan]quarto-coursegen generate[/cyan]"
        )
    else:
        console.print("\n[bold green]Done.[/bold green] (dry-run)")
