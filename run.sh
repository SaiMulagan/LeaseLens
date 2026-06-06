#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pip install -q -r requirements.txt
python scripts/generate_leases.py            # (re)create sample PDFs
python -m leaselens --seed                   # boot API + UI, preload the inbox
