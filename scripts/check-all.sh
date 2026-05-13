#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Python: pip install -r requirements-dev.txt"
python -m pip install -q -r requirements-dev.txt

if [[ ! -d node_modules ]]; then
  echo "npm install (no node_modules)"
  npm install
fi

echo "npm run check"
npm run check
