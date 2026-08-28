"""Unit tests for the ContextRetriever intent detection and utility methods.

Covers:
  - Intent detection (keyword classification)
  - Stacktrace parsing (Python, Java, JavaScript)
  - Keyword extraction
  - Blast radius detection signals
  - Node scoring
"""

from __future__ import annotations

import pytest
from cortex.chat.infrastructure.context_retriever import (
    ContextRetriever,
    QueryIntent,
    detect_intent,
)

# ── Intent Detection ──────────────────────────────────────────────────────────

class TestIntentDetection:
    """Tests for the deterministic intent classifier."""

    def test_architecture_keywords(self):
        assert detect_intent("What's the architecture of this project?") == QueryIntent.ARCHITECTURE
        assert detect_intent("How is the code organized?") == QueryIntent.ARCHITECTURE
        assert detect_intent("Describe the design patterns used") == QueryIntent.ARCHITECTURE

    def test_navigation_keywords(self):
        assert detect_intent("Where is the UserService defined?") == QueryIntent.NAVIGATION
        assert detect_intent("Find the file that handles auth") == QueryIntent.NAVIGATION

    def test_data_flow_keywords(self):
        assert detect_intent("How does a request flow through the system?") == QueryIntent.DATA_FLOW
        assert detect_intent("What's the pipeline for processing data?") == QueryIntent.DATA_FLOW

    def test_dependency_keywords(self):
        assert detect_intent("What depends on the UserService?") == QueryIntent.DEPENDENCY
        assert detect_intent("Show me the import relationships") == QueryIntent.DEPENDENCY

    def test_complexity_keywords(self):
        assert detect_intent("What's the most complex function?") == QueryIntent.COMPLEXITY
        assert detect_intent("Are there any god classes?") == QueryIntent.COMPLEXITY
        assert detect_intent("Show me code smells and risks") == QueryIntent.COMPLEXITY

    def test_debugging_with_stacktrace(self):
        trace = '''File "src/main.py", line 42, in handle_request
    result = process(data)'''
        assert detect_intent(trace) == QueryIntent.DEBUGGING

    def test_debugging_java_trace(self):
        trace = "at com.example.Service.process(Service.java:42)"
        assert detect_intent(trace) == QueryIntent.DEBUGGING

    def test_explanation_keywords(self):
        assert detect_intent("What does the GraphBuilder do?") == QueryIntent.EXPLANATION
        assert detect_intent("Explain the purpose of this module") == QueryIntent.EXPLANATION

    def test_metrics_keywords(self):
        assert detect_intent("What's the total count of classes?") == QueryIntent.METRICS
        assert detect_intent("What's the overall score?") == QueryIntent.METRICS

    def test_entry_point_keywords(self):
        assert detect_intent("Show me the main entry point") == QueryIntent.ENTRY_POINT
        assert detect_intent("What is the application's init bootstrap?") == QueryIntent.ENTRY_POINT

    def test_learning_keywords(self):
        assert detect_intent("What should I learn first?") == QueryIntent.LEARNING
        assert detect_intent("Help me understand this codebase") == QueryIntent.LEARNING

    def test_general_fallback(self):
        assert detect_intent("hello") == QueryIntent.GENERAL
        assert detect_intent("xyz abc 123") == QueryIntent.GENERAL


# ── Stacktrace Parsing ────────────────────────────────────────────────────────

class TestStacktraceParsing:
    """Tests for extracting symbols from error stacktraces."""

    @pytest.fixture
    def retriever(self) -> ContextRetriever:
        return ContextRetriever()

    def test_python_traceback(self, retriever: ContextRetriever):
        trace = '''Traceback (most recent call last):
  File "src/cortex/pipeline/stages.py", line 42, in execute
    result = self._parser.parse(content)
  File "src/cortex/parser.py", line 15, in parse
    return ast.parse(source)'''
        symbols = retriever._parse_stacktrace(trace)
        assert "execute" in symbols
        assert "parse" in symbols
        assert "stages" in symbols or "parser" in symbols

    def test_java_stacktrace(self, retriever: ContextRetriever):
        trace = '''at com.example.UserService.createUser(UserService.java:42)
at com.example.Controller.handlePost(Controller.java:18)'''
        symbols = retriever._parse_stacktrace(trace)
        assert "UserService" in symbols
        assert "createUser" in symbols
        assert "Controller" in symbols

    def test_javascript_stacktrace(self, retriever: ContextRetriever):
        trace = "at processRequest (src/handler.js:12:5)"
        symbols = retriever._parse_stacktrace(trace)
        assert "processRequest" in symbols

    def test_no_stacktrace(self, retriever: ContextRetriever):
        """Regular questions should not extract symbols."""
        symbols = retriever._parse_stacktrace("What does the UserService do?")
        assert symbols == []

    def test_deduplicates(self, retriever: ContextRetriever):
        trace = '''File "x.py", line 1, in foo
File "x.py", line 2, in foo'''
        symbols = retriever._parse_stacktrace(trace)
        assert symbols.count("foo") <= 1


# ── Keyword Extraction ────────────────────────────────────────────────────────

class TestKeywordExtraction:
    """Tests for extracting meaningful keywords from questions."""

    @pytest.fixture
    def retriever(self) -> ContextRetriever:
        return ContextRetriever()

    def test_removes_stopwords(self, retriever: ContextRetriever):
        keywords = retriever._extract_keywords("What is the architecture of this project?")
        assert "what" not in keywords
        assert "the" not in keywords
        assert "architecture" in keywords
        assert "project" in keywords

    def test_short_words_excluded(self, retriever: ContextRetriever):
        keywords = retriever._extract_keywords("Is it a big file?")
        assert "a" not in keywords
        # "it" is also too short or a stopword

    def test_limits_count(self, retriever: ContextRetriever):
        long_query = " ".join([f"word{i}" for i in range(50)])
        keywords = retriever._extract_keywords(long_query)
        assert len(keywords) <= 15


# ── Blast Radius Detection ────────────────────────────────────────────────────

class TestBlastRadiusDetection:
    """Tests for detecting when a user wants blast radius analysis."""

    @pytest.fixture
    def retriever(self) -> ContextRetriever:
        return ContextRetriever()

    def test_detects_change_impact(self, retriever: ContextRetriever):
        assert retriever._wants_blast_radius("What would break if I change UserService?")
        assert retriever._wants_blast_radius("What's the blast radius of this change?")
        assert retriever._wants_blast_radius("Is it safe to change the repository layer?")
        assert retriever._wants_blast_radius("What depends on this module?")
        assert retriever._wants_blast_radius("Who uses the GraphBuilder?")

    def test_does_not_false_positive(self, retriever: ContextRetriever):
        assert not retriever._wants_blast_radius("What does UserService do?")
        assert not retriever._wants_blast_radius("How is the code organized?")
        assert not retriever._wants_blast_radius("What's the overall score?")


# ── Node Scoring ──────────────────────────────────────────────────────────────

class TestNodeScoring:
    """Tests for relevance scoring of graph nodes."""

    @pytest.fixture
    def retriever(self) -> ContextRetriever:
        return ContextRetriever()

    def test_label_match_scores_high(self, retriever: ContextRetriever):
        score = retriever._score_node(
            "UserService",
            {"file": "service.py"},
            ["userservice"],
        )
        assert score > 0

    def test_file_path_match(self, retriever: ContextRetriever):
        score = retriever._score_node(
            "SomeClass",
            {"file": "src/auth/service.py"},
            ["auth"],
        )
        assert score > 0

    def test_no_match_scores_zero(self, retriever: ContextRetriever):
        score = retriever._score_node(
            "UserService",
            {"file": "service.py"},
            ["database", "migration"],
        )
        assert score == 0
