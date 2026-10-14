# 🤖 CodeAuditAI — AI Context File

> **Purpose**: This file provides comprehensive architectural, operational, and design context for any AI model working on or extending this repository. Read this file first before making changes or resuming work.

---

## 1. Project Identity & Core Mission

- **Project Name**: CodeAuditAI
- **Type**: Autonomous Multi-Agent Code Security & Performance Review Studio
- **Language / Runtime**: Python 3.10 – 3.14+
- **Primary Frameworks**: FastAPI, LangGraph, ChromaDB, SQLite, Rich CLI, Tailwind CSS (CDN), Prism.js
- **Repository Location**: `/home/suraj/Lab/Projects/01CodeAuditAI/`
- **GitHub Remote**: `https://github.com/Suraj-8300/ai-code-auditor.git` (branch: `main`)
- **Package Spec**: `pyproject.toml` with console script entry point `codeaudit = "app.cli:main"`

---

## 2. Product Architecture & Dual-Mode Delivery

CodeAuditAI provides a dual-surface experience for developers:

```
                               ┌────────────────────────────────────────────────────────┐
                               │       CodeAuditAI Unified Gateway (`codeaudit`)        │
                               └───────────────────────────┬────────────────────────────┘
                                                           │
                      ┌────────────────────────────────────┴────────────────────────────────────┐
                      ▼                                                                         ▼
     ┌──────────────────────────────────┐                                      ┌──────────────────────────────────┐
     │     Interactive Web Studio       │                                      │     Enterprise Terminal CLI      │
     │      (FastAPI + Web UI)          │                                      │          (`codeaudit`)           │
     ├──────────────────────────────────┤                                      ├──────────────────────────────────┤
     │ • Google Material 3 Light Theme  │                                      │ • Headless CI/CD test automation │
     │ • Dark Theme Toggle              │                                      │ • ANSI colorized tables (Rich)   │
     │ • High-Converting Landing Page   │                                      │ • 1-click GitHub URL cloning     │
     │ • Interactive Live Audit Demo    │                                      │ • Direct stdin/string snippets   │
     │ • Multi-Project Switcher         │                                      │ • Native SARIF v2.1.0 output     │
     │ • Polyglot Snippet Sandbox       │                                      │ • Markdown scorecard generation  │
     │ • CLI Docs Portal with Sidebar   │                                      │ • SQLite project cache manager   │
     └──────────────────────────────────┘                                      └──────────────────────────────────┘
```

### Web Routes:
- `GET /` or `GET /studio`: The interactive Web Review Studio (defaults to Landing Page until a project is loaded or user switches view).
- `GET /landing`: Explicit landing page view.
- `GET /cli` or `GET /docs`: Dedicated developer CLI documentation portal with sticky sidebar navigation.
- `GET /api/health`: Health status of the LLM provider, vector DB, and cache engine.
- `GET /supported-languages`: Returns the 26+ polyglot language definitions, extensions, and checklists.
- `GET /api/projects`: Lists indexed projects with file counts, audited counts, and paths.
- `DELETE /api/projects`: Deletes a project from the SQLite registry.
- `GET /api/byok/config`: Returns BYOK connection status, active model, and masked keys.
- `POST /api/byok/config`: Sets provider, API key, model, or custom OpenAI-compatible endpoint.
- `POST /api/byok/test`: Tests the active provider connection with a live ping.

---

## 3. LangGraph Multi-Agent Consensus Pipeline

Audits run through an autonomous multi-agent pipeline:

```
[Target Code File]
       │
       ▼
[Language Detector + Vector DB Context]
       │
       ├─────────────────────────────────────────┐
       ▼                                         ▼
[Security Auditor Node]               [Performance Critic Node]
 • OWASP Top 10 & CWE classification   • Big-O algorithmic time/space complexity
 • Memory safety, injection, crypto    • CPU/RAM leaks, I/O blocking, N+1 queries
 • Language-specific exploit checks    • Optimized code remediation
       │                                         │
       └────────────────────┬────────────────────┘
                            │
                            ▼
                [Joint Reconciler Node]
                 • Resolves inter-agent conflicts
                 • Ensures patches don't trade speed for safety
                 • Produces unified verdict: CRITICAL | WARNING | SAFE
                            │
       ┌────────────────────┼────────────────────┐
       ▼                    ▼                    ▼
[SARIF v2.1.0]       [Markdown Scorecard]  [SQLite & Vector Cache]
```

### Critical Implementation Details:
- **Language-Aware Prompts** (`app/agents/reviewer.py`): Ingests language-specific hints from `app/services/language_detector.py` into both Security and Performance nodes.
- **SARIF AST Parser** (`app/services/sarif_exporter.py`): Extracts CWE IDs and line numbers using 19 heuristic regex patterns rather than generic `CWE-General` fallbacks.
- **Path Normalization** (`app/cli.py` & `app/services/repo_mapper.py`): All repo paths are stored and queried as `os.path.abspath` to eliminate SQLite query mismatches between CLI and Web UI.

---

## 4. LLM BYOK Engine & Quota Architecture

### Free Tier Default Model:
- **Primary Model**: `gemini-3.5-flash-lite` (Google AI Studio)
  - **Quota**: **500 Requests Per Day (RPD)**, **15 Requests Per Minute (RPM)**.
  - **Important**: Do **NOT** set `gemini-2.5-flash` as primary default because Google AI Studio caps it at only **20 Requests Per Day**.
- **Automatic Fallback Chain**:
  `gemini-3.5-flash-lite` ➔ `gemini-flash-lite-latest` ➔ `gemini-3-flash-preview` ➔ `gemini-2.5-flash`.
- **429 Quota Exhaustion Protection** (`app/services/llm_client.py`):
  When daily quotas expire, Google returns `retry in X seconds` (e.g. 33,747s until midnight reset). The client strictly enforces `if wait_sec > 15: break` and sets `max_retries=0` in `ChatGoogleGenerativeAI`. This prevents the server from sleeping for 9 hours.

### Supported BYOK Providers:
1. **Google AI Studio** (Default, 100% Free Tier, no credit card required).
2. **Anthropic Claude** (`claude-3-7-sonnet-latest`, `claude-3-5-sonnet-latest`, `claude-3-5-haiku-latest`).
3. **OpenAI / Codex** (`gpt-4o`, `gpt-4o-mini`, `o3-mini`, `o1`).
4. **DeepSeek** (`deepseek-coder`, `deepseek-chat`, `deepseek-reasoner`).
5. **GitHub Copilot / Custom Proxies** (Azure OpenAI, Ollama, vLLM, custom OpenAI-compatible endpoints).

---

## 5. Repository File Layout

```
01CodeAuditAI/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI gateway, UI routing, & REST endpoints
│   ├── cli.py                           # Enterprise terminal CLI (codeaudit)
│   ├── static/
│   │   └── index.html                   # Google Material 3 single-page Studio & Docs
│   ├── agents/
│   │   └── reviewer.py                  # LangGraph multi-agent consensus pipeline
│   └── services/
│       ├── language_detector.py         # 26+ Polyglot rules, CWE mappings, & checklists
│       ├── llm_client.py                # Multi-provider BYOK client & fallback engine
│       ├── sarif_exporter.py            # OASIS SARIF v2.1.0 generator
│       ├── report_generator.py          # Executive Markdown scorecard generator
│       ├── vector_db.py                 # ChromaDB semantic chunking & embeddings
│       ├── sqlite_db.py                 # SQLite metadata, audit caching, & repo index
│       ├── repo_mapper.py               # Repository scanner, AST parser, & classifier
│       └── scanner.py                   # Async filesystem walker
├── examples/
│   └── demo-app/
│       ├── app.py                       # Self-contained demo project (SQLi, hardcoded key, O(n^2))
│       └── README.md                    # Demo instructions
├── codeaudit                            # Executable launcher (portable shebang)
├── install.sh                           # 1-line curl setup installer
├── requirements.txt                     # Production dependencies
├── pyproject.toml                       # Package setup and entry points
├── progresslog.md                       # Comprehensive engineering progress log
├── context.md                           # This AI model handoff & architecture guide
└── README.md                            # Platinum-grade project documentation
```

---

## 6. Guidelines for Future AI Instances

When making changes to this codebase:
1. **Preserve Google Light Aesthetic as Default**: The UI uses clean Google Product Sans typography, subtle elevation borders (`border-slate-200/80` and `google-shadow-1`), and light backgrounds (`#ffffff`, `#f8fafd`, `#f1f3f4`). Always support dark mode via `dark:` Tailwind classes.
2. **Never Hardcode Long Retries**: Keep LLM retry caps at $\le 15$ seconds to avoid blocking server worker threads.
3. **Ensure Path Normalization**: Whenever saving or querying files or repositories in SQLite, always run `os.path.abspath(...)`.
4. **Maintain Polyglot Support**: When adding new language features, update both `app/services/language_detector.py` and `app/services/vector_db.py`.
5. **Verify SARIF Compliance**: Any modifications to audit output schemas must maintain OASIS SARIF v2.1.0 validity so GitHub Security integration does not break.
