# Graph Data Model

Neo4j 5.20 graph model for the Cortex code knowledge graph.

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
