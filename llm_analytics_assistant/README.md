# LLM analytics assistant

Этот модуль реализует сценарий: **LLM-ассистент для интерпретации уже подготовленной аналитики**.

## Архитектура
PostgreSQL (dm + views) -> FastAPI -> Ollama -> текстовый insight
PostgreSQL (dm + views) -> Yandex DataLens -> dashboards

DataLens не требует прямого вызова LLM API: BI-дашборды строятся поверх тех же витрин `dm`, а ассистент открывается как отдельный сервис для интерпретации выбранного периода. В DataLens его удобно добавить ссылкой в текстовый виджет dashboard:

- `http://localhost:8000/insight/monthly-summary?month=2024-12`
- `http://localhost:8000/insight/plan-fact?month=2024-12`
- `http://localhost:8000/insight/inventory?report_date=2024-12-31`

## Эндпоинты
- GET /health
- GET /
- POST /insight/monthly-summary
- POST /insight/plan-fact
- POST /insight/inventory
- GET /insight/monthly-summary?month=YYYY-MM
- GET /insight/plan-fact?month=YYYY-MM
- GET /insight/inventory?report_date=YYYY-MM-DD

## Пример запуска
1. Скопируйте `.env.example` в `.env`
2. Убедитесь, что Ollama запущена на хосте и модель скачана:
   - `ollama pull qwen2.5:3b`
   - `OLLAMA_BASE_URL=http://host.docker.internal:11434`
   - `OLLAMA_MODEL=qwen2.5:3b`
3. Запустите сервис вместе с платформой: `docker compose up -d --build llm-analytics-assistant`
4. Создайте views после загрузки витрин: `docker compose exec postgres psql -U airflow -d retail -f /llm_sql/llm_views.sql`
   Если выполняете команду с хоста: `psql -h localhost -U airflow -d retail -f llm_analytics_assistant/sql/llm_views.sql`
5. Откройте веб-интерфейс: `http://localhost:8000`

Локальный запуск без Docker:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Связка с DataLens
1. В DataLens подключите PostgreSQL или загрузите CSV-файлы, как описано в датасете для диплома.
2. Постройте дашборды по продажам, магазинам, категориям, план/факт и остаткам.
3. Добавьте текстовый виджет "AI-интерпретация" со ссылкой на нужный endpoint ассистента.
4. На защите показывайте один и тот же период в DataLens и в ассистенте: графики дают числовую картину, ассистент формирует краткий управленческий вывод.

## Что писать в ВКР
В платформу добавлен интеллектуальный модуль текстовой интерпретации аналитики. Модуль реализован как отдельный backend-сервис на FastAPI. Он обращается к аналитическим витринам `dm`, получает агрегированные показатели и передает их в локальную LLM-модель через Ollama в виде структурированного контекста.
