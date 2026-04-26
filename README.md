# quarto-coursegen

A CLI tool that scaffolds [Quarto](https://quarto.org/) course websites from a
single `course.yaml` definition file.

It handles the **generation stage** of a two-stage workflow:

1. **Generation** — `quarto-coursegen generate` reads `course.yaml` and writes
   structured `.qmd` skeleton files and Quarto config files.
2. **Rendering** — `quarto render` (or `make slides` / `make handouts` / …)
   turns the completed `.qmd` files into HTML, PDF, and reveal.js slides.

> **Never mix the two stages.** Generation is structural and potentially
> destructive. Rendering is repeatable and safe.

---

## Installation

Requires Python ≥ 3.11.

```bash
pip install quarto-coursegen
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install quarto-coursegen
```

---

## Quick start

1. Create or clone a course repository based on the
   [quarto-course-template](https://github.com/xylomorph/quarto-course-template).
2. Edit `course.yaml` to describe your course, modules, and desired artifacts.
3. Generate the skeleton files:

```bash
quarto-coursegen generate
```

4. Fill in content in the generated `.qmd` files.
5. Render with Quarto:

```bash
quarto render          # course website
make slides            # reveal.js + Beamer PDF
make handouts          # PDF handouts
```

---

## `course.yaml` — the single source of truth

Everything the generator needs lives in `course.yaml`:

```yaml
course:
  id: my-course
  title: "Logic 101"
  subtitle: "Introduction to Formal Logic"
  semester: "WS 2026"
  language: "en"        # controls i18n strings in generated stubs
  ects: 3
  instructors:
    - name: "Prof. Jane Smith"
      email: "smith@example.com"
      role: "lecturer"
  organization:
    institution: "Example University"
    department: "Department of Philosophy"
  defaults:
    status: planned
    visibility: public
    duration: 90
  schedule:
    start_date: 2026-10-01
    end_date:   2027-01-31
    weekly_day: "Monday"

artifacts:                          # course-level artifacts
  - id: syllabus
    type: syllabus
    enabled: true
    file: "content/syllabus.qmd"

modules:
  - id: intro
    type: lecture
    title: "Introduction"
    date: 2026-10-01
    learning_objectives: |
      - Understand the scope of formal logic
      - Distinguish syntax from semantics
    artifacts:
      - id: intro-slides
        type: slides
        enabled: true
        output_formats: [revealjs, beamer]
      - id: intro-handout
        type: handout
        enabled: true
        output_formats: [website, pdf]
      - id: intro-assignment
        type: assignment
        enabled: false
```

### Artifact `output_formats`

| Format | Rendered by |
|--------|-------------|
| `revealjs` | `content/slides/` sub-project → reveal.js HTML |
| `beamer` | `content/slides/` sub-project → Beamer PDF |
| `pdf` | `content/handouts/` or `content/assignments/` sub-project → PDF |
| `website` | root Quarto website project → HTML page |

---

## `generate` command

```
Usage: quarto-coursegen generate [OPTIONS] [COURSE_YAML]
```

Run from the root of your course repository:

```bash
# Scaffold all missing stubs (skips files that already exist)
quarto-coursegen generate

# Same, but specify course.yaml explicitly
quarto-coursegen generate path/to/course.yaml

# Preview what would be written without touching any files
quarto-coursegen generate --dry-run

# Overwrite existing content stubs (use with care — loses manual edits)
quarto-coursegen generate --force
```

### Options

| Option | Short | Description |
|--------|-------|-------------|
| `COURSE_YAML` | | Path to `course.yaml` (default: `course.yaml` in current directory) |
| `--force` | `-f` | Overwrite existing content stubs |
| `--dry-run` | | Print what would be generated without writing any files |
| `--config` | `-c` | Path to a `coursegen.yaml` config file (see below) |
| `--templates-dir` | | Custom Jinja2 templates directory, searched before built-in templates |
| `--lang-dir` | | Custom i18n lang directory, searched before built-in lang files |
| `--output-root` | | Root directory for all output (default: current directory) |

### Overwrite policy

| File type | Default | With `--force` |
|-----------|---------|----------------|
| Content stubs (`content/**/*.qmd`, `index.qmd`, `_quarto.yml`) | **Skip** if exists | Overwrite |
| Config files (`_quarto-nav.yml`, sub-project `_quarto.yml`s) | **Always overwrite** | Always overwrite |

---

## Configuration file

Instead of passing CLI flags every time, you can place a `coursegen.yaml` (or
`.coursegen.yaml`) in the root of your course repository. The tool discovers it
automatically. Supported keys:

```yaml
# coursegen.yaml
course: course.yaml           # path to course.yaml (relative to this file)
output_root: .                # where content/, index.qmd, _quarto*.yml go
templates: templates/         # local Jinja2 templates overlay (optional)
lang: lang/                   # local i18n lang directory overlay (optional)
```

**Precedence:** CLI arguments > `coursegen.yaml` > built-in defaults.

You can also point to a config file explicitly:

```bash
quarto-coursegen generate --config /path/to/coursegen.yaml
```

---

## Custom templates

The built-in templates (one per artifact type) live inside the package. You can
override any of them by placing a file with the same name in a local
`templates/` directory (or any directory passed via `--templates-dir`).
Local templates are searched first; the built-in ones act as a fallback.

**Built-in templates:**

| Template | Used for |
|----------|----------|
| `slides.qmd.j2` | `type: slides` artifacts |
| `handout.qmd.j2` | `type: handout` artifacts |
| `notes.qmd.j2` | `type: notes` artifacts |
| `assignment.qmd.j2` | `type: assignment` artifacts |
| `syllabus.qmd.j2` | `type: syllabus` artifacts |
| `module.qmd.j2` | Module landing pages |
| `index.qmd.j2` | Course website home page |
| `default_template.qmd.j2` | Any unknown artifact type |

**Template resolution order** (first match wins):

1. `{artifact_id}.{output_format}.qmd.j2`
2. `{artifact_id}.qmd.j2`
3. `{artifact_type}.{output_format}.qmd.j2`
4. `{artifact_type}.qmd.j2`
5. `default_template.qmd.j2`

You can also pin a specific template in `course.yaml`:

```yaml
artifacts:
  - id: my-poster
    type: slides
    output_formats: [revealjs]
    stub_template: poster.qmd.j2          # single template for all formats

  - id: lecture-slides
    type: slides
    output_formats: [revealjs, beamer]
    stub_template:
      default: slides.qmd.j2
      beamer:  slides-beamer.qmd.j2       # per-format override
```

---

## Internationalisation (i18n)

Set `language` in `course.yaml`. Built-in languages: **`en`** (English, default)
and **`de`** (German).

For any other language, add a `{lang}.yaml` file to a local `lang/` directory
(structure mirrors the built-in `lang/en.yaml`). Partial files are fine — only
the keys present in the file override the English defaults.

Inline overrides are also supported directly in `course.yaml`:

```yaml
course:
  language: de
  i18n:
    nav:
      home: Startseite    # overrides the German lang file value
```

---

## Python API

The generator can be used programmatically:

```python
from quarto_coursegen import generate, CoursegenConfig, resolve_config
from pathlib import Path

# Using resolve_config for full precedence resolution
cfg = resolve_config(
    course_yaml=Path("course.yaml"),
    output_root=Path("/my/course"),
    force=False,
    dry_run=False,
)
generate(cfg)

# Or build CoursegenConfig directly for full control
from quarto_coursegen.config import BUILTIN_TEMPLATES_DIR, BUILTIN_LANG_DIR

cfg = CoursegenConfig(
    course_yaml=Path("course.yaml"),
    output_root=Path("."),
    templates_dirs=[Path("templates/"), BUILTIN_TEMPLATES_DIR],
    lang_dirs=[BUILTIN_LANG_DIR],
    force=True,
)
generate(cfg)
```

---

## Project layout (generated output)

```
course-repo/
├── course.yaml               ← you edit this
├── coursegen.yaml            ← optional config (you create this)
├── _quarto.yml               ← generated once, then hand-editable
├── _quarto-nav.yml           ← always regenerated by quarto-coursegen
├── index.qmd                 ← generated once, then hand-editable
├── templates/                ← optional local template overrides
├── lang/                     ← optional local i18n overrides
└── content/
    ├── modules/              ← one .qmd per module
    ├── slides/
    │   ├── _quarto.yml       ← always regenerated
    │   └── *.qmd             ← generated once, then hand-editable
    ├── handouts/
    │   ├── _quarto.yml       ← always regenerated
    │   └── *.qmd
    ├── notes/
    │   └── *.qmd
    ├── assignments/
    │   ├── _quarto.yml       ← always regenerated
    │   └── *.qmd
    └── syllabus.qmd
```

---

## Development

```bash
git clone https://github.com/xylomorph/quarto-coursegen.git
cd quarto-coursegen
uv sync --dev
uv run pytest
```
