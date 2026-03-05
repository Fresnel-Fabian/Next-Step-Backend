#!/usr/bin/env bash
# Start backend: ensure PostgreSQL (Docker) is running, then run uvicorn.
# Usage: ./start.sh   or   bash start.sh

set -e

CONTAINER_NAME="school_postgres"
POSTGRES_IMAGE="postgres:16-alpine"

echo "→ Checking Docker..."
if ! docker info >/dev/null 2>&1; then
  echo "  Docker is not running. Please start Docker Desktop and run this script again."
  exit 1
fi
echo "  Docker is running."

echo "→ Checking container '$CONTAINER_NAME'..."
if ! docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
  echo "  Container does not exist. Creating it..."
  docker run --name "$CONTAINER_NAME" \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=school_db \
    -p 5432:5432 \
    -d "$POSTGRES_IMAGE"
  echo "  Container created. Waiting for PostgreSQL to be ready..."
  sleep 3
else
  if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "  Container exists but is stopped. Starting it..."
    docker start "$CONTAINER_NAME"
    echo "  Waiting for PostgreSQL to be ready..."
    sleep 3
  else
    echo "  Container is already running."
  fi
fi

echo "→ Starting backend server..."
exec uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
