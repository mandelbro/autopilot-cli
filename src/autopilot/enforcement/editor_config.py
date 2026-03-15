"""Layer 1: Editor-time configuration generation (Task 060, RFC 3.5.2).

Generates ruff and pyright configuration covering all 11 enforcement
categories for sub-100ms editor feedback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from pathlib import Path

# Ruff rule codes mapped to enforcement categories
_CATEGORY_RULES: dict[str, list[str]] = {
    "duplication": ["TID251"],
    "conventions": ["I", "N"],
    "overengineering": ["C901", "SIM"],
    "security": ["S"],
    "error_handling": ["BLE", "TRY"],
    "dead_code": ["F401", "F841", "ERA"],
    "type_safety": ["ANN"],
    "test_quality": ["PT"],
    "comments": ["ERA"],
    "deprecated": ["UP"],
    "async_misuse": ["ASYNC"],
}


def generate_ruff_config(project_type: str = "python") -> dict[str, Any]:
    """Produce a ruff configuration dict covering all 11 categories.

    Returns a dict suitable for merging into ``[tool.ruff]`` in
    pyproject.toml.
    """
    all_codes: set[str] = set()
    for codes in _CATEGORY_RULES.values():
        all_codes.update(codes)

    return {
        "line-length": 100,
        "target-version": "py312" if project_type == "python" else "py311",
        "lint": {
            "select": sorted(all_codes),
            "ignore": ["ANN101", "ANN102"],
        },
        "lint.per-file-ignores": {
            "tests/**/*.py": ["S101", "ANN"],
        },
    }


def generate_pyright_config(project_type: str = "python") -> dict[str, Any]:
    """Produce a pyright strict mode configuration dict.

    Returns a dict suitable for merging into ``[tool.pyright]`` in
    pyproject.toml.
    """
    return {
        "typeCheckingMode": "strict",
        "reportMissingImports": True,
        "reportMissingTypeStubs": False,
        "pythonVersion": "3.12" if project_type == "python" else "3.11",
    }


def apply_to_pyproject(pyproject_path: Path, config: dict[str, Any]) -> None:
    """Merge enforcement configuration into an existing pyproject.toml.

    The merge is additive — existing keys not present in *config* are
    preserved.  If the file does not exist, it is created.
    """
    import tomllib

    existing: dict[str, Any] = {}
    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            existing = tomllib.load(f)

    tool: dict[str, Any] = existing.setdefault("tool", {})
    _deep_merge_into(tool, config)

    # Write back as TOML
    try:
        import tomli_w  # type: ignore[import-not-found]

        pyproject_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pyproject_path, "wb") as f:
            tomli_w.dump(existing, f)  # type: ignore[no-untyped-call]
    except ModuleNotFoundError:
        _write_toml_fallback(pyproject_path, existing)


def _deep_merge_into(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Recursively merge *overlay* into *base*, mutating base in place."""
    for key, value in overlay.items():
        base_val = base.get(key)
        if base_val is not None and isinstance(base_val, dict) and isinstance(value, dict):
            _deep_merge_into(cast("dict[str, Any]", base_val), cast("dict[str, Any]", value))
        else:
            base[key] = value


def _write_toml_fallback(path: Path, data: dict[str, Any]) -> None:
    """Write a minimal TOML representation when tomli_w is unavailable."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    _toml_section(lines, data, [])
    path.write_text("\n".join(lines) + "\n")


def _toml_section(lines: list[str], data: dict[str, Any], prefix: list[str]) -> None:
    """Recursively emit TOML sections."""
    simple: dict[str, Any] = {}
    nested: dict[str, dict[str, Any]] = {}

    for key, value in data.items():
        if isinstance(value, dict):
            nested[key] = value
        else:
            simple[key] = value

    if prefix and simple or prefix and not simple and not nested:
        lines.append(f"[{'.'.join(prefix)}]")

    for key, value in simple.items():
        lines.append(f"{key} = {_toml_value(value)}")

    for key, sub in nested.items():
        _toml_section(lines, sub, [*prefix, key])


def _toml_value(value: Any) -> str:
    """Convert a Python value to a TOML literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, list):
        import json

        return json.dumps(value)
    return repr(value)
