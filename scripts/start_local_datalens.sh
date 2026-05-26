#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATALENS_DIR="${DATALENS_DIR:-$ROOT_DIR/.local/datalens}"
UI_PORT="${UI_PORT:-8081}"
HC="${HC:-1}"

mkdir -p "$(dirname "$DATALENS_DIR")"

if [ ! -d "$DATALENS_DIR/.git" ]; then
  echo "Cloning open-source DataLens into $DATALENS_DIR..."
  git clone https://github.com/datalens-tech/datalens "$DATALENS_DIR"
fi

cd "$DATALENS_DIR"

echo "Starting local DataLens on http://localhost:$UI_PORT ..."
UI_PORT="$UI_PORT" HC="$HC" docker compose up -d

cat <<TEXT

DataLens is starting.

Open:
  http://localhost:$UI_PORT

Default login:
  admin

Default password:
  admin

Create PostgreSQL connection in DataLens:
  Hostname: host.docker.internal
  Port: 5432
  Database: retail
  Username: airflow
  Password: airflow
  TLS: off
  Raw SQL level: Allow subqueries in datasets

Recommended DataLens datasets:
  dm.v_sales_enriched
  dm.v_monthly_sales_kpi
  dm.v_store_performance
  dm.v_category_performance
  dm.v_plan_fact_dashboard
  dm.v_inventory_risks
  dm.v_dashboard_summary

TEXT
