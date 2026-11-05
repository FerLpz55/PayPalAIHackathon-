"""Comprobaciones automáticas de dependencias y pureza de capas."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "tallerclaro"

FORBIDDEN_FOR_INNER_LAYERS = {
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_settings",
    "httpx",
    "psycopg",
    "bcrypt",
    "tallerclaro.bootstrap",
    "tallerclaro.infrastructure",
    "tallerclaro.presentation",
    "tallerclaro.main",
}


def _python_files(relative: str) -> list[Path]:
    return sorted((SRC_ROOT / relative).rglob("*.py"))


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _is_forbidden(module: str) -> bool:
    return any(
        module == forbidden or module.startswith(f"{forbidden}.")
        for forbidden in FORBIDDEN_FOR_INNER_LAYERS
    )


@pytest.mark.parametrize("layer", ["domain", "application"])
def test_inner_layers_do_not_import_frameworks_or_outer_layers(layer):
    violations = []
    for path in _python_files(layer):
        for module in _imported_modules(path):
            if _is_forbidden(module):
                violations.append(f"{path.relative_to(SRC_ROOT)} -> {module}")
    assert violations == []


def test_application_does_not_import_presentation_or_infrastructure_symbols():
    for path in _python_files("application"):
        source = path.read_text(encoding="utf-8")
        assert "from tallerclaro.infrastructure" not in source
        assert "from tallerclaro.presentation" not in source
        assert "from tallerclaro.bootstrap" not in source


def test_application_does_not_sum_money_amounts():
    """La suma de importes es responsabilidad del dominio, no de los casos de uso."""
    offenders = []
    for path in _python_files("application"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sum":
                offenders.append(str(path.relative_to(SRC_ROOT)))
    assert offenders == []


def test_presentation_does_not_import_decimal_or_money():
    for path in _python_files("presentation"):
        modules = _imported_modules(path)
        assert "decimal" not in modules, path
        assert "tallerclaro.domain.value_objects" not in modules, path
        assert not any(module.endswith(".value_objects") for module in modules), path


def test_domain_does_not_import_application_or_outer_layers():
    for path in _python_files("domain"):
        for module in _imported_modules(path):
            assert not module.startswith("tallerclaro.application"), f"{path} -> {module}"
            assert not _is_forbidden(module), f"{path} -> {module}"


def test_application_interfaces_only_depend_on_domain_and_dtos():
    modules = _imported_modules(SRC_ROOT / "application" / "interfaces.py")
    internal = {module for module in modules if module.startswith("tallerclaro.")}
    assert internal <= {
        "tallerclaro.application.dtos",
        "tallerclaro.domain.entities",
    }
