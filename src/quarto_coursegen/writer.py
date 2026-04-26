"""
quarto_coursegen.writer — File writing helper with rich console output.
"""
from __future__ import annotations

from pathlib import Path

from rich.console import Console

console = Console()


def write_file(
    path: Path,
    content: str,
    *,
    overwrite: bool,
    always_overwrite: bool,
    dry_run: bool,
    root: Path,
) -> None:
    """Write *content* to *path*, respecting overwrite rules.

    Args:
        path:             Absolute destination path.
        content:          Text to write.
        overwrite:        Whether to overwrite existing stubs (--force).
        always_overwrite: True for generator-owned files (nav, sub-project configs).
        dry_run:          Print intent without writing.
        root:             Project root used to compute the display-relative path.
    """
    exists = path.exists()

    if exists and not overwrite and not always_overwrite:
        console.print(f"  [dim]SKIP  {path.relative_to(root)}  (already exists)[/dim]")
        return

    if dry_run:
        action = "OVERWRITE" if exists else "CREATE"
        console.print(f"  [yellow]{action} (dry-run)[/yellow]  {path.relative_to(root)}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    action = "[yellow]OVERWRITE[/yellow]" if exists else "[green]CREATE[/green]"
    console.print(f"  {action}  {path.relative_to(root)}")
