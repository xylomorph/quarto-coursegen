# quarto-coursegen

A CLI tool that scaffolds [Quarto](https://quarto.org/) course websites from a
single `course.yaml` definition file.

**→ Full documentation: `docs/index.html` (rendered from `docs_src/`)**

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

```bash
# 1. Create and bootstrap a new course project
quarto-coursegen init my-course
cd my-course

# 2. Edit course.yaml (title, modules, artifacts, instructors, …)

# 3. Scaffold .qmd stubs and Quarto config from course.yaml
quarto-coursegen generate

# 4. Fill in content in the generated .qmd files

# 5. Render with Quarto
quarto render          # course website → docs/
make slides            # reveal.js + Beamer PDF → docs/slides/
make handouts          # PDF handouts → docs/handouts/
```

For the full reference — `course.yaml` schema, command options, templates,
i18n, rendering guide, Python API — see the **[documentation](docs/index.html)**.

---

## Project layout (generated course repo)

```
course-repo/
│  ← quarto-coursegen init
├── course.yaml               ← edit this: title, modules, artifacts
├── Makefile                  ← rendering targets (make website / slides / …)
├── styles/
├── templates/                ← built-in Jinja2 templates (customise locally)
├── lang/                     ← built-in language files (customise locally)
│
│  ← optional
├── coursegen.yaml            ← tool config (overrides)
│
│  ← quarto-coursegen generate
├── _quarto.yml               ← generated once, then hand-editable
├── _quarto-nav.yml           ← always regenerated
├── index.qmd                 ← generated once, then hand-editable
└── content/
    ├── modules/
    ├── slides/
    ├── handouts/
    ├── notes/
    ├── assignments/
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

### Building the documentation

```bash
quarto render docs_src/      # output → docs/
```

### Package layout

```
src/quarto_coursegen/
├── cli.py            ← Typer app (init, generate commands)
├── config.py         ← CoursegenConfig, resolve_config, i18n loading
├── core.py           ← pure logic (normalize, resolve, collect)
├── env.py            ← Jinja2 environment factory
├── generators.py     ← generate() and per-file generator functions
├── initializer.py    ← init_project()
├── writer.py         ← write_file() with Rich output
└── package_data/
    ├── skeleton/     ← files copied by init (course.yaml, Makefile, …)
    ├── templates/    ← built-in Jinja2 templates
    └── lang/         ← built-in i18n files
```
