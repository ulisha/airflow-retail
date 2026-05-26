Airflow project files for retail ETL.
Connection in Airflow:
Conn Id: retail_postgres
Conn Type: Postgres
Host: postgres
Schema: retail
Login: airflow
Password: airflow
Port: 5432

## Локальный контур платформы

- Airflow: http://localhost:8080
- PostgreSQL: localhost:5432, база `retail`
- LLM-ассистент: http://localhost:8000
- Локальный DataLens: http://localhost:8081

Базовый запуск:

```bash
docker compose up -d
```

После выполнения DAG `retail_etl_pipeline` создайте views для ассистента:

```bash
docker compose exec postgres psql -U airflow -d retail -f /llm_sql/llm_views.sql
```

DataLens подключается к витринам PostgreSQL/CSV, а ассистент используется как отдельный сервис интерпретации:

- `http://localhost:8000/insight/monthly-summary?month=2024-12`
- `http://localhost:8000/insight/plan-fact?month=2024-12`
- `http://localhost:8000/insight/inventory?report_date=2024-12-31`

## Бесплатная реализация с локальным DataLens

Для ВКР используется полностью локальный и воспроизводимый контур без Managed PostgreSQL:

```text
CSV -> Airflow -> PostgreSQL Docker -> SQL-витрины dm.* -> локальный DataLens -> dashboards
                                                   -> LLM assistant
```

Дополнительный внешний источник:

```text
XML API ЦБ РФ -> Airflow -> raw.currency_rates_raw -> stg.currency_rates_clean -> dm.dm_currency_rates -> FX-витрины
```

Справочник `dm.dm_currency_rates` хранит историю курсов USD, EUR и CNY к рублю с 2024-01-01. Набор валют можно поменять через переменную окружения `CURRENCY_CODES`, например `USD,EUR,CNY,KZT`.

Практические витрины для графиков:

- `dm.v_currency_rates_monthly` — месячная динамика курса и волатильность.
- `dm.v_sales_fx_monthly` — выручка, себестоимость и прибыль в рублях и в пересчете по валютам.
- `dm.v_fx_risk_metrics` — оценка валютного давления на себестоимость и маржу.

Подробная инструкция: [docs/local-datalens.md](docs/local-datalens.md)

Команды:

```bash
./scripts/setup_local_analytics.sh
./scripts/start_local_datalens.sh
```
