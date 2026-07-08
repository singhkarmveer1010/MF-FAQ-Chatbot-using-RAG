#!/usr/bin/env bash
set -e

PORT="${PORT:-8000}"
echo "========================================================="
echo "Starting Mutual Fund FAQ Assistant API Server on port ${PORT}"
echo "========================================================="

exec uvicorn src.api.main:app --host 0.0.0.0 --port "${PORT}"
