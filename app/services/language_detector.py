"""
language_detector.py
--------------------
Provides language detection and per-language audit hint lookups for CodeAuditAI.
"""

import os
from typing import Dict

# ---------------------------------------------------------------------------
# Extension → human-readable language name
# ---------------------------------------------------------------------------
_EXT_TO_LANGUAGE: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".h": "C++",
    ".hpp": "C++",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "CSS",
    ".sass": "CSS",
    ".less": "CSS",
    ".go": "Go",
    ".rs": "Rust",
    ".php": "PHP",
    ".md": "Markdown",
    ".mdx": "Markdown",
    ".cs": "C#",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".scala": "Scala",
    ".lua": "Lua",
    ".pl": "Perl",
    ".pm": "Perl",
    ".r": "R",
    ".R": "R",
    ".sh": "Shell",
    ".bash": "Shell",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".sql": "SQL",
    ".toml": "TOML",
}

# ---------------------------------------------------------------------------
# Language name → markdown code-fence tag
# ---------------------------------------------------------------------------
_LANGUAGE_TO_FENCE: Dict[str, str] = {
    "Python": "python",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Java": "java",
    "C": "c",
    "C++": "cpp",
    "HTML": "html",
    "CSS": "css",
    "Go": "go",
    "Rust": "rust",
    "PHP": "php",
    "Markdown": "markdown",
    "C#": "csharp",
    "Ruby": "ruby",
    "Swift": "swift",
    "Kotlin": "kotlin",
    "Scala": "scala",
    "Lua": "lua",
    "Perl": "perl",
    "R": "r",
    "Shell": "bash",
    "JSON": "json",
    "YAML": "yaml",
    "XML": "xml",
    "SQL": "sql",
    "TOML": "toml",
}

# ---------------------------------------------------------------------------
# Per-language audit hints
# ---------------------------------------------------------------------------
_GENERIC_HINTS = {
    "security_hints": (
        "Watch for hardcoded secrets/credentials, credential exposure in plain text, "
        "injection risks via untrusted input, and sensitive data in comments."
    ),
    "performance_hints": (
        "Look for unnecessary re-parsing of large files, excessive in-memory buffering, "
        "and synchronous I/O where async alternatives exist."
    ),
}

_LANGUAGE_AUDIT_HINTS: Dict[str, Dict[str, str]] = {
    "Python": {
        "security_hints": (
            "SQL injection via string formatting; command injection via subprocess/os.system; "
            "unsafe deserialization via pickle; path traversal; SSTI; hardcoded credentials; "
            "insecure random (use secrets module); eval/exec usage; XXE; SSRF."
        ),
        "performance_hints": (
            "GIL contention in CPU-bound threads; N+1 DB queries; string concatenation in loops "
            "(use join); blocking I/O without async; large in-memory structures (use generators)."
        ),
    },
    "JavaScript": {
        "security_hints": (
            "XSS via innerHTML/document.write; prototype pollution; eval() usage; ReDoS; "
            "client-side secret exposure; DOM injection; insecure localStorage usage."
        ),
        "performance_hints": (
            "Blocking main thread with synchronous operations; missing debounce/throttle; "
            "memory leaks via unremoved event listeners; excessive DOM manipulation; "
            "large bundle size impacting load time."
        ),
    },
    "TypeScript": {
        "security_hints": (
            "XSS via innerHTML/document.write; prototype pollution; eval() usage; ReDoS; "
            "client-side secret exposure; DOM injection; insecure localStorage usage; "
            "unsafe 'any' casts bypassing type safety; missing null/undefined checks."
        ),
        "performance_hints": (
            "Blocking main thread with synchronous operations; missing debounce/throttle; "
            "memory leaks via unremoved event listeners; excessive DOM manipulation; "
            "large bundle size impacting load time."
        ),
    },
    "Java": {
        "security_hints": (
            "SQL injection; Java deserialization (ObjectInputStream); XXE; LDAP injection; "
            "insecure reflection; hardcoded credentials; path traversal; "
            "insecure crypto (MD5/SHA1); log injection."
        ),
        "performance_hints": (
            "String concatenation in loops (use StringBuilder); GC pressure from excessive "
            "object creation; N+1 JPA/Hibernate queries; synchronization bottlenecks in "
            "multi-threaded code."
        ),
    },
    "C": {
        "security_hints": (
            "Buffer overflow via gets/strcpy/sprintf; format string vulnerabilities; "
            "integer overflow/underflow; use-after-free; double free; null pointer dereference; "
            "off-by-one errors; memory leaks; uninitialized variable reads."
        ),
        "performance_hints": (
            "Cache miss patterns from poor data locality; unnecessary heap allocations "
            "(prefer stack where safe); blocking system calls in hot paths."
        ),
    },
    "C++": {
        "security_hints": (
            "Buffer overflow; use-after-free; dangling pointers; unsafe C-style casts; "
            "missing RAII (manual new/delete); race conditions without proper synchronization; "
            "uninitialized memory reads; integer overflow."
        ),
        "performance_hints": (
            "Unnecessary copy vs move semantics; excessive heap allocations; virtual function "
            "overhead in tight loops; missing constexpr for compile-time evaluation; "
            "poor cache locality in data structures."
        ),
    },
    "HTML": {
        "security_hints": (
            "Inline event handlers enabling XSS; missing Content-Security-Policy meta tags; "
            "form actions over HTTP (not HTTPS); missing CSRF tokens; sensitive data in HTML "
            "comments; missing rel='noopener noreferrer' on external links; "
            "iframe without sandbox attribute."
        ),
        "performance_hints": (
            "Missing lazy loading on images (loading='lazy'); non-deferred/async scripts "
            "blocking render; missing preload/prefetch hints for critical assets; "
            "excessive DOM depth impacting layout/paint."
        ),
    },
    "CSS": {
        "security_hints": (
            "CSS injection via user-controlled style properties; clickjacking via z-index "
            "manipulation; legacy expression() usage (IE); @import from untrusted external "
            "sources leaking browsing history."
        ),
        "performance_hints": (
            "Selector specificity wars causing expensive repaints; expensive properties "
            "(box-shadow, filter, opacity transitions); large unused CSS increasing parse time; "
            "blocking @import chains delaying render."
        ),
    },
    "Go": {
        "security_hints": (
            "SQL injection via fmt.Sprintf in queries; command injection via exec.Command with "
            "user input; path traversal; SSRF via user-controlled URLs; goroutine leaks; "
            "insecure TLS configuration (tls.Config)."
        ),
        "performance_hints": (
            "Goroutine leaks from missing context cancellation; channel misuse causing deadlocks; "
            "excessive allocations in hot paths (use sync.Pool); sync.Mutex misuse instead of "
            "RWMutex for read-heavy workloads."
        ),
    },
    "Rust": {
        "security_hints": (
            "Unsafe block misuse exposing memory safety guarantees; integer overflow silently "
            "wrapping in release builds; unwrap()/expect() panicking in production; "
            "TOCTOU race in filesystem operations; insecure deserialization with serde."
        ),
        "performance_hints": (
            "Unnecessary clones of large data; excessive Arc/Rc reference counting overhead; "
            "blocking operations inside async executors (tokio/async-std); missing zero-copy "
            "patterns (use Bytes or slices instead of owned vecs)."
        ),
    },
    "PHP": {
        "security_hints": (
            "SQL injection via string-concatenated queries; command injection via shell_exec/"
            "system/exec; LFI/RFI via include/require with user input; XSS via unescaped "
            "output (echo $_GET); CSRF on state-changing endpoints; insecure session management "
            "(session_regenerate_id missing); unserialize() with untrusted data."
        ),
        "performance_hints": (
            "N+1 database queries in loops; missing opcode caching (OPcache disabled); "
            "blocking synchronous I/O for remote calls."
        ),
    },
}


def detect_language(file_path: str) -> str:
    """
    Maps a file path's extension to a human-readable language name.

    Args:
        file_path: Absolute or relative path to the source file.

    Returns:
        Human-readable language string (e.g. 'Python'), or 'Unknown'.
    """
    _, ext = os.path.splitext(file_path)
    return _EXT_TO_LANGUAGE.get(ext, "Unknown")


def get_lang_fence(language: str) -> str:
    """
    Returns the markdown code-fence tag for a given language name.

    Args:
        language: Human-readable language name (e.g. 'Python', 'C++').

    Returns:
        Lowercase fence tag (e.g. 'python', 'cpp'), or 'text' if unknown.
    """
    return _LANGUAGE_TO_FENCE.get(language, "text")


def get_language_audit_hints(language: str) -> Dict[str, str]:
    """
    Returns a dict with 'security_hints' and 'performance_hints' strings
    tailored to the given language.

    Args:
        language: Human-readable language name (e.g. 'Python', 'Go').

    Returns:
        Dict with keys 'security_hints' and 'performance_hints'.
    """
    return _LANGUAGE_AUDIT_HINTS.get(language, _GENERIC_HINTS)
