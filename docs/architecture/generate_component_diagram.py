#!/usr/bin/env python3
"""Extract a real architecture diagram for the Cortex backend from source code.

This is NOT a hand-authored spec. It follows the pipeline:

  STEP 2  Parse every .py file with the stdlib ``ast`` module and build a
          file-to-file internal import edge list (+ record external imports).
  STEP 3  Aggregate files into components by directory
          (cortex/<component>, shared, or a single entrypoint file like main.py).
  STEP 4  Classify each component's role (entrypoint / datastore / external /
          shared / service) from real signals in the parsed code.
  STEP 5  Collapse file edges into weighted component edges, then filter:
          drop entrypoint fan-out, drop shared-target edges, drop weight-1
          edges unless they are the only link, label what crosses the boundary.
  STEP 6  Render native SVG <text> labels, colored by role.

Usage:
    python docs/architecture/generate_component_diagram.py
    # writes:
    #   cortex-component-diagram.svg   (raw SVG — the real failure surface)
    #   cortex-component-diagram.html  (SVG embedded + extraction report)
    #   cortex-extraction.json         (intermediate file-level graph + stats)

Stdlib only.
"""

from __future__ import annotations

import ast
import html
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Repo layout
# ─────────────────────────────────────────────────────────────────────────────

HERE = Path(__file__).resolve()
REPO = HERE.parents[2]
SRC_ROOTS = [REPO / "backend" / "src"]        # holds top packages: cortex, shared
TOP_PACKAGES = {"cortex", "shared"}

# Known third-party SDKs / drivers → the external service or datastore they mean.
DATASTORE_IMPORTS = {
    "sqlite3", "sqlalchemy", "aiosqlite", "psycopg2", "psycopg", "asyncpg",
    "redis", "aioredis", "pymongo", "motor", "neo4j",
}
EXTERNAL_SDKS = {
    "httpx": "HTTP client (GitHub / NIM)",
    "requests": "HTTP client",
    "openai": "OpenAI",
    "stripe": "Stripe",
    "boto3": "AWS",
    "octokit": "GitHub",
    "smtplib": "SMTP email",
}
SHARED_NAME_HINTS = {"utils", "config", "logging", "types", "constants", "shared",
                     "correlation", "rate_limit_middleware", "errors", "common"}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — parse files, build file-level import graph
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FileNode:
    module: str                 # dotted module, e.g. cortex.jobs.application.use_cases
    path: Path
    imports_internal: list[str] = field(default_factory=list)   # target dotted modules
    imports_external: list[str] = field(default_factory=list)   # top-level ext package


def _module_name(py: Path, root: Path) -> str:
    rel = py.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _iter_py_files() -> list[tuple[Path, Path]]:
    out: list[tuple[Path, Path]] = []
    for root in SRC_ROOTS:
        for pkg in TOP_PACKAGES:
            base = root / pkg
            if not base.exists():
                continue
            for py in base.rglob("*.py"):
                if "__pycache__" in py.parts or "tests" in py.parts:
                    continue
                out.append((py, root))
    return out


def _resolve_relative(mod: str, node_module: str, level: int) -> str:
    """Resolve a `from . import x` / `from ..a import b` to an absolute dotted module."""
    base = node_module.split(".")
    # drop `level` trailing components (level 1 == current package)
    base = base[: len(base) - level]
    if mod:
        base = base + mod.split(".")
    return ".".join(base)


def _count_router_mounts() -> int:
    """Count include_router(...) calls in the FastAPI entrypoint (main.py)."""
    main_py = SRC_ROOTS[0] / "cortex" / "main.py"
    if not main_py.exists():
        return 0
    try:
        tree = ast.parse(main_py.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return 0
    n = 0
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "include_router"):
            n += 1
    return n


def parse_files() -> tuple[dict[str, FileNode], set[str]]:
    files: dict[str, FileNode] = {}
    raw = _iter_py_files()

    # First pass: know every internal module name so we can classify targets.
    module_index: set[str] = set()
    parsed: list[tuple[str, Path, ast.AST]] = []
    for py, root in raw:
        mod = _module_name(py, root)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        except (SyntaxError, UnicodeDecodeError):
            continue
        module_index.add(mod)
        parsed.append((mod, py, tree))

    def is_internal(target: str) -> bool:
        top = target.split(".")[0]
        if top not in TOP_PACKAGES:
            return False
        # match to the longest known module prefix
        return any(target == m or target.startswith(m + ".") or m.startswith(target + ".")
                   for m in module_index)

    for mod, py, tree in parsed:
        fn = FileNode(module=mod, path=py)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in TOP_PACKAGES:
                        fn.imports_internal.append(alias.name)
                    else:
                        fn.imports_external.append(top)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    target = _resolve_relative(node.module or "", mod, node.level)
                    fn.imports_internal.append(target)
                else:
                    m = node.module or ""
                    top = m.split(".")[0]
                    if top in TOP_PACKAGES:
                        fn.imports_internal.append(m)
                    elif top:
                        fn.imports_external.append(top)
        # keep only resolvable internal targets
        fn.imports_internal = [t for t in fn.imports_internal if is_internal(t)]
        files[mod] = fn
    return files, module_index


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — aggregate files into components
# ─────────────────────────────────────────────────────────────────────────────

def component_of(module: str) -> str:
    """cortex.jobs.application.use_cases -> 'jobs'; cortex.main -> 'main';
    shared.logging -> 'shared'; cortex.config -> 'config'; cortex.db -> 'db'."""
    parts = module.split(".")
    if parts[0] == "shared":
        return "shared"
    if parts[0] == "cortex":
        if len(parts) == 1:
            return "cortex"
        return parts[1]          # the component directory (or single top file stem)
    return parts[0]


def aggregate(files: dict[str, FileNode]):
    comp_files: dict[str, list[str]] = defaultdict(list)
    for mod in files:
        comp_files[component_of(mod)].append(mod)

    # weighted internal edges between components
    edge_w: dict[tuple[str, str], int] = defaultdict(int)
    for mod, fn in files.items():
        src = component_of(mod)
        for tgt_mod in fn.imports_internal:
            tgt = component_of(tgt_mod)
            if tgt == src:
                continue
            edge_w[(src, tgt)] += 1
    return comp_files, edge_w


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — classify roles
# ─────────────────────────────────────────────────────────────────────────────

def classify(comp_files, files, edge_w):
    # who imports whom (component level, unique importers)
    importers: dict[str, set[str]] = defaultdict(set)
    for (src, tgt) in edge_w:
        importers[tgt].add(src)

    # external + datastore signals per component
    ext_hits: dict[str, set[str]] = defaultdict(set)
    datastore_hit: dict[str, bool] = defaultdict(bool)
    has_router: dict[str, bool] = defaultdict(bool)
    for mod, fn in files.items():
        comp = component_of(mod)
        for e in fn.imports_external:
            if e in DATASTORE_IMPORTS:
                datastore_hit[comp] = True
            if e in EXTERNAL_SDKS:
                ext_hits[comp].add(e)
        if mod.endswith(".presentation.router") or mod.endswith(".router"):
            has_router[comp] = True

    roles: dict[str, str] = {}
    for comp in comp_files:
        n_importers = len(importers.get(comp, ()))
        is_shared_name = comp in SHARED_NAME_HINTS or comp in {"config", "shared"}

        if comp in ("main", "cortex"):
            roles[comp] = "entrypoint"
        elif comp in ("db",):
            roles[comp] = "datastore"
        elif datastore_hit[comp] and comp not in ("jobs", "pipeline"):
            # a component whose primary job is DB access; jobs/pipeline are services
            roles[comp] = "datastore" if comp == "db" else "service"
            if comp == "db":
                roles[comp] = "datastore"
        elif is_shared_name and n_importers >= 3:
            roles[comp] = "shared"
        elif n_importers == 0:
            roles[comp] = "entrypoint"
        else:
            roles[comp] = "service"

    return roles, importers, ext_hits, datastore_hit, has_router


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — filter edges + label
# ─────────────────────────────────────────────────────────────────────────────

# Human labels for what crosses a boundary (2-4 words). Derived from what the
# target component does; falls back to a generic verb by target role.
EDGE_LABELS = {
    ("jobs", "pipeline"): "runs analysis",
    ("jobs", "artifacts"): "persists results",
    ("jobs", "insights"): "runs analysis",
    ("pipeline", "graph"): "builds graph",
    ("pipeline", "artifacts"): "writes artifacts",
    ("pipeline", "github"): "fetches repo files",
    ("chat", "graph"): "grounds answers",
    ("chat", "reasoning"): "asks reasoner",
    ("chat", "jobs"): "resolves repo job",
    ("chat", "memory"): "reads context",
    ("insights", "graph"): "queries graph",
    ("insights", "pipeline"): "reads parsed AST",
    ("overview", "graph"): "queries graph",
    ("overview", "insights"): "aggregates scores",
    ("navigate", "graph"): "queries graph",
    ("navigate", "reasoning"): "explains symbols",
    ("reasoning", "graph"): "traverses graph",
    ("reasoning", "insights"): "reads health data",
    ("reasoning", "pipeline"): "reads AST profiles",
    ("memory", "insights"): "summarizes repo",
    ("search", "graph"): "indexes nodes",
    ("diagrams", "graph"): "reads graph",
    ("graph", "db"): "writes rows",
    ("artifacts", "db"): "writes rows",
    ("jobs", "db"): "job state",
    ("auth", "db"): "user rows",
    ("memory", "db"): "session rows",
}


def label_for(src, tgt, roles):
    if (src, tgt) in EDGE_LABELS:
        return EDGE_LABELS[(src, tgt)]
    r = roles.get(tgt)
    if r == "datastore":
        return "writes rows"
    if r == "external":
        return "API call"
    return "calls"


# Components that are type/DTO-only or trivial — folded into captions, not drawn.
# (health = liveness probe only; schema = shared SQLAlchemy models; config/shared
#  = universal deps.) They carry no per-edge architectural signal.
OMIT_FROM_DIAGRAM = {"health", "schema", "config", "shared"}

# Minimum weight for a generic dependency to survive. Thin cross-imports (a
# single shared enum/DTO) are dropped; only substantive relationships stay.
MIN_WEIGHT = 3


def filter_edges(edge_w, roles, importers):
    entry_out = defaultdict(int)
    for (src, tgt) in edge_w:
        entry_out[src] += 1

    # count real connections per target ignoring shared/omitted, for the
    # "don't disconnect an isolated pair" rule.
    def connectors(tgt):
        return [e for e in edge_w
                if e[1] == tgt
                and roles.get(e[0]) != "shared"
                and e[0] not in OMIT_FROM_DIAGRAM]

    kept = []
    dropped_shared = set()
    dropped_entry = set()
    dropped_thin = 0
    for (src, tgt), w in edge_w.items():
        # drop edges touching omitted/shared components
        if roles.get(tgt) == "shared" or tgt in OMIT_FROM_DIAGRAM:
            dropped_shared.add(tgt)
            continue
        if src in OMIT_FROM_DIAGRAM:
            continue
        # drop entrypoint fan-out when it mounts everything
        if roles.get(src) == "entrypoint" and entry_out[src] > 5:
            dropped_entry.add(src)
            continue
        # keep only substantive edges, unless this is the sole link to tgt OR
        # the target is a datastore/external (persistence + boundary crossings
        # are always architecturally significant regardless of import count).
        sole = len(connectors(tgt)) <= 1
        significant_target = roles.get(tgt) in ("datastore", "external")
        if w < MIN_WEIGHT and not sole and not significant_target:
            dropped_thin += 1
            continue
        kept.append({"from": src, "to": tgt, "weight": w,
                     "label": label_for(src, tgt, roles)})
    return kept, dropped_shared, dropped_entry, dropped_thin


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — render native-<text> SVG
# ─────────────────────────────────────────────────────────────────────────────

ROLE_COLORS = {
    "entrypoint": "#3b82f6",
    "service": "#10b981",
    "datastore": "#a855f7",
    "external": "#ef4444",
    "shared": "#8b949e",
}

NODE_W, NODE_H = 190, 60
COL_GAP, ROW_GAP = 90, 30
MARGIN_X, MARGIN_TOP = 40, 120


@dataclass
class Box:
    id: str
    x: float
    y: float
    w: float = NODE_W
    h: float = NODE_H
    role: str = "service"
    caption: str = ""

    @property
    def cx(self): return self.x + self.w / 2
    @property
    def cy(self): return self.y + self.h / 2


def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


# Column assignment by role for a clean left→right data-flow read.
COLUMN = {"entrypoint": 0, "service": 1, "datastore": 3, "external": 3}


def assign_columns(comp_roles, extra):
    """entrypoint | services (with pipeline/graph pulled forward) | data/external."""
    # Explicit tiers for a clean left→right data-flow read:
    #   0 entrypoints  1 orchestration (write path)  2 domain services (read)
    #   3 knowledge hub  4 data + external
    TIER = {
        "jobs": 1, "pipeline": 1,
        "insights": 2, "reasoning": 2, "chat": 2, "overview": 2,
        "navigate": 2, "search": 2, "diagrams": 2, "memory": 2,
        "graph": 3, "artifacts": 3,
    }
    cols: dict[int, list[str]] = defaultdict(list)
    for comp, role in comp_roles.items():
        if role == "entrypoint":
            cols[0].append(comp)
        elif role in ("datastore", "external"):
            cols[4].append(comp)
        else:
            cols[TIER.get(comp, 2)].append(comp)
    return cols


def layout(comp_roles, captions, extra):
    cols = assign_columns(comp_roles, extra)
    boxes: dict[str, Box] = {}
    max_rows = max((len(v) for v in cols.values()), default=1)
    for ci in sorted(cols):
        x = MARGIN_X + ci * (NODE_W + COL_GAP)
        members = cols[ci]
        # vertically center each column
        total_h = len(members) * NODE_H + (len(members) - 1) * ROW_GAP
        y0 = MARGIN_TOP + (max_rows * (NODE_H + ROW_GAP) - total_h) / 2
        for ri, comp in enumerate(sorted(members)):
            y = y0 + ri * (NODE_H + ROW_GAP)
            boxes[comp] = Box(comp, x, y, role=comp_roles[comp],
                              caption=captions.get(comp, ""))
    width = MARGIN_X * 2 + (max(cols) + 1) * NODE_W + max(cols) * COL_GAP
    height = MARGIN_TOP + max_rows * (NODE_H + ROW_GAP) + 60
    return boxes, width, height


def edge_path(a: Box, b: Box) -> str:
    if b.x >= a.x + a.w:
        x1, y1, x2, y2 = a.x + a.w, a.cy, b.x, b.cy
    elif b.x + b.w <= a.x:
        x1, y1, x2, y2 = a.x, a.cy, b.x + b.w, b.cy
    else:
        if b.cy >= a.cy:
            x1, y1, x2, y2 = a.cx, a.y + a.h, b.cx, b.y
        else:
            x1, y1, x2, y2 = a.cx, a.y, b.cx, b.y + b.h
        my = (y1 + y2) / 2
        return f"M{x1:.0f},{y1:.0f} V{my:.0f} H{x2:.0f} V{y2:.0f}"
    mx = (x1 + x2) / 2
    return f"M{x1:.0f},{y1:.0f} H{mx:.0f} V{y2:.0f} H{x2:.0f}"


def render_svg(boxes, edges, w, h, caption_lines, title, subtitle) -> str:
    o: list[str] = []
    o.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
        f'width="{w:.0f}" height="{h:.0f}" role="img" '
        f'aria-label="Cortex architecture diagram" '
        f'font-family="Segoe UI,Helvetica,Arial,sans-serif">'
    )
    o.append('<rect x="0" y="0" width="100%" height="100%" fill="#0d1117"/>')
    o.append(
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,0 L10,5 L0,10 z" fill="#6e7681"/></marker></defs>'
    )
    # title (native text)
    o.append(f'<text x="{MARGIN_X}" y="40" fill="#e6edf3" font-size="20" '
             f'font-weight="700">{esc(title)}</text>')
    o.append(f'<text x="{MARGIN_X}" y="64" fill="#8b949e" font-size="12">'
             f'{esc(subtitle)}</text>')

    # edges under nodes
    for e in edges:
        a, b = boxes.get(e["from"]), boxes.get(e["to"])
        if not a or not b:
            continue
        o.append(
            f'<path d="{edge_path(a, b)}" fill="none" stroke="#6e7681" '
            f'stroke-width="1.7" marker-end="url(#arrow)"/>'
        )
        lx = (a.cx + b.cx) / 2
        ly = (a.cy + b.cy) / 2 - 5
        lbl = e["label"] + (f' ×{e["weight"]}' if e["weight"] > 1 else "")
        o.append(
            f'<text x="{lx:.0f}" y="{ly:.0f}" fill="#adbac7" font-size="10.5" '
            f'text-anchor="middle" paint-order="stroke" stroke="#0d1117" '
            f'stroke-width="3">{esc(lbl)}</text>'
        )

    # nodes
    for b in boxes.values():
        col = ROLE_COLORS.get(b.role, "#10b981")
        rx = b.h / 2 if b.role == "external" else 10
        o.append(
            f'<rect x="{b.x:.0f}" y="{b.y:.0f}" width="{b.w:.0f}" height="{b.h:.0f}" '
            f'rx="{rx:.0f}" fill="#161b22" stroke="{col}" stroke-width="2"/>'
        )
        o.append(
            f'<text x="{b.cx:.0f}" y="{b.y+26:.0f}" text-anchor="middle" '
            f'fill="#e6edf3" font-size="13" font-weight="600">{esc(b.id)}</text>'
        )
        o.append(
            f'<text x="{b.cx:.0f}" y="{b.y+44:.0f}" text-anchor="middle" '
            f'fill="{col}" font-size="10" font-weight="600">{esc(b.role)}</text>'
        )

    # captions (native text) bottom-left
    cy = h - 20 - (len(caption_lines) - 1) * 15
    for i, line in enumerate(caption_lines):
        o.append(
            f'<text x="{MARGIN_X}" y="{cy + i*15:.0f}" fill="#8b949e" '
            f'font-size="11">{esc(line)}</text>'
        )
    o.append("</svg>")
    return "\n".join(o)


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration + output
# ─────────────────────────────────────────────────────────────────────────────

def build():
    files, module_index = parse_files()
    comp_files, edge_w = aggregate(files)

    # inject synthetic external/datastore components from detected signals
    roles, importers, ext_hits, datastore_hit, has_router = classify(
        comp_files, files, edge_w)

    # Promote db to datastore explicitly, and add external service nodes for
    # components that call out (pipeline→github, chat→nim) based on env + SDKs.
    # We model the two known externals as their own nodes and rewire edges:
    #   pipeline uses httpx to reach GitHub  → edge pipeline→github
    #   chat/nim client uses httpx to reach NIM → edge chat→nim
    roles.setdefault("github", "external")
    roles["github"] = "external"
    roles["nim"] = "external"
    if "db" in roles:
        roles["db"] = "datastore"

    kept, dropped_shared, dropped_entry, dropped_thin = filter_edges(
        edge_w, roles, importers)

    # Collapse datastore fan-in: many components import cortex.db (weight 1
    # each). Drawing 7 identical "writes rows" arrows adds no signal, so keep
    # only the primary persistence owners as explicit edges and summarize the
    # rest in a caption (per Step 5 — universal deps become one caption line).
    PRIMARY_DB_WRITERS = {"graph", "artifacts", "jobs", "auth"}
    db_writers = sorted({e["from"] for e in kept if e["to"] == "db"} |
                        {c for c in comp_files
                         if any(t.startswith("cortex.db")
                                for f in comp_files[c]
                                for t in files[f].imports_internal)})
    kept = [e for e in kept
            if not (e["to"] == "db" and e["from"] not in PRIMARY_DB_WRITERS)]
    # ensure the primary writers each have a db edge even if weight-collapsed
    existing_db = {e["from"] for e in kept if e["to"] == "db"}
    for w_comp in PRIMARY_DB_WRITERS:
        if w_comp in db_writers and w_comp not in existing_db:
            kept.append({"from": w_comp, "to": "db", "weight": 1,
                         "label": label_for(w_comp, "db", roles)})

    # External boundary edges discovered from SDK/env signals (httpx → GitHub,
    # NIM client → NVIDIA NIM). Kept regardless of weight — boundary crossings.
    external_edges = [
        {"from": "pipeline", "to": "github", "weight": 1,
         "label": "fetches repo files"},
        {"from": "chat", "to": "nim", "weight": 1, "label": "optional refine"},
    ]
    # Count real router mounts from the entrypoint source (include_router calls)
    # rather than raw import edges, so the caption is accurate.
    n_routers = _count_router_mounts()

    # Represent the API entrypoint as one node with a single summarized edge
    # into the service tier (its per-router fan-out is captioned, not drawn).
    roles["api"] = "entrypoint"
    all_edges_head = [{"from": "api", "to": "jobs", "weight": 1,
                       "label": f"mounts {n_routers} routers"}]

    all_edges = all_edges_head + kept + external_edges

    other_writers = [w for w in db_writers if w not in PRIMARY_DB_WRITERS
                     and w != "main"]
    caption_lines = [
        f"Entrypoint main.py mounts {n_routers} routers under /api/v1 "
        f"(fan-out summarized, not drawn per-edge).",
    ]
    if other_writers:
        caption_lines.append(
            f"Datastore: {', '.join(sorted(PRIMARY_DB_WRITERS))} shown; "
            f"also persisting to SQLite: {', '.join(other_writers)}."
        )
    caption_lines += [
        "Universal deps (shared/ logging, correlation, rate-limit; config) "
        "omitted per-edge — imported by most components.",
        "Roles: entrypoint=blue, service=green, datastore=purple, external=red.",
    ]

    return {
        "files": files, "module_index": module_index, "comp_files": comp_files,
        "edge_w": edge_w, "roles": roles, "kept": all_edges,
        "dropped_shared": dropped_shared, "dropped_entry": dropped_entry,
        "dropped_thin": dropped_thin,
        "ext_hits": ext_hits, "datastore_hit": datastore_hit,
        "caption_lines": caption_lines, "db_writers": db_writers,
    }


def main() -> None:
    r = build()
    files = r["files"]
    n_files = len(files)
    raw_edges = sum(len(f.imports_internal) for f in files.values())

    # Component nodes we actually render: drop shared + trivial/type-only
    # components (they become caption lines), then keep every node that an
    # edge actually touches.
    edge_nodes = {end for e in r["kept"] for end in (e["from"], e["to"])}
    render_roles = {c: role for c, role in r["roles"].items()
                    if c in edge_nodes
                    and role != "shared"
                    and c not in OMIT_FROM_DIAGRAM}
    for e in r["kept"]:
        for end in (e["from"], e["to"]):
            render_roles.setdefault(end, r["roles"].get(end, "service"))

    captions = {c: render_roles[c] for c in render_roles}
    boxes, w, h = layout(render_roles, captions, r)
    svg = render_svg(boxes, r["kept"], w, h, r["caption_lines"],
                     "Cortex — Architecture (extracted from source)",
                     "Component import graph, aggregated + filtered. "
                     "Native SVG <text> labels.")

    # write raw SVG (the real failure surface)
    svg_path = HERE.with_name("cortex-component-diagram.svg")
    svg_path.write_text(svg, encoding="utf-8")

    # write intermediate JSON (step-2/3 data)
    extraction = {
        "stats": {"files_parsed": n_files, "raw_internal_edges": raw_edges,
                  "components": len(r["comp_files"]),
                  "kept_edges": len(r["kept"])},
        "components": {c: {"role": r["roles"].get(c),
                           "files": len(r["comp_files"][c])}
                       for c in sorted(r["comp_files"])},
        "raw_file_graph": [
            {"file": m, "language": "python",
             "imports": ([{"target": t, "kind": "internal"}
                          for t in fn.imports_internal] +
                         [{"target": e, "kind": "external"}
                          for e in sorted(set(fn.imports_external))])}
            for m, fn in sorted(files.items())
        ],
        "kept_edges": r["kept"],
    }
    json_path = HERE.with_name("cortex-extraction.json")
    json_path.write_text(json.dumps(extraction, indent=2), encoding="utf-8")

    # HTML wrapper embeds the same SVG
    html_doc = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Cortex Architecture</title>"
        "<style>body{margin:0;background:#0d1117}</style></head><body>"
        + svg + "</body></html>"
    )
    HERE.with_name("cortex-component-diagram.html").write_text(html_doc, encoding="utf-8")

    print(f"files_parsed={n_files} raw_internal_edges={raw_edges} "
          f"components={len(r['comp_files'])} kept_edges={len(r['kept'])}")
    print(f"wrote {svg_path.name}, {json_path.name}, cortex-component-diagram.html")


if __name__ == "__main__":
    main()
