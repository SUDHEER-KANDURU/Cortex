"""Tests for ManifestDetector (Req 2.4, Req 2.5)."""

from cortex.pipeline.domain.entities import ManifestInfo
from cortex.pipeline.infrastructure.manifest_detector import ManifestDetector


def detector() -> ManifestDetector:
    return ManifestDetector()


# ── Recognition ────────────────────────────────────────────────────────────────


def test_is_manifest_recognizes_known_files() -> None:
    d = detector()
    for path in (
        "package.json",
        "go.mod",
        "pom.xml",
        "Cargo.toml",
        "requirements.txt",
        "src/App.csproj",
        "Gemfile",
    ):
        assert d.is_manifest(path), path


def test_is_manifest_rejects_unknown_files() -> None:
    d = detector()
    assert not d.is_manifest("main.py")
    assert not d.is_manifest("README.md")


def test_detect_returns_none_for_unknown_file() -> None:
    assert detector().detect("main.py", "print(1)") is None


# ── package.json ─────────────────────────────────────────────────────────────────


def test_package_json_detects_typescript_and_react() -> None:
    content = """
    {
      "dependencies": {"react": "^18.0.0", "next": "13.0.0"},
      "devDependencies": {"typescript": "^5.0.0"}
    }
    """
    info = detector().detect("package.json", content)
    assert info is not None
    assert info.languages == ["typescript"]
    assert "react" in info.frameworks
    assert "nextjs" in info.frameworks
    names = info.dependency_names()
    assert "react" in names and "typescript" in names


def test_package_json_defaults_to_javascript_without_typescript() -> None:
    info = detector().detect(
        "package.json", '{"dependencies": {"express": "^4.0.0"}}'
    )
    assert info is not None
    assert info.languages == ["javascript"]
    assert info.frameworks == ["express"]


def test_malformed_package_json_yields_empty_info() -> None:
    info = detector().detect("package.json", "{ not valid json ")
    assert isinstance(info, ManifestInfo)
    assert info.source == "package.json"
    assert info.dependencies == []


# ── go.mod ──────────────────────────────────────────────────────────────────────


def test_go_mod_block_and_single_require() -> None:
    content = """
module example.com/app

go 1.21

require github.com/gin-gonic/gin v1.9.1

require (
    github.com/stretchr/testify v1.8.0
    github.com/labstack/echo/v4 v4.11.0
)
"""
    info = detector().detect("go.mod", content)
    assert info is not None
    assert info.languages == ["go"]
    names = info.dependency_names()
    assert "github.com/gin-gonic/gin" in names
    assert "github.com/labstack/echo/v4" in names
    assert "gin" in info.frameworks
    assert "echo" in info.frameworks


# ── pom.xml ─────────────────────────────────────────────────────────────────────


def test_pom_xml_extracts_spring_dependency() -> None:
    content = """
    <project>
      <dependencies>
        <dependency>
          <groupId>org.springframework.boot</groupId>
          <artifactId>spring-boot-starter-web</artifactId>
          <version>3.1.0</version>
        </dependency>
      </dependencies>
    </project>
    """
    info = detector().detect("pom.xml", content)
    assert info is not None
    assert info.languages == ["java"]
    assert "spring" in info.frameworks


# ── Cargo.toml ──────────────────────────────────────────────────────────────────


def test_cargo_toml_simple_and_inline_versions() -> None:
    content = """
[package]
name = "app"

[dependencies]
actix-web = "4"
tokio = { version = "1", features = ["full"] }

[dev-dependencies]
mockall = "0.11"
"""
    info = detector().detect("Cargo.toml", content)
    assert info is not None
    assert info.languages == ["rust"]
    names = info.dependency_names()
    assert "actix-web" in names and "tokio" in names
    assert "actix" in info.frameworks
    assert "tokio" in info.frameworks
    dev = [d for d in info.dependencies if d.scope == "dev"]
    assert any(d.name == "mockall" for d in dev)


# ── requirements.txt ─────────────────────────────────────────────────────────────


def test_requirements_txt_parses_names_and_ignores_options() -> None:
    content = """
# comment
fastapi==0.110.0
sqlalchemy>=2.0
-r other.txt
pytest  # inline comment
"""
    info = detector().detect("requirements.txt", content)
    assert info is not None
    assert info.languages == ["python"]
    names = info.dependency_names()
    assert "fastapi" in names and "sqlalchemy" in names and "pytest" in names
    assert "fastapi" in info.frameworks
    assert "sqlalchemy" in info.frameworks
    assert "pytest" in info.frameworks


# ── .csproj ─────────────────────────────────────────────────────────────────────


def test_csproj_package_references() -> None:
    content = """
    <Project Sdk="Microsoft.NET.Sdk.Web">
      <ItemGroup>
        <PackageReference Include="Microsoft.AspNetCore.Mvc" Version="2.2.0" />
        <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
      </ItemGroup>
    </Project>
    """
    info = detector().detect("src/Api.csproj", content)
    assert info is not None
    assert info.languages == ["csharp"]
    assert info.source == "Api.csproj"
    assert "aspnetcore" in info.frameworks


# ── Gemfile ─────────────────────────────────────────────────────────────────────


def test_gemfile_gem_declarations() -> None:
    content = """
source 'https://rubygems.org'
gem 'rails', '7.0.0'
gem 'sinatra'
"""
    info = detector().detect("Gemfile", content)
    assert info is not None
    assert info.languages == ["ruby"]
    names = info.dependency_names()
    assert "rails" in names and "sinatra" in names
    assert "rails" in info.frameworks
    assert "sinatra" in info.frameworks


# ── Aggregation & determinism ────────────────────────────────────────────────────


def test_detect_many_skips_non_manifests_and_sorts() -> None:
    files = [
        ("main.py", "print(1)"),
        ("Gemfile", "gem 'rails'"),
        ("package.json", '{"dependencies": {"react": "1"}}'),
    ]
    results = detector().detect_many(files)
    assert [i.source for i in results] == ["Gemfile", "package.json"]


def test_aggregate_orders_dominant_language_first() -> None:
    manifests = [
        ManifestInfo(source="package.json", languages=["typescript"], frameworks=["react"]),
        ManifestInfo(source="go.mod", languages=["go"], frameworks=["gin"]),
        ManifestInfo(source="requirements.txt", languages=["python"]),
        ManifestInfo(source="Gemfile", languages=["python"]),  # bump python count
    ]
    languages, frameworks = detector().aggregate(manifests)
    # python appears in two manifests → dominant, listed first.
    assert languages[0] == "python"
    assert set(languages) == {"python", "typescript", "go"}
    assert frameworks == ["gin", "react"]


def test_detect_is_deterministic() -> None:
    content = '{"dependencies": {"react": "1", "express": "1"}}'
    first = detector().detect("package.json", content)
    second = detector().detect("package.json", content)
    assert first is not None and second is not None
    assert first.frameworks == second.frameworks
    assert first.dependency_names() == second.dependency_names()
