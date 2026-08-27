"""Test script — runs the LayeredDiagramGenerator against Cortex's own repo.

Prints Level 1 (system), Level 2 (pipeline module), and Level 3 (GraphBuilder class)
output as JSON for verification.

Run from workspace root:
  .venv\Scripts\python.exe backend/scripts/test_diagram.py
"""

import sys
import json
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cortex.pipeline.infrastructure.ast_parser import ASTParser
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.pipeline.infrastructure.layered_diagram_generator import (
    LayeredDiagramGenerator,
)


def main():
    # Parse Cortex's own backend source files
    parser = ASTParser()
    src_root = os.path.join(os.path.dirname(__file__), "..", "src", "cortex")

    parsed_files = []
    for root, dirs, files in os.walk(src_root):
        # Skip pycache and test dirs
        dirs[:] = [d for d in dirs if d != "__pycache__" and d != ".pytest_cache"]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, os.path.join(os.path.dirname(__file__), ".."))
            rel_path = rel_path.replace("\\", "/")
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                parsed = parser.parse(content, rel_path)
                parsed_files.append(parsed)
            except Exception:
                pass

    print(f"Parsed {len(parsed_files)} source files")

    # Build the graph
    builder = GraphBuilder(job_id="test-diagram", repo_url="https://github.com/cortex-ai/Cortex")
    graph = builder.build(parsed_files)
    print(f"Graph: {graph.node_count()} nodes, {graph.edge_count()} edges")

    # Generate Level 1 — System View
    gen = LayeredDiagramGenerator(graph)
    system_view = gen.generate_system_view("Cortex")

    print("\n" + "=" * 60)
    print("LEVEL 1 — SYSTEM VIEW")
    print("=" * 60)
    print(f"Nodes: {len(system_view.nodes)}")
    print(f"Edges: {len(system_view.edges)}")
    print(f"Cycles: {len(system_view.cycles)}")
    print()
    for n in system_view.nodes:
        health_tag = f" [{n.health}]" if n.health != "healthy" else ""
        cycle_tag = " (CYCLE)" if n.in_cycle else ""
        print(f"  {n.label:20s}  files={n.file_count:2d}  classes={n.class_count:2d}  fns={n.function_count:3d}{health_tag}{cycle_tag}")
    print()
    for e in system_view.edges:
        cycle_tag = " <CYCLE>" if e.is_cycle else ""
        print(f"  {e.source:25s} --> {e.target:25s}  [{e.label}]{cycle_tag}")

    # Generate Level 2 — Module detail for 'pipeline'
    print("\n" + "=" * 60)
    print("LEVEL 2 — MODULE DETAIL (pipeline)")
    print("=" * 60)
    module_view = gen.generate_module_detail("pipeline", "Cortex")
    print(f"Nodes: {len(module_view.nodes)}")
    print(f"Edges: {len(module_view.edges)}")
    for n in module_view.nodes:
        print(f"  [{n.node_type:8s}] {n.label}")

    # Generate Level 3 — Class detail for a known class
    # Find a class to use
    print("\n" + "=" * 60)
    print("LEVEL 3 — CLASS DETAIL")
    print("=" * 60)

    # Pick the first class with methods
    target_class = None
    for c in graph.nodes:
        if c.node_type.value == "CLASS" and int(c.properties.get("methods", 0)) > 2:
            target_class = c.label
            break

    if target_class:
        print(f"Target class: {target_class}")
        class_view = gen.generate_class_detail(target_class, "Cortex")
        print(f"Nodes: {len(class_view.nodes)}")
        print(f"Edges: {len(class_view.edges)}")
        for n in class_view.nodes:
            role = n.properties.get("role", n.properties.get("central", ""))
            print(f"  [{n.node_type:8s}] {n.label}  {role}")
    else:
        print("No suitable class found for Level 3 demo")

    # Output summary verification
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    l1_pass = len(system_view.nodes) <= 20
    l1_edge_pass = len(system_view.edges) <= 30
    print(f"Level 1 nodes <= 20: {'PASS' if l1_pass else 'FAIL'} ({len(system_view.nodes)})")
    print(f"Level 1 edges <= 30: {'PASS' if l1_edge_pass else 'FAIL'} ({len(system_view.edges)})")


if __name__ == "__main__":
    main()
