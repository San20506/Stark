## ADDED Requirements

### Requirement: Accurate Install Docs
Install docs SHALL describe the post-S6 reality: MiniLM embeddings, no
NetworkX, and consistent model tags — with no `*.py` changes.

#### Scenario: GloVe gone
- **WHEN** the install doc is read
- **THEN** no GloVe 2GB `wget` or `networkx` install remains

#### Scenario: Tags agree
- **WHEN** constants, config, and docs are compared
- **THEN** the reflection and task model tags match
