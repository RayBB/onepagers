"""Lightweight dispatcher: runs the heavy worker as a short-lived subprocess.

This module deliberately imports only the stdlib (json, subprocess, sys) plus
the cheap Notion query, so the long-lived API server can use it without pulling
in litellm/instructor/trafilatura/markitdown. Each batch of rows is handed to a
fresh `python -m worker` subprocess that loads the heavy stack, does the work,
and dies — reclaiming its memory.
"""

import json
import subprocess
import sys
from typing import Iterator

MAX_BATCH = 10


def run_worker_batch(rows: list) -> list[dict]:
    """Run one worker subprocess for a batch of rows (each needs .id and .url).

    Returns a list of {"id", "ok", "error"?} result dicts, one per row.
    """
    payload = json.dumps([{"id": r.id, "url": r.url} for r in rows])
    proc = subprocess.run(
        [sys.executable, "-m", "worker"],
        input=payload,
        text=True,
        capture_output=True,
    )
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0 or not proc.stdout:
        err = (proc.stderr or f"worker exited {proc.returncode}").strip()
        return [{"id": r.id, "ok": False, "error": err} for r in rows]
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        err = (proc.stderr or proc.stdout or "unparseable worker output").strip()
        return [{"id": r.id, "ok": False, "error": err} for r in rows]


def run_all_batches(
    rows: list, max_batch: int = MAX_BATCH
) -> Iterator[tuple[list, list[dict]]]:
    """Yield (batch_rows, results) for each batch of rows.

    The rows are processed sequentially — one subprocess at a time — so at most
    one transient worker (~200MB) is alive at any moment.
    """
    for i in range(0, len(rows), max_batch):
        batch = rows[i : i + max_batch]
        yield batch, run_worker_batch(batch)
