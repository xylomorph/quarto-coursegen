"""quarto-coursegen — Scaffold Quarto course websites from a course.yaml definition."""

__version__ = "0.1.0"

from quarto_coursegen.generators import generate
from quarto_coursegen.config import CoursegenConfig, resolve_config

__all__ = ["generate", "CoursegenConfig", "resolve_config", "__version__"]
