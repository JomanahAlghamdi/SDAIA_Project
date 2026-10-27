# Architecture

```mermaid
flowchart TD
    U["Student: CLI and human approval"] --> H["Harness: session, rules and budgets"]
    H --> L["OpenRouter: selected free model"]
    L --> H
    H --> M["Read-only MCP subprocess"]
    M --> C["Synthetic opportunity catalog"]
    H --> E["Eligibility checks in Python"]
    H --> A["Exact-preview approval gate"]
    U --> A
    A --> D["Local SQLite drafts"]
    H --> T["Audit and evaluation evidence"]
```

One agent selects tools. The host binds identity, enforces four schemas and owns all writes. Search and detail retrieval cross a real SDK stdio MCP boundary. The catalog subprocess cannot approve or save a draft. Academic profile fields are editable only through direct CLI commands; model tools have no profile/identity mutation capability.

Each request can complete, ask for missing information, stop on a budget, fail on a provider error, or return a permission/eligibility denial. No graph or multi-agent coordinator is needed for this bounded task. SQLite stores drafts, not the conversation; session memory is in-process.
