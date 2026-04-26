"""
tests/test_generate.py — Tests for quarto_coursegen.

Adapted from the original course-template tests. All imports now point to the
quarto_coursegen package. Integration tests use CoursegenConfig directly instead
of monkeypatching global module variables — the new API is path-parameterised.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Generator

import pytest
import yaml

from quarto_coursegen.core import (
    apply_defaults,
    collect_subproject_files,
    default_artifact_path,
    has_website_artifacts,
    normalize_artifact,
    resolve_stub_template,
    subdir_for_type,
)
from quarto_coursegen.config import (
    BUILTIN_LANG_DIR,
    BUILTIN_TEMPLATES_DIR,
    CoursegenConfig,
    load_course,
    load_i18n,
)
from quarto_coursegen.generators import generate
from quarto_coursegen.initializer import SKELETON_DIR, init_project

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

MINIMAL_COURSE_YAML = textwrap.dedent("""\
    course:
      id: test-course
      title: "Test Course"
      semester: "WS 2026"
      language: "en"
      ects: 3
      instructors:
        - name: "Prof. Test"
          email: "test@example.com"
          role: "lecturer"
      organization:
        institution: "Test University"
        department: "Dept. of Testing"
      defaults:
        status: planned
        visibility: public
        duration: 90
      schedule:
        start_date: 2026-10-01
        end_date: 2027-01-31
        weekly_day: "Monday"

    artifacts:
      - id: syllabus
        type: syllabus
        enabled: true
        file: "content/syllabus.qmd"

    modules:
      - id: intro
        type: lecture
        title: "Introduction"
        date: 2026-10-01
        status: published
        learning_objectives: |
          - Objective A
          - Objective B
        artifacts:
          - id: intro-slides
            type: slides
            enabled: true
            output_formats: [revealjs, beamer]
          - id: intro-handout
            type: handout
            enabled: true
            output_formats: [pdf]
          - id: intro-notes
            type: notes
            enabled: true
            output_formats: [website]
          - id: intro-assignment
            type: assignment
            enabled: false

      - id: topic-a
        type: lecture
        title: "Topic A"
        date: 2026-10-08
        artifacts:
          - id: topic-a-slides
            type: slides
            enabled: false
    """)


@pytest.fixture()
def course_yaml_file(tmp_path: Path) -> Path:
    p = tmp_path / "course.yaml"
    p.write_text(MINIMAL_COURSE_YAML, encoding="utf-8")
    return p


@pytest.fixture()
def course_data() -> dict:
    return yaml.safe_load(MINIMAL_COURSE_YAML)


def _make_config(course_yaml: Path, tmp_path: Path, *, force: bool = False, dry_run: bool = False) -> CoursegenConfig:
    """Helper: build a CoursegenConfig pointing output to tmp_path."""
    return CoursegenConfig(
        course_yaml=course_yaml,
        output_root=tmp_path,
        templates_dirs=[BUILTIN_TEMPLATES_DIR],
        lang_dirs=[BUILTIN_LANG_DIR],
        force=force,
        dry_run=dry_run,
    )


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------

class TestApplyDefaults:
    def test_missing_keys_filled(self) -> None:
        modules = [{"id": "m1", "title": "M1"}]
        apply_defaults(modules, {"status": "planned", "duration": 90})
        assert modules[0]["status"] == "planned"
        assert modules[0]["duration"] == 90

    def test_existing_keys_not_overwritten(self) -> None:
        modules = [{"id": "m1", "status": "published"}]
        apply_defaults(modules, {"status": "planned"})
        assert modules[0]["status"] == "published"


class TestNormalizeArtifact:
    def test_id_generated_from_type(self) -> None:
        a = {"type": "slides", "output_formats": ["revealjs"]}
        normalize_artifact(a, 0)
        assert a["id"] == "slides-0"

    def test_id_generated_without_type(self) -> None:
        a = {"output_formats": ["pdf"]}
        normalize_artifact(a, 2)
        assert a["id"] == "artifact-2"

    def test_explicit_id_preserved(self) -> None:
        a = {"id": "my-slides", "type": "slides"}
        normalize_artifact(a, 0)
        assert a["id"] == "my-slides"

    def test_enabled_defaults_to_true(self) -> None:
        a = {"type": "slides"}
        normalize_artifact(a, 0)
        assert a["enabled"] is True

    def test_explicit_enabled_false_preserved(self) -> None:
        a = {"type": "slides", "enabled": False}
        normalize_artifact(a, 0)
        assert a["enabled"] is False

    def test_status_defaults_to_planned(self) -> None:
        a = {"type": "slides"}
        normalize_artifact(a, 0)
        assert a["status"] == "planned"


class TestSubdirForType:
    @pytest.mark.parametrize("art_type,expected", [
        ("slides",     "slides"),
        ("handout",    "handouts"),
        ("notes",      "notes"),
        ("assignment", "assignments"),
        ("syllabus",   ""),
        ("custom",     "custom"),
        (None,         ""),
    ])
    def test_known_and_unknown_types(self, art_type: str | None, expected: str) -> None:
        assert subdir_for_type(art_type) == expected


class TestDefaultArtifactPath:
    @pytest.mark.parametrize("artifact,scope_id,expected", [
        ({"type": "slides"},     "intro", "content/slides/intro-slides.qmd"),
        ({"type": "handout"},    "intro", "content/handouts/intro-handout.qmd"),
        ({"type": "notes"},      "intro", "content/notes/intro-notes.qmd"),
        ({"type": "assignment"}, "intro", "content/assignments/intro-assignment.qmd"),
        ({"type": "syllabus"},   None,    "content/syllabus.qmd"),
        ({"type": "custom"},     "intro", "content/custom/intro-custom.qmd"),
        ({"type": "custom"},     None,    "content/custom/custom.qmd"),
    ])
    def test_default_paths(self, artifact: dict, scope_id: str | None, expected: str) -> None:
        assert default_artifact_path(artifact, scope_id) == expected


class TestResolveStubTemplate:
    def test_explicit_string_stub_template(self, tmp_path: Path) -> None:
        artifact = {"type": "slides", "stub_template": "slides.qmd.j2"}
        assert resolve_stub_template(artifact, [tmp_path]) == "slides.qmd.j2"

    def test_explicit_dict_format_match(self, tmp_path: Path) -> None:
        artifact = {
            "type": "slides",
            "output_formats": ["pdf"],
            "stub_template": {"pdf": "pdf-slides.qmd.j2", "default": "slides.qmd.j2"},
        }
        assert resolve_stub_template(artifact, [tmp_path]) == "pdf-slides.qmd.j2"

    def test_explicit_dict_default_fallback(self, tmp_path: Path) -> None:
        artifact = {
            "type": "slides",
            "output_formats": ["revealjs"],
            "stub_template": {"default": "custom-default.qmd.j2"},
        }
        assert resolve_stub_template(artifact, [tmp_path]) == "custom-default.qmd.j2"

    def test_resolution_type_template(self, tmp_path: Path) -> None:
        (tmp_path / "slides.qmd.j2").write_text("x")
        artifact = {"type": "slides", "output_formats": ["revealjs"]}
        assert resolve_stub_template(artifact, [tmp_path]) == "slides.qmd.j2"

    def test_resolution_type_format_before_type(self, tmp_path: Path) -> None:
        (tmp_path / "slides.qmd.j2").write_text("x")
        (tmp_path / "slides.revealjs.qmd.j2").write_text("x")
        artifact = {"type": "slides", "output_formats": ["revealjs"]}
        assert resolve_stub_template(artifact, [tmp_path]) == "slides.revealjs.qmd.j2"

    def test_resolution_id_before_type(self, tmp_path: Path) -> None:
        (tmp_path / "slides.qmd.j2").write_text("x")
        (tmp_path / "my-deck.qmd.j2").write_text("x")
        artifact = {"id": "my-deck", "type": "slides", "output_formats": ["revealjs"]}
        assert resolve_stub_template(artifact, [tmp_path]) == "my-deck.qmd.j2"

    def test_resolution_falls_back_to_default(self, tmp_path: Path) -> None:
        (tmp_path / "default_template.qmd.j2").write_text("x")
        artifact = {"type": "unknown-type", "output_formats": []}
        assert resolve_stub_template(artifact, [tmp_path]) == "default_template.qmd.j2"

    def test_resolution_returns_default_even_if_missing(self, tmp_path: Path) -> None:
        artifact = {"type": "no-such-type"}
        assert resolve_stub_template(artifact, [tmp_path]) == "default_template.qmd.j2"

    def test_local_dir_takes_priority_over_builtin(self, tmp_path: Path) -> None:
        """A template in the first dir shadows one in the second dir."""
        dir_a = tmp_path / "a"
        dir_a.mkdir()
        dir_b = tmp_path / "b"
        dir_b.mkdir()
        (dir_b / "slides.qmd.j2").write_text("builtin")
        (dir_a / "slides.qmd.j2").write_text("local-override")
        artifact = {"type": "slides", "output_formats": []}
        assert resolve_stub_template(artifact, [dir_a, dir_b]) == "slides.qmd.j2"


class TestLoadI18n:
    def test_english_defaults_without_lang_dir(self, tmp_path: Path) -> None:
        course = {"language": "en"}
        i18n = load_i18n(course, [tmp_path])
        assert i18n["nav"]["home"] == "Home"
        assert i18n["artifact_labels"]["notes"] == "Notes"

    def test_lang_file_overrides_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "de.yaml").write_text(
            "nav:\n  home: Startseite\nartifact_labels:\n  notes: Mitschrift\n",
            encoding="utf-8",
        )
        course = {"language": "de"}
        i18n = load_i18n(course, [tmp_path])
        assert i18n["nav"]["home"] == "Startseite"
        assert i18n["artifact_labels"]["notes"] == "Mitschrift"

    def test_lang_file_partial_override_keeps_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "de.yaml").write_text(
            "nav:\n  home: Startseite\n",
            encoding="utf-8",
        )
        course = {"language": "de"}
        i18n = load_i18n(course, [tmp_path])
        assert i18n["nav"]["home"] == "Startseite"
        assert i18n["artifact_labels"]["slides"] == "Slides"

    def test_inline_i18n_overrides_lang_file(self, tmp_path: Path) -> None:
        (tmp_path / "de.yaml").write_text(
            "assignment:\n  title_suffix: Übungsblatt\n",
            encoding="utf-8",
        )
        course = {
            "language": "de",
            "i18n": {"assignment": {"title_suffix": "Hausaufgabe"}},
        }
        i18n = load_i18n(course, [tmp_path])
        assert i18n["assignment"]["title_suffix"] == "Hausaufgabe"

    def test_missing_language_falls_back_to_english(self, tmp_path: Path) -> None:
        course = {"language": "fr"}  # no fr.yaml file
        i18n = load_i18n(course, [tmp_path])
        assert i18n["nav"]["home"] == "Home"

    def test_no_language_key_uses_english(self, tmp_path: Path) -> None:
        course: dict = {}
        i18n = load_i18n(course, [tmp_path])
        assert i18n["nav"]["home"] == "Home"

    def test_deep_merge_does_not_mutate_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "de.yaml").write_text(
            "nav:\n  home: Startseite\n", encoding="utf-8"
        )
        i18n1 = load_i18n({"language": "de"}, [tmp_path])
        i18n2 = load_i18n({"language": "en"}, [tmp_path])
        assert i18n1["nav"]["home"] == "Startseite"
        assert i18n2["nav"]["home"] == "Home"

    def test_builtin_lang_dir_has_de(self) -> None:
        """Built-in lang/ contains de.yaml with German translations."""
        i18n = load_i18n({"language": "de"}, [BUILTIN_LANG_DIR])
        assert i18n["nav"]["home"] != "Home"  # should be German


class TestHasWebsiteArtifacts:
    def test_detects_website_format(self) -> None:
        modules = [{"artifacts": [{"enabled": True, "output_formats": ["website"]}]}]
        assert has_website_artifacts(modules) is True

    def test_returns_false_when_no_website(self) -> None:
        modules = [{"artifacts": [{"enabled": True, "output_formats": ["revealjs"]}]}]
        assert has_website_artifacts(modules) is False

    def test_disabled_artifacts_ignored(self) -> None:
        modules = [{"artifacts": [{"enabled": False, "output_formats": ["website"]}]}]
        assert has_website_artifacts(modules) is False

    def test_enabled_defaults_to_true(self) -> None:
        modules = [{"artifacts": [{"output_formats": ["website"]}]}]
        assert has_website_artifacts(modules) is True


class TestCollectSubprojectFiles:
    def test_slides_detected(self, course_data: dict) -> None:
        modules = course_data["modules"]
        for m in modules:
            m["artifacts"] = [normalize_artifact(a, i) for i, a in enumerate(m.get("artifacts") or [])]
        result = collect_subproject_files(modules)
        assert "intro-slides.qmd" in result["slides"]

    def test_pdf_handout_detected(self, course_data: dict) -> None:
        modules = course_data["modules"]
        for m in modules:
            m["artifacts"] = [normalize_artifact(a, i) for i, a in enumerate(m.get("artifacts") or [])]
        result = collect_subproject_files(modules)
        assert "intro-handout.qmd" in result["handouts"]

    def test_disabled_slides_not_included(self, course_data: dict) -> None:
        modules = course_data["modules"]
        for m in modules:
            m["artifacts"] = [normalize_artifact(a, i) for i, a in enumerate(m.get("artifacts") or [])]
        result = collect_subproject_files(modules)
        assert "topic-a-slides.qmd" not in result["slides"]

    def test_website_only_artifact_not_in_subprojects(self) -> None:
        modules = [{"id": "m1", "artifacts": [
            {"type": "notes", "enabled": True, "output_formats": ["website"]},
        ]}]
        result = collect_subproject_files(modules)
        assert result["slides"] == []
        assert result["handouts"] == []
        assert result["assignments"] == []

    def test_assignment_pdf_goes_to_assignments(self) -> None:
        modules = [{"id": "m1", "artifacts": [
            {"type": "assignment", "enabled": True, "output_formats": ["website", "pdf"]},
        ]}]
        result = collect_subproject_files(modules)
        assert "m1-assignment.qmd" in result["assignments"]
        assert result["handouts"] == []

    def test_course_level_slides_routed(self) -> None:
        modules: list[dict] = []
        course_artifacts = [
            {"type": "slides", "enabled": True, "file": "content/slides/overview.qmd",
             "output_formats": ["revealjs"]},
        ]
        result = collect_subproject_files(modules, course_artifacts)
        assert "overview.qmd" in result["slides"]


# ---------------------------------------------------------------------------
# Integration tests: generator writes expected files
# ---------------------------------------------------------------------------

class TestGeneratorIntegration:
    """Integration tests that actually run the generator and inspect the output.

    The new generate() function takes a CoursegenConfig, so no monkeypatching is
    needed — output is routed to tmp_path via output_root.
    """

    def test_dry_run_creates_no_files(self, course_yaml_file: Path, tmp_path: Path) -> None:
        cfg = _make_config(course_yaml_file, tmp_path, dry_run=True)
        generate(cfg)
        assert list(tmp_path.rglob("*.qmd")) == []

    def test_module_stubs_created(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        assert (tmp_path / "content" / "modules" / "intro.qmd").exists()
        assert (tmp_path / "content" / "modules" / "topic-a.qmd").exists()

    def test_enabled_artifact_stubs_created(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        assert (tmp_path / "content" / "slides" / "intro-slides.qmd").exists()
        assert (tmp_path / "content" / "handouts" / "intro-handout.qmd").exists()
        assert (tmp_path / "content" / "notes" / "intro-notes.qmd").exists()
        # assignment is disabled — must NOT be created
        assert not (tmp_path / "content" / "assignments" / "intro-assignment.qmd").exists()

    def test_disabled_artifact_not_created(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        assert not (tmp_path / "content" / "slides" / "topic-a-slides.qmd").exists()

    def test_no_overwrite_by_default(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        target = tmp_path / "content" / "modules" / "intro.qmd"
        target.write_text("MANUALLY EDITED", encoding="utf-8")
        generate(_make_config(course_yaml_file, tmp_path))
        assert target.read_text() == "MANUALLY EDITED"

    def test_force_overwrites(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        target = tmp_path / "content" / "modules" / "intro.qmd"
        target.write_text("MANUALLY EDITED", encoding="utf-8")
        generate(_make_config(course_yaml_file, tmp_path, force=True))
        assert target.read_text() != "MANUALLY EDITED"

    def test_nav_config_always_regenerated(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        nav = tmp_path / "_quarto-nav.yml"
        assert nav.exists()
        nav.write_text("CUSTOM CONTENT", encoding="utf-8")
        generate(_make_config(course_yaml_file, tmp_path))
        assert nav.read_text() != "CUSTOM CONTENT"

    def test_syllabus_created_from_course_artifact(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        syllabus = tmp_path / "content" / "syllabus.qmd"
        assert syllabus.exists()
        text = syllabus.read_text()
        assert "Introduction" in text
        assert "Topic A" in text

    def test_slides_subproject_config_created(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        config = tmp_path / "content" / "slides" / "_quarto.yml"
        assert config.exists()
        text = config.read_text()
        assert "intro-slides.qmd" in text
        assert "topic-a-slides.qmd" not in text

    def test_handouts_subproject_config_created(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        config = tmp_path / "content" / "handouts" / "_quarto.yml"
        assert config.exists()
        assert "intro-handout.qmd" in config.read_text()

    def test_subproject_config_always_regenerated(self, course_yaml_file: Path, tmp_path: Path) -> None:
        generate(_make_config(course_yaml_file, tmp_path))
        config = tmp_path / "content" / "slides" / "_quarto.yml"
        config.write_text("CUSTOM CONTENT", encoding="utf-8")
        generate(_make_config(course_yaml_file, tmp_path))
        assert config.read_text() != "CUSTOM CONTENT"

    def test_no_subproject_config_when_all_disabled(self, tmp_path: Path) -> None:
        data = yaml.safe_load(MINIMAL_COURSE_YAML)
        for m in data["modules"]:
            for a in (m.get("artifacts") or []):
                a["enabled"] = False
        course_yaml = tmp_path / "course.yaml"
        course_yaml.write_text(yaml.dump(data), encoding="utf-8")
        generate(_make_config(course_yaml, tmp_path))
        assert not (tmp_path / "content" / "slides" / "_quarto.yml").exists()

    def test_local_templates_dir_overlay(self, course_yaml_file: Path, tmp_path: Path) -> None:
        """A local templates/ dir can override built-in templates."""
        local_tmpl = tmp_path / "mytemplates"
        local_tmpl.mkdir()
        # Override module template with a trivially identifiable stub
        (local_tmpl / "module.qmd.j2").write_text("CUSTOM_MODULE_TEMPLATE", encoding="utf-8")

        cfg = CoursegenConfig(
            course_yaml=course_yaml_file,
            output_root=tmp_path,
            templates_dirs=[local_tmpl, BUILTIN_TEMPLATES_DIR],
            lang_dirs=[BUILTIN_LANG_DIR],
        )
        generate(cfg)
        content = (tmp_path / "content" / "modules" / "intro.qmd").read_text()
        assert content == "CUSTOM_MODULE_TEMPLATE"


# ---------------------------------------------------------------------------
# Tests: init_project
# ---------------------------------------------------------------------------

class TestInitProject:
    """Tests for quarto_coursegen.initializer.init_project."""

    SKELETON_FILES = {
        "course.yaml",
        "Makefile",
        "styles/custom.scss",
        "styles/slides.scss",
        ".gitignore",
    }

    def _relative_files(self, root: Path) -> set[str]:
        return {
            str(f.relative_to(root)).replace("\\", "/")
            for f in root.rglob("*")
            if f.is_file()
        }

    def _expected_files(self) -> set[str]:
        tmpl = {
            "templates/" + f.name
            for f in BUILTIN_TEMPLATES_DIR.iterdir()
            if f.is_file()
        }
        lang = {
            "lang/" + f.name
            for f in BUILTIN_LANG_DIR.iterdir()
            if f.is_file()
        }
        return self.SKELETON_FILES | tmpl | lang

    def test_copies_all_skeleton_files(self, tmp_path: Path) -> None:
        init_project(tmp_path)
        assert self._relative_files(tmp_path) == self._expected_files()

    def test_templates_dir_populated(self, tmp_path: Path) -> None:
        init_project(tmp_path)
        tmpl_dir = tmp_path / "templates"
        assert tmpl_dir.is_dir()
        assert any(tmpl_dir.glob("*.j2"))

    def test_lang_dir_populated(self, tmp_path: Path) -> None:
        init_project(tmp_path)
        lang_dir = tmp_path / "lang"
        assert lang_dir.is_dir()
        assert (lang_dir / "en.yaml").exists()
        assert (lang_dir / "de.yaml").exists()

    def test_creates_target_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "new-course"
        assert not target.exists()
        init_project(target)
        assert target.is_dir()
        assert (target / "course.yaml").exists()

    def test_course_yaml_is_valid_yaml(self, tmp_path: Path) -> None:
        init_project(tmp_path)
        data = yaml.safe_load((tmp_path / "course.yaml").read_text())
        assert "course" in data
        assert "modules" in data

    def test_makefile_has_rendering_targets(self, tmp_path: Path) -> None:
        init_project(tmp_path)
        makefile = (tmp_path / "Makefile").read_text()
        for target in ("website", "slides", "handouts", "assignments", "all", "clean"):
            assert f"{target}:" in makefile

    def test_makefile_has_no_generate_target(self, tmp_path: Path) -> None:
        """The Makefile should not contain a generate target — that's the CLI."""
        init_project(tmp_path)
        makefile = (tmp_path / "Makefile").read_text()
        assert "generate:" not in makefile

    def test_skip_existing_files_by_default(self, tmp_path: Path) -> None:
        (tmp_path / "course.yaml").write_text("CUSTOM", encoding="utf-8")
        init_project(tmp_path)
        assert (tmp_path / "course.yaml").read_text() == "CUSTOM"

    def test_force_overwrites_existing_files(self, tmp_path: Path) -> None:
        (tmp_path / "course.yaml").write_text("CUSTOM", encoding="utf-8")
        init_project(tmp_path, force=True)
        content = (tmp_path / "course.yaml").read_text()
        assert content != "CUSTOM"
        assert "course:" in content

    def test_dry_run_creates_no_files(self, tmp_path: Path) -> None:
        target = tmp_path / "dry-course"
        init_project(target, dry_run=True)
        assert not target.exists()

    def test_skeleton_dir_contains_expected_files(self) -> None:
        """Sanity check: the bundled skeleton has the expected files."""
        skeleton_files = {
            str(f.relative_to(SKELETON_DIR)).replace("\\", "/")
            for f in SKELETON_DIR.rglob("*")
            if f.is_file()
        }
        assert self.SKELETON_FILES == skeleton_files
