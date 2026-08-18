# storage.py
# SQLite storage layer for AgentAudit.
# Stores pipeline runs and individual claims for dashboard and regression testing.

import sqlite3
from datetime import datetime
from typing import Optional

from agentaudit.metrics.hallucination import HallucinationResult
from agentaudit.metrics.faithfulness import FaithfulnessResult
from agentaudit.metrics.cost import CostResult
from agentaudit.metrics.latency import LatencyResult


# --------------------------------------------------------------------------- #
# Database Setup
# --------------------------------------------------------------------------- #

import os
DEFAULT_DB_PATH = os.path.expanduser("~/.agentaudit/agentaudit.db")


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Creates the SQLite database and tables if they don't exist.
    Safe to call multiple times — won't overwrite existing data.
    """
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            pipeline_name       TEXT NOT NULL,
            timestamp           TEXT NOT NULL,
            query               TEXT,
            response            TEXT,
            context             TEXT,
            hallucination_score REAL,
            faithfulness_score  REAL,
            cost_usd            REAL,
            cost_inr            REAL,
            latency_ms          REAL,
            model_used          TEXT,
            error               TEXT,
            is_cost_estimated   INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL,
            metric_type TEXT NOT NULL,
            claim       TEXT NOT NULL,
            status      TEXT NOT NULL,
            evidence    TEXT,
            FOREIGN KEY (run_id) REFERENCES runs (id)
        )
    """)

    # Migration: add is_cost_estimated column if missing (for databases
    # created before this feature existed)
    try:
        cursor.execute("ALTER TABLE runs ADD COLUMN is_cost_estimated INTEGER")
    except sqlite3.OperationalError:
        pass  # column already exists — safe to ignore

    conn.commit()
    conn.close()


# --------------------------------------------------------------------------- #
# Save Run
# --------------------------------------------------------------------------- #

def save_run(
    pipeline_name: str,
    query: str,
    response: str,
    context: str,
    hallucination_result: Optional[HallucinationResult] = None,
    faithfulness_result: Optional[FaithfulnessResult] = None,
    cost_result: Optional[CostResult] = None,
    latency_result: Optional[LatencyResult] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """
    Saves one pipeline run and its claims to SQLite.
    Returns the run_id so caller can reference it later.
    """

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO runs (
            pipeline_name, timestamp, query, response, context,
            hallucination_score, faithfulness_score,
            cost_usd, cost_inr, latency_ms, model_used, error, is_cost_estimated
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        pipeline_name,
        datetime.utcnow().isoformat(),
        query,
        response,
        context,
        hallucination_result.hallucination_score if hallucination_result else None,
        faithfulness_result.faithfulness_score   if faithfulness_result else None,
        cost_result.cost_usd                     if cost_result else None,
        cost_result.cost_inr                     if cost_result else None,
        latency_result.latency_ms                if latency_result else None,
        hallucination_result.model_used          if hallucination_result else None,
        hallucination_result.error               if hallucination_result else None,
        1 if cost_result and cost_result.is_estimated else 0 if cost_result else None,
    ))

    run_id = cursor.lastrowid

    if hallucination_result and hallucination_result.claims:
        for claim in hallucination_result.claims:
            cursor.execute("""
                INSERT INTO claims (run_id, metric_type, claim, status, evidence)
                VALUES (?, ?, ?, ?, ?)
            """, (run_id, "hallucination", claim.claim, claim.status, claim.evidence))

    if faithfulness_result and faithfulness_result.claims:
        for claim in faithfulness_result.claims:
            cursor.execute("""
                INSERT INTO claims (run_id, metric_type, claim, status, evidence)
                VALUES (?, ?, ?, ?, ?)
            """, (run_id, "faithfulness", claim.claim, claim.status, claim.evidence))

    conn.commit()
    conn.close()

    return run_id


# --------------------------------------------------------------------------- #
# Read Runs
# --------------------------------------------------------------------------- #

def get_runs(
    pipeline_name: Optional[str] = None,
    limit: int = 100,
    db_path: str = DEFAULT_DB_PATH,
) -> list[dict]:
    """
    Fetch runs from the database.
    If pipeline_name is provided, filter by it.
    Returns list of dicts — easy to load into pandas or Streamlit.
    """

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if pipeline_name:
        cursor.execute("""
            SELECT * FROM runs
            WHERE pipeline_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (pipeline_name, limit))
    else:
        cursor.execute("""
            SELECT * FROM runs
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_run_by_id(
    run_id: int,
    db_path: str = DEFAULT_DB_PATH,
) -> Optional[dict]:
    """
    Fetch a single run by its id.
    Returns None if not found.
    """

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM runs WHERE id = ?", (run_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_claims(
    run_id: int,
    metric_type: Optional[str] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> list[dict]:
    """
    Fetch claims for a specific run.
    Optionally filter by metric_type — 'hallucination' or 'faithfulness'.
    """

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if metric_type:
        cursor.execute("""
            SELECT * FROM claims
            WHERE run_id = ? AND metric_type = ?
        """, (run_id, metric_type))
    else:
        cursor.execute("""
            SELECT * FROM claims
            WHERE run_id = ?
        """, (run_id,))

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows