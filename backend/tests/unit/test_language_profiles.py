"""Tests for LanguageCapabilityProfile and LanguageParser.profile() (Req 2.1)."""

from cortex.pipeline.domain.entities import LanguageCapabilityProfile
from cortex.pipeline.infrastructure.ast_parser import (
    Language,
    PythonASTParser,
)
from cortex.pipeline.infrastructure.tree_sitter_parser import (
    _CSHARP_SPEC,
    _GO_SPEC,
    _JAVA_SPEC,
    _RUBY_SPEC,
    _RUST_SPEC,
    _TS_SPEC,
    TreeSitterParser,
)


def _parser(spec) -> TreeSitterParser:
    return TreeSitterParser(spec, ())


def test_python_profile_declares_expected_concepts() -> None:
    profile = PythonASTParser().profile()
    assert isinstance(profile, LanguageCapabilityProfile)
    assert profile.language == Language.PYTHON.value
    assert profile.has_decorators is True
    assert profile.has_packages is True
    assert profile.has_async is True
    assert profile.has_traits is False


def test_java_profile_declares_interfaces_and_packages() -> None:
    profile = _parser(_JAVA_SPEC).profile()
    assert profile.language == Language.JAVA.value
    assert profile.has_interfaces is True
    assert profile.has_generics is True
    assert profile.has_packages is True
    assert profile.has_traits is False
    assert profile.has_async is False


def test_typescript_profile_declares_interfaces_no_packages() -> None:
    profile = _parser(_TS_SPEC).profile()
    assert profile.language == Language.TYPESCRIPT.value
    assert profile.has_interfaces is True
    assert profile.has_generics is True
    assert profile.has_packages is False


def test_go_profile_declares_packages_and_interfaces_no_decorators() -> None:
    profile = _parser(_GO_SPEC).profile()
    assert profile.language == Language.GO.value
    assert profile.has_packages is True
    assert profile.has_interfaces is True
    assert profile.has_decorators is False


def test_rust_profile_declares_traits() -> None:
    profile = _parser(_RUST_SPEC).profile()
    assert profile.language == Language.RUST.value
    assert profile.has_traits is True
    assert profile.has_generics is True


def test_csharp_profile_declares_namespaces_and_attributes() -> None:
    profile = _parser(_CSHARP_SPEC).profile()
    assert profile.language == Language.CSHARP.value
    assert profile.has_packages is True     # namespaces
    assert profile.has_decorators is True   # attributes


def test_ruby_profile_declares_traits_no_interfaces() -> None:
    profile = _parser(_RUBY_SPEC).profile()
    assert profile.language == Language.RUBY.value
    assert profile.has_traits is True       # mixins / modules
    assert profile.has_interfaces is False


def test_supports_uses_has_prefix_lookup() -> None:
    profile = _parser(_JAVA_SPEC).profile()
    assert profile.supports("interfaces") is True
    assert profile.supports("traits") is False
    # Unknown concepts return False rather than raising.
    assert profile.supports("nonexistent") is False


def test_applicable_sections_matches_answer_sections() -> None:
    profile = PythonASTParser().profile()
    assert profile.applicable_sections() == profile.answer_sections
    assert "endpoints" in profile.applicable_sections()


def test_profile_is_deterministic() -> None:
    # Same parser instance returns an equal profile every call (frozen dataclass).
    parser = PythonASTParser()
    assert parser.profile() == parser.profile()
