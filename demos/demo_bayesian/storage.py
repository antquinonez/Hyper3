"""
SQLite storage for the Bayesian reasoning demo.

Persists prior/posterior snapshots and evidence history so the walkthrough
can show how beliefs evolve across updates. Each call to bayes.update()
produces a row in the belief_snapshots table.

Tables:
    conditions       — name, severity, description, prevalence
    evidence_log     — step, evidence_name, description, kl_divergence
    belief_snapshots — step, condition, probability
"""

import sqlite3

try:
    from .data import CONDITIONS, EVIDENCE_SEQUENCE
except ImportError:
    from data import CONDITIONS, EVIDENCE_SEQUENCE


def open_db(path: str = ":memory:") -> sqlite3.Connection:
    """Open (or create) the demo database and return a connection."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _create_tables(conn)
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS conditions (
            name TEXT PRIMARY KEY,
            severity TEXT NOT NULL,
            description TEXT,
            prevalence REAL
        );

        CREATE TABLE IF NOT EXISTS evidence_log (
            step INTEGER PRIMARY KEY,
            evidence_name TEXT NOT NULL,
            description TEXT,
            kl_divergence REAL
        );

        CREATE TABLE IF NOT EXISTS belief_snapshots (
            step INTEGER NOT NULL,
            condition TEXT NOT NULL,
            probability REAL NOT NULL,
            PRIMARY KEY (step, condition)
        );
    """)
    conn.commit()


def seed_conditions(conn: sqlite3.Connection) -> None:
    """Insert the predefined conditions into the database."""
    for name, info in CONDITIONS.items():
        conn.execute(
            "INSERT OR REPLACE INTO conditions VALUES (?, ?, ?, ?)",
            (name, info["severity"], info["description"], info["prevalence"]),
        )
    conn.commit()


def snapshot_beliefs(
    conn: sqlite3.Connection,
    step: int,
    posterior: dict[str, float],
) -> None:
    """Record a belief snapshot after an evidence update."""
    for condition, probability in posterior.items():
        conn.execute(
            "INSERT OR REPLACE INTO belief_snapshots VALUES (?, ?, ?)",
            (step, condition, probability),
        )
    conn.commit()


def log_evidence(
    conn: sqlite3.Connection,
    step: int,
    evidence_name: str,
    description: str,
    kl_divergence: float,
) -> None:
    """Record that an evidence update was applied."""
    conn.execute(
        "INSERT OR REPLACE INTO evidence_log VALUES (?, ?, ?, ?)",
        (step, evidence_name, description, kl_divergence),
    )
    conn.commit()


def load_belief_history(conn: sqlite3.Connection) -> list[dict]:
    """Return all belief snapshots as a list of dicts, ordered by step."""
    rows = conn.execute(
        "SELECT step, condition, probability FROM belief_snapshots ORDER BY step, condition"
    ).fetchall()
    return [dict(r) for r in rows]


def load_evidence_log(conn: sqlite3.Connection) -> list[dict]:
    """Return all evidence log entries."""
    rows = conn.execute(
        "SELECT step, evidence_name, description, kl_divergence FROM evidence_log ORDER BY step"
    ).fetchall()
    return [dict(r) for r in rows]
