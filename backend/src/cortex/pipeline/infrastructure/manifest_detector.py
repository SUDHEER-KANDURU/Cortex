"""Manifest detection — deterministic language/framework identification (Req 2.4).

``ManifestDetector`` parses dependency/build descriptor files
(``package.json``, ``go.mod``, ``pom.xml``, ``Cargo.toml``,
``requirements.txt``, ``*.csproj``, ``Gemfile``) into ``ManifestInfo`` objects.
Each manifest tells us the ecosystem language and, via its declared
dependencies, the frameworks in use — signals the reasoner consumes in
addition to import/label sniffing so framework identification no longer relies
only on scanning source imports.

Everything here is deterministic and offline: standard-library JSON plus small,
tolerant regex/line parsers. A malformed manifest yields an empty-but-valid
``ManifestInfo`` rather than raising, so a broken descriptor never aborts
analysis.
"""

from __future__ import annotations

import json
import os
import re

import structlog
from cortex.pipeline.domain.entities import ManifestDependency, ManifestInfo

logger = structlog.get_logger()


# ── Dependency-name → framework mapping ─────────────────────────────────────────
# Keyed by a lowercased dependency-name substring. A framework is attributed
# when a declared dependency name contains the key. Explicit and deterministic
# so the same manifest always yields the same frameworks.
_FRAMEWORK_BY_DEPENDENCY: dict[str, str] = {
    # JavaScript / TypeScript
    "react": "react",
    "next": "nextjs",
    "express": "express",
    "@nestjs/core": "nestjs",
    "vue": "vue",
    "@angular/core": "angular",
    "svelte": "svelte",
    # Python
    "fastapi": "fastapi",
    "django": "django",
    "flask": "flask",
    "sqlalchemy": "sqlalchemy",
    "pytest": "pytest",
    # Java
    "spring-boot": "spring",
    "spring-core": "spring",
    "spring-context": "spring",
    "springframework": "spring",
    # Go
    "gin-gonic/gin": "gin",
    "labstack/echo": "echo",
    "gofiber/fiber": "fiber",
    # Rust
    "actix-web": "actix",
    "rocket": "rocket",
    "axum": "axum",
    "tokio": "tokio",
    # C#
    "microsoft.aspnetcore": "aspnetcore",
    "microsoft.entityframeworkcore": "entityframework",
    # Ruby
    "rails": "rails",
    "sinatra": "sinatra",
}


def _frameworks_for(dependency_names: list[str]) -> list[str]:
    """Return the sorted, de-duplicated frameworks implied by dependency names."""
    found: set[str] = set()
    for name in dependency_names:
        lowered = name.lower()
        for key, framework in _FRAMEWORK_BY_DEPENDENCY.items():
            if key in lowered:
                found.add(framework)
    return sorted(found)


def _manifest_kind(file_path: str) -> str | None:
    """Classify a path as one of the known manifest kinds, or None.

    Returns a stable kind string: ``package.json`` | ``go.mod`` | ``pom.xml`` |
    ``Cargo.toml`` | ``requirements.txt`` | ``csproj`` | ``Gemfile``.
    """
    base = os.path.basename(file_path)
    lowered = base.lower()
    if lowered == "package.json":
        return "package.json"
    if lowered == "go.mod":
        return "go.mod"
    if lowered == "pom.xml":
        return "pom.xml"
    if lowered == "cargo.toml":
        return "Cargo.toml"
    if lowered == "requirements.txt":
        return "requirements.txt"
    if lowered.endswith(".csproj"):
        return "csproj"
    if lowered == "gemfile":
        return "Gemfile"
    return None


# ── Per-manifest parsers ────────────────────────────────────────────────────────
# Each parser is tolerant: it returns whatever it can extract and never raises.


def _parse_package_json(content: str) -> ManifestInfo:
    """Parse ``package.json`` (npm/yarn). Language is JS/TS by ecosystem.

    TypeScript is reported when ``typescript`` appears as a dependency,
    otherwise JavaScript.
    """
    info = ManifestInfo(source="package.json")
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        return info
    if not isinstance(data, dict):
        return info

    for scope_key, scope in (
        ("dependencies", "runtime"),
        ("devDependencies", "dev"),
        ("peerDependencies", "runtime"),
        ("optionalDependencies", "runtime"),
    ):
        section = data.get(scope_key)
        if isinstance(section, dict):
            for name, version in section.items():
                info.dependencies.append(
                    ManifestDependency(
                        name=str(name),
                        version=str(version) if version is not None else "",
                        scope=scope,
                    )
                )

    names = info.dependency_names()
    if any(n == "typescript" or n.startswith("@types/") for n in names):
        info.languages = ["typescript"]
    else:
        info.languages = ["javascript"]
    info.frameworks = _frameworks_for([d.name for d in info.dependencies])
    return info


_GO_REQUIRE_LINE = re.compile(r"^\s*([^\s]+)\s+(v[^\s]+)")


def _parse_go_mod(content: str) -> ManifestInfo:
    """Parse ``go.mod``. Handles both single ``require x v1`` lines and
    ``require ( ... )`` blocks."""
    info = ManifestInfo(source="go.mod", languages=["go"])
    in_block = False
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        if line.startswith("require") and "(" in line:
            in_block = True
            continue
        if in_block:
            if line.startswith(")"):
                in_block = False
                continue
            match = _GO_REQUIRE_LINE.match(line)
            if match:
                info.dependencies.append(
                    ManifestDependency(
                        name=match.group(1), version=match.group(2), scope="runtime"
                    )
                )
            continue
        if line.startswith("require "):
            rest = line[len("require ") :].strip()
            match = _GO_REQUIRE_LINE.match(rest)
            if match:
                info.dependencies.append(
                    ManifestDependency(
                        name=match.group(1), version=match.group(2), scope="runtime"
                    )
                )
    info.frameworks = _frameworks_for([d.name for d in info.dependencies])
    return info


_POM_DEP = re.compile(
    r"<dependency>(.*?)</dependency>", re.DOTALL | re.IGNORECASE
)
_POM_GROUP = re.compile(r"<groupId>\s*(.*?)\s*</groupId>", re.DOTALL | re.IGNORECASE)
_POM_ARTIFACT = re.compile(
    r"<artifactId>\s*(.*?)\s*</artifactId>", re.DOTALL | re.IGNORECASE
)
_POM_VERSION = re.compile(r"<version>\s*(.*?)\s*</version>", re.DOTALL | re.IGNORECASE)


def _parse_pom_xml(content: str) -> ManifestInfo:
    """Parse Maven ``pom.xml`` dependency coordinates. Language is Java."""
    info = ManifestInfo(source="pom.xml", languages=["java"])
    for block in _POM_DEP.findall(content):
        group = _POM_GROUP.search(block)
        artifact = _POM_ARTIFACT.search(block)
        version = _POM_VERSION.search(block)
        group_id = group.group(1) if group else ""
        artifact_id = artifact.group(1) if artifact else ""
        if not group_id and not artifact_id:
            continue
        name = f"{group_id}:{artifact_id}" if group_id else artifact_id
        info.dependencies.append(
            ManifestDependency(
                name=name,
                version=version.group(1) if version else "",
                scope="runtime",
            )
        )
    info.frameworks = _frameworks_for([d.name for d in info.dependencies])
    return info


_CARGO_DEP_SECTION = re.compile(
    r"^\[(dependencies|dev-dependencies|build-dependencies)\]\s*$"
)
_CARGO_SECTION = re.compile(r"^\[.+\]\s*$")
_CARGO_DEP_LINE = re.compile(r'^\s*([A-Za-z0-9_\-]+)\s*=\s*(.+)$')


def _parse_cargo_toml(content: str) -> ManifestInfo:
    """Parse ``Cargo.toml`` dependency tables. Language is Rust.

    Handles both ``name = "1.0"`` and ``name = { version = "1.0" }`` forms
    without a full TOML parser (stdlib ``tomllib`` is avoided to keep behavior
    identical across the tolerant parsers).
    """
    info = ManifestInfo(source="Cargo.toml", languages=["rust"])
    scope_by_section = {
        "dependencies": "runtime",
        "dev-dependencies": "dev",
        "build-dependencies": "build",
    }
    current_scope: str | None = None
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        dep_section = _CARGO_DEP_SECTION.match(line)
        if dep_section:
            current_scope = scope_by_section[dep_section.group(1)]
            continue
        if _CARGO_SECTION.match(line):
            current_scope = None
            continue
        if current_scope is None:
            continue
        match = _CARGO_DEP_LINE.match(line)
        if not match:
            continue
        name = match.group(1)
        rhs = match.group(2).strip()
        version = ""
        simple = re.match(r'^"([^"]*)"', rhs)
        if simple:
            version = simple.group(1)
        else:
            inline = re.search(r'version\s*=\s*"([^"]*)"', rhs)
            if inline:
                version = inline.group(1)
        info.dependencies.append(
            ManifestDependency(name=name, version=version, scope=current_scope)
        )
    info.frameworks = _frameworks_for([d.name for d in info.dependencies])
    return info


def _parse_requirements_txt(content: str) -> ManifestInfo:
    """Parse ``requirements.txt`` (pip). Language is Python.

    Splits each dependency on the first version specifier and ignores
    comments, blank lines, and option lines (``-r``, ``--hash``, etc.).
    """
    info = ManifestInfo(source="requirements.txt", languages=["python"])
    for raw in content.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        # Strip inline comments and environment markers.
        line = line.split("#", 1)[0].strip()
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z0-9_.\-]+)\s*(.*)$", line)
        if not match:
            continue
        name = match.group(1)
        version = match.group(2).strip()
        info.dependencies.append(
            ManifestDependency(name=name, version=version, scope="runtime")
        )
    info.frameworks = _frameworks_for([d.name for d in info.dependencies])
    return info


_CSPROJ_PACKAGE = re.compile(
    r'<PackageReference\s+Include\s*=\s*"([^"]+)"'
    r'(?:\s+Version\s*=\s*"([^"]+)")?',
    re.IGNORECASE,
)


def _parse_csproj(content: str, source: str = "csproj") -> ManifestInfo:
    """Parse a ``.csproj`` project file's ``<PackageReference>`` entries.
    Language is C#."""
    info = ManifestInfo(source=source, languages=["csharp"])
    for match in _CSPROJ_PACKAGE.finditer(content):
        info.dependencies.append(
            ManifestDependency(
                name=match.group(1),
                version=match.group(2) or "",
                scope="runtime",
            )
        )
    info.frameworks = _frameworks_for([d.name for d in info.dependencies])
    return info


_GEMFILE_GEM = re.compile(
    r"""^\s*gem\s+['"]([^'"]+)['"]\s*(?:,\s*['"]([^'"]+)['"])?""",
    re.MULTILINE,
)


def _parse_gemfile(content: str) -> ManifestInfo:
    """Parse a Ruby ``Gemfile``'s ``gem`` declarations. Language is Ruby."""
    info = ManifestInfo(source="Gemfile", languages=["ruby"])
    for match in _GEMFILE_GEM.finditer(content):
        info.dependencies.append(
            ManifestDependency(
                name=match.group(1),
                version=match.group(2) or "",
                scope="runtime",
            )
        )
    info.frameworks = _frameworks_for([d.name for d in info.dependencies])
    return info


class ManifestDetector:
    """Detects languages, frameworks, and dependencies from manifest files.

    Deterministic and offline: the same manifest content always produces the
    same ``ManifestInfo``. Unknown files are ignored (``detect`` returns None);
    malformed known manifests yield an empty-but-valid ``ManifestInfo`` rather
    than raising, so a broken descriptor never aborts analysis (Req 2.4).
    """

    def is_manifest(self, file_path: str) -> bool:
        """Return True if ``file_path`` is a recognized manifest file."""
        return _manifest_kind(file_path) is not None

    def detect(self, file_path: str, content: str) -> ManifestInfo | None:
        """Parse a single manifest file into ``ManifestInfo``.

        Returns None when the path is not a recognized manifest. Never raises:
        parse failures are logged and produce an empty-but-valid result.
        """
        kind = _manifest_kind(file_path)
        if kind is None:
            return None
        try:
            if kind == "package.json":
                return _parse_package_json(content)
            if kind == "go.mod":
                return _parse_go_mod(content)
            if kind == "pom.xml":
                return _parse_pom_xml(content)
            if kind == "Cargo.toml":
                return _parse_cargo_toml(content)
            if kind == "requirements.txt":
                return _parse_requirements_txt(content)
            if kind == "csproj":
                return _parse_csproj(content, source=os.path.basename(file_path))
            if kind == "Gemfile":
                return _parse_gemfile(content)
        except Exception as exc:  # pragma: no cover - defensive; parsers are tolerant
            logger.warning("manifest_parse_error", path=file_path, error=str(exc))
            source = os.path.basename(file_path)
            return ManifestInfo(source=source)
        return None

    def detect_many(
        self, files: list[tuple[str, str]]
    ) -> list[ManifestInfo]:
        """Parse every recognized manifest in ``files`` (each ``(path, content)``).

        Non-manifest files are skipped. Results are returned sorted by source
        name so the aggregate is deterministic regardless of input order.
        """
        results: list[ManifestInfo] = []
        for file_path, content in files:
            info = self.detect(file_path, content)
            if info is not None:
                results.append(info)
        results.sort(key=lambda i: i.source)
        return results

    def aggregate(
        self, manifests: list[ManifestInfo]
    ) -> tuple[list[str], list[str]]:
        """Merge manifest results into deterministic (languages, frameworks).

        Languages are ordered by how many manifests imply them (descending),
        then alphabetically, so multi-language repositories surface their
        dominant ecosystem(s) first while still representing every detected
        language (Req 2.5). Frameworks are returned sorted and de-duplicated.
        """
        lang_counts: dict[str, int] = {}
        frameworks: set[str] = set()
        for info in manifests:
            for lang in info.languages:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            frameworks.update(info.frameworks)
        languages = sorted(
            lang_counts.keys(), key=lambda lang: (-lang_counts[lang], lang)
        )
        return languages, sorted(frameworks)
