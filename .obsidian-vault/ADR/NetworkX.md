---
source: brief
introduced-in: first-run
last-updated: first-run
component: Memory
---

# NetworkX (A-MEM Knowledge Graph)

## Why Chosen
NetworkX provides in-memory graph data structures for the A-MEM semantic knowledge graph. Bidirectional links between concepts, Zettelkasten-style connections, and episodic→semantic promotion all map naturally to graph operations.

## How It Fits
knowledge_graph.py implements the semantic graph layer of STARK's 4-layer memory stack. The consolidation.py daemon promotes diary patterns → knowledge graph nodes during nightly consolidation.

## Problem Solved
Long-term semantic memory (what STARK has learned across thousands of interactions) is better represented as a graph of connected concepts than as flat rows — enabling retrieval by concept proximity, not just keyword match.
