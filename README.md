# 🛡️ CodeAuditAI

<p align="center">
  <img src="https://img.shields.io/badge/CodeAuditAI-v1.2.0-2563eb?style=for-the-badge&logo=shield&logoColor=white" alt="CodeAuditAI Version" />
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/SARIF-v2.1.0%20Compliant-10b981?style=for-the-badge&logo=githubactions&logoColor=white" alt="SARIF v2.1.0" />
  <img src="https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge" alt="License MIT" />
  <img src="https://img.shields.io/badge/Free%20Tier-Google%20AI%20Studio-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Free Tier Ready" />
</p>

<h3 align="center">
  Autonomous Multi-Agent Code Security & Performance Review Studio
</h3>

<p align="center">
  <b>A polyglot AI auditing engine powered by LangGraph tri-agent consensus, ChromaDB vector semantic search, SQLite metadata caching, a Google Material 3 Web Studio, and an enterprise CLI.</b>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-dual-mode-experience">Dual Mode</a> •
  <a href="#-tri-agent-consensus-engine">Agent Pipeline</a> •
  <a href="#-free-tier--byok-provider-matrix">BYOK Matrix</a> •
  <a href="#-polyglot-language-matrix">Languages</a> •
  <a href="#-cli-reference">CLI Reference</a> •
  <a href="#-cicd-github-actions">CI/CD</a> •
  <a href="#-api-endpoints">REST API</a>
</p>

---

## 💡 Why CodeAuditAI?

Engineering teams face a fundamental dilemma when reviewing modern codebases:

| Tooling Class | How It Works | Fatal Flaw |
| :--- | :--- | :--- |
| **Traditional Static Linters**<br>*(SonarQube, ESLint, Cppcheck)* | Rigid regex matching & AST grammar rules | **Zero semantic awareness.** Floods developers with false-positive noise, cannot understand business logic, and never provides synthesized patches. |
| **Generic LLM Chatbots**<br>*(ChatGPT, Claude Web)* | Isolated chat box prompts | **No architectural memory.** Reviews files in total vacuum without knowledge of surrounding modules, imports, or cross-file dependencies. |
| **🛡️ CodeAuditAI** | **Whole-repo vector embedding + LangGraph Tri-Agent consensus** | **Full semantic grounding.** Evaluates holistic blast radius, identifies root-cause exploits, calculates Big-O algorithmic complexity, and exports **SARIF v2.1.0** for GitHub Advanced Security. |

---

## ⚡ Quick Start

### 1. One-Line Automatic Installer (Linux & macOS)

Install CodeAuditAI, create an isolated virtual environment, and symlink the `codeaudit` binary to your path in a single command:

```bash
curl -sSL https://raw.githubusercontent.com/Suraj-8300/CodeAuditAI/main/install.sh | bash
```

### 2. Manual Git Clone

```bash
git clone https://github.com/Suraj-8300/CodeAuditAI.git
cd CodeAuditAI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 3. Add Free Google AI Studio Key (0 Credit Card Required)

Get an instant free key from [Google AI Studio](https://aistudio.google.com/):

```bash
export GOOGLE_API_KEY="AIzaSy..."
```

> **Quota Note**: CodeAuditAI is optimized for Google's generous **`gemini-3.5-flash-lite`** free tier, delivering **500 Requests Per Day (RPD)** and **15 Requests Per Minute (RPM)** with automatic failover across fallback models.

### 4. Launch the Web Studio or Terminal CLI

```bash
# Option A: Launch Google Material 3 Web Studio
codeaudit web

# Option B: Audit any GitHub repository directly in your terminal
codeaudit audit https://github.com/owner/repository --export-sarif findings.sarif

# Option C: Audit a local codebase and output an executive Markdown report
codeaudit audit ./examples/demo-app --all --export-md audit_report.md
```

---

## 🖥️ Dual-Mode Experience

CodeAuditAI is engineered for both visual code reviewers and automated CI/CD terminal pipelines:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   CodeAuditAI Unified Gateway (`codeaudit`)            │
├───────────────────────────────────┬────────────────────────────────────┤
│   Mode 1: Web Review Studio       │   Mode 2: Enterprise Terminal CLI  │
│   • Google Material 3 Light/Dark  │   • Headless CI/CD test automation │
│   • 1-Click GitHub Repo Ingestion │   • ANSI colorized vulnerability   │
│   • Multi-Project Switcher        │   • Direct stdin & string snippets │
│   • Interactive Snippet Sandbox   │   • Native SARIF v2.1.0 exporter   │
│   • Live Remediations & Patches   │   • SQLite project management      │
└───────────────────────────────────┴────────────────────────────────────┘
```

### Mode 1: Interactive Web Review Studio (`codeaudit web`)
- **Google Material 3 Light Aesthetic**: Clean white cards, refined elevation (`0 1px 3px rgba(0,0,0,0.08)`), Google Product Sans typography, and subtle Google Blue (`#1a73e8`), Emerald (`#0d652d`), Amber (`#e37400`), and Coral (`#d93025`) accents.
- **Dark Theme Toggle**: Instant toggle to Google Dark surface palette (`#131314` and `#1e1f20`).
- **Product Landing Page**: High-converting hero showcase, live interactive audit simulation, feature highlights, and direct navigation.
- **Dedicated CLI Documentation Portal**: Sticky sidebar navigation with complete flag references, copy-to-clipboard curl commands, and GitHub Actions configs.
- **Multi-Project Workspace**: Switch between multiple cloned repositories, view file importance tiers (`High`, `Medium`, `Low`), and inspect cached findings without re-running audits.
- **Snippet Sandbox**: Instant multi-language scratchpad to paste code in C, C++, Java, Python, Go, Rust, TypeScript, or PHP and inspect instant audit verdicts.

### Mode 2: Enterprise Desktop CLI (`codeaudit`)
- **ANSI Terminal Tables**: Renders clean, colorized tables with Rich styling.
- **Automated Cloner**: Clones remote GitHub URLs directly into sandboxed directories.
- **SARIF v2.1.0 Exporter**: Directly outputs standard OASIS SARIF files for GitHub Code Scanning and VS Code SARIF Viewer.

---

## 🏛️ Tri-Agent Consensus Engine

Audits are executed through an autonomous multi-agent pipeline orchestrated by **LangGraph**:

```
                       ┌────────────────────────────┐
                       │   Target Source Code File  │
                       └─────────────┬──────────────┘
                                     │
                   ┌─────────────────┴─────────────────┐
                   │ Language & Dependency Recognition │
                   └─────────────────┬─────────────────┘
                                     │
                 ┌───────────────────┴───────────────────┐
                 │                                       │
     ┌───────────▼───────────┐               ┌───────────▼───────────┐
     │ 🛡️ Security Auditor   │               │ ⚡ Performance Critic  │
     ├───────────────────────┤               ├───────────────────────┤
     │ • OWASP Top 10 / CWE  │               │ • Big-O Complexity    │
     │ • Injection & Overflow│               │ • I/O Leaks & CPU Ops │
     │ • Deserialization     │               │ • Allocations & Cache │
     └───────────┬───────────┘               └───────────┬───────────┘
                 │                                       │
                 └───────────────────┬───────────────────┘
                                     │
                         ┌───────────▼───────────┐
                         │ 🤝 Joint Reconciler   │
                         ├───────────────────────┤
                         │ • Cross-Agent Defense │
                         │ • Zero Trade-Offs     │
                         │ • Unified Patch Synt. │
                         └───────────┬───────────┘
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       │                             │                             │
┌──────▼──────┐               ┌──────▼──────┐               ┌──────▼──────┐
│ SARIF v2.1  │               │ Markdown    │               │ SQLite &    │
│ Artifacts   │               │ Scorecards  │               │ Vector Cache│
└─────────────┘               └─────────────┘               └─────────────┘
```

1. **Language Detector**: Identifies 26+ programming languages, loads specialized audit vectors (e.g., buffer overflows in C, prototype pollution in JS, unsafe deserialization in Java), and retrieves surrounding code chunks from ChromaDB.
2. **Security Auditor Node**: Identifies exploit vectors, binds findings to official **CWE IDs** and **OWASP categories**, evaluates blast radius, and drafts remediation patches.
3. **Performance Critic Node**: Analyzes algorithmic time and space complexity, flags CPU bottlenecks, memory leaks, and N+1 query patterns.
4. **Joint Reconciler Node**: Combines security and performance verdicts to ensure proposed security patches do not introduce performance regressions, producing a final unified verdict (`CRITICAL`, `WARNING`, or `SAFE`).

---

## 🔑 Free Tier & BYOK Provider Matrix

CodeAuditAI supports **Bring Your Own Key (BYOK)** across major AI providers. Configure keys via environment variables or directly in the Web Studio settings modal.

| Provider | Supported Models | Pricing / Free Tier | Recommended Use |
| :--- | :--- | :--- | :--- |
| **Google AI Studio** *(Default)* | `gemini-3.5-flash-lite`<br>`gemini-flash-lite-latest`<br>`gemini-3-flash-preview`<br>`gemini-2.5-flash` | **100% Free**<br>(500 RPD, 15 RPM on `gemini-3.5-flash-lite`) | **Default & Recommended**: Zero cost, high speed, deep context window. |
| **Anthropic Claude** | `claude-3-7-sonnet-latest`<br>`claude-3-5-sonnet-latest`<br>`claude-3-5-haiku-latest` | BYOK Paid API Key | Maximum reasoning precision for mission-critical banking/crypto code. |
| **OpenAI / Codex** | `gpt-4o`<br>`gpt-4o-mini`<br>`o3-mini`<br>`o1` | BYOK Paid API Key | Standard enterprise compliance & reasoning. |
| **DeepSeek** | `deepseek-coder`<br>`deepseek-chat`<br>`deepseek-reasoner` | BYOK Paid API Key | Highly cost-efficient coding-specific audits. |
| **GitHub Copilot / Custom** | Azure OpenAI, Copilot Proxies, vLLM, Ollama | Local / Self-Hosted | Air-gapped on-premise execution with zero data egress. |

### Quota & Rate Limit Protection
CodeAuditAI features built-in **Smart Fallback** for Google AI Studio:
- If a daily quota limit is reached (HTTP 429), the engine automatically falls back to secondary free models (`gemini-flash-lite-latest` ➔ `gemini-3-flash-preview`) without hanging.
- Safe retry caps prevent thread freezes when upstream APIs suggest hours-long delays.

---

## 🌍 Polyglot Language Matrix

CodeAuditAI provides syntax-aware chunking and tailored vulnerability checklists for over **26 programming languages**:

| Language | Extensions | Specialized Security & Performance Checklist |
| :--- | :--- | :--- |
| **Python** | `.py` | SQL injection, `os.system` / `subprocess` shell injection, `pickle` deserialization, `eval`/`exec`, SSTI, GIL bottlenecks, N+1 ORM queries. |
| **JavaScript** | `.js`, `.jsx`, `.mjs`, `.cjs` | DOM XSS (`innerHTML`), prototype pollution, `eval()`, ReDoS regular expressions, dangling event listeners. |
| **TypeScript** | `.ts`, `.tsx` | All JavaScript checks + unsafe `any` casts, missing null/undefined boundary validation. |
| **C** | `.c` | Buffer overflows (`strcpy`, `sprintf`, `gets`), format string vulnerabilities, integer overflows, use-after-free, double-free. |
| **C++** | `.cpp`, `.cc`, `.cxx`, `.h`, `.hpp` | Dangling pointers, RAII violations, copy vs move semantics, virtual dispatch overhead, cache locality. |
| **Java** | `.java` | Insecure deserialization (`ObjectInputStream`), XXE, LDAP injection, SQL injection, `StringBuilder` loop efficiency, JPA N+1 queries. |
| **Go** | `.go` | Goroutine leaks, `exec.Command` injection, SSRF, TLS misconfigurations, `sync.Mutex` deadlocks. |
| **Rust** | `.rs` | Misused `unsafe` blocks, integer overflow in release mode, production `unwrap()` panics, excessive `Arc`/`Rc` cloning. |
| **PHP** | `.php` | SQL injection, `shell_exec`, LFI/RFI (`include`/`require`), unescaped output XSS, `unserialize()`. |
| **HTML** | `.html`, `.htm` | Inline event handlers, missing CSP meta headers, insecure form actions, missing iframe `sandbox`. |
| **CSS** | `.css`, `.scss`, `.sass`, `.less` | CSS expression injection, clickjacking via `z-index`, `@import` from untrusted origins, expensive layout repaints. |
| **C# / .NET** | `.cs` | SQL injection, insecure binary serialization, XXE, hardcoded Azure/AWS connection strings. |
| **Ruby** | `.rb` | SQL injection, command injection, `eval`, mass assignment vulnerabilities, SSRF. |
| **Swift** | `.swift` | Force unwrap crashes, SQL injection, hardcoded cryptographic keys, insecure Keychain storage. |
| **Kotlin** | `.kt`, `.kts` | Null pointer exceptions, coroutine resource exhaustion, insecure deserialization. |
| **Shell** | `.sh`, `.bash` | Unquoted variables (`$VAR`), command injection, path traversal, hardcoded tokens. |
| **Configs & Data** | `.json`, `.yaml`, `.xml`, `.sql`, `.toml` | Hardcoded API keys, XXE injection, overly permissive CI/CD permissions, privilege escalation. |

---

## 💻 CLI Reference

The `codeaudit` command provides a complete command-line interface for local use and CI/CD:

```
usage: codeaudit [-h] {web,audit,snippet,languages,projects} ...
```

### Commands & Flags

#### 1. `codeaudit web`
Launch the Google Material 3 Web Review Studio.
```bash
codeaudit web [--port 8000] [--reload]
```

#### 2. `codeaudit audit`
Audit a local directory or remote GitHub repository.
```bash
# Basic audit on High-importance files
codeaudit audit https://github.com/owner/repo

# Audit all source files and export SARIF and Markdown
codeaudit audit ./my-project --all --export-sarif findings.sarif --export-md report.md

# Audit with a specific LLM provider
codeaudit audit ./my-project --provider claude --model claude-3-5-sonnet-latest
```

| Flag | Type | Description |
| :--- | :--- | :--- |
| `target` | `str` | GitHub URL (`https://...`) or local directory path. |
| `--all` | `flag` | Audit all detected source files instead of High-importance only. |
| `--export-sarif` | `path` | Output findings to an OASIS SARIF v2.1.0 file. |
| `--export-md` | `path` | Output findings to an executive Markdown scorecard. |
| `--provider` | `str` | Override LLM provider (`google`, `claude`, `openai`, `deepseek`, `copilot`). |
| `--model` | `str` | Override specific model name. |

#### 3. `codeaudit snippet`
Audit raw code from a string or file argument.
```bash
# Audit a Python snippet
codeaudit snippet --lang python "import sqlite3; query = f'SELECT * FROM users WHERE id={user_id}'; db.execute(query)"

# Audit a C snippet
codeaudit snippet --lang c "char buf[16]; strcpy(buf, input);"
```

#### 4. `codeaudit languages`
Display the full polyglot matrix of supported languages, file extensions, and audit checklists directly in your terminal.
```bash
codeaudit languages
```

#### 5. `codeaudit projects`
View, inspect, or remove previously audited repositories from the SQLite cache.
```bash
# List all indexed projects
codeaudit projects

# Delete a project from cache
codeaudit projects --delete /path/to/project
```

---

## 🤖 CI/CD GitHub Actions

Automatically audit pull requests and upload findings directly into GitHub Advanced Security tab using the native SARIF export:

Create `.github/workflows/codeaudit.yml`:

```yaml
name: "CodeAuditAI Security & Performance Gate"

on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]

jobs:
  audit:
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      contents: read

    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install CodeAuditAI
        run: |
          pip install --upgrade pip
          pip install git+https://github.com/Suraj-8300/CodeAuditAI.git

      - name: Run Multi-Agent Audit
        env:
          GOOGLE_API_KEY: ${{ secrets.GOOGLE_API_KEY }}
        run: |
          codeaudit audit . --all --export-sarif codeaudit.sarif --export-md AUDIT_REPORT.md

      - name: Upload SARIF to GitHub Security Tab
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: codeaudit.sarif

      - name: Archive Markdown Report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: codeaudit-report
          path: AUDIT_REPORT.md
```

---

## 🌐 API Endpoints

The FastAPI server provides a RESTful API:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` or `/studio` | Interactive Google-styled Web Review Studio |
| `GET` | `/cli` or `/docs` | Dedicated Developer CLI Documentation Portal |
| `GET` | `/api/health` | System status, provider status, and model health check |
| `GET` | `/supported-languages` | Returns all 26 supported languages, extensions, and checklists |
| `POST` | `/analyze-github` | Clones a GitHub repo, indexes chunks, and audits files |
| `POST` | `/analyze-repo` | Maps a local directory, stores file hashes, and runs audits |
| `POST` | `/analyze-snippet` | Audits raw code string without requiring file system storage |
| `POST` | `/analyze` | Audits a single local file path with the multi-agent pipeline |
| `GET` | `/search-codebase` | Semantic vector search across indexed codebase chunks |
| `GET` | `/list-files` | Returns indexed files with language and importance ratings |
| `GET` | `/get-audit` | Retrieves cached audit verdicts and remediations |
| `DELETE` | `/clear-cache` | Clears audit cache for a specific file or all files (`*`) |
| `GET` | `/export/sarif` | Exports audited findings in OASIS SARIF v2.1.0 JSON |
| `GET` | `/export/markdown` | Exports executive Markdown report |
| `GET` | `/api/projects` | Lists all indexed projects with file & audit counts |
| `DELETE` | `/api/projects` | Deletes a project from the SQLite database |
| `GET` | `/api/byok/config` | Retrieves provider connection statuses and active models |
| `POST` | `/api/byok/config` | Updates API key, model selection, or custom proxy endpoint |
| `POST` | `/api/byok/test` | Verifies LLM provider credentials with a test ping |

---

## 📂 Project Structure

```
CodeAuditAI/
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI application & Web Studio routes
│   ├── cli.py                           # Enterprise terminal CLI (codeaudit)
│   ├── static/
│   │   └── index.html                   # Google Material 3 Web Studio & Docs Portal
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
│       ├── app.py                       # Zero-friction test project (SQLi, secret, O(n^2))
│       └── README.md                    # Sample test guide
├── codeaudit                            # Executable launcher script
├── install.sh                           # 1-line curl setup installer
├── requirements.txt                     # Production dependencies
├── pyproject.toml                       # Package setup and entry points
├── progresslog.md                       # Comprehensive engineering progress log
├── context.md                           # AI model handoff & architecture guide
└── README.md                            # Project documentation
```

---

## 🧪 Testing with the Built-in Demo App

A pre-packaged demo project is included in `examples/demo-app/` featuring three intentional vulnerabilities:
1. **SQL Injection (`CWE-89`)**: Dynamic f-string string interpolation in query execution.
2. **Hardcoded Credential (`CWE-798`)**: Insecure production secret embedded in source code.
3. **Algorithmic Bottleneck**: $O(n \cdot m \cdot k)$ triple nested loop replaceable with $O(n + m)$ `set` intersection.

Audit it immediately:

```bash
codeaudit audit ./examples/demo-app --all --export-md demo_audit.md --export-sarif demo_findings.sarif
```

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for details.

Developed with ❤️ for developers who take code security and performance seriously.
