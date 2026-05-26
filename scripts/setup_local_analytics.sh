#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"

echo "Starting PostgreSQL and Airflow services..."
docker compose up -d postgres redis airflow-apiserver airflow-scheduler airflow-worker airflow-dag-processor airflow-triggerer

echo "Ensuring retail database exists..."
docker compose exec -T postgres psql -U airflow -d postgres <<'SQL'
SELECT 'CREATE DATABASE retail'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'retail')\gexec
GRANT ALL PRIVILEGES ON DATABASE retail TO airflow;
SQL

echo "Creating base schemas and tables..."
docker compose exec -T postgres psql -U airflow -d retail -f /project_sql/retail_objects.sql

echo "Creating assistant and DataLens analytical views..."
docker compose exec -T postgres psql -U airflow -d retail -f /llm_sql/llm_views.sql
docker compose exec -T postgres psql -U airflow -d retail -f /project_sql/analytics_views.sql

echo "Granting DataLens read permissions..."
docker compose exec -T postgres psql -U airflow -d retail <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'retail_bi') THEN
        CREATE ROLE retail_bi LOGIN PASSWORD 'retail_bi';
    ELSE
        ALTER ROLE retail_bi WITH LOGIN PASSWORD 'retail_bi';
    END IF;
END $$;

GRANT CONNECT ON DATABASE retail TO retail_bi;
GRANT USAGE ON SCHEMA dm, stg TO retail_bi;
GRANT SELECT ON ALL TABLES IN SCHEMA dm, stg TO retail_bi;
ALTER DEFAULT PRIVILEGES IN SCHEMA dm GRANT SELECT ON TABLES TO retail_bi;
ALTER DEFAULT PRIVILEGES IN SCHEMA stg GRANT SELECT ON TABLES TO retail_bi;
SQL

cat <<'TEXT'

Local analytical layer is ready.

Next step:
1. Open Airflow: http://localhost:8080
2. Run DAG: retail_etl_pipeline
3. Run this script again after the DAG succeeds, so analytical views are recreated over loaded data.

TEXT
