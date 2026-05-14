"""
DuckDB storage for the graph analytics demo.

Stores centrality metrics, path results, and topology measurements so the
walkthrough can compare metrics across different analysis methods and produce
summary tables without re-running computations.

Tables:
    node_metrics    — node, metric_name, metric_value
    topology_summary — metric_name, metric_value
    paths           — source, target, path_text, method
"""

import duckdb


def open_db(path: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """Open (or create) the demo analytics database."""
    conn = duckdb.connect(path)
    _create_tables(conn)
    return conn


def _create_tables(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS node_metrics (
            node VARCHAR NOT NULL,
            metric_name VARCHAR NOT NULL,
            metric_value DOUBLE NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topology_summary (
            metric_name VARCHAR PRIMARY KEY,
            metric_value DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS paths (
            source VARCHAR NOT NULL,
            target VARCHAR NOT NULL,
            path_text VARCHAR NOT NULL,
            method VARCHAR NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            step INTEGER NOT NULL,
            description VARCHAR NOT NULL,
            node_count INTEGER,
            edge_count INTEGER
        )
    """)


def store_node_metrics(
    conn: duckdb.DuckDBPyConnection,
    metric_name: str,
    values: dict[str, float],
) -> None:
    """Store a centrality/degree metric for all nodes."""
    for node, value in values.items():
        conn.execute(
            "INSERT INTO node_metrics VALUES (?, ?, ?)",
            [node, metric_name, float(value)],
        )


def store_topology(conn: duckdb.DuckDBPyConnection, metrics: dict[str, float]) -> None:
    """Store global topology metrics."""
    for name, value in metrics.items():
        conn.execute(
            "INSERT OR REPLACE INTO topology_summary VALUES (?, ?)",
            [name, float(value)],
        )


def store_path(
    conn: duckdb.DuckDBPyConnection,
    source: str,
    target: str,
    path_text: str,
    method: str,
) -> None:
    conn.execute(
        "INSERT INTO paths VALUES (?, ?, ?, ?)",
        [source, target, path_text, method],
    )


def top_nodes(
    conn: duckdb.DuckDBPyConnection,
    metric_name: str,
    limit: int = 5,
) -> list[dict]:
    """Return the top-N nodes for a given metric."""
    rows = conn.execute(
        "SELECT node, metric_value FROM node_metrics WHERE metric_name = ? ORDER BY metric_value DESC LIMIT ?",
        [metric_name, limit],
    ).fetchall()
    return [{"node": r[0], "value": r[1]} for r in rows]


def metric_comparison(
    conn: duckdb.DuckDBPyConnection,
    metric_names: list[str],
    limit: int = 5,
) -> list[dict]:
    """Return a comparison table: node vs multiple metrics."""
    if not metric_names:
        return []
    cols = ", ".join(
        f"MAX(CASE WHEN metric_name = ? THEN metric_value END) AS \"{m}\""
        for m in metric_names
    )
    params = list(metric_names) + [limit]
    query = f"""
        SELECT node, {cols}
        FROM node_metrics
        GROUP BY node
        ORDER BY "{metric_names[0]}" DESC
        LIMIT ?
    """
    rows = conn.execute(query, params).fetchall()
    col_names = [desc[0] for desc in conn.description]
    return [dict(zip(col_names, row)) for row in rows]
