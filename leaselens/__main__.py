"""Entry point: ``python -m leaselens [--seed] [--port N]``."""

from __future__ import annotations

import argparse

import uvicorn

from .server import app, seed_from_samples


def main() -> None:
    parser = argparse.ArgumentParser(description="LeaseLens demo server")
    parser.add_argument("--seed", action="store_true", help="preload sample leases")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    if args.seed:
        count = seed_from_samples()
        print(f"Seeded {count} sample documents into the inbox.")

    print(f"LeaseLens running at http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
