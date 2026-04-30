---
source: brief
introduced-in: first-run
last-updated: first-run
component: Memory
---

# SQLite (WAL mode)

## Why Chosen
Append-only episodic log (diary_store.py) requires a reliable, local, low-overhead database. WAL mode allows concurrent reads during write operations — critical since inference reads memory while the reflection loop writes to it. SQLite WAL checkpointing in thread_state.py handles session persistence.

## How It Fits
diary_store.py stores the episodic memory log (append-only — R1 cardinal rule: never DELETE). thread_state.py uses SQLite for session checkpoint/crash recovery. Queried by activation_scorer.py for temporal retrieval.

## Problem Solved
Memory data must be append-only (cardinal rule R1) and crash-safe. SQLite's WAL mode with checkpointing provides both durability and the read/write concurrency needed between inference and background reflection.
