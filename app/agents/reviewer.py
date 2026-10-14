import os
import re
import json
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from app.services.llm_client import safe_invoke, get_message_text
from app.services.language_detector import detect_language, get_language_audit_hints, get_lang_fence

# Define our Shared Graph State Architecture
class AuditState(TypedDict):
    file_path: str               # The target file path
    source_code: str             # The code content being analyzed
    repo_path: str               # Root directory path of the repo
    repo_map: str                # Global repository structure and file roles
    retrieved_context: List[str] # Vector database clue hits
    security_draft: str          # Preliminary report from the security node
    performance_draft: str       # Preliminary report from the performance node
    security_report: str         # Final reconciled security report
    performance_report: str      # Final reconciled performance report


# Node #1: The Security Auditor Agent
async def security_auditor_node(state: AuditState) -> Dict[str, Any]:
    print(f"🛡️ [Agent] Security Auditor Node is analyzing: {state['file_path']}")
    code_to_review = state["source_code"]
    repo_context = state.get("repo_map", "No global repository context provided.")
    clues = "\n".join(state.get("retrieved_context", []))

    language = detect_language(state["file_path"])
    hints = get_language_audit_hints(language)
    lang_fence = get_lang_fence(language)

    prompt = (
        f"You are an elite application security engineer and code auditor specializing in **{language}**.\n"
        f"You are auditing the file: '{state['file_path']}' in the context of the following repository structure:\n"
        "--- Repository Map ---\n"
        f"{repo_context}\n"
        "----------------------\n\n"
        "Here are relevant database code clues from across the codebase:\n"
        "--- Code Database Clues ---\n"
        f"{clues}\n"
        "----------------------\n\n"
        f"Target Code to Audit ({language}):\n"
        f"```{lang_fence}\n{code_to_review}\n```\n\n"
        f"Language-specific security concerns to focus on for **{language}**:\n"
        f"{hints['security_hints']}\n\n"
        "Task: Audit the target code for security vulnerabilities, injection flaws, logical errors, "
        "credentials leaks, or OWASP/CWE violations — paying special attention to the language-specific "
        "concerns listed above.\n\n"
        "Respond with a detailed analysis containing:\n"
        "1. **Executive Summary**: High-level overview of findings.\n"
        "2. **Vulnerability Details**: A markdown table with these exact columns:\n"
        "   | CWE ID | OWASP Category | Severity | Line(s) | Description | Impact |\n"
        "   (Severity must be one of: CRITICAL, WARNING, or SAFE)\n"
        "3. **Remediation**: Complete, copy-pasteable corrected code blocks mitigating the security risks.\n"
        "4. **Overall Rating**: Explicitly assign a rating of either [SAFE], [WARNING], or [CRITICAL] at the end."
    )
    result = await safe_invoke(prompt)
    return {"security_draft": result}


# Node #2: The Performance Critic Agent
async def performance_critic_node(state: AuditState) -> Dict[str, Any]:
    print(f"⚡ [Agent] Performance Critic Node is analyzing: {state['file_path']}")
    code_to_review = state["source_code"]
    repo_context = state.get("repo_map", "No global repository context provided.")
    clues = "\n".join(state.get("retrieved_context", []))

    language = detect_language(state["file_path"])
    hints = get_language_audit_hints(language)
    lang_fence = get_lang_fence(language)

    prompt = (
        f"You are an elite principal systems and performance engineer specializing in **{language}**.\n"
        f"You are auditing the file: '{state['file_path']}' in the context of the following repository structure:\n"
        "--- Repository Map ---\n"
        f"{repo_context}\n"
        "----------------------\n\n"
        "Here are relevant database code clues from across the codebase:\n"
        "--- Code Database Clues ---\n"
        f"{clues}\n"
        "----------------------\n\n"
        f"Target Code to Audit ({language}):\n"
        f"```{lang_fence}\n{code_to_review}\n```\n\n"
        f"Language-specific performance concerns to focus on for **{language}**:\n"
        f"{hints['performance_hints']}\n\n"
        "Task: Audit the target code for computational bottlenecks, memory leaks, high time/space "
        "complexity (Big O), or I/O inefficiencies — paying special attention to the language-specific "
        "concerns listed above.\n\n"
        "Respond with a detailed analysis containing:\n"
        "1. **Executive Summary**: High-level performance overview.\n"
        "2. **Bottlenecks & Analysis**: Detailed description of efficiency issues (nested loops, "
        "file I/O, database round-trips, etc.).\n"
        "3. **Complexity Comparison**: A markdown table with these exact columns:\n"
        "   | Metric | Before | After |\n"
        "   (Include Time Complexity, Space Complexity, and any key I/O or concurrency metrics)\n"
        "4. **Optimized Code**: Corrected, highly efficient code blocks that solve the performance "
        "issues without breaking logic."
    )
    result = await safe_invoke(prompt)
    return {"performance_draft": result}


# Node #3: The Joint Reconciler / Synthesis Agent
async def joint_reconciler_node(state: AuditState) -> Dict[str, Any]:
    print(f"🤝 [Agent] Joint Reconciler Node is merging & resolving conflict reviews for: {state['file_path']}")

    security_draft = state.get("security_draft", "No security draft generated.")
    performance_draft = state.get("performance_draft", "No performance draft generated.")
    code_to_review = state["source_code"]

    prompt = (
        "You are the Joint Reconciler Agent for CodeAuditAI.\n"
        "Your task is to merge, polish, and resolve any contradictions between a security analysis report and a performance criticism report.\n\n"
        "Target Code Audited:\n"
        f"```\n{code_to_review}\n```\n\n"
        "--- Preliminary Security Report ---\n"
        f"{security_draft}\n\n"
        "--- Preliminary Performance Report ---\n"
        f"{performance_draft}\n\n"
        "Instructions:\n"
        "1. Compare both reports. Check if any optimization proposed in the Performance Report introduces a security leak, OR if any validation/mitigation in the Security Report creates a performance bottleneck (e.g. adding heavy synchronous calls or database checks).\n"
        "2. Resolve any conflicts by modifying/combining the suggestions. Ensure the recommended code blocks in both reports do not contradict each other.\n"
        "3. Output a final, unified response in the following exact JSON format (ensure it's valid JSON):\n"
        "{\n"
        '  "security_report": "[Detailed final reconciled security analysis in markdown format]",\n'
        '  "performance_report": "[Detailed final reconciled performance analysis in markdown format]"\n'
        "}\n"
        "Return ONLY the raw JSON string. Do not include markdown code block backticks (like ```json) in your final response."
    )

    content = await safe_invoke(prompt)
    sec_report, perf_report = _parse_reconciled_json(content, security_draft, performance_draft)

    return {
        "security_report": sec_report,
        "performance_report": perf_report
    }


def _parse_reconciled_json(raw: str, default_sec: str, default_perf: str) -> tuple:
    """Robustly extracts and parses security and performance reports from LLM JSON responses."""
    if not raw or not raw.strip():
        return default_sec, default_perf

    text = raw.strip()
    # Strip markdown code blocks if wrapped
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Attempt 1: Direct JSON parse with strict=False (allows control characters)
    try:
        data = json.loads(text, strict=False)
        sec = data.get("security_report")
        perf = data.get("performance_report")
        if sec and perf:
            return sec, perf
    except Exception:
        pass

    # Extract JSON object substring between outermost { and }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    candidate = text[first_brace:last_brace + 1] if (first_brace != -1 and last_brace > first_brace) else text

    # Attempt 2: Sanitize invalid escape sequences (e.g. \d, \s, \w, unescaped path backslashes)
    try:
        sanitized = re.sub(r'\\(?!([\"\\/bfnrt]|u[0-9a-fA-F]{4}))', r'\\\\', candidate)
        sanitized = re.sub(r',\s*([}\]])', r'\1', sanitized)
        data = json.loads(sanitized, strict=False)
        sec = data.get("security_report")
        perf = data.get("performance_report")
        if sec and perf:
            return sec, perf
    except Exception:
        pass

    # Attempt 3: Regex boundary extraction if JSON was truncated or malformed
    sec_match = re.search(r'"security_report"\s*:\s*"([\s\S]*?)(?="\s*,\s*"performance_report"|"\s*\})', candidate)
    perf_match = re.search(r'"performance_report"\s*:\s*"([\s\S]*?)(?="\s*,\s*"security_report"|"\s*\})', candidate)

    sec = default_sec
    perf = default_perf
    if sec_match:
        matched = sec_match.group(1).replace(r'\"', '"').replace(r'\n', '\n')
        if len(matched) > 20:
            sec = matched
    if perf_match:
        matched = perf_match.group(1).replace(r'\"', '"').replace(r'\n', '\n')
        if len(matched) > 20:
            perf = matched

    return sec, perf


# --- Wiring the Collaborative Architecture ---

workflow = StateGraph(AuditState)

# Register the specialized worker nodes
workflow.add_node("security_agent", security_auditor_node)
workflow.add_node("performance_agent", performance_critic_node)
workflow.add_node("reconciler_agent", joint_reconciler_node)

# Parallel execution path (Fan-out / Fan-in)
workflow.add_edge(START, "security_agent")
workflow.add_edge(START, "performance_agent")

workflow.add_edge("security_agent", "reconciler_agent")
workflow.add_edge("performance_agent", "reconciler_agent")

workflow.add_edge("reconciler_agent", END)

# Compile into executable graph
audit_agent_app = workflow.compile()