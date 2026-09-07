# Graph Data Model

The Cortex code knowledge graph model. The graph is stored in SQLite (nodes and
edges tables in `cortex.db`) via `graph/infrastructure/sqlite_repository.py`; the
node/edge model below is backend-agnostic and would map directly onto a property
graph such as Neo4j if that backend is ever adopted.

## Node Labels

| Label      | Properties                  | Description                   |
|------------|-----------------------------|-------------------------------|
| Repository | id, url, name               | Top-level repo node           |
| Module     | id, name, path              | Python/JS module              |
| File       | id, name, path, language    | Source file                   |
| Function   | id, name, signature         | Function or method            |
| Class      | id, name                    | Class definition              |
| Pattern    | id, name, category          | Detected design pattern       |

## Relationship Types

| Type        | From → To              | Meaning                     |
|-------------|------------------------|-----------------------------|
| CONTAINS    | Repository → Module    | Repo contains module        |
| CONTAINS    | Module → File          | Module contains file        |
| IMPORTS     | File → File            | File imports another file   |
| DEPENDS_ON  | Module → Module        | Module-level dependency     |
| EXHIBITS    | File → Pattern         | File exhibits a design pattern |
| CALLS       | Function → Function    | Function calls another      |
