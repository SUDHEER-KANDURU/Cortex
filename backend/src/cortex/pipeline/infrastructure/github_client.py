"""GitHub API client — fetches repository structure and file contents."""

import asyncio
import base64
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from cortex.config import get_settings
from shared.exceptions import InfrastructureError

logger = structlog.get_logger()

# Maximum number of code files fetched/analyzed in a single pass. Raised well
# above the previous fixed cap (was 50/60/150) so large repositories are handled
# (Req 10.1). When a repo has MORE candidate code files than this, the extra
# files are NOT dropped silently — the pipeline records them as coverage gaps so
# analysis degrades to partial Coverage instead of failing (Req 10.3).
MAX_ANALYSIS_FILES = 2000

# Shared set of extensions considered "code" for fetching and classification.
CODE_EXTENSIONS = {
    ".py", ".java", ".ts", ".tsx", ".js", ".jsx",
    ".go", ".rs", ".cpp", ".c", ".cs", ".rb",
    ".kt", ".swift", ".scala", ".r", ".m",
    ".php", ".dart", ".vue", ".svelte", ".lua",
    ".zig", ".ex", ".exs", ".erl", ".hs",
    ".ml", ".pl", ".pm", ".jl", ".sh", ".bash",
    ".html", ".css", ".scss", ".sass", ".less",
    ".sql", ".graphql", ".gql", ".proto",
}

# Fallback extensions used when no code files are found.
CONFIG_EXTENSIONS = {
    ".yaml", ".yml", ".toml", ".json", ".xml",
    ".md", ".rst", ".txt", ".cfg", ".ini",
    ".env", ".dockerfile",
}

CONFIG_FILENAMES = {
    "Dockerfile", "Makefile", "Procfile", "Gemfile",
    "package.json", "pyproject.toml", "pom.xml",
    "build.gradle", "Cargo.toml", "go.mod",
    "requirements.txt", "setup.py", "CMakeLists.txt",
}


@dataclass
class GitHubFile:
    path: str
    name: str
    content: str
    size: int
    sha: str
    encoding: str = "utf-8"

    def is_code_file(self) -> bool:
        return any(self.path.endswith(ext) for ext in CODE_EXTENSIONS)

    def is_config_file(self) -> bool:
        config_files = {
            "package.json", "pyproject.toml", "pom.xml",
            "build.gradle", "Cargo.toml", "go.mod",
            "requirements.txt", "setup.py", "Makefile",
        }
        config_extensions = {".yaml", ".yml", ".toml", ".json"}
        return (
            self.name in config_files
            or any(self.path.endswith(ext) for ext in config_extensions)
        )

    def line_count(self) -> int:
        return len(self.content.splitlines())


@dataclass
class GitHubTreeNode:
    path: str
    type: str  # "blob" or "tree"
    sha: str
    size: int = 0
    url: str = ""

    def is_file(self) -> bool:
        return self.type == "blob"

    def is_directory(self) -> bool:
        return self.type == "tree"

    def extension(self) -> str:
        if "." in self.path:
            return "." + self.path.rsplit(".", 1)[-1].lower()
        return ""


@dataclass
class RepoInfo:
    owner: str
    name: str
    full_name: str
    description: str | None
    default_branch: str
    language: str | None
    stars: int
    forks: int
    size_kb: int
    topics: list[str]

    @property
    def url(self) -> str:
        return f"https://github.com/{self.full_name}"


class GitHubClient:
    """Fetches repository data from the GitHub REST API.

    Fix 11 — uses a persistent httpx.AsyncClient for connection reuse
    instead of opening a new client per request.
    """

    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        settings = get_settings()
        self._token = settings.github_token
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        # Fix 11 — persistent client, shared across all requests in this instance
        self._client = httpx.AsyncClient(headers=headers, timeout=30.0)

        # Candidate code-file paths that exceeded the per-analysis file cap on
        # the most recent get_code_files call. Callers read this to record the
        # over-limit files as coverage gaps (partial Coverage, Req 10.3).
        self.last_skipped_files: list[str] = []

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._client.aclose()

    def parse_repo_url(self, url: str) -> tuple[str, str]:
        url = url.rstrip("/").removesuffix(".git")
        parts = url.replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            raise ValueError(
                f"Cannot parse GitHub URL: {url}. "
                f"Expected format: https://github.com/owner/repo"
            )
        return parts[0], parts[1]

    async def get_repo_info(self, owner: str, repo: str) -> RepoInfo:
        data = await self._get(f"/repos/{owner}/{repo}")
        return RepoInfo(
            owner=owner,
            name=repo,
            full_name=data["full_name"],
            description=data.get("description"),
            default_branch=data.get("default_branch", "main"),
            language=data.get("language"),
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            size_kb=data.get("size", 0),
            topics=data.get("topics", []),
        )

    async def get_file_tree(
        self,
        owner: str,
        repo: str,
        branch: str = "HEAD",
    ) -> list[GitHubTreeNode]:
        data = await self._get(
            f"/repos/{owner}/{repo}/git/trees/{branch}",
            params={"recursive": "1"},
        )

        if data.get("truncated"):
            logger.warning(
                "github_tree_truncated",
                owner=owner,
                repo=repo,
                message="Repository too large — tree was truncated by GitHub",
            )

        nodes = []
        for item in data.get("tree", []):
            nodes.append(GitHubTreeNode(
                path=item["path"],
                type=item["type"],
                sha=item["sha"],
                size=item.get("size", 0),
                url=item.get("url", ""),
            ))

        logger.info(
            "github_tree_fetched",
            owner=owner,
            repo=repo,
            total_nodes=len(nodes),
            files=sum(1 for n in nodes if n.is_file()),
            directories=sum(1 for n in nodes if n.is_directory()),
        )

        return nodes

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
    ) -> GitHubFile:
        data = await self._get(f"/repos/{owner}/{repo}/contents/{path}")

        if data.get("type") != "file":
            raise InfrastructureError(f"Path is not a file: {path}")

        raw_content = data.get("content", "").replace("\n", "").replace(" ", "")

        try:
            decoded = base64.b64decode(raw_content).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as e:
            raise InfrastructureError(
                f"Cannot decode file content for {path}: {e}"
            )

        return GitHubFile(
            path=path,
            name=path.split("/")[-1],
            content=decoded,
            size=data.get("size", 0),
            sha=data.get("sha", ""),
        )

    async def get_code_files(
        self,
        owner: str,
        repo: str,
        max_files: int = MAX_ANALYSIS_FILES,
    ) -> list[GitHubFile]:
        """Fetch code files in parallel with a concurrency limit of 10.

        Fix 10 — replaces sequential for-loop with asyncio.gather + semaphore.
        Fix 12 — expanded extension whitelist; fallback to config/markup files
        when no code files match so the pipeline never returns 0 files for a
        non-empty repository.

        Task 18 — the cap is raised to ``MAX_ANALYSIS_FILES`` so large repos are
        handled (Req 10.1). Candidate code files beyond the cap are recorded in
        ``self.last_skipped_files`` (largest-first ordering preserved) so the
        caller can degrade to partial Coverage rather than dropping them silently
        (Req 10.3).
        """
        tree = await self.get_file_tree(owner, repo)

        ranked_code = sorted(
            [
                n for n in tree
                if n.is_file() and n.extension() in CODE_EXTENSIONS
            ],
            key=lambda n: (-n.size, n.path),  # largest first; path tiebreak = deterministic
        )
        code_nodes = ranked_code[:max_files]
        # Files past the cap are not fetched but are remembered as gaps.
        self.last_skipped_files = [n.path for n in ranked_code[max_files:]]

        # Fallback: if no code files matched, fetch config/markup files so the
        # pipeline has something to analyze rather than failing outright.
        if not code_nodes:
            ranked_config = sorted(
                [
                    n for n in tree
                    if n.is_file() and (
                        n.extension() in CONFIG_EXTENSIONS
                        or n.path.split("/")[-1] in CONFIG_FILENAMES
                    )
                ],
                key=lambda n: (-n.size, n.path),
            )
            code_nodes = ranked_config[:max_files]
            self.last_skipped_files = [n.path for n in ranked_config[max_files:]]

        logger.info(
            "github_fetching_code_files",
            owner=owner,
            repo=repo,
            file_count=len(code_nodes),
        )

        semaphore = asyncio.Semaphore(10)

        async def fetch_one(node: GitHubTreeNode) -> GitHubFile | None:
            async with semaphore:
                try:
                    file = await self.get_file_content(owner, repo, node.path)
                    logger.info(
                        "github_file_fetched",
                        path=node.path,
                        lines=file.line_count(),
                    )
                    return file
                except InfrastructureError as e:
                    logger.warning(
                        "github_file_skipped",
                        path=node.path,
                        reason=str(e),
                    )
                    return None

        results = await asyncio.gather(*[fetch_one(n) for n in code_nodes])
        return [f for f in results if f is not None]

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated GET request to the GitHub API.

        Fix 11 — uses persistent self._client instead of creating a new one.
        """
        url = f"{self.BASE_URL}{path}"

        try:
            response = await self._client.get(url, params=params or {})
        except httpx.TimeoutException:
            raise InfrastructureError(f"GitHub API request timed out: {path}")
        except httpx.NetworkError as e:
            raise InfrastructureError(f"GitHub API network error: {e}")

        if response.status_code == 401:
            raise InfrastructureError(
                "GitHub token is invalid or expired. "
                "Check GITHUB_TOKEN in your .env file."
            )
        if response.status_code == 403:
            raise InfrastructureError(
                "GitHub API rate limit exceeded. "
                "Add a GITHUB_TOKEN to get 5000 requests/hour."
            )
        if response.status_code == 404:
            raise InfrastructureError(
                f"Repository or file not found: {path}. "
                "Check the URL is correct and the repo is public."
            )
        if response.status_code != 200:
            raise InfrastructureError(
                f"GitHub API error {response.status_code}: {response.text[:200]}"
            )

        return response.json()
