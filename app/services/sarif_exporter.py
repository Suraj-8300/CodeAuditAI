"""
sarif_exporter.py
-----------------
Exports CodeAuditAI security findings into the standardized SARIF v2.1.0 format
(Static Analysis Results Interchange Format).

Compatible with:
- GitHub Advanced Security / Code Scanning Alerts
- VS Code SARIF Viewer extension
- GitLab SAST
- SonarQube & DefectDojo
"""

import re
import json
from typing import List, Dict, Any, Optional


# Common vulnerability keyword heuristics for reports without explicit markdown tables
KEYWORD_TO_CWE = [
    (r"hardcoded|secret|credential|api[ _-]?key|token|password", "CWE-798", "Use of Hard-coded Credentials"),
    (r"race condition|toctou|concurrency|thread safe", "CWE-362", "Concurrent Execution using Shared Resource"),
    (r"path traversal|directory traversal|\.\./", "CWE-22", "Path Traversal"),
    (r"sql[ _-]?injection|sqli", "CWE-89", "SQL Injection"),
    (r"command[ _-]?injection|rce|shell_exec|exec\(", "CWE-78", "Command Injection"),
    (r"cross[ _-]?site|xss|innerhtml", "CWE-79", "Cross-site Scripting (XSS)"),
    (r"cors|origin|cross-origin", "CWE-942", "Permissive Cross-Origin Resource Sharing"),
    (r"input validation|sanitize|untrusted input", "CWE-20", "Improper Input Validation"),
    (r"buffer[ _-]?overflow|memory leak|use-after-free", "CWE-120", "Buffer Overflow & Memory Flaw"),
    (r"deserializ", "CWE-502", "Deserialization of Untrusted Data"),
    (r"information disclosure|leak|stack trace|error handling", "CWE-200", "Exposure of Sensitive Information"),
    (r"denial of service|dos|resource exhaustion|starve", "CWE-400", "Uncontrolled Resource Consumption"),
    (r"supply chain|dependency|cve|package", "CWE-829", "Inclusion of Untrusted Dependency"),
    (r"authorization|auth bypass|privilege", "CWE-285", "Improper Authorization"),
]


def _parse_vulnerabilities_from_markdown(security_report: str) -> List[Dict[str, Any]]:
    """
    Parses structured vulnerability entries from the security report markdown.
    Extracts CWE IDs, OWASP category, severity, lines, descriptions, and impact.
    Handles markdown tables, bulleted lists, and numbered findings.
    """
    vulnerabilities = []
    
    # 1. Look for markdown table rows: | CWE ID | OWASP Category | Severity | Line(s) | Description | Impact |
    table_row_pattern = re.compile(
        r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(CRITICAL|WARNING|SAFE|ERROR|HIGH|MEDIUM|LOW)\s*\|\s*([^|]*?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|",
        re.IGNORECASE
    )
    
    for match in table_row_pattern.finditer(security_report):
        cwe = match.group(1).strip()
        owasp = match.group(2).strip()
        severity = match.group(3).strip().upper()
        lines = match.group(4).strip()
        desc = match.group(5).strip()
        impact = match.group(6).strip()
        
        if "---" in cwe or cwe.lower() == "cwe id":
            continue
            
        line_num = 1
        line_match = re.search(r"(\d+)", lines)
        if line_match:
            try:
                line_num = int(line_match.group(1))
            except ValueError:
                line_num = 1
                
        vulnerabilities.append({
            "cwe": cwe,
            "owasp": owasp,
            "severity": severity,
            "line": line_num,
            "description": desc,
            "impact": impact
        })
        
    # 2. Look for bullet points or numbered lists: * **Title:** Description
    if not vulnerabilities:
        bullet_pattern = re.compile(r"^\s*[\*\-\d\.]+\s+\*\*([^\*]+)\*\*\s*(.*)$", re.MULTILINE)
        for m in bullet_pattern.finditer(security_report):
            title = m.group(1).rstrip(":").strip()
            desc = m.group(2).strip()
            if not desc and len(title) > 20:
                desc = title
            
            # Check for explicit CWE in title or desc
            cwe_match = re.search(r"(CWE-\d+)", title + " " + desc, re.IGNORECASE)
            if cwe_match:
                matched_cwe = cwe_match.group(1).upper()
                matched_owasp = title
            else:
                matched_cwe = "CWE-General"
                matched_owasp = title
                combined = (title + " " + desc).lower()
                for kw, cwe_code, owasp_name in KEYWORD_TO_CWE:
                    if re.search(kw, combined):
                        matched_cwe = cwe_code
                        matched_owasp = owasp_name
                        break
            
            line_match = re.search(r"line[s]?\s*(\d+)", desc, re.IGNORECASE)
            line_num = int(line_match.group(1)) if line_match else 1
            
            sev = "WARNING"
            if re.search(r"critical|high|rce|injection|hardcoded secret", (title + " " + desc).lower()):
                sev = "CRITICAL"
                
            vulnerabilities.append({
                "cwe": matched_cwe,
                "owasp": matched_owasp,
                "severity": sev,
                "line": line_num,
                "description": desc or title,
                "impact": f"Risk of {matched_owasp} in {title}."
            })

    # 3. Fallback: If no structured items detected, derive from overall rating
    if not vulnerabilities:
        rating = "WARNING"
        if "[CRITICAL]" in security_report:
            rating = "CRITICAL"
        elif "[SAFE]" in security_report:
            rating = "SAFE"
            
        if rating != "SAFE":
            vulnerabilities.append({
                "cwe": "CWE-General",
                "owasp": "Security Flaw",
                "severity": rating,
                "line": 1,
                "description": "Security vulnerabilities detected in file analysis.",
                "impact": "Potential security compromise or exploitation risk."
            })
            
    return vulnerabilities


def _map_severity_to_sarif_level(severity: str) -> str:
    """Maps audit severity to standard SARIF level: 'error', 'warning', or 'note'."""
    sev = severity.upper()
    if sev in {"CRITICAL", "ERROR", "HIGH"}:
        return "error"
    elif sev in {"WARNING", "MEDIUM"}:
        return "warning"
    else:
        return "note"


def generate_sarif_report(audited_files: List[Dict[str, Any]], repo_name: str = "CodeAuditAI Scan") -> Dict[str, Any]:
    """
    Generates a valid SARIF v2.1.0 dictionary from a list of audited file records.

    Each item in audited_files can be:
    {
        "file_path": str, # relative or absolute path
        "security_report": str, # markdown text
        "performance_report": Optional[str]
    }
    """
    rules_dict: Dict[str, Dict[str, Any]] = {}
    results: List[Dict[str, Any]] = []

    for file_info in audited_files:
        file_path = file_info.get("file_path", "unknown")
        sec_report = file_info.get("security_report", "")
        
        findings = _parse_vulnerabilities_from_markdown(sec_report)
        
        for finding in findings:
            cwe = finding["cwe"]
            rule_id = cwe.replace(" ", "-") if cwe else "CA-SEC-001"
            level = _map_severity_to_sarif_level(finding["severity"])
            
            # Register rule metadata
            if rule_id not in rules_dict:
                rules_dict[rule_id] = {
                    "id": rule_id,
                    "name": rule_id,
                    "shortDescription": {
                        "text": f"{finding['owasp']} ({cwe})"
                    },
                    "fullDescription": {
                        "text": finding["description"]
                    },
                    "defaultConfiguration": {
                        "level": level
                    },
                    "properties": {
                        "tags": ["security", finding.get("owasp", "OWASP"), finding.get("severity", "WARNING")]
                    }
                }
                
            # Create SARIF result item
            result_item = {
                "ruleId": rule_id,
                "level": level,
                "message": {
                    "text": f"{finding['description']} (Impact: {finding['impact']})"
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {
                                "uri": file_path.replace("\\", "/")
                            },
                            "region": {
                                "startLine": finding.get("line", 1)
                            }
                        }
                    }
                ]
            }
            results.append(result_item)

    sarif_log = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "CodeAuditAI",
                        "version": "1.2.0",
                        "informationUri": "https://github.com/CodeAuditAI",
                        "rules": list(rules_dict.values())
                    }
                },
                "invocations": [
                    {
                        "executionSuccessful": True
                    }
                ],
                "results": results
            }
        ]
    }

    return sarif_log


def sarif_to_json_string(sarif_dict: Dict[str, Any], indent: int = 2) -> str:
    """Formats SARIF dictionary as an indented JSON string."""
    return json.dumps(sarif_dict, indent=indent)
