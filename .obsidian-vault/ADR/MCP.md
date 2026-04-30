---
source: brief
introduced-in: first-run
last-updated: first-run
component: MCP Layer
---

# MCP (Model Context Protocol)

## Why Chosen
MCP makes STARK's capabilities accessible to any MCP-compatible client (Claude Code, IDE plugins, etc.) and allows STARK to consume external MCP servers (filesystem, git, databases). Bidirectional MCP enables STARK as both tool provider and tool consumer.

## How It Fits
mcp/server.py exposes STARK tools (stark_query, stark_code_generate, stark_file_read, stark_web_scrape, stark_memory_recall). mcp/client.py connects to external MCP servers. mcp/agent.py orchestrates multi-server workflows.

## Problem Solved
Need for STARK to integrate with the growing MCP ecosystem — both exposing its unique capabilities (memory, learning) and consuming external tools — without building custom integrations for every client.
