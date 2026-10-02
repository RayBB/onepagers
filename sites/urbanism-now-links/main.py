"""CLI: process all Notion rows missing an AI summary.

`uv run main.py` queries Notion for rows without an AI summary and processes them
by shelling out to worker.py (one short-lived subprocess per batch of up to
batch.MAX_BATCH rows). The heavy stack (litellm, trafilatura, markitdown) lives
only in those subprocesses, so this CLI's own footprint stays small and each
batch's memory is reclaimed when its worker exits.
"""

import sys

from batch import run_all_batches
from notion import get_notion_rows_without_ai_summary


def run_once() -> int:
    """Process all pending rows. Returns the number of errors."""
    rows = get_notion_rows_without_ai_summary()
    if not rows:
        print("no rows without AI summary; nothing to do")
        return 0

    print(f"processing {len(rows)} row(s) in batches of up to 10...")
    ok = 0
    errors = 0
    for batch, batch_results in run_all_batches(rows):
        for res in batch_results:
            if res.get("ok"):
                ok += 1
            else:
                errors += 1
                print(f"  error {res['id']}: {res.get('error')}", file=sys.stderr)
    print(f"done, {ok} ok, {errors} error(s)")
    return errors


if __name__ == "__main__":
    sys.exit(0 if run_once() == 0 else 1)
