"""Symbol table and deterministic reference resolver (Req 3).

A deterministic pre-pass that runs *before* edge building. It is populated
from every ``ParsedFile`` in a repository and then answers two questions the
``GraphBuilder`` asks while wiring CALLS and IMPORTS edges:

    "Which single definition does this call refer to?"
    "Which file does this import statement point at?"

The guiding rule is honesty over coverage: an edge is created *only* when a
reference resolves to exactly one target with confidence. When a reference is
ambiguous or unknown, no edge is fabricated — the caller increments an
``unresolved`` counter instead (Req 3.2, Req 3.4).

Resolution understands:
  - qualified names (``Class.method``) and bare names,
  - the scope hierarchy (same class → same file → imported → repo-unique),
  - relative imports (``from . import x`` / ``from ..pkg import y``),
  - package re-exports (a package ``__init__`` that re-exports a symbol),
  - configured path aliases (e.g. ``tsconfig`` ``paths`` such as ``@/*``).

Everything here is deterministic: the same parsed input, resolved with the
same alias configuration, always yields the same targets — and therefore the
same edges (Req 3.5). Determinism is achieved by never relying on dict/set
iteration order for a decision, sorting any candidate lists on a stable key,
and only ever committing to a resolution when it is unique.

Zero framework dependencies — plain dataclasses consistent with
``graph/domain/entities.py`` style.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from cortex.pipeline.infrastructure.ast_parser import ParsedFile, ParsedImport


def _normalize_path(path: str) -> str:
    """Normalize a repository-relative path to forward-slash form."""
    return path.replace("\\", "/").strip("/")


def _module_key(path: str) -> str:
    """Return the dotted module key for a source path.

    ``backend/app/auth/service.py`` → ``backend.app.auth.service``. The file
    extension (any) is stripped from the final segment. A package initializer
    (``__init__.py`` / ``index.ts`` / ``mod.rs``) collapses to its containing
    package so ``pkg/__init__.py`` → ``pkg``.
    """
    normalized = _normalize_path(path)
    parts = [p for p in normalized.split("/") if p]
    if not parts:
        return ""
    last = parts[-1]
    stem = last.rsplit(".", 1)[0] if "." in last else last
    if stem in ("__init__", "index", "mod"):
        parts = parts[:-1]
    else:
        parts = parts[:-1] + [stem]
    return ".".join(parts)


def _is_package_initializer(path: str) -> bool:
    """Return True when a path is a package entry file (re-export surface)."""
    base = _normalize_path(path).rsplit("/", 1)[-1]
    stem = base.rsplit(".", 1)[0] if "." in base else base
    return stem in ("__init__", "index", "mod")


@dataclass
class Symbol:
    """A single defined symbol (function, method, class, interface, enum...).

    ``qualified_name`` is scoped within its file: ``Class.method`` for methods,
    the bare name for top-level symbols. ``file`` is the repository-relative
    path the symbol is defined in. ``kind`` is a free-form category
    (``"function"``, ``"method"``, ``"class"``, ...). ``span`` is the
    ``(line_start, line_end)`` source range.
    """

    qualified_name: str
    file: str
    kind: str
    span: tuple[int, int] = (0, 0)

    @property
    def simple_name(self) -> str:
        """The last dotted segment (the symbol's own name)."""
        return self.qualified_name.rsplit(".", 1)[-1]


@dataclass(frozen=True)
class ResolvedTarget:
    """The result of a successful resolution.

    Points at a definition by ``file`` plus ``qualified_name`` so the caller
    can locate the corresponding graph node deterministically.
    """

    file: str
    qualified_name: str
    kind: str


@dataclass
class SymbolTable:
    """Per-repository index of symbols, exports, aliases, and module paths.

    Build it once from all ``ParsedFile``s, then call :meth:`resolve` for each
    call reference and :meth:`resolve_import` for each import statement. The
    table never mutates during resolution, so it is safe to reuse and its
    answers are stable.
    """

    #: Configured path aliases, e.g. ``{"@": "src"}`` from ``tsconfig`` paths.
    #: A leading alias segment on an import is rewritten to its target prefix
    #: before module lookup (Req 3.3).
    path_aliases: dict[str, str] = field(default_factory=dict)

    # ── Internal indexes (populated by add / build) ───────────────────────────
    #: All symbols, grouped by simple name → list of Symbol (collision-aware).
    _by_simple: dict[str, list[Symbol]] = field(default_factory=lambda: defaultdict(list))
    #: (file, simple_name) → Symbol — same-file scope lookup.
    _by_file_simple: dict[tuple[str, str], Symbol] = field(default_factory=dict)
    #: (parent_class, method_name) → Symbol — same-class scope lookup.
    _by_class_method: dict[tuple[str, str], Symbol] = field(default_factory=dict)
    #: qualified_name → list of Symbol — exact qualified lookup (collision-aware).
    _by_qualified: dict[str, list[Symbol]] = field(default_factory=lambda: defaultdict(list))
    #: Dotted module key → file path (e.g. ``a.b.c`` → ``a/b/c.py``).
    _module_to_file: dict[str, str] = field(default_factory=dict)
    #: file path → dotted module key.
    _file_to_module: dict[str, str] = field(default_factory=dict)
    #: Exported simple name → list of package module keys that re-export it.
    _reexports: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    #: file path → {import alias/name → module key} for that file.
    _import_aliases: dict[str, dict[str, str]] = field(default_factory=lambda: defaultdict(dict))

    # ── Construction ──────────────────────────────────────────────────────────

    @classmethod
    def from_parsed_files(
        cls,
        parsed_files: list[ParsedFile],
        path_aliases: dict[str, str] | None = None,
    ) -> SymbolTable:
        """Build a fully-populated table from every parsed file (Req 3.1)."""
        table = cls(path_aliases=dict(path_aliases or {}))
        # Sort by path so index construction order is deterministic and the
        # "first definition wins" tie-breaks are stable across runs.
        for parsed_file in sorted(parsed_files, key=lambda pf: pf.path):
            table._ingest_file(parsed_file)
        return table

    def _ingest_file(self, parsed_file: ParsedFile) -> None:
        path = parsed_file.path
        module_key = _module_key(path)
        if module_key:
            self._module_to_file.setdefault(module_key, path)
            self._file_to_module[path] = module_key

        # Top-level functions.
        for fn in parsed_file.functions:
            self.add(fn.qualified_name(), path, "function", (fn.line_start, fn.line_end))

        # Classes, their methods, and re-export surface.
        for cls_def in parsed_file.classes:
            kind = "enum" if cls_def.is_enum else ("interface" if cls_def.is_interface else "class")
            self.add(cls_def.name, path, kind, (cls_def.line_start, cls_def.line_end))
            for method in cls_def.methods:
                self.add(
                    method.qualified_name(),
                    path,
                    "method",
                    (method.line_start, method.line_end),
                )

        # A package initializer's exported names are re-export points: importing
        # the package resolves to a symbol the initializer exposes (Req 3.3).
        if module_key and _is_package_initializer(path):
            for exported in self._exported_simple_names(parsed_file):
                if module_key not in self._reexports[exported]:
                    self._reexports[exported].append(module_key)

        # Import aliases for this file, used later to resolve bare references
        # back to a source module (Req 3.1).
        for imp in parsed_file.imports:
            self._record_import_aliases(path, imp)

    def _exported_simple_names(self, parsed_file: ParsedFile) -> list[str]:
        """Simple names a file defines — its export surface for re-export."""
        names: list[str] = [fn.name for fn in parsed_file.functions]
        names.extend(cls_def.name for cls_def in parsed_file.classes)
        return names

    def _record_import_aliases(self, file_path: str, imp: ParsedImport) -> None:
        module = (imp.module or "").strip()
        if not module:
            return
        aliases = self._import_aliases[file_path]
        # `import a.b.c as x` → alias x maps to module a.b.c
        if imp.alias:
            aliases[imp.alias] = module
        # `from a.b import name` → name maps to module a.b (the source module)
        for name in imp.names:
            aliases.setdefault(name, module)
        # Bare `import a.b.c` → the last segment names the module locally.
        if not imp.names:
            aliases.setdefault(module.split(".")[-1], module)

    def add(self, qualified_name: str, file: str, kind: str, span: tuple[int, int]) -> None:
        """Register a defined symbol (Req 3.1 interface: ``SymbolTable.add``)."""
        symbol = Symbol(qualified_name=qualified_name, file=file, kind=kind, span=span)
        self._by_simple[symbol.simple_name].append(symbol)
        self._by_qualified[qualified_name].append(symbol)
        # First definition per (file, name) / (class, method) wins — stable
        # because files are ingested in sorted path order.
        self._by_file_simple.setdefault((file, symbol.simple_name), symbol)
        if "." in qualified_name:
            parent, method = qualified_name.rsplit(".", 1)
            self._by_class_method.setdefault((parent, method), symbol)

    # ── Resolution ─────────────────────────────────────────────────────────────

    def resolve(
        self,
        reference: str,
        from_file: str,
        imports: set[str] | None = None,
        parent_class: str = "",
    ) -> ResolvedTarget | None:
        """Resolve a call reference to one target, or ``None`` if uncertain.

        Resolution uses the strongest available context first and only commits
        to a repo-wide match when it is unique (Req 3.2, Req 3.5):

          1. ``self.<method>`` → a method of the same class,
          2. a definition in the same file,
          3. an exact qualified-name match (``Class.method``),
          4. an imported symbol that resolves to exactly one definition,
          5. a repo-wide unique definition.

        Ambiguous or unknown references return ``None`` — never a guess.
        """
        imported = imports or set()
        call = (reference or "").strip()
        if not call:
            return None

        parts = call.split(".")
        simple = parts[-1]
        prefix = parts[0] if len(parts) > 1 else ""

        # 1. self.<method> → method of the same class.
        if prefix == "self" and parent_class:
            hit = self._by_class_method.get((parent_class, simple))
            if hit is not None:
                return self._target(hit)

        # 2. Same-file definition.
        hit = self._by_file_simple.get((from_file, simple))
        if hit is not None:
            return self._target(hit)

        # 3. Exact qualified match ("Class.method"), then the trailing pair.
        qualified_hit = self._unique(self._by_qualified.get(call, []))
        if qualified_hit is not None:
            return self._target(qualified_hit)
        if len(parts) >= 2:
            tail = ".".join(parts[-2:])
            qualified_hit = self._unique(self._by_qualified.get(tail, []))
            if qualified_hit is not None:
                return self._target(qualified_hit)

        candidates = self._by_simple.get(simple, [])

        # 4. Imported symbol — only if THIS file imports something of that name
        #    AND the name resolves to exactly one definition repo-wide.
        if (prefix in imported or simple in imported):
            unique = self._unique(candidates)
            if unique is not None:
                return self._target(unique)

        # 5. Repo-wide unique definition — safe because there is no collision.
        unique = self._unique(candidates)
        if unique is not None:
            return self._target(unique)

        return None

    def resolve_import(
        self,
        import_module: str,
        from_file: str,
        imported_names: list[str] | None = None,
        is_relative: bool = False,
    ) -> ResolvedTarget | None:
        """Resolve an import statement to a single target file (Req 3.3).

        Handles relative imports (resolved against ``from_file``'s package),
        configured path aliases, direct module matches, and package
        re-exports. Returns ``None`` when the module cannot be located with
        confidence, so the caller counts it as unresolved rather than
        fabricating an IMPORTS edge (Req 3.2).
        """
        module = (import_module or "").strip()
        if not module:
            return None

        # Relative imports (``from . import x`` / ``from ..pkg import y``).
        if is_relative or module.startswith("."):
            resolved_module = self._resolve_relative_module(module, from_file)
            if resolved_module is None:
                return None
            module = resolved_module
        else:
            module = self._apply_path_alias(module)

        module = module.strip(".")
        if not module:
            return None

        # Direct module → file match.
        target_file = self._module_to_file.get(module)
        if target_file is not None:
            return self._import_target(target_file)

        # Suffix match on the dotted module path (handles package prefixes),
        # only when it resolves to a single file.
        suffix_file = self._unique_module_by_suffix(module)
        if suffix_file is not None:
            return self._import_target(suffix_file)

        # Package re-export: ``from pkg import name`` where ``pkg`` re-exports
        # ``name`` from another module in the package.
        for name in imported_names or []:
            packages = self._reexports.get(name, [])
            for package in packages:
                if package == module or module.endswith(package) or package.endswith(module):
                    target = self._module_to_file.get(package)
                    if target is not None:
                        return self._import_target(target)

        return None

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _apply_path_alias(self, module: str) -> str:
        """Rewrite a leading configured alias segment to its target prefix.

        With ``{"@": "src"}`` an import ``@/auth/service`` becomes
        ``src.auth.service``. Aliases are applied longest-key-first so a more
        specific alias wins deterministically.
        """
        # Normalize path-style separators to dotted form for matching.
        dotted = module.replace("/", ".").strip(".")
        for alias in sorted(self.path_aliases, key=len, reverse=True):
            alias_key = alias.rstrip("/*").rstrip(".")
            if not alias_key:
                continue
            if dotted == alias_key or dotted.startswith(alias_key + "."):
                target = self.path_aliases[alias].rstrip("/*").replace("/", ".").strip(".")
                remainder = dotted[len(alias_key):].strip(".")
                return f"{target}.{remainder}".strip(".") if remainder else target
        return dotted

    def _resolve_relative_module(self, module: str, from_file: str) -> str | None:
        """Resolve a relative import to an absolute dotted module key.

        ``level`` is the number of leading dots; each dot climbs one package
        level from the importing file's package.
        """
        level = len(module) - len(module.lstrip("."))
        remainder = module[level:].strip(".")

        from_module = self._file_to_module.get(from_file)
        if from_module is None:
            from_module = _module_key(from_file)
        base_parts = from_module.split(".") if from_module else []

        # For a plain module file `pkg/handler.py` (module key ``pkg.handler``),
        # a single leading dot refers to its own package, so we drop the
        # filename segment: `from .service` → ``pkg.service`` (climb == level).
        # For a package initializer (`pkg/__init__.py` → key ``pkg``), the
        # filename is already excluded, so a single dot IS the package itself
        # and we drop one fewer segment.
        climb = level
        if _is_package_initializer(from_file):
            climb = level - 1 if level >= 1 else 0
        target_parts = base_parts[: len(base_parts) - climb] if climb <= len(base_parts) else []
        if remainder:
            target_parts = target_parts + remainder.split(".")
        resolved = ".".join(p for p in target_parts if p)
        return resolved or None

    def _unique_module_by_suffix(self, module: str) -> str | None:
        """Return the single file whose module key ends with ``module``."""
        matches = sorted(
            {
                file
                for key, file in self._module_to_file.items()
                if key == module or key.endswith("." + module)
            }
        )
        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def _unique(symbols: list[Symbol]) -> Symbol | None:
        """Return the symbol if the candidate list resolves to exactly one file.

        Multiple definitions in the SAME file (e.g. an overload edge case)
        collapse to the first; definitions across DIFFERENT files are treated
        as ambiguous and rejected — a wrong edge is worse than a missing one.
        """
        if not symbols:
            return None
        distinct_files = sorted({s.file for s in symbols})
        if len(distinct_files) != 1:
            return None
        # Deterministic pick within the single file: lowest span, then name.
        return sorted(symbols, key=lambda s: (s.span, s.qualified_name))[0]

    @staticmethod
    def _target(symbol: Symbol) -> ResolvedTarget:
        return ResolvedTarget(
            file=symbol.file,
            qualified_name=symbol.qualified_name,
            kind=symbol.kind,
        )

    def _import_target(self, file_path: str) -> ResolvedTarget:
        return ResolvedTarget(
            file=file_path,
            qualified_name=self._file_to_module.get(file_path, _module_key(file_path)),
            kind="module",
        )
