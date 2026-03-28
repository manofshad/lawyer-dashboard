from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.sample_incidents import build_sample_incidents, dump_sample_incidents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transform the sample pothole CSV into normalized JSON records."
    )
    parser.add_argument(
        "--csv-path",
        type=Path,
        default=Path("street-pothole-sample-10.csv"),
        help="Path to the 10-row sample CSV.",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=Path("sample_incidents.json"),
        help="Path to write the normalized JSON artifact.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = build_sample_incidents(args.csv_path)
    dump_sample_incidents(records, args.output_path)
    print(f"Wrote {len(records)} records to {args.output_path}")


if __name__ == "__main__":
    main()
