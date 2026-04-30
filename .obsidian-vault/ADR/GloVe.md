---
source: brief
introduced-in: first-run
last-updated: first-run
component: Core
---

# GloVe Embeddings

## Why Chosen
GloVe 6B provides fast, cached word embeddings for the TF-IDF task detector and intent classifier. Pre-trained on 6 billion tokens — covers the vocabulary needed for task classification without requiring a neural embedding call on every query.

## How It Fits
Used by core/task_detector.py for the 8-category task classification. The 400-dimension vectors enable semantic similarity matching that improves on pure TF-IDF for short queries.

## Problem Solved
The TF-IDF task detector needs semantic similarity that pure keyword matching misses — GloVe provides that without the latency of calling the LLM for every classification decision.
