"""Independent process entrypoint for long Agent runs."""

from __future__ import annotations

import argparse

from x2video.application import ApplicationService


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--work-dir", required=True)
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    service = ApplicationService(work_dir=args.work_dir, db_path=args.db)
    service.execute_sync(args.run_id)


if __name__ == "__main__":
    main()

