from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text
from app.config import settings
from app.db import engine
from app.prompts import build_inventory_prompt, build_monthly_summary_prompt, build_plan_fact_prompt
from app.services.llm import generate_insight

def normalize_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value

def normalize_row(row: dict) -> dict:
    return {key: normalize_value(value) for key, value in row.items()}

def fetch_one(sql: str, params: dict) -> dict:
    with engine.begin() as conn:
        row = conn.execute(text(sql), params).mappings().first()
    return normalize_row(dict(row)) if row else {}

def fetch_many(sql: str, params: dict) -> list[dict]:
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    return [normalize_row(dict(r)) for r in rows]

def build_response(payload: dict, prompt: str) -> dict:
    if not any(value for key, value in payload.items() if key not in {"month", "report_date"}):
        return {
            "context": payload,
            "insight": "По выбранному периоду нет данных в аналитических витринах.",
        }
    try:
        insight = generate_insight(prompt)
        return {
            "context": payload,
            "insight": insight,
            "insight_source": settings.llm_provider.lower().strip(),
        }
    except Exception as exc:
        return {
            "context": payload,
            "insight": build_local_insight(payload),
            "insight_source": "local_fallback",
            "llm_error": str(exc),
        }

def format_money(value) -> str:
    return f"{float(value or 0):,.0f}".replace(",", " ")

def format_pct(value) -> str:
    pct = float(value or 0)
    if abs(pct) <= 1:
        pct *= 100
    return f"{pct:.1f}%".replace(".0%", "%")

def build_local_insight(payload: dict) -> str:
    if "kpi" in payload:
        kpi = payload.get("kpi") or {}
        plan_fact = payload.get("plan_fact") or {}
        top_stores = payload.get("top_stores") or []
        low_stores = payload.get("low_stores") or []
        top_categories = payload.get("top_categories") or []
        best_store = top_stores[0]["store_id"] if top_stores else "нет данных"
        weak_store = low_stores[0]["store_id"] if low_stores else "нет данных"
        best_category = top_categories[0]["category"] if top_categories else "нет данных"
        plan_pct = plan_fact.get("plan_revenue_pct") or plan_fact.get("revenue_plan_completion_pct")
        return (
            f"За {payload.get('month')} выручка составила {format_money(kpi.get('revenue'))} руб., "
            f"прибыль — {format_money(kpi.get('profit'))} руб., продано {format_money(kpi.get('quantity'))} единиц. "
            f"Лучший магазин по выручке: {best_store}, зона внимания: {weak_store}. "
            f"Сильнейшая категория месяца: {best_category}. "
            f"Выполнение плана по выручке: {format_pct(plan_pct)}; это можно использовать как основной управленческий индикатор месяца."
        )

    if "worst_stores_by_plan" in payload:
        summary = payload.get("summary") or {}
        worst_stores = payload.get("worst_stores_by_plan") or []
        worst_categories = payload.get("worst_categories_by_plan") or []
        weak_store = worst_stores[0]["store_id"] if worst_stores else "нет данных"
        weak_category = worst_categories[0]["category"] if worst_categories else "нет данных"
        return (
            f"За {payload.get('month')} план по выручке выполнен на "
            f"{format_pct(summary.get('plan_revenue_pct') or summary.get('revenue_plan_completion_pct'))}, "
            f"план по прибыли — на {format_pct(summary.get('plan_profit_pct') or summary.get('profit_plan_completion_pct'))}. "
            f"Фактическая выручка составила {format_money(summary.get('fact_revenue'))} руб. при плане "
            f"{format_money(summary.get('plan_revenue'))} руб. "
            f"Наибольшее отставание наблюдается по магазину {weak_store} и категории {weak_category}. "
            f"Рекомендуется детально проверить ассортимент, остатки и промо-активности в этих сегментах."
        )

    if "low_stock" in payload or "overstock" in payload:
        summary = payload.get("summary") or {}
        low_stock = payload.get("low_stock") or []
        overstock = payload.get("overstock") or []
        low_count = len(low_stock)
        over_count = len(overstock)
        return (
            f"На дату {payload.get('report_date')} общий запас составляет "
            f"{format_money(summary.get('total_stock_qty'))} единиц на сумму "
            f"{format_money(summary.get('total_stock_value'))} руб. "
            f"В выборке выявлено {low_count} дефицитных позиций и {over_count} позиций с избыточным запасом. "
            f"Основной риск — одновременная потеря продаж по дефицитным товарам и заморозка оборотного капитала в излишках. "
            f"Рекомендуется приоритизировать пополнение LOW-позиций и пересмотреть закупки по OVERSTOCK."
        )

    return "Данные получены из витрин, но для выбранного сценария не настроен локальный шаблон интерпретации."

def monthly_summary(month: str) -> dict:
    payload = {
        "month": month,
        "kpi": fetch_one("SELECT * FROM dm.v_monthly_kpi WHERE sale_month = :month", {"month": month}),
        "top_stores": fetch_many("SELECT * FROM dm.v_store_monthly_ranking WHERE sale_month = :month ORDER BY revenue DESC LIMIT 3", {"month": month}),
        "low_stores": fetch_many("SELECT * FROM dm.v_store_monthly_ranking WHERE sale_month = :month ORDER BY revenue ASC LIMIT 3", {"month": month}),
        "top_categories": fetch_many("SELECT * FROM dm.v_category_monthly_ranking WHERE sale_month = :month ORDER BY revenue DESC LIMIT 3", {"month": month}),
        "low_categories": fetch_many("SELECT * FROM dm.v_category_monthly_ranking WHERE sale_month = :month ORDER BY revenue ASC LIMIT 3", {"month": month}),
        "plan_fact": fetch_one("SELECT * FROM dm.v_plan_fact_summary WHERE plan_month = :month", {"month": month}),
    }
    return build_response(payload, build_monthly_summary_prompt(payload))

def plan_fact_summary(month: str) -> dict:
    payload = {
        "month": month,
        "summary": fetch_one("SELECT * FROM dm.v_plan_fact_summary WHERE plan_month = :month", {"month": month}),
        "worst_stores_by_plan": fetch_many("SELECT * FROM dm.v_plan_fact_store WHERE plan_month = :month ORDER BY plan_revenue_pct ASC LIMIT 5", {"month": month}),
        "worst_categories_by_plan": fetch_many("SELECT * FROM dm.v_plan_fact_category WHERE plan_month = :month ORDER BY plan_revenue_pct ASC LIMIT 5", {"month": month}),
    }
    return build_response(payload, build_plan_fact_prompt(payload))

def inventory_summary(report_date: str) -> dict:
    payload = {
        "report_date": report_date,
        "summary": fetch_one("SELECT * FROM dm.v_inventory_summary WHERE inventory_date = :report_date", {"report_date": report_date}),
        "low_stock": fetch_many("SELECT * FROM dm.v_inventory_alerts WHERE inventory_date = :report_date AND stock_status = 'LOW' ORDER BY stock_value DESC LIMIT 10", {"report_date": report_date}),
        "overstock": fetch_many("SELECT * FROM dm.v_inventory_alerts WHERE inventory_date = :report_date AND stock_status = 'OVERSTOCK' ORDER BY stock_value DESC LIMIT 10", {"report_date": report_date}),
    }
    return build_response(payload, build_inventory_prompt(payload))
