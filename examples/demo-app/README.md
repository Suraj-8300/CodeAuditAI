# 🧪 Demo Vulnerable App

A minimal demo application designed to demonstrate **CodeAuditAI's** multi-agent security and performance auditing capabilities.

## Contained Intentional Issues:
1. **CWE-798**: Hardcoded `SECRET_TOKEN` on line 14.
2. **CWE-89**: SQL Injection in `search_user()` on line 32 via raw f-string concatenation.
3. **Big-O Complexity**: \(O(n^2)\) quadratic nested loop in `find_matching_products()` on lines 47–52.

