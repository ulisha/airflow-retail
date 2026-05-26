# Managed PostgreSQL + DataLens

Эта инструкция переводит демонстрационный контур ВКР на облачный BI-слой:

```text
CSV -> Airflow ETL -> local PostgreSQL -> dump -> Managed PostgreSQL -> DataLens
                                             -> LLM assistant
```

## 1. Создать Managed PostgreSQL

В Yandex Cloud создайте кластер Managed Service for PostgreSQL.

Рекомендуемые параметры для ВКР:

- Cluster name: `retail-analytics-pg`
- Environment: `PRODUCTION`
- PostgreSQL version: 16
- Database: `retail`
- User: `retail_user`
- Disk: минимальный доступный размер для тарифа
- Hosts: 1 host для учебной демонстрации
- Access:
  - DataLens access: enabled
  - WebSQL access: enabled
  - Public IP: enabled, если будете загружать dump с Mac

DataLens должен быть активирован в том же cloud/folder.

## 2. Подготовить локальную БД

Запустите контейнеры:

```bash
cd /Users/ulyanasergeevna/airflow-retail
docker compose up -d
```

В Airflow выполните DAG `retail_etl_pipeline`.

После успешного DAG создайте витрины:

```bash
docker compose exec postgres psql -U airflow -d retail -f /llm_sql/llm_views.sql
docker compose exec postgres psql -U airflow -d retail -f /project_sql/analytics_views.sql
```

## 3. Сделать dump локальной БД

```bash
docker compose exec postgres pg_dump \
  -U airflow \
  -d retail \
  --schema=stg \
  --schema=dm \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file=/tmp/retail_dm.dump
```

Скопируйте dump из контейнера на Mac:

```bash
docker cp airflow-retail-postgres-1:/tmp/retail_dm.dump ./retail_dm.dump
```

Если имя контейнера отличается, посмотрите его:

```bash
docker compose ps postgres
```

## 4. Загрузить dump в Managed PostgreSQL

В Yandex Cloud откройте кластер PostgreSQL и скопируйте host/FQDN для подключения.

На Mac выполните:

```bash
pg_restore \
  --host=<managed_pg_host> \
  --port=6432 \
  --username=retail_user \
  --dbname=retail \
  --no-owner \
  --no-privileges \
  --clean \
  --if-exists \
  ./retail_dm.dump
```

Если порт 6432 не подходит, используйте порт, показанный в Connection Manager/Managed PostgreSQL.

## 5. Подключить DataLens

В DataLens:

1. Откройте workbook ВКР.
2. Create -> Connection.
3. Выберите PostgreSQL.
4. Лучше выбрать `Select in organization` или Connection Manager.
5. Укажите кластер `retail-analytics-pg`, базу `retail`, пользователя `retail_user`.
6. Нажмите Check connection.
7. Создайте datasets на основе views:
   - `dm.v_sales_enriched`
   - `dm.v_monthly_sales_kpi`
   - `dm.v_store_performance`
   - `dm.v_category_performance`
   - `dm.v_plan_fact_dashboard`
   - `dm.v_inventory_risks`
   - `dm.v_dashboard_summary`

## 6. Дашборды

Соберите 5 dashboard pages:

1. Executive Summary
2. Sales Analytics
3. Store Performance
4. Plan vs Fact
5. Inventory Risks

В текстовые виджеты добавьте ссылки на LLM assistant:

- `http://localhost:8000/insight/monthly-summary?month=2024-12`
- `http://localhost:8000/insight/plan-fact?month=2024-12`
- `http://localhost:8000/insight/inventory?report_date=2024-12-31`

Для публичной демонстрации ассистента можно развернуть отдельно в Yandex Cloud Container Registry + Serverless Containers или оставить локальным сервисом для защиты.
