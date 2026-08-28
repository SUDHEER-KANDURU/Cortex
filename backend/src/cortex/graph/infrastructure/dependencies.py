"""Graph infrastructure dependency — singleton repository instance."""

from cortex.config import get_settings
from cortex.graph.infrastructure.sqlite_repository import SQLiteGraphRepository

graph_repository = SQLiteGraphRepository(get_settings().database_url)
