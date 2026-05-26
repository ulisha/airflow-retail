# Полное описание проекта retail analytics

## 1. Назначение проекта

Проект представляет собой локальную аналитическую платформу для розничной сети. Она автоматизирует загрузку CSV-данных, очистку, хранение, расчет витрин, визуализацию показателей и текстовую интерпретацию аналитики через LLM-ассистента.

Основной сценарий работы:

```text
CSV-файлы -> Apache Airflow -> PostgreSQL -> SQL-витрины dm.* -> DataLens -> dashboard
                                      \
                                       -> LLM analytics assistant -> текстовые выводы
```

Дополнительный источник данных:

```text
XML API ЦБ РФ -> Airflow -> raw.currency_rates_raw -> stg.currency_rates_clean -> dm.dm_currency_rates -> FX-витрины
```

Система нужна для демонстрации в ВКР и для учебного контура бизнес-аналитики: продажи, магазины, товары, остатки, план/факт, валютные риски и управленческие выводы.

## 2. Технологический стек

- `Docker Compose` - запуск всех сервисов локально.
- `Apache Airflow` - оркестрация ETL-процесса.
- `PostgreSQL 16` - хранение исходных, очищенных и аналитических данных.
- `Redis` - брокер сообщений для Airflow CeleryExecutor.
- `Python`, `pandas`, `SQLAlchemy` - обработка CSV, очистка данных и запись в PostgreSQL.
- `FastAPI` - backend LLM-ассистента.
- `Ollama` - локальный запуск LLM-модели для генерации текстовых аналитических выводов.
- `DataLens` - визуализация витрин PostgreSQL.

## 3. Структура проекта

### Корень проекта

`README.md` - краткая стартовая инструкция. В нем указаны адреса сервисов, базовая команда запуска, описание локального DataLens-контура, ссылки на endpoints LLM-ассистента и команды настройки аналитического слоя.

`docker-compose.yaml` - главный файл запуска инфраструктуры. В нем описаны контейнеры:

- `postgres` - PostgreSQL, хранит базу Airflow и отдельную базу `retail`;
- `redis` - брокер для CeleryExecutor;
- `airflow-apiserver` - веб-интерфейс Airflow на `http://localhost:8080`;
- `airflow-scheduler` - планировщик Airflow;
- `airflow-dag-processor` - обработчик DAG-файлов;
- `airflow-worker` - исполнитель задач Airflow;
- `airflow-triggerer` - компонент для deferrable-задач;
- `airflow-init` - первичная инициализация Airflow;
- `airflow-cli` - вспомогательный CLI-профиль;
- `flower` - опциональный мониторинг Celery на `http://localhost:5555`;
- `llm-analytics-assistant` - FastAPI-сервис аналитического ассистента на `http://localhost:8000`.

`docker-compose.yaml.broken` - резервная или сломанная версия compose-файла. В рабочем запуске используется `docker-compose.yaml`.

`docker-compose.override.bak` - резервная копия override-конфига Docker Compose.

`.env` - переменные окружения для основного compose-контура. Сейчас содержит `AIRFLOW_UID=50000`.

`.DS_Store` - служебный файл macOS, к логике проекта не относится.

### Папка `dags`

`dags/retail_etl_dag.py` - Airflow DAG `retail_etl_pipeline`. Он задает расписание, задачи и порядок выполнения ETL.

Расписание DAG:

```text
0 6,12,18 * * *
```

То есть пайплайн запускается каждый день в 06:00, 12:00 и 18:00. `catchup=False`, поэтому старые пропущенные интервалы автоматически не догоняются.

Задачи DAG:

- `truncate_stg` - очищает staging-таблицы `stg.*`;
- `load_to_raw` - загружает CSV-файлы в `raw.*`;
- `load_currency_rates_to_raw` - загружает историю курсов валют из API ЦБ РФ;
- `transform_to_stg` - очищает CSV-данные и пишет их в `stg.*`;
- `transform_currency_rates_to_stg` - очищает валютные данные;
- `upsert_dm_stores` - обновляет витрину магазинов;
- `upsert_dm_products` - обновляет витрину товаров;
- `upsert_dm_sales` - обновляет витрину продаж;
- `upsert_dm_inventory` - обновляет витрину остатков;
- `upsert_dm_plan_sales` - обновляет витрину планов продаж;
- `upsert_dm_currency_rates` - обновляет витрину курсов валют.

`dags/retail_etl_pipeline.py` - Python-логика ETL. В этом файле находятся функции чтения CSV, загрузки в PostgreSQL, очистки данных, получения курсов валют и upsert в слой `dm`.

Ключевые функции:

- `get_engine()` - создает подключение к базе `retail`;
- `read_csv(name)` - читает файл из `/opt/airflow/data`, то есть из локальной папки `retail_data`;
- `load_raw_table()` - пишет исходные данные в схему `raw`;
- `write_clean()` - пишет очищенные данные в схему `stg`;
- `fetch_currency_rates()` - получает курсы за одну дату из XML API ЦБ РФ;
- `fetch_currency_rates_history()` - получает исторические курсы валют с `2024-01-01` до текущей даты или до даты из переменной `CURRENCY_HISTORY_END`;
- `transform_stores()` - очищает справочник магазинов;
- `transform_products()` - очищает справочник товаров;
- `transform_sales()` - очищает продажи;
- `transform_inventory()` - очищает остатки;
- `transform_plan_sales()` - очищает план продаж;
- `transform_currency_rates()` - очищает курсы валют;
- `load_to_raw()` - загружает все CSV-файлы в `raw`;
- `load_currency_rates_to_raw()` - загружает курсы валют в `raw.currency_rates_raw`;
- `transform_to_stg()` - чистит CSV-данные и записывает в `stg`;
- `transform_currency_rates_to_stg()` - переносит валютные данные из `raw` в `stg`;
- `upsert_dm_*()` - обновляют финальные таблицы `dm`.

`dags/__pycache__` - скомпилированные Python-файлы. Создается автоматически, не является исходным кодом.

### Папка `retail_data`

В этой папке лежат исходные CSV-данные, которые Airflow загружает в PostgreSQL.

`retail_data/stores.csv` - справочник магазинов. Поля: `store_id`, `store_name`, `city`, `region`, `format`, `opening_date`, `store_area_sqm`, `employees_count`.

`retail_data/products.csv` - справочник товаров. Поля: `product_id`, `stock_code`, `product_name`, `category`, `subcategory`, `brand`, `supplier`, `unit_cost`, `unit_price`, `uom`, `is_active`.

`retail_data/sales.csv` - фактические продажи. Поля: `sale_id`, `invoice_no`, `invoice_type`, `sale_datetime`, `sale_date`, `sale_month`, `store_id`, `product_id`, `stock_code`, `description`, `category`, `quantity`, `unit_price`, `discount_rate`, `revenue`, `unit_cost`, `total_cost`, `profit`, `customer_id`, `country`, `sales_channel`.

`retail_data/inventory.csv` - остатки. Поля: `inventory_date`, `store_id`, `product_id`, `stock_qty`, `stock_value`, `reorder_point`, `days_of_cover`, `stock_status`.

`retail_data/plan_sales.csv` - план продаж. Поля: `plan_month`, `store_id`, `category`, `plan_revenue`, `plan_profit`, `plan_qty`.

### Папка `sql`

`sql/retail_objects.sql` - создает основные схемы и таблицы PostgreSQL:

- `raw` - слой исходных данных;
- `stg` - слой очищенных данных;
- `dm` - аналитический слой.

Таблицы слоя `raw`:

- `raw.sales_raw`;
- `raw.stores_raw`;
- `raw.products_raw`;
- `raw.inventory_raw`;
- `raw.plan_sales_raw`;
- `raw.currency_rates_raw`.

Таблицы слоя `stg`:

- `stg.sales_clean`;
- `stg.stores_clean`;
- `stg.products_clean`;
- `stg.inventory_clean`;
- `stg.plan_sales_clean`;
- `stg.currency_rates_clean`.

Таблицы слоя `dm`:

- `dm.dm_sales`;
- `dm.dm_stores`;
- `dm.dm_products`;
- `dm.dm_inventory`;
- `dm.dm_plan_sales`;
- `dm.dm_currency_rates`.

`sql/analytics_views.sql` - создает расширенные аналитические views для BI и DataLens. Основные витрины:

- `dm.v_sales_enriched` - обогащенные продажи с датой, магазином, регионом, товаром, категорией, брендом, поставщиком, маржинальностью, выручкой на сотрудника и выручкой на квадратный метр;
- `dm.v_monthly_sales_kpi` - месячные KPI: выручка, себестоимость, прибыль, количество, маржа;
- `dm.v_store_performance` - эффективность магазинов;
- `dm.v_category_performance` - эффективность категорий, брендов и поставщиков;
- `dm.v_category_plan_fact_mart` - план/факт по категориям;
- `dm.v_plan_fact_dashboard` - план/факт по магазину и категории;
- `dm.v_inventory_risks` - риски по остаткам: дефицит, излишки, отклонение от точки заказа;
- `dm.v_dashboard_summary` - сводная витрина для executive dashboard;
- `dm.v_monthly_plan_fact_trend` - месячный тренд плана и факта;
- `dm.v_retail_kpi_mart` - широкая управленческая витрина по месяцу, магазину и категории;
- `dm.v_store_monthly_heatmap` - данные для тепловой карты магазинов;
- `dm.v_abc_xyz_analysis` - ABC/XYZ-анализ товаров;
- `dm.v_product_inventory_turnover` - оборачиваемость товаров и запасов;
- `dm.v_currency_rates_monthly` - месячная динамика курсов валют;
- `dm.v_sales_fx_monthly` - продажи, себестоимость и прибыль в рублях и пересчете по валютам;
- `dm.v_fx_risk_metrics` - оценка валютного давления на себестоимость и маржу.

### Папка `postgres-init`

`postgres-init/01-create-retail-db.sql` - init-скрипт PostgreSQL. При первом создании контейнера создает базу `retail`, если ее еще нет, и выдает права пользователю `airflow`.

Важно: этот скрипт выполняется только при первом создании volume PostgreSQL. Если volume уже существует, повторно он автоматически не отработает.

### Папка `scripts`

`scripts/setup_local_analytics.sh` - основной скрипт подготовки аналитического слоя. Он:

1. Запускает PostgreSQL, Redis и Airflow-сервисы.
2. Проверяет и создает базу `retail`.
3. Выполняет `sql/retail_objects.sql`.
4. Выполняет `llm_analytics_assistant/sql/llm_views.sql`.
5. Выполняет `sql/analytics_views.sql`.
6. Создает роль `retail_bi` с паролем `retail_bi`.
7. Выдает `retail_bi` права чтения на схемы `dm` и `stg`.

`scripts/start_local_datalens.sh` - запускает локальный open-source DataLens. Если исходники DataLens еще не скачаны, скрипт клонирует репозиторий в `.local/datalens`, затем запускает его через Docker Compose. По умолчанию UI доступен на `http://localhost:8081`.

`scripts/stop_local_datalens.sh` - останавливает локальный DataLens через `docker compose down` в папке `.local/datalens`.

### Папка `docs`

`docs/local-datalens.md` - подробная инструкция по локальному DataLens-контуру: запуск Airflow, запуск DAG, создание витрин, запуск DataLens, создание PostgreSQL connection, создание datasets и dashboard pages.

`docs/managed-postgresql-datalens.md` - инструкция для облачного сценария: локальная подготовка данных, dump PostgreSQL, загрузка в Managed PostgreSQL Yandex Cloud и подключение DataLens к облачной базе.

### Папка `llm_analytics_assistant`

Это отдельный backend-сервис аналитического ассистента.

`llm_analytics_assistant/README.md` - описание модуля, endpoints, запуск через Docker и локальный запуск.

`llm_analytics_assistant/Dockerfile` - сборка контейнера FastAPI-сервиса на базе `python:3.12-slim`.

`llm_analytics_assistant/requirements.txt` - зависимости Python:

- `fastapi`;
- `uvicorn`;
- `sqlalchemy`;
- `psycopg2-binary`;
- `pydantic`;
- `pydantic-settings`;
- `python-dotenv`;
- `openai`;
- `jinja2`.

`llm_analytics_assistant/.env` - реальные переменные окружения сервиса. В нем задаются параметры PostgreSQL, выбранный LLM-провайдер, адрес Ollama или параметры YandexGPT.

`llm_analytics_assistant/.env.example` - пример переменных окружения для ассистента.

`llm_analytics_assistant/authorized_key.json` - файл ключа/авторизации. Его нельзя публиковать в открытый репозиторий или прикладывать к публичной ВКР без удаления секретных данных.

`llm_analytics_assistant/test_llm.py` - простой тестовый скрипт вызова LLM через функцию `ask_llm`.

`llm_analytics_assistant/sql/llm_views.sql` - SQL-views, которые нужны именно LLM-ассистенту:

- `dm.v_monthly_kpi`;
- `dm.v_store_monthly_ranking`;
- `dm.v_category_monthly_ranking`;
- `dm.v_plan_fact_summary`;
- `dm.v_plan_fact_store`;
- `dm.v_plan_fact_category`;
- `dm.v_inventory_summary`;
- `dm.v_inventory_alerts`.

#### Код ассистента

`llm_analytics_assistant/app/main.py` - FastAPI-приложение. Содержит:

- создание приложения `FastAPI`;
- модели валидации `MonthRequest` и `InventoryRequest`;
- endpoint `/health`;
- HTML-интерфейс `/`;
- POST/GET endpoints для аналитических сценариев.

Основные endpoints:

- `GET /health` - проверка работоспособности;
- `GET /` - веб-интерфейс ассистента;
- `POST /insight/monthly-summary` - итог месяца;
- `POST /insight/plan-fact` - план/факт;
- `POST /insight/inventory` - остатки;
- `GET /insight/monthly-summary?month=YYYY-MM` - итог месяца через ссылку;
- `GET /insight/plan-fact?month=YYYY-MM` - план/факт через ссылку;
- `GET /insight/inventory?report_date=YYYY-MM-DD` - остатки через ссылку.

`llm_analytics_assistant/app/config.py` - настройки сервиса через `pydantic-settings`: host, port, подключение к PostgreSQL, LLM provider, Ollama, YandexGPT, timeout.

`llm_analytics_assistant/app/db.py` - создает SQLAlchemy engine для подключения к PostgreSQL.

`llm_analytics_assistant/app/llm.py` - тонкая обертка `ask_llm(prompt)`, которая вызывает `generate_insight`.

`llm_analytics_assistant/app/prompts.py` - системный prompt и шаблоны prompt для трех сценариев:

- месячное управленческое резюме;
- план/факт;
- остатки.

В prompt отдельно прописаны ограничения: не выдумывать факты, не пересчитывать проценты, писать по-русски, правильно трактовать выполнение плана.

`llm_analytics_assistant/app/services/analytics.py` - сервисный слой аналитики. Он выполняет SQL-запросы к views, собирает payload, вызывает LLM и при ошибке использует локальный fallback-текст.

`llm_analytics_assistant/app/services/llm.py` - слой работы с LLM. Поддерживает:

- `ollama` через локальный HTTP API;
- `yandex` через OpenAI-compatible API YandexGPT.

### Папка `config`

`config/airflow.cfg` - конфигурация Airflow, которая монтируется в контейнеры Airflow как `/opt/airflow/config/airflow.cfg`.

### Папка `plugins`

`plugins` - стандартная папка Airflow для пользовательских плагинов. Сейчас в проекте она пустая или не используется.

### Папка `logs`

`logs` - логи Airflow: обработка DAG, запуски задач, попытки выполнения. Эта папка создается и пополняется автоматически. Для описания проекта это служебная папка, но для администратора она важна при диагностике ошибок.

### Папка `.local`

`.local/datalens` - локальная копия open-source DataLens, если она уже была скачана скриптом `scripts/start_local_datalens.sh`. Это внешняя зависимость, не основной код проекта.

### Папка `диплом`

`диплом` - материалы ВКР: документы `.docx`, генератор форматированного документа, исходные или дублирующие наборы данных. На работу ETL-платформы напрямую не влияет, но относится к учебному оформлению проекта.

## 4. Логика работы ETL

### Шаг 1. Создание базы и таблиц

PostgreSQL поднимается в контейнере `postgres`. При первом старте выполняется `postgres-init/01-create-retail-db.sql`, который создает базу `retail`.

После этого скрипт `scripts/setup_local_analytics.sh` выполняет `sql/retail_objects.sql`, создавая схемы:

```text
raw -> stg -> dm
```

### Шаг 2. Загрузка исходных данных

Задача `load_to_raw` читает пять CSV-файлов из `retail_data`:

- `stores.csv`;
- `products.csv`;
- `sales.csv`;
- `inventory.csv`;
- `plan_sales.csv`.

Данные записываются в таблицы `raw.*` почти как есть. Дополнительно добавляются технические поля вроде `source_file` и `load_dttm`.

### Шаг 3. Загрузка курсов валют

Задача `load_currency_rates_to_raw` обращается к API ЦБ РФ:

- ежедневный endpoint: `https://www.cbr.ru/scripts/XML_daily.asp`;
- исторический endpoint: `https://www.cbr.ru/scripts/XML_dynamic.asp`.

По умолчанию загружаются валюты:

```text
USD, EUR, CNY
```

Список валют можно изменить через переменную:

```text
CURRENCY_CODES
```

### Шаг 4. Очистка данных

Задача `transform_to_stg`:

- удаляет дубли;
- приводит даты к типу date/timestamp;
- приводит числовые поля к числам;
- заполняет отдельные пустые значения нулями;
- удаляет записи без ключевых обязательных полей;
- фильтрует продажи с некорректными количествами и выручкой;
- проверяет связи продаж и остатков со справочниками магазинов и товаров.

Результат записывается в таблицы `stg.*`.

### Шаг 5. Обновление аналитического слоя

Задачи `upsert_dm_*` обновляют таблицы `dm.*` через `INSERT ... ON CONFLICT DO UPDATE`. Это значит, что при повторном запуске данные не просто дублируются в `dm`, а обновляются по ключам:

- продажи - по `sale_id`;
- магазины - по `store_id`;
- товары - по `product_id`;
- остатки - по `inventory_date`, `store_id`, `product_id`;
- план продаж - по `plan_month`, `store_id`, `category`;
- курсы валют - по `rate_date`, `currency_code`.

### Шаг 6. Витрины для BI и LLM

После загрузки `dm.*` создаются views:

- `llm_analytics_assistant/sql/llm_views.sql` - для LLM;
- `sql/analytics_views.sql` - для DataLens и расширенной аналитики.

## 5. Пользовательская инструкция

### Что нужно пользователю

Пользователю не нужно редактировать код. Основные действия:

1. Открыть Airflow.
2. Запустить DAG.
3. Открыть DataLens и смотреть dashboard.
4. Открыть LLM-ассистента и получить текстовый вывод.

### Запуск платформы

Откройте терминал и выполните:

```bash
cd /Users/ulyanasergeevna/airflow-retail
docker compose up -d
```

После запуска доступны:

- Airflow: `http://localhost:8080`;
- LLM-ассистент: `http://localhost:8000`;
- PostgreSQL: `localhost:5432`;
- локальный DataLens после отдельного запуска: `http://localhost:8081`.

Логин и пароль Airflow:

```text
airflow / airflow
```

### Запуск обработки данных

1. Откройте `http://localhost:8080`.
2. Найдите DAG `retail_etl_pipeline`.
3. Включите DAG, если он выключен.
4. Нажмите Trigger DAG для ручного запуска.
5. Дождитесь успешного выполнения всех задач.

После успешного выполнения DAG данные появятся в PostgreSQL в слоях `raw`, `stg`, `dm`.

### Подготовка аналитических витрин

После успешного DAG выполните:

```bash
cd /Users/ulyanasergeevna/airflow-retail
./scripts/setup_local_analytics.sh
```

Скрипт пересоздаст/обновит таблицы и views, а также выдаст права пользователю `retail_bi`.

### Запуск DataLens

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

### Подключение DataLens к PostgreSQL

В DataLens создайте PostgreSQL connection:

```text
Hostname: host.docker.internal
Port: 5432
Database: retail
Username: airflow
Password: airflow
TLS: off
Raw SQL level: Allow subqueries in datasets
```

Можно использовать отдельного пользователя только для чтения:

```text
Username: retail_bi
Password: retail_bi
```

### Рекомендуемые datasets в DataLens

Создайте datasets на основе views:

- `dm.v_sales_enriched` - продажи с расширенными атрибутами;
- `dm.v_monthly_sales_kpi` - KPI по месяцам;
- `dm.v_store_performance` - эффективность магазинов;
- `dm.v_category_performance` - эффективность категорий;
- `dm.v_plan_fact_dashboard` - план/факт;
- `dm.v_inventory_risks` - риски остатков;
- `dm.v_dashboard_summary` - сводка для главной страницы;
- `dm.v_retail_kpi_mart` - широкая управленческая витрина;
- `dm.v_abc_xyz_analysis` - ABC/XYZ товаров;
- `dm.v_fx_risk_metrics` - валютные риски.

### Рекомендуемые страницы dashboard

Executive Summary:

- KPI: выручка;
- KPI: прибыль;
- KPI: маржинальность;
- KPI: выполнение плана;
- график выручки по месяцам;
- таблица месячных KPI.

Sales Analytics:

- выручка по дням;
- выручка по категориям;
- прибыль по брендам;
- продажи по каналам;
- таблица продаж по магазину, товару и категории.

Store Performance:

- выручка по магазинам;
- прибыль по магазинам;
- выручка на сотрудника;
- выручка на квадратный метр.

Plan vs Fact:

- плановая выручка;
- фактическая выручка;
- процент выполнения плана;
- отклонение от плана по магазинам и категориям.

Inventory Risks:

- стоимость запасов;
- дефицитные позиции;
- избыточные позиции;
- остатки по категориям;
- таблица товаров со статусами запасов.

FX Risks:

- динамика USD/EUR/CNY;
- выручка и прибыль в пересчете по валютам;
- валютное давление на себестоимость;
- статус валютного риска.

### Использование LLM-ассистента

Откройте:

```text
http://localhost:8000
```

В интерфейсе доступны три сценария:

- итоги месяца;
- план/факт;
- остатки.

Примеры ссылок:

```text
http://localhost:8000/insight/monthly-summary?month=2024-12
http://localhost:8000/insight/plan-fact?month=2024-12
http://localhost:8000/insight/inventory?report_date=2024-12-31
```

Эти ссылки можно добавить в текстовые виджеты DataLens, чтобы рядом с dashboard открывать управленческий текстовый вывод.

### Остановка сервисов

Остановить основной контур:

```bash
cd /Users/ulyanasergeevna/airflow-retail
docker compose down
```

Остановить DataLens:

```bash
cd /Users/ulyanasergeevna/airflow-retail
./scripts/stop_local_datalens.sh
```

## 6. Инструкция для администратора и разработчика

### Требования

Для локального запуска нужны:

- Docker Desktop;
- Docker Compose;
- свободные порты `5432`, `8080`, `8000`, `8081`;
- не менее 4 GB RAM для Docker;
- доступ в интернет для загрузки образов Docker, клонирования DataLens и получения курсов ЦБ РФ.

Для локального LLM через Ollama дополнительно нужен запущенный Ollama на хосте:

```text
http://host.docker.internal:11434
```

По умолчанию используется модель:

```text
qwen2.5:3b
```

### Основные команды администратора

Запуск всех сервисов:

```bash
docker compose up -d
```

Пересборка LLM-сервиса:

```bash
docker compose up -d --build llm-analytics-assistant
```

Просмотр статуса контейнеров:

```bash
docker compose ps
```

Просмотр логов Airflow scheduler:

```bash
docker compose logs airflow-scheduler
```

Просмотр логов LLM-ассистента:

```bash
docker compose logs llm-analytics-assistant
```

Подключение к PostgreSQL:

```bash
docker compose exec postgres psql -U airflow -d retail
```

Ручное создание объектов:

```bash
docker compose exec postgres psql -U airflow -d retail -f /project_sql/retail_objects.sql
docker compose exec postgres psql -U airflow -d retail -f /llm_sql/llm_views.sql
docker compose exec postgres psql -U airflow -d retail -f /project_sql/analytics_views.sql
```

Проверка health LLM-сервиса:

```bash
curl http://localhost:8000/health
```

### Подключение Airflow к retail PostgreSQL

В Airflow должно быть подключение:

```text
Conn Id: retail_postgres
Conn Type: Postgres
Host: postgres
Schema: retail
Login: airflow
Password: airflow
Port: 5432
```

Это подключение используется задачей `truncate_stg` в `dags/retail_etl_dag.py`.

Python-функции ETL используют переменные окружения:

```text
RETAIL_DB_HOST=postgres
RETAIL_DB_PORT=5432
RETAIL_DB_NAME=retail
RETAIL_DB_USER=airflow
RETAIL_DB_PASSWORD=airflow
```

Если переменные не заданы, используются такие же значения по умолчанию.

### Настройка валют

В `dags/retail_etl_pipeline.py` используются переменные:

```text
CBR_DAILY_URL
CBR_DYNAMIC_URL
CURRENCY_CODES
CURRENCY_HISTORY_START
CURRENCY_HISTORY_END
```

По умолчанию:

```text
CURRENCY_CODES=USD,EUR,CNY
CURRENCY_HISTORY_START=2024-01-01
```

Чтобы добавить, например, тенге:

```text
CURRENCY_CODES=USD,EUR,CNY,KZT
```

После изменения нужно перезапустить Airflow-контейнеры и снова выполнить DAG.

### Настройка LLM-провайдера

Файл настроек:

```text
llm_analytics_assistant/.env
```

Локальный Ollama:

```text
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b
```

Если LLM недоступна, `analytics.py` возвращает локальный fallback-текст на основе данных из витрин.

### Как добавить новый CSV-источник

1. Положить файл в `retail_data`.
2. Добавить таблицу `raw.*` в `sql/retail_objects.sql`.
3. Добавить таблицу `stg.*`, если нужна очистка.
4. Добавить таблицу `dm.*`, если источник участвует в аналитическом слое.
5. Добавить функцию трансформации в `dags/retail_etl_pipeline.py`.
6. Добавить загрузку в `load_to_raw()`.
7. Добавить запись в `transform_to_stg()`.
8. Добавить upsert-функцию в `dm`.
9. Добавить задачу и зависимости в `dags/retail_etl_dag.py`.
10. При необходимости добавить views в `sql/analytics_views.sql` и `llm_analytics_assistant/sql/llm_views.sql`.

### Как добавить новую витрину для DataLens

1. Описать view в `sql/analytics_views.sql`.
2. Выполнить:

```bash
docker compose exec postgres psql -U airflow -d retail -f /project_sql/analytics_views.sql
```

3. Проверить view:

```sql
SELECT * FROM dm.<view_name> LIMIT 10;
```

4. Создать dataset в DataLens на основе этой view.

### Как добавить новый сценарий LLM-ассистента

1. Добавить SQL-view в `llm_analytics_assistant/sql/llm_views.sql`.
2. Добавить функцию выборки и сборки payload в `llm_analytics_assistant/app/services/analytics.py`.
3. Добавить prompt builder в `llm_analytics_assistant/app/prompts.py`.
4. Добавить Pydantic-модель запроса, endpoint и UI-логику в `llm_analytics_assistant/app/main.py`.
5. Пересобрать контейнер:

```bash
docker compose up -d --build llm-analytics-assistant
```

6. Проверить endpoint через браузер или `curl`.

### Диагностика типовых проблем

Airflow не открывается:

- проверить `docker compose ps`;
- проверить, свободен ли порт `8080`;
- посмотреть логи `airflow-apiserver` и `airflow-scheduler`.

DAG падает на подключении к PostgreSQL:

- проверить Airflow connection `retail_postgres`;
- проверить, что контейнер `postgres` healthy;
- проверить, что база `retail` создана.

DAG падает на загрузке курсов валют:

- проверить интернет-доступ из контейнера Airflow;
- проверить доступность `www.cbr.ru`;
- временно ограничить период через `CURRENCY_HISTORY_END`.

DataLens не подключается к PostgreSQL:

- использовать hostname `host.docker.internal`;
- проверить порт `5432`;
- проверить логин и пароль;
- проверить, что база `retail` существует;
- проверить, что views созданы.

LLM-ассистент пишет, что нет данных:

- сначала выполнить DAG;
- затем выполнить `scripts/setup_local_analytics.sh`;
- проверить наличие данных в `dm.dm_sales`, `dm.dm_plan_sales`, `dm.dm_inventory`;
- проверить views из `llm_analytics_assistant/sql/llm_views.sql`.

LLM-ассистент возвращает fallback:

- это значит, что данные получены, но модель недоступна или вернула ошибку;
- для Ollama проверить, что сервис запущен на хосте;
- проверить, что модель из `OLLAMA_MODEL` скачана командой `ollama pull`.

### Безопасность и публикация

Перед публикацией проекта нельзя выкладывать:

- реальные API-ключи из `llm_analytics_assistant/.env`;
- `llm_analytics_assistant/authorized_key.json`, если внутри есть приватный ключ;
- логи с потенциально чувствительными данными;
- временные Word lock-файлы из папки `диплом`, например файлы с префиксом `~$`.

Для публичной версии лучше оставить только `.env.example`, а реальные `.env` и ключи добавить в `.gitignore`.

## 7. Краткое описание для ВКР

В рамках проекта реализована контейнеризированная аналитическая платформа для розничной сети. Источниками данных являются CSV-файлы с продажами, справочниками магазинов и товаров, остатками и плановыми показателями, а также XML API Банка России для загрузки курсов валют. Apache Airflow автоматически выполняет ETL-процесс: загружает исходные данные в слой `raw`, очищает и нормализует их в слое `stg`, затем обновляет аналитические таблицы слоя `dm` в PostgreSQL.

На основе слоя `dm` построены SQL-витрины для анализа продаж, эффективности магазинов, категорий, выполнения плана, товарных остатков, ABC/XYZ-классификации и валютных рисков. Для визуализации используется DataLens, подключенный к PostgreSQL. Дополнительно реализован LLM-ассистент на FastAPI, который получает агрегированные показатели из аналитических витрин и формирует краткие управленческие выводы по итогам месяца, план/факт анализу и состоянию запасов.

Такое решение демонстрирует полный цикл современной аналитической системы: сбор данных, автоматизированную обработку, хранение, расчет витрин, визуализацию и интеллектуальную интерпретацию результатов.
