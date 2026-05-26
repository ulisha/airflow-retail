# Локальный DataLens для ВКР

Целевой бесплатный контур:

```text
CSV -> Airflow -> PostgreSQL Docker -> SQL-витрины dm.* -> локальный DataLens -> dashboards
                                                   -> LLM assistant
```

В этом варианте нет ручной загрузки CSV в DataLens. Airflow загружает и обрабатывает данные, PostgreSQL хранит аналитический слой, а DataLens подключается к PostgreSQL как BI-инструмент.

## 1. Поднять основной контур

```bash
cd /Users/ulyanasergeevna/airflow-retail
docker compose up -d
```

Откройте Airflow:

```text
http://localhost:8080
```

Логин и пароль:

```text
airflow / airflow
```

Запустите DAG:

```text
retail_etl_pipeline
```

## 2. Создать аналитические витрины

После успешного выполнения DAG:

```bash
cd /Users/ulyanasergeevna/airflow-retail
./scripts/setup_local_analytics.sh
```

Скрипт создает:

- базовые объекты `raw`, `stg`, `dm`;
- views для LLM-ассистента;
- расширенные views для DataLens.

Главная широкая витрина:

```text
dm.v_sales_enriched
```

В ней больше 20 аналитических атрибутов: дата, год, квартал, неделя, магазин, регион, формат, товар, категория, бренд, поставщик, выручка, прибыль, маржинальность, выручка на сотрудника, выручка на кв. м и другие показатели.

## 3. Запустить локальный DataLens

Airflow уже использует порт `8080`, поэтому DataLens запускается на `8081`.

```bash
cd /Users/ulyanasergeevna/airflow-retail
./scripts/start_local_datalens.sh
```

Откройте:

```text
http://localhost:8081
```

Логин и пароль локального DataLens:

```text
admin / admin
```

## 4. Создать PostgreSQL connection в DataLens

В DataLens:

1. Create -> Connection.
2. Выберите PostgreSQL.
3. Укажите параметры:

```text
Hostname: host.docker.internal
Port: 5432
Database: retail
Username: airflow
Password: airflow
TLS: off
Raw SQL level: Allow subqueries in datasets
```

Почему `host.docker.internal`: локальный DataLens тоже работает в Docker, а PostgreSQL проброшен на порт Mac `5432`. Через этот host контейнеры DataLens обращаются к хост-машине.

## 5. Создать datasets

Создайте отдельные datasets:

1. `Sales Enriched`
   - source: `dm.v_sales_enriched`
2. `Monthly Sales KPI`
   - source: `dm.v_monthly_sales_kpi`
3. `Store Performance`
   - source: `dm.v_store_performance`
4. `Category Performance`
   - source: `dm.v_category_performance`
5. `Plan Fact`
   - source: `dm.v_plan_fact_dashboard`
6. `Inventory Risks`
   - source: `dm.v_inventory_risks`
7. `Dashboard Summary`
   - source: `dm.v_dashboard_summary`

## 6. Собрать дашборды

### Executive Summary

Dataset: `Dashboard Summary`, `Monthly Sales KPI`.

Виджеты:

- KPI: revenue
- KPI: profit
- KPI: margin_pct
- KPI: revenue_plan_completion_pct
- line chart: revenue by sale_month
- bar chart: profit by sale_month
- table: sale_month, revenue, profit, margin_pct, revenue_plan_completion_pct

Селекторы:

- sale_month

### Sales Analytics

Dataset: `Sales Enriched`.

Виджеты:

- line chart: revenue by sale_date
- bar chart: revenue by category
- bar chart: profit by brand
- donut: revenue by sales_channel
- table: store_name, product_name, category, revenue, profit, margin_pct

Селекторы:

- sale_month
- region
- store_format
- category
- sales_channel

### Store Performance

Dataset: `Store Performance`.

Виджеты:

- bar chart: revenue by store_name
- bar chart: profit by store_name
- bar chart: revenue_per_employee by store_name
- bar chart: revenue_per_sqm by store_name
- table: store_name, city, region, revenue, profit, margin_pct, revenue_per_employee, revenue_per_sqm

Селекторы:

- sale_month
- region
- city
- store_format

### Plan vs Fact

Dataset: `Plan Fact`.

Виджеты:

- KPI: plan_revenue
- KPI: fact_revenue
- KPI: revenue_plan_completion_pct
- bar chart: plan_revenue and fact_revenue by category
- bar chart: revenue_variance by store_name
- table: store_name, category, plan_revenue, fact_revenue, revenue_variance, revenue_plan_completion_pct

Селекторы:

- plan_month
- region
- category

### Inventory Risks

Dataset: `Inventory Risks`.

Виджеты:

- KPI: stock_value
- KPI: is_low_stock
- KPI: is_overstock
- bar chart: stock_value by category
- table: store_name, product_name, category, stock_qty, reorder_point, days_of_cover, stock_status
- bar chart: stock_status by region

Селекторы:

- inventory_date
- region
- category
- stock_status

## 7. LLM-ассистент

Ассистент запускается в основном docker-compose:

```text
http://localhost:8000
```

Ссылки для текстовых виджетов в DataLens:

```text
http://localhost:8000/insight/monthly-summary?month=2024-12
http://localhost:8000/insight/plan-fact?month=2024-12
http://localhost:8000/insight/inventory?report_date=2024-12-31
```

## 8. Формулировка для ВКР

В работе реализована контейнеризированная аналитическая платформа для автоматизации обработки данных розничной сети. Загрузка и трансформация данных выполняются в Apache Airflow, хранение и расчет аналитических витрин реализованы в PostgreSQL, визуализация ключевых показателей выполнена в DataLens, развернутом локально в Docker. Дополнительно реализован LLM-модуль интерпретации аналитических витрин, который формирует текстовые управленческие выводы по продажам, план/факт анализу и остаткам.
