# OpenSpec Change: Hermes Messaging Bridge (v0.3.0 "Ubiquity")

**Change ID:** `add-hermes-bridge`
**Status:** Accepted
**Created:** 2026-05-09
**Author:** Sandy (San20506)
**Type:** Feature Addition

---

## Summary

Wire the Hermes MCP messaging bridge (Telegram/Discord/Slack/WhatsApp/Signal/Matrix) into STARK
as a bidirectional transport layer. STARK gains continuous reachability from any device and the
ability to push proactive notifications to the user — Jarvis-style — without any cloud dependency.

---

## Motivation

STARK v0.2.0 (Neuro-Memory) established cognition: local LLM, four-layer memory, agents, voice, RAG.
The missing piece is **ubiquity**: STARK is only reachable from the machine it runs on.
Hermes is already installed as an MCP server bridging all major messaging platforms.
Pairing them closes the loop.

---

## Design Principles

- Hermes is a **transport only** — all cognition stays in `core/main.py`.
- Feature flag `HERMES_ENABLED` (default `False`) gates everything (R6).
- Inbound + outbound are **async only**; never blocks `predict()` < 3s (R3).
- Every Hermes message → diary entry; `conversation_id` maps 1:1 to `thread_id` (P4).
- Proactive outbound gated by appraisal thresholds + cooldown (P5).
- Mention-gate drops group-chat noise before `predict()` (P6).
- Zero hardcoded values (R2).

---

## Architecture

```
[ Telegram / Discord / Slack / WhatsApp / Signal / Matrix ]
                        │
                  Hermes MCP Server
                        │
            ┌───────────▼────────────┐
            │     HermesAgent        │  events_wait() loop
            │   mention_gate.py      │  cheap classifier
            │   hermes_commands.py   │  /slash dispatch
            └───────────┬────────────┘
                        │ text / voice
            ┌───────────▼────────────┐
            │   core/main.py         │  STARK.predict()
            │   thread_state.py      │  cross-channel memory
            │   autonomous_orch.py   │  agent routing
            └───────────┬────────────┘
                        │ reflection complete
            ┌───────────▼────────────┐
            │  proactive_dispatcher  │  goal_relevance gate
            │  proactive_templates   │  message formatting
            └───────────┬────────────┘
                        │ messages_send
                  Hermes MCP Server
                        │
              [ User's phone / chat app ]
```

---

## New Files

```
agents/hermes_agent.py
agents/mention_gate.py
agents/hermes_commands.py
memory/channel_index.py
memory/proactive_dispatcher.py
memory/proactive_templates.py
tests/test_hermes_agent.py
tests/test_mention_gate.py
tests/test_hermes_commands.py
tests/test_proactive_dispatcher.py
tests/test_hermes_e2e.py
```

## Modified Files

```
core/constants.py             HERMES_* constants block
core/config.py                YAML schema hermes section
core/main.py                  boot HermesAgent when HERMES_ENABLED
memory/thread_state.py        external_id + platform columns
memory/consolidation.py       post-consolidation push hook
memory/reflection_loop.py     call proactive_dispatcher
config.yaml                   hermes section
```

---

## Success Criteria

- All phases 0-8 pass acceptance tests.
- ≥80% coverage on new modules.
- p95 reply latency ≤ 4s text / ≤ 8s voice.
- Zero crashes in 48-hour soak.
- Mention-gate precision ≥ 0.9 on 100-message group sample.
- `openspec validate --strict` green.
- Cardinal rules R1–R6 clean.
