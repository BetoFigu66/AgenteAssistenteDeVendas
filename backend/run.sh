#!/usr/bin/env bash
set -e
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
