#!/usr/bin/env python3
"""Work through the intake review queue.

The queue holds no patient details on purpose, so this is what puts a claim in
front of you: it decrypts one record from the vault, prints it, and that read
is audited like any other. Seeing a patient's data is an event worth recording,
including when it is you.

    ./review.py              what is waiting, worst first
    ./review.py <record>     open one claim
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vault  # noqa: E402

ORDER = {"BLOCK": 0, "FAILED": 1, "REVIEW": 2, "CLEAN": 3}


def main() -> int:
    queue_path = vault.VAULT / "review_queue.json"
    if not queue_path.is_file():
        print("no review queue yet - run: ./intake.py <folder>")
        return 1
    items = json.loads(queue_path.read_text())["items"]

    if len(sys.argv) > 1:
        record = sys.argv[1]
        claim = vault.get(record)          # audited read
        item = next((i for i in items if i.get("record") == record), {})
        print(f"\n{record}   [{item.get('status', '?')}]   from {item.get('file', '?')}\n")
        for why in item.get("reasons", []):
            print(f"  ! {why}")
        print()
        for k, v in claim.items():
            if isinstance(v, list):
                print(f"  {k}:")
                for entry in v:
                    print(f"      {entry}")
            else:
                print(f"  {k:20} {v}")
        print("\nThis is a draft. Nothing has been submitted.")
        return 0

    items.sort(key=lambda i: ORDER.get(i.get("status"), 9))
    counts = {}
    for i in items:
        counts[i["status"]] = counts.get(i["status"], 0) + 1
    print(f"\n{len(items)} in the queue: " +
          ", ".join(f"{v} {k}" for k, v in counts.items()) + "\n")
    for i in items:
        if i["status"] == "CLEAN":
            continue
        print(f"  [{i['status']:6}] {i['file']:30} {i.get('record') or '(not stored)'}")
        for why in i.get("reasons", [])[:3]:
            print(f"             - {why}")
    print("\nOpen one with:  ./review.py <record>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
