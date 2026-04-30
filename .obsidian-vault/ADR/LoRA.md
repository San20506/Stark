---
source: brief
introduced-in: first-run
last-updated: first-run
component: Learning
---

# LoRA (Low-Rank Adaptation)

## Why Chosen
LoRA enables parameter-efficient fine-tuning — adapts a base model with <1% of original parameters. Rank 8 adapters fit entirely in system RAM during training, leaving VRAM for inference. Enables 50+ task-specific adapters without 50× the storage.

## How It Fits
lora_adapter.py implements the LoRA matrices. adapter_manager.py manages 50+ task-specific adapters. continual_learner.py runs training in a background thread using the experience replay buffer (1M experiences).

## Problem Solved
Need to continuously improve inference quality through background learning without taking the system offline for retraining — LoRA adapters train incrementally without catastrophic forgetting of the base model.
