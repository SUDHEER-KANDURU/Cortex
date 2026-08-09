"""Language-specific rules for naming, documentation, and structural checks.

DO NOT apply Python rules to Java.
DO NOT apply Java rules to TypeScript.

Each language module defines:
  - naming_ok(name, symbol_type) -> bool
  - has_doc_support() -> bool
  - is_supported() -> bool
  - description() -> str
"""

from __future__ import annotations
import re
from typing import Literal

SymbolType = Literal["function", "method", "class", "variable", "module"]


class PythonRules:
    """PEP 8 naming conventions for Python."""

    _SNAKE   = re.compile(r'^[a-z_][a-z0-9_]*$')
    _PASCAL  = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
    _DUNDER  = re.compile(r'^__[a-z][a-z0-9_]*__$')
    _PRIVATE = re.compile(r'^_[a-z][a-z0-9_]*$')
    _SUNDER  = re.compile(r'^_[A-Z][a-zA-Z0-9]*$')  # _MyClass pattern

    # Single-letter names that are idiomatic in Python
    _IDIOMATIC_SINGLES = frozenset("ijknxyzefghst")

    def naming_ok(self, name: str, symbol_type: SymbolType) -> bool:
        if symbol_type in ("function", "method"):
            if self._dunder_ok(name):  return True
            if self._private_ok(name): return True
            if self._single_ok(name):  return True
            return bool(self._SNAKE.match(name))
        if symbol_type == "class":
            if self._sunder_ok(name): return True
            return bool(self._PASCAL.match(name))
        return True  # variables/modules: not checked at this level

    def is_idiomatic_short(self, name: str) -> bool:
        """Short names that are idiomatic in Python (loop vars, coordinates)."""
        if len(name) == 1 and name.lower() in self._IDIOMATIC_SINGLES:
            return True
        if len(name) == 2 and name in ("fn", "id", "db", "ok", "fs", "io", "ip"):
            return True
        return False

    def has_doc_support(self) -> bool:
        return True   # Python has docstrings natively

    def is_supported(self) -> bool:
        return True

    def description(self) -> str:
        return "Python — PEP 8"

    # ── helpers ───────────────────────────────────────────────────────────────
    def _dunder_ok(self, n: str) -> bool: return bool(self._DUNDER.match(n))
    def _private_ok(self, n: str) -> bool: return bool(self._PRIVATE.match(n))
    def _sunder_ok(self, n: str) -> bool: return bool(self._SUNDER.match(n))
    def _single_ok(self, n: str) -> bool: return self.is_idiomatic_short(n)


class JavaRules:
    """Google Java Style Guide naming conventions."""

    _CAMEL   = re.compile(r'^[a-z][a-zA-Z0-9]*$')
    _PASCAL  = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
    _UPPER   = re.compile(r'^[A-Z][A-Z0-9_]*$')  # constants

    _IDIOMATIC_SINGLES = frozenset("ijknxyz")

    def naming_ok(self, name: str, symbol_type: SymbolType) -> bool:
        if symbol_type in ("function", "method"):
            if len(name) == 1 and name in self._IDIOMATIC_SINGLES: return True
            return bool(self._CAMEL.match(name))
        if symbol_type == "class":
            return bool(self._PASCAL.match(name))
        return True

    def is_idiomatic_short(self, name: str) -> bool:
        if len(name) == 1 and name in self._IDIOMATIC_SINGLES: return True
        return False

    def has_doc_support(self) -> bool:
        return True   # Java has JavaDoc

    def is_supported(self) -> bool:
        return True

    def description(self) -> str:
        return "Java — Google Java Style Guide"


class TypeScriptRules:
    """Airbnb / TypeScript naming conventions."""

    _CAMEL   = re.compile(r'^[a-z][a-zA-Z0-9]*$')
    _PASCAL  = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
    _UPPER   = re.compile(r'^[A-Z][A-Z0-9_]*$')

    _IDIOMATIC_SINGLES = frozenset("ijknxyz")

    def naming_ok(self, name: str, symbol_type: SymbolType) -> bool:
        if symbol_type in ("function", "method"):
            if len(name) == 1 and name in self._IDIOMATIC_SINGLES: return True
            return bool(self._CAMEL.match(name)) or bool(self._PASCAL.match(name))
        if symbol_type == "class":
            return bool(self._PASCAL.match(name))
        return True

    def is_idiomatic_short(self, name: str) -> bool:
        return len(name) == 1 and name in self._IDIOMATIC_SINGLES

    def has_doc_support(self) -> bool:
        return True   # JSDoc / TSDoc

    def is_supported(self) -> bool:
        return True

    def description(self) -> str:
        return "TypeScript — Airbnb Style Guide"


class JavaScriptRules(TypeScriptRules):
    def description(self) -> str:
        return "JavaScript — Airbnb Style Guide"


class UnknownLanguageRules:
    """Fallback for unsupported languages — no rules applied."""

    def naming_ok(self, name: str, symbol_type: SymbolType) -> bool:
        return True   # don't flag what we don't understand

    def is_idiomatic_short(self, name: str) -> bool:
        return True

    def has_doc_support(self) -> bool:
        return False

    def is_supported(self) -> bool:
        return False

    def description(self) -> str:
        return "Unknown — no language-specific rules applied"


# ── Registry ──────────────────────────────────────────────────────────────────

_REGISTRY: dict[str, object] = {
    "python":     PythonRules(),
    "java":       JavaRules(),
    "typescript": TypeScriptRules(),
    "javascript": JavaScriptRules(),
}

_UNKNOWN_RULES = UnknownLanguageRules()


def get_rules(language: str):
    """Return the rules object for the given language string."""
    return _REGISTRY.get(language.lower(), _UNKNOWN_RULES)
