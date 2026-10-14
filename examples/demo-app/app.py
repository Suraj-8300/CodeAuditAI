"""
demo-app / app.py
-----------------
A simple demo application containing clear, intentional flaws for demonstration:
1. Security Flaw (CWE-89): SQL Injection via raw string formatting.
2. Security Flaw (CWE-798): Hardcoded authentication secret.
3. Performance Issue: Quadratic O(n^2) nested loop in list processing.
"""

import sqlite3
import hashlib

# ❌ VULNERABILITY #1 (CWE-798): Hardcoded Secret Key
# Risk: Secrets committed to source control can be leaked or extracted by attackers.
SECRET_TOKEN = "demo-insecure-api-secret-key-99999"


def authenticate_admin(token: str) -> bool:
    """Verifies if the provided token matches the admin secret."""
    return token == SECRET_TOKEN


def search_user(db_conn, username: str):
    """
    Looks up a user by username in the database.
    
    ❌ VULNERABILITY #2 (CWE-89): SQL Injection
    Risk: Unsanitized user input is concatenated directly into the SQL query string.
    An attacker can pass: ' OR '1'='1 to dump the entire database.
    """
    cursor = db_conn.cursor()
    # Flawed line:
    query = f"SELECT id, username, email FROM users WHERE username = '{username}'"
    cursor.execute(query)
    return cursor.fetchall()


def find_matching_products(catalog_a: list, catalog_b: list) -> list:
    """
    Finds items present in both catalogs.
    
    ⚡ PERFORMANCE ISSUE: O(n * m) Quadratic Time Complexity
    Problem: Using nested loops with an 'in' check creates an O(n^2) bottleneck.
    For 10,000 items, this performs 100,000,000 comparisons!
    """
    matches = []
    # Nested loops cause performance degradation on large datasets:
    for item_a in catalog_a:
        for item_b in catalog_b:
            if item_a == item_b:
                if item_a not in matches:
                    matches.append(item_a)
    return matches


if __name__ == "__main__":
    print("Demo App initialized.")

