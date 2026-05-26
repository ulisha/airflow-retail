SELECT 'CREATE DATABASE retail'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'retail')\gexec

GRANT ALL PRIVILEGES ON DATABASE retail TO airflow;
