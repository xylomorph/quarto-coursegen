# 🎓 quarto-coursegen

<div align="center">
  <p align="center">
 📖 <a href="https://sebastiancacean.de/quarto-coursegen">Documentation</a>
 </p>
</div>
<br/>

A CLI tool that scaffolds [Quarto](https://quarto.org/) course websites from a
single `course.yaml` definition file.


## ✨ Features

- **Single source of truth** — define your entire course (modules, artifacts, schedule, instructors) in one `course.yaml` file
- **Two-stage pipeline** — separate *generation* (scaffold `.qmd` stubs + Quarto config) from *rendering* (Quarto → HTML/PDF)
- **Multiple output formats** — reveal.js slides, Beamer PDF, HTML handouts, PDF assignments, and a full course website from the same source
- **Smart overwrite policy** — stubs are never overwritten after the first run; navigation and sub-project configs are always kept up to date
- **Customisable templates** — override any built-in Jinja2 template locally without forking the tool
- **i18n support** — UI strings and labels are externalised in `lang/*.yaml` (English and German included)
- **`init` command** — bootstraps a ready-to-use course repo with a sensible directory structure in one step


## 📦 Installation

Requires Python ≥ 3.11.

```bash
pip install quarto-coursegen
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install quarto-coursegen
```


## 🚀 Quick Start

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
i18n, rendering guide, Python API — see the **[documentation](https://sebastiancacean.de/quarto-coursegen/)**.


## 📁 Project layout (generated course repo)

```
course-repo/
│  ← quarto-coursegen init
├── course.yaml               ← edit this: title, modules, artifacts
├── Makefile                  ← rendering targets (make website / slides / …)
├── assets/
│   └── styles/
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


## 🧑‍💻 Development

```bash
git clone https://github.com/xylomorph/quarto-coursegen.git
cd quarto-coursegen
uv sync --dev
uv run pytest
```

### 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python ≥ 3.11 |
| CLI framework | [Typer](https://typer.tiangolo.com/) |
| Templating | [Jinja2](https://jinja.palletsprojects.com/) |
| Config parsing | [PyYAML](https://pyyaml.org/) + [Pydantic](https://docs.pydantic.dev/) |
| Output formatting | [Rich](https://github.com/Textualize/rich) |
| Publishing | [Quarto](https://quarto.org/) |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Testing | [pytest](https://pytest.org/) |


### 📚 Building the documentation

```bash
quarto render docs_src/      # output → docs/
```

### 🗂️ Package layout

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
