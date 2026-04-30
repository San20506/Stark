---
source: brief
introduced-in: first-run
last-updated: first-run
component: Inference
---

# Ollama

## Why Chosen
Local LLM inference with task-routed model selection (TASK_MODELS config). Multiple specialized models can be loaded for different query types (coding vs. reasoning vs. general). keep_alive prevents cold-start latency for the <50ms inference target.

## How It Fits
STARK's inference backend. The adaptive_router selects which Ollama model to use based on query classification. Never called directly by capability modules — always mediated through core/main.py.

## Problem Solved
Need for task-appropriate model routing — a 3B coding model gives better code results than a general 7B model for code queries, at lower latency. Ollama's API makes multi-model switching trivial.
