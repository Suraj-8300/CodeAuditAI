"""
cli.py
------
Command-Line Interface (CLI) for CodeAuditAI.
Provides terminal workflows for auditing GitHub repositories, local folders,
and standalone polyglot snippets, as well as launching the Web Review Studio.
"""

import sys
import os
import argparse
import asyncio
import webbrowser
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from app.services.sqlite_db import SQLiteStorageService
from app.services.vector_db import VectorStorageService
from app.services.repo_mapper import RepositoryMapperService
from app.services.language_detector import detect_language, get_language_audit_hints
from app.services.sarif_exporter import generate_sarif_report, sarif_to_json_string
from app.services.report_generator import generate_markdown_report
from app.agents.reviewer import audit_agent_app


console = Console() if HAS_RICH else None


def _print(msg: str, style: str = ""):
    if HAS_RICH and console:
        console.print(msg, style=style)
    else:
        print(msg)


def _print_panel(title: str, content: str, border_style: str = "green"):
    if HAS_RICH and console:
        console.print(Panel(content, title=title, border_style=border_style))
    else:
        print(f"\n=== {title} ===\n{content}\n" + "=" * (len(title) + 8))


def cmd_web(args):
    """Launches the CodeAuditAI Web Review Studio."""
    import uvicorn
    host = args.host
    port = args.port

    url = f"http://{host}:{port}"
    _print(f"\n🚀 [bold green]Starting CodeAuditAI Web Review Studio...[/bold green]")
    _print(f"📡 Studio URL: [bold cyan]{url}[/bold cyan]\n")

    if not args.no_browser:
        def open_browser():
            import time
            time.sleep(1.2)
            webbrowser.open(url)
        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("app.main:app", host=host, port=port, reload=args.reload)


def cmd_docs(args):
    """Launches the dedicated CodeAuditAI Documentation Portal."""
    import uvicorn
    host = args.host
    port = args.port

    url = f"http://{host}:{port}/docs"
    _print(f"\n📖 [bold green]Starting CodeAuditAI Documentation Portal...[/bold green]")
    _print(f"📡 Docs URL: [bold cyan]{url}[/bold cyan]\n")

    if not args.no_browser:
        def open_browser():
            import time
            time.sleep(1.2)
            webbrowser.open(url)
        import threading
        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("app.main:app", host=host, port=port, reload=False)


async def _run_audit_pipeline(target: str, high_only: bool = True, output_md: Optional[str] = None, output_sarif: Optional[str] = None):
    sqlite_service = SQLiteStorageService()
    vector_service = VectorStorageService()
    repo_mapper = RepositoryMapperService(sqlite_service, vector_service)

    is_github = target.startswith("http://") or target.startswith("https://")
    local_repo_path = os.path.abspath(target) if not is_github else target

    if is_github:
        _print(f"📥 [bold cyan]Cloning remote GitHub repository:[/bold cyan] {target}")
        cloned_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloned_repos")
        os.makedirs(cloned_dir, exist_ok=True)
        repo_slug = target.rstrip("/").split("/")[-1].replace(".git", "")
        local_repo_path = os.path.join(cloned_dir, repo_slug)

        import subprocess
        if not os.path.exists(local_repo_path):
            res = subprocess.run(["git", "clone", "--depth=1", target, local_repo_path], capture_output=True, text=True)
            if res.returncode != 0:
                _print(f"[bold red]Git clone failed:[/bold red] {res.stderr}")
                return
        else:
            _print(f"♻️ Existing clone found at {local_repo_path}. Pulling latest...")
            subprocess.run(["git", "-C", local_repo_path, "pull"], capture_output=True, text=True)

    _print(f"🧠 [bold cyan]Mapping and indexing codebase:[/bold cyan] {local_repo_path}")
    repo_data = await repo_mapper.map_repository(local_repo_path)
    repo_files = sqlite_service.get_repo_files(local_repo_path)

    _print(f"✅ Found [bold green]{len(repo_files)}[/bold green] source files in repository: [bold]{repo_data['name']}[/bold]")

    # Select target files
    target_files = [f for f in repo_files if f["importance"] == "High"] if high_only else repo_files
    if not target_files:
        target_files = repo_files[:5]  # Fallback to first 5 if no high importance files

    _print(f"⚡ [bold yellow]Auditing {len(target_files)} target file(s) via LangGraph Multi-Agent Consensus...[/bold yellow]\n")

    audited_results = []
    for file_entry in target_files:
        file_path = file_entry["file_path"]
        rel_path = os.path.relpath(file_path, local_repo_path)

        # Check cache
        cached_audit = sqlite_service.get_audit(file_path)
        if cached_audit:
            _print(f"🛡️  [green]Cache Hit:[/green] {rel_path}")
            sec_rep = cached_audit["security_report"]
            perf_rep = cached_audit["performance_report"]
        else:
            _print(f"🔍 [bold]Auditing:[/bold] {rel_path} ({file_entry.get('language', 'Code')})...")
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    source_code = f.read()

                db_hints = vector_service.semantic_search(query=f"vulnerabilities in {os.path.basename(file_path)}", limit=3)
                context_strings = [hit["content"] for hit in db_hints]

                initial_state = {
                    "file_path": file_path,
                    "source_code": source_code,
                    "repo_path": local_repo_path,
                    "repo_map": repo_data["repo_map_string"],
                    "retrieved_context": context_strings,
                    "security_draft": "",
                    "performance_draft": "",
                    "security_report": "",
                    "performance_report": ""
                }
                final_state = await audit_agent_app.ainvoke(initial_state)
                sec_rep = final_state.get("security_report", "Analysis failed.")
                perf_rep = final_state.get("performance_report", "Analysis failed.")
                sqlite_service.upsert_audit(file_path, sec_rep, perf_rep)
            except Exception as e:
                _print(f"[red]Error auditing {rel_path}: {e}[/red]")
                continue

        audited_results.append({
            "file_path": rel_path,
            "summary": file_entry.get("summary", ""),
            "security_report": sec_rep,
            "performance_report": perf_rep
        })

    # Display Terminal Summary Table
    if HAS_RICH and console:
        table = Table(title=f"CodeAuditAI Audit Scorecard — {repo_data['name']}")
        table.add_column("File Path", style="cyan", no_wrap=True)
        table.add_column("Language", style="magenta")
        table.add_column("Rating", style="bold")
        table.add_column("Key Remediation Highlight", style="green")

        for item in audited_results:
            sec = item["security_report"]
            rating = "[bold green]SAFE[/bold green]"
            if "[CRITICAL]" in sec:
                rating = "[bold red]CRITICAL[/bold red]"
            elif "[WARNING]" in sec:
                rating = "[bold yellow]WARNING[/bold yellow]"

            lang = detect_language(item["file_path"])
            table.add_row(item["file_path"], lang, rating, "Review complete. Patches available.")

        console.print(table)
        console.print()

    # Export Reports
    if output_md:
        md = generate_markdown_report(repo_data["name"], local_repo_path, audited_results, repo_data["summary"])
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(md)
        _print(f"📄 [bold green]Markdown report saved to:[/bold green] {output_md}")

    if output_sarif:
        sarif = generate_sarif_report(audited_results, repo_data["name"])
        with open(output_sarif, "w", encoding="utf-8") as f:
            f.write(sarif_to_json_string(sarif))
        _print(f"🛡️  [bold green]SARIF v2.1 export saved to:[/bold green] {output_sarif}")


def cmd_audit(args):
    """Runs repository audit from CLI."""
    asyncio.run(_run_audit_pipeline(
        target=args.target,
        high_only=not args.all,
        output_md=args.export_md,
        output_sarif=args.export_sarif
    ))


def cmd_languages(args):
    """Lists all supported languages."""
    from app.main import api_supported_languages
    data = api_supported_languages()

    if HAS_RICH and console:
        table = Table(title="CodeAuditAI Polyglot Support Matrix")
        table.add_column("Language", style="bold cyan")
        table.add_column("Extensions", style="green")
        table.add_column("Specialized Audit Focus", style="white")

        for lang, info in data.items():
            table.add_row(lang, ", ".join(info["extensions"]), info["audit_focus"])
        console.print(table)
    else:
        for lang, info in data.items():
            print(f"- {lang} ({', '.join(info['extensions'])}): {info['audit_focus']}")


def cmd_snippet(args):
    """Audits an inline code snippet or file."""
    code = args.code
    if not code and args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            code = f.read()

    if not code:
        _print("[bold red]Please provide code text or a --file path to inspect.[/bold red]")
        return

    lang = args.lang or "python"
    _print(f"🚀 [bold cyan]Auditing {lang.upper()} snippet via Multi-Agent Consensus...[/bold cyan]\n")

    import uuid
    import tempfile
    temp_dir = tempfile.gettempdir()
    from app.main import _LANG_SLUG_TO_EXT
    ext = _LANG_SLUG_TO_EXT.get(lang.lower(), ".txt")
    temp_file = os.path.join(temp_dir, f"snippet_{uuid.uuid4().hex[:8]}{ext}")

    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(code)

    async def _run_snippet():
        initial_state = {
            "file_path": temp_file,
            "source_code": code,
            "repo_path": temp_dir,
            "repo_map": "Standalone snippet audit",
            "retrieved_context": [],
            "security_draft": "",
            "performance_draft": "",
            "security_report": "",
            "performance_report": ""
        }
        res = await audit_agent_app.ainvoke(initial_state)
        return res

    result = asyncio.run(_run_snippet())

    if HAS_RICH and console:
        console.print(Panel(Markdown(result.get("security_report", "No security data.")), title="🛡️ Security Auditor Report", border_style="red"))
        console.print()
        console.print(Panel(Markdown(result.get("performance_report", "No performance data.")), title="⚡ Performance Critic Report", border_style="yellow"))
    else:
        print("\n--- SECURITY AUDIT ---\n" + result.get("security_report", ""))
        print("\n--- PERFORMANCE CRITIC ---\n" + result.get("performance_report", ""))

    if os.path.exists(temp_file):
        os.remove(temp_file)


def cmd_projects(args):
    """Lists or deletes indexed projects from SQLite cache."""
    db = SQLiteStorageService()
    if args.delete:
        db.delete_repository(args.delete)
        _print(f"🗑️ [bold green]Successfully removed project:[/bold green] {args.delete}")
        return

    projects = db.get_all_repositories()
    if not projects:
        _print("ℹ️ No indexed projects found. Ingest one with `codeaudit audit <path_or_url>` or launch `codeaudit web`.")
        return

    if HAS_RICH and console:
        table = Table(title="CodeAuditAI Indexed Projects", header_style="bold cyan")
        table.add_column("Project Name", style="bold white")
        table.add_column("Path", style="dim")
        table.add_column("Files", justify="right", style="green")
        table.add_column("Audited", justify="right", style="yellow")
        table.add_column("Summary", style="white")

        for p in projects:
            summary_txt = p.get("summary", "") or ""
            table.add_row(
                p.get("name", "Unknown"),
                p.get("path", ""),
                str(p.get("file_count", 0)),
                str(p.get("audited_count", 0)),
                summary_txt[:50] + "..." if len(summary_txt) > 50 else summary_txt
            )
        console.print(table)
    else:
        print("\n=== CodeAuditAI Indexed Projects ===")
        for p in projects:
            print(f"- {p.get('name')}: {p.get('file_count')} files ({p.get('audited_count')} audited) | Path: {p.get('path')}")


def main():
    parser = argparse.ArgumentParser(
        prog="codeaudit",
        description="CodeAuditAI — Autonomous Multi-Agent Code Security & Performance Review Studio"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # 1. web
    web_parser = subparsers.add_parser("web", help="Launch the interactive Web Review Studio")
    web_parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    web_parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    web_parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    web_parser.add_argument("--reload", action="store_true", help="Enable live auto-reloading")

    # 2. audit
    audit_parser = subparsers.add_parser("audit", help="Audit a GitHub repo URL or local path")
    audit_parser.add_argument("target", help="GitHub URL (https://github.com/...) or local directory path")
    audit_parser.add_argument("--all", action="store_true", help="Audit all files instead of high-risk files only")
    audit_parser.add_argument("--export-md", help="Path to export Markdown report (e.g. audit.md)")
    audit_parser.add_argument("--export-sarif", help="Path to export SARIF file (e.g. audit.sarif)")

    # 3. snippet
    snippet_parser = subparsers.add_parser("snippet", help="Audit a code snippet directly")
    snippet_parser.add_argument("code", nargs="?", default="", help="Code string to audit")
    snippet_parser.add_argument("--file", "-f", help="File path to read snippet from")
    snippet_parser.add_argument("--lang", "-l", default="python", help="Language slug (c, cpp, java, html, css, js, ts, python, go, rust, php)")

    # 4. languages
    subparsers.add_parser("languages", help="List all supported programming languages and audit focus")

    # 5. projects
    projects_parser = subparsers.add_parser("projects", help="List and manage indexed repositories/projects")
    projects_parser.add_argument("--delete", "-d", help="Delete a project and its cached audits by path")

    # 6. docs
    docs_parser = subparsers.add_parser("docs", help="Open the dedicated CLI & Architecture Documentation Portal")
    docs_parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    docs_parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    docs_parser.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")

    args = parser.parse_args()

    if args.command == "web":
        cmd_web(args)
    elif args.command == "docs":
        cmd_docs(args)
    elif args.command == "audit":
        cmd_audit(args)
    elif args.command == "snippet":
        cmd_snippet(args)
    elif args.command == "languages":
        cmd_languages(args)
    elif args.command == "projects":
        cmd_projects(args)
    else:
        parser.print_help()



if __name__ == "__main__":
    main()
