#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
if ! command -v brew >/dev/null 2>&1; then
  echo 'Install libmagic and Poppler with your system package manager first.'
else
  brew install libmagic poppler
fi
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-local.txt
.venv/bin/python -m spacy download en_core_web_lg
npm --prefix frontend ci
npm --prefix frontend run build
