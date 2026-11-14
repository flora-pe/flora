#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="${PWD}:${PYTHONPATH:-}"
API_PORT="${FLORA_API_PORT:-8000}"
UI_PORT="${FLORA_UI_PORT:-8501}"
uvicorn mvp.api:app --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!
cleanup() { kill "$API_PID" 2>/dev/null || true; wait "$API_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
export FLORA_API_URL="http://127.0.0.1:${API_PORT}"
echo "API http://127.0.0.1:${API_PORT}/docs | Frontend http://127.0.0.1:${UI_PORT}"
streamlit run mvp/ui.py --server.address 127.0.0.1 --server.port "$UI_PORT" --server.headless true
