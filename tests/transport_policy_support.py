"""Conservative source/build dependency scan, not a whole-repository word search.

Documentation can describe removed tools. Python docstrings and comments are
not command dependencies. Literal runtime references (including constant
concatenations) and packaging/launcher text remain checked. This static scan
is not a proof against every dynamically constructed command.
"""
from __future__ import annotations

import ast
from pathlib import Path


_SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".flatpak-builder", "node_modules"}
_CONFIG_SUFFIXES = {".sh", ".bash", ".yml", ".yaml", ".json", ".desktop", ".service", ".timer", ".toml", ".cfg", ".ini", ".xml"}


def _constant_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = _constant_string(node.left), _constant_string(node.right)
        if left is not None and right is not None:
            return left + right
    return None


def _python_strings(text: str) -> list[str]:
    tree = ast.parse(text)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.body and isinstance(node.body[0], ast.Expr):
                value = node.body[0].value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    docstrings.add(id(value))
    values = []
    for node in ast.walk(tree):
        if id(node) in docstrings:
            continue
        value = _constant_string(node)
        if value is not None:
            values.append(value)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            values.extend(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                values.append(node.module)
    return values


def transport_references(root: Path, token: str) -> list[str]:
    hits = []
    token = token.casefold()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        # Test fixtures intentionally describe disallowed commands. They are
        # checked against this scanner in an independent temporary runtime tree.
        if any(part in _SKIP_DIRS for part in rel.parts) or rel.parts[0] == "tests":
            continue
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix == ".py":
            values = _python_strings(path.read_text(encoding="utf-8"))
        elif path.suffix.lower() in _CONFIG_SUFFIXES or path.name in {"Makefile", "meson.build", "CMakeLists.txt"}:
            # Keep this deliberately conservative: config comments may produce
            # review findings, but command/dependency configuration is not skipped.
            values = [path.read_text(encoding="utf-8")]
        else:
            continue
        if any(token in value.casefold() for value in values):
            hits.append(rel.as_posix())
    return hits
