---
source: docs-generated
generated-at: first-run
---

# STARK — Self-Training Adaptive Reasoning Kernel

## What It Does
Fully offline, self-improving AI assistant that routes queries to local LLMs, stores 1M+ experiences in a neuromorphic memory network, and fine-tunes LoRA adapters continuously in the background. Target: <50ms inference on consumer hardware (RTX 4060).

## Primary Goal
AI assistant that never stops learning — continuously improves from interactions without catastrophic forgetting, running entirely on local hardware.

## Major Components
- **Core** — Constants, config, task detector (TF-IDF, 8 categories), adaptive router, orchestration
- **Models** — Ollama-backed base model loader + optimized inference engine
- **Memory (v0.2.0)** — 4-layer cognitive stack: Appraisal Engine, Episode Manager, ACT-R Scorer, Knowledge Graph, Diary Store, Reflection Loop, Consolidation
- **Learning** — LoRA adapters, continual learner, background training thread
- **Capabilities** — NLP interface, code assistant, reasoning (chain-of-thought)
- **MCP** — MCP server + client for external tool integration

## Technology Stack
- Language: Python
- LLM: DeepSeek Coder 1.3B (int8) via Ollama; task-routed model selection
- LoRA: PEFT library
- Memory: SQLite (diary/thread state), NetworkX/A-MEM (knowledge graph)
- Embeddings: GloVe 6B
- Voice: GPT-SoVITS (TTS)
- MCP: Model Context Protocol SDK
- Web UI: Flask/web_server.py

## Architectural Principles
- MEMORY_V2_ENABLED feature flag gates new memory path
- All thresholds/constants in core/constants.py — zero hardcoding
- predict() must return in <3s; reflection/consolidation are async-only
- Memory is append-only (soft-delete only, never DELETE FROM episodes)
- GPU mutex prevents writes during consolidation
- OpenSpec proposal required for API-level changes
