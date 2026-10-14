import sqlite3
import os
from typing import Dict, Any, Optional, List

class SQLiteStorageService:
    def __init__(self, db_path: str = "./app/services/codeaudit.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initializes the database schema if tables do not exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Repositories Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    name TEXT,
                    summary TEXT
                )
            """)
            
            # Files Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_path TEXT,
                    file_path TEXT UNIQUE,
                    hash TEXT,
                    summary TEXT,
                    importance TEXT,
                    language TEXT
                )
            """)
            
            # Audits Table (Security & Performance cached reports)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    security_report TEXT,
                    performance_report TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()

    # --- Repository Operations ---
    
    def upsert_repository(self, path: str, name: str, summary: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO repositories (path, name, summary)
                VALUES (?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    name=excluded.name,
                    summary=excluded.summary
            """, (path, name, summary))
            conn.commit()

    def get_repository(self, path: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repositories WHERE path = ?", (path,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_repositories(self) -> List[Dict[str, Any]]:
        """Returns a list of all indexed repositories with their file counts and audited file counts."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    r.id,
                    COALESCE(r.path, f.repo_path) AS path,
                    COALESCE(r.name, '') AS name,
                    COALESCE(r.summary, '') AS summary,
                    COUNT(DISTINCT f.id) AS file_count,
                    COUNT(DISTINCT a.id) AS audited_count
                FROM files f
                LEFT JOIN repositories r ON r.path = f.repo_path
                LEFT JOIN audits a ON a.file_path = f.file_path
                WHERE f.repo_path IS NOT NULL AND f.repo_path != ''
                GROUP BY COALESCE(r.path, f.repo_path)
                ORDER BY r.id DESC, file_count DESC
            """)
            repos = []
            for row in cursor.fetchall():
                d = dict(row)
                if not d["name"] and d["path"]:
                    d["name"] = os.path.basename(d["path"].rstrip("/"))
                repos.append(d)
            return repos

    def delete_repository(self, repo_path: str) -> bool:
        """Removes a repository, its file catalog, and cached audits from SQLite."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM audits 
                WHERE file_path IN (SELECT file_path FROM files WHERE repo_path = ?)
            """, (repo_path,))
            cursor.execute("DELETE FROM files WHERE repo_path = ?", (repo_path,))
            cursor.execute("DELETE FROM repositories WHERE path = ?", (repo_path,))
            conn.commit()
            return True


    # --- File Operations ---

    def upsert_file_metadata(self, repo_path: str, file_path: str, file_hash: str, 
                             summary: str = "", importance: str = "Medium", language: str = ""):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO files (repo_path, file_path, hash, summary, importance, language)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    hash=excluded.hash,
                    summary=excluded.summary,
                    importance=excluded.importance,
                    language=excluded.language
            """, (repo_path, file_path, file_hash, summary, importance, language))
            conn.commit()

    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_repo_files(self, repo_path: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE repo_path = ?", (repo_path,))
            return [dict(row) for row in cursor.fetchall()]

    # --- Audit Operations ---

    def upsert_audit(self, file_path: str, security_report: str, performance_report: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audits (file_path, security_report, performance_report, timestamp)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(file_path) DO UPDATE SET
                    security_report=excluded.security_report,
                    performance_report=excluded.performance_report,
                    timestamp=CURRENT_TIMESTAMP
            """, (file_path, security_report, performance_report))
            conn.commit()

    def get_audit(self, file_path: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audits WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def clear_audit(self, file_path: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audits WHERE file_path = ?", (file_path,))
            conn.commit()

    def clear_all_audits(self):
        """Removes every cached audit record from the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM audits")
            conn.commit()
