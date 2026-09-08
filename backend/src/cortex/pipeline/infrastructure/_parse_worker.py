"""Minimal, dependency-light worker entry point for out-of-process AST parsing.

Kept in its own module (imported by name in the spawned child) so the child's
import graph is small: it pulls in the parser stack only — never FastAPI, the
database, config, or the rest of the app. This makes respawns cheap, which
matters because the tree-sitter C grammars intermittently corrupt native state
after parsing many files and the parent must respawn a fresh worker to recover.
"""

from __future__ import annotations


def parse_worker_loop(in_q, out_q) -> None:  # pragma: no cover - runs in child
    """Read (index, content, path) items; stream back (index, ParsedFile).

    A single stuck or crashing parse takes down only this child; the parent
    detects the stall/exit and resumes the remaining files in a new worker.
    """
    import os
    os.environ.setdefault("LOG_LEVEL", "ERROR")

    # Silence structured logging in the worker so it never blocks on stdout.
    try:
        import logging
        import structlog
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(logging.CRITICAL)
        )
    except Exception:
        pass

    from cortex.pipeline.infrastructure.ast_parser import ASTParser
    from cortex.pipeline.infrastructure.ast_parser import ParsedFile

    parser = ASTParser()
    while True:
        item = in_q.get()
        if item is None:
            return
        index, content, path = item
        try:
            parsed = parser.parse(content, path)
        except Exception as e:
            parsed = ParsedFile(
                path=path,
                language=parser.detect_language(path),
                parse_errors=[f"Unexpected error: {e}"],
            )
        out_q.put((index, parsed))
