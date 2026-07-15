"""GitHub API client — fetches repository structure and file contents.
This is the data ingestion layer for the Cortex pipeline."""

import base64
from dataclasses import dataclass
from typing import Any
import httpx
import structlog
from cortex.config import get_settings
from shared.exceptions import InfrastructureError

logger = structlog.get_logger()


@dataclass
class GitHubFile:
    """A single file fetched from a GitHub repository."""
    path: str
    name: str
    content: str
    size: int
    sha: str
    encoding: str = "utf-8"

    def is_code_file(self) -> bool:
        """Returns True if this is a source code file worth parsing."""
        code_extensions = {
            ".py", ".java", ".ts", ".tsx", ".js", ".jsx",
            ".go", ".rs", ".cpp", ".c", ".cs", ".rb",
            ".kt", ".swift", ".scala", ".r", ".m",
        }
        return any(self.path.endswith(ext) for ext in code_extensions)

    def is_config_file(self) -> bool:
        """Returns True if this is a config/build file."""
        config_files = {
            "package.json", "pyproject.toml", "pom.xml",
            "build.gradle", "Cargo.toml", "go.mod",
            "requirements.txt", "setup.py", "Makefile",
        }
        config_extensions = {".yaml", ".yml", ".toml", ".json"}
        return (
            self.name in config_files or
            any(self.path.endswith(ext) for ext in config_extensions)
        )

    def line_count(self) -> int:
        """Returns the number of lines in this file."""
        return len(self.content.splitlines())


@dataclass
class GitHubTreeNode:
    """A single node in the repository file tree."""
    path: str
    type: str  # "blob" (file) or "tree" (directory)
    sha: str
    size: int = 0
    url: str = ""

    def is_file(self) -> bool:
        return self.type == "blob"

    def is_directory(self) -> bool:
        return self.type == "tree"

    def extension(self) -> str:
        """Returns the file extension including the dot."""
        if "." in self.path:
            return "." + self.path.rsplit(".", 1)[-1].lower()
        return ""


@dataclass
class RepoInfo:
    """Basic metadata about a GitHub repository."""
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

    Handles authentication, rate limiting, base64 decoding,
    and error normalization. All methods are async.

    Usage:
        client = GitHubClient()
        owner, repo = client.parse_repo_url("https://github.com/user/repo")
        tree = await client.get_file_tree(owner, repo)
        file = await client.get_file_content(owner, repo, "src/main.py")
    """

    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        settings = get_settings()
        self._token = settings.github_token
        self._headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            self._headers["Authorization"] = f"Bearer {self._token}"

    def parse_repo_url(self, url: str) -> tuple[str, str]:
        """Parse a GitHub URL into (owner, repo) tuple.

        Handles:
            https://github.com/owner/repo
            https://github.com/owner/repo/
            https://github.com/owner/repo.git
        """
        url = url.rstrip("/").removesuffix(".git")
        parts = url.replace("https://github.com/", "").split("/")
        if len(parts) < 2:
            raise ValueError(
                f"Cannot parse GitHub URL: {url}. "
                f"Expected format: https://github.com/owner/repo"
            )
        return parts[0], parts[1]

    async def get_repo_info(
        self,
        owner: str,
        repo: str,
    ) -> RepoInfo:
        """Fetch basic repository metadata."""
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
        """Fetch the complete recursive file tree for a repository.

        Returns all files and directories in one API call.
        GitHub limits this to repositories under 7MB uncompressed.
        """
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
        """Fetch and decode the content of a single file.

        GitHub returns file content as base64 encoded text.
        This method decodes it to a plain string automatically.
        """
        data = await self._get(
            f"/repos/{owner}/{repo}/contents/{path}"
        )

        if data.get("type") != "file":
            raise InfrastructureError(
                f"Path is not a file: {path}"
            )

        # GitHub returns base64 with newlines — strip them first
        raw_content = data.get("content", "")
        raw_content = raw_content.replace("\n", "").replace(" ", "")

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
        max_files: int = 50,
    ) -> list[GitHubFile]:
        """Fetch the content of all code files in a repository.

        Filters to only source code files (Python, Java, TypeScript etc.)
        Limits to max_files to avoid hitting rate limits.
        Files are sorted by size ascending — smaller files first.
        """
        tree = await self.get_file_tree(owner, repo)

        # Filter to code files only, sorted by size
        code_nodes = sorted(
            [n for n in tree if n.is_file() and n.extension() in {
                ".py", ".java", ".ts", ".tsx", ".js", ".jsx",
                ".go", ".rs", ".cpp", ".c", ".cs", ".rb",
            }],
            key=lambda n: n.size,
        )[:max_files]

        logger.info(
            "github_fetching_code_files",
            owner=owner,
            repo=repo,
            file_count=len(code_nodes),
        )

        files = []
        for node in code_nodes:
            try:
                file = await self.get_file_content(owner, repo, node.path)
                files.append(file)
                logger.info(
                    "github_file_fetched",
                    path=node.path,
                    lines=file.line_count(),
                )
            except InfrastructureError as e:
                # Skip files that can't be decoded — binary files etc.
                logger.warning(
                    "github_file_skipped",
                    path=node.path,
                    reason=str(e),
                )
                continue

        return files

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated GET request to the GitHub API."""
        url = f"{self.BASE_URL}{path}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers=self._headers,
                    params=params or {},
                    timeout=30.0,
                )
            except httpx.TimeoutException:
                raise InfrastructureError(
                    f"GitHub API request timed out: {path}"
                )
            except httpx.NetworkError as e:
                raise InfrastructureError(
                    f"GitHub API network error: {e}"
                )

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
                f"GitHub API error {response.status_code}: "
                f"{response.text[:200]}"
            )

        return response.json()