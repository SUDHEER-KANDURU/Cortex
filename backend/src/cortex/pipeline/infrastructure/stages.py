"""Pipeline stages — each stage does one job in the analysis pipeline.
GitHub fetch → AST parse → Graph build → Artifact generate.
Every stage reads from context, does its work, writes back to context."""

import json
import structlog

from cortex.pipeline.application.orchestrator import PipelineContext
from cortex.pipeline.domain.interfaces import AbstractPipelineStage
from cortex.pipeline.infrastructure.github_client import GitHubClient
from cortex.pipeline.infrastructure.ast_parser import ASTParser
from cortex.pipeline.infrastructure.graph_builder import GraphBuilder
from cortex.graph.domain.entities import NodeType, RelationshipType
from cortex.artifacts.domain.entities import ArtifactContentType

logger = structlog.get_logger()


class GitHubFetchStage(AbstractPipelineStage):
    """Stage 1 — Fetches repository structure and file contents
    from GitHub using the GitHub REST API."""

    def __init__(self) -> None:
        self._client = GitHubClient()

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Fetch the repository file tree and all code files."""
        try:
            owner, repo = self._client.parse_repo_url(
                context.repo_url
            )

            logger.info(
                "github_fetch_stage_started",
                job_id=context.job.id,
                owner=owner,
                repo=repo,
            )

            # Fetch repo metadata
            repo_info = await self._client.get_repo_info(owner, repo)
            logger.info(
                "repo_info_fetched",
                name=repo_info.full_name,
                language=repo_info.language,
                stars=repo_info.stars,
            )

            # Fetch full file tree
            tree = await self._client.get_file_tree(owner, repo)
            context.file_tree = [
                {
                    "path": node.path,
                    "type": node.type,
                    "size": node.size,
                }
                for node in tree
            ]

            # Fetch actual code file contents
            code_files = await self._client.get_code_files(
                owner, repo, max_files=60
            )

            context.file_contents = {
                f.path: f.content for f in code_files
            }

            logger.info(
                "github_fetch_stage_completed",
                job_id=context.job.id,
                tree_nodes=len(context.file_tree),
                code_files=len(context.file_contents),
            )

        except Exception as e:
            context.mark_error(
                f"GitHubFetchStage failed: {str(e)}"
            )

        return context


class ASTParseStage(AbstractPipelineStage):
    """Stage 2 — Parses all fetched code files using the AST parser.
    Extracts classes, functions, imports, and dependencies."""

    def __init__(self) -> None:
        self._parser = ASTParser()

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Parse all code files in context.file_contents."""
        if not context.file_contents:
            context.mark_error(
                "ASTParseStage: no file contents to parse. "
                "GitHubFetchStage may have failed."
            )
            return context

        try:
            logger.info(
                "ast_parse_stage_started",
                job_id=context.job.id,
                file_count=len(context.file_contents),
            )

            files_to_parse = [
                (content, path)
                for path, content in context.file_contents.items()
            ]

            parsed_files = self._parser.parse_many(files_to_parse)

            # Store parsed results in context for graph builder
            context._parsed_files = parsed_files  # type: ignore[attr-defined]

            successful = [p for p in parsed_files if not p.has_errors()]
            failed = [p for p in parsed_files if p.has_errors()]

            logger.info(
                "ast_parse_stage_completed",
                job_id=context.job.id,
                total=len(parsed_files),
                successful=len(successful),
                failed=len(failed),
                total_classes=sum(
                    len(p.classes) for p in successful
                ),
                total_functions=sum(
                    len(p.all_functions()) for p in successful
                ),
            )

        except Exception as e:
            context.mark_error(f"ASTParseStage failed: {str(e)}")

        return context


class GraphBuildStage(AbstractPipelineStage):
    """Stage 3 — Builds the knowledge graph from parsed files.
    Creates nodes and edges representing the codebase structure."""

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Build graph from parsed files and store via repository."""
        parsed_files = getattr(context, "_parsed_files", None)

        if not parsed_files:
            context.mark_error(
                "GraphBuildStage: no parsed files found. "
                "ASTParseStage may have failed."
            )
            return context

        try:
            logger.info(
                "graph_build_stage_started",
                job_id=context.job.id,
                parsed_file_count=len(parsed_files),
            )

            builder = GraphBuilder(
                job_id=context.job.id,
                repo_url=context.repo_url,
            )

            graph_result = builder.build(parsed_files)

            print("[graph_debug] graph_build_complete", {
                "nodes": graph_result.node_count(),
                "edges": graph_result.edge_count(),
                "modules": len([
                    n for n in graph_result.nodes
                    if n.node_type.value == "Module"
                ]),
            })
            print(
                "[pipeline_debug][GraphBuildStage] graph_after_build",
                {
                    "node_count": graph_result.node_count(),
                    "edge_count": graph_result.edge_count(),
                    "first_nodes": [
                        {
                            "type": node.node_type.value,
                            "label": node.label,
                            "path": node.properties.get("path"),
                        }
                        for node in graph_result.nodes[:30]
                    ],
                    "first_edges": [
                        {
                            "source": edge.source_id,
                            "target": edge.target_id,
                            "relationship": edge.relationship.value,
                        }
                        for edge in graph_result.edges[:30]
                    ],
                    "node_types": {
                        node_type.value: sum(
                            1 for n in graph_result.nodes if n.node_type == node_type
                        )
                        for node_type in sorted(
                            {node.node_type for node in graph_result.nodes},
                            key=lambda item: item.value,
                        )
                    },
                    "edge_types": {
                        relationship.value: sum(
                            1 for e in graph_result.edges if e.relationship == relationship
                        )
                        for relationship in sorted(
                            {edge.relationship for edge in graph_result.edges},
                            key=lambda item: item.value,
                        )
                    },
                },
            )

            context.node_count = graph_result.node_count()
            context.edge_count = graph_result.edge_count()

            # Store graph data in context for artifact generation
            context._graph_result = graph_result  # type: ignore[attr-defined]

            logger.info(
                "graph_build_stage_completed",
                job_id=context.job.id,
                nodes=context.node_count,
                edges=context.edge_count,
            )

        except Exception as e:
            context.mark_error(f"GraphBuildStage failed: {str(e)}")

        return context


class ArtifactGenerateStage(AbstractPipelineStage):
    """Stage 4 — Generates artifacts from the knowledge graph.
    Produces Mermaid diagrams, learning paths, and interview prep.
    Persists the artifact via ArtifactService and stores the artifact_id
    in the context so callers can retrieve it."""

    def __init__(self, artifact_service: "ArtifactService") -> None:  # type: ignore[name-defined]
        self._artifact_service = artifact_service

    async def execute(self, context: PipelineContext) -> PipelineContext:
        """Generate artifacts from the knowledge graph."""
        graph_result = getattr(context, "_graph_result", None)

        if not graph_result:
            context.mark_error(
                "ArtifactGenerateStage: no graph result found."
            )
            return context

        try:
            from cortex.pipeline.infrastructure.artifact_generator import (
                MermaidGenerator,
                MarkdownReportGenerator,
            )

            repo_name = context.repo_url.rstrip("/").split("/")[-1]
            artifact_type = context.artifact_type.value
            mermaid_gen = MermaidGenerator()
            markdown_gen = MarkdownReportGenerator()

            if artifact_type == "architecture_diagram":
                print(
                    "[pipeline_debug][ArtifactGenerateStage] graph_before_mermaid",
                    {
                        "node_count": graph_result.node_count(),
                        "edge_count": graph_result.edge_count(),
                        "first_nodes": [
                            {
                                "type": node.node_type.value,
                                "label": node.label,
                                "path": node.properties.get("path"),
                            }
                            for node in graph_result.nodes[:30]
                        ],
                        "first_edges": [
                            {
                                "source": edge.source_id,
                                "target": edge.target_id,
                                "relationship": edge.relationship.value,
                            }
                            for edge in graph_result.edges[:30]
                        ],
                    },
                )
                content = mermaid_gen.generate(graph_result, repo_name)
                content_type = ArtifactContentType.MERMAID

            elif artifact_type == "module_breakdown":
                content = markdown_gen.generate_module_breakdown(
                    graph_result, repo_name
                )
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "learning_path":
                content = markdown_gen.generate_learning_path(
                    graph_result, repo_name
                )
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "api_spec":
                content = markdown_gen.generate_api_spec(
                    graph_result, repo_name
                )
                content_type = ArtifactContentType.MARKDOWN

            elif artifact_type == "interview_questions":
                content = markdown_gen.generate_interview_questions(
                    graph_result, repo_name
                )
                content_type = ArtifactContentType.MARKDOWN

            else:
                content = mermaid_gen.generate(graph_result, repo_name)
                content_type = ArtifactContentType.MERMAID

            context.artifact_content = content
            context._artifact_content_type = content_type  # type: ignore[attr-defined]

            logger.info(
                "artifact_generate_stage_completed",
                job_id=context.job.id,
                artifact_type=artifact_type,
                content_length=len(content),
            )

        except Exception as e:
            context.mark_error(
                f"ArtifactGenerateStage failed: {str(e)}"
            )

        return context

    def _generate_architecture_diagram(
        self, graph_result: "GraphBuildResult"  # type: ignore[name-defined]
    ) -> str:
        """Generate a Mermaid architecture diagram."""
        lines = ["graph LR"]

        modules = graph_result.nodes_by_type(NodeType.MODULE)
        files = graph_result.nodes_by_type(NodeType.FILE)
        classes = graph_result.nodes_by_type(NodeType.CLASS)

        # Add module nodes
        for module in modules:
            safe_id = "node_" + module.id.replace("-", "_").replace(".", "_")[:20]
            lines.append(f'  {safe_id}["{module.label}"]')

        # Add class nodes
        for cls in classes[:20]:  # Limit to 20 for readability
            safe_id = cls.id.replace("-", "_")
            lines.append(f'  {safe_id}["{cls.label}"]')

        # Add edges
        for edge in graph_result.edges:
            if edge.relationship == RelationshipType.CONTAINS:
                src = next(
                    (n for n in graph_result.nodes
                     if n.id == edge.source_id), None
                )
                tgt = next(
                    (n for n in graph_result.nodes
                     if n.id == edge.target_id), None
                )
                if src and tgt:
                    if (
                        src.node_type in {NodeType.MODULE, NodeType.REPOSITORY}
                        and tgt.node_type == NodeType.CLASS
                    ):
                        src_id = src.id.replace("-", "_")
                        tgt_id = tgt.id.replace("-", "_")
                        lines.append(f"  {src_id} --> {tgt_id}")

            elif edge.relationship == RelationshipType.INHERITS:
                src = next(
                    (n for n in graph_result.nodes
                     if n.id == edge.source_id), None
                )
                tgt = next(
                    (n for n in graph_result.nodes
                     if n.id == edge.target_id), None
                )
                if src and tgt:
                    src_id = src.id.replace("-", "_")
                    tgt_id = tgt.id.replace("-", "_")
                    lines.append(f"  {src_id} -.->|inherits| {tgt_id}")

        return "\n".join(lines)

    def _generate_module_breakdown(
        self, graph_result: "GraphBuildResult"  # type: ignore[name-defined]
    ) -> str:
        """Generate a markdown module breakdown report."""
        lines = ["# Module Breakdown\n"]
        lines.append(
            f"**Total nodes:** {graph_result.node_count()}  \n"
            f"**Total edges:** {graph_result.edge_count()}\n"
        )

        modules = graph_result.nodes_by_type(NodeType.MODULE)
        files = graph_result.nodes_by_type(NodeType.FILE)
        classes = graph_result.nodes_by_type(NodeType.CLASS)
        functions = graph_result.nodes_by_type(NodeType.FUNCTION)

        lines.append(f"## Summary\n")
        lines.append(f"| Layer | Count |")
        lines.append(f"|---|---|")
        lines.append(f"| Modules | {len(modules)} |")
        lines.append(f"| Files | {len(files)} |")
        lines.append(f"| Classes | {len(classes)} |")
        lines.append(f"| Functions | {len(functions)} |")
        lines.append("")

        lines.append("## Modules\n")
        for module in modules:
            lines.append(f"### `{module.label}`")
            module_files = [
                f for f in files
                if str(f.properties.get("path", "")).startswith(
                    module.label.rstrip("/")
                )
            ]
            lines.append(f"**Files:** {len(module_files)}\n")
            for f in module_files:
                lines.append(
                    f"- `{f.label}` — "
                    f"{f.properties.get('lines', 0)} lines, "
                    f"{f.properties.get('classes', 0)} classes, "
                    f"{f.properties.get('functions', 0)} functions"
                )
            lines.append("")

        return "\n".join(lines)

    def _generate_learning_path(
        self,
        graph_result: "GraphBuildResult",  # type: ignore[name-defined]
        context: PipelineContext,
    ) -> str:
        """Generate a personalized learning path."""
        repo_name = context.repo_url.split("/")[-1]
        classes = graph_result.nodes_by_type(NodeType.CLASS)
        modules = graph_result.nodes_by_type(NodeType.MODULE)

        lines = [f"# Learning Path: {repo_name}\n"]
        lines.append(
            "A structured path to understand this codebase "
            "from first principles.\n"
        )

        lines.append("## Week 1 — Project Structure\n")
        lines.append(
            "Start by understanding what each module does "
            "before reading any code.\n"
        )
        for module in modules:
            lines.append(f"- **`{module.label}`** — understand its responsibility")
        lines.append("")

        lines.append("## Week 2 — Core Domain\n")
        lines.append(
            "Read the domain layer entities and interfaces. "
            "These define the language of the system.\n"
        )
        domain_classes = [
            c for c in classes
            if "domain" in str(c.properties.get("file", ""))
        ]
        for cls in domain_classes[:6]:
            lines.append(f"- **`{cls.label}`** — `{cls.properties.get('file', '')}`")
        lines.append("")

        lines.append("## Week 3 — Application Layer\n")
        lines.append(
            "Study the use cases and service classes. "
            "This is where business logic lives.\n"
        )
        app_classes = [
            c for c in classes
            if "application" in str(c.properties.get("file", ""))
            or "use_cases" in str(c.properties.get("file", ""))
            or "service" in c.label.lower()
        ]
        for cls in app_classes[:6]:
            lines.append(f"- **`{cls.label}`** — `{cls.properties.get('file', '')}`")
        lines.append("")

        lines.append("## Week 4 — Infrastructure\n")
        lines.append(
            "Read the repository and infrastructure implementations. "
            "See how data is stored and retrieved.\n"
        )
        infra_classes = [
            c for c in classes
            if "infrastructure" in str(c.properties.get("file", ""))
            or "repository" in c.label.lower()
        ]
        for cls in infra_classes[:6]:
            lines.append(f"- **`{cls.label}`** — `{cls.properties.get('file', '')}`")
        lines.append("")

        lines.append("## Key Concepts to Study\n")
        abstract_classes = [
            c for c in classes
            if str(c.properties.get("is_abstract", False)) == "True"
        ]
        if abstract_classes:
            lines.append(
                "These abstract classes define the system's contracts:"
            )
            for cls in abstract_classes:
                lines.append(f"- `{cls.label}`")

        return "\n".join(lines)

    def _generate_api_spec(
        self, graph_result: "GraphBuildResult"  # type: ignore[name-defined]
    ) -> str:
        """Generate an API specification from router functions."""
        functions = graph_result.nodes_by_type(NodeType.FUNCTION)
        router_fns = [
            f for f in functions
            if "router" in str(f.properties.get("file", ""))
            or "controller" in str(f.properties.get("file", "")).lower()
        ]

        lines = ["# API Specification\n"]
        lines.append(
            "Auto-generated from router and controller files.\n"
        )

        if not router_fns:
            lines.append(
                "_No router or controller files detected. "
                "This repository may not be an API project._"
            )
            return "\n".join(lines)

        lines.append("## Endpoints\n")
        lines.append("| Function | File | Parameters |")
        lines.append("|---|---|---|")
        for fn in router_fns:
            params = fn.properties.get("parameters", "")
            file_path = fn.properties.get("file", "")
            lines.append(f"| `{fn.label}` | `{file_path}` | `{params}` |")

        return "\n".join(lines)

    def _generate_interview_questions(
        self,
        graph_result: "GraphBuildResult",  # type: ignore[name-defined]
        context: PipelineContext,
    ) -> str:
        """Generate interview questions about the codebase."""
        repo_name = context.repo_url.split("/")[-1]
        classes = graph_result.nodes_by_type(NodeType.CLASS)
        modules = graph_result.nodes_by_type(NodeType.MODULE)
        abstract = [
            c for c in classes
            if str(c.properties.get("is_abstract", False)) == "True"
        ]

        lines = [f"# Interview Preparation: {repo_name}\n"]
        lines.append(
            "10 technical questions about this specific codebase.\n"
        )

        questions = [
            (
                "Architecture",
                f"Walk me through the high-level architecture of {repo_name}. "
                f"What are the {len(modules)} main modules and what does each one do?"
            ),
            (
                "Design Patterns",
                f"This codebase has {len(abstract)} abstract classes. "
                "What design pattern does this suggest and why is it used here?"
            ),
            (
                "Clean Architecture",
                "Explain the separation between the domain, application, "
                "infrastructure, and presentation layers in this codebase."
            ),
            (
                "Data Flow",
                "Trace the complete data flow from an incoming API request "
                "to the database and back. Name the specific classes involved."
            ),
            (
                "Dependency Injection",
                "How are dependencies injected in this codebase? "
                "Give a specific example using the actual class names."
            ),
            (
                "Error Handling",
                "How does this codebase handle errors? "
                "What exception hierarchy exists and where are exceptions caught?"
            ),
            (
                "Testing Strategy",
                "How would you write a unit test for the service layer "
                "in this codebase? What would you mock?"
            ),
            (
                "Scalability",
                f"This codebase has {graph_result.node_count()} graph nodes. "
                "What would need to change to handle 10x the current load?"
            ),
            (
                "Technical Decisions",
                "What was the most important technical decision made in this "
                "codebase and what tradeoffs does it involve?"
            ),
            (
                "Improvements",
                "If you had one week to improve this codebase, "
                "what would you change first and why?"
            ),
        ]

        for i, (category, question) in enumerate(questions, 1):
            lines.append(f"## Q{i}: {category}\n")
            lines.append(f"{question}\n")
            lines.append(
                "_Study tip: Answer using specific class and method names "
                "from the codebase, not generic descriptions._\n"
            )

        return "\n".join(lines)

    def _generate_folder_structure(
        self, context: PipelineContext
    ) -> str:
        """Generate a folder structure tree from the file tree."""
        if not context.file_tree:
            return "No file tree available."

        lines = ["Repository Structure\n", "```"]
        seen_dirs: set[str] = set()

        for item in sorted(
            context.file_tree, key=lambda x: x["path"]
        )[:100]:
            path = item["path"]
            depth = path.count("/")
            indent = "  " * depth
            name = path.split("/")[-1]

            if item["type"] == "tree":
                if path not in seen_dirs:
                    lines.append(f"{indent}{name}/")
                    seen_dirs.add(path)
            else:
                lines.append(f"{indent}{name}")

        lines.append("```")
        return "\n".join(lines)